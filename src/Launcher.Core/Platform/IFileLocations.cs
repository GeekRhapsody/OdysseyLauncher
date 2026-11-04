namespace Launcher.Core.Platform;

/// <summary>What a place the pickers start from is (M7).</summary>
public enum LocationKind
{
    /// <summary>A quick-access folder: the user's folder, Desktop, Downloads, the ROM root.</summary>
    Folder,
    Fixed,
    Removable,
    Network,
    Optical,
    Other,
}

/// <summary>A place the folder and file pickers list at their top level.</summary>
/// <param name="Path">The folder to open: <c>C:\</c>, <c>Z:\</c>, a quick-access folder.</param>
/// <param name="Label">What to call it: "Local disk (C:)", "Desktop".</param>
/// <param name="Detail">More about it: a mapped drive's share (<c>\\nas\roms</c>), "disconnected".</param>
/// <param name="Available">False for a place that can't be opened now (a mapped drive that isn't connected).</param>
public sealed record FileLocation(string Path, string Label, LocationKind Kind, string? Detail, bool Available = true);

/// <summary>
/// The drives and quick-access folders the pickers offer (M7). Listing must never hang the caller on a slow or
/// disconnected network drive, so it's split: <see cref="Drives"/> and <see cref="QuickAccess"/> are fast (no volume
/// or network queries), and <see cref="VolumeLabel"/>, which can block for tens of seconds on a disconnected share,
/// is called on a worker, with the caller not waiting for it.
/// </summary>
public interface IFileLocations
{
    /// <summary>Every drive letter (Windows) or the file system's root and the USB drives and shares mounted (Linux), with its type, and a mapped drive's share. Fast.</summary>
    IReadOnlyList<FileLocation> Drives();

    /// <summary>A drive's volume label, or null. May block: call it on a worker, and don't wait on it.</summary>
    string? VolumeLabel(string root);

    /// <summary>The user's folder, Desktop and Downloads, those that exist. Fast.</summary>
    IReadOnlyList<FileLocation> QuickAccess();
}
