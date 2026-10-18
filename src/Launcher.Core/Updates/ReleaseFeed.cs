using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using Launcher.Core.Theming.Downloads;

namespace Launcher.Core.Updates;

/// <summary>A file a release offers: its name, where to get it, its size in bytes, and its SHA-256 when the feed gives one.</summary>
public sealed record UpdateAsset(string Name, Uri Url, long Size, string? Sha256);

/// <summary>
/// A release with a package for this platform (<see cref="Package"/>: <c>OdysseyLauncher-&lt;version&gt;-&lt;platform&gt;.zip</c>,
/// as the release workflow names it) and, when the release has one, its <c>.sha256</c> file (<see cref="Checksum"/>).
/// </summary>
public sealed record UpdateRelease(
    AppVersion Version,
    string Tag,
    string Title,
    string Notes,
    Uri? Page,
    bool PreRelease,
    UpdateAsset Package,
    UpdateAsset? Checksum);

/// <summary>
/// Reads a GitHub releases list (<c>GET /repos/{owner}/{repo}/releases</c>, or a local feed's <c>releases.json</c> in the
/// same shape) into the releases this platform can install, and picks the one to offer. Never throws for a bad entry:
/// it's left out.
/// </summary>
public static partial class ReleaseFeed
{
    private static readonly JsonDocumentOptions Options = new() { MaxDepth = 64 };

    /// <summary>The package's file name for <paramref name="version"/> on <paramref name="platform"/> (<c>windows-x86_64</c>).</summary>
    public static string PackageName(AppVersion version, string platform) =>
        string.Create(CultureInfo.InvariantCulture, $"OdysseyLauncher-{version}-{platform}.zip");

    /// <summary>
    /// The releases in <paramref name="json"/> that have a package for <paramref name="platform"/>, drafts and tags that
    /// aren't versions left out. <paramref name="baseUri"/> resolves relative download URLs (a local feed's file
    /// names); without it, only absolute HTTPS URLs count. Throws <see cref="JsonException"/> if it isn't a JSON array.
    /// </summary>
    public static IReadOnlyList<UpdateRelease> Parse(string json, string platform, Uri? baseUri = null)
    {
        ArgumentNullException.ThrowIfNull(json);
        ArgumentNullException.ThrowIfNull(platform);
        using var document = JsonDocument.Parse(json, Options);
        if (document.RootElement.ValueKind != JsonValueKind.Array)
        {
            throw new JsonException("The releases list isn't a JSON array.");
        }

        var releases = new List<UpdateRelease>();
        foreach (var entry in document.RootElement.EnumerateArray())
        {
            if (Read(entry, platform, baseUri) is { } release)
            {
                releases.Add(release);
            }
        }

        return releases;
    }

    /// <summary>
    /// The newest release newer than <paramref name="current"/>, or null when there's none. Pre-releases are offered only
    /// to a pre-release (someone testing a beta gets the next beta or the release; everyone else gets releases).
    /// </summary>
    public static UpdateRelease? Newest(IReadOnlyList<UpdateRelease> releases, AppVersion current)
    {
        ArgumentNullException.ThrowIfNull(releases);
        UpdateRelease? newest = null;
        foreach (var release in releases)
        {
            if ((release.PreRelease || release.Version.PreRelease is not null) && current.PreRelease is null)
            {
                continue;
            }

            if (release.Version > current && (newest is null || release.Version > newest.Version))
            {
                newest = release;
            }
        }

        return newest;
    }

    /// <summary>
    /// The first <paramref name="maxLines"/> lines of a release's notes as plain text, for the question that offers it:
    /// GitHub's generated notes are Markdown (headings, bullets, links), and the changelog link and the "new
    /// contributors" heading say nothing about the launcher, nor does each change's "by @author in &lt;pull request&gt;".
    /// Each line is a bullet, cut at <paramref name="maxLength"/> characters; a line follows saying how many more there are.
    /// </summary>
    public static IReadOnlyList<string> Summary(string notes, int maxLines = 5, int maxLength = 100)
    {
        ArgumentNullException.ThrowIfNull(notes);
        var lines = new List<string>();
        var more = 0;
        foreach (var raw in notes.ReplaceLineEndings("\n").Split('\n'))
        {
            var line = Credit().Replace(raw.Trim().TrimStart('#', '*', '-', '+', ' ').Replace("**", string.Empty, StringComparison.Ordinal), string.Empty).Trim();
            if (line.Length == 0 || line.StartsWith("Full Changelog", StringComparison.OrdinalIgnoreCase)
                || line.Equals("What's Changed", StringComparison.OrdinalIgnoreCase) || line.Equals("New Contributors", StringComparison.OrdinalIgnoreCase)
                || line.StartsWith("<!--", StringComparison.Ordinal))
            {
                continue;
            }

            if (lines.Count == maxLines)
            {
                more++;
                continue;
            }

            lines.Add("• " + (line.Length <= maxLength ? line : string.Concat(line.AsSpan(0, maxLength - 1).TrimEnd(), "…")));
        }

        if (more > 0)
        {
            lines.Add(string.Create(CultureInfo.InvariantCulture, $"…and {more} more."));
        }

        return lines;
    }

