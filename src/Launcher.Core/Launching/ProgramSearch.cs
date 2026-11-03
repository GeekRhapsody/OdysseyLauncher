using Launcher.Core.Config;

namespace Launcher.Core.Launching;

/// <summary>
/// Finds an emulator profile's program and core among the places its <c>executable</c> and <c>core</c> list
/// (ARCHITECTURE.md A5, "Finding programs"): the first place that has the file wins. A bare
/// name (no folder) is looked for in the PATH's folders, as a shell would; a <c>*</c> in a file name matches the files
/// in its folder, the most recently written winning (an AppImage carries its version in its name); anything else is a
/// path that must exist. Does file I/O: never on the main thread.
/// </summary>
public sealed class ProgramSearch(Func<string, bool> fileExists, string? searchPath)
{
    // Inaccessible folders are skipped rather than thrown on, the folder searched too: it just has no match.
    private static readonly EnumerationOptions Matching = new() { IgnoreInaccessible = true, MatchType = MatchType.Simple };

    /// <summary>The real file system and this process's PATH.</summary>
    public static ProgramSearch System { get; } = new(File.Exists, Environment.GetEnvironmentVariable("PATH"));

    /// <summary>A place with no folder, which is looked for on the PATH.</summary>
    public static bool IsBareName(string place) => place.Length > 0 && place.IndexOfAny(['/', '\\']) < 0;

    /// <summary>The first of <paramref name="places"/> that has the file, or null.</summary>
    public string? Find(IReadOnlyList<string> places)
    {
        ArgumentNullException.ThrowIfNull(places);
        foreach (var place in places)
        {
            if (FindOne(place) is { } found)
            {
                return found;
            }
        }

        return null;
    }

    /// <summary>
    /// <paramref name="emulator"/> with the program and core it found in place of its first places, and whether each
    /// was found (a profile without a core counts its core as found). A run_file profile has nothing to find.
    /// </summary>
    public (EmulatorConfig Emulator, bool ProgramFound, bool CoreFound) Resolve(EmulatorConfig emulator)
    {
        ArgumentNullException.ThrowIfNull(emulator);
        if (emulator.RunFile)
        {
            return (emulator, true, true);
        }

        var program = Find(emulator.ProgramPlaces);
        var core = emulator.CorePlaces is { } cores ? Find(cores) : null;
        var found = emulator with { Executable = program ?? emulator.Executable, Core = core ?? emulator.Core };
        return (found, program is not null, emulator.Core is null || core is not null);
    }

    private string? FindOne(string place)
    {
        if (IsBareName(place))
        {
            return OnPath(place);
        }

        var name = Path.GetFileName(place);
        if (!name.Contains('*', StringComparison.Ordinal))
        {
            return fileExists(place) ? place : null;
        }

        // Only the file name can have a wildcard, not its folder.
        var folder = Path.GetDirectoryName(place);
        if (string.IsNullOrEmpty(folder) || folder.Contains('*', StringComparison.Ordinal) || !Directory.Exists(folder))
        {
            return null;
        }

        string? newest = null;
        var newestWritten = DateTime.MinValue;
        foreach (var file in Directory.EnumerateFiles(folder, name, Matching))
        {
            var written = File.GetLastWriteTimeUtc(file);
            if (newest is null || written > newestWritten)
            {
                newest = file;
                newestWritten = written;
            }
        }

        return newest;
    }

    private string? OnPath(string name)
    {
        if (searchPath is null)
        {
            return null;
        }

        foreach (var folder in searchPath.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            // A relative PATH entry would find a program by the launcher's working folder: never meant for a game.
            if (!Path.IsPathRooted(folder))
            {
                continue;
            }

            var path = Path.Combine(folder, name);
            if (fileExists(path))
            {
                return path;
            }
        }

        return null;
    }
}
