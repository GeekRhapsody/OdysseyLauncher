using System;
using System.Collections.Generic;
using System.Globalization;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Grid;
using Launcher.App.Launching;
using Launcher.App.Navigation;
using Launcher.App.Textures;
using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.App.Screens;

/// <summary>
/// The screens (A1 Screens): Systems → Games → Launching, and back, with animated transitions between the two
/// grids, focus memory per system, the focused item's details in the overlay, favourites, rescans and launching.
/// Library calls run on the thread pool and their results come back through the <see cref="MainThreadQueue"/>.
/// </summary>
public sealed partial class Navigator : Node
{
    public const string FavouritesId = "favourites";
    public const string RecentlyPlayedId = "recently_played";
    private const int RecentlyPlayedLimit = 60;
    private const double DetailsDelay = 0.12;
    private const float TransitionSeconds = 0.45f;
    private const double LaunchAnimationSeconds = 0.7;
    private const int CachedLists = 3;

    private const string SystemsHints = "A / Enter  Open     View / F5  Rescan";
    private const string GamesHints = "A / Enter  Play     B / Esc  Back     Y / F  Favourite     LB RB  Page     LT RT  Letter";

    private static readonly GridPose Shown = new(0, 1, 0);
    private static readonly GridPose SystemsHidden = new(1, 1.12f, 0.7f);
    private static readonly GridPose GamesHidden = new(1, 0.82f, -1.6f);

    private readonly AppServices _services;
    private readonly MainThreadQueue _queue;
    private readonly ItemGrid _systemsGrid;
    private readonly ItemGrid _gamesGrid;
    private readonly InfoOverlay _overlay;
    private readonly NavInput _input = new();
    private readonly Func<string, int> _templateOf;
    private readonly int _templateCount;
    private readonly Func<string, string> _systemNameOf;
    private readonly Dictionary<string, long> _lastGame = new(StringComparer.Ordinal);
    private readonly List<GamesSource> _cache = [];
    private readonly CancellationTokenSource _shutdown = new();

    private SystemsSource _systems = null!;
    private GamesSource? _games;
    private Screen _screen = Screen.Systems;
    private GridAnimation _systemsAnimation;
    private GridAnimation _gamesAnimation;
    private string? _entering;
    private int _focusedIndex = -1;
    private long _focusKey = -1;
    private double _detailsDue = -1;
    private double _clock;
    private GameDetails? _focusedGame;
    private bool _scanning;
    private double _launchStartedAt;
    private GameDetails? _launchGame;
    private int _systemsTemplate;

    public Navigator(AppServices services, MainThreadQueue queue, ItemGrid systemsGrid, ItemGrid gamesGrid, InfoOverlay overlay, IReadOnlyList<string> templateIds)
    {
        Name = "Navigator";
        _services = services;
        _queue = queue;
        _systemsGrid = systemsGrid;
        _gamesGrid = gamesGrid;
        _overlay = overlay;
        _templateCount = templateIds.Count;
        var indexOf = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i < templateIds.Count; i++)
        {
            indexOf[templateIds[i]] = i;
        }

