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

    /// <summary>The kinds that are images, and so can be the user's own art in <c>ConfigDir/media/&lt;system&gt;/&lt;kind&gt;/</c>.</summary>
    public static IReadOnlyList<string> Images { get; } = [Cover, Back, Spine, BoxTexture, Label, Screenshot, Logo, Hero];

    /// <summary>The kinds scraping can download (<c>[scraping] media</c>). No provider has labels.</summary>
    public static IReadOnlyList<string> Scrapable { get; } = [Cover, Back, Spine, BoxTexture, Screenshot, Logo, Hero];

    /// <summary>The image formats the app decodes, matched ignoring case.</summary>
    public static IReadOnlyList<string> ImageExtensions { get; } = [".png", ".jpg", ".jpeg", ".webp"];
}
