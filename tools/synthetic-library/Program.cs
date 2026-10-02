using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Runtime.InteropServices;
using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Models;

// synthetic-library --out=<absolute folder> --covers=<absolute M1 spike library> [--games=10000] [--others=<n>]
//                   [--no-art-every=9] [--slots=back,spine,...] [--models=<n>]
//
// Writes a portable user folder for `--user-dir`: settings, systems and emulators config, 20 systems (the 14 built-in
// ones plus 6 more), PlayStation 2 with --games games and the others with --others each (default 30 to 400), and
// empty ROM files with generated No-Intro-style names. Every game but one in --no-art-every has a cover in the media
// folder (DataDir/media), hardlinked from the spike library's JPEGs, and its baked BC7 derivative in cache/textures,
// hardlinked from the spike's DDS files, so the library costs almost no disk. With --slots, those games also get art
// of each named kind (a different spike image for each), for themes whose templates use more slots than the cover.
// With --models, that many PlayStation 2 games, spread evenly, get a per-game model of their own
// (DataDir/media/ps2/model/<rel path>.glb, M6): a lathed figure on a plinth, about 1,000 triangles, with a cover
// slot on the plinth and, on every third, a small texture of its own. Then it scans the library, so the app boots warm.
//
// The folder is deleted and recreated, but only if it's empty or was made by this tool.
var options = Options.Parse(args);
if (options is null)
{
    Console.Error.WriteLine("usage: synthetic-library --out=<absolute folder> --covers=<absolute spike library> [--games=10000] [--others=<n>] [--no-art-every=9] [--slots=back,spine,...] [--models=<n>]");
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
var models = 0;
// The 14 systems built in before the ES-DE catalogue, and the six above: the library is 20 systems, whatever the
// built-in list grows to (the rest are empty, and the grid leaves them out).
var generated = new HashSet<string>(
    ["gb", "gbc", "gba", "nes", "snes", "n64", "gc", "mastersystem", "megadrive", "saturn", "dreamcast", "psx", "ps2", "psp"],
    StringComparer.Ordinal);
foreach (var (id, _, _) in extra)
{
    generated.Add(id);
}

var generatedSystems = loaded.Config.Systems.Where(s => generated.Contains(s.Id)).ToList();
foreach (var system in generatedSystems)
{
    var count = system.Id == "ps2" ? options.Games : options.Others ?? random.Next(30, 401);
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
        if (system.Id == "ps2" && options.Models > 0 && i % Math.Max(1, count / options.Models) == 0 && models < options.Models)
        {
            var model = Path.Combine(root, MediaScanner.FolderName, "ps2", MediaKinds.Model, stem + extension + ".glb");
            Directory.CreateDirectory(Path.GetDirectoryName(model)!);
            File.WriteAllBytes(model, SyntheticModels.Make(random, models));
            models++;
        }

        if (options.NoArtEvery > 0 && games % options.NoArtEvery == 0)
        {
            continue;
        }

        // The spike's cover N, as the game's art, and its baked derivative under the key the app looks up; each
        // extra slot kind gets another spike image.
        var n = spikeCover++;
        Link(system.Id, MediaKinds.Cover, stem, n % 10_000);
        for (var k = 0; k < options.Slots.Count; k++)
        {
            Link(system.Id, options.Slots[k], stem, (n + 3_331 * (k + 1)) % 10_000);
        }

        covers++;
    }
}

Console.WriteLine($"Wrote {generatedSystems.Count} systems, {games:N0} games, {covers:N0} covers and {models:N0} per-game models in {stopwatch.Elapsed.TotalSeconds:0.0} s.");

stopwatch.Restart();
using (var library = await LibraryService.OpenAsync(loaded.Config, root, null, default))
{
    library.IndexMedia = true;
    var summary = await library.RescanAsync(null, null, default);
    Console.WriteLine($"Scanned {summary.Added:N0} games in {stopwatch.Elapsed.TotalSeconds:0.0} s; {summary.Diagnostics.Count} diagnostics.");
    foreach (var diagnostic in summary.Diagnostics.Take(5))
    {
        Console.WriteLine(diagnostic);
    }
}

Console.WriteLine($"Run the app with ++ --user-dir={root}");
return 0;

