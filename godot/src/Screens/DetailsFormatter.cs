using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.App.Screens;

/// <summary>
/// Turns config and library data into the details screens' fields (a game's, a system's) and the overlay's subtitles,
/// in UK English. Runs on the thread pool, so the main thread never formats strings (A3 C# rules).
/// </summary>
public static class DetailsFormatter
{
    private static readonly CultureInfo Uk = CultureInfo.GetCultureInfo("en-GB");

    /// <summary>
    /// Every field the library has for a game, for its details screen (Y): its metadata (A4 <c>metadata</c>, with the
    /// user's edits), the tags from its file name, its play history, and how it launches and where its data came from.
    /// Only fields with a value; the description is apart.
    /// </summary>
    public static IReadOnlyList<(string Label, string Value)> GameFields(GameDetails game, PlayStats? stats, AppConfig config, DateTimeOffset now)
    {
        var rows = new List<(string, string)>();
        var metadata = game.Metadata;
        Add(rows, "Released", ReleaseDate(metadata?.ReleaseDate));
        Add(rows, "Genre", metadata?.Genre);
        Add(rows, "Developer", metadata?.Developer);
        Add(rows, "Publisher", metadata?.Publisher);
        Add(rows, "Players", metadata?.Players);
        Add(rows, "Rating", metadata?.Rating is { } rating ? string.Create(Uk, $"{rating * 5:0.0} / 5") : null);

        Add(rows, "Region", game.Region);
        Add(rows, "Languages", game.Languages?.Replace(",", ", ", StringComparison.Ordinal));
        Add(rows, "Version", game.Revision);
        Add(rows, "Disc", game.Disc?.ToString(Uk));
        Add(rows, "Tags", game.Tags);

        if (stats is { PlayCount: > 0 })
        {
            Add(rows, "Played", stats.PlayCount == 1 ? "Once" : string.Create(Uk, $"{stats.PlayCount:N0} times"));
            Add(rows, "Last played", stats.LastPlayedAt is { } last ? Relative(last, now) : null);
            Add(rows, "Play time", Duration(stats.TotalPlayTime));
        }
        else
        {
            Add(rows, "Played", "Never");
        }

        Add(rows, "Favourite", game.IsFavourite ? "Yes" : "No");
        string NameOf(string id) => config.Emulators.TryGetValue(id, out var emulator) ? emulator.Name : id;
        Add(rows, "Emulator", game.EmulatorOverride is { } own
            ? NameOf(own) + " (its own)"
            : config.FindSystem(game.Key.SystemId) is { } system ? NameOf(system.Emulator) : null);
        Add(rows, "Title", game.TitleOverride is null ? null : "Yours");
        Add(rows, "Metadata", metadata?.Source is { } source
            ? source == "user" ? "Yours" : string.Join(" and ", Array.ConvertAll(source.Split(','), Settings.ScrapingPage.NameOf))
            : null);
        Add(rows, "Scraped", game.Scrape switch
        {
            null => "Never",
            { Status: "ok" } s => Relative(s.ScrapedAt, now),
            { Status: "partial" } s => Relative(s.ScrapedAt, now) + " · a provider failed",
            { Status: "not_found" } s => "Not found · " + Relative(s.ScrapedAt, now),
            { } s => "Failed · " + Relative(s.ScrapedAt, now),
        });
        Add(rows, "Size", Ui.UiStyle.Size(game.SizeBytes));
        return rows;
    }

