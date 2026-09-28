using System.Text;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Builds a Windows command line that the Microsoft C runtime (and <c>CommandLineToArgvW</c>) splits back into
/// exactly the arguments given. Windows passes a process one UTF-16 string, not an argv, so every argument has to
/// be quoted by these rules:
/// <list type="bullet">
/// <item>An argument with no space, tab, newline or double quote, and not empty, goes in as it is.</item>
/// <item>Anything else is wrapped in double quotes. Inside them, backslashes are literal unless they come before a
/// double quote: then 2n backslashes stand for n, and 2n+1 for n followed by a literal quote.</item>
/// </list>
/// Non-ASCII text needs nothing special: the command line is UTF-16 end to end (<c>CreateProcessW</c>).
/// There's no cmd.exe in the path, so <c>&amp;</c>, <c>%</c>, <c>^</c> and <c>|</c> are ordinary characters.
/// </summary>
public static class WindowsCommandLine
{
    /// <summary>The longest command line <c>CreateProcessW</c> accepts, in UTF-16 units, including the terminator.</summary>
    public const int MaxLength = 32_767;

    /// <summary>
    /// The program name comes first. The C runtime reads it with simpler rules (quotes, no escapes), which is
    /// fine because a Windows path can't contain a double quote.
    /// </summary>
    public static string Build(string executable, IReadOnlyList<string> arguments)
    {
        ArgumentNullException.ThrowIfNull(executable);
        ArgumentNullException.ThrowIfNull(arguments);
        if (executable.Contains('"', StringComparison.Ordinal))
        {
            throw new ArgumentException("A Windows path can't contain a double quote.", nameof(executable));
        }

        var builder = new StringBuilder(executable.Length + 2 + (arguments.Count * 16));
        builder.Append('"').Append(executable).Append('"');
        foreach (var argument in arguments)
        {
            builder.Append(' ');
            AppendArgument(builder, argument);
        }

        return builder.ToString();
    }

    /// <summary>Quotes one argument, if it needs it.</summary>
    public static string Quote(string argument)
    {
        ArgumentNullException.ThrowIfNull(argument);
        var builder = new StringBuilder(argument.Length + 2);
        AppendArgument(builder, argument);
        return builder.ToString();
    }

    private static void AppendArgument(StringBuilder builder, string argument)
    {
        if (argument.Length > 0 && argument.AsSpan().IndexOfAny(" \t\n\v\"") < 0)
        {
            builder.Append(argument);
            return;
        }

        builder.Append('"');
        var i = 0;
        while (i < argument.Length)
        {
            var backslashes = 0;
            while (i < argument.Length && argument[i] == '\\')
            {
                backslashes++;
                i++;
            }

            if (i == argument.Length)
            {
                // Before the closing quote: double them, so none escapes it.
                builder.Append('\\', backslashes * 2);
                break;
            }

            if (argument[i] == '"')
            {
                builder.Append('\\', (backslashes * 2) + 1).Append('"');
            }
            else
            {
                builder.Append('\\', backslashes).Append(argument[i]);
            }

            i++;
        }

        builder.Append('"');
    }
}