void Link(string systemId, string kind, string stem, int n)
{
    var sourceJpeg = Path.Combine(options.Covers, "jpg", n.ToString("D5", CultureInfo.InvariantCulture) + ".jpg");
    var sourceDds = Path.Combine(options.Covers, "dds-bc7", n.ToString("D5", CultureInfo.InvariantCulture) + ".dds");
    var relative = $"{MediaScanner.FolderName}/{systemId}/{kind}/{stem}.jpg";
    var art = Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar));
    Directory.CreateDirectory(Path.GetDirectoryName(art)!);
    HardLink(art, sourceJpeg);
    var info = new FileInfo(art);
    var key = TextureDerivatives.FileName(relative, info.Length, new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds());
    var derivative = Path.Combine(cacheDir, key);
    if (!File.Exists(derivative))
    {
        HardLink(derivative, sourceDds);
    }
}

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

internal sealed record Options(string Out, string Covers, int Games, int? Others, int NoArtEvery, IReadOnlyList<string> Slots, int Models)
{
    public static Options? Parse(string[] args)
    {
        string? output = null;
        string? covers = null;
        var games = 10_000;
        int? others = null;
        var noArtEvery = 9;
        var models = 0;
        var slots = new List<string>();
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
                case "--others" when int.TryParse(value, CultureInfo.InvariantCulture, out var n) && n >= 0:
                    others = n;
                    break;
                case "--slots":
                    foreach (var kind in value.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                    {
                        if (!MediaKinds.Images.Contains(kind) || kind == MediaKinds.Cover || slots.Contains(kind))
                        {
                            return null;
                        }

                        slots.Add(kind);
                    }

                    break;
                case "--no-art-every" when int.TryParse(value, CultureInfo.InvariantCulture, out var n) && n >= 0:
                    noArtEvery = n;
                    break;
                case "--models" when int.TryParse(value, CultureInfo.InvariantCulture, out var n) && n >= 0:
                    models = n;
                    break;
                default:
                    return null;
            }
        }

        return output is null || covers is null ? null : new Options(output, covers, games, others, noArtEvery, slots, models);
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

/// <summary>
/// Per-game models for benches (M6): a figure turned on a lathe (a random profile, 24 sides, 20 rings, 960 triangles)
/// on a box plinth whose front is a cover slot, in a random colour; every third has a 128² texture of its own on the
/// plinth, so a list of them has materials of its own too. Within the per-game budget (A7).
/// </summary>
internal static class SyntheticModels
{
    public static byte[] Make(Random random, int index)
    {
        var builder = new GltfBuilder { Generator = "synthetic-library" };
        var hue = random.NextSingle();
        var colour = Hsv(hue, 0.55f, 0.75f);
        var texture = -1;
        if (index % 3 == 0)
        {
            var rgba = new byte[128 * 128 * 4];
            var stripe = Hsv((hue + 0.5f) % 1, 0.6f, 0.9f);
            for (var y = 0; y < 128; y++)
            {
                for (var x = 0; x < 128; x++)
                {
                    var c = ((x + y) / 16 + index) % 2 == 0 ? stripe : colour;
                    var i = (y * 128 + x) * 4;
                    rgba[i] = (byte)(c.X * 255);
                    rgba[i + 1] = (byte)(c.Y * 255);
                    rgba[i + 2] = (byte)(c.Z * 255);
                    rgba[i + 3] = 255;
                }
            }

            texture = builder.AddImage(PngEncoder.Encode(rgba, 128, 128), "image/png");
        }

        var figure = builder.AddMaterial("figure", new Vector4(Linear(colour), 1), 0.35f, 0.2f);
        var plinth = builder.AddMaterial("plinth", texture >= 0 ? Vector4.One : new Vector4(0.08f, 0.08f, 0.1f, 1), 0.6f, 0, texture);
        var cover = builder.AddMaterial("cover", Vector4.One, 0.3f, aspect: 0.66f / 0.26f);

        // The lathe: a radius for each height, from a couple of random bulges.
        const int Sides = 24;
        const int Rings = 20;
        var a1 = 0.1f + random.NextSingle() * 0.15f;
        var a2 = random.NextSingle() * 0.12f;
        var f2 = 1.5f + random.NextSingle() * 3;
        var positions = new List<Vector3>();
        var normals = new List<Vector3>();
        var indices = new List<int>();
        for (var r = 0; r <= Rings; r++)
        {
            var t = (float)r / Rings;
            var radius = 0.04f + a1 * MathF.Sin(MathF.PI * t) + a2 * MathF.Sin(MathF.PI * f2 * t) * MathF.Sin(MathF.PI * t);
            for (var s = 0; s <= Sides; s++)
            {
                var (sin, cos) = MathF.SinCos(MathF.Tau * s / Sides);
                positions.Add(new Vector3(cos * radius, 0.3f + t * 0.7f, sin * radius));
                normals.Add(Vector3.Normalize(new Vector3(cos, 0.15f, sin)));
            }
        }

        for (var r = 0; r < Rings; r++)
        {
            for (var s = 0; s < Sides; s++)
            {
                var a = r * (Sides + 1) + s;
                var b = a + Sides + 1;
                indices.AddRange([a, b, a + 1, a + 1, b, b + 1]);
            }
        }

        var mesh = builder.AddMesh("figure", [
            new GltfPrimitive([.. positions], [.. normals], null, [.. indices], figure),
            Box(new Vector3(0, 0.15f, 0), new Vector3(0.7f, 0.3f, 0.5f), plinth),
            Box(new Vector3(0, 0.15f, 0.2505f), new Vector3(0.66f, 0.26f, 0.001f), cover),
        ]);
        builder.AddNode("figure", mesh);
        return builder.ToGlb();
    }