    /// <summary>
    /// Every field the app has for a system, for its details screen (Y): who made it and when, its games and their last
    /// scan (the library's summary), how they launch, where they're found and which files count, how they're shown and
    /// sorted (marked when the system has its own), the models the theme gives it, and where scraping looks it up. Only
    /// fields with a value; the description is apart.
    /// </summary>
    /// <param name="cardModel">The model its card uses, as the theme describes it; null if unknown.</param>
    /// <param name="gamesModel">The model its games use, likewise.</param>
    public static IReadOnlyList<(string Label, string Value)> SystemFields(
        SystemConfig system, SystemSummary? summary, AppConfig config, string? cardModel, string? gamesModel, DateTimeOffset now)
    {
        var rows = new List<(string, string)>();
        Add(rows, "Made by", system.Manufacturer);
        Add(rows, "Released", system.Year?.ToString(Uk));
        Add(rows, "Games", GamesCount(summary?.GameCount ?? 0));
        Add(rows, "Last scanned", summary?.ScannedAt is { } scanned ? Relative(scanned, now) : "Never");

        Add(rows, "Emulator", EmulatorName(config, system.Emulator));
        var alternatives = new List<string>();
        foreach (var id in system.OfferedEmulators())
        {
            if (id != system.Emulator)
            {
                alternatives.Add(EmulatorName(config, id));
            }
        }

        Add(rows, "Alternatives", alternatives.Count == 0 ? null : string.Join("\n", alternatives));
        Add(rows, system.RomDirs.Count > 1 && system.RomDirSource == RomDirSource.Configured ? "ROM folders" : "ROM folder", RomFolders(system));
        Add(rows, "Subfolders", system.Recursive ? "Scanned too" : "Not scanned");
        Add(rows, "Left out", system.Exclude.Count == 0 ? null : string.Join(", ", system.Exclude));
        Add(rows, "File types", string.Join(" ", system.Extensions));
        Add(rows, "Also known as", system.Aliases.Count == 0 ? null : string.Join(", ", system.Aliases));

        var display = config.Settings.Display;
        var layout = display.GamesLayoutFor(system);
        Add(rows, "Games view", Own(Settings.LayoutPage.GamesTitle(layout), system.GamesLayout is not null));
        if (layout == GamesLayout.Grid)
        {
            var size = display.GamesGridFor(system);
            Add(rows, "Grid size", Own(GridSize(size.Columns, size.Rows), system.GamesColumns is not null || system.GamesRows is not null));
        }

        var sort = display.GamesSortFor(system);
        Add(rows, "Games sorted", Own(
            $"{Settings.LayoutPage.GamesSortTitle(sort.Sort)}: {Settings.LayoutPage.GamesOrderDetail(sort.Sort, sort.Order)}",
            system.GamesSort is not null || system.GamesSortOrder is not null));
        Add(rows, "Card model", cardModel);
        Add(rows, "Games' model", gamesModel);

        Add(rows, "ScreenScraper", system.ScreenScraperId is { } ss ? string.Create(Uk, $"System {ss}") : "Not on ScreenScraper");
        Add(rows, "IGDB", system.IgdbPlatforms is { Count: > 0 } platforms
            ? (platforms.Count == 1 ? "Platform " : "Platforms ") + string.Join(", ", Array.ConvertAll([.. platforms], p => p.ToString(Uk)))
            : "Not looked up");
        Add(rows, "Steam store", system.SteamStore ? "Looked up by title" : null);
        Add(rows, "Id", system.Id);
        return rows;
    }

    /// <summary>Favourites' or Recently played's fields: how many games it holds, and from how many systems.</summary>
    public static IReadOnlyList<(string Label, string Value)> VirtualFields(int games, int systems)
    {
        var rows = new List<(string, string)>();
        Add(rows, "Games", GamesCount(games));
        Add(rows, "Systems", systems.ToString("N0", Uk));
        return rows;
    }

    /// <summary>What Favourites or Recently played is, for its details screen.</summary>
    public static string VirtualDescription(VirtualKind kind) => kind == VirtualKind.Favourites
        ? "The games you've marked as favourites, from every system. Press L3 (or F) on a game to add it, or to take it out."
        : "The games you've played most recently, from every system, newest first.";

    /// <summary>The subtitle under a system's name: who made it and when, and how many games there are.</summary>
    public static string SystemSubtitle(SystemConfig system, int games)
    {
        var count = games == 1 ? "1 game" : string.Create(Uk, $"{games:N0} games");
        return system.Manufacturer is { } maker
            ? system.Year is { } year ? string.Create(Uk, $"{maker} · {year} · {count}") : $"{maker} · {count}"
            : count;
    }

