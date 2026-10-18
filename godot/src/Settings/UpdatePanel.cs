using System;
using System.Globalization;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Platform;
using Launcher.Core.Updates;

namespace Launcher.App.Settings;

/// <summary>
/// Downloads an update and restarts into it (2026-10-18), over the settings until it's done: the package downloads,
/// is checked against its SHA-256 and is unpacked beside the launcher on a worker (<see cref="UpdateService"/>), then
/// the platform's installer is started and the launcher quits, so the installer can replace its files and start the
/// new version. Stop (A or B) cancels the download and deletes what came; a failure is told in a dialog. Either way,
/// nothing installed has changed. Menu doesn't close the settings under it while it works.
/// </summary>
public sealed partial class UpdatePanel : UiPanel
{
    private const double RefreshSeconds = 0.2;

    private readonly SettingsController _settings;
    private readonly AppUpdater _updater;
    private readonly UpdateService _service;
    private readonly UpdateRelease _release;
    private readonly UpdateHandover _handover;
    private readonly CancellationTokenSource _cancel = new();
    private readonly ProgressSink _progress = new();
    private readonly Label _counts;
    private readonly ProgressBar _bar;
    private readonly Button _stop;
    private UpdateProgress _shown = new(UpdateStage.Downloading, -1, 0);
    private double _sinceRefresh;
    private bool _started;
    private bool _installing;

    public UpdatePanel(SettingsController settings, AppUpdater updater, UpdateService service, UpdateRelease release, UpdateHandover handover)
        : base($"Updating to {release.Version}", new Vector2(760, 0), PanelPlacement.Centre, dimBelow: true)
    {
        _settings = settings;
        _updater = updater;
        _service = service;
        _release = release;
        _handover = handover;
        var text = UiStyle.Label($"Downloading Odyssey Launcher {release.Version} from {updater.SourceName}. Once it's checked, the launcher restarts with it.", UiStyle.Body, wrap: true);
        text.CustomMinimumSize = new Vector2(700, 0);
        Body.AddChild(text);
        _counts = UiStyle.Label("Starting…", UiStyle.Detail);
        Body.AddChild(_counts);
        _bar = JobsHud.Bar(0);
        Body.AddChild(_bar);
        Body.AddChild(new Control { CustomMinimumSize = new Vector2(0, 8), MouseFilter = MouseFilterEnum.Ignore });
        var buttons = new HBoxContainer { Alignment = BoxContainer.AlignmentMode.End, MouseFilter = MouseFilterEnum.Ignore };
        Body.AddChild(buttons);
        _stop = new Button { Text = "Stop", CustomMinimumSize = new Vector2(180, 46), FocusMode = FocusModeEnum.All };
        _stop.Pressed += Stop;
        buttons.AddChild(_stop);
        SetHints("A / B  Stop: nothing is changed");
    }

    /// <summary>Menu would close the settings under it: it's ignored until the download is done.</summary>
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

        // A few times a second, and only when it moved on: a label's text is a string made per change.
        _sinceRefresh += delta;
        var now = _progress.Last;
        if (_sinceRefresh >= RefreshSeconds && now != _shown && !_installing && !_cancel.IsCancellationRequested)
        {
            _sinceRefresh = 0;
            Show(now);
        }
    }

    private void Show(UpdateProgress progress)
    {
        _shown = progress;
        _counts.Text = progress.Stage switch
        {
            UpdateStage.Downloading when progress.Total > 0 => $"{UiStyle.Size(progress.Done)} of {UiStyle.Size(progress.Total)}",
            UpdateStage.Downloading => UiStyle.Size(progress.Done),
            UpdateStage.Verifying => "Checking the download…",
            _ => string.Create(CultureInfo.InvariantCulture, $"Unpacking: {progress.Done:N0} of {progress.Total:N0} files"),
        };
        _bar.Value = progress.Total > 0 ? (double)progress.Done / progress.Total : 0;
    }

    private void Stop()
    {
        if (_installing || _cancel.IsCancellationRequested)
        {
            return;
        }

        _cancel.Cancel();
        _stop.Disabled = true;
        _counts.Text = "Stopping…";
    }

    private void Start()
    {
        _updater.Updating = true;
        var queue = _settings.Ui.Queue;
        var token = _cancel.Token;
        _ = Task.Run(async () =>
        {
            string? failure;
            try
            {
                failure = _service.CheckWritable();
                if (failure is null)
                {
                    var staged = await _service.DownloadAsync(_release, _progress, token).ConfigureAwait(false);
                    token.ThrowIfCancellationRequested();
                    queue.Post(Installing);
                    failure = _updater.StartInstaller(_handover, staged);
                    if (failure is null)
                    {
                        queue.Post(Restart);
                        return;
                    }
                }
            }
            catch (OperationCanceledException)
            {
                _service.DeleteStaging();
                queue.Post(() => End(null));
                return;
            }
            catch (UpdateException e)
            {
                failure = e.Message;
            }
            catch (Exception e)
            {
                failure = e.Message;
                GD.PushError($"Update: {_release.Version} failed: {e}");
            }

            GD.Print($"Update: {_release.Version} wasn't installed: {failure}");
            _service.DeleteStaging();
            queue.Post(() => End(failure));
        });
    }

    private void Installing()
    {
        _installing = true;
        _stop.Disabled = true;
        _counts.Text = "Starting the installer…";
        _bar.Value = 1;
    }

    /// <summary>The installer waits for the launcher to quit: quit (closing the databases as any quit does).</summary>
    private void Restart()
    {
        _counts.Text = $"Restarting with {_release.Version}…";
        SetHints(string.Empty);
        GD.Print($"Update: quitting, so {_release.Version} can be installed.");
        // A frame later, so the line above is drawn.
        GetTree().CreateTimer(0).Timeout += () => GetTree().Quit();
    }

    /// <param name="failure">Why it wasn't installed, or null when it was stopped.</param>
    private void End(string? failure)
    {
        var layer = Layer;
        _updater.Updating = false;
        Close();
        if (layer is null)
        {
            return;
        }

        var current = _updater.Current is { } version ? version.ToString() : Launcher.Core.CoreInfo.Version;
        if (failure is null)
        {
            layer.Top?.ShowStatus($"Update stopped: you still have {current}.", UiStyle.Dim, 6);
        }
        else
        {
            ConfirmDialog.Tell(layer, "Not updated", $"{failure}\n\nNothing was changed: you still have {current}.");
        }
    }

    public override void OnClosed()
    {
        // Closed while it works (the settings closing some other way): stop, which deletes what came.
        if (!_installing)
        {
            _cancel.Cancel();
        }
    }

    /// <summary>The worker's latest progress, read a few times a second (<see cref="Progress{T}"/> would post through Godot's context, unbudgeted).</summary>
    private sealed class ProgressSink : IProgress<UpdateProgress>
    {
        private readonly object _gate = new();
        private UpdateProgress _last = new(UpdateStage.Downloading, 0, 0);

        public UpdateProgress Last
        {
            get
            {
                lock (_gate)
                {
                    return _last;
                }
            }
        }

        public void Report(UpdateProgress value)
        {
            lock (_gate)
            {
                _last = value;
            }
        }
    }
}
