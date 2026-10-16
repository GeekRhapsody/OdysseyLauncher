using System.Globalization;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Platform;

namespace Launcher.Core.Theming.Downloads;

/// <summary>Where theme downloads keep their files (A6 Downloading themes).</summary>
/// <param name="ThemesDir"><c>ConfigDir/themes</c>: installed themes, where <see cref="ThemeCatalog"/> finds them.</param>
/// <param name="StagingDir">
/// <c>ConfigDir/themes-staging</c>: clones in progress, beside the themes folder (one volume, so moving one in is a
/// rename) but outside it, so an interrupted clone is never loaded as a theme.
/// </param>
/// <param name="BackupsDir"><c>DataDir/theme-backups</c>: themes a download replaced, outside the themes folder so they aren't loaded.</param>
/// <param name="ListDir"><c>CacheDir/themes-list</c>: the theme list's clone.</param>
public sealed record ThemeDownloadPaths(string ThemesDir, string StagingDir, string BackupsDir, string ListDir)
{
    public static ThemeDownloadPaths For(IPlatformPaths paths)
    {
        ArgumentNullException.ThrowIfNull(paths);
        return new ThemeDownloadPaths(
            Path.Combine(paths.ConfigDir, ThemeLoader.FolderName),
            Path.Combine(paths.ConfigDir, "themes-staging"),
            Path.Combine(paths.DataDir, "theme-backups"),
            Path.Combine(paths.CacheDir, "themes-list"));
    }
}

/// <summary>The list, and what the user has of each theme on it.</summary>
/// <param name="RefreshProblem">Why the list couldn't be brought up to date (offline): what's shown is the copy from last time.</param>
/// <param name="Refreshed">Whether the list was fetched just now.</param>
public sealed record ThemeListResult(ThemeIndex Index, IReadOnlyList<ThemeStatus> Themes, string? RefreshProblem, bool Refreshed)
{
    /// <summary>Whether the launcher is older than the list's latest release (ES-DE's warning).</summary>
    public bool AppOutdated(AppVersion? app) =>
        app is { } current && Index.LatestAppVersion is { } text && AppVersion.TryParse(text, out var latest) && current < latest;
}

/// <param name="Diagnostics">The theme's manifest's problems, as the app will report them.</param>
/// <param name="BackupFolder">Where a theme the install replaced was moved; null when nothing was.</param>
public sealed record ThemeOperationResult(ThemeStatus Status, IReadOnlyList<Diagnostic> Diagnostics, string? BackupFolder = null);

/// <summary>
/// The theme downloader (A6 Downloading themes), as ES-DE's: a curated list in a git repository (<c>themes.json</c> and
/// screenshots), cloned into the cache and refreshed when the downloader opens, and each listed theme a git clone in
/// <c>ConfigDir/themes/&lt;id&gt;/</c>. Unlike ES-DE's, each entry pins a commit, so a theme changes only when the list's
/// owner, who tests each one, moves it. One operation at a time; every method does I/O on the thread pool.
/// </summary>
public sealed class ThemeDownloads
{
    public const string DefaultListUrl = "https://github.com/GeekRhapsody/odyssey-themes.git";

    private readonly IGitClient _git;
    private readonly IReadOnlyCollection<string> _reservedIds;
    private readonly ILog _log;
    private readonly string _listUrl;
    private readonly string? _localList;
    private readonly TimeProvider _clock;
    private readonly SemaphoreSlim _gate = new(1, 1);

    /// <param name="reservedIds">The built-in themes' ids, which a listed theme can't take.</param>
    /// <param name="localList">A folder to read the list from as it is, never fetched (<c>--themes-list</c>, tests and captures).</param>
    /// <param name="appVersion">The running launcher's, for <c>min_app_version</c>; null to accept any.</param>
    public ThemeDownloads(
        IGitClient git,
        ThemeDownloadPaths paths,
        IReadOnlyCollection<string> reservedIds,
        ILog log,
        string? listUrl = null,
        string? localList = null,
        AppVersion? appVersion = null,
        TimeProvider? clock = null)
    {
        ArgumentNullException.ThrowIfNull(git);
        ArgumentNullException.ThrowIfNull(paths);
        ArgumentNullException.ThrowIfNull(reservedIds);
        ArgumentNullException.ThrowIfNull(log);
        _git = git;
        Paths = paths;
        _reservedIds = reservedIds;
        _log = log;
        _listUrl = listUrl ?? DefaultListUrl;
        _localList = localList;
        AppVersion = appVersion;
        _clock = clock ?? TimeProvider.System;
    }

    public ThemeDownloadPaths Paths { get; }

    public AppVersion? AppVersion { get; }

