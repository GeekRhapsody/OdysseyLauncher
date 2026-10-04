using System.Collections.Generic;
using System.Linq;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// The regions scraping prefers (<c>[scraping] regions</c>, 2026-10-04): ScreenScraper takes each game's name, release
/// date and media from the first of them it has, and IGDB its release date. The chosen regions come first, in order,
/// then the others ScreenScraper's region list commonly has. A turns one on or off; left and right (or the mouse's
/// arrows) move it earlier or later. A code the user wrote that isn't in <see cref="ScreenScraperScraper.KnownRegions"/>
/// keeps its place, shown by its code.
/// </summary>
public sealed partial class RegionsPage : ListPanel
{
    private readonly SettingsController _settings;

    /// <summary>The region just turned on, off or moved, so the focus goes with it when the page rebuilds.</summary>
    private string? _follow;

    public RegionsPage(SettingsController settings)
        : base("Regions", new Vector2(860, 640))
    {
        _settings = settings;
        Subtitle = "[scraping] regions in settings.toml";
        Build();
        SetHints("A  On or off     Left Right  Earlier or later     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    /// <summary>The Scraping page's summary of the list: "Europe, then World, then USA".</summary>
    public static string Summary(IReadOnlyList<string> regions) =>
        regions.Count == 0 ? "None: ScreenScraper's own order" : string.Join(", then ", regions.Select(ScreenScraperScraper.RegionName));

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        var order = Build();
        if (_follow is { } follow && order.IndexOf(follow) is var index and >= 0)
        {
            focused = index;
        }

        _follow = null;
        FocusRow(focused);
    }

    /// <returns>The regions in the rows' order.</returns>
    private List<string> Build()
    {
        var regions = _settings.Services.Config.Settings.Scraping.Regions;
        var fallback = string.Join(", ", ScreenScraperScraper.FallbackRegions.Select(ScreenScraperScraper.RegionName));
        AddNote($"Each game's name, release date and media come from the first region on this list that has them. When none has, ScreenScraper tries {fallback}, in that order. Changes apply to games scraped from now on.");

        // The chosen regions in order, then the others.
        var order = regions.Concat(ScreenScraperScraper.KnownRegions.Select(r => r.Code).Where(c => !regions.Contains(c))).ToList();
        for (var i = 0; i < order.Count; i++)
        {
            var code = order[i];
            var on = i < regions.Count;
            var line = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
            line.AddThemeConstantOverride("separation", 6);
            Rows.AddChild(line);
            var name = ScreenScraperScraper.RegionName(code);
            var row = new SettingRow(name, name == code ? "A code of your own" : code, on ? $"On, {Ordinal(i + 1)}" : "Off", () => Toggle(code))
            {
                ValueColour = on ? UiStyle.Good : UiStyle.Faint,
            };
            if (on)
            {
                row.Adjuster = direction => Move(code, direction);
            }

            line.AddChild(row);

            // For the mouse: the pad and keyboard move with left and right.
            if (on)
            {
                line.AddChild(Arrow("↑", () => Move(code, -1)));
                line.AddChild(Arrow("↓", () => Move(code, 1)));
            }
        }

        return order;
    }

    private static Button Arrow(string text, System.Action pressed)
    {
        var button = new Button { Text = text, FocusMode = FocusModeEnum.None, CustomMinimumSize = new Vector2(46, 0) };
        button.Pressed += pressed;
        return button;
    }

    private static string Ordinal(int n) => (n % 100) switch
    {
        11 or 12 or 13 => $"{n}th",
        _ => (n % 10) switch
        {
            1 => $"{n}st",
            2 => $"{n}nd",
            3 => $"{n}rd",
            _ => $"{n}th",
        },
    };

    private void Toggle(string code)
    {
        var regions = _settings.Services.Config.Settings.Scraping.Regions.ToList();
        var name = ScreenScraperScraper.RegionName(code);
        if (regions.Remove(code))
        {
            if (regions.Count == 0)
            {
                ShowStatus("Scraping needs at least one region: turn another on first.", UiStyle.Warning, 5);
                return;
            }

            Save(code, regions, $"{name} isn't preferred any more.");
            return;
        }

        regions.Add(code);
        Save(code, regions, $"{name} is preferred {Ordinal(regions.Count)} now.");
    }

    private void Move(string code, int direction)
    {
        var regions = _settings.Services.Config.Settings.Scraping.Regions.ToList();
        var index = regions.IndexOf(code);
        var target = index + direction;
        if (index < 0 || target < 0 || target >= regions.Count)
        {
            return;
        }

        (regions[index], regions[target]) = (regions[target], regions[index]);
        Save(code, regions, $"{ScreenScraperScraper.RegionName(code)} is preferred {Ordinal(target + 1)} now.");
    }

    private void Save(string code, List<string> regions, string saved)
    {
        _follow = code;
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["scraping", "regions"], regions)], saved);
    }
}
