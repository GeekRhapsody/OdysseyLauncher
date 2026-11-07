using System;
using System.Collections.Generic;
using System.Globalization;
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
/// set, and where (secrets.toml, or an <c>ODYSSEY_*</c> variable, which wins). A release has ScreenScraper's developer
/// credentials built in, and then doesn't list them: only the user's account. A types a new value on the on-screen
/// keyboard (hidden, with Show to check it), Y clears it, and "Test connection" tries them with one cheap request.
/// LaunchBox has no credentials: its page shows the local copy of its database instead, and A on it updates it.
/// </summary>
public sealed partial class ProviderPage : ListPanel
{
    private static readonly Hint[] Hints = [new("Change", Prompt.Accept), new("Clear", Prompt.Secondary), new("Back", Prompt.Back)];

    private readonly SettingsController _settings;
    private readonly string _provider;
    private readonly List<(SettingRow Row, string Key)> _keyRows = [];
    private SettingRow? _test;
    private SettingRow? _copy;
    private ProviderAccounts? _accounts;
    private int _check;
    private bool _testing;

    public ProviderPage(SettingsController settings, string provider)
        : base(ScrapingPage.NameOf(provider))
    {
        _settings = settings;
        _provider = provider;
        var keyless = ConfigInput.CredentialKeys(provider).Count == 0;
        Subtitle = keyless ? "No credentials needed" : null;
        Build();
        SetHints(keyless ? CommonHints.ChooseBack : Hints);
        Load();
        if (provider == ScraperIds.LaunchBox)
        {
            _settings.Jobs.LaunchBox.UpdateEnded += LaunchBoxUpdated;
            LoadCopy();
        }
    }

