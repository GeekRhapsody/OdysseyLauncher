using System;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Grid;
using Launcher.App.Launching;

namespace Launcher.App.Screens;

public sealed partial class Navigator
{
    // ---- Launching ------------------------------------------------------------------------------

    private void StartLaunch()
    {
        if (_games is null || _focusedIndex < 0 || Launcher is null)
        {
            return;
        }

        _screen = Screen.Launching;
        _launchPad = Gamepads.Pressing();
        _launchStartedAt = _clock;
        _launchSeconds = _gamesGrid.LaunchSeconds;
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

        // Play statistics changed, and Recently played with them, and a list sorted by plays: the shown one is read
        // again shortly (keeping the focus on the game), and cached ones are dropped.
        _detailsDue = _clock;
        _cache.RemoveAll(static list => list.Ordering.FollowsPlays);
        if (_games is { Ordering.FollowsPlays: true } games)
        {
            foreach (var system in games.SystemIds)
            {
                _titleSystems.Add(system);
            }

            if (_titlesDue < 0)
            {
                _titlesDue = _clock + TitlesDelay;
            }
        }
    }

    /// <summary>
    /// A game is starting: free the media textures for the emulator (A1 Starting). The renderer lets go of them only
    /// once it draws and the wrappers holding them are collected, which <see cref="CollectAfterFree"/> does a moment on.
    /// </summary>
    public void OnGameModeEntered()
    {
        _gamesGrid.DisableTextures();
        Streamer?.Evict();
        _systemsGrid.DisableTextures();
        CardStreamer?.Evict();

        // The tree is paused, so the timer is one that runs anyway.
        GetTree().CreateTimer(CollectAfterGameSeconds, processAlways: true).Timeout += CollectAfterFree;
    }

    /// <summary>Back in the launcher: recreate the media arrays and re-request what's on screen.</summary>
    public void OnGameModeLeft()
    {
        Streamer?.Restore();
        _gamesGrid.EnableTextures();
        CardStreamer?.Restore();
        _systemsGrid.EnableTextures();
    }

    /// <summary>
    /// Main thread, a moment after a game starts: a full collection that waits for the finalisers, then frames drawn by
    /// hand. The arrays went through a Variant, whose disposer holds them until its finaliser runs (2026-10-16, as
    /// after a theme switch), and the render loop is off, so the renderer only lets go of what was freed when it draws
    /// (more frames than it keeps in flight). Without them the first launch of a session freed the arrays but every
    /// later one freed nothing, and each return added another 171 MB (a Console library, measured 2026-10-28).
    /// </summary>
    private void CollectAfterFree()
    {
        if (Launcher?.InGameMode != true)
        {
            return;
        }

        GC.Collect(2, GCCollectionMode.Forced, blocking: true);
        GC.WaitForPendingFinalizers();
        for (var frame = 0; frame < ReleaseDraws; frame++)
        {
            RenderingServer.ForceDraw(true, 0.0);
        }
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

        // The list of titles fades with the games grid.
        if (_overlay.List.Visible && _overlay.List.Modulate.A != 1 - _gamesGrid.Fade)
        {
            _overlay.List.Modulate = new Color(1, 1, 1, 1 - _gamesGrid.Fade);
        }

        // So does the showcase, and its hero art.
        if (_overlay.Showcase.Visible)
        {
            _overlay.Showcase.FadeWithGrid(1 - _gamesGrid.Fade);
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
}
