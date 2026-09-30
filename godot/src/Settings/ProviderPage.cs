using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// One provider's credentials (M7), stored in secrets.toml only. Values are never shown: each row says whether it's
/// set, and where (secrets.toml, or an <c>ODYSSEY_*</c> variable, which wins). A types a new value on the on-screen
/// keyboard (hidden, with Show to check it), Y clears it, and "Test connection" tries them with one cheap request.
/// </summary>
public sealed partial class ProviderPage : ListPanel
{
    private readonly SettingsController _settings;
    private readonly string _provider;
    private readonly List<(SettingRow Row, string Key)> _keyRows = [];
    private SettingRow? _test;
    private ProviderAccounts? _accounts;
    private int _check;
    private bool _testing;

    public ProviderPage(SettingsController settings, string provider)
        : base(ScrapingPage.NameOf(provider))
    {
        _settings = settings;
        _provider = provider;
        Subtitle = $"[{provider}] in secrets.toml";
        Build();
        SetHints("A  Change     Y  Clear     B  Back");
        Load();
    }

    /// <summary>A provider's credentials at a glance: "Ready", "Needs its credentials"… and whether it can be used.</summary>
    public static (string Text, bool Ready) CredentialState(ProviderAccounts accounts, string provider)
    {
        var keys = ConfigInput.CredentialKeys(provider);
        var set = keys.Count(k => accounts.SourceOf(provider, k.Key) != CredentialSource.None);
        return provider switch
        {
            ScraperIds.ScreenScraper when accounts.ScreenScraperDevId is null || accounts.ScreenScraperDevPassword is null => ("Needs developer credentials", false),
            ScraperIds.ScreenScraper when accounts.ScreenScraperUsername is null || accounts.ScreenScraperPassword is null => ("Ready, anonymous", true),
            _ when set == keys.Count => ("Ready", true),
            _ => (set == 0 ? "Not set" : "Incomplete", false),
        };
    }

    private static string HelpOf(string provider) => provider switch
    {
        ScraperIds.ScreenScraper =>
            "Developer credentials are issued by ScreenScraper, on its forum, for a program. Your own account (free at screenscraper.fr) raises your daily quota and threads; without it, anonymous limits apply.",
        ScraperIds.Igdb =>
            "IGDB uses a Twitch application: register one at dev.twitch.tv/console (a confidential client), and copy its client ID and a new client secret.",
        ScraperIds.SteamGridDb =>
            "Make an API key on steamgriddb.com: Preferences, then API.",
        _ => string.Empty,
    };

    private void Build()
    {
        AddNote(HelpOf(_provider));
        AddSection("Credentials");
        foreach (var (key, label, _) in ConfigInput.CredentialKeys(_provider))
        {
            var captured = key;
            var row = AddRow(label, "Checking…", null, () => Edit(captured, label));
            _keyRows.Add((row, key));
        }

        AddSection("Check");
        _test = AddRow("Test connection", "One request with these credentials", null, Test);
    }

    /// <summary>Reads secrets.toml (and the environment) off the main thread, then shows what's set.</summary>
    private void Load()
    {
        var check = ++_check;
        var configDir = _settings.Services.Paths.ConfigDir;
        _ = Task.Run(() =>
        {
            var accounts = ProviderAccounts.Load(configDir).Accounts;
            _settings.Ui.Queue.Post(() =>
            {
                if (check == _check)
                {
                    Show(accounts);
                }
            });
        });
    }

    private void Show(ProviderAccounts accounts)
    {
        _accounts = accounts;
        foreach (var (row, key) in _keyRows)
        {
            if (!IsInstanceValid(row))
            {
                continue;
            }

            switch (accounts.SourceOf(_provider, key))
            {
                case CredentialSource.File:
                    row.Detail = "Set in secrets.toml";
                    row.Value = "••••••••";
                    row.ValueColour = UiStyle.Good;
                    break;
                case CredentialSource.Environment:
                    row.Detail = $"Set by {ProviderAccounts.EnvironmentVariable(_provider, key)}, which overrides secrets.toml";
                    row.Value = "••••••••";
                    row.ValueColour = UiStyle.Accent;
                    break;
                default:
                    row.Detail = _provider == ScraperIds.ScreenScraper && key is "username" or "password" ? "Not set: optional" : "Not set";
                    row.Value = "Not set";
                    row.ValueColour = UiStyle.Warning;
                    break;
            }
        }
    }

    public override bool Handle(NavCommand command)
    {
        if (command != NavCommand.Favourite)
        {
            return false;
        }

        var focused = GetViewport().GuiGetFocusOwner();
        foreach (var (row, key) in _keyRows)
        {
            if (row == focused)
            {
                Clear(key, row.Title);
                return true;
            }
        }

        return false;
    }

    private void Edit(string key, string label)
    {
        OnScreenKeyboard.Open(Layer, new KeyboardRequest(
            $"{ScrapingPage.NameOf(_provider)}: {label}",
            string.Empty,
            value => Save(key, value.Trim(), $"{label} saved."),
            Secret: true,
            Placeholder: "Type or paste the new value",
            Subtitle: "Saved to secrets.toml only. Show reveals what you've typed.",
            Validate: ConfigInput.CheckCredential));
    }

    private void Clear(string key, string label)
    {
        if (_accounts?.SourceOf(_provider, key) == CredentialSource.None)
        {
            ShowStatus($"{label} isn't set.", UiStyle.Dim, 3);
            return;
        }

        var environment = _accounts?.SourceOf(_provider, key) == CredentialSource.Environment
            ? $" {ProviderAccounts.EnvironmentVariable(_provider, key)} still sets it: remove that variable too."
            : string.Empty;
        ConfirmDialog.Ask(Layer, $"Clear the {label.ToLowerInvariant()}?",
            $"It's removed from secrets.toml.{environment}", "Clear it", "Keep it", yes =>
            {
                if (yes)
                {
                    Save(key, null, $"{label} cleared.");
                }
            }, destructive: true);
    }

    private void Save(string key, string? value, string saved) =>
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Secrets, [_provider, key], value)], saved, then: _ => Load());

    private void Test()
    {
        if (_testing || _test is null)
        {
            return;
        }

        _testing = true;
        _test.Value = "Testing…";
        _test.ValueColour = UiStyle.Dim;
        _test.Detail = "One request with these credentials";
        var jobs = _settings.Jobs;
        var provider = _provider;
        _ = Task.Run(async () =>
        {
            ConnectionTestResult result;
            try
            {
                result = await jobs.TestConnectionAsync(provider, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                result = new ConnectionTestResult(provider, false, $"The test couldn't run: {e.Message}");
            }

            _settings.Ui.Queue.Post(() =>
            {
                _testing = false;
                if (!IsInstanceValid(_test))
                {
                    return;
                }

                _test.Value = result.Succeeded ? "Connected" : "Failed";
                _test.ValueColour = result.Succeeded ? UiStyle.Good : UiStyle.Bad;
                _test.Detail = result.Message;
                _test.DetailColour = result.Succeeded ? UiStyle.Good : UiStyle.Bad;
                ShowStatus(result.Message, result.Succeeded ? UiStyle.Good : UiStyle.Bad, 0);
            });
        });
    }
}
