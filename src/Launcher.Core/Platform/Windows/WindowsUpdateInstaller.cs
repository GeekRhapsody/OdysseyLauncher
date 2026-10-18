using System.Globalization;
using System.Runtime.InteropServices;
using static Launcher.Core.Platform.Windows.NativeMethods;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Installs a staged update with <c>OdysseyUpdater.exe</c> (<c>src/Launcher.Updater</c>), the helper the release ships
/// beside the launcher, built with Native AOT so it needs no .NET on the PC. The installed helper is copied into the
/// staging folder and run from there, so it never runs from a file it replaces; it's the installed launcher's own, so
/// the two always agree on its command line. It's started with no window, no inherited handles (an inherited handle to
/// the launcher's PCK would keep it open after the launcher quits) and, where the launcher's job allows it, out of that
/// job, so it outlives the launcher whatever started it.
/// </summary>
/// <param name="helper">The helper to run; by default <see cref="HelperFileName"/> beside the launcher (<see cref="UpdateHandover.InstallDir"/>).</param>
public sealed class WindowsUpdateInstaller(string? helper = null) : IUpdateInstaller
{
    public const string HelperFileName = "OdysseyUpdater.exe";

    private const uint CreateNoWindow = 0x0800_0000;
    private const uint CreateBreakawayFromJob = 0x0100_0000;

    public string? Platform => RuntimeInformation.ProcessArchitecture == Architecture.X64 ? "windows-x86_64" : null;

    public string? HelperName => HelperFileName;

    /// <summary>The helper's arguments: the handover as options, then <c>--</c> and the launcher's own arguments.</summary>
    public static IReadOnlyList<string> Arguments(UpdateHandover handover)
    {
        ArgumentNullException.ThrowIfNull(handover);
        var arguments = new List<string>
        {
            "--pid", handover.ProcessId.ToString(CultureInfo.InvariantCulture),
            "--install", Path.GetFullPath(handover.InstallDir),
            "--package", Path.GetFullPath(handover.PackageDir),
            "--backup", Path.GetFullPath(handover.BackupDir),
            "--staging", Path.GetFullPath(handover.StagingDir),
            "--exe", Path.GetFullPath(handover.Executable),
            "--cwd", Path.GetFullPath(Directory.Exists(handover.WorkingDirectory) ? handover.WorkingDirectory : handover.InstallDir),
            "--log", Path.GetFullPath(handover.LogFile),
            "--attempts", Math.Max(1, handover.MoveAttempts).ToString(CultureInfo.InvariantCulture),
            "--",
        };
        arguments.AddRange(handover.Arguments);
        return arguments;
    }

    public string? Start(UpdateHandover handover)
    {
        ArgumentNullException.ThrowIfNull(handover);
        var source = helper ?? Path.Combine(handover.InstallDir, HelperFileName);
        if (!File.Exists(source))
        {
            return $"{HelperFileName}, which installs the update, isn't beside the launcher ({source}). Download the new version from its release page instead.";
        }

        var copy = Path.Combine(handover.StagingDir, HelperFileName);
        string commandLine;
        try
        {
            // The release's helper is one file. A plain build (the tests') has its .dll and runtime config beside it.
            foreach (var file in Directory.GetFiles(Path.GetDirectoryName(Path.GetFullPath(source))!, Path.GetFileNameWithoutExtension(HelperFileName) + ".*"))
            {
                if (!file.EndsWith(".pdb", StringComparison.OrdinalIgnoreCase))
                {
                    File.Copy(file, Path.Combine(handover.StagingDir, Path.GetFileName(file)), overwrite: true);
                }
            }

            commandLine = WindowsCommandLine.Build(copy, Arguments(handover));
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return $"The update's installer couldn't be copied to {handover.StagingDir} ({e.Message}).";
        }

        if (commandLine.Length >= WindowsCommandLine.MaxLength)
        {
            return "The launcher's command line is too long to hand to the update's installer.";
        }

        // Out of the launcher's job if it may leave it; a job that refuses breakaway fails the call, so try again in it.
        var error = StartDetached(copy, commandLine, CreateBreakawayFromJob);
        if (error == ErrorAccessDenied)
        {
            error = StartDetached(copy, commandLine, 0);
        }

        return error == 0 ? null : $"The update's installer couldn't be started ({new System.ComponentModel.Win32Exception(error).Message}).";
    }

    /// <summary>Starts <paramref name="program"/> with <paramref name="commandLine"/>; returns 0, or the Win32 error.</summary>
    private static unsafe int StartDetached(string program, string commandLine, uint extraFlags)
    {
        var startup = default(StartupInfoEx);
        startup.StartupInfo.Cb = sizeof(StartupInfo);
        var buffer = new char[commandLine.Length + 1];
        commandLine.CopyTo(0, buffer, 0, commandLine.Length);
        fixed (char* line = buffer)
        {
            // Its working folder is System32, never the launcher's folder or the staging folder, which it changes.
            if (!CreateProcess(program, line, 0, 0, inheritHandles: false, CreateNoWindow | CreateDefaultErrorMode | CreateUnicodeEnvironment | extraFlags,
                    0, Environment.SystemDirectory, &startup, out var info))
            {
                return Marshal.GetLastPInvokeError();
            }

            CloseHandle(info.Thread);
            CloseHandle(info.Process);
            return 0;
        }
    }
}
