using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Scraping;

namespace Launcher.App.Options;

/// <summary>
/// Manual matching, for the game options' "scrape this game": every provider is searched at once for the game's name
/// (its title, or a name the user types), and each one's results are listed under it, the closest name first. A on a
/// result scrapes the game with it (<see cref="ScrapeService.ScrapeGameWithMatchAsync"/>): that game's data comes
/// first, and the other providers fill in what it lacks. The choice is saved as a manual match, which later scrapes
/// keep to. Each provider's current match is marked, so scraping again with it is one press. From 2026-10-07 each
/// result shows its cover, so games of one name can be told apart: downloaded small and decoded off the main thread,
/// each provider's from the top of its list, two at a time, and kept while the panel is open (a search for another
/// name shows the ones it already has at once).
/// </summary>
public sealed partial class GameMatchPanel : ListPanel
{
    /// <summary>Each provider's covers downloaded at once (its own limits still apply).</summary>
    private const int CoversAtOnce = 2;

    /// <summary>A result's cover frame, about a box's shape.</summary>
    private static readonly Vector2 CoverSize = new(60, 80);

    /// <summary>What a cover is scaled down to fit when decoded: twice its frame, for a window larger than the UI's 1280×800.</summary>
    private static readonly Vector2I DecodeSize = new(120, 160);

    private readonly Dictionary<(string Provider, string Id), Cover> _covers = [];
    private readonly Dictionary<(string Provider, string Id), SettingRow> _coverRows = [];
    private readonly ItemOptions _options;
    private readonly GameKey _key;
    private readonly string _title;
    private readonly Action<string, string> _scrape;
    private readonly bool _madeUp;
    private MatchSearch? _search;
    private string? _failure;
    private bool _searching;
    private int _generation;
    private CancellationTokenSource? _cancel;
    private CancellationTokenSource? _coverCancel;
    private int _coverGeneration;

    /// <param name="scrape">Gets the provider and its game's id when the user chooses one (the panel has closed by then).</param>
    /// <param name="madeUp">Results to show instead of searching (<c>--open=match</c>): nothing is searched or scraped.</param>
    public GameMatchPanel(ItemOptions options, GameDetails game, Action<string, string> scrape, MatchSearch? madeUp = null)
        : base($"Scrape {game.Title}")
    {
        _options = options;
        _key = game.Key;
        _title = game.Title;
        _scrape = scrape;
        Subtitle = "Choose the right game: it's scraped with that one, and the other providers fill in what it lacks";
        SetHints("A  Scrape with this game     X  Search for another name     B  Back");
        if (madeUp is null)
        {
            Search(null);
        }
        else
        {
            _madeUp = true;
            _search = madeUp;
            MakeUpCovers(madeUp);
            Build(focusFirstResult: false);
        }
    }

    /// <summary>
    /// Made-up results for <paramref name="game"/>, for captures (<c>--open=match</c>): each kind of provider
    /// section (the file's own match and results with the current match among them, the current match not among
    /// them, nothing found, and providers that couldn't be searched). Nothing goes over the network.
    /// </summary>
    public static MatchSearch MadeUpResults(GameDetails game, string systemName)
    {
        var term = game.Title;
        return new MatchSearch(game.Key, term,
        [
            new ProviderMatches(ScraperIds.ScreenScraper, "ScreenScraper", true,
            [
                new MatchCandidate("1187", term, "1994", 1, MatchMethods.Filename),
                new MatchCandidate("1190", term + " & Knuckles", "1994", 0.9),
                new MatchCandidate("52211", term + " (Prototype)", null, 0.9),
                new MatchCandidate("3402", "Sonic Spinball", "1993", 0.41),
            ], null, "1187", false),
            new ProviderMatches(ScraperIds.Igdb, "IGDB", true,
            [
                new MatchCandidate("1234", term, "1994", 1),
                new MatchCandidate("99", "Sonic Mania", "2017", 0.38),
            ], null, "8800", true),
            new ProviderMatches(ScraperIds.SteamGridDb, "SteamGridDB", true, [], null, null, false),
            new ProviderMatches(ScraperIds.Steam, "Steam store", false, [], $"{systemName} has no steam_store in systems.toml", null, false),
        ]);
    }

    public override bool Handle(NavCommand command)
    {
        if (command != NavCommand.Alternate)
        {
            return false;
        }

        EditTerm();
        return true;
    }

