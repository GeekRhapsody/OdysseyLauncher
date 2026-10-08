using System.Text;
using Launcher.Core.Config;

namespace Launcher.Core.Platform;

/// <summary>
/// The rendering driver the engine starts with (<c>[display] rendering_driver</c>, 2026-10-08). The engine chooses it
/// before any of our code runs, so the choice goes into Godot's <c>override.cfg</c> beside the executable, which an
/// exported build reads at start-up over its project settings. Direct3D 12 is the project's own driver, so choosing it
/// takes the line out (and the file, when nothing else is in it); Vulkan writes it. Other lines in the file are kept.
/// Windows only: Linux uses Vulkan already.
/// </summary>
public static class RenderingOverride
{
    public const string FileName = "override.cfg";

    public const string Section = "rendering";

    /// <summary>The project setting, inside <see cref="Section"/>.</summary>
    public const string DriverKey = "rendering_device/driver.windows";

    /// <summary>The driver <c>override.cfg</c> in <paramref name="executableDir"/> asks for; null when it asks for none. Does file I/O.</summary>
    public static RenderingDriver? Read(string executableDir)
    {
        var path = Path.Combine(executableDir, FileName);
        try
        {
            return File.Exists(path) ? DriverIn(File.ReadAllText(path)) : null;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    /// <summary>
    /// Makes <c>override.cfg</c> in <paramref name="executableDir"/> ask for <paramref name="driver"/>, writing only when
    /// that changes it. Does file I/O. Returns why it couldn't, written for the user, or null.
    /// </summary>
    public static string? Write(string executableDir, RenderingDriver driver)
    {
        var path = Path.Combine(executableDir, FileName);
        try
        {
            var existing = File.Exists(path) ? File.ReadAllText(path) : null;
            var merged = Merge(existing, driver);
            if (merged == existing)
            {
                return null;
            }

            if (merged is null)
            {
                File.Delete(path);
            }
            else
            {
                File.WriteAllText(path, merged, new UTF8Encoding(false));
            }

            return null;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return $"Couldn't write {path}: {e.Message}";
        }
    }

    /// <summary>The driver an <c>override.cfg</c>'s text asks for; null when it asks for none (or one we don't offer).</summary>
    public static RenderingDriver? DriverIn(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var section = string.Empty;
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim();
            if (SectionOf(line) is { } name)
            {
                section = name;
            }
            else if (section == Section && KeyOf(line) == DriverKey)
            {
                var value = line[(line.IndexOf('=', StringComparison.Ordinal) + 1)..].Trim().Trim('"');
                return DisplayNames.TryParse(value, out RenderingDriver driver) ? driver : null;
            }
        }

        return null;
    }

    /// <summary>
    /// <paramref name="existing"/> (null: no file) with the driver line for <paramref name="driver"/>, every other line
    /// kept. Null when the file would hold nothing but section headings and blank lines.
    /// </summary>
    public static string? Merge(string? existing, RenderingDriver driver)
    {
        var lines = new List<string>();
        if (existing is not null)
        {
            lines.AddRange(existing.Replace("\r\n", "\n", StringComparison.Ordinal).Split('\n'));
            if (lines.Count > 0 && lines[^1].Length == 0)
            {
                lines.RemoveAt(lines.Count - 1);
            }
        }

        // Take out every driver line in [rendering], noting where the section starts.
        var section = string.Empty;
        var heading = -1;
        for (var i = 0; i < lines.Count; i++)
        {
            var line = lines[i].Trim();
            if (SectionOf(line) is { } name)
            {
                section = name;
                if (name == Section && heading < 0)
                {
                    heading = i;
                }
            }
            else if (section == Section && KeyOf(line) == DriverKey)
            {
                lines.RemoveAt(i--);
            }
        }

        if (driver != RenderingDriver.D3D12)
        {
            var entry = $"{DriverKey}=\"{DisplayNames.Name(driver)}\"";
            if (heading >= 0)
            {
                lines.Insert(heading + 1, entry);
            }
            else
            {
                if (lines.Count > 0 && lines[^1].Trim().Length > 0)
                {
                    lines.Add(string.Empty);
                }

                lines.Add($"[{Section}]");
                lines.Add(entry);
            }
        }

        var meaningful = false;
        foreach (var line in lines)
        {
            var trimmed = line.Trim();
            if (trimmed.Length > 0 && SectionOf(trimmed) is null)
            {
                meaningful = true;
                break;
            }
        }

        return meaningful ? string.Join('\n', lines) + "\n" : null;
    }

    private static string? SectionOf(string line) =>
        line.Length > 2 && line[0] == '[' && line[^1] == ']' ? line[1..^1].Trim() : null;

    private static string? KeyOf(string line)
    {
        var equals = line.IndexOf('=', StringComparison.Ordinal);
        return equals > 0 && line[0] != ';' ? line[..equals].Trim() : null;
    }
}
