using System.Globalization;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Launcher.Core.Diagnostics;
using Launcher.Core.Theming.Downloads;

namespace Launcher.Core.Updates;

/// <summary>What a check found: the running version, and the release to offer (null when it's the newest).</summary>
public sealed record UpdateCheck(AppVersion Current, UpdateRelease? Available);

public enum UpdateStage
{
    Downloading,
    Verifying,
    Extracting,
}

/// <summary>A download's progress: bytes received (or files extracted) of the total, 0 while it isn't known.</summary>
public readonly record struct UpdateProgress(UpdateStage Stage, long Done, long Total);

/// <summary>
/// A release downloaded, checked and unpacked beside the installed launcher, ready for <see cref="Platform.IUpdateInstaller"/>:
/// <see cref="PackageDir"/> holds the new version's files as the zip's one folder has them.
/// </summary>
public sealed record StagedUpdate(UpdateRelease Release, string StagingDir, string PackageDir, string BackupDir);

/// <summary>
/// Checks for a newer launcher and downloads it (2026-10-18, docs/ARCHITECTURE.md A1 <c>Updates</c>): the releases list
/// from <see cref="IReleaseSource"/>, the newest release newer than this one with a package for this platform, and that
/// package downloaded into <c>&lt;install dir&gt;/.odyssey-update/</c> (beside the files it replaces, so the swap is a rename
/// on one volume), its SHA-256 checked against the release's, and unpacked there. Installing it is the platform's
/// (<see cref="Platform.IUpdateInstaller"/>), as the running files can't be replaced while the launcher runs. Thread pool.
/// </summary>
public sealed class UpdateService
{
    /// <summary>The folder beside the executable an update is downloaded and unpacked in, and the old files kept in until it's done.</summary>
    public const string StagingFolderName = ".odyssey-update";

    /// <summary>What a package may never contain: the user's files beside the executable, which an update keeps.</summary>
    public static readonly IReadOnlyList<string> KeptNames = [PlatformPathsMarker, "userdata", "override.cfg", StagingFolderName];

    /// <summary>
    /// What the installer leaves in the staging folder when it couldn't put the old version back whole: the old files
    /// that are still there wait in its <c>old</c> folder, so the staging folder is left alone and nothing is updated
    /// until the user has dealt with it.
    /// </summary>
    public const string IncompleteMarker = "incomplete.txt";

    private const string PlatformPathsMarker = Platform.PlatformPaths.PortableMarker;
    private const int BufferSize = 128 * 1024;

    private readonly IReleaseSource _source;
    private readonly string _platform;
    private readonly ILog _log;
    private readonly string? _helperName;

    /// <param name="installDir">The folder the running launcher's executable is in.</param>
    /// <param name="executableName">Its file name (<c>OdysseyLauncher.exe</c>): a package must have it, and its <c>.pck</c>.</param>
    /// <param name="platform">The packages' platform (<c>windows-x86_64</c>).</param>
    /// <param name="helperName">The installer's helper (<c>OdysseyUpdater.exe</c>), which a package must have too; null for none.</param>
    public UpdateService(IReleaseSource source, string installDir, string executableName, string platform, ILog log, string? helperName = null)
    {
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(installDir);
        ArgumentNullException.ThrowIfNull(executableName);
        ArgumentNullException.ThrowIfNull(platform);
        ArgumentNullException.ThrowIfNull(log);
        _source = source;
        InstallDir = Path.GetFullPath(installDir);
        ExecutableName = executableName;
        _platform = platform;
        _log = log;
        _helperName = helperName;
    }

    public string InstallDir { get; }

    public string ExecutableName { get; }

    public string StagingDir => Path.Combine(InstallDir, StagingFolderName);

    /// <summary>The newest release newer than <paramref name="current"/>. Throws <see cref="UpdateException"/>.</summary>
    public async Task<UpdateCheck> CheckAsync(AppVersion current, CancellationToken token = default)
    {
        var json = await _source.ReadReleasesAsync(token).ConfigureAwait(false);
        IReadOnlyList<UpdateRelease> releases;
        try
        {
            releases = ReleaseFeed.Parse(json, _platform, _source.BaseUri);
        }
        catch (JsonException e)
        {
            throw new UpdateException($"{_source.Name}'s list of releases couldn't be read.", e);
        }

        var newest = ReleaseFeed.Newest(releases, current);
        _log.Write(LogLevel.Info, newest is null
            ? $"Update: {current} is the newest ({releases.Count} release(s) for {_platform} on {_source.Name})."
            : $"Update: {newest.Version} is available ({current} running), {newest.Package.Url}.");
        return new UpdateCheck(current, newest);
    }

