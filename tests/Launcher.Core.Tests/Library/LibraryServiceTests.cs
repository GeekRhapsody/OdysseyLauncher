using System.Globalization;
using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Data;
using Launcher.Core.Library;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Library;

public sealed class LibraryServiceTests : IAsyncLifetime
{
    private readonly TempDir _dir = new();
    private readonly ManualClock _clock = new(new DateTimeOffset(2026, 9, 28, 10, 0, 0, TimeSpan.Zero));
    private LibraryService _library = null!;

    private string DataDir => _dir.Combine("data");

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    public async ValueTask InitializeAsync() => _library = await Open(LoadConfig());

    public ValueTask DisposeAsync()
    {
        _library.Dispose();
        SqliteConnection.ClearAllPools();
        _dir.Dispose();
        return ValueTask.CompletedTask;
    }

    private AppConfig LoadConfig(string? systems = null)
    {
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = _dir.Path,
            ConfigDir = _dir.Combine("config"),
            Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = '{_dir.Combine("ROMs")}'\n"),
            Systems = systems is null ? null : new ConfigFile("systems.toml", systems),
        });
        Assert.False(result.HasErrors, string.Join('\n', result.Diagnostics));
        return result.Config;
    }

    private async Task<LibraryService> Open(AppConfig config)
    {
        var library = await LibraryService.OpenAsync(config, DataDir, _clock, Ct);
        library.IndexMedia = true;
        return library;
    }

    private string Rom(string relPath, string content = "rom", DateTime? modified = null) => _dir.File("ROMs/" + relPath, content, modified);

    /// <summary>A file in the media folder: <c>data/media/&lt;relPath&gt;</c>.</summary>
    private string Art(string relPath, byte[] content, DateTime? modified = null)
    {
        var path = _dir.File("data/media/" + relPath);
        File.WriteAllBytes(path, content);
        File.SetLastWriteTimeUtc(path, modified ?? new DateTime(2020, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        return path;
    }

    private async Task<string[]> Titles(string system) =>
        (await _library.GetGamesAsync(system, Ct)).Games.Select(g => g.Title).ToArray();

    private async Task<GameRow> Game(string system, string title) =>
        (await _library.GetGamesAsync(system, Ct)).Games.Single(g => g.Title == title);

    // ---- Scanning into the library ---------------------------------------------------------------

    [Fact]
    public async Task A_first_scan_adds_every_game_sorted_by_title()
    {
        Rom("snes/Super Mario World (USA).sfc");
        Rom("snes/Legend of Zelda, The - A Link to the Past (USA).sfc");
        Rom("snes/Mega Man X (USA).sfc");
        Rom("snes/Mega Man X2 (USA).sfc");
        Rom("megadrive/Sonic the Hedgehog (USA, Europe).md");

        var summary = await _library.RescanAsync(null, null, Ct);

        Assert.Equal(5, summary.Added);
        Assert.Equal(["The Legend of Zelda - A Link to the Past", "Mega Man X", "Mega Man X2", "Super Mario World"], await Titles("snes"));
        var systems = await _library.GetSystemsAsync(Ct);
        Assert.Equal(_library.Config.Systems.Count, systems.Count);
        Assert.Equal(4, systems.Single(s => s.SystemId == "snes").GameCount);
        Assert.Equal(1, systems.Single(s => s.SystemId == "megadrive").GameCount);
        Assert.Equal(0, systems.Single(s => s.SystemId == "psx").GameCount);
        Assert.Equal(_clock.Now, systems.Single(s => s.SystemId == "snes").ScannedAt);
    }

    [Fact]
    public async Task A_rescan_with_no_changes_writes_nothing()
    {
        Rom("snes/A.sfc");
        Rom("snes/B.sfc");
        await _library.RescanAsync(null, null, Ct);
        var before = Dump();

        var summary = await _library.RescanAsync(null, null, Ct);

        Assert.Equal((0, 0, 0, 2), (summary.Added, summary.Updated, summary.Removed, summary.Unchanged));
        Assert.Equal(before, Dump());
    }

    [Fact]
    public async Task A_rescan_picks_up_added_changed_and_removed_files()
    {
        Rom("snes/Keep.sfc");
        Rom("snes/Change.sfc");
        var remove = Rom("snes/Remove.sfc");
        await _library.RescanAsync("snes", null, Ct);
        var changedId = (await Game("snes", "Change")).GameId;

        Rom("snes/Change.sfc", "new content", new DateTime(2024, 5, 1, 0, 0, 0, DateTimeKind.Utc));
        File.Delete(remove);
        Rom("snes/Added.sfc");
        var summary = await _library.RescanAsync("snes", null, Ct);

        Assert.Equal((1, 1, 1, 1), (summary.Added, summary.Updated, summary.Removed, summary.Unchanged));
        Assert.Equal(["Added", "Change", "Keep"], await Titles("snes"));
        var changed = await _library.GetGameAsync(changedId, Ct);
        Assert.Equal("new content".Length, changed!.SizeBytes);
    }

    [Fact]
    public async Task A_rename_is_a_remove_plus_an_add_and_the_old_user_data_is_kept_as_an_orphan()
    {
        var old = Rom("snes/Old Name (USA).sfc");
        await _library.RescanAsync("snes", null, Ct);
        await _library.SetFavouriteAsync(new GameKey("snes", "old name (usa).sfc"), true, Ct);

        File.Move(old, _dir.Combine("ROMs", "snes", "New Name (USA).sfc"));
        var summary = await _library.RescanAsync("snes", null, Ct);

        Assert.Equal((1, 1), (summary.Added, summary.Removed));
        Assert.False((await Game("snes", "New Name")).IsFavourite);

        // Moving the file back restores its favourite: user data is keyed by path_key and never deleted by a scan.
        File.Move(_dir.Combine("ROMs", "snes", "New Name (USA).sfc"), old);
        await _library.RescanAsync("snes", null, Ct);
        Assert.True((await Game("snes", "Old Name")).IsFavourite);
    }

    [Fact]
    public async Task A_case_only_rename_keeps_the_game_id_and_its_user_data()
    {
        var old = Rom("snes/super mario world (usa).sfc");
        await _library.RescanAsync("snes", null, Ct);
        var before = await Game("snes", "super mario world");
        await _library.SetFavouriteAsync(new GameKey("snes", "super mario world (usa).sfc"), true, Ct);

        var renamed = _dir.Combine("ROMs", "snes", "Super Mario World (USA).sfc");
        File.Move(old, old + ".tmp");
        File.Move(old + ".tmp", renamed);
        var summary = await _library.RescanAsync("snes", null, Ct);

        Assert.Equal((0, 1, 0), (summary.Added, summary.Updated, summary.Removed));
        var after = await Game("snes", "Super Mario World");
        Assert.Equal(before.GameId, after.GameId);
        Assert.True(after.IsFavourite);
        Assert.Equal("Super Mario World (USA).sfc", (await _library.GetGameAsync(after.GameId, Ct))!.RelPath);
    }

    [Fact]
    public async Task Adding_an_m3u_later_folds_its_discs_into_one_game()
    {
        Rom("psx/Final Fantasy VII (USA) (Disc 1).chd");
        Rom("psx/Final Fantasy VII (USA) (Disc 2).chd");
        await _library.RescanAsync("psx", null, Ct);
        Assert.Equal(["Final Fantasy VII (Disc 1)", "Final Fantasy VII (Disc 2)"], await Titles("psx"));

        Rom("psx/Final Fantasy VII (USA).m3u", "Final Fantasy VII (USA) (Disc 1).chd\nFinal Fantasy VII (USA) (Disc 2).chd\n");
        var summary = await _library.RescanAsync("psx", null, Ct);

        Assert.Equal((1, 2), (summary.Added, summary.Removed));
        Assert.Equal(["Final Fantasy VII"], await Titles("psx"));
    }

    [Fact]
    public async Task A_system_can_have_several_folders()
    {
        _dir.File("Drive1/Sonic (USA).md");
        _dir.File("Drive2/Streets of Rage (USA).md");
        _library.Config = LoadConfig($"[systems.megadrive]\nrom_dirs = ['{_dir.Combine("Drive1")}', '{_dir.Combine("Drive2")}']\n");

        await _library.RescanAsync("megadrive", null, Ct);

        Assert.Equal(["Sonic", "Streets of Rage"], await Titles("megadrive"));
        var details = await _library.GetGameAsync((await Game("megadrive", "Streets of Rage")).GameId, Ct);
        Assert.Equal(_dir.Combine("Drive2", "Streets of Rage (USA).md"), details!.RomPath);
    }

    [Fact]
    public async Task A_full_rescan_drops_systems_that_are_now_disabled()
    {
        Rom("snes/A.sfc");
        Rom("nes/B.nes");
        await _library.RescanAsync(null, null, Ct);

        _library.Config = LoadConfig("[systems.nes]\nenabled = false\n");
        await _library.RescanAsync(null, null, Ct);

        using var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.LibraryFileName));
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT group_concat(system_id) FROM (SELECT system_id FROM games ORDER BY system_id)";
        Assert.Equal("snes", command.ExecuteScalar());
    }

    [Fact]
    public async Task Parallel_scans_give_the_same_library_and_diagnostics_in_config_order()
    {
        // Every system gets games and a missing second folder, so each scan reports one warning.
        var systems = new StringBuilder();
        foreach (var (id, extension) in (IEnumerable<(string, string)>)
            [("gb", ".gb"), ("nes", ".nes"), ("snes", ".sfc"), ("n64", ".z64"), ("megadrive", ".md"), ("psx", ".chd"), ("ps2", ".iso"), ("psp", ".cso")])
        {
            for (var i = 0; i < 20; i++)
            {
                _dir.File($"ROMs/{id}/Game {i} (USA){extension}");
            }

            systems.Append(CultureInfo.InvariantCulture, $"[systems.{id}]\nrom_dirs = ['{_dir.Combine("ROMs", id)}', '{_dir.Combine("missing", id)}']\n");
        }

        _library.Config = LoadConfig(systems.ToString());
        _library.ScanParallelism = 1;
        var sequential = await _library.RescanAsync(null, null, Ct);
        var sequentialDump = Dump();

        _library.ScanParallelism = 8;
        var reports = new List<JobProgress>();
        var parallel = await _library.RebuildAsync(new SynchronousProgress(reports), Ct);

        Assert.Equal(sequentialDump, Dump());
        Assert.Equal(sequential.Diagnostics.Select(d => d.Key), parallel.Diagnostics.Select(d => d.Key));
        Assert.Equal(
            ["systems.gb.rom_dirs", "systems.nes.rom_dirs", "systems.snes.rom_dirs", "systems.n64.rom_dirs"],
            parallel.Diagnostics.Take(4).Select(d => d.Key));
        Assert.Equal(160, parallel.Added);
        // 0, then one report per finished system, each count once (every built-in system is enabled).
        Assert.Equal(Enumerable.Range(0, _library.Config.Systems.Count + 1), reports.Where(r => r.Phase == "scan").Select(r => r.Done).Order());
    }

    [Fact]
    public async Task A_cancelled_scan_throws_and_writes_nothing()
    {
        Rom("snes/A.sfc");
        using var cancel = new CancellationTokenSource();
        await cancel.CancelAsync();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => _library.RescanAsync(null, null, cancel.Token));

        Assert.Empty(await Titles("snes"));
    }

    private sealed class SynchronousProgress(List<JobProgress> reports) : IProgress<JobProgress>
    {
        public void Report(JobProgress value)
        {
            lock (reports)
            {
                reports.Add(value);
            }
        }
    }

    // ---- User data in the grid queries ---------------------------------------------------------

    [Fact]
    public async Task Favourites_hidden_games_and_title_overrides_show_in_the_grid()
    {
        Rom("snes/Alpha.sfc");
        Rom("snes/Beta.sfc");
        Rom("snes/Gamma.sfc");
        Rom("nes/Delta.nes");
        await _library.RescanAsync(null, null, Ct);

        await _library.SetFavouriteAsync(new GameKey("snes", "gamma.sfc"), true, Ct);
        await _library.SetFavouriteAsync(new GameKey("nes", "delta.nes"), true, Ct);
        await _library.SetHiddenAsync(new GameKey("snes", "beta.sfc"), true, Ct);
        await _library.SetTitleOverrideAsync(new GameKey("snes", "alpha.sfc"), "Zeta", Ct);

        var games = (await _library.GetGamesAsync("snes", Ct)).Games;
        Assert.Equal(["Gamma", "Zeta"], games.Select(g => g.Title));
        Assert.Equal([true, false], games.Select(g => g.IsFavourite));

        var favourites = await _library.GetFavouritesAsync(Ct);
        Assert.Equal([("nes", "Delta"), ("snes", "Gamma")], favourites.Select(f => (f.SystemId, f.Game.Title)));

        await _library.SetTitleOverrideAsync(new GameKey("snes", "alpha.sfc"), null, Ct);
        await _library.SetHiddenAsync(new GameKey("snes", "beta.sfc"), false, Ct);
        await _library.SetFavouriteAsync(new GameKey("snes", "gamma.sfc"), false, Ct);
        Assert.Equal(["Alpha", "Beta", "Gamma"], await Titles("snes"));
        Assert.Single(await _library.GetFavouritesAsync(Ct));
    }

    [Fact]
    public async Task A_games_chosen_template_comes_with_its_rows_and_details_and_the_chosen_ids_once()
    {
        Rom("snes/Alpha.sfc");
        Rom("snes/Beta.sfc");
        Rom("nes/Gamma.nes");
        await _library.RescanAsync(null, null, Ct);
        var alpha = new GameKey("snes", "alpha.sfc");
        Assert.Empty(await _library.GetChosenGameTemplatesAsync(Ct));

        await _library.SetGameTemplateAsync(alpha, "snes_box_vertical", Ct);
        await _library.SetGameTemplateAsync(new GameKey("nes", "gamma.nes"), " snes_box_vertical ", Ct);
        await _library.SetGameTemplateAsync(new GameKey("snes", "beta.sfc"), "dvd_case", Ct);
        await _library.SetTitleOverrideAsync(alpha, "Alpha Two", Ct);           // the same row, another column
        await _library.SetFavouriteAsync(alpha, true, Ct);
        UserData("INSERT INTO play_stats (system_id, path_key, play_count, last_played_at) VALUES ('snes', 'alpha.sfc', 1, 100)");

        Assert.Equal([("Alpha Two", "snes_box_vertical"), ("Beta", "dvd_case")], (await _library.GetGamesAsync("snes", Ct)).Games.Select(g => (g.Title, g.Template)));
        Assert.Equal("snes_box_vertical", (await _library.GetFavouritesAsync(Ct)).Single().Game.Template);
        Assert.Equal("snes_box_vertical", (await _library.GetRecentlyPlayedAsync(10, Ct)).Single().Game.Template);
        Assert.Equal("snes_box_vertical", (await _library.GetGameAsync(alpha, Ct))!.TemplateOverride);
        Assert.Equal(["dvd_case", "snes_box_vertical"], await _library.GetChosenGameTemplatesAsync(Ct));

        await _library.SetGameTemplateAsync(alpha, null, Ct);
        await _library.SetGameTemplateAsync(new GameKey("snes", "beta.sfc"), "  ", Ct);

        var game = (await _library.GetGameAsync(alpha, Ct))!;
        Assert.Null(game.TemplateOverride);
        Assert.Equal("Alpha Two", game.Title);
        Assert.Equal(["snes_box_vertical"], await _library.GetChosenGameTemplatesAsync(Ct));
    }

    [Fact]
    public async Task Recently_played_lists_newest_first()
    {
        Rom("snes/A.sfc");
        Rom("snes/B.sfc");
        Rom("snes/C.sfc");
        await _library.RescanAsync(null, null, Ct);
        using (var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.UserDataFileName)))
        {
            MigrationRunner.Execute(connection, """
                INSERT INTO play_stats (system_id, path_key, play_count, last_played_at) VALUES
                  ('snes', 'a.sfc', 1, 100), ('snes', 'c.sfc', 3, 300), ('snes', 'gone.sfc', 1, 400), ('snes', 'b.sfc', 0, NULL)
                """);
        }

        var recent = await _library.GetRecentlyPlayedAsync(10, Ct);

        Assert.Equal(["C", "A"], recent.Select(r => r.Game.Title));
        Assert.Single(await _library.GetRecentlyPlayedAsync(1, Ct));
    }

    // ---- Sorting a system's games ([display] games_sort) ----------------------------------------

    private async Task<string[]> Titles(string system, GameSort sort, SortOrder order = SortOrder.Ascending) =>
        (await _library.GetGamesAsync(system, new GamesOrdering(sort, order), Ct)).Games.Select(g => g.Title).ToArray();

    private void UserData(string sql)
    {
        using var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.UserDataFileName));
        MigrationRunner.Execute(connection, sql);
    }

    [Fact]
    public async Task Games_sort_alphabetically_either_way_leaving_hidden_games_out()
    {
        Rom("snes/Alpha.sfc");
        Rom("snes/Beta.sfc");
        Rom("snes/Gamma.sfc");
        await _library.RescanAsync(null, null, Ct);
        await _library.SetHiddenAsync(new GameKey("snes", "beta.sfc"), true, Ct);

        Assert.Equal(["Alpha", "Gamma"], await Titles("snes", GameSort.Alphabetical));
        Assert.Equal(["Gamma", "Alpha"], await Titles("snes", GameSort.Alphabetical, SortOrder.Descending));
        Assert.Equal(await Titles("snes"), await Titles("snes", GameSort.Alphabetical));
        foreach (var sort in Enum.GetValues<GameSort>())
        {
            Assert.Equal(2, (await Titles("snes", sort, SortOrder.Descending)).Length);
        }
    }

    [Fact]
    public async Task Games_sort_by_last_played_with_games_never_played_last_either_way()
    {
        Rom("snes/A.sfc");
        Rom("snes/B.sfc");
        Rom("snes/C.sfc");
        Rom("snes/D.sfc");
        await _library.RescanAsync(null, null, Ct);
        UserData("""
            INSERT INTO play_stats (system_id, path_key, play_count, total_seconds, last_played_at) VALUES
              ('snes', 'a.sfc', 1, 600, 300), ('snes', 'b.sfc', 2, 60, 100), ('snes', 'c.sfc', 1, 0, 200)
            """);

        Assert.Equal(["B", "C", "A", "D"], await Titles("snes", GameSort.LastPlayed));
        Assert.Equal(["A", "C", "B", "D"], await Titles("snes", GameSort.LastPlayed, SortOrder.Descending));
    }

    [Fact]
    public async Task Games_sort_by_play_time_and_a_game_never_played_has_none()
    {
        Rom("snes/A.sfc");
        Rom("snes/B.sfc");
        Rom("snes/C.sfc");
        Rom("snes/D.sfc");
        await _library.RescanAsync(null, null, Ct);
        UserData("""
            INSERT INTO play_stats (system_id, path_key, play_count, total_seconds, last_played_at) VALUES
              ('snes', 'a.sfc', 1, 600, 300), ('snes', 'b.sfc', 2, 60, 100), ('snes', 'c.sfc', 1, 0, 200)
            """);

        // C (a crashed session: a play with no time) and D (never played) tie at none, so they go by title.
        Assert.Equal(["C", "D", "B", "A"], await Titles("snes", GameSort.PlayTime));
        Assert.Equal(["A", "B", "C", "D"], await Titles("snes", GameSort.PlayTime, SortOrder.Descending));
    }

    [Fact]
    public async Task Games_sort_by_release_date_the_users_over_the_scraped_with_undated_games_last()
    {
        Rom("snes/A.sfc");
        Rom("snes/B.sfc");
        Rom("snes/C.sfc");
        Rom("snes/D.sfc");
        await _library.RescanAsync(null, null, Ct);
        using (var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.LibraryFileName)))
        {
            MigrationRunner.Execute(connection, """
                INSERT INTO metadata (game_id, release_date, source)
                SELECT game_id, CASE path_key WHEN 'a.sfc' THEN '1994-11' WHEN 'b.sfc' THEN '1991' ELSE '1993-06-01' END, 'screenscraper'
                FROM games WHERE path_key IN ('a.sfc', 'b.sfc', 'c.sfc')
                """);
        }

        await _library.SetMetadataOverrideAsync(new GameKey("snes", "c.sfc"), new MetadataOverride(null, "1990", null, null, null, null, null), Ct);

        Assert.Equal(["C", "B", "A", "D"], await Titles("snes", GameSort.ReleaseDate));
        Assert.Equal(["A", "B", "C", "D"], await Titles("snes", GameSort.ReleaseDate, SortOrder.Descending));
    }

    [Fact]
    public async Task Games_sort_by_when_their_files_arrived_and_a_file_copied_again_moves()
    {
        var a = Rom("snes/A.sfc");
        var b = Rom("snes/B.sfc");
        var c = Rom("snes/C.sfc");
        File.SetCreationTimeUtc(a, new DateTime(2021, 3, 1, 0, 0, 0, DateTimeKind.Utc));
        File.SetCreationTimeUtc(b, new DateTime(2019, 3, 1, 0, 0, 0, DateTimeKind.Utc));
        File.SetCreationTimeUtc(c, new DateTime(2020, 3, 1, 0, 0, 0, DateTimeKind.Utc));
        await _library.RescanAsync(null, null, Ct);

        Assert.Equal(["B", "C", "A"], await Titles("snes", GameSort.Added));
        Assert.Equal(["A", "C", "B"], await Titles("snes", GameSort.Added, SortOrder.Descending));

        // Same content and time, but a new creation time (deleted and copied in again): a rescan updates it.
        File.SetCreationTimeUtc(b, new DateTime(2025, 3, 1, 0, 0, 0, DateTimeKind.Utc));
        var summary = await _library.RescanAsync(null, null, Ct);
        Assert.Equal((0, 1, 2), (summary.Added, summary.Updated, summary.Unchanged));
        Assert.Equal(["C", "A", "B"], await Titles("snes", GameSort.Added));
    }

    [Fact]
    public async Task User_data_under_an_alias_is_rekeyed_to_the_canonical_id()
    {
        Rom("megadrive/Sonic.md");
        _library.Dispose();
        using (var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.UserDataFileName)))
        {
            MigrationRunner.Execute(connection, "INSERT INTO favourites VALUES ('genesis', 'sonic.md', 1)");
        }

        _library = await Open(LoadConfig());
        await _library.RescanAsync(null, null, Ct);

        Assert.True((await Game("megadrive", "Sonic")).IsFavourite);
    }

    // ---- The user's own art (M5) ---------------------------------------------------------------

    [Fact]
    public async Task User_art_is_indexed_as_covers_with_their_aspect()
    {
        Rom("ps2/Game A (USA).iso");
        Rom("ps2/Sub/Game B.chd");
        Rom("ps2/No Art.iso");
        Art("ps2/covers/Game A (USA).png", TestImages.Png(700, 1000));
        Art("ps2/covers/Sub/Game B.chd.jpg", TestImages.Jpeg(1000, 1000));

        var summary = await _library.RescanAsync("ps2", null, Ct);

        Assert.Empty(summary.Diagnostics);
        var a = await Game("ps2", "Game A");
        Assert.Equal("media/ps2/covers/Game A (USA).png", a.CoverPath);
        Assert.Equal(0.7f, a.CoverAspect, 3);
        var b = await Game("ps2", "Game B");
        Assert.Equal("media/ps2/covers/Sub/Game B.chd.jpg", b.CoverPath);
        Assert.Equal(1f, b.CoverAspect);
        var none = await Game("ps2", "No Art");
        Assert.Equal((null, 0f), (none.CoverPath, none.CoverAspect));
    }

    [Fact]
    public async Task The_media_folder_settings_name_is_indexed_and_stored_paths_dont_name_it()
    {
        Rom("ps2/Game A (USA).iso");
        Art("ps2/covers/Game A (USA).png", TestImages.Png(700, 1000));
        var elsewhere = _dir.File("Launcher media/ps2/screenshots/Game A (USA).png");
        File.WriteAllBytes(elsewhere, TestImages.Png(640, 480));
        await _library.RescanAsync("ps2", null, Ct);
        Assert.Equal(Path.Combine(DataDir, "media"), _library.MediaDir);

        // [paths] media (2026-10-04): the library follows its config, and the rows keep "media/" for wherever it is.
        var config = _library.Config;
        _library.Config = config with { Settings = config.Settings with { MediaDir = _dir.Combine("Launcher media") } };
        await _library.RescanAsync("ps2", null, Ct);

        Assert.Equal(_dir.Combine("Launcher media"), _library.MediaDir);
        var a = await Game("ps2", "Game A");
        Assert.Null(a.CoverPath);
        var rows = await _library.GetGameMediaAsync("ps2", ["cover", "screenshot"], Ct);
        var screenshot = Assert.Single(rows);
        Assert.Equal("media/ps2/screenshots/Game A (USA).png", screenshot.Media.Path);
        Assert.Equal(elsewhere, _library.MediaPath(screenshot.Media.Path));
    }

    [Fact]
    public async Task An_exact_match_beats_a_stem_match_and_a_stem_match_covers_every_format()
    {
        Rom("psx/Crash.cue", "");
        Rom("psx/Crash.chd");
        Rom("psx/Spyro.chd");
        Art("psx/covers/Crash.png", TestImages.Png(10, 10));
        Art("psx/covers/Crash.chd.webp", TestImages.WebPLossy(20, 10));
        Art("psx/covers/spyro.JPG", TestImages.Jpeg(30, 10));

        await _library.RescanAsync("psx", null, Ct);

        var games = (await _library.GetGamesAsync("psx", Ct)).Games;
        Assert.Equal(
            ["media/psx/covers/Crash.chd.webp", "media/psx/covers/Crash.png", "media/psx/covers/spyro.JPG"],
            games.Select(g => g.CoverPath).Order(StringComparer.Ordinal));
    }

    [Fact]
    public async Task Unchanged_art_isnt_read_again_and_changed_or_removed_art_is_picked_up()
    {
        Rom("snes/Game.sfc");
        var art = Art("snes/covers/Game.png", TestImages.Png(700, 1000));
        await _library.RescanAsync("snes", null, Ct);

        // Same size and time: the stored header stands, so the new content isn't read.
        Art("snes/covers/Game.png", TestImages.Png(800, 1000));
        await _library.RescanAsync("snes", null, Ct);
        Assert.Equal(0.7f, (await Game("snes", "Game")).CoverAspect, 3);

        Art("snes/covers/Game.png", TestImages.Png(800, 1000), new DateTime(2024, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        await _library.RescanAsync("snes", null, Ct);
        Assert.Equal(0.8f, (await Game("snes", "Game")).CoverAspect, 3);

        File.Delete(art);
        await _library.RescanAsync("snes", null, Ct);
        Assert.Null((await Game("snes", "Game")).CoverPath);
    }

    [Fact]
    public async Task Art_that_isnt_an_image_is_a_warning_and_other_kinds_are_indexed_too()
    {
        Rom("snes/Game.sfc");
        Art("snes/covers/Game.png", "not an image"u8.ToArray());
        Art("snes/backcovers/Game.png", TestImages.Png(10, 10));
        Art("snes/unknown/Game.png", TestImages.Png(10, 10));

        var summary = await _library.RescanAsync("snes", null, Ct);

        var warning = Assert.Single(summary.Diagnostics);
        Assert.Contains("isn't a PNG, JPEG or WebP", warning.Message, StringComparison.Ordinal);
        Assert.Null((await Game("snes", "Game")).CoverPath);
        using var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.LibraryFileName));
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT kind || ':' || path FROM media";
        Assert.Equal("back:media/snes/backcovers/Game.png", command.ExecuteScalar());
    }

    [Fact]
    public async Task Media_no_game_would_use_isnt_read_so_a_media_folder_shared_with_es_de_costs_only_its_listing()
    {
        // Not images at all: had the scan opened them, each would be a warning.
        Rom("snes/Game.sfc");
        Art("snes/covers/Game.png", TestImages.Png(10, 10));
        Art("snes/covers/Not In The Library.png", "not an image"u8.ToArray());
        Art("snes/screenshots/Sub/Game.png", "not an image"u8.ToArray());
        Art("3do/covers/A System With No Games.png", "not an image"u8.ToArray());

        var summary = await _library.RescanAsync(null, null, Ct);

        Assert.Empty(summary.Diagnostics);
        Assert.Equal("media/snes/covers/Game.png", (await Game("snes", "Game")).CoverPath);
        using var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.LibraryFileName));
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT COUNT(*) FROM media";
        Assert.Equal(1L, command.ExecuteScalar());
    }

    // ---- Media for theme slots and per-game models (M6) --------------------------------------------

    [Fact]
    public async Task Slot_media_come_by_system_or_by_game_for_only_the_kinds_asked()
    {
        Rom("snes/Game A.sfc");
        Rom("snes/Game B.sfc");
        Rom("nes/Other.nes");
        Art("snes/backcovers/Game A.png", TestImages.Png(500, 1000));
        Art("snes/spines/Game A.png", TestImages.Png(50, 1000));
        Art("snes/screenshots/Game B.png", TestImages.Png(640, 480));
        Art("nes/backcovers/Other.png", TestImages.Png(10, 10));
        await _library.RescanAsync(null, null, Ct);

        var rows = await _library.GetGameMediaAsync("snes", ["back", "screenshot"], Ct);

        var a = await Game("snes", "Game A");
        var b = await Game("snes", "Game B");
        Assert.Equal(
            [(a.GameId, "back", "media/snes/backcovers/Game A.png", 0.5f), (b.GameId, "screenshot", "media/snes/screenshots/Game B.png", 640f / 480)],
            rows.Select(r => (r.GameId, r.Kind, r.Media.Path, r.Media.Aspect)).OrderBy(r => r.Kind, StringComparer.Ordinal));
        Assert.All(rows, r => Assert.True(r.Media.SizeBytes > 0 && r.Media.MtimeMs > 0));

        var byGame = await _library.GetGameMediaAsync([a.GameId], ["spine", "back"], Ct);
        Assert.Equal(["back", "spine"], byGame.Select(r => r.Kind).Order(StringComparer.Ordinal));
        Assert.Empty(await _library.GetGameMediaAsync("snes", [], Ct));
    }

    [Fact]
    public async Task Per_game_models_are_indexed_like_art_so_nothing_is_probed_per_item()
    {
        Rom("ps2/Game A (USA).iso");
        Rom("ps2/Sub/Game B.chd");
        Rom("ps2/Game C.iso");
        var modelA = _dir.File("data/media/ps2/models/Game A (USA).glb", "glTF");
        _dir.File("data/media/ps2/models/Sub/Game B.chd.glb", "glTF");
        _dir.File("data/media/ps2/models/Game C.txt", "not a model");

        var summary = await _library.RescanAsync("ps2", null, Ct);

        Assert.Empty(summary.Diagnostics);
        var rows = await _library.GetGameMediaAsync("ps2", [Launcher.Core.Media.MediaKinds.Model], Ct);
        Assert.Equal(
            ["media/ps2/models/Game A (USA).glb", "media/ps2/models/Sub/Game B.chd.glb"],
            rows.Select(r => r.Media.Path).Order(StringComparer.Ordinal));
        Assert.All(rows, r => Assert.Equal(0f, r.Media.Aspect));

        File.Delete(modelA);
        await _library.RescanAsync("ps2", null, Ct);
        Assert.Single(await _library.GetGameMediaAsync("ps2", [Launcher.Core.Media.MediaKinds.Model], Ct));
    }

    [Fact]
    public async Task Videos_are_indexed_with_no_size_and_files_of_another_kinds_format_are_ignored()
    {
        Rom("snes/Game.sfc");
        _dir.File("data/media/snes/videos/Game.sfc.mp4", "an mp4");
        _dir.File("data/media/snes/videos/Game.png", "not a video");
        _dir.File("data/media/snes/covers/Game.glb", "not an image");
        _dir.File("config/media/snes/backcovers/Game.png", "the old place for the user's art");

        var summary = await _library.RescanAsync("snes", null, Ct);

        Assert.Empty(summary.Diagnostics);
        var game = await Game("snes", "Game");
        var rows = await _library.GetGameMediaInfoAsync(game.GameId, Ct);
        var video = Assert.Single(rows);
        Assert.Equal(("video", "media/snes/videos/Game.sfc.mp4", (int?)null, (int?)null), (video.Kind, video.Media.Path, video.Width, video.Height));
        Assert.True(video.Media.SizeBytes > 0);
    }

    [Fact]
    public async Task A_rescan_reports_only_the_games_whose_art_or_model_changed()
    {
        Rom("snes/Game A.sfc");
        Rom("snes/Game B.sfc");
        Art("snes/covers/Game A.png", TestImages.Png(10, 10));
        var changes = new List<IReadOnlyList<GameKey>?>();
        _library.MediaChanged += (_, e) => changes.Add(e.Games);

        await _library.RescanAsync("snes", null, Ct);
        Assert.Equal([new GameKey("snes", "game a.sfc")], Assert.Single(changes)!);

        changes.Clear();
        await _library.RescanAsync("snes", null, Ct);
        Assert.Empty(changes);

        _dir.File("data/media/snes/models/Game B.glb", "glTF");
        await _library.RescanAsync("snes", null, Ct);
        Assert.Equal([new GameKey("snes", "game b.sfc")], Assert.Single(changes)!);
    }

    [Fact]
    public async Task Scraped_metadata_comes_with_the_game_details()
    {
        Rom("snes/Game.sfc");
        await _library.RescanAsync("snes", null, Ct);
        var id = (await Game("snes", "Game")).GameId;
        Assert.Null((await _library.GetGameAsync(id, Ct))!.Metadata);
        using (var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.LibraryFileName)))
        {
            MigrationRunner.Execute(connection, $"""
                INSERT INTO metadata (game_id, description, release_date, developer, genre, players, rating, source)
                VALUES ({id}, 'A game.', '1991-06', 'Someone', 'Platform', '1-2', 0.8, 'screenscraper')
                """);
        }

        var metadata = (await _library.GetGameAsync(id, Ct))!.Metadata;

        Assert.Equal(new GameMetadata("A game.", "1991-06", "Someone", null, "Platform", "1-2", 0.8, "screenscraper"), metadata);
    }

    // ---- Deleting a game (2026-10-03) ----------------------------------------------------------

    [Fact]
    public async Task Deleting_a_game_deletes_its_file_and_takes_it_out_of_the_library()
    {
        var file = Rom("snes/Mega Man X (USA).sfc", "12345");
        Rom("snes/Super Mario World (USA).sfc");
        await _library.RescanAsync("snes", null, Ct);
        var key = new GameKey("snes", "mega man x (usa).sfc");
        await _library.SetFavouriteAsync(key, true, Ct);

        var plan = await _library.PlanDeleteAsync(key, Ct);
        Assert.NotNull(plan);
        Assert.False(plan.IsPlaylist);
        Assert.Equal([("Mega Man X (USA).sfc", file, 5L)], plan.Files.Select(f => (f.RelPath, f.FullPath, f.SizeBytes)));
        var result = await _library.DeleteGameAsync(plan, Ct);

        Assert.Equal((true, 1, 5L), (result.Deleted, result.FilesDeleted, result.BytesFreed));
        Assert.Empty(result.Failed);
        Assert.False(File.Exists(file));
        Assert.Equal(["Super Mario World"], await Titles("snes"));
        Assert.Equal(1, (await _library.GetSystemsAsync(Ct)).Single(s => s.SystemId == "snes").GameCount);

        // The library is as a rescan leaves it, and the user data stays for the file coming back.
        var after = Dump();
        Assert.Equal((0, 0, 0, 1), Changes(await _library.RescanAsync("snes", null, Ct)));
        Assert.Equal(after, Dump());
        Rom("snes/Mega Man X (USA).sfc");
        await _library.RescanAsync("snes", null, Ct);
        Assert.True((await Game("snes", "Mega Man X")).IsFavourite);
    }

    [Fact]
    public async Task A_folder_game_isnt_deleted()
    {
        var inner = Rom("snes/Dump.sfc/data/game.bin", "12345");
        await _library.RescanAsync("snes", null, Ct);
        var key = new GameKey("snes", "dump.sfc");

        var plan = (await _library.PlanDeleteAsync(key, Ct))!;
        Assert.True(plan.IsFolder);
        var result = await _library.DeleteGameAsync(plan, Ct);

        Assert.False(result.Deleted);
        Assert.Equal("Dump.sfc", Assert.Single(result.Failed).RelPath);
        Assert.True(File.Exists(inner));
        Assert.Equal(["Dump"], await Titles("snes"));
    }

    [Fact]
    public async Task Deleting_a_playlist_deletes_every_file_it_lists_and_the_folder_they_leave_empty()
    {
        Rom("psx/Final Fantasy VII.m3u", "#EXTM3U\nFF7/Disc 1.cue\nFF7/Disc 2.cue\nFF7/Disc 3.cue\n");
        Rom("psx/FF7/Disc 1.cue", "FILE \"Disc 1 (Track 1).bin\" BINARY\nFILE \"Disc 1 (Track 2).bin\" BINARY\n");
        Rom("psx/FF7/Disc 1 (Track 1).bin", "track");
        Rom("psx/FF7/Disc 1 (Track 2).bin", "track");
        Rom("psx/FF7/Disc 2.cue", "FILE \"Disc 2.bin\" BINARY\n");
        Rom("psx/FF7/Disc 2.bin", "track");
        Rom("psx/Crash Bandicoot (USA).chd");
        await _library.RescanAsync("psx", null, Ct);
        Assert.Equal(["Crash Bandicoot", "Final Fantasy VII"], await Titles("psx"));

        var plan = (await _library.PlanDeleteAsync(new GameKey("psx", "final fantasy vii.m3u"), Ct))!;
        Assert.True(plan.IsPlaylist);
        Assert.Equal(
            ["Final Fantasy VII.m3u", "FF7/Disc 1.cue", "FF7/Disc 2.cue", "FF7/Disc 1 (Track 1).bin", "FF7/Disc 1 (Track 2).bin", "FF7/Disc 2.bin"],
            plan.Files.Select(f => f.RelPath));
        Assert.Equal(["FF7/Disc 3.cue"], plan.Missing);
        Assert.Empty(plan.Shared);
        var result = await _library.DeleteGameAsync(plan, Ct);

        Assert.Equal((true, 6), (result.Deleted, result.FilesDeleted));
        Assert.False(Directory.Exists(_dir.Combine("ROMs", "psx", "FF7")));
        Assert.True(File.Exists(_dir.Combine("ROMs", "psx", "Crash Bandicoot (USA).chd")));
        Assert.Equal(["Crash Bandicoot"], await Titles("psx"));
        var after = Dump();
        Assert.Equal((0, 0, 0, 1), Changes(await _library.RescanAsync("psx", null, Ct)));
        Assert.Equal(after, Dump());
    }

    [Fact]
    public async Task A_file_another_games_playlist_lists_is_kept()
    {
        Rom("psx/A.m3u", "Shared.cue\nA (Disc 2).chd\n");
        Rom("psx/B.m3u", "Shared.cue\n");
        Rom("psx/Shared.cue", "FILE \"Shared.bin\" BINARY\n");
        Rom("psx/Shared.bin", "track");
        Rom("psx/A (Disc 2).chd");
        await _library.RescanAsync("psx", null, Ct);

        var plan = (await _library.PlanDeleteAsync(new GameKey("psx", "a.m3u"), Ct))!;
        Assert.Equal(["A.m3u", "A (Disc 2).chd"], plan.Files.Select(f => f.RelPath));
        Assert.Equal(["Shared.cue", "Shared.bin"], plan.Shared);
        await _library.DeleteGameAsync(plan, Ct);

        Assert.True(File.Exists(_dir.Combine("ROMs", "psx", "Shared.cue")));
        Assert.True(File.Exists(_dir.Combine("ROMs", "psx", "Shared.bin")));
        Assert.Equal(["B"], await Titles("psx"));
    }

    [Fact]
    public async Task A_read_only_game_is_deleted_too()
    {
        var file = Rom("snes/A.sfc");
        File.SetAttributes(file, FileAttributes.ReadOnly);
        await _library.RescanAsync("snes", null, Ct);

        var result = await _library.DeleteGameAsync((await _library.PlanDeleteAsync(new GameKey("snes", "a.sfc"), Ct))!, Ct);

        Assert.True(result.Deleted);
        Assert.False(File.Exists(file));
    }

    [Fact]
    public async Task When_the_games_own_file_cant_be_deleted_nothing_is()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "An open file can be deleted on Linux.");
        var playlist = Rom("psx/A.m3u", "A (Disc 1).chd\n");
        var disc = Rom("psx/A (Disc 1).chd");
        await _library.RescanAsync("psx", null, Ct);
        var plan = (await _library.PlanDeleteAsync(new GameKey("psx", "a.m3u"), Ct))!;

        GameDeleteResult result;
        using (File.Open(playlist, FileMode.Open, FileAccess.Read, FileShare.None))
        {
            result = await _library.DeleteGameAsync(plan, Ct);
        }

        Assert.False(result.Deleted);
        Assert.Equal("A.m3u", Assert.Single(result.Failed).RelPath);
        Assert.True(File.Exists(playlist));
        Assert.True(File.Exists(disc));
        Assert.Equal(["A"], await Titles("psx"));
    }

    [Fact]
    public async Task A_game_no_longer_in_the_library_has_no_plan() =>
        Assert.Null(await _library.PlanDeleteAsync(new GameKey("snes", "gone.sfc"), Ct));

    private static (int, int, int, int) Changes(ScanSummary summary) => (summary.Added, summary.Updated, summary.Removed, summary.Unchanged);

    // ---- Rebuild -------------------------------------------------------------------------------

    [Fact]
    public async Task A_rebuild_from_disk_equals_the_incrementally_built_library()
    {
        // Build the library up through several incremental scans with every kind of change...
        Rom("snes/Super Mario World (USA).sfc");
        Rom("snes/zelda.sfc");
        Rom("psx/FF7 (Disc 1).chd");
        Rom("psx/FF7 (Disc 2).chd");
        Rom("psx/Crash (USA).cue", "FILE \"Crash (USA).bin\" BINARY\n");
        Rom("megadrive/Sonic (USA).md");
        Art("megadrive/covers/Sonic (USA).png", TestImages.Png(640, 896));
        Art("psx/covers/FF7 (Disc 1).jpg", TestImages.Jpeg(500, 500));
        await _library.RescanAsync(null, null, Ct);

        Rom("psx/FF7.m3u", "FF7 (Disc 1).chd\nFF7 (Disc 2).chd\n");
        Art("psx/covers/FF7.png", TestImages.Png(500, 500));
        Art("snes/spines/zelda.png", TestImages.Png(30, 500));
        Rom("megadrive/Sonic (USA).md", "changed", new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        File.Move(_dir.Combine("ROMs", "snes", "zelda.sfc"), _dir.Combine("ROMs", "snes", "Zelda.sfc"));
        Rom("nes/Metroid (USA).nes");
        await _library.RescanAsync(null, null, Ct);
        File.Delete(_dir.Combine("ROMs", "nes", "Metroid (USA).nes"));
        await _library.RescanAsync("nes", null, Ct);
        var incremental = Dump();
        await _library.SetFavouriteAsync(new GameKey("snes", "zelda.sfc"), true, Ct);

        // ...then throw it away and rebuild it offline from disk.
        var summary = await _library.RebuildAsync(null, Ct);

        Assert.Equal(incremental, Dump());
        Assert.Equal(summary.Added, (await _library.GetSystemsAsync(Ct)).Sum(s => s.GameCount));
        Assert.True((await Game("snes", "Zelda")).IsFavourite);
        Assert.False(File.Exists(Path.Combine(DataDir, LibraryService.LibraryFileName + ".rebuild")));
    }

    [Fact]
    public async Task A_recreated_library_reports_it()
    {
        _library.Dispose();
        var path = Path.Combine(DataDir, LibraryService.LibraryFileName);
        SqliteConnection.ClearAllPools();
        Sqlite.DeleteFiles(path);
        File.WriteAllText(path, "garbage garbage garbage garbage garbage garbage garbage garbage garbage garbage");

        _library = await Open(LoadConfig());

        Assert.Equal(LibraryOpenOutcome.Recreated, _library.OpenOutcome);
        Assert.NotNull(_library.RecreatedBecause);
    }

    /// <summary>The library's contents, without ids or timestamps.</summary>
    private string Dump()
    {
        using var connection = Sqlite.Open(Path.Combine(DataDir, LibraryService.LibraryFileName));
        var dump = new StringBuilder();
        foreach (var sql in (ReadOnlySpan<string>)
        [
            "SELECT system_id, game_count, scanned_at IS NOT NULL FROM systems ORDER BY system_id",
            "SELECT system_id, position, path FROM rom_dirs ORDER BY system_id, position",
            """
            SELECT g.system_id, d.path, g.rel_path, g.path_key, g.size_bytes, g.mtime_ms, g.crc32, g.md5, g.sha1,
                   g.title, g.sort_title, g.region, g.languages, g.revision, g.disc, g.tags
            FROM games g JOIN rom_dirs d ON d.dir_id = g.dir_id ORDER BY g.system_id, g.path_key
            """,
            "SELECT system_id, path_key, size_bytes, mtime_ms, refs FROM playlists ORDER BY system_id, path_key",
            """
            SELECT g.system_id, g.path_key, m.kind, m.path, m.width, m.height, m.size_bytes, m.mtime_ms
            FROM media m JOIN games g ON g.game_id = m.game_id ORDER BY g.system_id, g.path_key, m.kind
            """,
        ])
        {
            using var command = connection.CreateCommand();
            command.CommandText = sql;
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                for (var i = 0; i < reader.FieldCount; i++)
                {
                    dump.Append(reader.IsDBNull(i) ? "NULL" : Convert.ToString(reader.GetValue(i), CultureInfo.InvariantCulture)).Append('|');
                }

                dump.Append('\n');
            }

            dump.Append("--\n");
        }

        return dump.ToString();
    }
}
