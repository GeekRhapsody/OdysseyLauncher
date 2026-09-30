using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Drive letters from <c>GetLogicalDrives</c> and <c>GetDriveTypeW</c>, and a mapped drive's share from
/// <c>WNetGetConnectionW</c>: none of them touches the drive, so a disconnected share can't hang the list. Volume labels
/// (<c>GetVolumeInformationW</c>, which does touch it) are fetched separately. Downloads comes from its known folder,
/// since .NET has no special folder for it.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed unsafe partial class WindowsFileLocations(string homeDir) : IFileLocations
{
    private const uint DriveRemovable = 2;
    private const uint DriveFixed = 3;
    private const uint DriveRemote = 4;
    private const uint DriveCdRom = 5;
    private const uint DriveRamDisk = 6;
    private const int NoError = 0;
    private const int ErrorConnectionUnavailable = 1201;
    private const int LabelLength = 261;

    private static readonly Guid DownloadsFolder = new("374DE290-123F-4565-9164-39C4925E467B");

    public IReadOnlyList<FileLocation> Drives()
    {
        var drives = new List<FileLocation>();
        var mask = GetLogicalDrives();
        for (var i = 0; i < 26; i++)
        {
            if ((mask & (1u << i)) == 0)
            {
                continue;
            }

            var letter = (char)('A' + i);
            var root = letter + @":\";
            switch (GetDriveTypeW(root))
            {
                case DriveRemote:
                {
                    var (share, connected) = MappedShare(letter);
                    var detail = connected ? share : share is null ? "disconnected" : share + ", disconnected";
                    drives.Add(new FileLocation(root, $"Network drive ({letter}:)", LocationKind.Network, detail, connected));
                    break;
                }

                case DriveRemovable:
                    drives.Add(new FileLocation(root, $"Removable drive ({letter}:)", LocationKind.Removable, null));
                    break;
                case DriveCdRom:
                    drives.Add(new FileLocation(root, $"Disc drive ({letter}:)", LocationKind.Optical, null));
                    break;
                case DriveFixed or DriveRamDisk:
                    drives.Add(new FileLocation(root, $"Local disk ({letter}:)", LocationKind.Fixed, null));
                    break;
                default:
                    drives.Add(new FileLocation(root, $"Drive ({letter}:)", LocationKind.Other, null));
                    break;
            }
        }

        return drives;
    }

    public string? VolumeLabel(string root)
    {
        ArgumentNullException.ThrowIfNull(root);
        var label = stackalloc char[LabelLength];
        return GetVolumeInformationW(root, label, LabelLength, null, null, null, null, 0) && label[0] != '\0'
            ? new string(label)
            : null;
    }

    public IReadOnlyList<FileLocation> QuickAccess()
    {
        var places = new List<FileLocation>();
        void Add(string? folder, string label)
        {
            if (!string.IsNullOrEmpty(folder) && Directory.Exists(folder)
                && !places.Exists(p => string.Equals(p.Path, folder, StringComparison.OrdinalIgnoreCase)))
            {
                places.Add(new FileLocation(folder, label, LocationKind.Folder, null));
            }
        }

        Add(homeDir, "Your folder");
        Add(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Desktop");
        Add(KnownFolder(DownloadsFolder), "Downloads");
        return places;
    }

    /// <summary>A mapped drive's share, and whether it's connected (a remembered mapping may not be).</summary>
    private static (string? Share, bool Connected) MappedShare(char letter)
    {
        var buffer = stackalloc char[512];
        var length = 512;
        return WNetGetConnectionW(letter + ":", buffer, ref length) switch
        {
            NoError => (new string(buffer), true),
            ErrorConnectionUnavailable => (new string(buffer), false),
            _ => (null, true),
        };
    }

    private static string? KnownFolder(Guid id)
    {
        var result = SHGetKnownFolderPath(id, 0, 0, out var path);
        try
        {
            return result == 0 ? Marshal.PtrToStringUni(path) : null;
        }
        finally
        {
            Marshal.FreeCoTaskMem(path);
        }
    }

    [LibraryImport("kernel32.dll")]
    private static partial uint GetLogicalDrives();

    [LibraryImport("kernel32.dll", StringMarshalling = StringMarshalling.Utf16)]
    private static partial uint GetDriveTypeW(string root);

    [LibraryImport("kernel32.dll", StringMarshalling = StringMarshalling.Utf16)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool GetVolumeInformationW(
        string root, char* volumeName, int volumeNameSize, uint* serialNumber, uint* maxComponentLength, uint* flags,
        char* fileSystemName, int fileSystemNameSize);

    [LibraryImport("mpr.dll", StringMarshalling = StringMarshalling.Utf16)]
    private static partial int WNetGetConnectionW(string localName, char* remoteName, ref int length);

    [LibraryImport("shell32.dll")]
    private static partial int SHGetKnownFolderPath(in Guid id, uint flags, nint token, out nint path);
}
