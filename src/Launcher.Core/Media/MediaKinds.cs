namespace Launcher.Core.Media;

/// <summary>
/// The <c>media.kind</c> values (ARCHITECTURE.md A4), which are also the media slot names of models (A7), and the
/// folders of the media folder: <c>DataDir/media/&lt;system&gt;/&lt;kind&gt;/</c>.
/// </summary>
public static class MediaKinds
{
    public const string Cover = "cover";
    public const string Back = "back";
    public const string Spine = "spine";
    public const string BoxTexture = "box_texture";
    public const string Label = "label";
    public const string Screenshot = "screenshot";
    public const string Logo = "logo";
    public const string Hero = "hero";

    /// <summary>A gameplay video (an MP4): not an image, so not a slot; the game's details screen plays it (<see cref="IVideoDecoder"/>).</summary>
    public const string Video = "video";

    /// <summary>A per-game model: <c>DataDir/media/&lt;system&gt;/model/&lt;rel path&gt;.glb</c> (M6).</summary>
    public const string Model = "model";

    /// <summary>The kinds that are images: any of them can fill a theme's slot, and each gets a derivative.</summary>
    public static IReadOnlyList<string> Images { get; } = [Cover, Back, Spine, BoxTexture, Label, Screenshot, Logo, Hero];

    /// <summary>Every kind the media folder has a folder for, so every kind a scan indexes.</summary>
    public static IReadOnlyList<string> All { get; } = [.. Images, Video, Model];

    /// <summary>
    /// The kinds scraping can download (<c>[scraping] media</c>), in the order the settings list them. Box textures
    /// aren't scraped any more (2026-10-01); the slot stays for the user's own art.
    /// </summary>
    public static IReadOnlyList<string> Scrapable { get; } = [Cover, Back, Spine, Screenshot, Logo, Hero, Label, Video];

    /// <summary>The image formats the app decodes, matched ignoring case.</summary>
    public static IReadOnlyList<string> ImageExtensions { get; } = [".png", ".jpg", ".jpeg", ".webp"];

    /// <summary>The video formats a scan indexes.</summary>
    public static IReadOnlyList<string> VideoExtensions { get; } = [".mp4"];

    /// <summary>The model format a scan indexes (A7: glTF binary only).</summary>
    public static IReadOnlyList<string> ModelExtensions { get; } = [".glb"];

    /// <summary>The file extensions a kind's folder is indexed for, matched ignoring case.</summary>
    public static IReadOnlyList<string> ExtensionsOf(string kind) => kind switch
    {
        Video => VideoExtensions,
        Model => ModelExtensions,
        _ => ImageExtensions,
    };
}
