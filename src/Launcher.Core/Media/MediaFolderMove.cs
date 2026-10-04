namespace Launcher.Core.Media;

/// <summary>A file in the media folder: its path under the folder (the OS's separators) and its size.</summary>
public readonly record struct MediaMoveFile(string RelativePath, long SizeBytes);

/// <summary>What moving the media folder takes on (<see cref="MediaFolderMove.Plan"/>).</summary>
/// <param name="From">The media folder now, in full.</param>
/// <param name="To">The folder it moves to, in full.</param>
/// <param name="Files">Every file in it, hidden and system files left out (they aren't media), in ordinal order.</param>
/// <param name="SameVolume">
/// Both are on one volume: each file is renamed, at once. Otherwise each is copied, and the originals are deleted only
/// once the new folder is in use (<see cref="MediaMove.Finish"/>), so until then the old folder is whole.
/// </param>
public sealed record MediaMovePlan(string From, string To, IReadOnlyList<MediaMoveFile> Files, long Bytes, bool SameVolume);

/// <summary>How far a move has got.</summary>
public readonly record struct MediaMoveProgress(int Files, int TotalFiles, long Bytes, long TotalBytes);

/// <summary>
/// Moves the media folder's files to another folder (A4, 2026-10-04: Settings > Media folder). Stored paths don't name
/// the folder (<see cref="MediaFolder"/>), so the library's rows and the derivatives stay as they are: a file keeps its
/// path under the folder, and its modification time. Does file I/O: never on the main thread.
/// <para>
/// The caller moves (<see cref="Move"/>), then saves the new folder in settings.toml, then calls
/// <see cref="MediaMove.Finish"/>; if the save fails, <see cref="MediaMove.Undo"/> puts everything back. A cancelled or
/// failed move puts back what it had moved before it throws.
/// </para>
/// </summary>
public static class MediaFolderMove
{
    /// <summary>How many times a file is tried, a moment apart (a reader such as the derivative baker can hold it briefly).</summary>
    internal const int Attempts = 3;

    /// <summary>Why the media folder can't move from <paramref name="from"/> to <paramref name="to"/>, or null.</summary>
    public static string? Problem(string from, string to)
    {
        ArgumentNullException.ThrowIfNull(from);
        ArgumentNullException.ThrowIfNull(to);
        if (!Path.IsPathFullyQualified(to))
        {
            return $"'{to}' isn't a full path.";
        }

        if (MediaFolder.Same(from, to))
        {
            return "That's the media folder already.";
        }

        if (MediaFolder.Inside(to, from))
        {
            return $"'{to}' is inside the media folder. Choose a folder outside it.";
        }

        if (MediaFolder.Inside(from, to))
        {
            return $"The media folder is inside '{to}'. Choose a folder of its own for the media, such as a new folder in that one.";
        }

        return null;
    }

    /// <summary>Lists the files to move. A media folder that doesn't exist has none.</summary>
    public static MediaMovePlan Plan(string from, string to, CancellationToken cancellationToken)
    {
        var source = MediaFolder.Normalise(from);
        var target = MediaFolder.Normalise(to);
        var files = new List<MediaMoveFile>();
        long bytes = 0;
        if (Directory.Exists(source))
        {
            var options = new EnumerationOptions
            {
                RecurseSubdirectories = true,
                IgnoreInaccessible = true,
                AttributesToSkip = FileAttributes.Hidden | FileAttributes.System | FileAttributes.ReparsePoint,
                ReturnSpecialDirectories = false,
            };
            foreach (var file in new DirectoryInfo(source).EnumerateFiles("*", options))
            {
                cancellationToken.ThrowIfCancellationRequested();
                files.Add(new MediaMoveFile(Path.GetRelativePath(source, file.FullName), file.Length));
                bytes += file.Length;
            }
        }

        files.Sort(static (a, b) => string.CompareOrdinal(a.RelativePath, b.RelativePath));
        var sameVolume = string.Equals(Path.GetPathRoot(source), Path.GetPathRoot(target), MediaFolder.PathComparison);
        return new MediaMovePlan(source, target, files, bytes, sameVolume);
    }

    /// <summary>
    /// Moves (or copies) every planned file into <see cref="MediaMovePlan.To"/>, keeping its path under the folder. A
    /// file the new folder already has stays where it is, and the new folder's is kept
    /// (<see cref="MediaMove.AlreadyThere"/>); one that's gone meanwhile is skipped.
    /// </summary>
    /// <exception cref="OperationCanceledException">Cancelled: what was moved has been put back.</exception>
    /// <exception cref="IOException">A file couldn't be moved: what was moved has been put back.</exception>
    /// <exception cref="UnauthorizedAccessException">Likewise, for a file or folder Windows refused.</exception>
    public static MediaMove Move(MediaMovePlan plan, IProgress<MediaMoveProgress>? progress, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(plan);
        var move = new MediaMove(plan);
        long bytes = 0;
        try
        {
            Directory.CreateDirectory(plan.To);
            for (var i = 0; i < plan.Files.Count; i++)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var file = plan.Files[i];
                move.Transfer(file.RelativePath, cancellationToken);
                bytes += file.SizeBytes;
                progress?.Report(new MediaMoveProgress(i + 1, plan.Files.Count, bytes, plan.Bytes));
            }
        }
        catch
        {
            move.Undo();
            throw;
        }

