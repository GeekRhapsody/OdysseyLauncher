using System.Text;
using System.Text.RegularExpressions;

namespace Launcher.Core.Diagnostics;

/// <summary>
/// Removes credentials from text before it's logged or saved (ARCHITECTURE.md A5). Two passes: every known credential
/// value (as written, URL-encoded and JSON-escaped) becomes <c>***</c>, and so does the value of every URL
/// parameter or header that carries one, known or not: ScreenScraper echoes its full request URL in each
/// response and embeds the credentials in every media URL.
/// </summary>
public sealed partial class Redactor
{
    public const string Mask = "***";

    private readonly string[] _values;

    /// <param name="values">Credential values. Blank ones are ignored, and so are values under 4 characters, which would mangle ordinary text.</param>
    public Redactor(IEnumerable<string> values)
    {
        ArgumentNullException.ThrowIfNull(values);
        var forms = new HashSet<string>(StringComparer.Ordinal);
        foreach (var value in values)
        {
            if (string.IsNullOrWhiteSpace(value) || value.Length < 4)
            {
                continue;
            }

            forms.Add(value);
            forms.Add(Uri.EscapeDataString(value));
            forms.Add(System.Net.WebUtility.UrlEncode(value));
            forms.Add(System.Text.Json.JsonEncodedText.Encode(value).Value);
        }

        // Longest first, so a value containing another is masked whole.
        _values = [.. forms.OrderByDescending(f => f.Length)];
    }

    public static Redactor None { get; } = new([]);

    public string Redact(string? text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return text ?? string.Empty;
        }

        var result = text;
        if (_values.Length > 0)
        {
            var builder = new StringBuilder(result);
            foreach (var value in _values)
            {
                builder.Replace(value, Mask);
            }

            result = builder.ToString();
        }

        result = SecretParameter().Replace(result, m => m.Groups[1].Value + Mask);
        return BearerToken().Replace(result, m => m.Groups[1].Value + Mask);
    }

    /// <summary>
    /// A URL or form parameter that carries a credential: <c>devpassword=...</c>, also when its '&amp;' is JSON-escaped
    /// (<c>&</c>) or HTML-escaped (<c>&amp;amp;</c>). The value runs to the next separator or quote.
    /// </summary>
    [GeneratedRegex(@"((?:^|[?&;\s""']|\\u0026|&amp;)(?:devid|devpassword|ssid|sspassword|client_id|client_secret|access_token|api_key|apikey|key|password)=)[^&""'\s\\<>]*",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex SecretParameter();

    [GeneratedRegex(@"((?:Bearer|OAuth)\s+)[A-Za-z0-9\-._~+/=]{8,}", RegexOptions.CultureInvariant)]
    private static partial Regex BearerToken();
}

public enum LogLevel
{
    Info,
    Warning,
    Error,
}

/// <summary>A minimal log sink. Messages are already redacted when they arrive (see <see cref="RedactingLog"/>).</summary>
public interface ILog
{
    void Write(LogLevel level, string message);
}

/// <summary>Discards everything.</summary>
public sealed class NullLog : ILog
{
    public static NullLog Instance { get; } = new();

    public void Write(LogLevel level, string message)
    {
    }
}

/// <summary>Redacts every message before passing it on.</summary>
public sealed class RedactingLog(ILog inner, Redactor redactor) : ILog
{
    public void Write(LogLevel level, string message) => inner.Write(level, redactor.Redact(message));
}
