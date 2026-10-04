using System.IO.Enumeration;

namespace Launcher.Core.Files;

/// <summary>Which files a file picker offers (M7). Folders are always listed, so the user can move through them.</summary>
/// <param name="Extensions">Lower-case, each starting with '.'; empty offers every file.</param>
public sealed record FileFilter(string Name, IReadOnlyList<string> Extensions)
{
    /// <summary>Art the launcher can show (A4: PNG, JPEG or WebP).</summary>
    public static FileFilter Images { get; } = new("Images", [".png", ".jpg", ".jpeg", ".webp"]);

    /// <summary>A game's or theme's model (A7: glTF binary only).</summary>
    public static FileFilter Models { get; } = new("3D models", [".glb"]);

    /// <summary>What <c>ModelImportService</c> takes: a .glb, a zip of an OBJ model, or an .obj.</summary>
    public static FileFilter ModelImports { get; } = new("3D models", [".glb", ".zip", ".obj"]);

    /// <summary>An ES-DE gamelist, for importing a system's metadata and media (2026-10-04).</summary>
    public static FileFilter Gamelists { get; } = new("Gamelists", [".xml"]);

    /// <summary>Emulators: .exe on Windows (A5 rejects .bat and .cmd); any file elsewhere.</summary>
    public static FileFilter Executables { get; } = new("Programs", OperatingSystem.IsWindows() ? [".exe"] : []);

