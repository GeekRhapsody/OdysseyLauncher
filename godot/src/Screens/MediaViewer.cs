using System;
using System.Collections.Generic;
using System.Globalization;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Media;

namespace Launcher.App.Screens;

/// <summary>
/// One of a game's images or its video at the window's full size, on black (A on a card of its details screen). Left
/// and right go to the previous and next; A pauses and plays a video (and plays it again once it's ended); B or Y
/// goes back. An image is decoded on a worker to fit the window (never enlarged in the decode; the screen scales it);
/// a video plays through <see cref="VideoPlayback"/>. The caption fades after a few seconds and comes back with any
/// button.
/// </summary>
public sealed partial class MediaViewer : UiPanel
{
    private const double CaptionSeconds = 3;
    private const float CaptionFade = 0.4f;

    private readonly UiContext _ui;
    private readonly IVideoDecoder? _video;
    private readonly IReadOnlyList<Item> _items;
    private readonly AspectRatioContainer _fit;
    private readonly TextureRect _picture;
    private readonly Label _message;
    private readonly Control _caption;
    private readonly Label _name;
    private readonly Label _place;
    private readonly Label _controls;
    private readonly ProgressBar _progress;
    private readonly AudioStreamPlayer _sound;
    private int _index;
    private int _generation;
    private VideoPlayback? _playback;
    private ImageTexture? _image;
    private double _captionAge;
    private string? _shownError;

