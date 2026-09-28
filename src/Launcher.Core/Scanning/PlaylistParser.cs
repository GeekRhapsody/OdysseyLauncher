using System.Text;
using System.Text.RegularExpressions;

namespace Launcher.Core.Scanning;

/// <summary>
/// Reads the files a multi-file game is made of. An <c>.m3u</c> lists its discs, a <c>.cue</c> its
/// <c>FILE</c> tracks and a <c>.gdi</c> its track files. The scanner hides every referenced file, so the
/// playlist alone represents the game.
/// </summary>
public static partial class PlaylistParser
{
    /// <summary>Playlists bigger than this aren't real playlists, so they aren't read.</summary>
    public const int MaxBytes = 256 * 1024;

    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    public static bool IsPlaylist(string extension) =>
        extension.Equals(".m3u", StringComparison.OrdinalIgnoreCase)
        || extension.Equals(".cue", StringComparison.OrdinalIgnoreCase)
        || extension.Equals(".gdi", StringComparison.OrdinalIgnoreCase);

    /// <summary>Returns the references as written (relative to the playlist's folder), in order.</summary>
    public static List<string> Parse(string extension, string text)
    {
        ArgumentNullException.ThrowIfNull(extension);
        ArgumentNullException.ThrowIfNull(text);
        var references = new List<string>();
        var isM3u = extension.Equals(".m3u", StringComparison.OrdinalIgnoreCase);
        var isCue = extension.Equals(".cue", StringComparison.OrdinalIgnoreCase);
        var firstLine = true;
        foreach (var rawLine in text.Split('\n'))
        {
            var line = rawLine.Trim().TrimStart('﻿');
            if (line.Length == 0)
            {
                continue;
            }

            if (isM3u)
            {
                if (!line.StartsWith('#'))
                {
                    references.Add(line);
                }

                continue;
            }

            if (isCue)
            {
                var match = CueFileRegex().Match(line);
                if (match.Success)
                {
                    references.Add(match.Groups[1].Success ? match.Groups[1].Value : match.Groups[2].Value);
                }

                continue;
            }

            // .gdi: the first line is the track count, then "track lba type sector-size file offset".
            if (firstLine)
            {
                firstLine = false;
                continue;
            }

            var track = GdiTrackRegex().Match(line);
            if (track.Success)
            {
                references.Add(track.Groups[1].Success ? track.Groups[1].Value : track.Groups[2].Value);
            }
        }

        return references;
    }

    /// <summary>Decodes playlist bytes: UTF-8 when valid, otherwise Latin-1 (old cue sheets aren't UTF-8).</summary>
    public static string Decode(ReadOnlySpan<byte> bytes)
    {
        try
        {
            return StrictUtf8.GetString(bytes);
        }
        catch (DecoderFallbackException)
        {
            return Encoding.Latin1.GetString(bytes);
        }
    }

    [GeneratedRegex("""^FILE\s+(?:"([^"]*)"|(\S+))(?:\s+\S+)?\s*$""", RegexOptions.CultureInvariant | RegexOptions.IgnoreCase)]
    private static partial Regex CueFileRegex();

    [GeneratedRegex("""^\d+\s+\d+\s+\d+\s+\d+\s+(?:"([^"]*)"|(\S+))\s+-?\d+\s*$""", RegexOptions.CultureInvariant)]
    private static partial Regex GdiTrackRegex();
}