    public bool Matches(ReadOnlySpan<char> fileName)
    {
        if (Extensions.Count == 0)
        {
            return true;
        }

        var extension = Path.GetExtension(fileName);
        foreach (var wanted in Extensions)
        {
            if (extension.Equals(wanted, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }
}

/// <summary>One folder or file in a listing.</summary>
public readonly record struct DirectoryEntry(string Name, bool IsFolder, long SizeBytes, DateTime ModifiedUtc);

/// <summary>A folder's contents, sorted: folders first, then files, each in natural order ignoring case.</summary>
/// <param name="Problem">Why the folder couldn't be listed, written for the user; null when it was.</param>
/// <param name="FilteredOut">Files left out because the filter didn't match them.</param>
public sealed record DirectoryListingResult(string Folder, IReadOnlyList<DirectoryEntry> Entries, string? Problem, int FilteredOut)
{
    public bool Failed => Problem is not null;
}

/// <summary>
/// Lists one folder for the pickers (M7). It never throws for a folder that can't be read: a missing folder, a
/// refused one, a drive with no disc and a network share that's gone all come back as a <see cref="DirectoryListingResult.Problem"/>.
/// Hidden and system entries are skipped, and so are entries that can't be read. Listing a folder on a slow share can
/// take many seconds and can't be interrupted inside one directory read, so the pickers call it on a dedicated
/// thread and simply stop waiting when the user moves on.
/// </summary>
public static class DirectoryListing
{
    // Win32 errors, as IOException.HResult & 0xFFFF.
    private const int ErrorAccessDenied = 5;
    private const int ErrorNotReady = 21;
    private const int ErrorUnexpectedNetworkError = 59;
    private const int ErrorBadNetworkPath = 53;
    private const int ErrorNetworkNameDeleted = 64;
    private const int ErrorBadNetworkName = 67;
    private const int ErrorSemaphoreTimeout = 121;
    private const int ErrorConnectionUnavailable = 1201;
    private const int ErrorNetworkUnreachable = 1231;
    private const int ErrorHostUnreachable = 1232;
    private const int ErrorLogonFailure = 1326;

    /// <param name="filter">Which files to include; null lists folders only (the folder picker).</param>
    /// <param name="progress">Counts entries read so far, so a picker can say how far a slow listing has got.</param>
    public static DirectoryListingResult List(string folder, FileFilter? filter, CancellationToken cancellationToken, ListingProgress? progress = null)
    {
        ArgumentNullException.ThrowIfNull(folder);
        var filteredOut = 0;
        var options = new EnumerationOptions
        {
            IgnoreInaccessible = true,
            AttributesToSkip = FileAttributes.Hidden | FileAttributes.System,
            RecurseSubdirectories = false,
            ReturnSpecialDirectories = false,

            // Fewer round trips on a network share (A1 Scanning).
            BufferSize = 256 * 1024,
        };

        var entries = new List<DirectoryEntry>();
        try
        {
            var enumerable = new FileSystemEnumerable<DirectoryEntry>(
                folder,
                (ref FileSystemEntry e) => new DirectoryEntry(e.FileName.ToString(), e.IsDirectory, e.IsDirectory ? 0 : e.Length, e.LastWriteTimeUtc.UtcDateTime),
                options)
            {
                ShouldIncludePredicate = (ref FileSystemEntry e) =>
                {
                    if (e.IsDirectory)
                    {
                        return true;
                    }

                    if (filter is not null && filter.Matches(e.FileName))
                    {
                        return true;
                    }

                    filteredOut++;
                    return false;
                },
            };

            foreach (var entry in enumerable)
            {
                cancellationToken.ThrowIfCancellationRequested();
                entries.Add(entry);
                if (progress is not null)
                {
                    progress.Value = entries.Count;
                }
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or System.Security.SecurityException or ArgumentException)
        {
            return new DirectoryListingResult(folder, [], Explain(folder, e), 0);
        }

        entries.Sort(static (a, b) => a.IsFolder != b.IsFolder ? (a.IsFolder ? -1 : 1) : NaturalComparer.Instance.Compare(a.Name, b.Name));
        return new DirectoryListingResult(folder, entries, null, filteredOut);
    }

    /// <summary>Why a folder couldn't be listed, in words the user can act on.</summary>
    public static string Explain(string folder, Exception exception)
    {
        ArgumentNullException.ThrowIfNull(exception);
        return exception switch
        {
            DirectoryNotFoundException => $"{folder} doesn't exist any more, or its drive isn't connected.",
            UnauthorizedAccessException or System.Security.SecurityException => $"You don't have permission to open {folder}.",
            ArgumentException => $"'{folder}' isn't a valid folder path.",
            IOException io => (io.HResult & 0xFFFF) switch
            {
                ErrorNotReady => $"{folder} isn't ready. Is there a disc or card in the drive?",
                ErrorBadNetworkPath or ErrorBadNetworkName or ErrorNetworkNameDeleted or ErrorUnexpectedNetworkError
                    or ErrorSemaphoreTimeout or ErrorConnectionUnavailable or ErrorNetworkUnreachable or ErrorHostUnreachable =>
                    $"{folder} can't be reached. Check the computer or NAS that shares it is on and connected, then try again.",
                ErrorAccessDenied or ErrorLogonFailure => $"You don't have permission to open {folder}.",
                _ => $"{folder} couldn't be read: {io.Message}",
            },
            _ => $"{folder} couldn't be read: {exception.Message}",
        };
    }
}

/// <summary>A counter one thread writes and another reads (a listing's progress).</summary>
public sealed class ListingProgress
{
    private int _value;

    public int Value
    {
        get => Volatile.Read(ref _value);
        set => Volatile.Write(ref _value, value);
    }
}

/// <summary>Case-insensitive order with runs of digits compared as numbers: "Disc 2" before "Disc 10".</summary>
public sealed class NaturalComparer : IComparer<string>
{
    public static NaturalComparer Instance { get; } = new();

    public int Compare(string? x, string? y)
    {
        if (ReferenceEquals(x, y))
        {
            return 0;
        }

        if (x is null || y is null)
        {
            return x is null ? -1 : 1;
        }

        int i = 0, j = 0;
        while (i < x.Length && j < y.Length)
        {
            if (char.IsAsciiDigit(x[i]) && char.IsAsciiDigit(y[j]))
            {
                var startX = i;
                var startY = j;
                while (i < x.Length && char.IsAsciiDigit(x[i]))
                {
                    i++;
                }

                while (j < y.Length && char.IsAsciiDigit(y[j]))
                {
                    j++;
                }

                var a = x.AsSpan(startX, i - startX).TrimStart('0');
                var b = y.AsSpan(startY, j - startY).TrimStart('0');
                var byNumber = a.Length != b.Length ? a.Length.CompareTo(b.Length) : a.SequenceCompareTo(b);
                if (byNumber != 0)
                {
                    return byNumber;
                }

                continue;
            }

            var byChar = char.ToUpperInvariant(x[i]).CompareTo(char.ToUpperInvariant(y[j]));
            if (byChar != 0)
            {
                return byChar;
            }

            i++;
            j++;
        }

        var byLength = (x.Length - i).CompareTo(y.Length - j);
        return byLength != 0 ? byLength : string.CompareOrdinal(x, y);
    }
}

/// <summary>
/// Jump-to-letter for long lists (the pickers' triggers, as the games grid's): entries are grouped by their first
/// letter, digits and symbols together as '#'.
/// </summary>
public static class LetterJump
{
    public static char GroupOf(string name)
    {
        ArgumentNullException.ThrowIfNull(name);
        foreach (var c in name)
        {
            if (char.IsLetter(c))
            {
                // Accents group with their letter: "École" with E.
                var plain = c.ToString().Normalize(System.Text.NormalizationForm.FormD)[0];
                return char.ToUpperInvariant(plain);
            }

            if (!char.IsWhiteSpace(c) && c is not ('(' or '[' or '.' or '_'))
            {
                return '#';
            }
        }

        return '#';
    }

    /// <summary>The first entry after <paramref name="index"/> in another group; the last entry if there's none.</summary>
    public static int Next(int count, Func<int, string> nameAt, int index)
    {
        ArgumentNullException.ThrowIfNull(nameAt);
        if (count == 0)
        {
            return -1;
        }

        index = Math.Clamp(index, 0, count - 1);
        var group = GroupOf(nameAt(index));
        for (var i = index + 1; i < count; i++)
        {
            if (GroupOf(nameAt(i)) != group)
            {
                return i;
            }
        }

        return count - 1;
    }

    /// <summary>The start of <paramref name="index"/>'s group, or of the group before when it's already there.</summary>
    public static int Previous(int count, Func<int, string> nameAt, int index)
    {
        ArgumentNullException.ThrowIfNull(nameAt);
        if (count == 0)
        {
            return -1;
        }

        index = Math.Clamp(index, 0, count - 1);
        var start = StartOfGroup(nameAt, index);
        return start < index ? start : start == 0 ? 0 : StartOfGroup(nameAt, start - 1);
    }

    private static int StartOfGroup(Func<int, string> nameAt, int index)
    {
        var group = GroupOf(nameAt(index));
        while (index > 0 && GroupOf(nameAt(index - 1)) == group)
        {
            index--;
        }

        return index;
    }
}
