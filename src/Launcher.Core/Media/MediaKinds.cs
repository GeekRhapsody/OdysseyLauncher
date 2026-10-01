namespace Launcher.Core.Media;

/// <summary>The <c>media.kind</c> values (ARCHITECTURE.md A4), which are also the media slot names of models (A7).</summary>
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

    /// <summary>A gameplay video (scraped only, an MP4): not an image, so not a slot, and nothing plays it yet.</summary>
    public const string Video = "video";

    /// <summary>A per-game model: the user's <c>ConfigDir/models/games/&lt;system&gt;/&lt;rel path&gt;.glb</c> (M6).</summary>
    public const string Model = "model";

    /// <summary>The kinds that are images, and so can be the user's own art in <c>ConfigDir/media/&lt;system&gt;/&lt;kind&gt;/</c>.</summary>
    public static IReadOnlyList<string> Images { get; } = [Cover, Back, Spine, BoxTexture, Label, Screenshot, Logo, Hero];

    /// <summary>
    /// The kinds scraping can download (<c>[scraping] media</c>), in the order the settings list them. Box textures
    /// aren't scraped any more (2026-10-01); the slot stays for the user's own art.
    /// </summary>
    public static IReadOnlyList<string> Scrapable { get; } = [Cover, Back, Spine, Screenshot, Logo, Hero, Label, Video];

    /// <summary>The image formats the app decodes, matched ignoring case.</summary>
    public static IReadOnlyList<string> ImageExtensions { get; } = [".png", ".jpg", ".jpeg", ".webp"];
}
