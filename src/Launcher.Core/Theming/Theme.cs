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
/// <param name="ShapeFromMedia">
/// <c>shape = "media"</c>: each game's box takes its front's proportions from its cover (or, for a model with no
/// <c>cover</c> material, its screenshot) and its depth from its spine (<see cref="BoxShape"/>); otherwise the model's
/// own shape.
/// </param>
/// <param name="WholeSlots">
/// <c>[templates.&lt;id&gt;.fit]</c>: the slots whose art is drawn whole, fitted inside the face over its fallback (a
/// screen showing a tall screenshot pillarboxed), rather than centre-cropped to fill it. Null for none.
/// </param>
/// <param name="ThemeId">The theme that declares the template (one extending a base template by its id declares its own).</param>
/// <param name="ModelFromBase">
/// <see cref="Model"/> is the base theme's (relative to its folder): the template extends a base template of the same
/// id without a model of its own.
/// </param>
public sealed record GameTemplate(
    string Id,
    string Model,
    IReadOnlyDictionary<int, SlotChain> Slots,
    bool ShapeFromMedia = false,
    IReadOnlySet<int>? WholeSlots = null,
    string ThemeId = "",
    bool ModelFromBase = false)
{
    public SlotChain ChainFor(int slot) => Slots.TryGetValue(slot, out var chain) ? chain : SlotChain.Default(slot);

    /// <summary>Whether the slot's art is drawn whole (<c>fit = "whole"</c>); a logo always is, whatever this says.</summary>
    public bool ShowsWhole(int slot) => WholeSlots?.Contains(slot) == true;
}

/// <summary>What a theme says about one system (<c>[systems.&lt;id&gt;]</c>).</summary>
/// <param name="Model">The system card's <c>.glb</c>, relative to the theme's folder; null for the theme's default.</param>
/// <param name="Tint">Whether the card's plain materials take the system's colour; null for the theme's default.</param>
/// <param name="GameTemplate">A template id in the same theme or the base theme; null for the theme's default.</param>
/// <param name="Colour">The system's colour: its card's tint and its plain boxes' colour. Null when the theme has none.</param>
/// <param name="Look">The look while the system's games are shown, already layered over the theme's look.</param>
/// <param name="Logo">The system's image (<c>logo</c>), relative to the theme's folder; null for <c>logos/&lt;id&gt;.*</c> if there is one.</param>
/// <param name="Slots">
/// <c>[systems.&lt;id&gt;.slots]</c>: the chains of its card's slots, by slot number, over the theme's
/// <see cref="ThemeDefaults.SystemSlots"/>. Null for none.
/// </param>
public sealed record ThemeSystem(
    string Id,
    string? Model,
    bool? Tint,
    string? GameTemplate,
    Rgb? Colour,
    Look Look,
    string? Logo = null,
    IReadOnlyDictionary<int, SlotChain>? Slots = null);

/// <summary><c>[defaults]</c>.</summary>
/// <param name="SystemModel">The card for systems without their own model, relative to the theme's folder.</param>
/// <param name="TintSystemModel">Whether that default card takes each system's colour.</param>
/// <param name="GameTemplate">The template for systems the theme doesn't assign one: its own or the base theme's.</param>
/// <param name="SystemSlots">
/// <c>[defaults.system_slots]</c>: the chains of the slots of this theme's cards, by slot number. A slot it doesn't list
/// uses <see cref="SlotChain.ForSystemModel"/>.
/// </param>
public sealed record ThemeDefaults(string? SystemModel, bool TintSystemModel, string? GameTemplate, IReadOnlyDictionary<int, SlotChain> SystemSlots);

public enum ThemeOrigin
{
    /// <summary>
    /// Shipped with the app, in the <c>themes/&lt;id&gt;/</c> folder beside its executable (outside the PCK). Trusted: its
    /// models aren't inspected when they load, as Core's tests check them.
    /// </summary>
    BuiltIn,

    /// <summary><c>ConfigDir/themes/&lt;id&gt;/</c>.</summary>
    User,
}

/// <summary>A loaded, validated theme (A6). Only valid entries are present.</summary>
/// <param name="Folder">The theme's folder, an absolute path.</param>
/// <param name="LookTransitionMs">How long a cross-fade between looks takes.</param>
/// <param name="Logos">
/// Each card's image, by system id (or <c>favourites</c> and <c>recently_played</c>), relative to the theme's folder: a
/// system's <c>logo</c>, else <c>logos/&lt;id&gt;.png</c>, <c>.jpg</c>, <c>.jpeg</c> or <c>.webp</c>.
/// </param>
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
    IReadOnlyDictionary<string, ThemeSystem> Systems,
    IReadOnlyDictionary<string, string> Logos)
{
    /// <summary>The folder whose images are cards' logos by file name (<c>logos/ps2.webp</c>).</summary>
    public const string LogosFolder = "logos";

    /// <summary>The look for a system's games, or the theme's own look for the systems grid (null) and virtual systems.</summary>
    public Look LookFor(string? systemId) =>
        systemId is not null && Systems.TryGetValue(systemId, out var system) ? system.Look : Look;

    /// <summary>A path inside the theme, as its loader opens it: an absolute file path.</summary>
    public string PathOf(string relative) => Path.GetFullPath(Path.Combine(Folder, relative.Replace('/', Path.DirectorySeparatorChar)));
}
