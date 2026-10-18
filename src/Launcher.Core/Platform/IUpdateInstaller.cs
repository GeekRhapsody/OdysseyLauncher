namespace Launcher.Core.Platform;

/// <summary>
/// Everything the helper needs to install a staged update once the launcher has quit: the launcher's process to wait for,
/// the folder to install into and the new files, where the old ones wait until the new ones are in, and how to start the
/// launcher again (its executable, with the arguments and working folder it ran with). <see cref="MoveAttempts"/> is how
/// many times each move is tried, half a second apart, before the update is undone.
/// </summary>
public sealed record UpdateHandover(
    int ProcessId,
    string InstallDir,
    string PackageDir,
    string BackupDir,
    string StagingDir,
    string Executable,
    IReadOnlyList<string> Arguments,
    string WorkingDirectory,
    string LogFile,
    int MoveAttempts = 20);

/// <summary>
/// Installs a staged update (docs/ARCHITECTURE.md A1 <c>Updates</c>). The launcher's own files are open while it runs
/// (its executable, its PCK, the .NET assemblies), so a helper program waits for it to quit, moves each of the package's
/// files and folders into the launcher's folder (the old ones aside first, and back if anything fails), starts the
/// launcher again, and deletes the staging folder.
/// </summary>
public interface IUpdateInstaller
{
    /// <summary>The packages this platform installs (<c>windows-x86_64</c>), or null when it can't update itself.</summary>
    string? Platform { get; }

    /// <summary>The helper program a package must bring (<c>OdysseyUpdater.exe</c>), so the next update can be installed too; null for none.</summary>
    string? HelperName { get; }

    /// <summary>
    /// Starts the helper: null once it's running (the caller then quits at once, and the helper waits for that), else
    /// why it couldn't start, for the user.
    /// </summary>
    string? Start(UpdateHandover handover);
}

/// <summary>Linux, until it's worth doing: no updates.</summary>
public sealed class NullUpdateInstaller : IUpdateInstaller
{
    public static NullUpdateInstaller Instance { get; } = new();

    public string? Platform => null;

    public string? HelperName => null;

    public string? Start(UpdateHandover handover) => "The launcher can't update itself on this platform yet.";
}
