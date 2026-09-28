using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;

// synthetic-library --out=<absolute folder> --covers=<absolute M1 spike library> [--games=10000] [--no-art-every=9]
//
// Writes a portable user folder for `--user-dir`: settings, systems and emulators config, 20 systems (the 14 built-in
// ones plus 6 more), PlayStation 2 with --games games and the others with 30 to 400 each, and empty ROM files with
// generated No-Intro-style names. Every game but one in --no-art-every has a cover in ConfigDir/media, hardlinked
// from the spike library's JPEGs, and its baked BC7 derivative in cache/textures, hardlinked from the spike's DDS
// files, so the library costs almost no disk. Then it scans the library, so the app boots warm.
//
// The folder is deleted and recreated, but only if it's empty or was made by this tool.
var options = Options.Parse(args);
if (options is null)
{
    Console.Error.WriteLine("usage: synthetic-library --out=<absolute folder> --covers=<absolute spike library> [--games=10000] [--no-art-every=9]");
    return 2;
}

const string Marker = "synthetic-library.txt";
var root = options.Out;
if (Directory.Exists(root) && Directory.EnumerateFileSystemEntries(root).Any() && !File.Exists(Path.Combine(root, Marker)))
{
    Console.Error.WriteLine($"{root} isn't empty and wasn't made by this tool, so it's left alone.");
    return 1;
}

var stopwatch = Stopwatch.StartNew();
if (Directory.Exists(root))
{
    Directory.Delete(root, recursive: true);
}

Directory.CreateDirectory(root);
File.WriteAllText(Path.Combine(root, Marker), "Made by tools/synthetic-library. Safe to delete.\n");
var romRoot = Path.Combine(root, "ROMs");
var cacheDir = Path.Combine(root, "cache", TextureDerivatives.FolderName);
Directory.CreateDirectory(cacheDir);

File.WriteAllText(Path.Combine(root, ConfigSources.SettingsFileName), $"""
    [paths]
    rom_root = '{romRoot}'

    [display]
    fullscreen = false
    """);

var extra = new (string Id, string Name, string Model)[]
{
    ("gamegear", "Game Gear", "cartridge_box"),
    ("segacd", "Mega-CD", "jewel_case"),
    ("pcengine", "PC Engine", "cartridge_box"),
    ("neogeo", "Neo Geo", "clamshell"),
    ("wonderswan", "WonderSwan", "cartridge_box"),
    ("psvita", "PlayStation Vita", "umd_case"),
};
var systemsToml = new StringBuilder();
foreach (var (id, name, model) in extra)
{
    systemsToml.Append(CultureInfo.InvariantCulture, $"""
        [systems.{id}]
        name = "{name}"
        extensions = [".rom"]
        emulator = "synthetic"
        game_model = "{model}"


        """);
}

File.WriteAllText(Path.Combine(root, ConfigSources.SystemsFileName), systemsToml.ToString());
File.WriteAllText(Path.Combine(root, ConfigSources.EmulatorsFileName), """
    [emulators.synthetic]
    name = "Synthetic (not installed)"
    executable = "C:/Synthetic/emulator.exe"
    args = ["{rom}"]
    """);

var loaded = new ConfigLoader().Load(ConfigSources.FromDirectory(root, root) with { FileExists = null });
if (loaded.HasErrors)
{
    foreach (var diagnostic in loaded.Diagnostics)
    {
        Console.Error.WriteLine(diagnostic);
    }

    return 1;
}

var random = new Random(20260928);
var spikeCover = 0;
var covers = 0;
var games = 0;
foreach (var system in loaded.Config.Systems)
{
    var count = system.Id == "ps2" ? options.Games : random.Next(30, 401);
    var extension = system.Extensions.FirstOrDefault(e => e is not ".zip" and not ".7z" and not ".m3u" and not ".cue") ?? system.Extensions[0];
    var folder = Path.Combine(romRoot, system.Id);
    Directory.CreateDirectory(folder);
    var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    for (var i = 0; i < count; i++)
    {
        string stem;
        do
        {
            stem = Titles.Make(random);
        }
        while (!names.Add(stem));

        File.WriteAllBytes(Path.Combine(folder, stem + extension), []);
        games++;
        if (options.NoArtEvery > 0 && games % options.NoArtEvery == 0)
        {
            continue;
        }

        // The spike's cover N, as the game's user art, and its baked derivative under the key the app looks up.
        var n = spikeCover++ % 10_000;
        var sourceJpeg = Path.Combine(options.Covers, "jpg", n.ToString("D5", CultureInfo.InvariantCulture) + ".jpg");
        var sourceDds = Path.Combine(options.Covers, "dds-bc7", n.ToString("D5", CultureInfo.InvariantCulture) + ".dds");
        var relative = $"{UserMedia.FolderName}/{system.Id}/{MediaKinds.Cover}/{stem}.jpg";
        var art = Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar));
        Directory.CreateDirectory(Path.GetDirectoryName(art)!);
        HardLink(art, sourceJpeg);
        var info = new FileInfo(art);
        var key = TextureDerivatives.FileName(MediaRoot.Config, relative, info.Length, new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds());
        var derivative = Path.Combine(cacheDir, key);
        if (!File.Exists(derivative))
        {
            HardLink(derivative, sourceDds);
        }

        covers++;
    }
}

