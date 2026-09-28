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
    public void Rel_paths_are_NFC()
    {
        // "é" as e + combining acute (NFD), as macOS and some tools write it.
        _dir.File("psx/Pok\u0065\u0301mon.chd");

        var scan = new RomScanner().Scan(System([".chd"]), null, TestContext.Current.CancellationToken);

        Assert.Equal("Pok\u00e9mon.chd", Assert.Single(scan.Games).RelPath);
    }
}