    /// <summary>The list's folder: the clone in the cache, or the local list.</summary>
    public string ListFolder => _localList ?? Paths.ListDir;

    /// <summary>The list as it was last fetched, without the network. Empty if it never was.</summary>
    public Task<ThemeListResult> ReadCachedAsync(CancellationToken cancellation = default) =>
        Task.Run(() => Read(null, refreshed: false), cancellation);

    /// <summary>
    /// Fetches the list (cloning it the first time; discarding any change to it, as ES-DE does), then reads it. Offline,
    /// it reads last time's copy and says why it couldn't refresh. Also clears clones a quit interrupted.
    /// </summary>
    public async Task<ThemeListResult> RefreshAsync(IProgress<GitProgress>? progress = null, CancellationToken cancellation = default)
    {
        await _gate.WaitAsync(cancellation).ConfigureAwait(false);
        try
        {
            return await Task.Run(() =>
            {
                ClearStaging();
                if (_localList is not null)
                {
                    return Read(null, refreshed: false);
                }

                string? problem = null;
                try
                {
                    RefreshList(progress, cancellation);
                }
                catch (GitException e)
                {
                    problem = e.Message;
                    _log.Write(LogLevel.Warning, $"Themes: couldn't refresh the theme list from {_listUrl}: {e.Message}");
                }
                catch (IOException e)
                {
                    problem = e.Message;
                    _log.Write(LogLevel.Warning, $"Themes: couldn't refresh the theme list: {e.Message}");
                }

                return Read(problem, refreshed: problem is null);
            }, cancellation).ConfigureAwait(false);
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>What the user has of one listed theme now.</summary>
    public Task<ThemeStatus> InspectAsync(ThemeListing listing, CancellationToken cancellation = default) =>
        Task.Run(() => ThemeInventory.Inspect(_git, listing, Paths.ThemesDir, AppVersion), cancellation);

    /// <summary>
    /// Installs a listed theme: cloned into the staging folder, the pinned commit checked out, its manifest loaded over
    /// <paramref name="baseTheme"/> (refused if it can't be used at all), then moved into the themes folder. A folder of
    /// the theme's id already there (<see cref="ThemeInstallState.ManualInstall"/> or <see cref="ThemeInstallState.Broken"/>)
    /// is replaced only with <paramref name="replace"/>, after being moved to the backups folder.
    /// </summary>
    /// <exception cref="GitException">It couldn't be installed; the message is for the user. Nothing was changed.</exception>
    public async Task<ThemeOperationResult> InstallAsync(
        ThemeListing listing, Theme? baseTheme, bool replace, IProgress<GitProgress>? progress = null, CancellationToken cancellation = default)
    {
        ArgumentNullException.ThrowIfNull(listing);
        await _gate.WaitAsync(cancellation).ConfigureAwait(false);
        try
        {
            return await Task.Run(() => Install(listing, baseTheme, replace, progress, cancellation), cancellation).ConfigureAwait(false);
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>
    /// Brings an installed theme to the commit the list pins: fetched, then checked out (files git doesn't track stay).
    /// Changes to its tracked files are overwritten only with <paramref name="discardChanges"/>. A version whose manifest
    /// can't be used is refused, and the theme left as it was.
    /// </summary>
    /// <exception cref="GitException">It couldn't be updated; the message is for the user.</exception>
    public async Task<ThemeOperationResult> UpdateAsync(
        ThemeListing listing, Theme? baseTheme, bool discardChanges, IProgress<GitProgress>? progress = null, CancellationToken cancellation = default)
    {
        ArgumentNullException.ThrowIfNull(listing);
        await _gate.WaitAsync(cancellation).ConfigureAwait(false);
        try
        {
            return await Task.Run(() => Update(listing, baseTheme, discardChanges, progress, cancellation), cancellation).ConfigureAwait(false);
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Deletes an installed theme's folder. The caller switches away from it first if it's in use.</summary>
    /// <exception cref="GitException">It couldn't be deleted; the message is for the user.</exception>
    public async Task<ThemeStatus> RemoveAsync(ThemeListing listing, CancellationToken cancellation = default)
    {
        ArgumentNullException.ThrowIfNull(listing);
        await _gate.WaitAsync(cancellation).ConfigureAwait(false);
        try
        {
            return await Task.Run(() =>
            {
                var folder = ThemeFolder(listing.Id);
                try
                {
                    FolderTree.Delete(folder);
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException)
                {
                    throw new GitException($"Couldn't delete {folder}: {e.Message}", e);
                }

                _log.Write(LogLevel.Info, $"Themes: removed '{listing.Id}' ({folder})");
                return ThemeInventory.Inspect(_git, listing, Paths.ThemesDir, AppVersion);
            }, cancellation).ConfigureAwait(false);
        }
        finally
        {
            _gate.Release();
        }
    }

    /// <summary>Deletes clones a quit or a failure left in the staging folder.</summary>
    public void ClearStaging()
    {
        try
        {
            FolderTree.Delete(Paths.StagingDir);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            _log.Write(LogLevel.Warning, $"Themes: couldn't clear {Paths.StagingDir}: {e.Message}");
        }
    }

    private ThemeListResult Read(string? refreshProblem, bool refreshed)
    {
        var file = Path.Combine(ListFolder, ThemeIndexReader.FileName);
        ThemeIndex index;
        if (!File.Exists(file))
        {
            index = ThemeIndex.Empty([]);
            refreshProblem ??= _localList is null ? null : $"{file} doesn't exist";
        }
        else
        {
            try
            {
                index = ThemeIndexReader.Read(File.ReadAllText(file), file, ListFolder, _reservedIds, allowFileUrls: _localList is not null);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                index = ThemeIndex.Empty([new Diagnostic(Severity.Error, file, 0, 0, string.Empty, $"couldn't be read: {e.Message}")]);
            }
        }

        foreach (var diagnostic in index.Diagnostics)
        {
            _log.Write(diagnostic.IsError ? LogLevel.Error : LogLevel.Warning, $"Themes: {diagnostic}");
        }

        var statuses = index.Themes.Select(t => ThemeInventory.Inspect(_git, t, Paths.ThemesDir, AppVersion)).ToList();
        return new ThemeListResult(index, statuses, refreshProblem, refreshed);
    }

    private void RefreshList(IProgress<GitProgress>? progress, CancellationToken cancellation)
    {
        var folder = Paths.ListDir;
        if (_git.IsRepository(folder) && ThemeInventory.SameRepository(_git.OriginUrl(folder), _listUrl))
        {
            try
            {
                _git.Fetch(folder, progress, cancellation);
                _git.ResetToRemote(folder);
                return;
            }
            catch (GitException e) when (_git.HeadCommit(folder) is null || !_git.HasTrackedFiles(folder))
            {
                // A broken clone: cloned again below.
                _log.Write(LogLevel.Warning, $"Themes: the theme list's clone is broken ({e.Message}), so it's cloned again");
            }
        }

        // Cloned beside the old copy, which stays until the new one is complete.
        var fresh = folder + "-new";
        FolderTree.Delete(fresh);
        try
        {
            _git.Clone(_listUrl, fresh, progress, cancellation);
            _git.ResetToRemote(fresh);
        }
        catch
        {
            TryDelete(fresh);
            throw;
        }

        FolderTree.Delete(folder);
        Directory.Move(fresh, folder);
        _log.Write(LogLevel.Info, $"Themes: cloned the theme list from {_listUrl}");
    }

    private ThemeOperationResult Install(ThemeListing listing, Theme? baseTheme, bool replace, IProgress<GitProgress>? progress, CancellationToken cancellation)
    {
        var folder = ThemeFolder(listing.Id);
        var before = ThemeInventory.Inspect(_git, listing, Paths.ThemesDir, AppVersion);
        if (before.NeedsNewerApp)
        {
            throw new GitException($"{listing.Name} needs Odyssey Launcher {listing.MinAppVersion} or later");
        }

        if (before.IsInstalled)
        {
            return Update(listing, baseTheme, discardChanges: false, progress, cancellation);
        }

        if (before.State != ThemeInstallState.NotInstalled && !replace)
        {
            throw new GitException($"There's already a theme in {folder}");
        }

        var staging = Path.Combine(Paths.StagingDir, listing.Id);
        IReadOnlyList<Diagnostic> diagnostics;
        try
        {
            FolderTree.Delete(staging);
            Directory.CreateDirectory(Paths.StagingDir);
            _log.Write(LogLevel.Info, $"Themes: cloning '{listing.Id}' from {listing.Url}");
            _git.Clone(listing.Url, staging, progress, cancellation);
            _git.CheckOut(staging, listing.Commit);
            diagnostics = Check(listing, staging, baseTheme);
        }
        catch (Exception e) when (e is GitException or OperationCanceledException or IOException or UnauthorizedAccessException)
        {
            TryDelete(staging);
            RemoveIfEmpty(Paths.StagingDir);
            if (e is IOException or UnauthorizedAccessException)
            {
                throw new GitException(e.Message, e);
            }

            throw;
        }

        string? backup = null;
        try
        {
            if (Directory.Exists(folder))
            {
                backup = BackupFolder(listing.Id);
                FolderTree.Move(folder, backup);
                _log.Write(LogLevel.Info, $"Themes: moved the old '{listing.Id}' to {backup}");
            }

            Directory.CreateDirectory(Paths.ThemesDir);
            Directory.Move(staging, folder);
            RemoveIfEmpty(Paths.StagingDir);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            TryDelete(staging);
            throw new GitException($"Couldn't move the theme into {folder}: {e.Message}", e);
        }

        _log.Write(LogLevel.Info, $"Themes: installed '{listing.Id}' at {listing.ShortCommit}");
        return new ThemeOperationResult(ThemeInventory.Inspect(_git, listing, Paths.ThemesDir, AppVersion), diagnostics, backup);
    }

    private ThemeOperationResult Update(ThemeListing listing, Theme? baseTheme, bool discardChanges, IProgress<GitProgress>? progress, CancellationToken cancellation)
    {
        var folder = ThemeFolder(listing.Id);
        var before = ThemeInventory.Inspect(_git, listing, Paths.ThemesDir, AppVersion);
        if (!before.IsInstalled)
        {
            throw new GitException($"{listing.Name} isn't installed");
        }

        if (before.NeedsNewerApp)
        {
            throw new GitException($"This version of {listing.Name} needs Odyssey Launcher {listing.MinAppVersion} or later");
        }

        if (before.LocalChanges && !discardChanges)
        {
            throw new GitException($"{listing.Name} has changes of your own, which updating would overwrite");
        }

        if (!before.UpdateAvailable && !before.LocalChanges)
        {
            return new ThemeOperationResult(before, []);
        }

        try
        {
            if (!_git.HasCommit(folder, listing.Commit))
            {
                _log.Write(LogLevel.Info, $"Themes: fetching '{listing.Id}' from {listing.Url}");
                _git.Fetch(folder, progress, cancellation);
            }

            _git.CheckOut(folder, listing.Commit);
            IReadOnlyList<Diagnostic> diagnostics;
            try
            {
                diagnostics = Check(listing, folder, baseTheme);
            }
            catch (GitException) when (before.InstalledCommit is { } old)
            {
                _git.CheckOut(folder, old);
                throw;
            }

            _log.Write(LogLevel.Info, $"Themes: updated '{listing.Id}' from {before.InstalledCommit?[..7]} to {listing.ShortCommit}");
            return new ThemeOperationResult(ThemeInventory.Inspect(_git, listing, Paths.ThemesDir, AppVersion), diagnostics);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            throw new GitException(e.Message, e);
        }
    }

    // The theme as the app will load it: refused only if it can't be used at all (the owner tested it, so a problem
    // here is a launcher too old for it, or a damaged download).
    private static IReadOnlyList<Diagnostic> Check(ThemeListing listing, string folder, Theme? baseTheme)
    {
        var manifest = Path.Combine(folder, ThemeLoader.ManifestFileName);
        if (!File.Exists(manifest))
        {
            throw new GitException($"{listing.Name}'s repository has no {ThemeLoader.ManifestFileName} at its top");
        }

        if (baseTheme is null)
        {
            return [];
        }

        var source = new ThemeSource(listing.Id, new ConfigFile(manifest, File.ReadAllText(manifest)), ThemeOrigin.User, folder, new FolderThemeFiles(folder));
        var result = ThemeLoader.Load(source, baseTheme);
        if (result.Theme is null)
        {
            var first = result.Diagnostics.FirstOrDefault(d => d.IsError)?.ToString() ?? "it can't be loaded";
            throw new GitException($"{listing.Name} can't be used by this version of the launcher: {first}");
        }

        return result.Diagnostics;
    }

    private string ThemeFolder(string id)
    {
        if (!TomlValidator.IsValidId(id) || _reservedIds.Contains(id))
        {
            throw new GitException($"'{id}' can't be a downloaded theme's id");
        }

        return Path.Combine(Paths.ThemesDir, id);
    }

    private string BackupFolder(string id)
    {
        var stamp = _clock.GetLocalNow().ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        var folder = Path.Combine(Paths.BackupsDir, $"{id}-{stamp}");
        for (var n = 2; Directory.Exists(folder); n++)
        {
            folder = Path.Combine(Paths.BackupsDir, string.Create(CultureInfo.InvariantCulture, $"{id}-{stamp}-{n}"));
        }

        return folder;
    }

    private static void RemoveIfEmpty(string folder)
    {
        try
        {
            if (Directory.Exists(folder) && !Directory.EnumerateFileSystemEntries(folder).Any())
            {
                Directory.Delete(folder);
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // Cleared the next time the downloader opens.
        }
    }

    private void TryDelete(string folder)
    {
        try
        {
            FolderTree.Delete(folder);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            _log.Write(LogLevel.Warning, $"Themes: couldn't delete {folder}: {e.Message}");
        }
    }
}