Console.WriteLine($"Wrote {loaded.Config.Systems.Count} systems, {games:N0} games and {covers:N0} covers in {stopwatch.Elapsed.TotalSeconds:0.0} s.");

stopwatch.Restart();
using (var library = await LibraryService.OpenAsync(loaded.Config, root, null, default))
{
    library.ConfigDir = root;
    var summary = await library.RescanAsync(null, null, default);
    Console.WriteLine($"Scanned {summary.Added:N0} games in {stopwatch.Elapsed.TotalSeconds:0.0} s; {summary.Diagnostics.Count} diagnostics.");
    foreach (var diagnostic in summary.Diagnostics.Take(5))
    {
        Console.WriteLine(diagnostic);
    }
}

Console.WriteLine($"Run the app with ++ --user-dir={root}");
return 0;

static void HardLink(string link, string target)
{
    if (!File.Exists(target))
    {
        throw new FileNotFoundException($"The spike library has no {target}. Generate it first (docs/SPIKE_RESULTS.md, Reproducing).", target);
    }

    if (!NativeMethods.CreateHardLinkW(link, target, 0))
    {
        throw new IOException($"Couldn't hardlink {link} to {target}: Win32 error {Marshal.GetLastWin32Error()}.");
    }
}

internal sealed record Options(string Out, string Covers, int Games, int NoArtEvery)
{
    public static Options? Parse(string[] args)
    {
        string? output = null;
        string? covers = null;
        var games = 10_000;
        var noArtEvery = 9;
        foreach (var arg in args)
        {
            var (name, value) = arg.IndexOf('=') is var i and > 0 ? (arg[..i], arg[(i + 1)..]) : (arg, "");
            switch (name)
            {
                case "--out" when Path.IsPathFullyQualified(value):
                    output = Path.GetFullPath(value);
                    break;
                case "--covers" when Path.IsPathFullyQualified(value):
                    covers = Path.GetFullPath(value);
                    break;
                case "--games" when int.TryParse(value, CultureInfo.InvariantCulture, out var n) && n > 0:
                    games = n;
                    break;
                case "--no-art-every" when int.TryParse(value, CultureInfo.InvariantCulture, out var n) && n >= 0:
                    noArtEvery = n;
                    break;
                default:
                    return null;
            }
        }

        return output is null || covers is null ? null : new Options(output, covers, games, noArtEvery);
    }
}

/// <summary>No-Intro-style names from word lists: "Crimson Odyssey II (Europe) (En,Fr,De)".</summary>
internal static class Titles
{
    private static readonly string[] First =
    [
        "Crimson", "Silent", "Eternal", "Burning", "Shadow", "Iron", "Neon", "Lost", "Frozen", "Golden", "Hyper", "Wild",
        "Final", "Dark", "Sky", "Star", "Thunder", "Ghost", "Ancient", "Rapid", "Super", "Mystic", "Solar", "Rogue",
        "Velvet", "Arcane", "Omega", "Turbo", "Hidden", "Broken", "Savage", "Cosmic", "Midnight", "Scarlet", "Echo", "Paper",
    ];

    private static readonly string[] Second =
    [
        "Odyssey", "Legends", "Racer", "Knights", "Quest", "Frontier", "Saga", "Warriors", "Horizon", "Chronicles", "Fighter",
        "Kingdom", "Drift", "Hunter", "Tactics", "Rally", "Protocol", "Island", "Pilot", "Arena", "Empire", "Heroes", "Circuit",
        "Dungeon", "Galaxy", "Rhapsody", "Division", "Voyage", "Squadron", "Labyrinth", "Carnival", "Paradox",
    ];

    private static readonly string[] Suffix = ["", "", "", "", " II", " III", " 2", " 3", " Zero", " Deluxe", " Advance", " - Director's Cut", " - Reborn", " - The Lost Chapter"];

    private static readonly string[] Regions = ["(Europe)", "(USA)", "(Japan)", "(USA, Europe)", "(Europe) (En,Fr,De)", "(Europe) (En,Fr,De,Es,It)", "(World)", "(UK)"];

    public static string Make(Random random)
    {
        var article = random.Next(10) == 0 ? "The " : string.Empty;
        var revision = random.Next(12) == 0 ? " (Rev 1)" : string.Empty;
        return $"{article}{First[random.Next(First.Length)]} {Second[random.Next(Second.Length)]}{Suffix[random.Next(Suffix.Length)]} {Regions[random.Next(Regions.Length)]}{revision}";
    }
}

internal static partial class NativeMethods
{
    [LibraryImport("kernel32.dll", EntryPoint = "CreateHardLinkW", StringMarshalling = StringMarshalling.Utf16, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static partial bool CreateHardLinkW(string fileName, string existingFileName, nint securityAttributes);
}
