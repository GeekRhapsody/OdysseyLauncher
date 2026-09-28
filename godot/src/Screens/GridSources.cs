using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Grid;
using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.App.Screens;

/// <summary>One card of the systems grid: a configured system, or Favourites or Recently played.</summary>
public sealed record SystemEntry(
    string Id,
    string Name,
    string Subtitle,
    Color Colour,
    SystemConfig? System,
    SystemSummary? Summary,
    VirtualKind Virtual);

public enum VirtualKind
{
    None,
    Favourites,
    RecentlyPlayed,
}

/// <summary>Colours for cards and plain boxes. UI choices, not config (M6 themes may override them).</summary>
public static class Palette
{
    private static readonly Dictionary<string, Color> Systems = new(StringComparer.Ordinal)
    {
        ["gb"] = new Color("#8A9A5B"),
        ["gbc"] = new Color("#6B3FA0"),
        ["gba"] = new Color("#3F3A9E"),
        ["nes"] = new Color("#A8232E"),
        ["snes"] = new Color("#6C5BA6"),
        ["n64"] = new Color("#2F8F4E"),
        ["gc"] = new Color("#5A4FCF"),
        ["mastersystem"] = new Color("#B83A3A"),
        ["megadrive"] = new Color("#1F3E8C"),
        ["saturn"] = new Color("#4A4F5C"),
        ["dreamcast"] = new Color("#D06A1E"),
        ["psx"] = new Color("#7C8594"),
        ["ps2"] = new Color("#1F3A7A"),
        ["psp"] = new Color("#3B3E48"),
    };

    public static readonly Color Favourites = new("#C99A2E");
    public static readonly Color RecentlyPlayed = new("#2E8C7A");

    public static Color ForSystem(string id)
    {
        if (Systems.TryGetValue(id, out var colour))
        {
            return colour;
        }

        var hash = (uint)StringComparer.Ordinal.GetHashCode(id);
        return Color.FromHsv(hash % 360 / 360f, 0.5f, 0.6f);
    }

    /// <summary>A box with no art: its system's colour, darker, with a small per-game shift so a shelf of them varies.</summary>
    public static Color PlainBox(Color system, long gameId)
    {
        var h = (uint)(gameId * 2654435761L);
        system.ToHsv(out var hue, out var saturation, out var value);
        var shift = (h % 1000 / 1000f - 0.5f) * 0.08f;
        var lightness = 0.42f + h / 1000 % 1000 / 1000f * 0.2f;
        return Color.FromHsv((hue + shift + 1) % 1, Math.Min(1, saturation * 0.9f + 0.1f), Math.Min(value, 1) * lightness + 0.08f);
    }
}

/// <summary>The systems grid: every card uses the generic system model, tinted by its colour.</summary>
public sealed class SystemsSource(IReadOnlyList<SystemEntry> entries, int template) : IGridSource
{
    public IReadOnlyList<SystemEntry> Entries => entries;

    public int Count => entries.Count;

    public void Describe(int index, out CellInfo cell)
    {
        var entry = entries[index];
        cell = new CellInfo { Title = entry.Name, Template = template, Plain = entry.Colour };
    }

    public bool UsesTemplate(int t) => t == template;
}

/// <summary>
/// A grid of games, from one system's list or a virtual one. Built on the thread pool (it works out each game's
/// letter group for letter jumps), then handed to the main thread.
/// </summary>
public sealed class GamesSource : IGridSource
{
    private readonly GameRow[] _rows;
    private readonly int[] _templates;
    private readonly Color[] _colours;
    private readonly string[] _systemNames;
    private readonly char[] _letters;
    private readonly bool[] _usesTemplate;

    /// <param name="templateOf">A system id's template index in the games grid.</param>
    private GamesSource(string id, string name, IReadOnlyList<(string SystemId, GameRow Row)> rows, Func<string, int> templateOf, Func<string, string> nameOf, int templateCount)
    {
        Id = id;
        Name = name;
        _rows = new GameRow[rows.Count];
        _templates = new int[rows.Count];
        _colours = new Color[rows.Count];
        _systemNames = new string[rows.Count];
        _letters = new char[rows.Count];
        _usesTemplate = new bool[templateCount];
        var systemColours = new Dictionary<string, Color>(StringComparer.Ordinal);
        for (var i = 0; i < rows.Count; i++)
        {
            var (systemId, row) = rows[i];
            _rows[i] = row;
            _templates[i] = templateOf(systemId);
            _usesTemplate[_templates[i]] = true;
            _systemNames[i] = nameOf(systemId);
            if (!systemColours.TryGetValue(systemId, out var colour))
            {
                systemColours[systemId] = colour = Palette.ForSystem(systemId);
            }

            _colours[i] = Palette.PlainBox(colour, row.GameId);
            _letters[i] = LetterOf(row.Title);
        }
    }

