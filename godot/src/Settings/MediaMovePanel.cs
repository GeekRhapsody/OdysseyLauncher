using System;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Media;

namespace Launcher.App.Settings;

/// <summary>
/// Moves the media folder (2026-10-04, A4), over the media folder page until it's done: the files move on a worker
/// (<see cref="MediaFolderMove"/>), then the new folder is saved in settings.toml and applied, then the old folder's
/// originals go (when they were copied from another drive). Cancelling, or a file that can't move, puts back what had
/// moved, and nothing is saved; a save that fails puts everything back too. It stays on top while it works (Menu doesn't
/// close the settings), so nothing writes to the media folder meanwhile: the page doesn't start it while a scan, a
/// scrape or an import runs. Closing the window while it works stops it first (or lets the save finish), then quits, so
/// the media is never left split between the two folders.
/// </summary>
public sealed partial class MediaMovePanel : UiPanel
{
    private readonly SettingsController _settings;
    private readonly UiPanel _page;
    private readonly MediaMovePlan _plan;
    private readonly ConfigEdit _edit;
    private readonly CancellationTokenSource _cancel = new();
    private readonly ProgressSink _progress = new();
    private readonly Label _counts;
    private readonly ProgressBar _bar;
    private readonly Button _stop;
    private MediaMoveProgress _shown = new(-1, 0, 0, 0);
    private SceneTree? _tree;

    /// <summary>Moves running: while one is, closing the window is this panel's to handle (it stops, then quits).</summary>
    public static int Moving { get; private set; }
    private bool _started;
    private bool _saving;
    private bool _quitWhenDone;

    public MediaMovePanel(SettingsController settings, UiPanel page, MediaMovePlan plan, ConfigEdit edit)
        : base("Moving your media", new Vector2(760, 0), PanelPlacement.Centre, dimBelow: true)
    {
        _settings = settings;
        _page = page;
        _plan = plan;
        _edit = edit;
        var text = UiStyle.Label($"From {plan.From}\nTo {plan.To}", UiStyle.Body, wrap: true);
        text.CustomMinimumSize = new Vector2(700, 0);
        Body.AddChild(text);
        _counts = UiStyle.Label(string.Empty, UiStyle.Detail);
        Body.AddChild(_counts);
        _bar = JobsHud.Bar(0);
        Body.AddChild(_bar);
        Body.AddChild(new Control { CustomMinimumSize = new Vector2(0, 8), MouseFilter = MouseFilterEnum.Ignore });
        var buttons = new HBoxContainer { Alignment = BoxContainer.AlignmentMode.End, MouseFilter = MouseFilterEnum.Ignore };
        Body.AddChild(buttons);
        _stop = new Button { Text = "Stop", CustomMinimumSize = new Vector2(180, 46), FocusMode = FocusModeEnum.All };
        _stop.Pressed += Stop;
        buttons.AddChild(_stop);
        SetHints("A / B  Stop: what moved goes back");
        ShowCounts(new MediaMoveProgress(0, plan.Files.Count, 0, plan.Bytes));
    }

    protected override string BackLabel => "Stop";

    /// <summary>Menu would close the settings under it: it's ignored until the move is done.</summary>
    public override bool Handle(NavCommand command) => command == NavCommand.Menu;

    public override void GoBack() => Stop();

    public override void Tick(double delta)
    {
        base.Tick(delta);
        if (!_started)
        {
            _started = true;
            Start();
        }

        // Only when it moved on: a label's text is a string made per change, not per frame.
        var now = _progress.Last;
        if (now.Files != _shown.Files && !_saving && !_cancel.IsCancellationRequested)
        {
            ShowCounts(now);
        }
    }

    private void ShowCounts(MediaMoveProgress progress)
    {
        _shown = progress;
        _counts.Text = string.Create(CultureInfo.InvariantCulture,
            $"{progress.Files:N0} of {progress.TotalFiles:N0} files · {UiStyle.Size(progress.Bytes)} of {UiStyle.Size(progress.TotalBytes)}");
        _bar.Value = progress.TotalBytes > 0 ? (double)progress.Bytes / progress.TotalBytes : progress.TotalFiles > 0 ? (double)progress.Files / progress.TotalFiles : 0;
    }

    private void Stop()
    {
        if (_saving || _cancel.IsCancellationRequested)
        {
            return;
        }

        _cancel.Cancel();
        _stop.Disabled = true;
        _counts.Text = "Stopping: putting back what moved…";
    }

    public override void _Notification(int what)
    {
        base._Notification(what);
        if (what == NotificationWMCloseRequest && _tree is not null)
        {
            // AutoAcceptQuit is off while it works: stop (or finish saving), then quit.
            _quitWhenDone = true;
            Stop();
        }
    }

