using Launcher.Core.Config;
using Launcher.Core.Scanning;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Scanning;

public sealed class RomScannerTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private SystemConfig System(string[] extensions, string[]? dirs = null, bool recursive = true, string[]? exclude = null) => new(
        "psx", "PlayStation", null, null, [], extensions, "emu", [], "jewel_case", null,
        dirs ?? [_dir.Combine("psx")], RomDirSource.Configured, recursive, exclude ?? []);

    private static string[] Games(SystemScan scan) => scan.Games.Select(g => g.RelPath).ToArray();

    [Fact]
    public void Finds_files_by_extension_ignoring_case_and_recursing()
    {
        _dir.File("psx/a.chd");
        _dir.File("psx/B.CHD");
        _dir.File("psx/sub/c.pbp");
        _dir.File("psx/readme.txt");

        var scan = new RomScanner().Scan(System([".chd", ".pbp"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["B.CHD", "a.chd", "sub/c.pbp"], Games(scan));
        Assert.Equal("b.chd", scan.Games[0].PathKey);
        Assert.Empty(scan.Diagnostics);
    }

    [Fact]
    public void Recursion_can_be_turned_off()
    {
        _dir.File("psx/a.chd");
        _dir.File("psx/sub/b.chd");

        var scan = new RomScanner().Scan(System([".chd"], recursive: false), null, TestContext.Current.CancellationToken);

        Assert.Equal(["a.chd"], Games(scan));
    }

    [Fact]
    public void Excluded_files_and_folders_are_skipped()
    {
        _dir.File("psx/a.chd");
        _dir.File("psx/bios/scph1001.chd");
        _dir.File("psx/deep/bios/other.chd");
        _dir.File("psx/demos/x (Demo).chd");
        _dir.File("psx/keep/y.chd");

        var scan = new RomScanner().Scan(System([".chd"], exclude: ["bios", "*(Demo)*"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["a.chd", "keep/y.chd"], Games(scan));
    }

    [Fact]
    public void The_default_exclusions_skip_media_folders_and_gamelists_at_any_depth()
    {
        _dir.File("psx/Game.chd");
        _dir.File("psx/images/Game-image.chd");
        _dir.File("psx/Videos/Game.chd");
        _dir.File("psx/manuals/Game.xml");
        _dir.File("psx/Multi Disc/manuals/Game.chd");
        _dir.File("psx/Multi Disc/Game (Disc 1).chd");
        _dir.File("psx/gamelist.xml");
        _dir.File("psx/other.xml");
        _dir.File("psx/images.chd");

        var scan = new RomScanner().Scan(
            System([".chd", ".xml"], exclude: ["images", "manuals", "videos", "gamelist.xml"]), null, TestContext.Current.CancellationToken);

        // "images" is a folder name here; the file images.chd has a different name, so it's kept.
        Assert.Equal(["Game.chd", "Multi Disc/Game (Disc 1).chd", "images.chd", "other.xml"], Games(scan));
    }

    [Fact]
    public void An_m3u_represents_its_discs_and_hides_them()
    {
        _dir.File("psx/Final Fantasy VII (USA).m3u", "#EXTM3U\r\n.discs/FF7 (Disc 1).chd\r\n.discs/FF7 (Disc 2).chd\n\n.discs\\FF7 (Disc 3).chd\n");
        _dir.File("psx/.discs/FF7 (Disc 1).chd");
        _dir.File("psx/.discs/FF7 (Disc 2).chd");
        _dir.File("psx/.discs/FF7 (Disc 3).chd");
        _dir.File("psx/Other (Disc 1).chd");

        var scan = new RomScanner().Scan(System([".m3u", ".chd"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["Final Fantasy VII (USA).m3u", "Other (Disc 1).chd"], Games(scan));
        var playlist = Assert.Single(scan.Playlists);
        Assert.Equal([".discs/ff7 (disc 1).chd", ".discs/ff7 (disc 2).chd", ".discs/ff7 (disc 3).chd"], playlist.Refs);
    }

    [Fact]
    public void A_cue_hides_its_bin_tracks()
    {
        _dir.File("psx/Game (USA).cue", """
            FILE "Game (USA) (Track 1).bin" BINARY
              TRACK 01 MODE2/2352
                INDEX 01 00:00:00
            FILE "Game (USA) (Track 2).bin" BINARY
              TRACK 02 AUDIO
                INDEX 01 00:02:00
            """);
        _dir.File("psx/Game (USA) (Track 1).bin");
        _dir.File("psx/Game (USA) (Track 2).bin");
        _dir.File("psx/Loose.bin");

        var scan = new RomScanner().Scan(System([".cue", ".bin"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["Game (USA).cue", "Loose.bin"], Games(scan));
    }

    [Fact]
    public void A_gdi_hides_its_tracks_including_quoted_names()
    {
        _dir.File("psx/Crazy Taxi/Crazy Taxi.gdi", """
            3
            1 0 4 2352 track01.bin 0
            2 756 0 2352 "track 02.raw" 0
            3 45000 4 2352 track03.bin 0
            """);
        _dir.File("psx/Crazy Taxi/track01.bin");
        _dir.File("psx/Crazy Taxi/track 02.raw");
        _dir.File("psx/Crazy Taxi/track03.bin");

        var scan = new RomScanner().Scan(System([".gdi", ".bin", ".raw"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["Crazy Taxi/Crazy Taxi.gdi"], Games(scan));
    }

    [Fact]
    public void An_m3u_of_cues_hides_the_cues_and_their_tracks()
    {
        _dir.File("psx/MGS.m3u", "MGS (Disc 1).cue\nMGS (Disc 2).cue\n");
        _dir.File("psx/MGS (Disc 1).cue", "FILE \"MGS (Disc 1).bin\" BINARY\n");
        _dir.File("psx/MGS (Disc 2).cue", "FILE \"MGS (Disc 2).bin\" BINARY\n");
        _dir.File("psx/MGS (Disc 1).bin");
        _dir.File("psx/MGS (Disc 2).bin");

        var scan = new RomScanner().Scan(System([".m3u", ".cue", ".bin"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["MGS.m3u"], Games(scan));
        Assert.Equal(3, scan.Playlists.Count);
    }

    [Fact]
    public void References_match_ignoring_case_and_cannot_escape_the_rom_folder()
    {
        _dir.File("psx/sub/Game.cue", "FILE \"GAME.BIN\" BINARY\nFILE \"../../outside.bin\" BINARY\nFILE \"C:/abs.bin\" BINARY\n");
        _dir.File("psx/sub/game.bin");

        var scan = new RomScanner().Scan(System([".cue", ".bin"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["sub/Game.cue"], Games(scan));
        Assert.Equal(["sub/game.bin"], Assert.Single(scan.Playlists).Refs);
    }

    [Fact]
    public void Unchanged_playlists_come_from_the_cache_and_changed_ones_are_read_again()
    {
        _dir.File("psx/a.m3u", "a1.chd\n");
        _dir.File("psx/b.m3u", "b1.chd\n");
        _dir.File("psx/a1.chd");
        _dir.File("psx/b1.chd");
        var scanner = new RomScanner();
        var first = scanner.Scan(System([".m3u", ".chd"]), null, TestContext.Current.CancellationToken);
        Assert.Equal(2, first.PlaylistsRead);

        _dir.File("psx/b.m3u", "b1.chd\nb2.chd\n", new DateTime(2021, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        _dir.File("psx/b2.chd");
        var cache = first.Playlists.ToDictionary(p => p.PathKey);
        var second = scanner.Scan(System([".m3u", ".chd"]), cache, TestContext.Current.CancellationToken);

        Assert.Equal(1, second.PlaylistsRead);
        Assert.Equal(["a.m3u", "b.m3u"], Games(second));
    }

    [Fact]
    public void With_several_folders_the_first_folder_wins_a_path_collision()
    {
        _dir.File("one/Game.chd", "first");
        _dir.File("two/GAME.chd", "second");
        _dir.File("two/Other.chd");

        var scan = new RomScanner().Scan(System([".chd"], dirs: [_dir.Combine("one"), _dir.Combine("two")]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["Game.chd", "Other.chd"], Games(scan));
        Assert.Equal([0, 1], scan.Games.Select(g => g.DirIndex));
        var warning = Assert.Single(scan.Diagnostics);
        Assert.Contains("same path, ignoring case", warning.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_missing_configured_folder_is_a_warning()
    {
        var scan = new RomScanner().Scan(System([".chd"], dirs: [_dir.Combine("nope")]), null, TestContext.Current.CancellationToken);

        Assert.Empty(scan.Games);
        Assert.Equal(Severity.Warning, Assert.Single(scan.Diagnostics).Severity);
    }

    [Fact]
    public void The_default_folder_falls_back_to_the_first_alias_that_exists()
    {
        _dir.File("ROMs/genesis/Sonic.md");
        var system = new SystemConfig(
            "megadrive", "Mega Drive", null, null, ["genesis"], [".md"], "emu", [], "clamshell", null,
            [_dir.Combine("ROMs", "megadrive"), _dir.Combine("ROMs", "genesis")], RomDirSource.Default, true, []);

        var scan = new RomScanner().Scan(system, null, TestContext.Current.CancellationToken);

        Assert.Equal([_dir.Combine("ROMs", "genesis")], scan.RomDirs);
        Assert.Equal(["Sonic.md"], Games(scan));
        Assert.Empty(scan.Diagnostics);
    }

    [Fact]
    public void A_folder_with_an_extension_is_a_game_and_isnt_entered()
    {
        _dir.File("psx/Demon's Souls.ps3/PS3_GAME/USRDIR/EBOOT.BIN");
        _dir.File("psx/Demon's Souls.ps3/PS3_GAME/PARAM.SFO");
        _dir.File("psx/Bloodborne.ps4/eboot.bin");
        _dir.File("psx/Bloodborne.ps4/sce_sys/param.bin");
        _dir.File("psx/Loose/eboot.bin");
        _dir.File("psx/Loose/Nested.ps4/eboot.bin");

        var scan = new RomScanner().Scan(System([".bin", ".ps3", ".ps4"]), null, TestContext.Current.CancellationToken);

        // A folder without an extension is still searched; a folder game's own files never are.
        Assert.Equal(["Bloodborne.ps4", "Demon's Souls.ps3", "Loose/Nested.ps4", "Loose/eboot.bin"], Games(scan));
        Assert.Equal(4, scan.FilesSeen);
        Assert.All(scan.Games.Where(g => g.RelPath.EndsWith(".ps3", StringComparison.Ordinal) || g.RelPath.EndsWith(".ps4", StringComparison.Ordinal)), g =>
        {
            Assert.True(g.IsFolder);
            Assert.Equal(0, g.SizeBytes);
        });
        Assert.False(scan.Games.Single(g => g.RelPath == "Loose/eboot.bin").IsFolder);
    }

    [Fact]
    public void Folder_games_are_found_without_recursion_and_can_be_excluded()
    {
        _dir.File("psx/Game.ps3/EBOOT.BIN");
        _dir.File("psx/Other.ps3/EBOOT.BIN");
        _dir.File("psx/sub/Deep.ps3/EBOOT.BIN");

        var scan = new RomScanner().Scan(System([".ps3"], recursive: false, exclude: ["Other.ps3"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["Game.ps3"], Games(scan));
    }

    [Fact]
    public void A_folder_named_as_a_playlist_isnt_read_as_one()
    {
        _dir.File("psx/Final Fantasy VII.m3u/Final Fantasy VII.m3u", "Disc 1.chd\n");
        _dir.File("psx/Final Fantasy VII.m3u/Disc 1.chd");

        var scan = new RomScanner().Scan(System([".m3u", ".chd"]), null, TestContext.Current.CancellationToken);

        Assert.Equal(["Final Fantasy VII.m3u"], Games(scan));
        Assert.True(scan.Games[0].IsFolder);
        Assert.Empty(scan.Playlists);
        Assert.Empty(scan.Diagnostics);
    }

    [Fact]
    public void A_folder_games_launch_target_is_its_file_of_the_same_name_or_the_folder()
    {
        _dir.File("psx/Jet Grind Radio.cue/Jet Grind Radio.cue");
        _dir.File("psx/Game.ps3/PS3_GAME/USRDIR/EBOOT.BIN");
        var file = _dir.File("psx/Plain.chd");

        var withFile = _dir.Combine("psx", "Jet Grind Radio.cue");
        Assert.Equal(Path.Combine(withFile, "Jet Grind Radio.cue"), FolderGame.LaunchTarget(withFile));
        Assert.Equal(_dir.Combine("psx", "Game.ps3"), FolderGame.LaunchTarget(_dir.Combine("psx", "Game.ps3")));
        Assert.Equal(file, FolderGame.LaunchTarget(file));
        Assert.True(FolderGame.IsFolder(withFile));
        Assert.False(FolderGame.IsFolder(file));
    }

    [Fact]
    public void Rel_paths_are_NFC()
    {
        // "é" as e + combining acute (NFD), as macOS and some tools write it.
        _dir.File("psx/Pok\u0065\u0301mon.chd");

        var scan = new RomScanner().Scan(System([".chd"]), null, TestContext.Current.CancellationToken);

        Assert.Equal("Pok\u00e9mon.chd", Assert.Single(scan.Games).RelPath);
    }
}
