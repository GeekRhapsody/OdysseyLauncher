using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// Scraping (M7): "Scrape what's missing" (on the main page until 2026-11-07), the provider asked first (left and right change it in place), the fallbacks and their order, the
/// media to download, the regions preferred and their order (2026-10-04), and each provider's credentials. The page says which providers are ready, which have no credentials, and whether an
/// <c>ODYSSEY_*</c> variable sets them.
/// </summary>
public sealed partial class ScrapingPage : ListPanel
{
    private static readonly string[] Providers = [ScraperIds.ScreenScraper, ScraperIds.LaunchBox, ScraperIds.Igdb, ScraperIds.SteamGridDb, ScraperIds.Steam];

    private readonly SettingsController _settings;
    private readonly Dictionary<string, SettingRow> _credentialRows = new(StringComparer.Ordinal);
    private SettingRow _scrapeMissing = null!;
    private int _check;
    private bool _counting;

    public ScrapingPage(SettingsController settings)
        : base("Scraping")
    {
        _settings = settings;
        Subtitle = "Where your games' details and art come from";
        Build();
        SetHints(CommonHints.ChooseChangeBack);
        _settings.ConfigApplied += Rebuild;
        _settings.Jobs.Jobs.Changed += ShowJob;
    }

    public static string NameOf(string provider) => provider switch
    {
        ScraperIds.ScreenScraper => "ScreenScraper",
        ScraperIds.Igdb => "IGDB",
        ScraperIds.SteamGridDb => "SteamGridDB",
        ScraperIds.Steam => "Steam store",
        ScraperIds.LaunchBox => "LaunchBox Games DB",
        _ => provider,
    };

    /// <summary>Why a provider in the order is left out of a scrape, for the question that starts one.</summary>
    public static string SkippedNote(ProviderStatus provider) => provider switch
    {
        { State: ProviderState.MissingCredentials } => $"{provider.DisplayName} has no credentials, so it's skipped.",
        { Until: { } until } => string.Create(CultureInfo.InvariantCulture,
            $"{provider.DisplayName} has reached its limit or is closed, so it's skipped until {until.ToLocalTime():d MMMM, HH:mm}."),
        _ => $"{provider.DisplayName} refused its credentials, so it's skipped until the launcher restarts.",
    };

    public static string AboutOf(string provider) => provider switch
    {
        ScraperIds.ScreenScraper => "Metadata and every kind of media, videos included",
        ScraperIds.Igdb => "Metadata, covers, screenshots and artwork",
        ScraperIds.SteamGridDb => "Community covers, heroes and logos; no metadata",
        ScraperIds.Steam => "Steam's own art and store metadata, for Windows and Steam games",
        ScraperIds.LaunchBox => "Metadata, boxes, logos, fan art and disc art; no account, a 110 MB download",
        _ => string.Empty,
    };

    public override void OnClosed()
    {
        _settings.ConfigApplied -= Rebuild;
        _settings.Jobs.Jobs.Changed -= ShowJob;
    }

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
        AddSection("Scrape");
        _scrapeMissing = AddRow("Scrape what's missing", "Games never scraped, not found, or without a front cover", activated: ScrapeMissing);
        ShowJob();

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
        AddRow("Preferred regions", RegionsPage.Summary(scraping.Regions), null, () => Layer.Push(new RegionsPage(_settings)));

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

    // ---- Scrape all missing ---------------------------------------------------------------------------

    private void ShowJob() => _scrapeMissing.Value = _settings.Jobs.Scraping ? "Running" : _counting ? "Counting…" : null;

    /// <summary>Counts what it would scrape first, and asks, saying which providers will be used.</summary>
    private void ScrapeMissing()
    {
        if (_settings.Jobs.Scraping)
        {
            ShowStatus("Scraping is already running: it's at the top of the settings.", UiStyle.Dim, 4);
            return;
        }

        if (_counting)
        {
            return;
        }

        _counting = true;
        ShowJob();
        var config = _settings.Services.Config;
        var jobs = _settings.Jobs;
        _ = Task.Run(async () =>
        {
            string? failure = null;
            (MissingSummary Missing, IReadOnlyList<ProviderStatus> Providers) preview = default;
            try
            {
                preview = await jobs.PreviewMissingAsync(CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            _settings.Ui.Queue.Post(() =>
            {
                _counting = false;
                ShowJob();
                if (Layer?.Top != this)
                {
                    return;
                }

                if (failure is not null)
                {
                    ConfirmDialog.Tell(Layer, "Couldn't count the games", failure);
                    return;
                }

                AskToScrape(config, preview.Missing!, preview.Providers!);
            });
        });
    }

    private void AskToScrape(AppConfig config, MissingSummary missing, IReadOnlyList<ProviderStatus> providers)
    {
        if (missing.Games == 0)
        {
            ConfirmDialog.Tell(Layer, "Nothing to scrape", "Every game has been scraped and has a front cover.");
            return;
        }

        var usable = providers.Where(p => p.InOrder && p.State == ProviderState.Ready).ToList();
        if (usable.Count == 0)
        {
            ConfirmDialog.Tell(Layer, "No provider can scrape yet",
                "None of the providers you use has its credentials yet. Add them to one under Providers, below, first.");
            return;
        }

        var text = new StringBuilder();
        text.Append(CultureInfo.InvariantCulture, $"{missing.Games:N0} game{(missing.Games == 1 ? string.Empty : "s")} in ");
        text.Append(string.Join(", ", missing.Systems.Take(6).Select(s => string.Create(CultureInfo.InvariantCulture, $"{config.FindSystem(s.SystemId)?.Name ?? s.SystemId} ({s.Games:N0})"))));
        if (missing.Systems.Count > 6)
        {
            text.Append(CultureInfo.InvariantCulture, $" and {missing.Systems.Count - 6} more systems");
        }

        text.Append(" have never been scraped, weren't found, or have no front cover.\n\n");
        text.Append("They'll be looked up with ").Append(string.Join(", then ", usable.Select(p => p.DisplayName))).Append('.');
        foreach (var skipped in providers.Where(p => p.InOrder && p.State != ProviderState.Ready))
        {
            text.Append(' ').Append(SkippedNote(skipped));
        }

        text.Append("\n\nIt runs in the background: you can keep browsing, and stop it from its row at the top of the settings.");
        ConfirmDialog.Ask(Layer, $"Scrape {missing.Games:N0} games?", text.ToString(), "Start scraping", "Not now", yes =>
        {
            if (yes)
            {
                _settings.Jobs.ScrapeMissing();
            }
        });
    }
}
