using Launcher.Core.Config;

namespace Launcher.Core.Scraping;

/// <summary>What <see cref="ProviderAccounts.Load"/> read, and any problems with the file (never quoting a value).</summary>
public sealed record AccountsLoadResult(ProviderAccounts Accounts, IReadOnlyList<Diagnostic> Diagnostics);

/// <summary>
/// The scraping providers' credentials (ARCHITECTURE.md A5): <c>ConfigDir/secrets.toml</c>, overridden per value by
/// <c>ODYSSEY_*</c> environment variables. They exist nowhere else: never in the repo, logs, saved responses or
/// bench output. <see cref="ToString"/> never shows a value.
/// <code>
/// [screenscraper]      # ODYSSEY_SCREENSCRAPER_DEV_ID, _DEV_PASSWORD, _USERNAME, _PASSWORD
/// dev_id = "..."       # developer credentials, issued by ScreenScraper for this software
/// dev_password = "..."
/// username = "..."     # your ScreenScraper account (optional: without it, anonymous limits apply)
/// password = "..."
///
/// [steamgriddb]        # ODYSSEY_STEAMGRIDDB_API_KEY
/// api_key = "..."
///
/// [igdb]               # ODYSSEY_IGDB_CLIENT_ID, ODYSSEY_IGDB_CLIENT_SECRET (a Twitch application's)
/// client_id = "..."
/// client_secret = "..."
/// </code>
/// </summary>
public sealed class ProviderAccounts
{
    public const string FileName = "secrets.toml";

    private static readonly (string Section, string Key, string Env)[] Entries =
    [
        ("screenscraper", "dev_id", "ODYSSEY_SCREENSCRAPER_DEV_ID"),
        ("screenscraper", "dev_password", "ODYSSEY_SCREENSCRAPER_DEV_PASSWORD"),
        ("screenscraper", "username", "ODYSSEY_SCREENSCRAPER_USERNAME"),
        ("screenscraper", "password", "ODYSSEY_SCREENSCRAPER_PASSWORD"),
        ("steamgriddb", "api_key", "ODYSSEY_STEAMGRIDDB_API_KEY"),
        ("igdb", "client_id", "ODYSSEY_IGDB_CLIENT_ID"),
        ("igdb", "client_secret", "ODYSSEY_IGDB_CLIENT_SECRET"),
    ];

    private readonly Dictionary<string, string> _values;

    private ProviderAccounts(Dictionary<string, string> values) => _values = values;

    /// <summary>No credentials at all.</summary>
    public static ProviderAccounts None { get; } = new(new Dictionary<string, string>(StringComparer.Ordinal));

    public string? ScreenScraperDevId => Get("screenscraper.dev_id");

    public string? ScreenScraperDevPassword => Get("screenscraper.dev_password");

    public string? ScreenScraperUsername => Get("screenscraper.username");

    public string? ScreenScraperPassword => Get("screenscraper.password");

    public string? SteamGridDbApiKey => Get("steamgriddb.api_key");

    public string? IgdbClientId => Get("igdb.client_id");

    public string? IgdbClientSecret => Get("igdb.client_secret");

    /// <summary>Every value set, for redaction.</summary>
    public IReadOnlyCollection<string> Values => _values.Values;

    /// <summary>For tests and tools: values from code, keyed "section.key" (e.g. "igdb.client_id").</summary>
    public static ProviderAccounts FromValues(IReadOnlyDictionary<string, string> values)
    {
        ArgumentNullException.ThrowIfNull(values);
        var copy = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (key, value) in values)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                copy[key] = value.Trim();
            }
        }

        return new ProviderAccounts(copy);
    }

    /// <summary>Reads <c>secrets.toml</c> from <paramref name="configDir"/> and the environment. Does file I/O: never on the main thread.</summary>
    public static AccountsLoadResult Load(string configDir, Func<string, string?>? environment = null)
    {
        ArgumentNullException.ThrowIfNull(configDir);
        var path = Path.Combine(configDir, FileName);
        var text = File.Exists(path) ? File.ReadAllText(path) : null;
        return Parse(text, path, environment ?? Environment.GetEnvironmentVariable);
    }

    /// <param name="text">The file's text, or null when there's no file.</param>
    public static AccountsLoadResult Parse(string? text, string source, Func<string, string?> environment)
    {
        ArgumentNullException.ThrowIfNull(source);
        ArgumentNullException.ThrowIfNull(environment);
        var diagnostics = new List<Diagnostic>();
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        var tree = text is null ? null : TomlTree.Parse(text, source, diagnostics);

        // A parser message can quote the text it choked on, which here may be a credential: keep only the position.
        for (var i = 0; i < diagnostics.Count; i++)
        {
            var d = diagnostics[i];
            diagnostics[i] = d with { Message = "TOML syntax error, so the file is ignored (the parser's message isn't shown: it may quote a credential)" };
        }
        if (tree is not null)
        {
            foreach (var sectionName in tree.Keys)
            {
                tree.TryGet(sectionName, out var sectionNode);
                if (sectionName == "format")
                {
                    continue;
                }

                if (!Array.Exists(Entries, e => e.Section == sectionName))
                {
                    diagnostics.Add(At(Severity.Warning, sectionNode, sectionName, "unknown section. It's ignored"));
                    continue;
                }

                if (sectionNode is not TomlTableNode section)
                {
                    diagnostics.Add(At(Severity.Error, sectionNode, sectionName, "expected a table"));
                    continue;
                }

                foreach (var key in section.Keys)
                {
                    section.TryGet(key, out var node);
                    var dotted = sectionName + "." + key;
                    if (!Array.Exists(Entries, e => e.Section == sectionName && e.Key == key))
                    {
                        diagnostics.Add(At(Severity.Warning, node, dotted, "unknown key. It's ignored"));
                    }
                    else if (node is TomlScalar { Kind: TomlKind.String, Value: string value })
                    {
                        if (!string.IsNullOrWhiteSpace(value))
                        {
                            values[dotted] = value.Trim();
                        }
                    }
                    else
                    {
                        // Never echo the value: it may have been typed without quotes.
                        diagnostics.Add(At(Severity.Error, node, dotted, "expected a string in quotes. It's ignored"));
                    }
                }
            }
        }

        foreach (var (section, key, env) in Entries)
        {
            if (environment(env) is { } value && !string.IsNullOrWhiteSpace(value))
            {
                values[section + "." + key] = value.Trim();
            }
        }

        return new AccountsLoadResult(new ProviderAccounts(values), diagnostics);
    }

    public override string ToString() => $"ProviderAccounts ({_values.Count} values set, redacted)";

    private string? Get(string key) => _values.TryGetValue(key, out var value) ? value : null;

    private static Diagnostic At(Severity severity, TomlNode node, string key, string message) =>
        new(severity, node.Pos.Source, node.Pos.Line, node.Pos.Column, key, message);
}
