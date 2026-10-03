using System.Text;

namespace Launcher.Core.Scanning;

/// <summary>
/// ROM identity (ARCHITECTURE.md A4). <c>rel_path</c> is the path as on disk, relative to its ROM
/// folder, '/'-separated and NFC. <c>path_key</c> is <c>rel_path</c> lower-cased (invariant) on every OS.
/// </summary>
public static class PathKeys
{
    /// <summary>Normalises a relative path to <c>rel_path</c> form.</summary>
    public static string ToRelPath(string relative)
    {
        ArgumentNullException.ThrowIfNull(relative);
        var path = relative.Replace('\\', '/');
        return path.IsNormalized(NormalizationForm.FormC) ? path : path.Normalize(NormalizationForm.FormC);
    }

    public static string ToPathKey(string relPath)
    {
        ArgumentNullException.ThrowIfNull(relPath);
        return relPath.ToLowerInvariant();
    }

    /// <summary>
    /// Resolves <paramref name="reference"/> (as written inside a playlist) against the folder of
    /// <paramref name="fromRelPath"/>, giving a <c>path_key</c>. Null when it points outside the ROM folder.
    /// </summary>
    public static string? ResolveReference(string fromRelPath, string reference) =>
        ResolveRelPath(fromRelPath, reference) is { } relPath ? ToPathKey(relPath) : null;

    /// <summary>
    /// <see cref="ResolveReference"/>, giving the <c>rel_path</c> as the playlist writes it (case kept), to find the
    /// file on disk.
    /// </summary>
    public static string? ResolveRelPath(string fromRelPath, string reference)
    {
        ArgumentNullException.ThrowIfNull(fromRelPath);
        ArgumentNullException.ThrowIfNull(reference);
        var target = reference.Trim().Replace('\\', '/');
        if (target.Length == 0 || target.Contains(':', StringComparison.Ordinal) || target.StartsWith('/'))
        {
            // Absolute paths (C:/..., /...) and URLs can't be matched against files under a ROM folder.
            return null;
        }

        var segments = new List<string>();
        var slash = fromRelPath.LastIndexOf('/');
        if (slash > 0)
        {
            segments.AddRange(fromRelPath[..slash].Split('/'));
        }

        foreach (var segment in target.Split('/'))
        {
            if (segment.Length == 0 || segment == ".")
            {
                continue;
            }

            if (segment == "..")
            {
                if (segments.Count == 0)
                {
                    return null;
                }

                segments.RemoveAt(segments.Count - 1);
                continue;
            }

            segments.Add(segment);
        }

        return segments.Count == 0 ? null : ToRelPath(string.Join('/', segments));
    }
}
