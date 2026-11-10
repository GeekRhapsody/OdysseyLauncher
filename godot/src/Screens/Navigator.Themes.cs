using System;
using System.Collections.Generic;
using System.Globalization;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Diagnostics;
using Launcher.App.Models;
using Launcher.App.Theming;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;
using OverlayPalette = Launcher.Core.Theming.OverlayPalette;

namespace Launcher.App.Screens;

public sealed partial class Navigator
{
    // ---- Themes (M6) ------------------------------------------------------------------------------

    /// <summary>
    /// Loads a theme (null: the next one, in id order) in the background and applies it when its models are in:
    /// systems and templates are rebuilt without a restart. For this session only; the settings screen (M7) will
    /// write <c>[display] theme</c>.
    /// </summary>
    public void SwitchTheme(string? id)
    {
        if (_switchingTheme)
        {
            return;
        }

        var available = _theme.Plan.Themes.Available;
        if (id is null && available.Count == 0)
        {
            return;
        }

        var target = id ?? available[(Math.Max(0, IndexOf(available, ThemeId)) + 1) % available.Count];
        _switchingTheme = true;
        _themeRequestedAt = _clock;
        _overlay.SetStatus($"Loading the theme '{target}'…");
        var services = _services;
        _ = Task.Run(async () =>
        {
            try
            {
                var plan = ThemePlan.Build(services.Config, services.Paths, target, services.BuiltInThemes);
                foreach (var diagnostic in plan.Diagnostics)
                {
                    GD.Print(diagnostic.ToString());
                }

                // The templates games chose are loaded with the theme's, so its slot layout covers them.
                var choices = await services.Library.GetChosenGameTemplatesAsync(CancellationToken.None).ConfigureAwait(false);
                _queue.Post(() =>
                {
                    _loader.ForgetUserModels();
                    _pendingTheme = new ThemeRuntime(plan, _loader);
                    _pendingTheme.UseGameChoices(choices);
                    _pendingTheme.UseShownSystems(ShownSystemIds(_services.Systems, _services.Config));
                });
            }
            catch (Exception e)
            {
                _queue.Post(() => ThemeFailed(e.Message));
            }
        });
    }

    private void PollTheme(ThemeRuntime pending)
    {
        try
        {
            if (pending.Poll())
            {
                ApplyTheme(pending);
            }
        }
        catch (InvalidOperationException e)
        {
            ThemeFailed(e.Message);
        }
    }

    private void ThemeFailed(string message)
    {
        _pendingTheme = null;
        _switchingTheme = false;
        GD.PushError($"Theme: {message}");
        ShowStatus($"The theme couldn't be loaded. {message}");
    }

    /// <summary>Main thread: swaps every template, the slot layout and the look, and rebinds what's on screen.</summary>
    private void ApplyTheme(ThemeRuntime theme)
    {
        var clock = System.Diagnostics.Stopwatch.StartNew();
        _pendingTheme = null;
        _switchingTheme = false;
        _theme = theme;
        _services.Theme = theme.Plan;
        _cache.Clear();
        _perGameLoading.Clear();

        _systemsGrid.DisableTextures();
        _systemsGrid.SetMotion(theme.Plan.Active.Motion);
        _systemsGrid.SetTemplates(theme.CardTemplates);
        _gamesGrid.DisableTextures();
        _gamesGrid.SetMotion(theme.Plan.Active.Motion);
        _gamesGrid.SetTemplates(theme.GameTemplates);

        // What the new theme doesn't use is freed now, video memory and all (2026-10-16), not kept for the session.
        var inUse = new List<ItemTemplate>(theme.GameTemplates);
        inUse.AddRange(theme.CardTemplates);
        if (ModelView.ReleaseParked() is { } detailsModel)
        {
            inUse.Add(detailsModel);
        }

        var freed = _loader.ReleaseUnused(inUse);
        _themeCollectDue = _clock + ThemeCollectDelay;
        InstallLayout(theme);
        InstallCardLayout(theme);

        var systemsFocus = _systemsGrid.FocusIndex;
        _systems = new SystemsSource(BuildEntries(_services.Systems), _systemsGrid.Templates.Count);
        _systemsGrid.Layout = SystemsLayout();
        _systemsGrid.Bind(_systems, Math.Max(0, systemsFocus));
        BakeLogos();
        var shownEntry = _games is { } shown ? FindEntry(shown.Id) : null;
        _stage.ForgetWallpapers();
        _stage.Show(theme.LookFor(shownEntry is { Virtual: VirtualKind.None } ? shownEntry.Id : null), theme.TransitionSeconds);
        var menus = System.Diagnostics.Stopwatch.StartNew();
        MenuLook.Use(theme.Plan.Active.Menu);
        _overlay.Use(OverlayPalette.For(theme.Plan.Active.Menu));
        var menusMs = menus.Elapsed.TotalMilliseconds;

        if (_screen == Screen.Entering && _entering is { } entering && FindEntry(entering) is { } enteringEntry)
        {
            // A list still loading for the old theme is dropped when it arrives, so it's loaded again for this one.
            LoadGames(enteringEntry, null, null);
        }
        else if (_games is { } games && shownEntry is not null)
        {
            // The shown list is bound to the new templates at once, then loaded again with the media kinds the new
            // theme's chains name.
            var focusIndex = Math.Max(0, _gamesGrid.FocusIndex);
            var focusGame = focusIndex < games.Count ? games.Row(focusIndex).GameId : 0;
            games.BindTemplates(theme.GameTemplateOf, theme.ChosenTemplateOf, _gamesGrid.Templates.Count);
            BindGames(games, focusIndex);
            LoadGames(shownEntry, null, focusGame);
        }

        DebugHooks.Theme = (theme.Plan.Active.Id, theme.Layout.ToString());
        GD.Print(FormattableString.Invariant($"Theme: now '{theme.Plan.Active.Id}' ({theme.Plan.Active.Name}), {_clock - _themeRequestedAt:0.000} s after it was asked for, applied in {clock.Elapsed.TotalMilliseconds:0.0} ms on the main thread (the menus {menusMs:0.0} ms): {theme.GameTemplates.Count} game template(s), {theme.CardTemplates.Count} system model(s), {freed} model(s) freed; media slots: {theme.Layout}."));
        ShowStatus($"Theme: {theme.Plan.Active.Name}");
        OnFocusChanged();
    }

