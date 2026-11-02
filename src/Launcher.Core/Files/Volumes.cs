namespace Launcher.Core.Files;

/// <summary>
/// Whether two paths are on one volume, so a rename can move between them (a move to another volume is a copy). On
/// Windows that's the same root, a drive or a share. Elsewhere every root is <c>/</c>, so it's the same mount point:
/// the longest one that holds each path, from the mount table, which no drive is touched to read.
/// </summary>
public static class Volumes
{
    public static bool Same(string a, string b)
    {
        ArgumentNullException.ThrowIfNull(a);
        ArgumentNullException.ThrowIfNull(b);
        var first = Path.GetFullPath(a);
        var second = Path.GetFullPath(b);
        if (OperatingSystem.IsWindows())
        {
            return string.Equals(Path.GetPathRoot(first), Path.GetPathRoot(second), StringComparison.OrdinalIgnoreCase);
        }

        string[] mounts;
        try
        {
            mounts = Array.ConvertAll(DriveInfo.GetDrives(), drive => drive.Name);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // Unknown: another volume, which only means a copy where a rename would have done.
            return false;
        }

        return string.Equals(MountOf(first, mounts), MountOf(second, mounts), StringComparison.Ordinal);
    }

    /// <summary>
    /// The mount point holding <paramref name="path"/> (an absolute Unix path): the longest of <paramref name="mounts"/>
    /// that it's in by whole names, else <c>/</c>. A bind mount counts as a volume of its own.
    /// </summary>
    internal static string MountOf(string path, IEnumerable<string> mounts)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(mounts);
        var best = "/";
        foreach (var mount in mounts)
        {
            var root = mount.Length > 1 ? mount.TrimEnd('/') : mount;
            if (root.Length > best.Length && (path == root || path.StartsWith(root + "/", StringComparison.Ordinal)))
            {
                best = root;
            }
        }

        return best;
    }
}
