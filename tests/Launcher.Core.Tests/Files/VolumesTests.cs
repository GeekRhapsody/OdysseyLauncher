using Launcher.Core.Files;

namespace Launcher.Core.Tests.Files;

public class VolumesTests
{
    private static readonly string[] Mounts = ["/", "/home", "/mnt/games", "/mnt/games/old", "/run/media/ann/USB Stick"];

    [Theory]
    [InlineData("/home/ann/.local/share/OdysseyLauncher/media", "/home")]
    [InlineData("/mnt/games/ROMs", "/mnt/games")]
    [InlineData("/mnt/games/old/ROMs", "/mnt/games/old")]
    [InlineData("/mnt/gamesbackup/ROMs", "/")]            // whole names: /mnt/games doesn't hold /mnt/gamesbackup
    [InlineData("/mnt/games", "/mnt/games")]
    [InlineData("/run/media/ann/USB Stick/media", "/run/media/ann/USB Stick")]
    [InlineData("/tmp/x", "/")]
    public void A_path_is_on_the_longest_mount_point_that_holds_it(string path, string mount)
    {
        Assert.Equal(mount, Volumes.MountOf(path, Mounts));
    }

    [Fact]
    public void A_mount_point_with_a_trailing_slash_counts_and_with_no_list_everything_is_on_the_root()
    {
        Assert.Equal("/mnt/games", Volumes.MountOf("/mnt/games/ROMs", ["/", "/mnt/games/"]));
        Assert.Equal("/", Volumes.MountOf("/mnt/games/ROMs", []));
    }

    [Fact]
    public void Two_folders_in_one_folder_are_on_one_volume()
    {
        var root = Path.Combine(Path.GetTempPath(), "odyssey-volumes");

        Assert.True(Volumes.Same(Path.Combine(root, "a"), Path.Combine(root, "b", "c")));
    }
}
