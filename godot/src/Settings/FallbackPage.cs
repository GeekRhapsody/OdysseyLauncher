using System.Collections.Generic;
using System.Linq;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// The fallback providers and their order (M7): each is asked, in order, only for what the ones before it didn't
/// have. A turns one on or off; left and right (or the mouse's arrows) move it earlier or later.
/// </summary>
public sealed partial class FallbackPage : ListPanel
{
    private readonly SettingsController _settings;

    public FallbackPage(SettingsController settings)
        : base("Fallbacks", new Vector2(860, 560))
    {
        _settings = settings;
        Subtitle = "Asked in order, for what the default provider didn't have";
        Build();
        SetHints("A  On or off     Left Right  Earlier or later     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var scraping = _settings.Services.Config.Settings.Scraping;
        AddNote($"{ScrapingPage.NameOf(scraping.Provider)} is the default, so it's asked first. Change that on the Scraping page.");

        // The fallbacks in order, then the providers that are off.
        var order = scraping.Fallback.Concat(ConfigLoader.Scrapers.Where(p => p != scraping.Provider && !scraping.Fallback.Contains(p))).ToList();
        for (var i = 0; i < order.Count; i++)
        {
            var id = order[i];
            var on = scraping.Fallback.Contains(id);
            var line = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
            line.AddThemeConstantOverride("separation", 6);
            Rows.AddChild(line);
            var row = new SettingRow(ScrapingPage.NameOf(id), ScrapingPage.AboutOf(id), on ? $"On, {Ordinal(i + 1)}" : "Off", () => Toggle(id))
            {
                ValueColour = on ? UiStyle.Good : UiStyle.Faint,
            };
            if (on)
            {
                row.Adjuster = direction => Move(id, direction);
            }

            line.AddChild(row);

            // For the mouse: the pad and keyboard move with left and right.
            if (on)
            {
                line.AddChild(Arrow("↑", () => Move(id, -1)));
                line.AddChild(Arrow("↓", () => Move(id, 1)));
            }
        }
    }

    private static Button Arrow(string text, System.Action pressed)
    {
        var button = new Button { Text = text, FocusMode = FocusModeEnum.None, CustomMinimumSize = new Vector2(46, 0) };
        button.Pressed += pressed;
        return button;
    }

    private static string Ordinal(int n) => n switch
    {
        1 => "1st",
        2 => "2nd",
        3 => "3rd",
        _ => $"{n}th",
    };

    private void Toggle(string id)
    {
        var fallback = _settings.Services.Config.Settings.Scraping.Fallback.ToList();
        if (!fallback.Remove(id))
        {
            fallback.Add(id);
        }

        Save(fallback, fallback.Contains(id) ? $"{ScrapingPage.NameOf(id)} is a fallback now." : $"{ScrapingPage.NameOf(id)} isn't asked any more.");
    }

    private void Move(string id, int direction)
    {
        var fallback = _settings.Services.Config.Settings.Scraping.Fallback.ToList();
        var index = fallback.IndexOf(id);
        var target = index + direction;
        if (index < 0 || target < 0 || target >= fallback.Count)
        {
            return;
        }

        (fallback[index], fallback[target]) = (fallback[target], fallback[index]);
        Save(fallback, $"{ScrapingPage.NameOf(id)} is asked {Ordinal(target + 1)} among the fallbacks now.");
    }

    private void Save(List<string> fallback, string saved)
    {
        var provider = _settings.Services.Config.Settings.Scraping.Provider;
        if (ConfigInput.CheckProviders(provider, fallback) is { } problem)
        {
            ShowStatus(problem, UiStyle.Bad, 5);
            return;
        }

        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["scraping", "fallback"], fallback)], saved);
    }
}
