using Launcher.Core.Launching;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Platform;

public class PortableProcessRunnerTests
{
    [Fact]
    public void An_emulator_isnt_given_what_an_AppImages_runtime_set_for_the_launcher()
    {
        var environment = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["APPIMAGE"] = "/home/ann/Odyssey.AppImage",
            ["APPDIR"] = "/tmp/.mount_ab",
            ["ARGV0"] = "./Odyssey.AppImage",
            ["OWD"] = "/home/ann",
            ["HOME"] = "/home/ann",
            ["PATH"] = "/usr/bin",
        };

        PortableProcessRunner.LeaveOutAppImageVariables(environment);

        Assert.Equal(["HOME", "PATH"], environment.Keys.Order(StringComparer.Ordinal));
    }

    private static LaunchPlan RunFile(string file) => new("run-file", "Run file", file, [], "/games", null, RunFile: true);

    [Fact]
    public void A_desktop_shortcut_runs_its_Exec_line_in_its_Path_folder()
    {
        using var dir = new TempDir();
        var shortcut = dir.File("Game.desktop", "[Desktop Entry]\nType=Application\nExec=/opt/game/run --fast\nPath=/opt/game\n");

        var (program, arguments, workingDirectory) = PortableProcessRunner.RunFileCommand(RunFile(shortcut));

        Assert.Equal("/opt/game/run", program);
        Assert.Equal(["--fast"], arguments);
        Assert.Equal("/opt/game", workingDirectory);
    }

    [Fact]
    public void A_shortcut_with_no_command_is_refused_with_its_path()
    {
        using var dir = new TempDir();
        var shortcut = dir.File("Broken.desktop", "[Desktop Entry]\nName=Broken\n");

        var e = Assert.Throws<ProcessStartException>(() => PortableProcessRunner.RunFileCommand(RunFile(shortcut)));

        Assert.Contains(shortcut, e.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_script_runs_with_a_shell_and_anything_else_as_it_is()
    {
        var (shell, arguments, _) = PortableProcessRunner.RunFileCommand(RunFile("/games/start.sh"));
        Assert.Matches("(bash|sh)(\\.exe)?$", shell);
        Assert.Equal(["/games/start.sh"], arguments);

        var (program, none, workingDirectory) = PortableProcessRunner.RunFileCommand(RunFile("/games/Game.AppImage"));
        Assert.Equal("/games/Game.AppImage", program);
        Assert.Empty(none);
        Assert.Equal("/games", workingDirectory);
    }

    [Fact]
    public void A_file_that_is_not_executable_fails_the_launch_rather_than_exiting_at_once()
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), "setsid and file modes are Linux's.");
        using var dir = new TempDir();
        var game = dir.File("Game.AppImage", "not a program");
        var plan = new LaunchPlan("run-file", "Run file", game, [], dir.Path, null, RunFile: true);

        var e = Assert.Throws<ProcessStartException>(() => new PortableProcessRunner().Start(plan));

        Assert.Equal(13, e.NativeErrorCode);
        Assert.Contains(game, e.Message, StringComparison.Ordinal);
    }
}
