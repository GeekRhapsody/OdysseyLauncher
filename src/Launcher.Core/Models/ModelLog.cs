using System.Globalization;
using Launcher.Core.Diagnostics;

namespace Launcher.Core.Models;

/// <summary>
/// The log of model problems the user can read (A7): <c>DataDir/logs/models.log</c>, one line per message with its
/// time and level, written by the app when it processes a model (a rejected model names why, and what's used
/// instead) and by the import service. The settings UI (M7) shows <see cref="ReadRecent"/>; <c>odyssey-scrape
/// models-log</c> prints it. Kept to about 1 MB: the older half moves to <c>models.1.log</c>. Thread-safe.
/// </summary>
public sealed class ModelLog : ILog
{
    public const string FileName = "models.log";
    public const string PreviousFileName = "models.1.log";
    public const long MaxBytes = 1024 * 1024;

    private readonly object _lock = new();
    private readonly TimeProvider _clock;

    public ModelLog(string dataDir, TimeProvider? clock = null)
    {
        ArgumentNullException.ThrowIfNull(dataDir);
        Path = PathIn(dataDir);
        _clock = clock ?? TimeProvider.System;
    }

    /// <summary>The log file's path.</summary>
    public string Path { get; }

    public static string PathIn(string dataDir) => System.IO.Path.Combine(dataDir, "logs", FileName);

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
                    File.Move(Path, System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Path)!, PreviousFileName), overwrite: true);
                }

                File.AppendAllText(Path, line);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                // A log that can't be written mustn't stop a model loading.
            }
        }
    }

    /// <summary>A report's errors, warnings and notes, each on its own line, about <paramref name="source"/>.</summary>
    public void Report(string source, ModelReport report, string? outcome = null)
    {
        ArgumentNullException.ThrowIfNull(report);
        foreach (var error in report.Errors)
        {
            Write(LogLevel.Error, $"{source}: {error}");
        }

        foreach (var warning in report.Warnings)
        {
            Write(LogLevel.Warning, $"{source}: {warning}");
        }

        foreach (var note in report.Notes)
        {
            Write(LogLevel.Info, $"{source}: {note}");
        }

        Write(report.Accepted ? LogLevel.Info : LogLevel.Error, $"{source}: {report.Summary()}{(outcome is null ? string.Empty : ". " + outcome)}");
    }

    /// <summary>The last <paramref name="lines"/> lines of the log, oldest first (empty if there's none).</summary>
    public static IReadOnlyList<string> ReadRecent(string dataDir, int lines = 200)
    {
        ArgumentNullException.ThrowIfNull(dataDir);
        var path = PathIn(dataDir);
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