    /// <summary>
    /// Main thread: the cards of the systems the grid shows are in (2026-10-27), after systems appeared or went (a
    /// rescan, a deleted game, showing or hiding empty systems). The systems grid gets them and is bound again, and
    /// the cards no longer shown are freed, video memory and all, as a theme switch frees a theme's (2026-10-16); while
    /// a switch is on its way, it frees them instead, since its models aren't in use yet.
    /// </summary>
    private void ApplyCards()
    {
        var clock = System.Diagnostics.Stopwatch.StartNew();
        _systemsGrid.DisableTextures();
        _systemsGrid.SetTemplates(_theme.CardTemplates);
        var freed = 0;
        if (!_switchingTheme)
        {
            var inUse = new List<ItemTemplate>(_theme.GameTemplates);
            inUse.AddRange(_theme.CardTemplates);
            if (ModelView.ReleaseParked() is { } detailsModel)
            {
                inUse.Add(detailsModel);
            }

            freed = _loader.ReleaseUnused(inUse);
            _themeCollectDue = _clock + ThemeCollectDelay;
        }

        InstallCardLayout(_theme);
        RebindSystems(_services.Systems);
        if (_screen == Screen.Systems)
        {
            OnFocusChanged();
        }

        GD.Print(FormattableString.Invariant($"Theme: the shown systems' cards applied in {clock.Elapsed.TotalMilliseconds:0.0} ms on the main thread: {_theme.CardTemplates.Count} system model(s), {freed} model(s) freed."));
    }

    /// <summary>The theme's slot layout: its arrays are built on a worker (creating textures can stall), then installed.</summary>
    private void InstallLayout(ThemeRuntime theme)
    {
        if (Streamer is not { } streamer)
        {
            return;
        }

        var layout = theme.Layout;
        var (large, small) = (streamer.Large, streamer.Small);
        _ = Task.Run(() =>
        {
            var built = System.Diagnostics.Stopwatch.StartNew();
            var arrays = streamer.BuildArrays(layout, large, small);
            GD.Print(FormattableString.Invariant($"Theme: media arrays for {layout} ready in {built.Elapsed.TotalMilliseconds:0.0} ms on a worker (reused: large {arrays.Large == large}, small {arrays.Small == small})."));
            _queue.Post(() =>
            {
                if (theme != _theme)
                {
                    return;
                }

                streamer.Install(layout, arrays.Large, arrays.Small);
                if (Launcher?.InGameMode != true)
                {
                    _gamesGrid.EnableTextures();
                }
            });
        });
    }

    /// <summary>
    /// The systems grid's layout for its cards' logos: with none, nothing to build; else its array is built on a
    /// worker, as the games grid's are, then installed.
    /// </summary>
    public void InstallCardLayout(ThemeRuntime theme)
    {
        if (CardStreamer is not { } streamer)
        {
            return;
        }

        var layout = theme.CardLayout;
        if (layout.ChannelCount == 0)
        {
            streamer.Install(layout, null, null);
            _systemsGrid.EnableTextures();
            return;
        }

        var (large, small) = (streamer.Large, streamer.Small);
        _ = Task.Run(() =>
        {
            var built = System.Diagnostics.Stopwatch.StartNew();
            var arrays = streamer.BuildArrays(layout, large, small);
            GD.Print(FormattableString.Invariant($"Theme: card logo arrays for {layout} ready in {built.Elapsed.TotalMilliseconds:0.0} ms on a worker."));
            _queue.Post(() =>
            {
                if (theme != _theme)
                {
                    return;
                }

                streamer.Install(layout, arrays.Large, arrays.Small);
                if (Launcher?.InGameMode != true)
                {
                    _systemsGrid.EnableTextures();
                }
            });
        });
    }