    private void Start()
    {
        _tree = GetTree();
        _tree.AutoAcceptQuit = false;
        Moving++;
        var writer = _settings.Writer();
        var queue = _settings.Ui.Queue;
        var token = _cancel.Token;
        _ = Task.Run(async () =>
        {
            MediaMove move;
            try
            {
                move = MediaFolderMove.Move(_plan, _progress, token);
            }
            catch (OperationCanceledException)
            {
                queue.Post(() => End("Not moved", "Stopped: your media is all in the old folder, as it was.", false));
                return;
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                queue.Post(() => End("Not moved", $"A file couldn't be moved, so what had moved went back to the old folder: {e.Message}", false));
                return;
            }

            // The files are in the new folder: from here it saves, or puts them back if it can't.
            queue.Post(() =>
            {
                _saving = true;
                _stop.Disabled = true;
                _counts.Text = "Saving the new folder…";
            });
            var result = SettingsController.Write(writer, [_edit]);
            if (!result.Saved)
            {
                var stuck = move.Undo();
                queue.Post(() => End("Not moved", stuck == 0
                    ? $"The new folder couldn't be saved, so your media went back to the old folder. {result.Problem}"
                    : string.Create(CultureInfo.InvariantCulture, $"The new folder couldn't be saved, and {stuck:N0} file{(stuck == 1 ? " is" : "s are")} still in {_plan.To}: move {(stuck == 1 ? "it" : "them")} back by hand. {result.Problem}"), false));
                return;
            }

            var applied = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            queue.Post(() =>
            {
                _settings.Apply(_page, [_edit], result, "Media folder moved.");
                applied.SetResult();
            });
            await applied.Task.ConfigureAwait(false);

            var leftBehind = move.Finish();
            GD.Print(string.Create(CultureInfo.InvariantCulture,
                $"Media folder: moved from {_plan.From} to {_plan.To}: {move.Moved} file(s) moved, {move.AlreadyThere} already there, {move.Gone} gone, {leftBehind} left behind."));
            queue.Post(() => End("Media folder moved", Outcome(move, leftBehind), true));
        });
    }

    private string Outcome(MediaMove move, int leftBehind)
    {
        var text = new StringBuilder();
        text.Append(CultureInfo.InvariantCulture, $"{move.Moved:N0} file{(move.Moved == 1 ? string.Empty : "s")} moved to:\n{_plan.To}\n\n");
        if (move.AlreadyThere > 0)
        {
            text.Append(CultureInfo.InvariantCulture,
                $"{move.AlreadyThere:N0} {(move.AlreadyThere == 1 ? "was" : "were")} in the new folder already: the new folder's {(move.AlreadyThere == 1 ? "is" : "are")} used, and the old folder's stay in {_plan.From}. ");
        }

        if (leftBehind > 0)
        {
            text.Append(CultureInfo.InvariantCulture, $"{leftBehind:N0} couldn't be deleted from {_plan.From}, and stay there, unused. ");
        }

        return text.Append("The library is being rescanned.").ToString();
    }

    private void End(string title, string message, bool moved)
    {
        var layer = Layer;
        var tree = _tree;
        _tree = null;
        if (tree is not null)
        {
            // POC: the main scene keeps AutoAcceptQuit off and quits gracefully itself (Boot/AppQuit).
            Moving--;
        }

        Close();
        if (moved)
        {
            _settings.MediaFolderMoved(_settings.Services.Library.MediaDir);
        }

        if (_quitWhenDone && tree is not null)
        {
            GD.Print($"Media folder: {title.ToLowerInvariant()}; quitting, as the window was closed.");
            Launcher.App.Boot.AppQuit.Request(tree);
        }
        else if (layer is not null)
        {
            ConfirmDialog.Tell(layer, title, message);
        }
    }

    public override void OnClosed()
    {
        // Closed while it works (the settings closing some other way): stop, which puts everything back.
        if (!_saving)
        {
            _cancel.Cancel();
        }
    }

    /// <summary>The worker's latest progress, read once a frame (<see cref="Progress{T}"/> would post through Godot's context, unbudgeted).</summary>
    private sealed class ProgressSink : IProgress<MediaMoveProgress>
    {
        private readonly object _gate = new();
        private MediaMoveProgress _last;

        public MediaMoveProgress Last
        {
            get
            {
                lock (_gate)
                {
                    return _last;
                }
            }
        }

        public void Report(MediaMoveProgress value)
        {
            lock (_gate)
            {
                _last = value;
            }
        }
    }
}
