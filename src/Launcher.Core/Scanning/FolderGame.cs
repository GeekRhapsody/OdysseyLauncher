namespace Launcher.Core.Scanning;

/// <summary>
/// A game that is a folder named with one of its system's extensions (<c>Game.ps3</c>, <c>Game.ps4</c>), as ES-DE's
/// "directories interpreted as files" (<see cref="RomScanner"/>). The library doesn't record which games are folders:
/// the stages that care ask the disk when they run. Does file I/O: never on the main thread.
/// </summary>
public static class FolderGame
{
    /// <summary>Whether the game at <paramref name="romPath"/> is a folder.</summary>
    public static bool IsFolder(string romPath) => Directory.Exists(romPath);

    /// <summary>
    /// What the emulator is given for <paramref name="romPath"/>: a folder game's file of the folder's own name, when it
    /// holds one (<c>Jet Grind Radio.cue/Jet Grind Radio.cue</c>), else the folder itself (RPCS3 and shadPS4 take a
    /// game's folder). A file is given as it is.
    /// </summary>
    public static string LaunchTarget(string romPath)
    {
        ArgumentNullException.ThrowIfNull(romPath);
        if (!Directory.Exists(romPath))
        {
            return romPath;
        }

        var inner = Path.Combine(romPath, Path.GetFileName(Path.TrimEndingDirectorySeparator(romPath)));
        return File.Exists(inner) ? inner : romPath;
    }
}
