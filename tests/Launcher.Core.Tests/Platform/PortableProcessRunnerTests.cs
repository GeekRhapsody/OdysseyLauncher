using Launcher.Core.Platform;

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
}
