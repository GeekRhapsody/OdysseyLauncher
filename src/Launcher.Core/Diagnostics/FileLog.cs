using System.Globalization;

namespace Launcher.Core.Diagnostics;

/// <summary>
/// A log the user can read, in a file under <c>DataDir/logs</c>: one line per message with its time and level. Kept
/// to about 1 MB: the older half moves to the previous file. Thread-safe, and a log that can't be written is
/// silent, so it never stops what it describes.
/// </summary>
public class FileLog : ILog
{
    public const long MaxBytes = 1024 * 1024;

    private readonly object _lock = new();
    private readonly TimeProvider _clock;
    private readonly string _previousFileName;

    public FileLog(string path, string previousFileName, TimeProvider? clock = null)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(previousFileName);
        Path = path;
        _previousFileName = previousFileName;
        _clock = clock ?? TimeProvider.System;
    }

    /// <summary>The log file's path.</summary>
    public string Path { get; }

    public void Write(LogLevel level, string message)
    {
        ArgumentNullException.ThrowIfNull(message);
        var line = string.Create(CultureInfo.InvariantCulture,
            $"{_clock.GetLocalNow():yyyy-MM-dd HH:mm:ss} {level.ToString().ToLowerInvariant()}: {message.ReplaceLineEndings(" ")}{Environment.NewLine}");
        lock (_lock)
        {
            try
            {
                Directory.CreateDirectory(System.IO.Path.GetDirectoryName(Path)!);
                if (File.Exists(Path) && new FileInfo(Path).Length > MaxBytes)
                {
                    File.Move(Path, System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Path)!, _previousFileName), overwrite: true);
                }

                File.AppendAllText(Path, line);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                // A log that can't be written mustn't stop what it describes.
            }
        }
    }

    /// <summary>The last <paramref name="lines"/> lines of the log at <paramref name="path"/>, oldest first (empty if there's none).</summary>
    public static IReadOnlyList<string> ReadLast(string path, int lines)
    {
        ArgumentNullException.ThrowIfNull(path);
        try
        {
            if (!File.Exists(path))
            {
                return [];
            }

            var all = File.ReadAllLines(path);
            return all.Length <= lines ? all : all[^lines..];
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return [];
        }
    }
}
