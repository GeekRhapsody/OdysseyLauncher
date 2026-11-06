using System;
using System.Collections.Generic;
using System.Globalization;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Diagnostics;
using Launcher.App.Grid;
using Launcher.App.Launching;
using Launcher.App.Models;
using Launcher.App.Navigation;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using OverlayPalette = Launcher.Core.Theming.OverlayPalette;

namespace Launcher.App.Screens;

/// <summary>
/// The screens (A1 Screens): Systems → Games → Launching, and back, with animated transitions between the two
/// grids (each laid out as settings.toml's <c>[display]</c> says: a grid, a carousel, one system at a time, a list
/// of games with the focused one's model beside it, a coverflow, or a showcase), each system's look cross-faded in (A6), focus memory per system, the focused item's title in the
/// overlay (a system's and a game's details are on their details screens, Y), favourites, rescans, the power menu, launching, and themes (M6):
/// switching one at run time, per-game models, and
/// rebinding a game's media when it changes. Library calls run on the thread pool and their results come back
/// through the <see cref="MainThreadQueue"/>.
/// </summary>
public sealed partial class Navigator : Node
{
    public const string FavouritesId = "favourites";
    public const string RecentlyPlayedId = "recently_played";
    public const string AllGamesId = "all_games";
    public const int RecentlyPlayedLimit = 60;
    private const double DetailsDelay = 0.12;

    /// <summary>How long a system's card is focused before its wallpaper is fetched ahead (A6 Background), in seconds.</summary>
    private const double WallpaperDelay = 0.15;
    private const float TransitionSeconds = 0.45f;
    private const double StatusSeconds = 2.5;
    private const int CachedLists = 3;

    private static readonly Hint[] SystemsHints =
    [
        new("Open", Prompt.Accept), new("Options", Prompt.Alternate), new("Details", Prompt.Secondary), new("Power", Prompt.Power),
        new("Settings", Prompt.Menu),
    ];

    private static readonly Hint[] GamesHints =
    [
        new("Play", Prompt.Accept), new("Back", Prompt.Back), new("Options", Prompt.Alternate), new("Details", Prompt.Secondary),
        new("Favourite", Prompt.Favourite), new("Zoom", Prompt.Inspect), new("Page", Prompt.Pages), new("Letter", Prompt.Letters),
    ];
    private const double TitlesDelay = 0.4;

    /// <summary>How long after a theme is applied its predecessor's leftovers are collected, in seconds (2026-10-16).</summary>
    private const double ThemeCollectDelay = 1;

    /// <summary>Frames drawn by hand once a game's textures are freed, so the renderer lets go of them (2026-10-28).</summary>
    private const int ReleaseDraws = 3;

    /// <summary>How long after a game starts the collection and those draws run, in seconds (2026-10-28).</summary>
    private const double CollectAfterGameSeconds = 0.3;

    private static readonly GridPose Shown = new(0, 1, 0);
    private static readonly GridPose SystemsHidden = new(1, 1.12f, 0.7f);
    private static readonly GridPose GamesHidden = new(1, 0.82f, -1.6f);

    private readonly AppServices _services;
    private readonly MainThreadQueue _queue;
    private readonly ItemGrid _systemsGrid;
    private readonly ItemGrid _gamesGrid;
    private readonly InfoOverlay _overlay;
    private readonly LookStage _stage;
    private readonly ModelLoader _loader;
    private readonly NavInput _input = new();
    private readonly Func<string, string> _systemNameOf;
    private readonly Dictionary<string, long> _lastGame = new(StringComparer.Ordinal);
    private readonly List<GamesSource> _cache = [];
    private readonly List<(GamesSource Source, int Model, string Path)> _perGameLoading = [];
    private readonly CancellationTokenSource _shutdown = new();

    private ThemeRuntime _theme;
    private ThemeRuntime? _pendingTheme;
    private bool _switchingTheme;
    private double _themeRequestedAt;
    private double _themeCollectDue = -1;
    private SystemsSource _systems = null!;
    private GamesSource? _games;
    private Screen _screen = Screen.Systems;
    private GridAnimation _systemsAnimation;
    private GridAnimation _gamesAnimation;
    private string? _entering;
    private int _focusedIndex = -1;
    private long _focusKey = -1;
    private double _detailsDue = -1;
    private double _wallpaperDue = -1;
    private double _statusClearAt = -1;
    private double _clock;
    private GameDetails? _focusedGame;
    private double _launchStartedAt;
    private double _launchSeconds;
    private GameDetails? _launchGame;

    /// <summary>The pad the game being launched was chosen with, or -1 (player 1 when its controllers are set up).</summary>
    private int _launchPad = -1;
    private double _titlesDue = -1;
    private readonly HashSet<string> _titleSystems = new(StringComparer.Ordinal);

    public Navigator(AppServices services, MainThreadQueue queue, ItemGrid systemsGrid, ItemGrid gamesGrid, InfoOverlay overlay, LookStage stage, ModelLoader loader, ThemeRuntime theme)
    {
        Name = "Navigator";
        _services = services;
        _queue = queue;
        _systemsGrid = systemsGrid;
        _gamesGrid = gamesGrid;
        _overlay = overlay;
        _stage = stage;
        _loader = loader;
        _theme = theme;

        // The overlay's colours before it first shows: the theme's menu colours (A6 Menus), else the launcher's own.
        overlay.Use(OverlayPalette.For(theme.Plan.Active.Menu));
        var systemName = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var system in services.Config.Systems)
        {
            systemName[system.Id] = system.Name;
        }