    private CancellationTokenSource? _logoBake;
    private int _logoRefreshQueued;

    /// <summary>
    /// Bakes the active theme's logos that have no derivative yet (the cards in the grid's order first), ahead of any
    /// library bake on the derivative service's below-normal thread, and deletes the logo derivatives it doesn't name:
    /// they're kept for the last theme with logos, so switching to a theme without them and back bakes nothing. Each
    /// card shows its fallback until its logo is baked, then the logo. After the warm-up (never in start-up) and after
    /// each theme switch, which cancels a bake still running.
    /// </summary>
    public void BakeLogos()
    {
        _logoBake?.Cancel();
        _logoBake = null;
        var theme = _theme;
        if (theme.Plan.Logos.Count == 0)
        {
            return;
        }

        // The cards in the grid's order first, then the rest (a system hidden for having no games).
        var logos = new List<ThemeLogo>(theme.Plan.Logos.Count);
        foreach (var entry in _systems.Entries)
        {
            if (theme.Plan.Logos.TryGetValue(entry.Id, out var logo))
            {
                logos.Add(logo);
            }
        }

        foreach (var logo in theme.Plan.Logos.Values)
        {
            if (!logos.Contains(logo))
            {
                logos.Add(logo);
            }
        }

        var derivatives = _services.Derivatives;
        var cacheDir = theme.Plan.Paths.CacheDir;
        var bake = _logoBake = CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var token = bake.Token;
        _ = Task.Run(async () =>
        {
            try
            {
                var summary = await ThemeLogos.BakeMissingAsync(derivatives, cacheDir, logos, () => RefreshLogos(theme), token).ConfigureAwait(false);
                if (summary.Baked + summary.Failed + summary.Pruned > 0)
                {
                    GD.Print(string.Create(CultureInfo.InvariantCulture,
                        $"Theme: logos: {summary.Baked} baked, {summary.Failed} failed, {summary.Pruned} stale removed, of {summary.Logos} ({summary.Elapsed.TotalSeconds:0.0} s)"));
                }
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception e)
            {
                GD.PushWarning($"Theme: baking logos failed: {e.Message}");
            }
        }, token);
    }

    /// <summary>
    /// Any thread, after a logo is baked: the cards that found no derivative showed their fallback, so they ask again
    /// (once per frame at most, however many were baked since).
    /// </summary>
    private void RefreshLogos(ThemeRuntime theme)
    {
        if (Interlocked.Exchange(ref _logoRefreshQueued, 1) == 1)
        {
            return;
        }

        _queue.Post(() =>
        {
            Volatile.Write(ref _logoRefreshQueued, 0);
            if (theme == _theme && Launcher?.InGameMode != true)
            {
                _systemsGrid.EnableTextures();
            }
        });
    }

    /// <summary>A virtual card's games: Favourites or All games in <paramref name="ordering"/>'s order, or Recently played. Thread pool.</summary>
    public static Task<IReadOnlyList<VirtualGameRow>> VirtualGamesAsync(ILibrary library, VirtualKind kind, GamesOrdering ordering, CancellationToken token) =>
        kind switch
        {
            VirtualKind.Favourites => library.GetFavouritesAsync(ordering, token),
            VirtualKind.RecentlyPlayed => library.GetRecentlyPlayedAsync(RecentlyPlayedLimit, token),
            _ => library.GetAllGamesAsync(ordering, token),
        };

    /// <summary>Whether a card's group and the systems its shown list was read from are the same (both null for a plain system).</summary>
    private static bool SameMembers(IReadOnlyList<string>? card, IReadOnlyList<string>? list)
    {
        if (card is null || list is null)
        {
            return card is null && list is null;
        }

        if (card.Count != list.Count)
        {
            return false;
        }

        for (var i = 0; i < card.Count; i++)
        {
            if (card[i] != list[i])
            {
                return false;
            }
        }

        return true;
    }

    private SystemEntry? FindEntry(string id)
    {
        foreach (var entry in _systems.Entries)
        {
            if (entry.Id == id)
            {
                return entry;
            }
        }

        return null;
    }

    private static int IndexOf(IReadOnlyList<string> list, string value)
    {
        for (var i = 0; i < list.Count; i++)
        {
            if (list[i] == value)
            {
                return i;
            }
        }

        return -1;
    }

    private void ShowStatus(string status)
    {
        _overlay.SetStatus(status);
        _statusClearAt = _clock + StatusSeconds;
    }
}
