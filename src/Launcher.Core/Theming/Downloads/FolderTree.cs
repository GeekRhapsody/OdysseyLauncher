namespace Launcher.Core.Theming.Downloads;

/// <summary>Deleting and moving a clone's folder, whose pack files libgit2 leaves read-only (Windows refuses to delete those).</summary>
internal static class FolderTree
{
    public static void Delete(string folder)
    {
        if (!Directory.Exists(folder))
        {
            return;
        }

        ClearReadOnly(folder);
        Directory.Delete(folder, recursive: true);
    }

    public static void ClearReadOnly(string folder)
    {
        foreach (var file in Directory.EnumerateFiles(folder, "*", new EnumerationOptions { RecurseSubdirectories = true, AttributesToSkip = 0 }))
        {
            var attributes = File.GetAttributes(file);
            if ((attributes & FileAttributes.ReadOnly) != 0)
            {
                File.SetAttributes(file, attributes & ~FileAttributes.ReadOnly);
            }
        }
    }

    /// <summary>
    /// Moves a folder, on another volume by copying it (<see cref="Directory.Move"/> works within one only), so the
    /// backups folder (DataDir) needn't share a volume with the themes folder (ConfigDir).
    /// </summary>
    public static void Move(string from, string to)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(to)!);
        try
        {
            Directory.Move(from, to);
            return;
        }
        catch (IOException) when (!SameRoot(from, to))
        {
            // Another volume: copy, then delete below.
        }

        Copy(from, to);
        Delete(from);
    }

    private static bool SameRoot(string a, string b) =>
        string.Equals(Path.GetPathRoot(Path.GetFullPath(a)), Path.GetPathRoot(Path.GetFullPath(b)), StringComparison.OrdinalIgnoreCase);

    private static void Copy(string from, string to)
    {
        Directory.CreateDirectory(to);
        foreach (var file in Directory.EnumerateFiles(from))
        {
            File.Copy(file, Path.Combine(to, Path.GetFileName(file)));
        }

        foreach (var folder in Directory.EnumerateDirectories(from))
        {
            Copy(folder, Path.Combine(to, Path.GetFileName(folder)));
        }
    }
}