    /// <summary>The entry id this list belongs to (a system id, or a virtual one).</summary>
    public string Id { get; }

    /// <summary>The heading for the grid (the system's name).</summary>
    public string Name { get; }

    public int Count => _rows.Length;

    public GameRow Row(int index) => _rows[index];

    /// <summary>The name of the system the game belongs to, for the overlay.</summary>
    public string SystemName(int index) => _systemNames[index];

    public static GamesSource ForSystem(string id, string name, GameList list, Func<string, int> templateOf, int templateCount)
    {
        var rows = new (string, GameRow)[list.Games.Count];
        for (var i = 0; i < rows.Length; i++)
        {
            rows[i] = (list.SystemId, list.Games[i]);
        }

        return new GamesSource(id, name, rows, templateOf, _ => name, templateCount);
    }

    public static GamesSource ForVirtual(string id, string name, IReadOnlyList<VirtualGameRow> list, Func<string, int> templateOf, Func<string, string> nameOf, int templateCount)
    {
        var rows = new (string, GameRow)[list.Count];
        for (var i = 0; i < rows.Length; i++)
        {
            rows[i] = (list[i].SystemId, list[i].Game);
        }

        return new GamesSource(id, name, rows, templateOf, nameOf, templateCount);
    }

    public void Describe(int index, out CellInfo cell)
    {
        ref readonly var row = ref _rows[index];
        cell = new CellInfo
        {
            Title = row.Title,
            Template = _templates[index],
            Plain = _colours[index],
            CoverRoot = row.CoverRoot,
            CoverPath = row.CoverPath,
            CoverAspect = row.CoverAspect,
            CoverSizeBytes = row.CoverSizeBytes,
            CoverMtimeMs = row.CoverMtimeMs,
        };
    }

    public bool UsesTemplate(int template) => template < _usesTemplate.Length && _usesTemplate[template];

    /// <summary>The first item of the next letter group after <paramref name="index"/>'s, or -1.</summary>
    public int NextLetter(int index)
    {
        for (var i = index + 1; i < _letters.Length; i++)
        {
            if (_letters[i] != _letters[index])
            {
                return i;
            }
        }

        return -1;
    }

    /// <summary>The start of <paramref name="index"/>'s letter group, or of the one before if it's already there; -1 at the top.</summary>
    public int PreviousLetter(int index)
    {
        var start = index;
        while (start > 0 && _letters[start - 1] == _letters[index])
        {
            start--;
        }

        if (start < index)
        {
            return start;
        }

        if (start == 0)
        {
            return -1;
        }

        var previous = start - 1;
        while (previous > 0 && _letters[previous - 1] == _letters[start - 1])
        {
            previous--;
        }

        return previous;
    }

    /// <summary>The first index of the game with this id, or -1.</summary>
    public int IndexOf(long gameId)
    {
        for (var i = 0; i < _rows.Length; i++)
        {
            if (_rows[i].GameId == gameId)
            {
                return i;
            }
        }

        return -1;
    }

    /// <summary>The letter a title sorts under: its first letter after a leading article, upper-case; '#' for anything else.</summary>
    public static char LetterOf(string title)
    {
        var span = title.AsSpan().TrimStart();
        foreach (var article in (ReadOnlySpan<string>)["The ", "A ", "An "])
        {
            if (span.StartsWith(article, StringComparison.OrdinalIgnoreCase) && span.Length > article.Length)
            {
                span = span[article.Length..];
                break;
            }
        }

        foreach (var c in span)
        {
            if (char.IsLetter(c))
            {
                var baseLetter = char.ToUpperInvariant(RemoveAccent(c));
                return baseLetter is >= 'A' and <= 'Z' ? baseLetter : '#';
            }

            if (char.IsDigit(c))
            {
                return '#';
            }
        }

        return '#';
    }

    private static char RemoveAccent(char c)
    {
        var decomposed = c.ToString().Normalize(System.Text.NormalizationForm.FormD);
        return decomposed.Length > 0 ? decomposed[0] : c;
    }
}