    /// <summary>A box, each face's UVs spanning 0..1 upright, counter-clockwise from outside.</summary>
    private static GltfPrimitive Box(Vector3 centre, Vector3 size, int material)
    {
        var h = size / 2;
        var positions = new List<Vector3>();
        var normals = new List<Vector3>();
        var uvs = new List<Vector2>();
        var indices = new List<int>();
        foreach (var (normal, right, up) in (ReadOnlySpan<(Vector3, Vector3, Vector3)>)[
            (Vector3.UnitZ, Vector3.UnitX, Vector3.UnitY), (-Vector3.UnitZ, -Vector3.UnitX, Vector3.UnitY),
            (Vector3.UnitX, -Vector3.UnitZ, Vector3.UnitY), (-Vector3.UnitX, Vector3.UnitZ, Vector3.UnitY),
            (Vector3.UnitY, Vector3.UnitX, -Vector3.UnitZ), (-Vector3.UnitY, Vector3.UnitX, Vector3.UnitZ)])
        {
            var c = centre + normal * MathF.Abs(Vector3.Dot(normal, h));
            var r = right * MathF.Abs(Vector3.Dot(right, h));
            var u = up * MathF.Abs(Vector3.Dot(up, h));
            var first = positions.Count;
            positions.AddRange([c - r + u, c + r + u, c + r - u, c - r - u]);
            normals.AddRange([normal, normal, normal, normal]);
            uvs.AddRange([new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1)]);
            indices.AddRange([first, first + 3, first + 2, first, first + 2, first + 1]);
        }

        return new GltfPrimitive([.. positions], [.. normals], [.. uvs], [.. indices], material);
    }

    private static Vector3 Hsv(float h, float s, float v)
    {
        var sector = (int)(h * 6) % 6;
        var f = h * 6 - MathF.Floor(h * 6);
        var (p, q, t) = (v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s));
        return sector switch
        {
            0 => new Vector3(v, t, p),
            1 => new Vector3(q, v, p),
            2 => new Vector3(p, v, t),
            3 => new Vector3(p, q, v),
            4 => new Vector3(t, p, v),
            _ => new Vector3(v, p, q),
        };
    }

    private static Vector3 Linear(Vector3 srgb) => new(MathF.Pow(srgb.X, 2.2f), MathF.Pow(srgb.Y, 2.2f), MathF.Pow(srgb.Z, 2.2f));
}

internal static partial class NativeMethods
{
    [LibraryImport("kernel32.dll", EntryPoint = "CreateHardLinkW", StringMarshalling = StringMarshalling.Utf16, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static partial bool CreateHardLinkW(string fileName, string existingFileName, nint securityAttributes);
}
