using System;
using System.Collections.Generic;
using System.Globalization;
using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.App.Screens;

/// <summary>
/// Turns library data into the overlay's rows and the game details screen's fields, in UK English. Runs on the thread
/// pool, so the main thread never formats strings (A3 C# rules).
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

    /// <summary>A system from config, with its boot summary.</summary>
    public static OverlayDetails System(long key, SystemConfig system, SystemSummary summary, AppConfig config, DateTimeOffset now)
    {
        var rows = new List<(string, string)>();
        Add(rows, "Made by", system.Manufacturer);
        Add(rows, "Released", system.Year?.ToString(Uk));
        Add(rows, "Games", summary.GameCount.ToString("N0", Uk));
        Add(rows, "Last scanned", summary.ScannedAt is { } scanned ? Relative(scanned, now) : "Never");
        Add(rows, "Emulator", config.Emulators.TryGetValue(system.Emulator, out var emulator) ? emulator.Name : system.Emulator);
        return new OverlayDetails(key, rows, null, false);
    }

    /// <summary>A virtual system, which has only a description.</summary>
    public static OverlayDetails Virtual(long key, string description) => new(key, [], description, false);

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

    private static void Add(List<(string, string)> rows, string label, string? value)
    {
        if (!string.IsNullOrWhiteSpace(value))
        {
            rows.Add((label, value));
        }
    }
}
