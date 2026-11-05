using System;
using System.Collections.Generic;
using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.App.Screens;

public sealed partial class Navigator
{
    // ---- Entries --------------------------------------------------------------------------------

    /// <summary>
    /// Main thread: the systems grid built again from <paramref name="summaries"/> and bound, whichever screen is
    /// shown, with the focus on the system it was on (or in the same place, if that one dropped out).
    /// </summary>
    private void RebindSystems(IReadOnlyList<SystemSummary> summaries)
    {
        var systemsFocus = _systemsGrid.FocusIndex;
        var focusedId = systemsFocus >= 0 && systemsFocus < _systems.Entries.Count ? _systems.Entries[systemsFocus].Id : null;
        _systems = new SystemsSource(BuildEntries(summaries), _systemsGrid.Templates.Count);
        var index = -1;
        for (var i = 0; focusedId is not null && i < _systems.Entries.Count; i++)
        {
            if (_systems.Entries[i].Id == focusedId)
            {
                index = i;
                break;
            }
        }

        _systemsGrid.Layout = SystemsLayout();
        _systemsGrid.Bind(_systems, index >= 0 ? index : Math.Clamp(systemsFocus, 0, Math.Max(0, _systems.Entries.Count - 1)));
    }

    private List<SystemEntry> BuildEntries(IReadOnlyList<SystemSummary> summaries)
    {
        var entries = new List<SystemEntry>
        {
            new(FavouritesId, "Favourites", "The games you've marked", Palette.Favourites, null, null, VirtualKind.Favourites, _theme.CardTemplateOf(FavouritesId),
                _theme.LogoOf(FavouritesId)),
            new(RecentlyPlayedId, "Recently played", "Newest first", Palette.RecentlyPlayed, null, null, VirtualKind.RecentlyPlayed, _theme.CardTemplateOf(RecentlyPlayedId),
                _theme.LogoOf(RecentlyPlayedId)),
        };
        // Only the shown systems' cards are loaded (2026-10-27): a system that just appeared shows the default card until
        // its own is in (ApplyCards), and the cards of those that went are freed then.
        var cards = SystemCards(summaries, _services.Config);
        var shown = new List<string>(cards.Count);
        foreach (var card in cards)
        {
            shown.Add(card.System.Id);
        }

        _theme.UseShownSystems(shown);
        _pendingTheme?.UseShownSystems(shown);

        var games = 0;
        foreach (var summary in summaries)
        {
            if (_services.Config.FindSystem(summary.SystemId) is not null)
            {
                games += summary.GameCount;
            }
        }

        var systems = new List<SystemEntry>(cards.Count);
        foreach (var (system, summary, members) in cards)
        {
            systems.Add(new SystemEntry(system.Id, system.Name, DetailsFormatter.SystemSubtitle(system, summary.GameCount),
                _theme.ColourOf(system.Id), system, summary, VirtualKind.None, _theme.CardTemplateOf(system.Id), _theme.LogoOf(system.Id),
                members));
        }

        entries.Add(new(AllGamesId, "All games", DetailsFormatter.GamesCount(games), Palette.AllGames, null, null, VirtualKind.AllGames,
            _theme.CardTemplateOf(AllGamesId), _theme.LogoOf(AllGamesId)));

        // Favourites, Recently played and All games stay first, whatever the systems' order.
        SystemOrder.Sort(systems, static entry => entry.System!, _services.Config.Settings.Display.SystemsSort);
        entries.AddRange(systems);
        return entries;
    }

    /// <summary>Whether the systems grid shows a system the config has: one with games, or any while empty ones show.</summary>
    public static bool Shows(SystemSummary summary, DisplaySettings display) => summary.GameCount > 0 || !display.HideEmptySystems;

    /// <summary>The systems the grid shows cards of (<see cref="SystemCards"/>), whose cards the theme loads (2026-10-27).</summary>
    public static List<string> ShownSystemIds(IReadOnlyList<SystemSummary> summaries, AppConfig config)
    {
        var cards = SystemCards(summaries, config);
        var ids = new List<string>(cards.Count);
        foreach (var card in cards)
        {
            ids.Add(card.System.Id);
        }

        return ids;
    }