        _systemNameOf = id => systemName.TryGetValue(id, out var n) ? n : id;
        services.Library.MediaChanged += OnLibraryMediaChanged;
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

    /// <summary>Rescans and scrapes with progress (M7); the navigator's rescans go through it too.</summary>
    public Settings.LibraryJobs? Jobs
    {
        get => _jobs;
        set
        {
            if (_jobs is not null)
            {
                _jobs.ScanCompleted -= OnRescanned;
            }

            _jobs = value;
            if (value is not null)
            {
                value.ScanCompleted += OnRescanned;
            }
        }
    }

    private Settings.LibraryJobs? _jobs;

    /// <summary>True while another screen (the settings) has the input: the grids ignore it, and wait for it to be let go.</summary>
    public Func<bool>? InputSuspended { get; set; }

    /// <summary>Menu, or Back on the systems screen: the settings screen should open (M7).</summary>
    public event Action? SettingsRequested;

    /// <summary>View (Select) or P in either grid: the power menu should open.</summary>
    public event Action? PowerRequested;

    /// <summary>X on a system: its options panel should open (M7). The system's id.</summary>
    public event Action<string>? SystemOptionsRequested;

    /// <summary>X on a game: its options panel should open (M7). The game's id.</summary>
    public event Action<long>? GameOptionsRequested;

    /// <summary>Y on a game: its details screen should open (every field of its metadata, and its images and videos). The game's id.</summary>
    public event Action<long>? GameDetailsRequested;

    /// <summary>
    /// Y on a system, Favourites, Recently played or All games: its details screen should open (its description, every field, and
    /// its card's model). The card.
    /// </summary>
    public event Action<SystemEntry>? SystemDetailsRequested;

    /// <summary>The theme the grids show (the options panels say which model each system uses).</summary>
    public ThemeRuntime Theme => _theme;

    /// <summary><c>--layout</c>: this run's layouts instead of settings.toml's, or null.</summary>
    public LayoutOverride? LayoutOverride { get; set; }

    /// <summary>The display settings the grids are laid out by: settings.toml's, with <c>--layout</c> over them.</summary>
    private DisplaySettings Display =>
        LayoutOverride?.ApplyTo(_services.Config.Settings.Display) ?? _services.Config.Settings.Display;

    private GridLayout SystemsLayout() => GridLayout.Systems(Display);

    /// <summary>A list's layout: the games layout, with the system's own grid size (the virtual lists use settings.toml's).</summary>
    private GridLayout GamesLayout(string id) => GridLayout.Games(Display, _services.Config.FindSystem(id));

    /// <summary>
    /// A system's games' order: its own <c>games_sort</c>, else settings.toml's, which All games follows too (Favourites
    /// and Recently played have their own).
    /// </summary>
    private GamesOrdering GamesSort(string id) => Display.GamesSortFor(_services.Config.FindSystem(id));

    /// <summary>The media streamer, for evicting textures while a game runs and for a theme's layout.</summary>
    public TextureStreamer? Streamer { get; set; }

    /// <summary>The navigation sounds, from the warm-up; null until then.</summary>
    public UiSounds? Sounds { get; set; }

    /// <summary>The systems grid's streamer, for its cards' logos (A6 <c>logos/</c>); null with <c>--no-textures</c>.</summary>
    public TextureStreamer? CardStreamer { get; set; }

    /// <summary>True once a system's games are bound and its transition has finished.</summary>
    public bool InGames => _screen == Screen.Games && !_gamesAnimation.Active;

    public ItemGrid GamesGrid => _gamesGrid;

    public string? CurrentSystem => _games?.Id;

    /// <summary>The active theme's id.</summary>
    public string ThemeId => _theme.Plan.Active.Id;

    /// <summary>True while a theme switch loads.</summary>
    public bool SwitchingTheme => _switchingTheme;

    /// <summary>Per-game models of the shown list still loading (the scroll bench waits for them).</summary>
    public int PerGameLoading => _perGameLoading.Count;

    /// <summary>Where the focus is, for the <c>--nav-script</c> log.</summary>
    public string Describe()
    {
        var grid = _screen == Screen.Systems ? _systemsGrid : _gamesGrid;
        var title = _screen == Screen.Systems
            ? grid.FocusIndex >= 0 ? _systems.Entries[grid.FocusIndex].Name : "-"
            : _games is not null && grid.FocusIndex >= 0 ? _games.Row(grid.FocusIndex).Title : "-";
        return $"{_screen}, {(_screen == Screen.Systems ? "systems" : _games?.Id ?? "?")}, item {grid.FocusIndex}: {title}{(grid.Inspecting ? ", inspected" : "")} (theme {ThemeId})";
    }

