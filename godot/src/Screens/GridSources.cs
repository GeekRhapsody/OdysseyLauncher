using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Grid;
using Launcher.App.Models;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Theming;

namespace Launcher.App.Screens;

/// <summary>One card of the systems grid: a configured system, or Favourites or Recently played.</summary>
/// <param name="Template">The card's model, as an index into the systems grid's templates.</param>
/// <param name="Logo">The card's logo from the theme (A6 <c>logos/</c>), for a slot whose chain names <c>logo</c>; null for none.</param>
public sealed record SystemEntry(
    string Id,
    string Name,
    string Subtitle,
    Color Colour,
    SystemConfig? System,
    SystemSummary? Summary,
    VirtualKind Virtual,
    int Template,
    MediaRef? Logo = null);

public enum VirtualKind
{
    None,
    Favourites,
    RecentlyPlayed,
}

/// <summary>
/// Colours the theme doesn't give: the virtual systems' cards, and a system with no colour in either the active theme
/// or the built-in one (a user-defined system), which gets one from its id.
/// </summary>
public static class Palette
{
    public static readonly Color Favourites = new("#C99A2E");
    public static readonly Color RecentlyPlayed = new("#2E8C7A");

    public static Color ForSystem(Rgb? themeColour, string id)
    {
        if (themeColour is { } colour)
        {
            return Color.Color8(colour.R, colour.G, colour.B);
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

/// <summary>The systems grid: each card uses its system's model from the theme, tinted by its colour where the theme says so.</summary>
public sealed class SystemsSource(IReadOnlyList<SystemEntry> entries, int templateCount) : IGridSource
{
    private readonly bool[] _uses = Uses(entries, templateCount);

    public IReadOnlyList<SystemEntry> Entries => entries;

    public int Count => entries.Count;

    public void Describe(int index, out CellInfo cell)
    {
        var entry = entries[index];
        cell = new CellInfo { Title = entry.Name, Template = entry.Template, Plain = entry.Colour };
    }

    /// <summary>A system's only media is its theme's logo (A6 <c>logos/</c>); its other slots show what the theme draws or authored.</summary>
    public bool TryGetMedia(int index, int slot, out MediaRef media)
    {
        if (slot == MediaSlots.Logo && entries[index].Logo is { } logo)
        {
            media = logo;
            return true;
        }

        media = default;
        return false;
    }

    public bool UsesTemplate(int template) => template < _uses.Length && _uses[template];

    private static bool[] Uses(IReadOnlyList<SystemEntry> entries, int count)
    {
        var uses = new bool[count];
        foreach (var entry in entries)
        {
            if (entry.Template < count)
            {
                uses[entry.Template] = true;
            }
        }

        return uses;
    }
}

/// <summary>
/// A grid of games, from one system's list or a virtual one, with each game's media for the slots the theme uses and
/// its per-game model, if any. Built on the thread pool (it works out each game's letter group for letter jumps),
/// then handed to the main thread, which binds it to templates (<see cref="BindTemplates"/>) and updates its media
/// when they change (<see cref="ReplaceMedia"/>).
/// </summary>
public sealed class GamesSource : IGridSource
{
    private readonly GameRow[] _rows;
    private readonly int[] _system;
    private readonly string[] _systemIds;
    private readonly Color[] _colours;
    private readonly string[] _systemNames;
    private readonly char[] _letters;
    private readonly MediaRef[]?[] _media = new MediaRef[]?[MediaSlots.Count];
    private readonly bool[] _replaces = new bool[MediaSlots.Count];
    private readonly int[] _model;
    private readonly List<string> _modelPaths = [];
    private readonly List<MediaRef> _modelFiles = [];
    private Dictionary<long, int>? _index;
    private int[] _systemTemplate = [];
    private int[] _template = [];
    private ItemTemplate?[] _models = [];
    private bool[] _usesTemplate = [];

    private GamesSource(
        string id, string name, IReadOnlyList<(string SystemId, GameRow Row)> rows, IReadOnlyList<GameMediaRow> media,
        IReadOnlyList<string> kinds, Func<string, Color> colourOf, Func<string, string> nameOf)
    {
        Id = id;
        Name = name;
        Kinds = kinds;
        _rows = new GameRow[rows.Count];
        _system = new int[rows.Count];
        _colours = new Color[rows.Count];
        _systemNames = new string[rows.Count];
        _letters = new char[rows.Count];
        _model = new int[rows.Count];
        Array.Fill(_model, -1);
        var systems = new List<string>();
        var systemColours = new List<Color>();
        for (var i = 0; i < rows.Count; i++)
        {
            var (systemId, row) = rows[i];
            _rows[i] = row;
            var system = systems.IndexOf(systemId);
            if (system < 0)
            {
                system = systems.Count;
                systems.Add(systemId);
                systemColours.Add(colourOf(systemId));
            }

            _system[i] = system;
            _systemNames[i] = nameOf(systemId);
            _colours[i] = Palette.PlainBox(systemColours[system], row.GameId);
            _letters[i] = LetterOf(row.Title);
        }

        _systemIds = [.. systems];

        // The kinds the theme's chains name come from the media query, which replaces them; the cover also comes with
        // each row, for a theme whose chains never name it.
        foreach (var kind in kinds)
        {
            if (MediaSlots.IndexOf(kind) is var slot and >= 0)
            {
                _media[slot] = new MediaRef[_rows.Length];
                _replaces[slot] = true;
            }
        }

        var cover = _media[MediaSlots.Cover] ??= new MediaRef[_rows.Length];
        for (var i = 0; i < _rows.Length; i++)
        {
            var row = _rows[i];
            if (row.CoverPath is not null)
            {
                cover[i] = new MediaRef(row.CoverPath, row.CoverAspect, row.CoverSizeBytes, row.CoverMtimeMs);
            }
        }

        ReplaceMedia(media, null);
    }

    /// <summary>The entry id this list belongs to (a system id, or a virtual one).</summary>
    public string Id { get; }

    /// <summary>The heading for the grid (the system's name).</summary>
    public string Name { get; }

    /// <summary>The media kinds this list was loaded with (the theme's, when it was built).</summary>
    public IReadOnlyList<string> Kinds { get; }

    /// <summary>The order a system's list was read in (<c>games_sort</c>); a virtual list's own order is fixed.</summary>
    public GamesOrdering Ordering { get; private init; }

    /// <summary>The systems its games come from (one, except in a virtual list).</summary>
    public IReadOnlyList<string> SystemIds => _systemIds;

    /// <summary>The per-game model files its games use (DataDir-relative), each once.</summary>
    public IReadOnlyList<string> ModelPaths => _modelPaths;

    /// <summary>Per-game model files whose size or time changed in the last <see cref="ReplaceMedia"/> (to load again).</summary>
    public List<string> ChangedModelFiles { get; } = [];

    public int Count => _rows.Length;

    public GameRow Row(int index) => _rows[index];

    /// <summary>The name of the system the game belongs to, for the overlay.</summary>
    public string SystemName(int index) => _systemNames[index];

    /// <summary>Every game id, for refreshing a virtual list's media.</summary>
    public long[] GameIds()
    {
        var ids = new long[_rows.Length];
        for (var i = 0; i < ids.Length; i++)
        {
            ids[i] = _rows[i].GameId;
        }

        return ids;
    }

    /// <param name="ordering">The order the list was read in, so a change of sort can tell it's stale.</param>
    public static GamesSource ForSystem(
        string id, string name, GameList list, IReadOnlyList<GameMediaRow> media, IReadOnlyList<string> kinds, Func<string, Color> colourOf,
        GamesOrdering ordering = default)
    {
        var rows = new (string, GameRow)[list.Games.Count];
        for (var i = 0; i < rows.Length; i++)
        {
            rows[i] = (list.SystemId, list.Games[i]);
        }

        return new GamesSource(id, name, rows, media, kinds, colourOf, _ => name) { Ordering = ordering };
    }

    public static GamesSource ForVirtual(
        string id, string name, IReadOnlyList<VirtualGameRow> list, IReadOnlyList<GameMediaRow> media, IReadOnlyList<string> kinds,
        Func<string, Color> colourOf, Func<string, string> nameOf)
    {
        var rows = new (string, GameRow)[list.Count];
        for (var i = 0; i < rows.Length; i++)
        {
            rows[i] = (list[i].SystemId, list[i].Game);
        }

        return new GamesSource(id, name, rows, media, kinds, colourOf, nameOf);
    }

    /// <summary>
    /// Main thread: which grid template each game uses: the template the user chose for it, when the theme has it
    /// loaded (<paramref name="chosenTemplate"/>, -1 when not), else its system's. Per-game models are given as they
    /// load (<see cref="SetModel"/>); until then a game shows its template.
    /// </summary>
    public void BindTemplates(Func<string, int> systemTemplate, Func<string, int> chosenTemplate, int templateCount)
    {
        _systemTemplate = new int[_systemIds.Length];
        for (var s = 0; s < _systemIds.Length; s++)
        {
            _systemTemplate[s] = systemTemplate(_systemIds[s]);
        }

        _template = new int[_rows.Length];
        for (var i = 0; i < _rows.Length; i++)
        {
            _template[i] = _rows[i].Template is { } chosen && chosenTemplate(chosen) is var t and >= 0 ? t : _systemTemplate[_system[i]];
        }

        _models = new ItemTemplate?[_modelPaths.Count];
        UpdateUses(templateCount);
    }

    /// <summary>Main thread: a per-game model has loaded (drawn on its own node). Returns the games that use it.</summary>
    public List<int> SetModel(int model, ItemTemplate template)
    {
        _models[model] = template;
        var games = new List<int>();
        for (var i = 0; i < _model.Length; i++)
        {
            if (_model[i] == model)
            {
                games.Add(i);
            }
        }

        return games;
    }

    /// <summary>
    /// Replaces the media of the games the rows cover (<paramref name="gameIds"/>: those games; null: every game) and
    /// returns the indices whose media or per-game model changed. Main thread once the source is bound.
    /// </summary>
    public List<int> ReplaceMedia(IReadOnlyList<GameMediaRow> rows, IReadOnlyList<long>? gameIds)
    {
        ChangedModelFiles.Clear();
        if (_index is null)
        {
            _index = new Dictionary<long, int>(_rows.Length);
            for (var i = 0; i < _rows.Length; i++)
            {
                _index.TryAdd(_rows[i].GameId, i);
            }
        }

        // What the rows say, per game; a game being replaced that has no row of a kind has none of it now.
        var incoming = new Dictionary<int, (MediaRef[] Slots, MediaRef? Model)>();
        foreach (var row in rows)
        {
            if (!_index.TryGetValue(row.GameId, out var i))
            {
                continue;
            }

            if (!incoming.TryGetValue(i, out var entry))
            {
                entry = (new MediaRef[MediaSlots.Count], null);
            }

            if (row.Kind == MediaKinds.Model)
            {
                entry.Model = row.Media;
            }
            else if (MediaSlots.IndexOf(row.Kind) is var slot and >= 0)
            {
                entry.Slots[slot] = row.Media;
            }

            incoming[i] = entry;
        }

        var changed = new List<int>();
        var count = gameIds?.Count ?? _rows.Length;
        for (var n = 0; n < count; n++)
        {
            var i = n;
            if (gameIds is not null && !_index.TryGetValue(gameIds[n], out i))
            {
                continue;
            }

            incoming.TryGetValue(i, out var entry);
            var differs = false;
            for (var slot = 0; slot < MediaSlots.Count; slot++)
            {
                if (!_replaces[slot])
                {
                    continue;
                }

                var media = entry.Slots is null ? default : entry.Slots[slot];
                if (_media[slot]![i] != media)
                {
                    _media[slot]![i] = media;
                    differs = true;
                }
            }

            var model = entry.Model is { } file ? ModelIndex(file.Path) : -1;
            if (model != _model[i])
            {
                _model[i] = model;
                differs = true;
            }

            // The same file changed (imported again): it's loaded again, and the game shows its template meanwhile.
            if (entry.Model is { } changedFile && _modelFiles[model] != changedFile)
            {
                if (_modelFiles[model].Path is not null)
                {
                    ChangedModelFiles.Add(changedFile.Path);
                    if (model < _models.Length)
                    {
                        _models[model] = null;
                    }

                    differs = true;
                }

                _modelFiles[model] = changedFile;
            }

            if (differs)
            {
                changed.Add(i);
            }
        }

        if (_models.Length != _modelPaths.Count)
        {
            var grown = new ItemTemplate?[_modelPaths.Count];
            Array.Copy(_models, grown, Math.Min(_models.Length, grown.Length));
            _models = grown;
        }

        return changed;
    }

    /// <summary>
    /// Main thread: the list read again after titles changed (M7). When it holds the same games in the same order, the
    /// titles are updated in place and the indices that changed returned; otherwise null, and the list must be bound
    /// again. A game whose chosen template changed (2026-10-07) also needs the list bound again, to its templates.
    /// </summary>
    public List<int>? UpdateTitles(IReadOnlyList<GameRow> rows)
    {
        if (rows.Count != _rows.Length)
        {
            return null;
        }

        for (var i = 0; i < rows.Count; i++)
        {
            if (rows[i].GameId != _rows[i].GameId || !string.Equals(rows[i].Template, _rows[i].Template, StringComparison.Ordinal))
            {
                return null;
            }
        }

        var changed = new List<int>();
        for (var i = 0; i < rows.Count; i++)
        {
            if (!string.Equals(rows[i].Title, _rows[i].Title, StringComparison.Ordinal))
            {
                _rows[i] = _rows[i] with { Title = rows[i].Title };
                _letters[i] = LetterOf(rows[i].Title);
                changed.Add(i);
            }
        }

        return changed;
    }

    public void Describe(int index, out CellInfo cell)
    {
        ref readonly var row = ref _rows[index];
        var model = _model[index];
        cell = new CellInfo
        {
            Title = row.Title,
            Template = _template[index],
            Model = model >= 0 ? _models[model] : null,
            Plain = _colours[index],
        };
    }

    public bool TryGetMedia(int index, int slot, out MediaRef media)
    {
        if (_media[slot] is { } kind && kind[index].Path is not null)
        {
            media = kind[index];
            return true;
        }

        media = default;
        return false;
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

    private int ModelIndex(string path)
    {
        var index = _modelPaths.IndexOf(path);
        if (index < 0)
        {
            index = _modelPaths.Count;
            _modelPaths.Add(path);
            _modelFiles.Add(default);
        }

        return index;
    }

    private void UpdateUses(int templateCount)
    {
        _usesTemplate = new bool[templateCount];
        foreach (var template in _template)
        {
            if (template >= 0 && template < templateCount)
            {
                _usesTemplate[template] = true;
            }
        }
    }

    private static char RemoveAccent(char c)
    {
        var decomposed = c.ToString().Normalize(System.Text.NormalizationForm.FormD);
        return decomposed.Length > 0 ? decomposed[0] : c;
    }
}