    /// <summary>
    /// The systems grid's system cards, in the summaries' order (A5 Grouped systems): every system not grouped under
    /// another, that <see cref="Shows"/> or has a grouped system that does. A group's card has its members, and its
    /// summary counts all their games.
    /// </summary>
    public static List<SystemCard> SystemCards(IReadOnlyList<SystemSummary> summaries, AppConfig config)
    {
        var display = config.Settings.Display;
        Dictionary<string, (int Games, bool Shows)>? groups = null;
        foreach (var summary in summaries)
        {
            if (config.FindSystem(summary.SystemId) is { } system && config.GroupParentOf(system) is { } parent)
            {
                groups ??= new Dictionary<string, (int, bool)>(StringComparer.Ordinal);
                groups.TryGetValue(parent.Id, out var group);
                groups[parent.Id] = (group.Games + summary.GameCount, group.Shows || Shows(summary, display));
            }
        }

        var cards = new List<SystemCard>(summaries.Count);
        foreach (var summary in summaries)
        {
            if (config.FindSystem(summary.SystemId) is not { } system || config.GroupParentOf(system) is not null)
            {
                continue;
            }

            if (groups is not null && groups.TryGetValue(system.Id, out var group))
            {
                if (Shows(summary, display) || group.Shows)
                {
                    cards.Add(new SystemCard(system, summary with { GameCount = summary.GameCount + group.Games }, config.GroupMembers(system.Id)));
                }
            }
            else if (Shows(summary, display))
            {
                cards.Add(new SystemCard(system, summary, null));
            }
        }

        return cards;
    }

    /// <summary>The first real system with games (or the first real one), so boot lands on something useful.</summary>
    private int FirstRealSystem()
    {
        var first = -1;
        for (var i = 0; i < _systems.Entries.Count; i++)
        {
            var entry = _systems.Entries[i];
            if (entry.Virtual != VirtualKind.None)
            {
                continue;
            }

            if (first < 0)
            {
                first = i;
            }

            if (entry.Summary is { GameCount: > 0 })
            {
                return i;
            }
        }

        return Math.Max(first, 0);
    }

    /// <summary>A grid's transition state: faded into the background, scaled and moved in depth.</summary>
    private readonly record struct GridPose(float Fade, float Zoom, float Depth)
    {
        public static GridPose Lerp(GridPose a, GridPose b, float t) =>
            new(a.Fade + (b.Fade - a.Fade) * t, a.Zoom + (b.Zoom - a.Zoom) * t, a.Depth + (b.Depth - a.Depth) * t);
    }

    private struct GridAnimation
    {
        private GridPose _from;
        private GridPose _to;
        private float _time;
        private float _duration;

        public bool Active { get; private set; }

        public float Progress => Active && _duration > 0 ? Math.Min(1, _time / _duration) : 0;

        public void Start(GridPose from, GridPose to, float duration)
        {
            _from = from;
            _to = to;
            _time = 0;
            _duration = duration;
            Active = true;
        }

        /// <summary>True when the pose changed this frame.</summary>
        public bool Update(float dt, out GridPose pose)
        {
            if (!Active)
            {
                pose = _to;
                return false;
            }

            _time += dt;
            var t = Math.Min(1, _time / _duration);
            var eased = 1 - (1 - t) * (1 - t) * (1 - t);
            pose = GridPose.Lerp(_from, _to, eased);

            // The outgoing grid has faded by 65% of the way and the incoming one appears from 30%, so the two barely
            // overlap: they're opaque, and the nearer would hide the other.
            var hiding = _to.Fade > _from.Fade;
            var fade = hiding ? Math.Min(1, t / 0.65f) : Math.Clamp((t - 0.3f) / 0.7f, 0, 1);
            pose = pose with { Fade = _from.Fade + (_to.Fade - _from.Fade) * fade };
            if (t >= 1)
            {
                Active = false;
            }

            return true;
        }
    }
}
