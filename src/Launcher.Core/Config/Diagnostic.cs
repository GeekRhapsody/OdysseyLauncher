using System.Globalization;

namespace Launcher.Core.Config;

public enum Severity
{
    Info,
    Warning,
    Error,
}

/// <summary>
/// A problem found in user input: a config file, or a file the scanner read.
/// </summary>
/// <param name="Source">The file, as named by whoever supplied it (a path, or e.g. <c>built-in/systems.toml</c>).</param>
/// <param name="Line">1-based line, or 0 when the problem isn't tied to a line.</param>
/// <param name="Column">1-based column, or 0 when the problem isn't tied to a column.</param>
/// <param name="Key">Dotted key path (<c>systems.megadrive.emulator</c>), or empty when there's no key.</param>
public sealed record Diagnostic(Severity Severity, string Source, int Line, int Column, string Key, string Message)
{
    public bool IsError => Severity == Severity.Error;

    /// <summary>Formats as <c>file:line:column: error: key: message</c>, leaving out the parts that are absent.</summary>
    public override string ToString()
    {
        var location = Line > 0
            ? Column > 0
                ? string.Create(CultureInfo.InvariantCulture, $"{Source}:{Line}:{Column}")
                : string.Create(CultureInfo.InvariantCulture, $"{Source}:{Line}")
            : Source;
        var severity = Severity switch
        {
            Severity.Error => "error",
            Severity.Warning => "warning",
            _ => "info",
        };
        return Key.Length > 0
            ? $"{location}: {severity}: {Key}: {Message}"
            : $"{location}: {severity}: {Message}";
    }
}