    /// <summary>
    /// Null when the launcher's folder can be written to (a file made and deleted there), else why not, for the user.
    /// A launcher unzipped into Program Files can't update itself without being run as an administrator.
    /// </summary>
    public string? CheckWritable()
    {
        var probe = Path.Combine(InstallDir, $".odyssey-write-test-{Environment.ProcessId.ToString(CultureInfo.InvariantCulture)}");
        try
        {
            File.WriteAllBytes(probe, []);
            File.Delete(probe);
            return null;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return $"The launcher's folder, {InstallDir}, can't be written to, so the launcher can't update itself there ({e.Message}).";
        }
    }

    /// <summary>
    /// Downloads <paramref name="release"/>'s package into the staging folder (what was there from an earlier try goes
    /// first), checks its SHA-256, and unpacks it. Throws <see cref="UpdateException"/>, or
    /// <see cref="OperationCanceledException"/>; either way, nothing installed is touched.
    /// </summary>
    public async Task<StagedUpdate> DownloadAsync(UpdateRelease release, IProgress<UpdateProgress>? progress = null, CancellationToken token = default)
    {
        ArgumentNullException.ThrowIfNull(release);
        var expected = release.Package.Sha256 ?? await ReadChecksumAsync(release, token).ConfigureAwait(false)
            ?? throw new UpdateException($"Release {release.Version} has no checksum to check its download against, so it isn't installed.");

        if (File.Exists(Path.Combine(StagingDir, IncompleteMarker)))
        {
            throw new UpdateException($"An earlier update couldn't put every file of the old version back, and they're in {Path.Combine(StagingDir, "old")}. Move them back into {InstallDir}, or download the launcher again from its release page, then delete {StagingDir}.");
        }

        await Task.Run(DeleteStaging, token).ConfigureAwait(false);
        try
        {
            // Hidden, as the launcher's own working folder: it's there while an update downloads, and briefly after.
            Directory.CreateDirectory(StagingDir).Attributes |= FileAttributes.Hidden;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            throw new UpdateException($"The update couldn't be saved in {InstallDir} ({e.Message}).", e);
        }

        var zip = Path.Combine(StagingDir, release.Package.Name);
        var hash = await DownloadFileAsync(release.Package, zip, progress, token).ConfigureAwait(false);
        progress?.Report(new UpdateProgress(UpdateStage.Verifying, 0, 0));
        if (!string.Equals(hash, expected, StringComparison.Ordinal))
        {
            TryDelete(zip);
            throw new UpdateException($"The download of {release.Version} doesn't match its checksum, so it isn't installed. Try again: it may have been damaged on the way.");
        }

        _log.Write(LogLevel.Info, $"Update: downloaded {release.Package.Name}, SHA-256 {hash} as published.");
        var unpacked = Path.Combine(StagingDir, "new");
        await Task.Run(() => Extract(zip, unpacked, progress, token), token).ConfigureAwait(false);
        TryDelete(zip);
        var package = FindPackageRoot(unpacked);
        _log.Write(LogLevel.Info, $"Update: {release.Version} unpacked in {package}.");
        return new StagedUpdate(release, StagingDir, package, Path.Combine(StagingDir, "old"));
    }

    /// <summary>
    /// Deletes the staging folder (an update cancelled, failed, or done but not cleared by the installer), unless the
    /// installer left old files in it (<see cref="IncompleteMarker"/>). Never throws.
    /// </summary>
    public void DeleteStaging()
    {
        if (File.Exists(Path.Combine(StagingDir, IncompleteMarker)))
        {
            _log.Write(LogLevel.Warning, $"Update: {StagingDir} holds old files an update couldn't put back, so it's kept.");
            return;
        }

        for (var attempt = 0; attempt < 3 && Directory.Exists(StagingDir); attempt++)
        {
            try
            {
                Directory.Delete(StagingDir, recursive: true);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                if (attempt == 2)
                {
                    _log.Write(LogLevel.Warning, $"Update: {StagingDir} couldn't be deleted: {e.Message}");
                }

                Thread.Sleep(100);
            }
        }
    }

    private async Task<string?> ReadChecksumAsync(UpdateRelease release, CancellationToken token)
    {
        if (release.Checksum is not { } file)
        {
            return null;
        }

        var (stream, _) = await _source.OpenAsync(file.Url, token).ConfigureAwait(false);
        await using (stream.ConfigureAwait(false))
        {
            using var reader = new StreamReader(stream, Encoding.UTF8);
            var buffer = new char[512];
            var read = await reader.ReadBlockAsync(buffer, token).ConfigureAwait(false);
            return Checksums.FromChecksumFile(new string(buffer, 0, read));
        }
    }

