using System.Diagnostics;
using System.Runtime.Versioning;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Linux;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Updates;

/// <summary>
/// The Linux installer run for real, with the fake emulator standing in for the running launcher it waits for and for
/// the new <c>.AppImage</c> it starts.
/// </summary>
[SupportedOSPlatform("linux")]
public sealed class LinuxUpdateInstallerTests : IDisposable
{
    private const string LinuxOnly = "Linux-only: the AppImage is replaced and restarted through /bin/sh.";
    private static readonly TimeSpan Wait = TimeSpan.FromSeconds(60);

    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    // Spaces and non-ASCII letters, as a user's folder may have.
    private string InstallDir => _dir.Combine("Zoë's Games", "Applications");

    private string StagingDir => Path.Combine(InstallDir, ".odyssey-update");

    private string Staged => Path.Combine(StagingDir, "OdysseyLauncher-0.17.0-linux-x86_64.AppImage");

    // Renamed by its user: the update keeps the name.
    private string AppImage => Path.Combine(InstallDir, "Odyssey Launcher.AppImage");

    [Theory]
    [InlineData("/tmp/.mount_ab/usr/bin/OdysseyLauncher.x86_64", "/home/zoë/Applications/Odyssey Launcher.AppImage")]
    [InlineData("/opt/odyssey/OdysseyLauncher.x86_64", null)]
    public void The_target_is_the_AppImage_the_launcher_runs_from(string executable, string? expected)
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), LinuxOnly);
        var environment = new Dictionary<string, string?> { ["APPIMAGE"] = "/home/zoë/Applications/Odyssey Launcher.AppImage", ["APPDIR"] = "/tmp/.mount_ab" };

        var target = new LinuxUpdateInstaller(name => environment.GetValueOrDefault(name)).Target(executable, out var problem);

        Assert.Equal(expected, target);
        if (expected is null)
        {
            Assert.Contains("isn't running from an AppImage", problem, StringComparison.Ordinal);
        }
        else
        {
            Assert.Null(problem);
        }
    }

    [Fact]
    public async Task An_update_replaces_the_AppImage_keeping_its_name_and_mode_and_starts_it_once_the_launcher_has_quit()
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), LinuxOnly);
        InstallOld();
        StageNew();
        var restarted = _dir.Combine("restarted.json");
        var workingDir = _dir.Combine("where it was started");
        Directory.CreateDirectory(workingDir);
        using var running = StartRunning(1500);

        var problem = new LinuxUpdateInstaller(_ => null).Start(Handover(running.Id, [$"--fake-log={restarted}", "--", "--user-dir=/home/zoë/Odyssey Games"], workingDir));

        Assert.Null(problem);
        Assert.False(File.Exists(Staged));
        Assert.Equal(File.ReadAllBytes(Path.Combine(FakeEmulator.OutputDir, FakeEmulator.ExeName)), File.ReadAllBytes(AppImage));
        Assert.Equal(UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute | UnixFileMode.GroupRead, File.GetUnixFileMode(AppImage));
        await WaitFor(() => File.Exists(restarted));
        Assert.True(running.HasExited);
        var log = FakeEmulator.ReadLog(restarted);
        Assert.Equal([$"--fake-log={restarted}", "--", "--user-dir=/home/zoë/Odyssey Games"], log.Args);
        Assert.Equal(workingDir, Path.TrimEndingDirectorySeparator(log.WorkingDirectory));
        Assert.True(File.GetLastWriteTimeUtc(restarted) >= running.ExitTime.ToUniversalTime().AddMilliseconds(-50), "It didn't wait for the launcher to quit.");
        Assert.False(Directory.Exists(StagingDir));
    }

    [Fact]
    public async Task An_AppImage_that_cant_be_replaced_changes_nothing_and_nothing_restarts()
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), LinuxOnly);
        InstallOld();
        StageNew();
        // A folder that isn't empty where the AppImage was: nothing can be renamed over it, root or not.
        File.Delete(AppImage);
        Directory.CreateDirectory(AppImage);
        File.WriteAllText(Path.Combine(AppImage, "in the way"), string.Empty);
        var restarted = _dir.Combine("restarted.json");
        using var running = StartRunning(300);

        var problem = new LinuxUpdateInstaller(_ => null).Start(Handover(running.Id, [$"--fake-log={restarted}"], InstallDir));

        Assert.NotNull(problem);
        Assert.Contains("couldn't replace", problem, StringComparison.Ordinal);
        Assert.True(File.Exists(Staged));
        await running.WaitForExitAsync(TestContext.Current.CancellationToken).WaitAsync(Wait, TestContext.Current.CancellationToken);
        await Task.Delay(1000, TestContext.Current.CancellationToken);
        Assert.False(File.Exists(restarted), "The restart should have been stopped with the update.");
    }

    private UpdateHandover Handover(int processId, IReadOnlyList<string> arguments, string workingDir) =>
        new(processId, InstallDir, Staged, Path.Combine(StagingDir, "old"), StagingDir, AppImage, arguments, workingDir, _dir.Combine("update.log"));

    /// <summary>The running launcher: the fake emulator, quitting after <paramref name="sleepMs"/>.</summary>
    private static Process StartRunning(int sleepMs) =>
        Process.Start(new ProcessStartInfo(Path.Combine(FakeEmulator.OutputDir, FakeEmulator.ExeName)) { ArgumentList = { $"--fake-sleep={sleepMs}" }, UseShellExecute = false })!;

    /// <summary>The old version, read and written by its owner only, and the fake's assemblies, which the new one runs on, beside it.</summary>
    private void InstallOld()
    {
        FakeEmulator.InstallAt(InstallDir);
        File.WriteAllText(AppImage, "old AppImage");
        File.SetUnixFileMode(AppImage, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.GroupRead);
    }

    /// <summary>The new version as <c>UpdateService.DownloadAsync</c> leaves it: alone in the staging folder, not executable.</summary>
    private void StageNew()
    {
        Directory.CreateDirectory(StagingDir);
        File.Copy(Path.Combine(FakeEmulator.OutputDir, FakeEmulator.ExeName), Staged);
        File.SetUnixFileMode(Staged, UnixFileMode.UserRead | UnixFileMode.UserWrite);
    }

    private static async Task WaitFor(Func<bool> condition)
    {
        var watch = Stopwatch.StartNew();
        while (!condition())
        {
            Assert.True(watch.Elapsed < Wait, "The restart didn't happen in time.");
            await Task.Delay(100, TestContext.Current.CancellationToken);
        }
    }
}
