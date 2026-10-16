namespace Launcher.Core.Theming.Downloads;

/// <summary>A download's progress: git objects received of the total, and bytes.</summary>
public readonly record struct GitProgress(int ReceivedObjects, int TotalObjects, long ReceivedBytes)
{
    /// <summary>0 to 1; 0 until the total is known.</summary>
    public double Fraction => TotalObjects > 0 ? (double)ReceivedObjects / TotalObjects : 0;
}

/// <summary>A git operation that failed, with a message written for the user.</summary>
public sealed class GitException : Exception
{
    public GitException()
    {
    }

    public GitException(string message)
        : base(message)
    {
    }

    public GitException(string message, Exception inner)
        : base(message, inner)
    {
    }
}

/// <summary>
/// The git operations theme downloads need (A6 Downloading themes). Every call is synchronous and does network or file
/// I/O: never on the main thread. Failures are <see cref="GitException"/>s; a cancelled transfer throws
/// <see cref="OperationCanceledException"/>.
/// </summary>
public interface IGitClient
{
    /// <summary>Whether the folder is the top of a git working tree.</summary>
    bool IsRepository(string folder);

    /// <summary>
    /// Clones <paramref name="url"/> into <paramref name="folder"/> (which mustn't exist, or be empty), checking nothing
    /// out: <see cref="CheckOut"/> or <see cref="ResetToRemote"/> does, with line endings as committed whatever the user's
    /// git settings.
    /// </summary>
    void Clone(string url, string folder, IProgress<GitProgress>? progress, CancellationToken cancellation);

    /// <summary>Fetches every branch and tag from <c>origin</c>.</summary>
    void Fetch(string folder, IProgress<GitProgress>? progress, CancellationToken cancellation);

    /// <summary>The commit checked out, lower-case; null for none (an empty repository).</summary>
    string? HeadCommit(string folder);

    /// <summary><c>origin</c>'s URL; null for none.</summary>
    string? OriginUrl(string folder);

    /// <summary>Whether the repository has the commit.</summary>
    bool HasCommit(string folder, string commit);

    /// <summary>Whether a tracked file was changed or deleted. Files git doesn't track are ignored, as ES-DE does.</summary>
    bool HasLocalChanges(string folder);

    /// <summary>Whether the checked-out commit has any files (an interrupted clone has none).</summary>
    bool HasTrackedFiles(string folder);

    /// <summary>Checks the commit out, detached, overwriting changes to tracked files (untracked files stay).</summary>
    void CheckOut(string folder, string commit);

    /// <summary>
    /// Discards changes to tracked files and moves the checked-out branch to its <c>origin</c> branch's tip (after a
    /// <see cref="Fetch"/>): the theme list's refresh.
    /// </summary>
    void ResetToRemote(string folder);
}
