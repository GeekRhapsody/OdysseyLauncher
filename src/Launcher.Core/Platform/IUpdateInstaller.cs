using Launcher.Core.Updates;

namespace Launcher.Core.Platform;

/// <summary>
/// Everything the installer needs to install a staged update once the launcher has quit: the launcher's process to wait
/// for, the folder to install into and the new version (<see cref="Package"/>: a folder of files, or the new
/// <c>.AppImage</c>), where the old files wait until the new ones are in, and how to start the launcher again (the file
/// <see cref="IUpdateInstaller.Target"/> gives, with the arguments and working folder it ran with).
/// <see cref="MoveAttempts"/> is how many times each move is tried, half a second apart, before the update is undone.
/// </summary>
public sealed record UpdateHandover(
    int ProcessId,
    string InstallDir,
    string Package,
    string BackupDir,
    string StagingDir,
    string Executable,
    IReadOnlyList<string> Arguments,
    string WorkingDirectory,
    string LogFile,
    int MoveAttempts = 20);

/// <summary>
/// Installs a staged update (docs/ARCHITECTURE.md A1 <c>Updates</c>). On Windows the launcher's own files are open while
/// it runs (its executable, its PCK, the .NET assemblies), so a helper program waits for it to quit, moves each of the
/// package's files and folders into the launcher's folder (the old ones aside first, and back if anything fails), starts
/// the launcher again, and deletes the staging folder. On Linux the new <c>.AppImage</c> is renamed over the running one
/// and started once the launcher has quit.
/// </summary>
public interface IUpdateInstaller
{
    /// <summary>The packages this platform installs (<c>windows-x86_64</c>), or null when it can't update itself.</summary>
    string? Platform { get; }

    /// <summary>What those packages are.</summary>
    UpdatePackage Package { get; }

    /// <summary>The helper program a package must bring (<c>OdysseyUpdater.exe</c>), so the next update can be installed too; null for none.</summary>
    string? HelperName { get; }

    /// <summary>
    /// The file an update replaces and starts again, for the launcher running from <paramref name="executable"/>: the
    /// executable (Windows) or the <c>.AppImage</c> it runs from (Linux). Null when this run can't be updated, with
    /// why in <paramref name="problem"/>, for the user.
    /// </summary>
    string? Target(string executable, out string? problem);

    /// <summary>
    /// Starts the helper: null once it's running (the caller then quits at once, and the helper waits for that), else
    /// why it couldn't start, for the user.
    /// </summary>
    string? Start(UpdateHandover handover);
}

/// <summary>Any other OS: no updates.</summary>
public sealed class NullUpdateInstaller : IUpdateInstaller
{
    private const string Problem = "The launcher can't update itself on this platform yet.";

    public static NullUpdateInstaller Instance { get; } = new();

    public string? Platform => null;

    public UpdatePackage Package => UpdatePackage.Zip;

    public string? HelperName => null;

    public string? Target(string executable, out string? problem)
    {
        problem = Problem;
        return null;
    }

    public string? Start(UpdateHandover handover) => Problem;
}
