using System.Globalization;

namespace Launcher.Core.Tests.Benchmarks;

/// <summary>
/// Writes a synthetic ROM tree: exactly <c>fileCount</c> files across 12 systems, named like No-Intro and
/// Redump sets, with the multi-file layouts the scanner groups (.m3u discs, .cue with .bin tracks, .gdi
/// with tracks) and some non-ROM files the extension filter drops. Files are empty: the scanner reads
/// names, sizes and times, and only opens playlists.
/// </summary>
public static class FakeRomTree
{
    public static readonly string[] Systems =
        ["gb", "gbc", "gba", "nes", "snes", "n64", "mastersystem", "megadrive", "saturn", "dreamcast", "psx", "ps2"];

    private static readonly string[] Regions = ["USA", "Europe", "Japan", "USA, Europe", "World"];

    private static readonly Dictionary<string, string> SingleFileExtension = new(StringComparer.Ordinal)
    {
        ["gb"] = ".gb", ["gbc"] = ".gbc", ["gba"] = ".gba", ["nes"] = ".nes", ["snes"] = ".sfc",
        ["n64"] = ".z64", ["mastersystem"] = ".sms", ["megadrive"] = ".md", ["ps2"] = ".chd",
        ["saturn"] = ".chd", ["dreamcast"] = ".chd", ["psx"] = ".chd",
    };

    /// <summary>Writes the tree under <paramref name="romRoot"/>. Returns the number of games the scanner should find.</summary>
    public static int Write(string romRoot, int fileCount)
    {
        var written = 0;
        var games = 0;
        var index = 0;
        var mtime = new DateTime(2024, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        while (written < fileCount)
        {
            var system = Systems[index % Systems.Length];
            var dir = Path.Combine(romRoot, system, index % 7 == 0 ? "Sub Folder" : string.Empty);
            var name = string.Create(CultureInfo.InvariantCulture,
                $"Game {index:D5} - Subtitle ({Regions[index % Regions.Length]}){(index % 11 == 0 ? " (Rev 1)" : string.Empty)}");
            index++;
            var remaining = fileCount - written;
            var files = new List<(string Path, string Content)>();

            if (remaining >= 4 && system == "dreamcast")
            {
                files.Add((Path.Combine(dir, name, name + ".gdi"),
                    $"3\n1 0 4 2352 \"{name} (Track 1).bin\" 0\n2 756 0 2352 \"{name} (Track 2).raw\" 0\n3 45000 4 2352 \"{name} (Track 3).bin\" 0\n"));
                files.Add((Path.Combine(dir, name, name + " (Track 1).bin"), string.Empty));
                files.Add((Path.Combine(dir, name, name + " (Track 2).raw"), string.Empty));
                files.Add((Path.Combine(dir, name, name + " (Track 3).bin"), string.Empty));
            }
            else if (remaining >= 3 && system == "psx" && index % 5 == 0)
            {
                files.Add((Path.Combine(dir, name + ".m3u"), $"{name} (Disc 1).chd\n{name} (Disc 2).chd\n"));
                files.Add((Path.Combine(dir, name + " (Disc 1).chd"), string.Empty));
                files.Add((Path.Combine(dir, name + " (Disc 2).chd"), string.Empty));
            }
            else if (remaining >= 3 && system is "psx" or "saturn")
            {
                files.Add((Path.Combine(dir, name + ".cue"),
                    $"FILE \"{name} (Track 1).bin\" BINARY\n  TRACK 01 MODE2/2352\nFILE \"{name} (Track 2).bin\" BINARY\n  TRACK 02 AUDIO\n"));
                files.Add((Path.Combine(dir, name + " (Track 1).bin"), string.Empty));
                files.Add((Path.Combine(dir, name + " (Track 2).bin"), string.Empty));
            }
            else if (index % 50 == 0)
            {
                // Not a ROM: dropped by the extension filter.
                files.Add((Path.Combine(dir, name + ".txt"), "notes"));
                games--;
            }
            else
            {
                files.Add((Path.Combine(dir, name + SingleFileExtension[system]), string.Empty));
            }

            foreach (var (path, content) in files)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path)!);
                File.WriteAllText(path, content);
                File.SetLastWriteTimeUtc(path, mtime);
            }

            written += files.Count;
            games++;
        }

        return games;
    }
}