    public MediaViewer(UiContext ui, IVideoDecoder? video, IReadOnlyList<Item> items, int index)
        : base(items[index].Name, Vector2.Zero, PanelPlacement.FullScreen)
    {
        _ui = ui;
        _video = video;
        _items = items;

        var area = new Control { SizeFlagsVertical = SizeFlags.ExpandFill, SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        Body.AddChild(area);
        _fit = new AspectRatioContainer { StretchMode = AspectRatioContainer.StretchModeEnum.Fit, MouseFilter = MouseFilterEnum.Ignore };
        _fit.SetAnchorsPreset(LayoutPreset.FullRect);
        area.AddChild(_fit);
        _picture = new TextureRect
        {
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.Scale,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        _fit.AddChild(_picture);

        _message = UiStyle.Label(string.Empty, new LabelSettings { FontSize = UiStyle.RowSize, FontColor = UiStyle.Dim }, wrap: true);
        _message.SetAnchorsPreset(LayoutPreset.Center);
        _message.OffsetLeft = -420;
        _message.OffsetRight = 420;
        _message.OffsetTop = -40;
        _message.OffsetBottom = 40;
        _message.HorizontalAlignment = HorizontalAlignment.Center;
        _message.VerticalAlignment = VerticalAlignment.Center;
        area.AddChild(_message);

        // The caption: what it is, which of how many, the controls, and a video's progress.
        var bar = new PanelContainer { MouseFilter = MouseFilterEnum.Ignore };
        var barBox = new StyleBoxFlat { BgColor = new Color(0, 0, 0.03f, 0.6f), ContentMarginLeft = 24, ContentMarginRight = 24, ContentMarginTop = 10, ContentMarginBottom = 12 };
        bar.AddThemeStyleboxOverride("panel", barBox);
        bar.SetAnchorsPreset(LayoutPreset.BottomWide);
        bar.GrowVertical = GrowDirection.Begin;
        area.AddChild(bar);
        _caption = bar;
        var lines = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        lines.AddThemeConstantOverride("separation", 6);
        bar.AddChild(lines);
        var line = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        line.AddThemeConstantOverride("separation", 16);
        lines.AddChild(line);
        _name = UiStyle.Label(string.Empty, new LabelSettings { FontSize = UiStyle.RowSize, FontColor = UiStyle.Text, ShadowColor = UiStyle.Glow, ShadowSize = 6, ShadowOffset = Vector2.Zero });
        line.AddChild(_name);
        _place = UiStyle.Label(string.Empty, UiStyle.Detail);
        _place.SizeFlagsHorizontal = SizeFlags.ExpandFill;
        _place.VerticalAlignment = VerticalAlignment.Center;
        line.AddChild(_place);
        _controls = UiStyle.Label(string.Empty, UiStyle.Hint);
        _controls.VerticalAlignment = VerticalAlignment.Center;
        line.AddChild(_controls);

        // For the mouse: the pad and keyboard have B and Escape.
        var back = new Button { Text = "Back", FocusMode = FocusModeEnum.None };
        back.Pressed += () => GoBack();
        line.AddChild(back);
        _progress = new ProgressBar { ShowPercentage = false, CustomMinimumSize = new Vector2(0, 6), MaxValue = 1, MouseFilter = MouseFilterEnum.Ignore };
        lines.AddChild(_progress);

        _sound = new AudioStreamPlayer();
        AddChild(_sound);
        ShowItem(index);
    }

    /// <summary>A file to show: its media kind, its absolute path, and its name for people.</summary>
    public sealed record Item(string Kind, string Path, string Name);

    public override Control? DefaultFocus => null;

    public override bool Handle(NavCommand command)
    {
        _captionAge = 0;
        switch (command)
        {
            case NavCommand.Left or NavCommand.PageUp:
                if (_index > 0)
                {
                    ShowItem(_index - 1);
                }

                return true;
            case NavCommand.Right or NavCommand.PageDown:
                if (_index < _items.Count - 1)
                {
                    ShowItem(_index + 1);
                }

                return true;
            case NavCommand.First:
                ShowItem(0);
                return true;
            case NavCommand.Last:
                ShowItem(_items.Count - 1);
                return true;
            case NavCommand.Accept:
                PlayOrPause();
                return true;
            case NavCommand.Secondary:
                Close();
                return true;
            case NavCommand.Back or NavCommand.Menu:
                return false;
            default:
                // Nothing else here, and no focus to move.
                return true;
        }
    }

    public override void Tick(double delta)
    {
        base.Tick(delta);
        if (_playback is { } playback)
        {
            playback.Tick(delta);
            if (playback.Texture is { } frame && _picture.Texture != frame)
            {
                _picture.Texture = frame;
                _fit.Ratio = playback.Aspect > 0 ? playback.Aspect : 4f / 3;
                _message.Text = string.Empty;
                UpdateControls();
            }

            if (playback.Error is { } error && !ReferenceEquals(error, _shownError))
            {
                _shownError = error;
                _message.Text = $"This video can't be played: {error}.";
                _progress.Visible = false;
                UpdateControls();
            }

            var length = playback.Duration.TotalSeconds;
            _progress.Value = length > 0 ? Math.Min(1, playback.Position.TotalSeconds / length) : 0;
            if (playback.Ended && _controls.Text != EndedControls)
            {
                _controls.Text = EndedControls;
            }
        }

        // The caption stays while a video is paused or over, or something's wrong; otherwise it fades.
        var holding = _playback is { } p ? p.Paused || p.Ended || p.Error is not null : _picture.Texture is null;
        _captionAge = holding ? 0 : _captionAge + delta;
        var alpha = (float)Math.Clamp(1 - (_captionAge - CaptionSeconds) / CaptionFade, 0, 1);
        if (_caption.Modulate.A != alpha)
        {
            _caption.Modulate = new Color(1, 1, 1, alpha);
        }
    }

    public override void OnClosed() => Release();

    private const string EndedControls = "A  Play again     Left Right  Previous / next     B  Back";

    private void ShowItem(int index)
    {
        Release();
        _index = Math.Clamp(index, 0, _items.Count - 1);
        var item = _items[_index];
        var generation = ++_generation;
        Heading = item.Name;
        _name.Text = item.Name;
        _place.Text = _items.Count > 1 ? string.Create(CultureInfo.InvariantCulture, $"{_index + 1} of {_items.Count}") : string.Empty;
        _picture.Texture = null;
        _shownError = null;
        _captionAge = 0;
        _progress.Visible = item.Kind == MediaKinds.Video;
        _progress.Value = 0;
        UpdateControls();

        if (item.Kind == MediaKinds.Video)
        {
            if (_video is null)
            {
                _message.Text = "Videos can't be played on this system yet.";
                return;
            }

            _message.Text = "Loading…";
            _playback = new VideoPlayback(_video, item.Path, _sound);
            return;
        }

        // Decoded to fit the window's larger side, so it's sharp at 4K and no bigger than it can show.
        _message.Text = "Loading…";
        var window = DisplayServer.WindowGetSize();
        var side = Math.Max(256, Math.Max(window.X, window.Y));
        var decoder = _ui.Decoder;
        var queue = _ui.Queue;
        _ = Task.Run(() =>
        {
            var texture = Thumbnails.Load(item.Path, side, decoder, out var info);
            queue.Post(() =>
            {
                if (generation != _generation || !IsInstanceValid(this) || !IsInsideTree())
                {
                    texture?.Dispose();
                    return;
                }

                if (texture is null)
                {
                    _message.Text = info;
                    return;
                }

                _image = texture;
                _picture.Texture = texture;
                var size = texture.GetSize();
                _fit.Ratio = size.Y > 0 ? size.X / size.Y : 1;
                _message.Text = string.Empty;
                _place.Text = (_place.Text.Length > 0 ? _place.Text + "  ·  " : string.Empty) + info;
            });
        });
    }

    private void PlayOrPause()
    {
        if (_playback is not { } playback)
        {
            return;
        }

        if (playback.Ended)
        {
            // Again from the start: a new playback, so nothing of the last one's timing is left.
            ShowItem(_index);
            return;
        }

        playback.Paused = !playback.Paused;
        UpdateControls();
    }

    private void UpdateControls()
    {
        var video = _items[_index].Kind == MediaKinds.Video;
        var move = _items.Count > 1 ? "Left Right  Previous / next     " : string.Empty;
        _controls.Text = video && _video is not null && _shownError is null
            ? (_playback?.Paused == true ? "A  Play     " : "A  Pause     ") + move + "B  Back"
            : move + "B  Back";
    }

    /// <summary>Stops the video and lets go of the picture.</summary>
    private void Release()
    {
        _generation++;
        _picture.Texture = null;
        _playback?.Dispose();
        _playback = null;
        _image?.Dispose();
        _image = null;
    }
}