    public override void OnClosed()
    {
        _cancel?.Cancel();
        _coverCancel?.Cancel();
        _coverGeneration++;
        foreach (var cover in _covers.Values)
        {
            cover.Texture?.Dispose();
        }

        _covers.Clear();
    }

    // ---- Searching -----------------------------------------------------------------------------------

    /// <summary>Searches every provider for <paramref name="term"/> (null: the game's own title), off the main thread.</summary>
    private void Search(string? term)
    {
        if (_madeUp)
        {
            ShowStatus("These results are made up (--open=match): nothing is searched.", UiStyle.Dim, 4);
            return;
        }

        _cancel?.Cancel();
        var cancel = new CancellationTokenSource();
        _cancel = cancel;
        var generation = ++_generation;
        _searching = true;
        _failure = null;
        Build(focusFirstResult: false);

        var jobs = _options.Jobs;
        var key = _key;
        _ = Task.Run(async () =>
        {
            MatchSearch? search = null;
            string? failure = null;
            try
            {
                search = await jobs.SearchMatchesAsync(key, term, cancel.Token).ConfigureAwait(false);
                failure = search is null ? "It isn't in the library any more: rescan first." : null;
            }
            catch (OperationCanceledException)
            {
                return;
            }
            catch (Exception e)
            {
                failure = $"The search failed: {e.Message}";
            }

            _options.Ui.Queue.Post(() =>
            {
                if (generation != _generation || !IsInstanceValid(this))
                {
                    return;
                }

                _searching = false;
                _failure = failure;
                if (search is not null)
                {
                    _search = search;
                    GD.Print(string.Create(CultureInfo.InvariantCulture,
                        $"Match: {key.SystemId}/{key.PathKey}: '{search.Term}': {string.Join(", ", search.Providers.Select(p => $"{p.Provider} {(p.Problem is null ? p.Candidates.Count : "-")}{FileHit(p)}"))}"));
                }

                Build(focusFirstResult: true);
                LoadCovers();
            });
        });
    }

    private void EditTerm()
    {
        OnScreenKeyboard.Open(Layer, new KeyboardRequest(
            $"Search for {_title}",
            _search?.Term ?? string.Empty,
            text => Search(text.Trim()),
            Placeholder: "The game's name",
            Subtitle: "Every provider is searched for this name",
            Validate: text => text.Trim().Length == 0 ? "Type a name to search for." : null));
    }

    // ---- The list ------------------------------------------------------------------------------------

    private void Build(bool focusFirstResult)
    {
        ClearRows(out var focused);
        _coverRows.Clear();
        var term = _search?.Term;
        var rows = 1;
        AddRow("Search for", _searching ? "Searching every provider…" : term is null ? "—" : Quote(term), "Change", EditTerm);
        if (_failure is not null)
        {
            AddNote(_failure, UiStyle.Bad);
        }

        // After a search the focus goes to the first current match, else the first result.
        var first = -1;
        var firstCurrent = -1;
        var unsearched = new List<ProviderMatches>();
        foreach (var provider in _search?.Providers ?? [])
        {
            if (provider.Problem is not null)
            {
                unsearched.Add(provider);
                continue;
            }

            AddSection(provider.DisplayName + (provider.InOrder ? string.Empty : " · not in your scraping order"));
            var current = provider.Current;
            if (current is not null && provider.Candidates.All(c => c.ProviderGameId != current))
            {
                // Its match isn't among these results: it can still be scraped again.
                AddResult(provider, current, null, "Its match now, not among these results", $"ID {current} · {Origin(provider)}", isCurrent: true);
                firstCurrent = firstCurrent < 0 ? rows : firstCurrent;
                rows++;
            }

            foreach (var candidate in provider.Candidates)
            {
                var isCurrent = candidate.ProviderGameId == current;
                var detail = candidate.MatchedBy is { } matchedBy
                    ? $"ID {candidate.ProviderGameId} · matches the file's {(matchedBy == MatchMethods.Hash ? "contents" : "name")}"
                    : string.Create(CultureInfo.InvariantCulture, $"ID {candidate.ProviderGameId} · {candidate.Similarity * 100:0}% like {Quote(_search!.Term)}");
                AddResult(provider, candidate.ProviderGameId, candidate, Label(candidate), isCurrent ? $"{detail} · its match now, {Origin(provider)}" : detail, isCurrent);
                first = first < 0 ? rows : first;
                firstCurrent = isCurrent && firstCurrent < 0 ? rows : firstCurrent;
                rows++;
            }

            if (provider.Candidates.Count == 0)
            {
                AddNote($"Nothing found for {Quote(_search!.Term)}. Search for another name with X.");
            }
        }

        if (unsearched.Count > 0)
        {
            AddSection("Couldn't be searched");
            foreach (var provider in unsearched)
            {
                AddNote($"{provider.DisplayName}: {provider.Problem}" + (provider.Current is not null ? ". It keeps its match." : string.Empty), UiStyle.Faint);
            }
        }

        var target = firstCurrent >= 0 ? firstCurrent : first;
        FocusRow(focusFirstResult && target > 0 ? target : Math.Max(focused, 0));
    }