    /// <summary>GitHub's " by @author in https://…" after each change in generated notes.</summary>
    [GeneratedRegex(@"\s+by\s+@\S+\s+in\s+https?://\S+$", RegexOptions.CultureInvariant)]
    private static partial Regex Credit();

    private static UpdateRelease? Read(JsonElement entry, string platform, Uri? baseUri)
    {
        if (entry.ValueKind != JsonValueKind.Object || Bool(entry, "draft"))
        {
            return null;
        }

        var tag = Text(entry, "tag_name");
        if (tag is null || !AppVersion.TryParse(tag.StartsWith('v') ? tag[1..] : tag, out var version))
        {
            return null;
        }

        if (!entry.TryGetProperty("assets", out var assets) || assets.ValueKind != JsonValueKind.Array)
        {
            return null;
        }

        var packageName = PackageName(version, platform);
        UpdateAsset? package = null;
        UpdateAsset? checksum = null;
        foreach (var asset in assets.EnumerateArray())
        {
            var name = asset.ValueKind == JsonValueKind.Object ? Text(asset, "name") : null;
            if (name == packageName)
            {
                package = Asset(asset, name, baseUri);
            }
            else if (name == packageName + ".sha256")
            {
                checksum = Asset(asset, name, baseUri);
            }
        }

        if (package is null)
        {
            return null;
        }

        var page = Uri.TryCreate(Text(entry, "html_url"), UriKind.Absolute, out var html) && html.Scheme == Uri.UriSchemeHttps ? html : null;
        return new UpdateRelease(version, tag, Text(entry, "name") is { Length: > 0 } title ? title : tag, Text(entry, "body") ?? string.Empty,
            page, Bool(entry, "prerelease"), package, checksum);
    }

    private static UpdateAsset? Asset(JsonElement asset, string name, Uri? baseUri)
    {
        var url = Text(asset, "browser_download_url");
        Uri? resolved = null;
        if (url is not null && Uri.TryCreate(url, UriKind.Absolute, out var absolute) && absolute.Scheme == Uri.UriSchemeHttps)
        {
            resolved = absolute;
        }
        else if (url is not null && baseUri is not null && Uri.TryCreate(baseUri, url, out var relative))
        {
            resolved = relative;
        }

        if (resolved is null)
        {
            return null;
        }

        var size = asset.TryGetProperty("size", out var s) && s.ValueKind == JsonValueKind.Number && s.TryGetInt64(out var bytes) ? bytes : 0;
        // GitHub gives each asset's digest ("sha256:<hex>") since 2025.
        var digest = Text(asset, "digest");
        var sha256 = digest is not null && digest.StartsWith("sha256:", StringComparison.OrdinalIgnoreCase) ? Checksums.Normalise(digest[7..]) : null;
        return new UpdateAsset(name, resolved, size, sha256);
    }

    private static string? Text(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static bool Bool(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.True;
}

/// <summary>SHA-256 checksums as text.</summary>
public static class Checksums
{
    /// <summary>64 hex digits in lower case, or null if <paramref name="text"/> isn't one.</summary>
    public static string? Normalise(string? text)
    {
        var hex = text?.Trim();
        if (hex is not { Length: 64 } || !hex.All(char.IsAsciiHexDigit))
        {
            return null;
        }

        return hex.ToLowerInvariant();
    }

    /// <summary>
    /// The checksum in a <c>.sha256</c> file (<c>&lt;hex&gt;  &lt;file name&gt;</c>, as <c>sha256sum</c> and the release
    /// workflow write it), or null.
    /// </summary>
    public static string? FromChecksumFile(string? text)
    {
        if (text is null)
        {
            return null;
        }

        var trimmed = text.TrimStart('﻿').Trim();
        var end = 0;
        while (end < trimmed.Length && !char.IsWhiteSpace(trimmed[end]))
        {
            end++;
        }

        return Normalise(trimmed[..end]);
    }
}
