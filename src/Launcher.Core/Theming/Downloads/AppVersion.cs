using System.Globalization;

namespace Launcher.Core.Theming.Downloads;

/// <summary>
/// A launcher version as releases name them (<c>0.17.0</c>, <c>0.2.0-beta.1</c>; build metadata after a <c>+</c> is
/// ignored), compared the way SemVer orders them: a pre-release comes before its release.
/// </summary>
public readonly record struct AppVersion(Version Release, string? PreRelease) : IComparable<AppVersion>
{
    public static bool TryParse(string? text, out AppVersion version)
    {
        version = default;
        if (string.IsNullOrWhiteSpace(text))
        {
            return false;
        }

        var core = text.Trim();
        var plus = core.IndexOf('+', StringComparison.Ordinal);
        if (plus >= 0)
        {
            core = core[..plus];
        }

        string? pre = null;
        var dash = core.IndexOf('-', StringComparison.Ordinal);
        if (dash >= 0)
        {
            pre = core[(dash + 1)..];
            core = core[..dash];
            if (pre.Length == 0)
            {
                return false;
            }
        }

        var parts = core.Split('.');
        if (parts.Length is < 2 or > 3 || !parts.All(p => p.Length > 0 && p.All(char.IsAsciiDigit)))
        {
            return false;
        }

        if (!Version.TryParse(parts.Length == 2 ? core + ".0" : core, out var release))
        {
            return false;
        }

        version = new AppVersion(release, pre);
        return true;
    }

    /// <summary>The running launcher's version (Core's informational version), or null when it isn't one (a test build).</summary>
    public static AppVersion? Current => TryParse(CoreInfo.Version, out var version) ? version : null;

    public int CompareTo(AppVersion other)
    {
        var release = Release.CompareTo(other.Release);
        if (release != 0)
        {
            return release;
        }

        return (PreRelease, other.PreRelease) switch
        {
            (null, null) => 0,
            (null, _) => 1,
            (_, null) => -1,
            _ => ComparePreRelease(PreRelease!, other.PreRelease!),
        };
    }

    public static bool operator <(AppVersion a, AppVersion b) => a.CompareTo(b) < 0;

    public static bool operator >(AppVersion a, AppVersion b) => a.CompareTo(b) > 0;

    public static bool operator <=(AppVersion a, AppVersion b) => a.CompareTo(b) <= 0;

    public static bool operator >=(AppVersion a, AppVersion b) => a.CompareTo(b) >= 0;

    public override string ToString() => PreRelease is null
        ? Release.ToString(3)
        : string.Create(CultureInfo.InvariantCulture, $"{Release.ToString(3)}-{PreRelease}");

    // SemVer: dot-separated identifiers, numbers numerically and below words, fewer identifiers first.
    private static int ComparePreRelease(string a, string b)
    {
        var left = a.Split('.');
        var right = b.Split('.');
        for (var i = 0; i < Math.Min(left.Length, right.Length); i++)
        {
            var leftNumber = int.TryParse(left[i], NumberStyles.None, CultureInfo.InvariantCulture, out var l);
            var rightNumber = int.TryParse(right[i], NumberStyles.None, CultureInfo.InvariantCulture, out var r);
            var order = (leftNumber, rightNumber) switch
            {
                (true, true) => l.CompareTo(r),
                (true, false) => -1,
                (false, true) => 1,
                _ => string.CompareOrdinal(left[i], right[i]),
            };
            if (order != 0)
            {
                return order;
            }
        }

        return left.Length.CompareTo(right.Length);
    }
}