    /// <param name="candidate">The search hit, whose cover the row shows; null for a current match the search didn't list (an empty frame).</param>
    private void AddResult(ProviderMatches provider, string id, MatchCandidate? candidate, string title, string detail, bool isCurrent)
    {
        var row = AddRow(title, detail, isCurrent ? "In use" : null, () => Choose(provider.Provider, id));
        row.ValueColour = UiStyle.Good;
        row.ShowPicture(CoverSize);
        if (candidate is null)
        {
            return;
        }

        var key = (provider.Provider, id);
        if (_covers.TryGetValue(key, out var cover))
        {
            row.SetPicture(cover.Texture, cover.Loaded ? cover.Caption : "…");
            _coverRows[key] = row;
        }
        else if (candidate.Cover is null)
        {
            row.SetPicture(null, "No cover");
        }
        else
        {
            // Asked for once the list is built (LoadCovers).
            row.SetPicture(null, "…");
            _coverRows[key] = row;
        }
    }

    // ---- Covers --------------------------------------------------------------------------------------

    /// <summary>
    /// Main thread, after a search: downloads the covers of the results not loaded yet, each provider's on a worker
    /// of its own from the top of its list. A cover still loading for an earlier search is asked for again.
    /// </summary>
    private void LoadCovers()
    {
        if (_search is null || _madeUp)
        {
            return;
        }

        _coverCancel?.Cancel();
        var cancel = new CancellationTokenSource();
        _coverCancel = cancel;
        var generation = ++_coverGeneration;
        foreach (var key in _covers.Where(c => !c.Value.Loaded).Select(c => c.Key).ToList())
        {
            _covers.Remove(key);
        }

        var jobs = _options.Jobs;
        var queue = _options.Ui.Queue;
        foreach (var provider in _search.Providers)
        {
            var wanted = new List<((string Provider, string Id) Key, MatchCover Cover)>();
            foreach (var candidate in provider.Candidates)
            {
                var key = (provider.Provider, candidate.ProviderGameId);
                if (candidate.Cover is { } cover && !_covers.ContainsKey(key))
                {
                    _covers[key] = new Cover();
                    wanted.Add((key, cover));
                }
            }

            if (wanted.Count == 0)
            {
                continue;
            }

            _ = Task.Run(async () =>
            {
                try
                {
                    var parallel = new ParallelOptions { MaxDegreeOfParallelism = CoversAtOnce, CancellationToken = cancel.Token };
                    await Parallel.ForEachAsync(wanted, parallel, async (item, token) =>
                    {
                        ImageTexture? texture;
                        string? caption;
                        try
                        {
                            var bytes = await jobs.GetMatchCoverAsync(item.Cover, token).ConfigureAwait(false);
                            texture = bytes is null ? null : Decode(bytes);
                            caption = texture is null ? "No cover" : null;
                        }
                        catch (OperationCanceledException)
                        {
                            return;
                        }
                        catch (Exception e)
                        {
                            GD.PushWarning($"Match: {item.Cover}: {e.Message}");
                            texture = null;
                            caption = "Not loaded";
                        }

                        queue.Post(() => CoverLoaded(generation, item.Key, texture, caption));
                    }).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    // Another search, or the panel closed.
                }
            });
        }
    }

