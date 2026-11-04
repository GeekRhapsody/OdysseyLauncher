using System.Text;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// The file system's root, then what's mounted where USB drives and shares go: <c>/run/media/&lt;user&gt;</c> (udisks2 on
/// Arch and its kin, such as CachyOS), <c>/media/&lt;user&gt;</c> (udisks2 on Debian and its kin, such as Mint) and
/// <c>/mnt</c> (shares and disks mounted by hand or by fstab), from the mount table (<c>/proc/self/mountinfo</c>), which
/// never touches a drive, so a share that's gone can't hang the list. Each is named after its folder (udisks names
/// it after the volume's label); a share's detail is its source (<c>//nas/roms</c>). A drive that isn't mounted isn't
/// listed: mounting it is the desktop's job.
/// </summary>
/// <param name="mountInfo">The mount table: <c>/proc/self/mountinfo</c>, or a test's.</param>
public sealed class LinuxFileLocations(string homeDir, string userName, string mountInfo) : IFileLocations
{
    private static readonly string[] NetworkFileSystems = ["cifs", "smb3", "smbfs", "nfs", "nfs4", "fuse.sshfs"];

    private readonly string[] _removableRoots = ["/run/media/" + userName + "/", "/media/" + userName + "/"];

    public IReadOnlyList<FileLocation> Drives()
    {
        var drives = new List<FileLocation> { new("/", "File system", LocationKind.Fixed, null) };
        string[] lines;
        try
        {
            lines = File.ReadAllLines(mountInfo);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return drives;
        }

        foreach (var line in lines)
        {
            if (Mount(line) is not { } mount)
            {
                continue;
            }

            // A mount point mounted over (an automount, then the share it mounts) is listed once, as the last.
            var index = drives.FindIndex(d => d.Path == mount.Path);
            if (index < 0)
            {
                drives.Add(mount);
            }
            else
            {
                drives[index] = mount;
            }
        }

        return drives;
    }

    public string? VolumeLabel(string root) => null;

    public IReadOnlyList<FileLocation> QuickAccess()
    {
        var places = new List<FileLocation> { new(homeDir, "Home", LocationKind.Folder, null) };
        foreach (var name in (ReadOnlySpan<string>)["Desktop", "Downloads"])
        {
            var folder = Path.Combine(homeDir, name);
            if (Directory.Exists(folder))
            {
                places.Add(new FileLocation(folder, name, LocationKind.Folder, null));
            }
        }

        return places;
    }

    /// <summary>
    /// One line of the mount table as a place, or null when it isn't in one of the places listed:
    /// <c>id parent major:minor root mount-point options [optional fields...] - type source super-options</c>.
    /// </summary>
    private FileLocation? Mount(string line)
    {
        var fields = line.Split(' ');
        var separator = fields.Length > 6 ? Array.IndexOf(fields, "-", 6) : -1;
        if (separator < 0 || separator + 2 >= fields.Length)
        {
            return null;
        }

        var path = Unescape(fields[4]);
        var removable = Array.Exists(_removableRoots, root => path.StartsWith(root, StringComparison.Ordinal) && path.Length > root.Length);
        if (!removable && path != "/mnt" && !path.StartsWith("/mnt/", StringComparison.Ordinal))
        {
            return null;
        }

        var label = Path.GetFileName(path.TrimEnd('/'));
        var type = fields[separator + 1];
        return Array.IndexOf(NetworkFileSystems, type) >= 0
            ? new FileLocation(path, label, LocationKind.Network, Unescape(fields[separator + 2]))
            : new FileLocation(path, label, removable ? LocationKind.Removable : LocationKind.Fixed, path);
    }

    /// <summary>The mount table writes a space, tab, newline or backslash in a path as an octal escape (<c>\040</c>).</summary>
    private static string Unescape(string field)
    {
        if (!field.Contains('\\', StringComparison.Ordinal))
        {
            return field;
        }

        var text = new StringBuilder(field.Length);
        for (var i = 0; i < field.Length; i++)
        {
            if (field[i] == '\\' && IsOctal(field, i + 1))
            {
                text.Append((char)Convert.ToInt32(field.Substring(i + 1, 3), 8));
                i += 3;
            }
            else
            {
                text.Append(field[i]);
            }
        }

        return text.ToString();
    }

    private static bool IsOctal(string field, int start) =>
        start + 3 <= field.Length && field[start] is >= '0' and <= '3' && field[start + 1] is >= '0' and <= '7' && field[start + 2] is >= '0' and <= '7';
}