    public static string GamesCount(int games) => games == 1 ? "1 game" : string.Create(Uk, $"{games:N0} games");

    /// <summary>ISO 8601, possibly partial: '1991' stays as it is, '1991-06' is 'June 1991', '1991-06-23' is '23 June 1991'.</summary>
    public static string? ReleaseDate(string? iso)
    {
        if (string.IsNullOrWhiteSpace(iso))
        {
            return null;
        }

        if (DateTime.TryParseExact(iso, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var day))
        {
            return day.ToString("d MMMM yyyy", Uk);
        }

        if (DateTime.TryParseExact(iso, "yyyy-MM", CultureInfo.InvariantCulture, DateTimeStyles.None, out var month))
        {
            return month.ToString("MMMM yyyy", Uk);
        }

        return iso;
    }

    /// <summary>'Today at 14:05', 'Yesterday', '3 days ago', or a date.</summary>
    public static string Relative(DateTimeOffset when, DateTimeOffset now)
    {
        var local = when.ToLocalTime();
        var today = now.ToLocalTime().Date;
        var days = (today - local.Date).Days;
        return days switch
        {
            < 0 => local.ToString("d MMMM yyyy", Uk),
            0 => "Today at " + local.ToString("HH:mm", Uk),
            1 => "Yesterday at " + local.ToString("HH:mm", Uk),
            < 7 => string.Create(Uk, $"{days} days ago"),
            _ => local.ToString("d MMMM yyyy", Uk),
        };
    }

    /// <summary>'Under a minute', '45 min', '3 h 20 min'.</summary>
    public static string Duration(TimeSpan time)
    {
        if (time < TimeSpan.FromMinutes(1))
        {
            return "Under a minute";
        }

        var hours = (int)time.TotalHours;
        return hours == 0 ? string.Create(Uk, $"{time.Minutes} min") : string.Create(Uk, $"{hours:N0} h {time.Minutes} min");
    }

    /// <summary>
    /// The folders set in systems.toml, one a line; or the default's candidates, which share the ROM root, as the root
    /// and then their names. Nothing is checked on disk (a disconnected share can take a long time to answer).
    /// </summary>
    private static string? RomFolders(SystemConfig system)
    {
        var dirs = system.RomDirs;
        if (dirs.Count == 0)
        {
            return null;
        }

        if (system.RomDirSource == RomDirSource.Configured)
        {
            return string.Join("\n", dirs);
        }

        if (dirs.Count == 1)
        {
            return dirs[0] + "\nThe default";
        }

        var parent = Path.GetDirectoryName(dirs[0]);
        var names = new List<string>(dirs.Count);
        foreach (var dir in dirs)
        {
            if (!string.Equals(Path.GetDirectoryName(dir), parent, StringComparison.OrdinalIgnoreCase))
            {
                return string.Join("\n", dirs) + "\nThe default: the first of these that exists";
            }

            names.Add(Path.GetFileName(dir));
        }

        return $"{parent}\nThe default: the first of {string.Join(", ", names)} in it that exists";
    }

    private static string EmulatorName(AppConfig config, string id) => config.Emulators.TryGetValue(id, out var emulator) ? emulator.Name : id;

    /// <summary>A setting's value, marked when the system has its own rather than the Layout page's.</summary>
    private static string Own(string value, bool own) => own ? value + " (its own)" : value;

    private static string GridSize(int columns, int rows) => (columns, rows) switch
    {
        (0, 0) => "Automatic",
        (_, 0) => string.Create(Uk, $"{columns} columns"),
        (0, _) => string.Create(Uk, $"{rows} rows"),
        _ => string.Create(Uk, $"{columns} columns, {rows} rows"),
    };

    private static void Add(List<(string, string)> rows, string label, string? value)
    {
        if (!string.IsNullOrWhiteSpace(value))
        {
            rows.Add((label, value));
        }
    }
}