    /// <summary>Builds the systems grid from the boot query. Main thread.</summary>
    public void ShowSystems()
    {
        _systems = new SystemsSource(BuildEntries(_services.Systems), _systemsGrid.Templates.Count);
        _systemsGrid.Layout = SystemsLayout();
        _systemsGrid.Bind(_systems, FirstRealSystem());
        DebugHooks.Layout = $"{_systemsGrid.Layout}/{GridLayout.Games(Display, null)}";
        _systemsGrid.Fade = 0;
        _gamesGrid.Fade = 1;
        _overlay.SetHints(SystemsHints);
        OnFocusChanged();
    }

    public override void _ExitTree()
    {
        Jobs = null;
        _services.Library.MediaChanged -= OnLibraryMediaChanged;
        _shutdown.Cancel();
    }

    /// <summary>Main thread, once per frame, before the grids tick (called by Main, so input acts in the same frame).</summary>
    public void Update(double delta)
    {
        _clock += delta;
        var dt = (float)delta;
        HandleInput(delta);
        Animate(dt);
        if (_stage.Tick(dt))
        {
            var backdrop = _stage.Backdrop;
            _systemsGrid.SetBackground(backdrop);
            _gamesGrid.SetBackground(backdrop);
        }

        if (_wallpaperDue >= 0 && _clock >= _wallpaperDue)
        {
            _wallpaperDue = -1;
            PrefetchWallpaper();
        }

        if (_detailsDue >= 0 && _clock >= _detailsDue)
        {
            _detailsDue = -1;
            RequestDetails();
        }

        if (_statusClearAt >= 0 && _clock >= _statusClearAt)
        {
            _statusClearAt = -1;
            _overlay.SetStatus(null);
        }

        if (_pendingTheme is { } pending)
        {
            PollTheme(pending);
        }

        if (_theme.CardsPending && _theme.PollCards())
        {
            ApplyCards();
        }

        if (_overlay.List.Visible)
        {
            _overlay.List.Update(_gamesGrid.ScrollPosition, _gamesGrid.FocusIndex);
        }

        // An inspected game stands in front of the titles (and their highlight) and the labels, not behind them.
        _overlay.TitlesBehind = (_overlay.List.Visible || _overlay.GameLabels.Visible || _overlay.Showcase.Visible) && _gamesGrid.InspectShown;

        if (_titlesDue >= 0 && _clock >= _titlesDue)
        {
            _titlesDue = -1;
            RefreshTitles();
        }

        if (_themeCollectDue >= 0 && _clock >= _themeCollectDue)
        {
            // 2026-10-16: every texture or array the old theme's materials were given went through a Variant, whose
            // disposer holds it until its finaliser runs; the app's SustainedLowLatency mode can put that off for good,
            // which kept a theme switched from in video memory. By now the nodes that drew them are freed and the new
            // theme's arrays are installed, so a background full collection lets them all go.
            _themeCollectDue = -1;
            GC.Collect(2, GCCollectionMode.Forced, blocking: false);
        }

        if (_perGameLoading.Count > 0 && _theme.PollLoads())
        {
            FinishPerGameModels();
        }

        if (_screen == Screen.Launching && _launchGame is not null && _clock - _launchStartedAt >= _launchSeconds)
        {
            var game = _launchGame;
            _launchGame = null;
            if (Launcher is null)
            {
                FinishLaunch("The launcher isn't ready yet. Try again in a moment.");
            }
            else
            {
                Launcher.Launch(game, _launchPad);
            }
        }
    }

    // ---- Input ----------------------------------------------------------------------------------

