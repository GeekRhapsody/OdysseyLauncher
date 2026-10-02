using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// Scraping (M7): the provider asked first (left and right change it in place), the fallbacks and their order, the
/// media to download, and each provider's credentials. The page says which providers are ready, which have no credentials, and whether an
/// <c>ODYSSEY_*</c> variable sets them.
/// </summary>
public sealed partial class ScrapingPage : ListPanel
{
    private static readonly string[] Providers = [ScraperIds.ScreenScraper, ScraperIds.Igdb, ScraperIds.SteamGridDb, ScraperIds.Steam];

    private readonly SettingsController _settings;
    private readonly Dictionary<string, SettingRow> _credentialRows = new(StringComparer.Ordinal);
    private int _check;

    public ScrapingPage(SettingsController settings)
        : base("Scraping")
    {
        _settings = settings;
        Subtitle = "[scraping] in settings.toml; credentials in secrets.toml";
        Build();
        SetHints("A  Choose     Left Right  Change     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    public static string NameOf(string provider) => provider switch
    {
        ScraperIds.ScreenScraper => "ScreenScraper",
        ScraperIds.Igdb => "IGDB",
        ScraperIds.SteamGridDb => "SteamGridDB",
        ScraperIds.Steam => "Steam store",
        _ => provider,
    };

    public static string AboutOf(string provider) => provider switch
    {
        ScraperIds.ScreenScraper => "Metadata and every kind of media, videos included",
        ScraperIds.Igdb => "Metadata, covers, screenshots and artwork",
        ScraperIds.SteamGridDb => "Community covers, heroes and logos; no metadata",
        ScraperIds.Steam => "Steam's own art and store metadata, for Windows and Steam games",
        _ => string.Empty,
    };

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    public override void OnRevealed() => CheckCredentials();

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        _credentialRows.Clear();
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var scraping = _settings.Services.Config.Settings.Scraping;
        AddSection("Order");
        var provider = AddRow("Default provider", "Asked first for every game", NameOf(scraping.Provider), ChooseProvider);
        provider.Adjuster = direction =>
        {
            var index = Array.IndexOf(Providers, scraping.Provider);
            SetProvider(Providers[(index + direction + Providers.Length) % Providers.Length]);
        };
        AddRow("Fallbacks", scraping.Fallback.Count == 0 ? "None: only the default provider is asked" : string.Join(", then ", scraping.Fallback.Select(NameOf)),
            null, () => Layer.Push(new FallbackPage(_settings)));

        AddSection("Media");
        AddRow("Media to scrape", ScrapeMediaPage.Summary(scraping.Media), null, () => Layer.Push(new ScrapeMediaPage(_settings)));

        AddSection("Providers");
        foreach (var id in Providers)
        {
            var captured = id;
            _credentialRows[id] = AddRow(NameOf(id), AboutOf(id), "Checking…", () => Layer.Push(new ProviderPage(_settings, captured)));
        }

        CheckCredentials();
    }

    /// <summary>Which providers have their credentials: reads secrets.toml, so off the main thread.</summary>
    private void CheckCredentials()
    {
        var check = ++_check;
        var configDir = _settings.Services.Paths.ConfigDir;
        _ = Task.Run(() =>
        {
            var accounts = ProviderAccounts.Load(configDir, builtIn: ProviderAccounts.BuiltIn).Accounts;
            var states = Providers.ToDictionary(p => p, p => ProviderPage.CredentialState(accounts, p));
            _settings.Ui.Queue.Post(() =>
            {
                if (check != _check)
                {
                    return;
                }

                foreach (var (id, (text, ready)) in states)
                {
                    if (_credentialRows.TryGetValue(id, out var row) && IsInstanceValid(row))
                    {
                        row.Value = text;
                        row.ValueColour = ready ? UiStyle.Good : UiStyle.Warning;
                    }
                }
            });
        });
    }

    private void ChooseProvider()
    {
        var current = _settings.Services.Config.Settings.Scraping.Provider;
        var choices = Providers.Select(p => new Choice(p, NameOf(p), AboutOf(p))).ToList();
        Layer.Push(new ChoicePanel("Default provider", "Asked first for every game; the fallbacks fill in what it doesn't have", choices, current, choice => SetProvider(choice.Id)));
    }

    /// <summary>Makes <paramref name="provider"/> the default; it leaves the fallbacks, and the old default takes its place there.</summary>
    private void SetProvider(string provider)
    {
        var scraping = _settings.Services.Config.Settings.Scraping;
        if (provider == scraping.Provider)
        {
            return;
        }

        var fallback = scraping.Fallback.Select(f => f == provider ? scraping.Provider : f).ToList();
        if (!fallback.Contains(scraping.Provider))
        {
            fallback.Insert(0, scraping.Provider);
        }

        fallback.Remove(provider);
        if (ConfigInput.CheckProviders(provider, fallback) is { } problem)
        {
            ShowStatus(problem, UiStyle.Bad, 5);
            return;
        }

        _settings.Save(this,
        [
            new ConfigEdit(ConfigFileKind.Settings, ["scraping", "provider"], provider),
            new ConfigEdit(ConfigFileKind.Settings, ["scraping", "fallback"], fallback),
        ], $"{NameOf(provider)} is asked first now.");
    }
}
