using System.Globalization;

namespace Launcher.Core.Theming;

/// <summary>An sRGB colour as a theme writes it: <c>#RRGGBB</c>.</summary>
public readonly record struct Rgb(byte R, byte G, byte B)
{
    public static bool TryParse(string? text, out Rgb colour)
    {
        colour = default;
        if (text is not { Length: 7 } || text[0] != '#'
            || !int.TryParse(text.AsSpan(1), NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture, out var value))
        {
            return false;
        }

        colour = new Rgb((byte)(value >> 16), (byte)(value >> 8), (byte)value);
        return true;
    }

    public override string ToString() => string.Create(CultureInfo.InvariantCulture, $"#{R:X2}{G:X2}{B:X2}");
}

/// <summary>A light's direction of travel, in view space: +X right, +Y up, +Z towards the viewer (A6).</summary>
public readonly record struct LightDirection(float X, float Y, float Z);

/// <summary>The icon.sys-style background: one sRGB colour per screen corner.</summary>
public sealed record LookBackground(Rgb TopLeft, Rgb TopRight, Rgb BottomLeft, Rgb BottomRight);

/// <param name="Energy">A linear multiplier.</param>
public sealed record LookAmbient(Rgb Colour, float Energy);

public sealed record LookLight(LightDirection Direction, Rgb Colour, float Energy);

/// <summary>A look (A6): the background gradient, the ambient light and one to three directional lights.</summary>
public sealed record Look(LookBackground Background, LookAmbient Ambient, IReadOnlyList<LookLight> Lights);

/// <summary>A game template (<c>[templates.&lt;id&gt;]</c>): a model, and the fallback chain of each of its slots.</summary>
/// <param name="Model">The <c>.glb</c>, relative to the theme's folder, '/'-separated.</param>
/// <param name="Slots">The chains the theme writes, by slot number; a slot it doesn't list uses <see cref="SlotChain.Default"/>.</param>
public sealed record GameTemplate(string Id, string Model, IReadOnlyDictionary<int, SlotChain> Slots)
{
    public SlotChain ChainFor(int slot) => Slots.TryGetValue(slot, out var chain) ? chain : SlotChain.Default(slot);
}

/// <summary>What a theme says about one system (<c>[systems.&lt;id&gt;]</c>).</summary>
/// <param name="Model">The system card's <c>.glb</c>, relative to the theme's folder; null for the theme's default.</param>
/// <param name="Tint">Whether the card's plain materials take the system's colour; null for the theme's default.</param>
/// <param name="GameTemplate">A template id in the same theme; null for the theme's default.</param>
/// <param name="Colour">The system's colour: its card's tint and its plain boxes' colour. Null when the theme has none.</param>
/// <param name="Look">The look while the system's games are shown, already layered over the theme's look.</param>
public sealed record ThemeSystem(string Id, string? Model, bool? Tint, string? GameTemplate, Rgb? Colour, Look Look);

/// <summary><c>[defaults]</c>.</summary>
/// <param name="SystemModel">The card for systems without their own model, relative to the theme's folder.</param>
/// <param name="TintSystemModel">Whether that default card takes each system's colour.</param>
/// <param name="GameTemplate">The template for systems the theme doesn't assign one.</param>
public sealed record ThemeDefaults(string? SystemModel, bool TintSystemModel, string? GameTemplate);

public enum ThemeOrigin
{
    /// <summary>Shipped in the app's PCK (<c>res://themes/&lt;id&gt;/</c>), its models exported as the <c>.glb</c> files themselves.</summary>
    BuiltIn,

    /// <summary><c>ConfigDir/themes/&lt;id&gt;/</c>.</summary>
    User,
}

/// <summary>A loaded, validated theme (A6). Only valid entries are present.</summary>
/// <param name="Folder">The theme's folder: <c>res://themes/&lt;id&gt;</c> or an absolute path.</param>
/// <param name="LookTransitionMs">How long a cross-fade between looks takes.</param>
public sealed record Theme(
    string Id,
    string Name,
    string? Author,
    ThemeOrigin Origin,
    string Folder,
    int LookTransitionMs,
    Look Look,
    ThemeDefaults Defaults,
    IReadOnlyDictionary<string, GameTemplate> Templates,
    IReadOnlyDictionary<string, ThemeSystem> Systems)
{
    /// <summary>The look for a system's games, or the theme's own look for the systems grid (null) and virtual systems.</summary>
    public Look LookFor(string? systemId) =>
        systemId is not null && Systems.TryGetValue(systemId, out var system) ? system.Look : Look;

    /// <summary>A path inside the theme, as its loader opens it (a <c>res://</c> path, or an absolute file path).</summary>
    public string PathOf(string relative) => Origin == ThemeOrigin.BuiltIn
        ? $"{Folder.TrimEnd('/')}/{relative}"
        : Path.GetFullPath(Path.Combine(Folder, relative.Replace('/', Path.DirectorySeparatorChar)));
}