    private void HandleInput(double delta)
    {
        var blocked = (Launcher?.IsInputBlocked ?? false) || (InputSuspended?.Invoke() ?? false);
        var command = _input.Poll(delta, blocked || _screen is Screen.Entering or Screen.Launching);
        if (command != NavCommand.None)
        {
            Run(command);
        }

        // The right stick turns the focused system or game, in either grid, until the focus moves.
        if (!blocked && _screen is Screen.Systems or Screen.Games && NavInput.ReadTurn() is var turn && turn != Vector2.Zero)
        {
            (_screen == Screen.Systems ? _systemsGrid : _gamesGrid).Turn(turn, (float)delta);
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

        // A page is four rows of a grid, a carousel's width, a coverflow's side, or the titles a list shows.
        var page = grid == _gamesGrid && _overlay.List.Visible ? _overlay.List.RowsShown : grid.PageStep;
        var moved = command switch
        {
            NavCommand.Up => grid.Move(0, -1),
            NavCommand.Down => grid.Move(0, 1),
            NavCommand.Left => grid.Move(-1, 0),
            NavCommand.Right => grid.Move(1, 0),
            NavCommand.PageUp => Jump(grid, grid.FocusIndex - page),
            NavCommand.PageDown => Jump(grid, grid.FocusIndex + page),
            NavCommand.First => Jump(grid, 0),
            NavCommand.Last => Jump(grid, grid.Count - 1),
            NavCommand.LetterNext => _screen == Screen.Games && _games is not null && Jump(grid, _games.NextLetter(grid.FocusIndex)),
            NavCommand.LetterPrevious => _screen == Screen.Games && _games is not null && Jump(grid, _games.PreviousLetter(grid.FocusIndex)),
            _ => false,
        };

        if (moved)
        {
            Sounds?.Tock();
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
                // B puts an inspected game back first; the next B leaves.
                if (!_gamesGrid.EndInspect())
                {
                    LeaveGames();
                }

                break;
            case NavCommand.Inspect when _screen == Screen.Games:
                _gamesGrid.ToggleInspect();
                break;
            case NavCommand.Secondary when _screen == Screen.Systems:
                if (_systemsGrid.FocusIndex >= 0 && _systemsGrid.FocusIndex < _systems.Entries.Count)
                {
                    SystemDetailsRequested?.Invoke(_systems.Entries[_systemsGrid.FocusIndex]);
                }

                break;
            case NavCommand.Secondary when _screen == Screen.Games:
                if (_games is not null && _gamesGrid.FocusIndex >= 0 && _gamesGrid.FocusIndex < _games.Count)
                {
                    GameDetailsRequested?.Invoke(_games.Row(_gamesGrid.FocusIndex).GameId);
                }

                break;
            case NavCommand.Favourite when _screen == Screen.Games:
                ToggleFavourite();
                break;
            case NavCommand.Rescan when _screen == Screen.Systems:
                Rescan(null, RescanMedia.SystemsWithNewGames);
                break;
            case NavCommand.RescanMedia when _screen == Screen.Systems:
                Rescan(null, RescanMedia.All);
                break;
            case NavCommand.NextTheme when _screen == Screen.Systems:
                SwitchTheme(null);
                break;
            case NavCommand.Menu:
            case NavCommand.Back when _screen == Screen.Systems:
                SettingsRequested?.Invoke();
                break;
            case NavCommand.Alternate:
                RequestOptions();
                break;
            case NavCommand.Power:
                PowerRequested?.Invoke();
                break;
        }
    }

    /// <summary>X: the focused system's or game's options. Favourites, Recently played and All games have none.</summary>
    private void RequestOptions()
    {
        if (_screen == Screen.Systems)
        {
            if (_systemsGrid.FocusIndex >= 0 && _systems.Entries[_systemsGrid.FocusIndex] is { Virtual: VirtualKind.None } entry)
            {
                SystemOptionsRequested?.Invoke(entry.Id);
            }
            else
            {
                ShowStatus("Favourites, Recently played and All games have no options. Press X on a system or a game.");
            }

            return;
        }

        if (_games is not null && _gamesGrid.FocusIndex >= 0 && _gamesGrid.FocusIndex < _games.Count)
        {
            GameOptionsRequested?.Invoke(_games.Row(_gamesGrid.FocusIndex).GameId);
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
            // A system's details are on its details screen (Y); the overlay has its name and subtitle, and nothing to read.
            _focusedIndex = _systemsGrid.FocusIndex;
            _focusKey = _focusedIndex;
            if (_focusedIndex >= 0)
            {
                var entry = _systems.Entries[_focusedIndex];
                _overlay.ShowHeading(entry.Name, entry.Subtitle);
            }

            _detailsDue = -1;
            _wallpaperDue = _clock + WallpaperDelay;
            return;
        }

        _focusedIndex = _gamesGrid.FocusIndex;
        if (_focusedIndex < 0)
        {
            _focusKey = -1;
            return;
        }

        var row = _games.Row(_focusedIndex);
        _focusKey = row.GameId;
        _overlay.ShowHeading(row.Title, _games.SystemName(_focusedIndex));

        // Details wait until the focus rests, so holding a direction doesn't query every step.
        _detailsDue = _clock + DetailsDelay;
    }

    /// <summary>The focused system's wallpaper starts loading, so entering it shows it at once (A6 Background).</summary>
    private void PrefetchWallpaper()
    {
        if (_screen == Screen.Systems && _focusedIndex >= 0 && _focusedIndex < _systems.Entries.Count
            && _systems.Entries[_focusedIndex] is { Virtual: VirtualKind.None } entry)
        {
            _stage.Prefetch(_theme.LookFor(entry.Id));
        }
    }

    /// <summary>The focused game's details: whether it's a favourite, and the game to launch.</summary>
    private void RequestDetails()
    {
        var key = _focusKey;
        if (key < 0 || _screen == Screen.Systems || _games is null)
        {
            return;
        }

        var library = _services.Library;
        var token = _shutdown.Token;
        var showcase = _overlay.Showcase.Visible;
        var artDecoder = showcase && !_overlay.Showcase.HasArt(key) ? ShowcaseDecoder() : null;
        _ = Task.Run(async () =>
        {
            try
            {
                var game = await library.GetGameAsync(key, token).ConfigureAwait(false);
                if (game is null)
                {
                    return;
                }

                // A game's metadata is on its details screen (Y); the overlay keeps its title and whether it's a favourite.
                var details = new OverlayDetails(key, game.IsFavourite);
                var shown = showcase ? new ShowcaseDetails(key, game.Metadata?.Description ?? string.Empty, DetailsFormatter.ShowcaseFields(game.Metadata)) : null;
                _queue.Post(() =>
                {
                    if (_focusKey == key && _screen is Screen.Games or Screen.Launching)
                    {
                        _focusedGame = game;
                        _overlay.ShowDetails(details, _focusKey);
                        if (shown is not null)
                        {
                            _overlay.Showcase.ShowDetails(shown, _focusKey);
                        }
                    }
                });

                if (artDecoder is not null)
                {
                    await LoadShowcaseArtAsync(key, artDecoder, token).ConfigureAwait(false);
                }
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

    /// <summary>The focused item's details are read again now (its favourite changed on its details screen).</summary>
    public void RefreshDetails()
    {
        if (_focusKey >= 0)
        {
            _detailsDue = _clock;
        }
    }

    // ---- Systems → games ------------------------------------------------------------------------

    /// <summary>
    /// Enters a system's games grid (also used by --start-system and the scroll bench); a grouped system's is its
    /// group's card (A5 Grouped systems).
    /// </summary>
    public bool EnterSystem(string id, int? focusIndex = null)
    {
        for (var i = 0; i < _systems.Entries.Count; i++)
        {
            if (_systems.Entries[i].Id == id || (_systems.Entries[i].Members is { } members && IndexOf(members, id) >= 0))
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
        Sounds?.Whoosh();
        _overlay.ClearDetails();
        _stage.Show(_theme.LookFor(entry.Virtual == VirtualKind.None ? entry.Id : null), _theme.TransitionSeconds);

        var ordering = GamesSort(entry.Id);
        var cached = entry.Sorted ? _cache.Find(s => s.Id == entry.Id && s.Ordering == ordering) : null;
        if (cached is not null)
        {
            var theme = _theme;
            _queue.Post(() => OnGamesLoaded(cached, focusIndex, null, theme));
            return;
        }

        LoadGames(entry, focusIndex, null);
    }

    /// <summary>A list and its media for the theme's slots, on the thread pool; then <see cref="OnGamesLoaded"/>.</summary>
    private void LoadGames(SystemEntry entry, int? focusIndex, long? focusGame)
    {
        var library = _services.Library;
        var token = _shutdown.Token;
        var theme = _theme;
        var kinds = theme.Layout.MediaKinds;
        var nameOf = _systemNameOf;
        var ordering = GamesSort(entry.Id);
        _ = Task.Run(async () =>
        {
            try
            {
                GamesSource source;
                if (entry.Members is { } members)
                {
                    // A group's card (A5 Grouped systems): its systems' games in one list, each in its own system's template.
                    var rows = await library.GetGamesAsync(members, ordering, token).ConfigureAwait(false);
                    var media = await library.GetGameMediaAsync(members, kinds, token).ConfigureAwait(false);
                    source = GamesSource.ForVirtual(entry.Id, entry.Name, rows, media, kinds, theme.ColourOf, nameOf, ordering, members);
                }
                else if (entry.Virtual == VirtualKind.None)
                {
                    var list = await library.GetGamesAsync(entry.Id, ordering, token).ConfigureAwait(false);
                    var media = await library.GetGameMediaAsync(entry.Id, kinds, token).ConfigureAwait(false);
                    source = GamesSource.ForSystem(entry.Id, entry.Name, list, media, kinds, theme.ColourOf, ordering);
                }
                else
                {
                    var rows = await VirtualGamesAsync(library, entry.Virtual, ordering, token).ConfigureAwait(false);
                    IReadOnlyList<GameMediaRow> media;
                    if (entry.Virtual == VirtualKind.AllGames)
                    {
                        media = await library.GetAllGameMediaAsync(kinds, token).ConfigureAwait(false);
                    }
                    else
                    {
                        var ids = new long[rows.Count];
                        for (var i = 0; i < ids.Length; i++)
                        {
                            ids[i] = rows[i].Game.GameId;
                        }

                        media = await library.GetGameMediaAsync(ids, kinds, token).ConfigureAwait(false);
                    }

                    source = GamesSource.ForVirtual(entry.Id, entry.Name, rows, media, kinds, theme.ColourOf, nameOf,
                        entry.Sorted ? ordering : default);
                }

                _queue.Post(() => OnGamesLoaded(source, focusIndex, focusGame, theme));
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

    /// <param name="focusGame">Set when the shown list was loaded again (a theme switch): keep the focus on this game.</param>
    private void OnGamesLoaded(GamesSource source, int? focusIndex, long? focusGame, ThemeRuntime theme)
    {
        if (theme != _theme)
        {
            // Loaded for a theme that has since been switched: the switch loads it again.
            return;
        }

        var reloading = focusGame is not null && _games is not null && _games.Id == source.Id && _screen is Screen.Games or Screen.Launching;
        if (!reloading && (_screen != Screen.Entering || _entering != source.Id))
        {
            return;
        }

        if (source.Id is not (FavouritesId or RecentlyPlayedId))
        {
            _cache.Remove(source);
            _cache.Insert(0, source);
            if (_cache.Count > CachedLists)
            {
                _cache.RemoveAt(_cache.Count - 1);
            }
        }

        _games = source;
        source.BindTemplates(_theme.GameTemplateOf, _theme.ChosenTemplateOf, _gamesGrid.Templates.Count);
        ReleasePerGameModels();
        RequestPerGameModels(source);
        var focus = focusIndex
            ?? (focusGame is { } game ? Math.Max(0, source.IndexOf(game))
            : _lastGame.TryGetValue(source.Id, out var gameId) ? Math.Max(0, source.IndexOf(gameId)) : 0);
        BindGames(source, Math.Min(focus, Math.Max(0, source.Count - 1)));
        if (reloading)
        {
            if (source.Count == 0)
            {
                _overlay.SetStatus(EmptyMessage(source.Id));
            }

            OnFocusChanged();
            return;
        }

        _gamesAnimation.Start(GamesHidden, Shown, TransitionSeconds);
        _screen = Screen.Games;
        _overlay.SetHints(GamesHints);
        _overlay.SetStatus(source.Count == 0 ? EmptyMessage(source.Id) : null);
        OnFocusChanged();
    }

    private void OnGamesFailed(SystemEntry entry, string message)
    {
        GD.PushError($"Couldn't load {entry.Name}'s games: {message}");
        if (_screen != Screen.Entering)
        {
            return;
        }

        _screen = Screen.Systems;
        _entering = null;
        _systemsAnimation.Start(SystemsHidden, Shown, TransitionSeconds);
        _stage.Show(_theme.LookFor(null), _theme.TransitionSeconds);
        _overlay.SetStatus($"Couldn't load {entry.Name}'s games. {message}");
    }

    private string EmptyMessage(string id)
    {
        if (id == FavouritesId)
        {
            return "No favourites yet. Press L3 (or F) on a game to add it.";
        }

        if (id == RecentlyPlayedId)
        {
            return "Nothing played yet.";
        }

        if (id == AllGamesId)
        {
            return "No games yet. Set your ROM folders in the settings (Menu), then rescan.";
        }

        var system = _services.Config.FindSystem(id);
        var folder = system is null || system.RomDirs.Count == 0 ? "its ROM folder" : system.RomDirs[0];
        return $"No games found in {folder}. Add some, then rescan from the settings (Menu), or press F5 on the systems screen.";
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
        _overlay.List.Bind(null, false);
        _overlay.ShowShowcase(false);
        _perGameLoading.Clear();
        _gamesAnimation.Start(Shown, GamesHidden, TransitionSeconds);
        _systemsAnimation.Start(SystemsHidden, Shown, TransitionSeconds);
        _stage.Show(_theme.LookFor(null), _theme.TransitionSeconds);
        _overlay.SetStatus(null);
        _overlay.SetHints(SystemsHints);
        OnFocusChanged();
    }

    /// <summary>Binds a list to the games grid in its layout, with the list of titles beside it in the list layout.</summary>
    private void BindGames(GamesSource source, int focus)
    {
        var layout = GamesLayout(source.Id);
        _gamesGrid.Layout = layout;
        _gamesGrid.Bind(source, focus);
        _overlay.List.Bind(layout.Shape == GridShape.List ? source : null, source.SystemIds.Count > 1 || source.Id is FavouritesId or RecentlyPlayedId or AllGamesId);
        _overlay.ShowShowcase(layout.Shape == GridShape.Showcase);
        DebugHooks.Layout = $"{SystemsLayout()}/{layout}";
    }

    // ---- Per-game models (A7) ----------------------------------------------------------------------

    /// <summary>
    /// Before a list is bound: the grid forgets the previous list's per-game models, and the loader drops those no
    /// shown or cached list uses, so memory follows the lists rather than everything seen this session.
    /// </summary>
    private void ReleasePerGameModels()
    {
        _gamesGrid.ReleaseModels();
        var keep = new HashSet<string>(StringComparer.Ordinal);
        foreach (var list in _cache)
        {
            foreach (var path in list.ModelPaths)
            {
                keep.Add(_theme.PerGamePath(path));
            }
        }

        if (_games is { } shown)
        {
            foreach (var path in shown.ModelPaths)
            {
                keep.Add(_theme.PerGamePath(path));
            }
        }

        _loader.ReleasePerGame(keep);
    }

    /// <summary>
    /// Starts loading the list's per-game models. A game shows its system's template until its own model has
    /// loaded, then switches to it without rebinding anything else.
    /// </summary>
    private void RequestPerGameModels(GamesSource source)
    {
        for (var model = 0; model < source.ModelPaths.Count; model++)
        {
            var path = source.ModelPaths[model];
            switch (_theme.RequestPerGame(path))
            {
                case ModelState.Ready:
                    UsePerGameModel(source, model, path);
                    break;
                case ModelState.Loading when !_perGameLoading.Exists(p => p.Source == source && p.Model == model):
                    _perGameLoading.Add((source, model, path));
                    break;
            }
        }
    }

    private void FinishPerGameModels()
    {
        for (var i = _perGameLoading.Count - 1; i >= 0; i--)
        {
            var (source, model, path) = _perGameLoading[i];
            var state = _theme.RequestPerGame(path);
            if (state == ModelState.Loading)
            {
                continue;
            }

            _perGameLoading.RemoveAt(i);
            if (state == ModelState.Ready && source == _games)
            {
                UsePerGameModel(source, model, path);
            }
        }
    }

    private void UsePerGameModel(GamesSource source, int model, string path)
    {
        if (_theme.PerGame(path) is not { } template)
        {
            return;
        }

        _gamesGrid.PrepareModel(template);
        foreach (var game in source.SetModel(model, template))
        {
            if (source == _games)
            {
                _gamesGrid.RefreshItem(game);
            }
        }
    }

    // ---- Media changes (M6) -------------------------------------------------------------------------

    /// <summary>A worker thread: some games' media changed (a rescan, a scrape, a clear, a bake).</summary>
    private void OnLibraryMediaChanged(object? sender, MediaChangedEventArgs e) => _queue.Post(() => OnMediaChanged(e.Games));

    /// <summary>
    /// Re-reads the shown list's media and rebinds the games whose media changed, keeping their models and the slots
    /// that didn't change. A bake (no games named) rebinds every bound game, so slots that were missing a derivative
    /// try again.
    /// </summary>
    private void OnMediaChanged(IReadOnlyList<GameKey>? games)
    {
        _cache.Clear();
        if (_games is not { } source || (games is not null && !Concerns(source, games)))
        {
            return;
        }

        RefreshShowcaseArt(games);
        var library = _services.Library;
        var token = _shutdown.Token;
        var kinds = source.Kinds;
        var ids = source.Id is FavouritesId or RecentlyPlayedId ? source.GameIds() : null;
        var all = source.Id is AllGamesId;
        _ = Task.Run(async () =>
        {
            try
            {
                var rows = all ? await library.GetAllGameMediaAsync(kinds, token).ConfigureAwait(false)
                    : source.Members is { } members ? await library.GetGameMediaAsync(members, kinds, token).ConfigureAwait(false)
                    : ids is null ? await library.GetGameMediaAsync(source.Id, kinds, token).ConfigureAwait(false)
                    : await library.GetGameMediaAsync(ids, kinds, token).ConfigureAwait(false);
                _queue.Post(() =>
                {
                    if (_games != source)
                    {
                        return;
                    }

                    var changed = source.ReplaceMedia(rows, null);
                    foreach (var file in source.ChangedModelFiles)
                    {
                        _theme.ForgetPerGame(file);
                    }

                    if (games is null)
                    {
                        for (var i = 0; i < source.Count; i++)
                        {
                            _gamesGrid.RefreshItem(i);
                        }
                    }
                    else
                    {
                        foreach (var game in changed)
                        {
                            _gamesGrid.RefreshItem(game);
                        }
                    }

                    RequestPerGameModels(source);
                    GD.Print($"Media: {changed.Count} game(s) in {source.Id} changed and were rebound in place{(games is null ? "; every bound game looked for its media again" : string.Empty)}.");
                });
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception e)
            {
                GD.PushWarning($"Media: couldn't re-read {source.Id}'s media: {e.Message}");
            }
        }, token);
    }

    private static bool Concerns(GamesSource source, IReadOnlyList<GameKey> games)
    {
        foreach (var game in games)
        {
            foreach (var system in source.SystemIds)
            {
                if (system == game.SystemId)
                {
                    return true;
                }
            }
        }

        return false;
    }

    // ---- A deleted game (2026-10-03) ------------------------------------------------------------------

    /// <summary>
    /// Main thread: a game was deleted from its options: its files are gone and it left the library. The systems grid
    /// is built again with the new counts (a system left with no games drops out, as after a rescan), and the shown
    /// list, if it held the game, is read again with the focus where it was, now on the next game. A list whose card
    /// dropped out (its last game) goes back to the systems.
    /// </summary>
    public void OnGameDeleted(GameKey game, IReadOnlyList<SystemSummary> systems)
    {
        _services.Systems = systems;
        _cache.Clear();
        RebindSystems(systems);
        if (_screen == Screen.Systems)
        {
            OnFocusChanged();
            return;
        }

        if (_screen != Screen.Games || _games is not { } shown || !Concerns(shown, [game]))
        {
            return;
        }

        if (FindEntry(shown.Id) is { } entry)
        {
            LoadGames(entry, Math.Max(0, _gamesGrid.FocusIndex), 0);
        }
        else
        {
            LeaveGames();
        }
    }

    // ---- Titles and details after a scrape or an edit (M7) ------------------------------------------

    /// <summary>
    /// Main thread: these games' titles or metadata changed (a scrape, a clear, an edit in the options panel). Their
    /// media follow MediaChanged; their titles are read again shortly after (several changes in a row read once), and
    /// the focused game's details now.
    /// </summary>
    public void OnGamesUpdated(IReadOnlyList<GameKey> games)
    {
        _cache.Clear();
        foreach (var game in games)
        {
            _titleSystems.Add(game.SystemId);
        }

        if (_titlesDue < 0)
        {
            _titlesDue = _clock + TitlesDelay;
        }

        if (_screen is Screen.Games && _focusKey >= 0)
        {
            _detailsDue = _clock;
        }
    }

    /// <summary>
    /// Reads the shown list again and updates the titles in place when its games are still in the same order; a title
    /// that moved a game (an edited title sorts in its own place, as does a scraped release date or a play when the list
    /// is sorted by them) binds the list again, keeping the focus on its game.
    /// </summary>
    private void RefreshTitles()
    {
        var concerns = false;
        if (_games is { } shown)
        {
            foreach (var system in shown.SystemIds)
            {
                concerns |= _titleSystems.Contains(system);
            }
        }

        _titleSystems.Clear();
        if (!concerns || _games is not { } source || FindEntry(source.Id) is not { } entry)
        {
            return;
        }

        var library = _services.Library;
        var token = _shutdown.Token;
        var ordering = source.Ordering;
        _ = Task.Run(async () =>
        {
            try
            {
                GameRow[] rows;
                if (entry.Virtual == VirtualKind.None && entry.Members is null)
                {
                    rows = [.. (await library.GetGamesAsync(entry.Id, ordering, token).ConfigureAwait(false)).Games];
                }
                else
                {
                    var list = entry.Members is { } members
                        ? await library.GetGamesAsync(members, ordering, token).ConfigureAwait(false)
                        : await VirtualGamesAsync(library, entry.Virtual, ordering, token).ConfigureAwait(false);
                    rows = new GameRow[list.Count];
                    for (var i = 0; i < rows.Length; i++)
                    {
                        rows[i] = list[i].Game;
                    }
                }

                _queue.Post(() =>
                {
                    if (_games != source)
                    {
                        return;
                    }

                    if (source.UpdateTitles(rows) is not { } changed)
                    {
                        var focusIndex = Math.Max(0, _gamesGrid.FocusIndex);
                        LoadGames(entry, null, focusIndex < source.Count ? source.Row(focusIndex).GameId : 0);
                        GD.Print($"Titles: {source.Id}'s order or a game's template changed, so it was bound again.");
                        return;
                    }

                    foreach (var game in changed)
                    {
                        _gamesGrid.RefreshItem(game);
                        if (game == _gamesGrid.FocusIndex && _screen == Screen.Games)
                        {
                            _overlay.ShowHeading(source.Row(game).Title, source.SystemName(game));
                            _detailsDue = _clock;
                        }
                    }

                    if (changed.Count > 0)
                    {
                        _overlay.List.RefreshTitles();
                        GD.Print($"Titles: {changed.Count} game(s) in {source.Id} renamed in place.");
                    }
                });
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception e)
            {
                GD.PushWarning($"Titles: couldn't re-read {source.Id}: {e.Message}");
            }
        }, token);
    }

    /// <summary>
    /// The theme resolved again and applied (a system's own model was imported or removed, or its <c>game_model</c>
    /// changed: M7; a game chose a template the theme hadn't loaded: 2026-10-07), as a switch to the same theme is.
    /// </summary>
    public void ReloadTheme() => SwitchTheme(ThemeId);

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

    /// <summary>
    /// Rescans the given systems (null: all) in the background, with its progress on the jobs card (M7), then refreshes
    /// the systems grid. Once at a time. <paramref name="media"/>: every media folder, or only those of systems with new games.
    /// </summary>
    public void Rescan(IReadOnlyList<string>? systemIds, RescanMedia media)
    {
        if (_jobs?.Scan(systemIds, media) == false)
        {
            ShowStatus("A scan is already running.");
        }
    }

    /// <summary>Bake missing derivatives after each scan (off in benches, which measure a library as it is).</summary>
    public bool BakeAfterScans { get; set; }

    private int _baking;

    /// <summary>
    /// Bakes every image that has no derivative yet, the user's own art included (M4), on the derivative service's
    /// below-normal thread. The library then reports media changed, so the grid shows them (M6).
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
                    $"Derivatives: {summary.Baked} baked, {summary.Failed} failed, {summary.Pruned} stale removed, of {summary.Images} images ({summary.Elapsed.TotalSeconds:0.0} s)"));
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
        if (error is not null)
        {
            ShowStatus(error);
        }

        if (systems is null)
        {
            return;
        }

        if (BakeAfterScans)
        {
            BakeDerivatives();
        }

        _services.Systems = systems;
        _ = _services.CheckInstallsAsync();
        _cache.Clear();
        var focus = _systemsGrid.FocusIndex;
        _systems = new SystemsSource(BuildEntries(systems), _systemsGrid.Templates.Count);
        if (_screen == Screen.Systems)
        {
            _systemsGrid.Layout = SystemsLayout();
            _systemsGrid.Bind(_systems, focus);
            OnFocusChanged();
        }
    }

    /// <summary>
    /// Main thread: the settings screen saved config (M7). The systems grid is built again with it (names, emulators,
    /// folders in the details, its layout and order, whether systems without games show), keeping the focus on the
    /// same system, on whichever screen; ROM folder changes are rescanned by the settings screen, which refreshes it
    /// again. The games shown are read again if their order changed, or laid out again if their layout did, keeping
    /// the focus on the same game.
    /// </summary>
    public void OnConfigChanged()
    {
        _cache.Clear();
        RebindSystems(_services.Systems);
        if (_screen == Screen.Systems)
        {
            OnFocusChanged();
        }
        else if (_screen == Screen.Games && _games is { } games && FindEntry(games.Id) is { Sorted: true } entry
                 && (GamesSort(games.Id) != games.Ordering || !SameMembers(entry.Members, games.Members)))
        {
            var focusIndex = Math.Max(0, _gamesGrid.FocusIndex);
            LoadGames(entry, null, focusIndex < games.Count ? games.Row(focusIndex).GameId : 0);
        }
        else if (_screen == Screen.Games && _games is { } shown && GamesLayout(shown.Id) != _gamesGrid.Layout)
        {
            BindGames(shown, Math.Max(0, _gamesGrid.FocusIndex));
            OnFocusChanged();
        }
    }
}
