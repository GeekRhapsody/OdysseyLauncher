using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Launcher.Core.Updates;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// Installs an update on Linux (L5; docs/ARCHITECTURE.md A1 <c>Updates</c>, decisions log 2026-11-05): the release's
/// <c>.AppImage</c>, downloaded and checked beside the running one by <see cref="UpdateService"/>, is renamed over it
/// (<c>$APPIMAGE</c>, keeping its name and mode), and started again with the launcher's arguments once the launcher has
/// quit. No helper program: Linux lets a running file be replaced, and the running AppImage keeps the old file's data
/// until it quits. The restart is a shell started first, so the rename is the last step that can fail, and a failure
/// leaves nothing changed.
/// </summary>
/// <param name="environment">The launcher's environment variables (<c>APPIMAGE</c>, <c>APPDIR</c>), for tests.</param>
[SupportedOSPlatform("linux")]
public sealed class LinuxUpdateInstaller(Func<string, string?> environment) : IUpdateInstaller
{
    /// <summary>
    /// Waits for the launcher's process ($1) to end, removes the staging folder ($2) if it's empty, as the rename leaves
    /// it, closes every file it inherited but the standard three, then becomes the new AppImage ($3) with the
    /// launcher's arguments. The AppImage runtime leaves its mount point open in the launcher (fd 1023, inherited by
    /// what it starts): passed on, it kept the old version mounted while the new one ran. bash, as only it closes a
    /// file number above 9 (<c>{fd}&gt;&amp;-</c>).
    /// </summary>
    private const string RestartScript = """
        pid=$1 staging=$2
        shift 2
        while kill -0 "$pid" 2> /dev/null; do sleep 0.2; done
        rmdir -- "$staging" 2> /dev/null
        for fd in /proc/self/fd/*; do
            fd=${fd##*/}
            (( fd > 2 )) && exec {fd}>&-
        done 2> /dev/null
        exec "$@"
        """;

    public LinuxUpdateInstaller()
        : this(Environment.GetEnvironmentVariable)
    {
    }

    public string? Platform => RuntimeInformation.ProcessArchitecture == Architecture.X64 ? "linux-x86_64" : null;

    public UpdatePackage Package => UpdatePackage.AppImage;

    public string? HelperName => null;

    public string? Target(string executable, out string? problem)
    {
        ArgumentNullException.ThrowIfNull(executable);
        var file = PlatformPaths.AppImageFile(Path.GetDirectoryName(Path.GetFullPath(executable))!, environment);
        problem = file is null
            ? "The launcher isn't running from an AppImage, so there's no AppImage file for the update to replace. Download the new version's AppImage instead."
            : null;
        return file;
    }

    public string? Start(UpdateHandover handover)
    {
        ArgumentNullException.ThrowIfNull(handover);
        using var restart = new Process { StartInfo = RestartInfo(handover) };
        try
        {
            restart.Start();
        }
        catch (Win32Exception e)
        {
            return $"The launcher couldn't be made to restart after the update ({e.Message}).";
        }

        try
        {
            File.SetUnixFileMode(handover.Package, File.GetUnixFileMode(handover.Executable) | UnixFileMode.UserRead | UnixFileMode.UserExecute);
            File.Move(handover.Package, handover.Executable, overwrite: true);
            return null;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // Nothing was replaced, so nothing restarts when the launcher quits later.
            restart.Kill();
            return $"The new AppImage couldn't replace {handover.Executable} ({e.Message}).";
        }
    }

    /// <summary>The restart: <see cref="RestartScript"/>, in the launcher's working folder, without the AppImage runtime's variables, which the new one sets.</summary>
    private static ProcessStartInfo RestartInfo(UpdateHandover handover)
    {
        var info = new ProcessStartInfo("/bin/bash")
        {
            UseShellExecute = false,
            WorkingDirectory = Directory.Exists(handover.WorkingDirectory) ? handover.WorkingDirectory : handover.InstallDir,
        };
        foreach (var argument in (string[])["-c", RestartScript, "odyssey-update", handover.ProcessId.ToString(CultureInfo.InvariantCulture), handover.StagingDir, handover.Executable])
        {
            info.ArgumentList.Add(argument);
        }

        foreach (var argument in handover.Arguments)
        {
            info.ArgumentList.Add(argument);
        }

        PortableProcessRunner.LeaveOutAppImageVariables(info.Environment);
        return info;
    }
}
