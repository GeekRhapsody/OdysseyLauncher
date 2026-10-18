using System.Diagnostics;
using System.Reflection;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Windows;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Updates;

/// <summary>
/// The update helper (<c>OdysseyUpdater.exe</c>, <c>src/Launcher.Updater</c>) run for real, its plain build rather than
/// the release's Native AOT one, with the fake emulator standing in for the launcher: as the running launcher it
/// waits for, and as the old and new versions' executable it starts again.
/// </summary>
public sealed class WindowsUpdateInstallerTests : IDisposable
{
    private static readonly TimeSpan Wait = TimeSpan.FromSeconds(60);

    /// <summary>The helper's build output, from the test project's <c>UpdaterDir</c> metadata.</summary>
    private static readonly string HelperDir = Path.GetFullPath(
        typeof(WindowsUpdateInstallerTests).Assembly.GetCustomAttributes<AssemblyMetadataAttribute>().Single(a => a.Key == "UpdaterDir").Value!);

    private static readonly string Helper = Path.Combine(HelperDir, WindowsUpdateInstaller.HelperFileName);

    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    // Spaces, brackets and non-ASCII letters, as a user's folder may have.
    private string InstallDir => _dir.Combine("Zoë's Games [PC]", "Odyssey Launcher");

    private string StagingDir => Path.Combine(InstallDir, ".odyssey-update");

    private string PackageDir => Path.Combine(StagingDir, "new", "OdysseyLauncher-0.17.0-windows-x86_64");

    private string LogFile => _dir.Combine("userdata", "logs", "update.log");

    private string Executable => Path.Combine(InstallDir, "OdysseyLauncher.exe");

    [Fact]
    public void The_helper_gets_the_handover_as_options_then_the_launchers_own_arguments()
    {
        var arguments = WindowsUpdateInstaller.Arguments(Handover(1234, ["--", "--user-dir=C:\\My Games\\Odyssey"]));

        Assert.Equal(
            [
                "--pid", "1234", "--install", InstallDir, "--package", PackageDir, "--backup", Path.Combine(StagingDir, "old"),
                "--staging", StagingDir, "--exe", Executable, "--cwd", InstallDir, "--log", LogFile, "--attempts", "20",
                "--", "--", "--user-dir=C:\\My Games\\Odyssey",
            ],
            arguments);
    }

    [Fact]
    public async Task An_update_replaces_the_launchers_files_keeps_the_users_and_starts_it_again()
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        InstallOld();
        StageNew();
        var restarted = _dir.Combine("restarted.json");
        // The running launcher: the old version's executable, quitting a moment after the helper starts.
        using var running = Process.Start(new ProcessStartInfo(Executable) { ArgumentList = { "--fake-sleep=1500" }, UseShellExecute = false })!;

        var problem = new WindowsUpdateInstaller(Helper).Start(Handover(running.Id, [$"--fake-log={restarted}", "--", "--user-dir=C:\\My Games\\Odyssey"]));

        Assert.Null(problem);
        await WaitFor(() => File.Exists(restarted) && File.Exists(LogFile) && File.ReadAllText(LogFile).Contains("started", StringComparison.Ordinal));
        Assert.True(running.HasExited);
        var log = FakeEmulator.ReadLog(restarted);
        Assert.Equal([$"--fake-log={restarted}", "--", "--user-dir=C:\\My Games\\Odyssey"], log.Args);
        Assert.Equal(Path.TrimEndingDirectorySeparator(InstallDir), Path.TrimEndingDirectorySeparator(log.WorkingDirectory));
        Assert.True(File.GetCreationTimeUtc(restarted) >= running.ExitTime.ToUniversalTime().AddMilliseconds(-50), "It didn't wait for the launcher to quit.");

        Assert.Equal("new pck", File.ReadAllText(Path.Combine(InstallDir, "OdysseyLauncher.pck")));
        Assert.Equal("new theme", File.ReadAllText(Path.Combine(InstallDir, "themes", "slab", "theme.toml")));
        Assert.False(Directory.Exists(Path.Combine(InstallDir, "themes", "dropped")), "The old themes folder should go whole.");
        Assert.Equal("the user's library", File.ReadAllText(Path.Combine(InstallDir, "userdata", "library.db")));
        Assert.True(File.Exists(Path.Combine(InstallDir, "portable.txt")));
        Assert.Equal("driver", File.ReadAllText(Path.Combine(InstallDir, "override.cfg")));
        Assert.Contains("installed", File.ReadAllText(LogFile), StringComparison.Ordinal);

