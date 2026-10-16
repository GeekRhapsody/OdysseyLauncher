namespace Launcher.Core.Theming.Downloads;

/// <summary>What's in a listed theme's folder, <c>ConfigDir/themes/&lt;id&gt;/</c>.</summary>
public enum ThemeInstallState
{
    NotInstalled,

    /// <summary>A clone of the listed repository.</summary>
    Installed,

    /// <summary>
    /// A theme of that id the downloader didn't put there: not a repository, or a clone of another one (ES-DE's manual
    /// download and wrong URL). Installing replaces it, after moving it to the backups folder.
    /// </summary>
    ManualInstall,

    /// <summary>A repository with no files (an interrupted clone, ES-DE's corrupt repository). Installing replaces it.</summary>
    Broken,
}

/// <summary>A listed theme and what the user has of it.</summary>
/// <param name="InstalledCommit">The commit checked out, for <see cref="ThemeInstallState.Installed"/>.</param>
/// <param name="UpdateAvailable">Installed, at another commit than the list pins.</param>
/// <param name="LocalChanges">Installed, with tracked files changed: updating would overwrite them.</param>
/// <param name="NeedsNewerApp">The theme's <c>min_app_version</c> is above the running launcher's.</param>
/// <param name="Problem">Why the folder couldn't be read, when it couldn't.</param>
public sealed record ThemeStatus(
    ThemeListing Listing,
    ThemeInstallState State,
    string? InstalledCommit,
    bool UpdateAvailable,
    bool LocalChanges,
    bool NeedsNewerApp,
    string? Problem = null)
{
    public bool IsInstalled => State == ThemeInstallState.Installed;
}

/// <summary>
/// Compares the list with the user's themes folder (A6 Downloading themes). Offline: an update is a pinned commit the
/// clone isn't at, which ES-DE can only learn by fetching. Does file I/O: never on the main thread.
/// </summary>
public static class ThemeInventory
{
    public static ThemeStatus Inspect(IGitClient git, ThemeListing listing, string themesDir, AppVersion? appVersion)
    {
        ArgumentNullException.ThrowIfNull(git);
        ArgumentNullException.ThrowIfNull(listing);
        ArgumentNullException.ThrowIfNull(themesDir);
        var needsNewer = appVersion is { } app && listing.MinAppVersion is { } text && AppVersion.TryParse(text, out var min) && app < min;
        var folder = Path.Combine(themesDir, listing.Id);
        if (!Directory.Exists(folder))
        {
            return new ThemeStatus(listing, ThemeInstallState.NotInstalled, null, false, false, needsNewer);
        }

        try
        {
            if (!git.IsRepository(folder) || !SameRepository(git.OriginUrl(folder), listing.Url))
            {
                return new ThemeStatus(listing, ThemeInstallState.ManualInstall, null, false, false, needsNewer);
            }

            var head = git.HeadCommit(folder);
            if (head is null || !git.HasTrackedFiles(folder))
            {
                return new ThemeStatus(listing, ThemeInstallState.Broken, head, false, false, needsNewer);
            }

            return new ThemeStatus(
                listing,
                ThemeInstallState.Installed,
                head,
                !head.Equals(listing.Commit, StringComparison.OrdinalIgnoreCase),
                git.HasLocalChanges(folder),
                needsNewer);
        }
        catch (GitException e)
        {
            return new ThemeStatus(listing, ThemeInstallState.Broken, null, false, false, needsNewer, e.Message);
        }
    }

    /// <summary>Whether two git URLs name one repository: ignoring case, a trailing <c>/</c> and <c>.git</c>.</summary>
    public static bool SameRepository(string? a, string? b)
    {
        if (a is null || b is null)
        {
            return false;
        }

        return Normalise(a).Equals(Normalise(b), StringComparison.OrdinalIgnoreCase);

        static string Normalise(string url)
        {
            var trimmed = url.Trim().TrimEnd('/', '\\');
            return trimmed.EndsWith(".git", StringComparison.OrdinalIgnoreCase) ? trimmed[..^4] : trimmed;
        }
    }
}
