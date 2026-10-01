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
using Launcher.Core.Scraping;

namespace Launcher.App.Options;

/// <summary>
/// Manual matching, for the game options' "scrape this game": every provider is searched at once for the game's name
/// (its title, or a name the user types), and each one's results are listed under it, the closest name first. A on a
/// result scrapes the game with it (<see cref="ScrapeService.ScrapeGameWithMatchAsync"/>): that game's data comes
/// first, and the other providers fill in what it lacks. The choice is saved as a manual match, which later scrapes
/// keep to. Each provider's current match is marked, so scraping again with it is one press.
/// </summary>
public sealed partial class GameMatchPanel : ListPanel
{
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
            Build(focusFirstResult: false);
        }
    }

    /// <summary>
    /// Made-up results for <paramref name="game"/>, for captures (<c>--open=match</c>): each kind of provider
    /// section (results with the current match among them, the current match not among them, nothing found, and
    /// providers that couldn't be searched). Nothing goes over the network.
    /// </summary>
    public static MatchSearch MadeUpResults(GameDetails game, string systemName)
    {
        var term = game.Title;
        return new MatchSearch(game.Key, term,
        [
            new ProviderMatches(ScraperIds.ScreenScraper, "ScreenScraper", true,
            [
                new MatchCandidate("1187", term, "1994", 1),
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

    public override void OnClosed() => _cancel?.Cancel();

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
                        $"Match: {key.SystemId}/{key.PathKey}: '{search.Term}': {string.Join(", ", search.Providers.Select(p => $"{p.Provider} {(p.Problem is null ? p.Candidates.Count : "-")}"))}"));
                }

                Build(focusFirstResult: true);
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
                AddResult(provider, current, "Its match now, not among these results", $"ID {current} · {Origin(provider)}", isCurrent: true);
                firstCurrent = firstCurrent < 0 ? rows : firstCurrent;
                rows++;
            }

            foreach (var candidate in provider.Candidates)
            {
                var isCurrent = candidate.ProviderGameId == current;
                var detail = string.Create(CultureInfo.InvariantCulture, $"ID {candidate.ProviderGameId} · {candidate.Similarity * 100:0}% like {Quote(_search!.Term)}");
                AddResult(provider, candidate.ProviderGameId, Label(candidate), isCurrent ? $"{detail} · its match now, {Origin(provider)}" : detail, isCurrent);
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

    private void AddResult(ProviderMatches provider, string id, string title, string detail, bool isCurrent)
    {
        var row = AddRow(title, detail, isCurrent ? "In use" : null, () => Choose(provider.Provider, id));
        row.ValueColour = UiStyle.Good;
    }

    private void Choose(string provider, string id)
    {
        GD.Print($"Match: {_key.SystemId}/{_key.PathKey}: scraping with {provider} {id}");
        Close();
        _scrape(provider, id);
    }

    private static string Label(MatchCandidate candidate) => candidate.Year is { } year ? $"{candidate.Name} ({year})" : candidate.Name;

    private static string Origin(ProviderMatches provider) => provider.CurrentIsManual ? "chosen by you" : "found automatically";

    private static string Quote(string text) => $"“{text}”";
}
