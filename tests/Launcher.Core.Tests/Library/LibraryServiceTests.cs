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

    private Task<LibraryService> Open(AppConfig config) => LibraryService.OpenAsync(config, DataDir, _clock, Ct);

    private string Rom(string relPath, string content = "rom", DateTime? modified = null) => _dir.File("ROMs/" + relPath, content, modified);

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
        Assert.Equal(14, systems.Count);
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
        // 0, then one report per finished system, each count once (all 14 built-in systems are enabled).
        Assert.Equal(Enumerable.Range(0, 15), reports.Where(r => r.Phase == "scan").Select(r => r.Done).Order());
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
        await _library.RescanAsync(null, null, Ct);

        Rom("psx/FF7.m3u", "FF7 (Disc 1).chd\nFF7 (Disc 2).chd\n");
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
