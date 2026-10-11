using Launcher.Core.Media;

namespace Launcher.Core.Theming;

/// <summary>
/// The media slots of a model (A7): a material named after an image media kind shows that game's media of the
/// kind. Slots are numbered in <see cref="MediaKinds.Images"/> order, which the item shader mirrors.
/// </summary>
public static class MediaSlots
{
    public const int Cover = 0;
    public const int Back = 1;
    public const int Spine = 2;
    public const int BoxTexture = 3;
    public const int Label = 4;
    public const int Screenshot = 5;
    public const int Logo = 6;
    public const int Hero = 7;
    public const int Count = 8;

    /// <summary>The slot names, by slot number: <c>cover</c>, <c>back</c>, <c>spine</c>, <c>box_texture</c>, <c>label</c>, <c>screenshot</c>, <c>logo</c>, <c>hero</c>.</summary>
    public static IReadOnlyList<string> Names => MediaKinds.Images;

    /// <summary>The slot number of a media kind, or -1.</summary>
    public static int IndexOf(string kind)
    {
        for (var i = 0; i < Count; i++)
        {
            if (string.Equals(Names[i], kind, StringComparison.Ordinal))
            {
                return i;
            }
        }

        return -1;
    }

    /// <summary>
    /// The slot a material's name makes it, or -1 for a plain material. Matching ignores case and a trailing Blender
    /// <c>.NNN</c> suffix (A7), so <c>Cover.001</c> is the cover.
    /// </summary>
    public static int OfMaterial(string? materialName)
    {
        if (string.IsNullOrEmpty(materialName))
        {
            return -1;
        }

        var name = WithoutSuffix(materialName);
        for (var i = 0; i < Count; i++)
        {
            if (name.Equals(Names[i], StringComparison.OrdinalIgnoreCase))
            {
                return i;
            }
        }

        return -1;
    }

    /// <summary>The name of the material a system card plays its theme's video on (A6 Card videos).</summary>
    public const string VideoMaterial = "video";

    /// <summary>
    /// Whether a material is the card's screen for its theme's video (<c>video</c>, matched as slot names are). Its own
    /// texture is what it shows when no video plays.
    /// </summary>
    public static bool IsVideoMaterial(string? materialName) =>
        !string.IsNullOrEmpty(materialName) && WithoutSuffix(materialName).Equals(VideoMaterial, StringComparison.OrdinalIgnoreCase);

    /// <summary>A material's name without Blender's trailing <c>.NNN</c>.</summary>
    private static ReadOnlySpan<char> WithoutSuffix(string materialName)
    {
        var name = materialName.AsSpan();
        var dot = name.LastIndexOf('.');
        return dot > 0 && dot == name.Length - 4 && int.TryParse(name[(dot + 1)..], out _) ? name[..dot] : name;
    }

    /// <summary>
    /// Whether the launcher can draw the slot itself (<c>generated</c> in a fallback chain): a title card for the cover,
    /// a spine and back in the cover's colour, and a paper label with the title (M5's generated faces).
    /// </summary>
    public static bool HasGenerator(int slot) => slot is Cover or Back or Spine or Label;

    /// <summary>
    /// The side, in pixels, of the square every slot's media is standardised to on the GPU (A3). Every derivative is
    /// the whole image squeezed into a 512² BC7 DDS with mips; the cover uses it whole, and every other slot uses its
    /// mip chain from 256² down, so one derivative serves any slot and the shader crops it by the media's aspect.
    /// </summary>
    public static int TextureSize(int slot) => slot == Cover ? TextureDerivatives.Size : TextureDerivatives.Size / 2;
}