        return move;
    }

    /// <summary>A file Windows wouldn't move because another program had it open (a sharing or lock violation), which a moment later may not.</summary>
    internal static bool InUse(IOException e) => (e.HResult & 0xFFFF) is 32 or 33;
}

/// <summary>A move made by <see cref="MediaFolderMove.Move"/>: finished once the new folder is in use, or undone.</summary>
public sealed class MediaMove
{
    private readonly List<(string Source, string Target)> _moved = [];
    private readonly List<string> _madeFolders = [];

    internal MediaMove(MediaMovePlan plan) => Plan = plan;

    public MediaMovePlan Plan { get; }

    /// <summary>Files now in the new folder.</summary>
    public int Moved => _moved.Count;

    /// <summary>Files the new folder had already, by the same path: the new folder's are kept, and these stay in the old one.</summary>
    public int AlreadyThere { get; private set; }

    /// <summary>Files gone from the old folder between the plan and the move.</summary>
    public int Gone { get; private set; }

    internal void Transfer(string relativePath, CancellationToken cancellationToken)
    {
        var source = Path.Combine(Plan.From, relativePath);
        var target = Path.Combine(Plan.To, relativePath);
        if (File.Exists(target))
        {
            AlreadyThere++;
            return;
        }

        if (!File.Exists(source))
        {
            Gone++;
            return;
        }

        MakeFolder(Path.GetDirectoryName(target)!);
        for (var attempt = 1; ; attempt++)
        {
            try
            {
                if (Plan.SameVolume)
                {
                    File.Move(source, target, overwrite: false);
                }
                else
                {
                    Copy(source, target);
                }

                _moved.Add((source, target));
                return;
            }
            catch (IOException) when (File.Exists(target))
            {
                AlreadyThere++;
                return;
            }
            catch (IOException e) when (attempt < MediaFolderMove.Attempts && MediaFolderMove.InUse(e))
            {
                cancellationToken.WaitHandle.WaitOne(250);
                cancellationToken.ThrowIfCancellationRequested();
            }
        }
    }

    /// <summary>
    /// Puts back what was moved (renamed back, or the copies deleted) and removes the folders the move made, if empty.
    /// </summary>
    /// <returns>Files that couldn't be put back (they're in the new folder still).</returns>
    public int Undo()
    {
        var failed = 0;
        for (var i = _moved.Count - 1; i >= 0; i--)
        {
            var (source, target) = _moved[i];
            try
            {
                if (Plan.SameVolume)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(source)!);
                    File.Move(target, source, overwrite: false);
                }
                else
                {
                    File.Delete(target);
                }

                _moved.RemoveAt(i);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                failed++;
            }
        }

        for (var i = _madeFolders.Count - 1; i >= 0; i--)
        {
            TryRemoveEmpty(_madeFolders[i]);
        }

        return failed;
    }

    /// <summary>
    /// Once the new folder is in use: deletes the originals of copied files, then the old folder's subfolders left
    /// empty (the folder itself stays).
    /// </summary>
    /// <returns>Originals that couldn't be deleted (they stay in the old folder, unused).</returns>
    public int Finish()
    {
        var failed = 0;
        if (!Plan.SameVolume)
        {
            foreach (var (source, _) in _moved)
            {
                try
                {
                    File.Delete(source);
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException)
                {
                    failed++;
                }
            }
        }

        if (Directory.Exists(Plan.From))
        {
            var folders = Directory.GetDirectories(Plan.From, "*", new EnumerationOptions { RecurseSubdirectories = true, IgnoreInaccessible = true, AttributesToSkip = FileAttributes.ReparsePoint });
            Array.Sort(folders, static (a, b) => b.Length.CompareTo(a.Length));
            foreach (var folder in folders)
            {
                TryRemoveEmpty(folder);
            }
        }

        return failed;
    }

    /// <summary>Copies to a temporary file beside the target, with the source's modification time (a derivative's key has it), then moves it in place.</summary>
    private static void Copy(string source, string target)
    {
        var temporary = target + ".moving";
        try
        {
            File.Copy(source, temporary, overwrite: true);
            File.SetLastWriteTimeUtc(temporary, File.GetLastWriteTimeUtc(source));
            File.Move(temporary, target, overwrite: false);
        }
        catch
        {
            File.Delete(temporary);
            throw;
        }
    }

    /// <summary>Creates a folder and those above it, noting each one made, so an undo can remove them.</summary>
    private void MakeFolder(string folder)
    {
        if (Directory.Exists(folder))
        {
            return;
        }

        if (Path.GetDirectoryName(folder) is { } parent)
        {
            MakeFolder(parent);
        }

        Directory.CreateDirectory(folder);
        _madeFolders.Add(folder);
    }

    private static void TryRemoveEmpty(string folder)
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
            // A folder something else is using stays.
        }
    }
}
