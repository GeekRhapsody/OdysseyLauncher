using System.Collections.Generic;
using System.Linq;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Media;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// The media kinds scraping downloads (<c>[scraping] media</c>): one row each, in <see cref="MediaKinds.Scrapable"/>
/// order, saying what it is and which providers have it. A turns one on or off; left is no, right is yes. Turning
/// one off only stops new downloads: what's already scraped stays.
/// </summary>
public sealed partial class ScrapeMediaPage : ListPanel
{
    private static readonly (string Id, ScraperCapabilities Supplies)[] Providers =
    [
        (ScraperIds.ScreenScraper, ScreenScraperScraper.Supplies),
        (ScraperIds.Igdb, IgdbScraper.Supplies),
        (ScraperIds.SteamGridDb, SteamGridDbScraper.Supplies),
        (ScraperIds.Steam, SteamStoreScraper.Supplies),
    ];

    private readonly SettingsController _settings;

    public ScrapeMediaPage(SettingsController settings)
        : base("Media to scrape", new Vector2(900, 640))
    {
        _settings = settings;
        Subtitle = "[scraping] media in settings.toml";
        Build();
        SetHints("A  Yes or no     Left Right  No or yes     B  Back");
        _settings.ConfigApplied += Rebuild;
    }

    /// <summary>A scrapable kind, for people, in ScreenScraper's words where they differ from the slot's.</summary>
    public static string NameOf(string kind) => kind switch
    {
        MediaKinds.Cover => "Front cover",
        MediaKinds.Back => "Box back",
        MediaKinds.Spine => "Box spine",
        MediaKinds.Screenshot => "Screenshot",
        MediaKinds.Logo => "Wheel",
        MediaKinds.Hero => "Fan art",
        MediaKinds.Label => "Support texture",
        MediaKinds.Video => "Video",
        _ => kind,
    };

    private static string AboutOf(string kind) => kind switch
    {
        MediaKinds.Logo => "The game's logo",
        MediaKinds.Hero => "Wide artwork, for the hero slot",
        MediaKinds.Label => "A disc's or cartridge's art, for the label slot",
        MediaKinds.Video => "A gameplay clip, several MB a game; nothing plays it yet",
        _ => string.Empty,
    };

    /// <summary>Which providers have <paramref name="kind"/>: "ScreenScraper only", "ScreenScraper, IGDB".</summary>
    private static string SourcesOf(string kind)
    {
        var names = Providers.Where(p => p.Supplies.Media.Contains(kind)).Select(p => ScrapingPage.NameOf(p.Id)).ToList();
        return names.Count == 1 ? names[0] + " only" : string.Join(", ", names);
    }

    /// <summary>The Scraping page's summary of the list: "Front cover, box back and 3 more".</summary>
    public static string Summary(IReadOnlyList<string> media)
    {
        var names = MediaKinds.Scrapable.Where(media.Contains).Select(NameOf).ToList();
        return names.Count switch
        {
            0 => "None",
            1 => names[0],
            2 => $"{names[0]} and {names[1].ToLowerInvariant()}",
            _ => $"{names[0]}, {names[1].ToLowerInvariant()} and {names.Count - 2} more",
        };
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
        var media = _settings.Services.Config.Settings.Scraping.Media;
        AddNote("Downloaded for each game scraped from now on. Turning one off keeps what's already scraped; Clear metadata in a game's options removes it.");
        foreach (var kind in MediaKinds.Scrapable)
        {
            var on = media.Contains(kind);
            var about = AboutOf(kind);
            var row = AddRow(NameOf(kind), (about.Length > 0 ? about + " · " : string.Empty) + SourcesOf(kind), on ? "Yes" : "No", () => Set(kind, !media.Contains(kind)));
            row.ValueColour = on ? UiStyle.Good : UiStyle.Faint;
            row.Adjuster = direction => Set(kind, direction > 0);
        }
    }

    private void Set(string kind, bool on)
    {
        var current = _settings.Services.Config.Settings.Scraping.Media;
        if (current.Contains(kind) == on)
        {
            return;
        }

        // Kept in the page's order, so the file reads the same whichever way it was built up.
        var media = MediaKinds.Scrapable.Where(k => k == kind ? on : current.Contains(k)).ToList();
        if (media.Count == 0)
        {
            ShowStatus("Scraping needs at least one kind of media: turn another on first.", UiStyle.Warning, 5);
            return;
        }

        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["scraping", "media"], media)],
            on ? $"{NameOf(kind)}: downloaded from now on." : $"{NameOf(kind)}: not downloaded any more.");
    }
}
