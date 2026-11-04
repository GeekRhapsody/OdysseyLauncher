using Launcher.Core.Platform;
using Launcher.Core.Platform.Linux;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Platform;

/// <summary>The pickers' places on Linux, from a made-up mount table: these run on every OS.</summary>
public sealed class LinuxFileLocationsTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    [Fact]
    public void Usb_drives_and_shares_are_listed_after_the_root()
    {
        var drives = Drives(
            "22 1 0:21 / /proc rw,nosuid,nodev,noexec,relatime shared:12 - proc proc rw",
            "26 1 259:2 / / rw,noatime shared:1 - btrfs /dev/nvme0n1p2 rw,subvol=/@",
            "95 26 0:52 / /home rw,noatime shared:45 - btrfs /dev/nvme0n1p2 rw,subvol=/@home",
            "310 26 8:17 / /run/media/claudio/USB\\040STICK rw,nosuid,nodev,relatime shared:170 - vfat /dev/sdb1 rw,fmask=0022",
            "320 26 8:33 / /media/claudio/Games rw,nosuid,nodev,relatime shared:180 - ext4 /dev/sdc1 rw",
            "330 26 0:60 / /mnt/nas rw,relatime shared:190 - cifs //nas/roms rw,vers=3.1.1",
            "340 26 8:49 / /mnt/games rw,relatime shared:200 - ext4 /dev/sdd1 rw",
            "350 26 8:65 / /run/media/someone-else/Theirs rw shared:210 - vfat /dev/sde1 rw");

        Assert.Equal(
            [
                new FileLocation("/", "File system", LocationKind.Fixed, null),
                new FileLocation("/run/media/claudio/USB STICK", "USB STICK", LocationKind.Removable, "/run/media/claudio/USB STICK"),
                new FileLocation("/media/claudio/Games", "Games", LocationKind.Removable, "/media/claudio/Games"),
                new FileLocation("/mnt/nas", "nas", LocationKind.Network, "//nas/roms"),
                new FileLocation("/mnt/games", "games", LocationKind.Fixed, "/mnt/games"),
            ],
            drives);
    }

    [Fact]
    public void An_automounted_share_is_listed_once_as_what_is_mounted_over_it()
    {
        var drives = Drives(
            "60 26 0:40 / /mnt/nas rw,relatime shared:30 - autofs systemd-1 rw,fd=50,pgrp=1",
            "400 60 0:70 / /mnt/nas rw,relatime shared:300 - nfs4 nas:/export/roms rw,vers=4.2");

        Assert.Equal(
            [
                new FileLocation("/", "File system", LocationKind.Fixed, null),
                new FileLocation("/mnt/nas", "nas", LocationKind.Network, "nas:/export/roms"),
            ],
            drives);
    }

    [Fact]
    public void A_line_it_can_not_read_is_skipped()
    {
        var drives = Drives("garbage", "1 2 3", "310 26 8:17 / /run/media/claudio/USB rw shared:1 -");

        Assert.Equal([new FileLocation("/", "File system", LocationKind.Fixed, null)], drives);
    }

    [Fact]
    public void Without_the_mount_table_only_the_root_is_listed() =>
        Assert.Equal(
            [new FileLocation("/", "File system", LocationKind.Fixed, null)],
            new LinuxFileLocations(_dir.Path, "claudio", _dir.Combine("missing")).Drives());

    private IReadOnlyList<FileLocation> Drives(params string[] lines) =>
        new LinuxFileLocations(_dir.Path, "claudio", _dir.File("mountinfo", string.Join('\n', lines) + "\n")).Drives();
}
