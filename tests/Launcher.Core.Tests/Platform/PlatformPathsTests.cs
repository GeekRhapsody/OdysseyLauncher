using Launcher.Core.Platform;

namespace Launcher.Core.Tests.Platform;

/// <summary>Linux's folders, worked out from a made-up environment, so these run on either OS.</summary>
public class PlatformPathsTests
{
    private const string Home = "/home/ann";

    private static Func<string, string?> Variables(params (string Name, string? Value)[] variables) =>
        name => Array.Find(variables, v => v.Name == name).Value;

    private static PlatformPaths Linux(string executableDir, Func<string, string?> environment, Func<string, bool>? fileExists = null) =>
        PlatformPaths.Detect(executableDir, Home, windows: false, environment, fileExists ?? (_ => false));

    [Fact]
    public void On_Linux_the_folders_are_the_XDG_defaults_under_home()
    {
        var paths = Linux("/opt/odyssey", Variables());

        Assert.Equal(
            ("/home/ann/.config/OdysseyLauncher", "/home/ann/.local/share/OdysseyLauncher", "/home/ann/.cache/OdysseyLauncher", Home),
            (paths.ConfigDir, paths.DataDir, paths.CacheDir, paths.HomeDir));
    }

    [Fact]
    public void The_XDG_variables_move_them_and_a_relative_one_is_ignored_as_the_spec_says()
    {
        var paths = Linux("/opt/odyssey", Variables(("XDG_CONFIG_HOME", "/cfg"), ("XDG_DATA_HOME", "/data/"), ("XDG_CACHE_HOME", "cache")));

        Assert.Equal(
            ("/cfg/OdysseyLauncher", "/data/OdysseyLauncher", "/home/ann/.cache/OdysseyLauncher"),
            (paths.ConfigDir, paths.DataDir, paths.CacheDir));
    }

    [Fact]
    public void A_portable_marker_beside_the_executable_puts_everything_in_its_userdata_folder()
    {
        var paths = Linux("/opt/odyssey", Variables(), path => path == "/opt/odyssey/portable.txt");

        Assert.Equal(
            ("/opt/odyssey/userdata", "/opt/odyssey/userdata", "/opt/odyssey/userdata/cache"),
            (paths.ConfigDir, paths.DataDir, paths.CacheDir));
    }

    [Fact]
    public void In_an_AppImage_the_portable_marker_is_beside_the_AppImage_file_not_in_its_read_only_mount()
    {
        var appImage = Variables(("APPIMAGE", "/home/ann/Games/Odyssey.AppImage"), ("APPDIR", "/tmp/.mount_OdyssXy"));

        var portable = Linux("/tmp/.mount_OdyssXy/usr/bin", appImage, path => path == "/home/ann/Games/portable.txt");
        var inTheMount = Linux("/tmp/.mount_OdyssXy/usr/bin", appImage, path => path == "/tmp/.mount_OdyssXy/usr/bin/portable.txt");

        Assert.Equal(
            ("/home/ann/Games/userdata", "/home/ann/Games/userdata", "/home/ann/Games/userdata/cache"),
            (portable.ConfigDir, portable.DataDir, portable.CacheDir));
        Assert.Equal("/home/ann/.config/OdysseyLauncher", inTheMount.ConfigDir);
    }

    [Theory]
    [InlineData(null, "/tmp/.mount_ab")]
    [InlineData("Odyssey.AppImage", "/tmp/.mount_ab")]
    [InlineData("/home/ann/Odyssey.AppImage", null)]
    [InlineData("/home/ann/Odyssey.AppImage", "mount_ab")]
    [InlineData("/home/ann/Odyssey.AppImage", "/tmp/.mount_a")]   // a prefix of the executable's mount, not its mount
    [InlineData("/home/ann/Odyssey.AppImage", "/tmp/.mount_xy")]  // another AppImage's, inherited from the one that started it
    public void Only_an_AppImage_whose_mount_holds_the_executable_counts(string? file, string? mount)
    {
        Assert.Null(PlatformPaths.AppImageDir("/tmp/.mount_ab/usr/bin", Variables(("APPIMAGE", file), ("APPDIR", mount))));
    }

    [Fact]
    public void The_AppImage_files_folder_is_given_when_its_mount_holds_the_executable()
    {
        Assert.Equal("/home/ann", PlatformPaths.AppImageDir("/tmp/.mount_ab/usr/bin", Variables(("APPIMAGE", "/home/ann/Odyssey.AppImage"), ("APPDIR", "/tmp/.mount_ab/"))));
        Assert.Equal("/", PlatformPaths.AppImageDir("/tmp/.mount_ab", Variables(("APPIMAGE", "/Odyssey.AppImage"), ("APPDIR", "/tmp/.mount_ab"))));
    }
}
