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
/// then the others ScreenScraper's region list commonly has. A code the user wrote that isn't in
/// <see cref="ScreenScraperScraper.KnownRegions"/> keeps its place, shown by its code.
/// </summary>
public sealed partial class RegionsPage : OrderedListPage
{
    private readonly SettingsController _settings;

    public RegionsPage(SettingsController settings)
        : base("Regions", new Vector2(860, 640))
    {
        _settings = settings;
        Subtitle = "[scraping] regions in settings.toml";
        Build();
        _settings.ConfigApplied += Rebuild;
    }

    /// <summary>The Scraping page's summary of the list: "Europe, then World, then USA".</summary>
    public static string Summary(IReadOnlyList<string> regions) =>
        regions.Count == 0 ? "None: ScreenScraper's own order" : string.Join(", then ", regions.Select(ScreenScraperScraper.RegionName));

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    protected override void Build()
    {
        var regions = _settings.Services.Config.Settings.Scraping.Regions;
        var fallback = string.Join(", ", ScreenScraperScraper.FallbackRegions.Select(ScreenScraperScraper.RegionName));
        AddNote($"Each game's name, release date and media come from the first region on this list that has them. When none has, ScreenScraper tries {fallback}, in that order. Changes apply to games scraped from now on.");

        // The chosen regions in order, then the others.
        var order = regions.Concat(ScreenScraperScraper.KnownRegions.Select(r => r.Code).Where(c => !regions.Contains(c))).ToList();
        for (var i = 0; i < order.Count; i++)
        {
            var code = order[i];
            var name = ScreenScraperScraper.RegionName(code);
            AddItem(code, name, name == code ? "A code of your own" : code, i < regions.Count ? i + 1 : 0);
        }
    }

    protected override void Toggle(string code)
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

            Save(regions, $"{name} isn't preferred any more.");
            return;
        }

        regions.Add(code);
        Save(regions, $"{name} is preferred {Ordinal(regions.Count)} now.");
    }

    protected override void Move(string code, int direction)
    {
        var regions = _settings.Services.Config.Settings.Scraping.Regions.ToList();
        var index = regions.IndexOf(code);
        var target = index + direction;
        if (index < 0 || target < 0 || target >= regions.Count)
        {
            return;
        }

        (regions[index], regions[target]) = (regions[target], regions[index]);
        Save(regions, $"{ScreenScraperScraper.RegionName(code)} is preferred {Ordinal(target + 1)} now.");
    }

    private void Save(List<string> regions, string saved)
    {
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["scraping", "regions"], regions)], saved);
    }
}
