using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Launcher.Core.Files;

/// <summary>What a picker is for, so each remembers its own last folder (M7).</summary>
public static class PickerUses
{
    public const string RomRoot = "rom-root";
    public const string RomFolder = "rom-folder";
    public const string Emulator = "emulator";
    public const string Image = "image";
    public const string Model = "model";
    public const string Gamelist = "gamelist";
    public const string MediaFolder = "media-folder";
}

/// <summary>
/// The last folder each picker use was in (<see cref="PickerUses"/>), kept in <c>DataDir/picker-locations.json</c> so
/// the next pick of the same kind starts there, across sessions. Losing the file loses nothing that matters.
/// Thread-safe; <see cref="Load"/> and <see cref="Save"/> do file I/O, so never call them on the main thread.
/// </summary>
public sealed class PickerHistory
{
    public const string FileName = "picker-locations.json";

    private readonly Dictionary<string, string> _folders;
    private readonly string? _file;
    private readonly object _lock = new();

    private PickerHistory(string? file, Dictionary<string, string> folders)
    {
        _file = file;
        _folders = folders;
    }

    /// <summary>A history that isn't saved anywhere (tests, and a run with no data folder).</summary>
    public static PickerHistory InMemory() => new(null, new Dictionary<string, string>(StringComparer.Ordinal));

    /// <summary>Reads the file in <paramref name="dataDir"/>; a missing or unreadable file starts empty.</summary>
    public static PickerHistory Load(string dataDir)
    {
        ArgumentNullException.ThrowIfNull(dataDir);
        var file = Path.Combine(dataDir, FileName);
        var folders = new Dictionary<string, string>(StringComparer.Ordinal);
        try
        {
            if (File.Exists(file) && JsonSerializer.Deserialize(File.ReadAllText(file), PickerJsonContext.Default.DictionaryStringString) is { } saved)
            {
                foreach (var (use, folder) in saved)
                {
                    if (!string.IsNullOrWhiteSpace(folder) && Path.IsPathFullyQualified(folder))
                    {
                        folders[use] = folder;
                    }
                }
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or JsonException)
        {
            // Only a convenience: start again.
        }

        return new PickerHistory(file, folders);
    }

    public string? Get(string use)
    {
        ArgumentNullException.ThrowIfNull(use);
        lock (_lock)
        {
            return _folders.TryGetValue(use, out var folder) ? folder : null;
        }
    }

    public void Set(string use, string folder)
    {
        ArgumentNullException.ThrowIfNull(use);
        ArgumentNullException.ThrowIfNull(folder);
        lock (_lock)
        {
            _folders[use] = folder;
        }
    }

    /// <summary>Writes the file (a temporary file, then a move). Failures are ignored: it's only a convenience.</summary>
    public void Save()
    {
        if (_file is null)
        {
            return;
        }

        string json;
        lock (_lock)
        {
            json = JsonSerializer.Serialize(new SortedDictionary<string, string>(_folders, StringComparer.Ordinal), PickerJsonContext.Default.SortedDictionaryStringString);
        }

        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(_file)!);
            var temporary = _file + ".saving";
            File.WriteAllText(temporary, json, new UTF8Encoding(false));
            File.Move(temporary, _file, overwrite: true);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
        }
    }
}

[JsonSourceGenerationOptions(WriteIndented = true)]
[JsonSerializable(typeof(Dictionary<string, string>))]
[JsonSerializable(typeof(SortedDictionary<string, string>))]
internal sealed partial class PickerJsonContext : JsonSerializerContext;