    /// <summary>Streams <paramref name="asset"/> to <paramref name="path"/>, hashing as it goes; returns the SHA-256.</summary>
    private async Task<string> DownloadFileAsync(UpdateAsset asset, string path, IProgress<UpdateProgress>? progress, CancellationToken token)
    {
        var (stream, length) = await _source.OpenAsync(asset.Url, token).ConfigureAwait(false);
        var total = length ?? asset.Size;
        long received = 0;
        using var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        await using (stream.ConfigureAwait(false))
        {
            var file = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None, BufferSize, useAsync: true);
            await using (file.ConfigureAwait(false))
            {
                var buffer = new byte[BufferSize];
                using var stall = CancellationTokenSource.CreateLinkedTokenSource(token);
                while (true)
                {
                    // Each read gets the timeout afresh: a slow download is fine, a stalled one isn't.
                    stall.CancelAfter(GitHubReleaseSource.Timeout);
                    int read;
                    try
                    {
                        read = await stream.ReadAsync(buffer, stall.Token).ConfigureAwait(false);
                    }
                    catch (OperationCanceledException) when (!token.IsCancellationRequested)
                    {
                        throw new UpdateException($"The download stopped arriving for {GitHubReleaseSource.Timeout.TotalSeconds:0} seconds. Check the network, then try again.");
                    }
                    catch (IOException e)
                    {
                        throw new UpdateException($"The download broke off ({e.Message}). Try again.", e);
                    }

                    if (read == 0)
                    {
                        break;
                    }

                    sha.AppendData(buffer, 0, read);
                    try
                    {
                        await file.WriteAsync(buffer.AsMemory(0, read), token).ConfigureAwait(false);
                    }
                    catch (IOException e)
                    {
                        throw new UpdateException($"The update couldn't be saved in {InstallDir} ({e.Message}).", e);
                    }

                    received += read;
                    progress?.Report(new UpdateProgress(UpdateStage.Downloading, received, Math.Max(total, received)));
                }
            }
        }

        if (total > 0 && received != total)
        {
            throw new UpdateException($"The download ended after {received:N0} of {total:N0} bytes. Try again.");
        }

        return Convert.ToHexString(sha.GetHashAndReset()).ToLowerInvariant();
    }

    /// <summary>Unpacks <paramref name="zip"/> into <paramref name="folder"/>, refusing any entry that would land outside it.</summary>
    internal static void Extract(string zip, string folder, IProgress<UpdateProgress>? progress, CancellationToken token)
    {
        var root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(folder)) + Path.DirectorySeparatorChar;
        try
        {
            using var archive = ZipFile.OpenRead(zip);
            var count = archive.Entries.Count;
            for (var i = 0; i < count; i++)
            {
                token.ThrowIfCancellationRequested();
                var entry = archive.Entries[i];
                var target = Path.GetFullPath(Path.Combine(root, entry.FullName));
                if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                {
                    throw new UpdateException($"The update's zip has a file outside its folder ({entry.FullName}), so it isn't installed.");
                }

                if (entry.FullName.EndsWith('/') || entry.FullName.EndsWith('\\'))
                {
                    Directory.CreateDirectory(target);
                }
                else
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(target)!);
                    entry.ExtractToFile(target, overwrite: false);
                }

                progress?.Report(new UpdateProgress(UpdateStage.Extracting, i + 1, count));
            }
        }
        catch (Exception e) when (e is InvalidDataException or IOException or UnauthorizedAccessException)
        {
            throw new UpdateException($"The update's zip couldn't be unpacked ({e.Message}).", e);
        }
    }

    /// <summary>
    /// The zip's one folder (the release workflow puts everything in a folder named after the package), or the unpacked
    /// folder itself, checked to hold the launcher and nothing an update must keep.
    /// </summary>
    internal string FindPackageRoot(string unpacked)
    {
        var folders = Directory.GetDirectories(unpacked);
        var root = folders.Length == 1 && Directory.GetFiles(unpacked).Length == 0 ? folders[0] : unpacked;
        var pck = Path.ChangeExtension(ExecutableName, ".pck");
        foreach (var needed in _helperName is null ? new[] { ExecutableName, pck } : [ExecutableName, pck, _helperName])
        {
            if (!File.Exists(Path.Combine(root, needed)))
            {
                throw new UpdateException($"The update has no {needed}, so it isn't installed.");
            }
        }

        foreach (var kept in KeptNames)
        {
            if (Path.Exists(Path.Combine(root, kept)))
            {
                throw new UpdateException($"The update has a {kept}, which would replace yours, so it isn't installed.");
            }
        }

        return root;
    }

    private static void TryDelete(string path)
    {
        try
        {
            File.Delete(path);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // The staging folder goes with it later.
        }
    }
}