    /// <summary>Main thread: a cover downloaded and decoded (null: none, with why in <paramref name="caption"/>).</summary>
    private void CoverLoaded(int generation, (string Provider, string Id) key, ImageTexture? texture, string? caption)
    {
        if (generation != _coverGeneration || !IsInstanceValid(this) || !_covers.TryGetValue(key, out var cover) || cover.Loaded)
        {
            texture?.Dispose();
            return;
        }

        cover.Loaded = true;
        cover.Texture = texture;
        cover.Caption = caption;
        if (_coverRows.TryGetValue(key, out var row) && IsInstanceValid(row))
        {
            row.SetPicture(texture, caption);
        }
    }

    /// <summary>Worker thread: a cover's bytes as a texture no larger than <see cref="DecodeSize"/>; null when they can't be read.</summary>
    private static ImageTexture? Decode(byte[] bytes)
    {
        var image = new Image();
        var error = ImageFormats.Sniff(bytes) switch
        {
            ".png" => image.LoadPngFromBuffer(bytes),
            ".jpg" => image.LoadJpgFromBuffer(bytes),
            ".webp" => image.LoadWebpFromBuffer(bytes),
            _ => Error.FileUnrecognized,
        };
        if (error != Error.Ok || image.IsEmpty())
        {
            image.Dispose();
            return null;
        }

        var scale = Math.Min(1.0, Math.Min((double)DecodeSize.X / image.GetWidth(), (double)DecodeSize.Y / image.GetHeight()));
        if (scale < 1)
        {
            image.Resize(Math.Max(1, (int)Math.Round(image.GetWidth() * scale)), Math.Max(1, (int)Math.Round(image.GetHeight() * scale)), Image.Interpolation.Lanczos);
        }

        var texture = ImageTexture.CreateFromImage(image);
        image.Dispose();
        return texture;
    }

    /// <summary>
    /// <c>--open=match</c>: made-up covers for the made-up results, a gradient in a colour of each one's own, and none
    /// for the prototype, so a capture shows both.
    /// </summary>
    private void MakeUpCovers(MatchSearch search)
    {
        foreach (var provider in search.Providers)
        {
            foreach (var candidate in provider.Candidates)
            {
                var none = candidate.Name.EndsWith("(Prototype)", StringComparison.Ordinal);
                ImageTexture? texture = null;
                if (!none)
                {
                    // Its id's characters, not GetHashCode (which differs on each run), so captures repeat.
                    var hash = 0u;
                    foreach (var c in candidate.ProviderGameId)
                    {
                        hash = (hash * 31) + c;
                    }

                    var hue = hash % 360 / 360f;
                    var image = Image.CreateEmpty(DecodeSize.X / 2, DecodeSize.Y / 2, false, Image.Format.Rgba8);
                    for (var y = 0; y < image.GetHeight(); y++)
                    {
                        image.FillRect(new Rect2I(0, y, image.GetWidth(), 1), Color.FromHsv(hue, 0.6f, 0.9f - (0.5f * y / image.GetHeight())));
                    }

                    texture = ImageTexture.CreateFromImage(image);
                    image.Dispose();
                }

                _covers[(provider.Provider, candidate.ProviderGameId)] = new Cover { Loaded = true, Texture = texture, Caption = none ? "No cover" : null };
            }
        }
    }

    private void Choose(string provider, string id)
    {
        GD.Print($"Match: {_key.SystemId}/{_key.PathKey}: scraping with {provider} {id}");
        Close();
        _scrape(provider, id);
    }

    /// <summary>For the log: the provider's match for the file itself (its ROM index), when it had one.</summary>
    private static string FileHit(ProviderMatches provider) =>
        provider.Candidates.Count > 0 && provider.Candidates[0].MatchedBy is { } matchedBy
            ? $" (file: {provider.Candidates[0].ProviderGameId} by {matchedBy})"
            : string.Empty;

    private static string Label(MatchCandidate candidate) => candidate.Year is { } year ? $"{candidate.Name} ({year})" : candidate.Name;

    private static string Origin(ProviderMatches provider) => provider.CurrentIsManual ? "chosen by you" : "found automatically";

    private static string Quote(string text) => $"“{text}”";

    /// <summary>A result's cover: loading, loaded (its texture), or none (and why).</summary>
    private sealed class Cover
    {
        public bool Loaded { get; set; }

        public ImageTexture? Texture { get; set; }

        public string? Caption { get; set; }
    }
}