        var config = services.Config;
        var systemTemplate = new Dictionary<string, int>(StringComparer.Ordinal);
        var systemName = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var system in config.Systems)
        {
            systemTemplate[system.Id] = indexOf.TryGetValue(system.GameModel, out var t) ? t : 0;
            systemName[system.Id] = system.Name;
        }

        _templateOf = id => systemTemplate.TryGetValue(id, out var t) ? t : 0;
        _systemNameOf = id => systemName.TryGetValue(id, out var n) ? n : id;
    }

    private enum Screen
    {
        Systems,
        Entering,
        Games,
        Launching,
    }

    /// <summary>The launch controller, once the warm-up has built it.</summary>
    public LaunchController? Launcher { get; set; }

    /// <summary>The cover streamer, for evicting textures while a game runs.</summary>
    public TextureStreamer? Streamer { get; set; }

    /// <summary>True once a system's games are bound and its transition has finished.</summary>
    public bool InGames => _screen == Screen.Games && !_gamesAnimation.Active;

    public ItemGrid GamesGrid => _gamesGrid;

    public string? CurrentSystem => _games?.Id;

    /// <summary>Where the focus is, for the <c>--nav-script</c> log.</summary>
    public string Describe()
    {
        var grid = _screen == Screen.Systems ? _systemsGrid : _gamesGrid;
        var title = _screen == Screen.Systems
            ? grid.FocusIndex >= 0 ? _systems.Entries[grid.FocusIndex].Name : "-"
            : _games is not null && grid.FocusIndex >= 0 ? _games.Row(grid.FocusIndex).Title : "-";
        return $"{_screen}, {(_screen == Screen.Systems ? "systems" : _games?.Id ?? "?")}, item {grid.FocusIndex}: {title}";
    }

    /// <summary>Builds the systems grid from the boot query. Main thread.</summary>
    public void ShowSystems(int systemsTemplate)
    {
        _systemsTemplate = systemsTemplate;
        _systems = new SystemsSource(BuildEntries(_services.Systems), systemsTemplate);
        _systemsGrid.Bind(_systems, FirstRealSystem());
        _systemsGrid.Fade = 0;
        _gamesGrid.Fade = 1;
        _overlay.SetHints(SystemsHints);
        OnFocusChanged();
    }

    public override void _ExitTree()
    {
        _shutdown.Cancel();
    }

    /// <summary>Main thread, once per frame, before the grids tick (called by Main, so input acts in the same frame).</summary>
    public void Update(double delta)
    {
        _clock += delta;
        var dt = (float)delta;
        HandleInput(delta);
        Animate(dt);
        if (_detailsDue >= 0 && _clock >= _detailsDue)
        {
            _detailsDue = -1;
            RequestDetails();
        }

        if (_screen == Screen.Launching && _launchGame is not null && _clock - _launchStartedAt >= LaunchAnimationSeconds)
        {
            var game = _launchGame;
            _launchGame = null;
            if (Launcher is null)
            {
                FinishLaunch("The launcher isn't ready yet. Try again in a moment.");
            }
            else
            {
                Launcher.Launch(game);
            }
        }
    }

    // ---- Input ----------------------------------------------------------------------------------

    private void HandleInput(double delta)
    {
        var blocked = Launcher?.IsInputBlocked ?? false;
        var command = _input.Poll(delta, blocked || _screen is Screen.Entering or Screen.Launching);
        if (command != NavCommand.None)
        {
            Run(command);
        }
    }

    /// <summary>Acts on one command, from the controller or keyboard, or from <c>--nav-script</c>. Main thread.</summary>
    public void Run(NavCommand command)
    {
        if (_screen is Screen.Entering or Screen.Launching)
        {
            return;
        }

        var grid = _screen == Screen.Systems ? _systemsGrid : _gamesGrid;
        var moved = command switch
        {
            NavCommand.Up => grid.MoveFocus(-grid.Columns),
            NavCommand.Down => grid.MoveFocus(grid.Columns),
            NavCommand.Left => grid.MoveFocus(-1),
            NavCommand.Right => grid.MoveFocus(1),
            NavCommand.PageUp => Jump(grid, grid.FocusIndex - grid.Columns * 4),
            NavCommand.PageDown => Jump(grid, grid.FocusIndex + grid.Columns * 4),
            NavCommand.First => Jump(grid, 0),
            NavCommand.Last => Jump(grid, grid.Count - 1),
            NavCommand.LetterNext => _screen == Screen.Games && _games is not null && Jump(grid, _games.NextLetter(grid.FocusIndex)),
            NavCommand.LetterPrevious => _screen == Screen.Games && _games is not null && Jump(grid, _games.PreviousLetter(grid.FocusIndex)),
            _ => false,
        };

        if (moved)
        {
            OnFocusChanged();
            return;
        }

        switch (command)
        {
            case NavCommand.Accept when _screen == Screen.Systems:
                EnterSystem(_systemsGrid.FocusIndex);
                break;
            case NavCommand.Accept when _screen == Screen.Games:
                StartLaunch();
                break;
            case NavCommand.Back when _screen == Screen.Games:
                LeaveGames();
                break;
            case NavCommand.Favourite when _screen == Screen.Games:
                ToggleFavourite();
                break;
            case NavCommand.Rescan when _screen == Screen.Systems:
                Rescan(null);
                break;
        }
    }

    private static bool Jump(ItemGrid grid, int index)
    {
        if (index < 0 || grid.Count == 0)
        {
            return false;
        }

        index = Math.Clamp(index, 0, grid.Count - 1);
        if (index == grid.FocusIndex)
        {
            return false;
        }

        grid.SetFocus(index);
        return true;
    }

    // ---- Focus and details ----------------------------------------------------------------------

    private void OnFocusChanged()
    {
        _overlay.ClearDetails();
        _focusedGame = null;
        if (_screen == Screen.Systems || _games is null)
        {
            _focusedIndex = _systemsGrid.FocusIndex;
            _focusKey = _focusedIndex;
            if (_focusedIndex >= 0)
            {
                var entry = _systems.Entries[_focusedIndex];
                _overlay.ShowHeading(entry.Name, entry.Subtitle);
            }
        }
        else
        {
            _focusedIndex = _gamesGrid.FocusIndex;
            if (_focusedIndex < 0)
            {
                _focusKey = -1;
                return;
            }

            var row = _games.Row(_focusedIndex);
            _focusKey = row.GameId;
            _overlay.ShowHeading(row.Title, _games.SystemName(_focusedIndex));
        }

        // Details wait until the focus rests, so holding a direction doesn't query every step.
        _detailsDue = _clock + DetailsDelay;
    }

    private void RequestDetails()
    {
        var key = _focusKey;
        if (key < 0)
        {
            return;
        }

        var library = _services.Library;
        var token = _shutdown.Token;
        if (_screen == Screen.Systems || _games is null)
        {
            var entry = _systems.Entries[(int)key];
            var config = _services.Config;
            _ = Task.Run(() =>
            {
                var details = entry.Virtual switch
                {
                    VirtualKind.Favourites => DetailsFormatter.Virtual(key, "The games you've marked as favourites. Press Y on a game to add it."),
                    VirtualKind.RecentlyPlayed => DetailsFormatter.Virtual(key, "The games you've played most recently, newest first."),
                    _ => DetailsFormatter.System(key, entry.System!, entry.Summary!, config, DateTimeOffset.Now),
                };
                _queue.Post(() =>
                {
                    if (_screen == Screen.Systems)
                    {
                        _overlay.ShowDetails(details, _focusKey);
                    }
                });
            }, token);
            return;
        }

        _ = Task.Run(async () =>
        {
            try
            {
                var game = await library.GetGameAsync(key, token).ConfigureAwait(false);
                if (game is null)
                {
                    return;
                }

                var stats = await library.GetPlayStatsAsync(game.Key, token).ConfigureAwait(false);
                var details = DetailsFormatter.Game(key, game, stats, DateTimeOffset.Now);
                _queue.Post(() =>
                {
                    if (_focusKey == key && _screen is Screen.Games or Screen.Launching)
                    {
                        _focusedGame = game;
                        _overlay.ShowDetails(details, _focusKey);
                    }
                });
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception e)
            {
                GD.PushError($"Details: {e.Message}");
            }
        }, token);
    }

    // ---- Systems → games ------------------------------------------------------------------------

    /// <summary>Enters a system's games grid (also used by --start-system and the scroll bench).</summary>
    public bool EnterSystem(string id, int? focusIndex = null)
    {
        for (var i = 0; i < _systems.Entries.Count; i++)
        {
            if (_systems.Entries[i].Id == id)
            {
                _systemsGrid.SetFocus(i);
                OnFocusChanged();
                EnterSystem(i, focusIndex);
                return true;
            }
        }

        return false;
    }

    private void EnterSystem(int index, int? focusIndex = null)
    {
        if (index < 0 || _screen != Screen.Systems)
        {
            return;
        }

        var entry = _systems.Entries[index];
        _screen = Screen.Entering;
        _entering = entry.Id;
        _systemsAnimation.Start(Shown, SystemsHidden, TransitionSeconds);
        _overlay.ClearDetails();

        var cached = entry.Virtual == VirtualKind.None ? _cache.Find(s => s.Id == entry.Id) : null;
        if (cached is not null)
        {
            _queue.Post(() => OnGamesLoaded(cached, focusIndex));
            return;
        }

        var library = _services.Library;
        var token = _shutdown.Token;
        var templateOf = _templateOf;
        var nameOf = _systemNameOf;
        var templateCount = _templateCount;
        _ = Task.Run(async () =>
        {
            try
            {
                GamesSource source = entry.Virtual switch
                {
                    VirtualKind.Favourites => GamesSource.ForVirtual(entry.Id, entry.Name,
                        await library.GetFavouritesAsync(token).ConfigureAwait(false), templateOf, nameOf, templateCount),
                    VirtualKind.RecentlyPlayed => GamesSource.ForVirtual(entry.Id, entry.Name,
                        await library.GetRecentlyPlayedAsync(RecentlyPlayedLimit, token).ConfigureAwait(false), templateOf, nameOf, templateCount),
                    _ => GamesSource.ForSystem(entry.Id, entry.Name,
                        await library.GetGamesAsync(entry.Id, token).ConfigureAwait(false), templateOf, templateCount),
                };
                _queue.Post(() => OnGamesLoaded(source, focusIndex));
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception e)
            {
                _queue.Post(() => OnGamesFailed(entry, e.Message));
            }
        }, token);
    }

    private void OnGamesLoaded(GamesSource source, int? focusIndex)
    {
        if (_screen != Screen.Entering || _entering != source.Id)
        {
            return;
        }

        if (!source.Id.Equals(FavouritesId, StringComparison.Ordinal) && !source.Id.Equals(RecentlyPlayedId, StringComparison.Ordinal))
        {
            _cache.Remove(source);
            _cache.Insert(0, source);
            if (_cache.Count > CachedLists)
            {
                _cache.RemoveAt(_cache.Count - 1);
            }
        }

        _games = source;
        var focus = focusIndex ?? (_lastGame.TryGetValue(source.Id, out var gameId) ? Math.Max(0, source.IndexOf(gameId)) : 0);
        _gamesGrid.Bind(source, focus);
        _gamesAnimation.Start(GamesHidden, Shown, TransitionSeconds);
        _screen = Screen.Games;
        _overlay.SetHints(GamesHints);
        _overlay.SetStatus(source.Count == 0 ? EmptyMessage(source.Id) : null);
        OnFocusChanged();
    }

    private void OnGamesFailed(SystemEntry entry, string message)
    {
        GD.PushError($"Couldn't load {entry.Name}'s games: {message}");
        _screen = Screen.Systems;
        _entering = null;
        _systemsAnimation.Start(SystemsHidden, Shown, TransitionSeconds);
        _overlay.SetStatus($"Couldn't load {entry.Name}'s games. {message}");
    }

    private string EmptyMessage(string id)
    {
        if (id == FavouritesId)
        {
            return "No favourites yet. Press Y on a game to add it.";
        }

        if (id == RecentlyPlayedId)
        {
            return "Nothing played yet.";
        }

        var system = _services.Config.FindSystem(id);
        var folder = system is null || system.RomDirs.Count == 0 ? "its ROM folder" : system.RomDirs[0];
        return $"No games found in {folder}. Add some, then press View or F5 on the systems screen to rescan.";
    }

    private void LeaveGames()
    {
        if (_games is not null && _gamesGrid.FocusIndex >= 0 && _gamesGrid.FocusIndex < _games.Count)
        {
            _lastGame[_games.Id] = _games.Row(_gamesGrid.FocusIndex).GameId;
        }

        _screen = Screen.Systems;
        _games = null;
        _entering = null;
        _gamesAnimation.Start(Shown, GamesHidden, TransitionSeconds);
        _systemsAnimation.Start(SystemsHidden, Shown, TransitionSeconds);
        _overlay.SetStatus(null);
        _overlay.SetHints(SystemsHints);
        OnFocusChanged();
    }

    // ---- Favourites and rescans -------------------------------------------------------------------

    private void ToggleFavourite()
    {
        if (_games is null || _focusedIndex < 0)
        {
            return;
        }

        var key = _focusKey;
        var known = _focusedGame;
        var library = _services.Library;
        var token = _shutdown.Token;
        _ = Task.Run(async () =>
        {
            try
            {
                var game = known ?? await library.GetGameAsync(key, token).ConfigureAwait(false);
                if (game is null)
                {
                    return;
                }

                await library.SetFavouriteAsync(game.Key, !game.IsFavourite, token).ConfigureAwait(false);
                _queue.Post(() =>
                {
                    if (_focusKey == key)
                    {
                        _detailsDue = _clock;
                    }
                });
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception e)
            {
                GD.PushError($"Favourite: {e.Message}");
            }
        }, token);
    }

    /// <summary>Rescans the given systems (null: all), then refreshes the systems grid. Once at a time.</summary>
    public void Rescan(IReadOnlyList<string>? systemIds)
    {
        if (_scanning)
        {
            return;
        }

        _scanning = true;
        _overlay.SetStatus("Scanning your ROM folders…");
        var library = _services.Library;
        var token = _shutdown.Token;
        _ = Task.Run(async () =>
        {
            string? status = null;
            try
            {
                var added = 0;
                if (systemIds is null)
                {
                    added = (await library.RescanAsync(null, null, token).ConfigureAwait(false)).Added;
                }
                else
                {
                    foreach (var id in systemIds)
                    {
                        added += (await library.RescanAsync(id, null, token).ConfigureAwait(false)).Added;
                    }
                }

                var systems = await library.GetSystemsAsync(token).ConfigureAwait(false);
                GD.Print($"Scan: {added} game(s) added.");
                _queue.Post(() => OnRescanned(systems, null));
                if (BakeAfterScans)
                {
                    await BakeAsync(token).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception e)
            {
                status = $"The scan failed: {e.Message}";
                _queue.Post(() => OnRescanned(null, status));
            }
        }, token);
    }

    /// <summary>Bake missing cover derivatives after each scan (off in benches, which measure a library as it is).</summary>
    public bool BakeAfterScans { get; set; }

    private int _baking;

    /// <summary>
    /// Bakes every cover that has no derivative yet, the user's own art included (M4), on the derivative service's
    /// below-normal thread. Covers baked now show the next time their system is entered.
    /// </summary>
    public void BakeDerivatives()
    {
        var token = _shutdown.Token;
        _ = Task.Run(() => BakeAsync(token), token);
    }

    private async Task BakeAsync(CancellationToken token)
    {
        if (Interlocked.Exchange(ref _baking, 1) == 1)
        {
            return;
        }

        try
        {
            var summary = await _services.Derivatives.BakeMissingAsync(null, token).ConfigureAwait(false);
            if (summary.Baked + summary.Failed + summary.Pruned > 0)
            {
                GD.Print(string.Create(CultureInfo.InvariantCulture,
                    $"Derivatives: {summary.Baked} baked, {summary.Failed} failed, {summary.Pruned} stale removed, of {summary.Covers} covers ({summary.Elapsed.TotalSeconds:0.0} s)"));
            }

            if (summary.Baked > 0)
            {
                _queue.Post(() => _cache.Clear());
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception e)
        {
            GD.PushWarning($"Derivatives: baking failed: {e.Message}");
        }
        finally
        {
            Volatile.Write(ref _baking, 0);
        }
    }

    private void OnRescanned(IReadOnlyList<SystemSummary>? systems, string? error)
    {
        _scanning = false;
        _overlay.SetStatus(error);
        if (systems is null)
        {
            return;
        }

        _services.Systems = systems;
        _cache.Clear();
        var focus = _systemsGrid.FocusIndex;
        _systems = new SystemsSource(BuildEntries(systems), _systemsTemplate);
        if (_screen == Screen.Systems)
        {
            _systemsGrid.Bind(_systems, focus);
            OnFocusChanged();
        }
    }

    // ---- Launching ------------------------------------------------------------------------------

    private void StartLaunch()
    {
        if (_games is null || _focusedIndex < 0 || Launcher is null)
        {
            return;
        }

        _screen = Screen.Launching;
        _launchStartedAt = _clock;
        _gamesGrid.PlayLaunch();
        var key = _focusKey;
        if (_focusedGame is { GameId: var id } game && id == key)
        {
            _launchGame = game;
            return;
        }

        var library = _services.Library;
        var token = _shutdown.Token;
        _ = Task.Run(async () =>
        {
            try
            {
                var found = await library.GetGameAsync(key, token).ConfigureAwait(false);
                _queue.Post(() =>
                {
                    if (found is null)
                    {
                        FinishLaunch("That game isn't in the library any more. Rescan to refresh it.");
                    }
                    else
                    {
                        _launchGame = found;
                    }
                });
            }
            catch (OperationCanceledException)
            {
            }
        }, token);
    }

    /// <summary>Main thread: the launch controller says the game has ended (or never started).</summary>
    public void FinishLaunch(string? failure)
    {
        _gamesGrid.StopLaunch();
        _launchGame = null;
        if (_screen == Screen.Launching)
        {
            _screen = Screen.Games;
        }

        if (failure is not null)
        {
            GD.PrintErr($"Launch failed: {failure}");
        }

        // Play statistics changed, and Recently played with them.
        _detailsDue = _clock;
    }

    /// <summary>A game is starting: free the cover textures for the emulator (A1 Starting).</summary>
    public void OnGameModeEntered()
    {
        _gamesGrid.DisableTextures();
        Streamer?.Evict();
    }

    /// <summary>Back in the launcher: recreate the cover array and re-request what's on screen.</summary>
    public void OnGameModeLeft()
    {
        Streamer?.CreateArray();
        _gamesGrid.EnableTextures();
    }

    // ---- Animation ------------------------------------------------------------------------------

    private void Animate(float dt)
    {
        if (_systemsAnimation.Update(dt, out var systemsPose))
        {
            Apply(_systemsGrid, systemsPose);
        }

        if (_gamesAnimation.Update(dt, out var gamesPose))
        {
            Apply(_gamesGrid, gamesPose);
            if (!_gamesAnimation.Active && _screen == Screen.Systems)
            {
                _gamesGrid.UnbindAll();
            }
        }

        // The overlay dips while a transition swaps its text.
        var t = Math.Max(_systemsAnimation.Progress, _gamesAnimation.Progress);
        _overlay.Opacity = _systemsAnimation.Active || _gamesAnimation.Active ? Math.Abs(2 * t - 1) * 0.7f + 0.3f : 1;
    }

    private static void Apply(ItemGrid grid, GridPose pose)
    {
        grid.Fade = pose.Fade;
        grid.Zoom = pose.Zoom;
        grid.Offset = new Vector3(0, 0, pose.Depth);
    }

    // ---- Entries --------------------------------------------------------------------------------

    private List<SystemEntry> BuildEntries(IReadOnlyList<SystemSummary> summaries)
    {
        var entries = new List<SystemEntry>
        {
            new(FavouritesId, "Favourites", "The games you've marked", Palette.Favourites, null, null, VirtualKind.Favourites),
            new(RecentlyPlayedId, "Recently played", "Newest first", Palette.RecentlyPlayed, null, null, VirtualKind.RecentlyPlayed),
        };
        foreach (var summary in summaries)
        {
            if (_services.Config.FindSystem(summary.SystemId) is { } system)
            {
                entries.Add(new SystemEntry(system.Id, system.Name, DetailsFormatter.SystemSubtitle(system, summary.GameCount),
                    Palette.ForSystem(system.Id), system, summary, VirtualKind.None));
            }
        }

        return entries;
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