        // All that's left of the staging folder is the helper, which ran from it.
        await WaitFor(() => Directory.GetDirectories(StagingDir).Length == 0);
        Assert.All(Directory.GetFiles(StagingDir), f => Assert.StartsWith("OdysseyUpdater.", Path.GetFileName(f), StringComparison.Ordinal));
    }

    [Fact]
    public async Task A_move_that_fails_puts_the_old_version_back_and_starts_it()
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        InstallOld();
        StageNew();
        var restarted = _dir.Combine("restarted.json");
        // A file held open in the new themes folder: that folder can't be moved into place.
        using (new FileStream(Path.Combine(PackageDir, "themes", "slab", "theme.toml"), FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            var exit = await RunHelper(WindowsUpdateInstaller.Arguments(Handover(processId: int.MaxValue, [$"--fake-log={restarted}"], moveAttempts: 2)));
            Assert.Equal(1, exit);
        }

        await WaitFor(() => File.Exists(restarted));
        Assert.Equal("old pck", File.ReadAllText(Path.Combine(InstallDir, "OdysseyLauncher.pck")));
        Assert.Equal("old theme", File.ReadAllText(Path.Combine(InstallDir, "themes", "slab", "theme.toml")));
        Assert.True(Directory.Exists(Path.Combine(InstallDir, "themes", "dropped")));
        Assert.Equal("old dll", File.ReadAllText(Path.Combine(InstallDir, "data_OdysseyLauncher_windows_x86_64", "Launcher.Core.dll")));
        Assert.Equal("the user's library", File.ReadAllText(Path.Combine(InstallDir, "userdata", "library.db")));
        // Everything was put back, so the staging folder goes (but for the file this test held open as it was deleted).
        Assert.False(Directory.Exists(Path.Combine(StagingDir, "old")));
        var log = File.ReadAllText(LogFile);
        Assert.Contains("the old version is put back", log, StringComparison.Ordinal);
        Assert.DoesNotContain("couldn't be put back", log, StringComparison.Ordinal);
        Assert.False(File.Exists(Path.Combine(StagingDir, "incomplete.txt")));
    }

    [Fact]
    public async Task Bad_arguments_change_nothing()
    {
        InstallOld();

        var exit = await RunHelper(["--pid", "12", "--install", "relative", "--log", LogFile]);

        Assert.Equal(2, exit);
        Assert.Contains("bad arguments", File.ReadAllText(LogFile), StringComparison.Ordinal);
        Assert.Equal("old pck", File.ReadAllText(Path.Combine(InstallDir, "OdysseyLauncher.pck")));
    }

    [Fact]
    public void Without_the_helper_beside_the_launcher_nothing_starts()
    {
        StageNew();

        var problem = new WindowsUpdateInstaller().Start(Handover(1234, []));

        Assert.NotNull(problem);
        Assert.Contains("OdysseyUpdater.exe", problem, StringComparison.Ordinal);
    }

    private UpdateHandover Handover(int processId, IReadOnlyList<string> arguments, int moveAttempts = 20) =>
        new(processId, InstallDir, PackageDir, Path.Combine(StagingDir, "old"), StagingDir, Executable, arguments, InstallDir, LogFile, moveAttempts);

    private static async Task<int> RunHelper(IReadOnlyList<string> arguments)
    {
        var start = new ProcessStartInfo(Helper) { UseShellExecute = false };
        foreach (var argument in arguments)
        {
            start.ArgumentList.Add(argument);
        }

        using var helper = Process.Start(start)!;
        await helper.WaitForExitAsync(TestContext.Current.CancellationToken).WaitAsync(Wait, TestContext.Current.CancellationToken);
        return helper.ExitCode;
    }

    /// <summary>The old version: the fake emulator as the launcher's executable, its files, and the user's beside them.</summary>
    private void InstallOld()
    {
        FakeEmulator.InstallAt(InstallDir, "OdysseyLauncher.exe");
        Write(InstallDir, "OdysseyLauncher.pck", "old pck");
        Write(InstallDir, "data_OdysseyLauncher_windows_x86_64/Launcher.Core.dll", "old dll");
        Write(InstallDir, "themes/slab/theme.toml", "old theme");
        Write(InstallDir, "themes/dropped/theme.toml", "a theme the new version doesn't have");
        Write(InstallDir, "portable.txt", string.Empty);
        Write(InstallDir, "userdata/library.db", "the user's library");
        Write(InstallDir, "override.cfg", "driver");
    }

    /// <summary>The new version, unpacked in the staging folder as <c>UpdateService.DownloadAsync</c> leaves it.</summary>
    private void StageNew()
    {
        FakeEmulator.InstallAt(PackageDir, "OdysseyLauncher.exe");
        Write(PackageDir, "OdysseyLauncher.pck", "new pck");
        Write(PackageDir, "data_OdysseyLauncher_windows_x86_64/Launcher.Core.dll", "new dll");
        Write(PackageDir, "themes/slab/theme.toml", "new theme");
    }

    private static void Write(string folder, string relative, string content)
    {
        var path = Path.Combine([folder, .. relative.Split('/')]);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, content);
    }

    private static async Task WaitFor(Func<bool> condition)
    {
        var watch = Stopwatch.StartNew();
        while (!condition())
        {
            Assert.True(watch.Elapsed < Wait, "The update helper didn't finish in time.");
            await Task.Delay(100, TestContext.Current.CancellationToken);
        }
    }
}