    public override void OnClosed()
    {
        if (_provider == ScraperIds.LaunchBox)
        {
            _settings.Jobs.LaunchBox.UpdateEnded -= LaunchBoxUpdated;
        }
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

    private string TestDetail => _provider switch
    {
        ScraperIds.LaunchBox => "One request for LaunchBox's database, without downloading it",
        _ when ConfigInput.CredentialKeys(_provider).Count == 0 => "One search on the store",
        _ => "One request with these credentials",
    };

    /// <summary>Whether this build carries <paramref name="key"/> (ScreenScraper's developer credentials, in a release).</summary>
    private static bool IsBuiltIn(string provider, string key) => ProviderAccounts.BuiltIn.ContainsKey(provider + "." + key);

    /// <summary>ScreenScraper's developer credentials: a program's, not the user's, so they're listed after the account.</summary>
    private static bool IsDeveloperKey(string provider, string key) => provider == ScraperIds.ScreenScraper && key is "dev_id" or "dev_password";

    private static string HelpOf(string provider) => provider switch
    {
        ScraperIds.ScreenScraper when IsBuiltIn(provider, "dev_id") =>
            "Sign in with your ScreenScraper account (free at screenscraper.fr) for your own daily quota and threads; without it, anonymous limits apply.",
        ScraperIds.ScreenScraper =>
            "Developer credentials are issued by ScreenScraper, on its forum, for a program; a release has its own, but this build doesn't. Your own account (free at screenscraper.fr) raises your daily quota and threads; without it, anonymous limits apply.",
        ScraperIds.Igdb =>
            "IGDB uses a Twitch application: register one at dev.twitch.tv/console (a confidential client), and copy its client ID and a new client secret.",
        ScraperIds.SteamGridDb =>
            "Make an API key on steamgriddb.com: Preferences, then API.",
        ScraperIds.Steam =>
            "The Steam store needs no account. It finds a game by its title (not the shortcut's app id), for the Windows and Steam systems. A game no longer sold can't be found.",
        ScraperIds.LaunchBox =>
            "LaunchBox's Games DB needs no account. Its whole database (about 110 MB) is downloaded the first time a scrape needs it and checked for a newer copy once a week; games are then found in it without the network, for the systems it covers. Names and art follow your preferred regions.",
        _ => string.Empty,
    };

    private void Build()
    {
        AddNote(HelpOf(_provider));
        // A release's built-in developer credentials are the only ones it uses (ProviderAccounts.Parse): not listed.
        var keys = ConfigInput.CredentialKeys(_provider);
        var account = keys.Where(k => !IsDeveloperKey(_provider, k.Key)).ToList();
        var developer = keys.Where(k => IsDeveloperKey(_provider, k.Key) && !IsBuiltIn(_provider, k.Key)).ToList();
        if (account.Count > 0)
        {
            AddSection(account.Count < keys.Count ? "Your account" : "Credentials");
            AddKeyRows(account);
        }

        if (developer.Count > 0)
        {
            AddSection("Developer credentials");
            AddKeyRows(developer);
        }

        if (_provider == ScraperIds.LaunchBox)
        {
            AddSection("Database");
            _copy = AddRow("Local copy", "Checking…", null, UpdateLaunchBox);
        }

        AddSection("Check");
        _test = AddRow("Test connection", TestDetail, null, Test);
    }

    /// <summary>Reads the local copy's state off the main thread (it opens the index), then shows it.</summary>
    private void LoadCopy()
    {
        var database = _settings.Jobs.LaunchBox;
        _ = Task.Run(() =>
        {
            var info = database.Info;
            _settings.Ui.Queue.Post(() =>
            {
                if (!IsInstanceValid(_copy))
                {
                    return;
                }

                if (info is null)
                {
                    _copy.Value = "Not downloaded";
                    _copy.ValueColour = UiStyle.Dim;
                    _copy.Detail = "Downloaded the first time a scrape needs it. A downloads it now.";
                    return;
                }

                var published = info.Published is { } p ? p.ToLocalTime().ToString("d MMM yyyy", CultureInfo.InvariantCulture) : "on an unknown date";
                _copy.Value = info.Games.ToString("N0", CultureInfo.InvariantCulture) + " games";
                _copy.ValueColour = UiStyle.Good;
                _copy.Detail = $"Published {published}, checked {info.Checked.ToLocalTime().ToString("d MMM yyyy", CultureInfo.InvariantCulture)}. A checks for a newer one.";
            });
        });
    }

    /// <summary>Worker thread: an update ended, so the copy's state may have changed.</summary>
    private void LaunchBoxUpdated(object? sender, LaunchBoxUpdateEndedEventArgs e) => _settings.Ui.Queue.Post(LoadCopy);

    private void UpdateLaunchBox() => ShowStatus(_settings.Jobs.UpdateLaunchBox()
        ? "Updating LaunchBox's database: the progress card shows how it's going."
        : "LaunchBox's database is already updating.", UiStyle.Dim, 4);

    private void AddKeyRows(List<(string Key, string Label, bool Secret)> keys)
    {
        foreach (var (key, label, _) in keys)
        {
            var captured = key;
            var row = AddRow(label, "Checking…", null, () => Edit(captured, label));
            _keyRows.Add((row, key));
        }
    }

    /// <summary>Reads secrets.toml (and the environment) off the main thread, then shows what's set.</summary>
    private void Load()
    {
        var check = ++_check;
        var configDir = _settings.Services.Paths.ConfigDir;
        _ = Task.Run(() =>
        {
            var accounts = ProviderAccounts.Load(configDir, builtIn: ProviderAccounts.BuiltIn).Accounts;
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
                    row.Detail = "Set";
                    row.Value = "••••••••";
                    row.ValueColour = UiStyle.Good;
                    break;
                case CredentialSource.Environment:
                    row.Detail = $"Set by {ProviderAccounts.EnvironmentVariable(_provider, key)}, which overrides the saved value";
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
        if (command != NavCommand.Secondary)
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
            Subtitle: "Saved only on this computer. Show reveals what you've typed.",
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
            $"It's removed from this computer.{environment}", "Clear it", "Keep it", yes =>
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
        _test.Detail = TestDetail;
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
