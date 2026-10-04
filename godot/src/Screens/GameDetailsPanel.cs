using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Navigation;
using Launcher.App.Options;
using Launcher.App.Ui;
using Launcher.Core.Library;
using Launcher.Core.Media;

namespace Launcher.App.Screens;

/// <summary>
/// A game's details (Y on a game in the grid): its whole description, then every field of its metadata, its file name's
/// tags, its play history, how it launches and where its data came from; and a card for its video, its front cover, its
/// screenshot, then each of its other images.
/// A on a card shows it full size, or plays the video (<see cref="MediaViewer"/>); L3 (or F) adds or removes the
/// favourite; Y or B goes back. Read off the main thread before it opens; thumbnails are decoded on a worker, one after
/// another, as the game options' images are.
/// </summary>
public sealed partial class GameDetailsPanel : UiPanel
{
    private const int ThumbSide = 168;
    private const float ScrollStep = 60;

    private readonly UiContext _ui;
    private readonly AppServices _services;
    private readonly IVideoDecoder? _video;
    private readonly Action _favouriteChanged;
    private readonly PanelContainer _info;
    private readonly ScrollContainer _infoScroll;
    private readonly VBoxContainer _fields;
    private readonly Label _description;
    private readonly List<MediaCard> _cards = [];
    private readonly List<MediaViewer.Item> _items = [];
    private GameDetails _game;
    private bool _closed;
    private bool _saving;

    private GameDetailsPanel(UiContext ui, AppServices services, IVideoDecoder? video, Action favouriteChanged, Loaded loaded)
        : base(loaded.Game.Title, new Vector2(1220, 700))
    {
        _ui = ui;
        _services = services;
        _video = video;
        _favouriteChanged = favouriteChanged;
        _game = loaded.Game;
        var systemName = services.Config.FindSystem(_game.Key.SystemId)?.Name ?? _game.Key.SystemId;
        Subtitle = $"{systemName} · {Path.GetFileName(_game.RelPath)}";

        // The metadata and description: one focusable block that up and down scroll.
        _info = new PanelContainer { FocusMode = FocusModeEnum.All, SizeFlagsVertical = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Pass };
        _info.AddThemeStyleboxOverride("panel", InfoBox(false));
        _info.FocusEntered += () => _info.AddThemeStyleboxOverride("panel", InfoBox(true));
        _info.FocusExited += () => _info.AddThemeStyleboxOverride("panel", InfoBox(false));
        Body.AddChild(_info);
        _infoScroll = new ScrollContainer { HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled, FollowFocus = false };
        _info.AddChild(_infoScroll);
        var column = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        column.AddThemeConstantOverride("separation", 8);
        _infoScroll.AddChild(column);
        _description = UiStyle.Label(string.Empty, UiStyle.Body, wrap: true);
        _description.SizeFlagsHorizontal = SizeFlags.ExpandFill;
        column.AddChild(_description);
        column.AddChild(Section("Details"));
        _fields = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        column.AddChild(_fields);

        // The images and the video: a card each, along the bottom.
        Body.AddChild(Section("Images and videos"));
        var strip = new ScrollContainer
        {
            VerticalScrollMode = ScrollContainer.ScrollMode.Disabled,
            HorizontalScrollMode = ScrollContainer.ScrollMode.ShowNever,
            FollowFocus = true,
            CustomMinimumSize = new Vector2(0, MediaCard.CardHeight + 6),
        };
        Body.AddChild(strip);
        var cards = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        cards.AddThemeConstantOverride("separation", 12);
        strip.AddChild(cards);
        foreach (var row in Ordered(loaded.Media))
        {
            var file = services.Library.MediaPath(row.Media.Path);
            var index = _items.Count;
            var name = GameMediaPanel.SlotName(row.Kind);
            _items.Add(new MediaViewer.Item(row.Kind, file, name));
            var card = new MediaCard(name, row.Kind == MediaKinds.Video);
            card.Pressed += () => Layer.Push(new MediaViewer(_ui, _video, _items, index));
            cards.AddChild(card);
            _cards.Add(card);
        }

        if (_cards.Count == 0)
        {
            var none = UiStyle.Label("None yet. Scrape the game, or choose your own images: X on the game, then Images.", UiStyle.Detail);
            none.CustomMinimumSize = new Vector2(0, 40);
            cards.AddChild(none);
        }

        SetHints("A  View full size     Up Down  Scroll the details     L3 / F  Favourite     B / Y  Back");
        Show(loaded);
        LoadThumbnails();
    }

    public override Control? DefaultFocus => _cards.Count > 0 ? _cards[0] : _info;

    /// <summary>Reads the game, its play history and its media off the main thread, then opens its details. Main thread.</summary>
    public static void Open(UiContext ui, AppServices services, IVideoDecoder? video, long gameId, Action favouriteChanged)
    {
        _ = Task.Run(async () =>
        {
            Loaded? loaded = null;
            try
            {
                loaded = await LoadAsync(services, gameId).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                GD.PushError($"Details: couldn't read game {gameId}: {e.Message}");
            }

            ui.Queue.Post(() =>
            {
                if (loaded is not null && !ui.Layer.IsOpen)
                {
                    ui.Layer.Push(new GameDetailsPanel(ui, services, video, favouriteChanged, loaded));
                }
            });
        });
    }

    public override bool Handle(NavCommand command)
    {
        switch (command)
        {
            case NavCommand.Secondary:
                Close();
                return true;
            case NavCommand.Favourite:
                ToggleFavourite();
                return true;
            case NavCommand.Up or NavCommand.Down or NavCommand.PageUp or NavCommand.PageDown when GetViewport().GuiGetFocusOwner() == _info:
                return Scroll(command);
            default:
                return false;
        }
    }

    public override void OnClosed()
    {
        _closed = true;
        foreach (var card in _cards)
        {
            card.SetImage(null, null);
        }
    }

    /// <summary>Up and down scroll the details; down at the bottom goes on to the cards.</summary>
    private bool Scroll(NavCommand command)
    {
        var bar = _infoScroll.GetVScrollBar();
        var page = Math.Max(ScrollStep, _infoScroll.Size.Y - ScrollStep);
        var step = command switch
        {
            NavCommand.Up => -ScrollStep,
            NavCommand.Down => ScrollStep,
            NavCommand.PageUp => -page,
            _ => page,
        };
        var bottom = Math.Max(0, bar.MaxValue - bar.Page);
        if (step > 0 && _infoScroll.ScrollVertical >= bottom - 1)
        {
            return command == NavCommand.PageDown;
        }

        _infoScroll.ScrollVertical = (int)Math.Clamp(_infoScroll.ScrollVertical + step, 0, bottom);
        return true;
    }

    private void Show(Loaded loaded)
    {
        _game = loaded.Game;
        Heading = _game.Title;
        foreach (var child in _fields.GetChildren())
        {
            _fields.RemoveChild(child);
            child.QueueFree();
        }

        // Two columns of fields, filled down then across, as the overlay's were; then the file, which is long.
        var columns = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        columns.AddThemeConstantOverride("separation", 32);
        _fields.AddChild(columns);
        var half = (loaded.Fields.Count + 1) / 2;
        for (var part = 0; part < 2; part++)
        {
            var grid = new GridContainer { Columns = 2, SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
            grid.AddThemeConstantOverride("h_separation", 16);
            grid.AddThemeConstantOverride("v_separation", 4);
            columns.AddChild(grid);
            for (var i = part * half; i < Math.Min(loaded.Fields.Count, (part + 1) * half); i++)
            {
                AddField(grid, loaded.Fields[i].Label, loaded.Fields[i].Value);
            }
        }

        var file = new GridContainer { Columns = 2, MouseFilter = MouseFilterEnum.Ignore };
        file.AddThemeConstantOverride("h_separation", 16);
        _fields.AddChild(file);
        AddField(file, "File", _game.RomPath);

        var description = _game.Metadata?.Description;
        _description.Text = string.IsNullOrWhiteSpace(description) ? "No description yet." : description.Trim();
        _description.LabelSettings = string.IsNullOrWhiteSpace(description) ? UiStyle.Detail : UiStyle.Body;
    }

    private static void AddField(GridContainer grid, string label, string value)
    {
        var key = UiStyle.Label(label, KeyStyle);
        key.CustomMinimumSize = new Vector2(110, 0);
        key.VerticalAlignment = VerticalAlignment.Top;
        grid.AddChild(key);
        var text = UiStyle.Label(value, ValueStyle, wrap: true);
        text.SizeFlagsHorizontal = SizeFlags.ExpandFill;
        text.CustomMinimumSize = new Vector2(300, 0);
        grid.AddChild(text);
    }

    private static readonly LabelSettings KeyStyle = new() { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Dim };

    private static readonly LabelSettings ValueStyle = new() { FontSize = UiStyle.DetailSize + 1, FontColor = UiStyle.Text };

    private static Label Section(string text)
    {
        var label = UiStyle.Label(text.ToUpperInvariant(), UiStyle.Section);
        label.CustomMinimumSize = new Vector2(0, 26);
        label.VerticalAlignment = VerticalAlignment.Bottom;
        return label;
    }

    private static StyleBoxFlat InfoBox(bool focused)
    {
        var box = UiStyle.RowBox(focused ? new Color(0.1f, 0.15f, 0.4f, 0.45f) : new Color(0.06f, 0.09f, 0.25f, 0.3f), focused ? UiStyle.Accent : default, focused ? 2 : 0, focused ? 8 : 0);
        box.ContentMarginLeft = box.ContentMarginRight = 18;
        box.ContentMarginTop = box.ContentMarginBottom = 12;
        return box;
    }

    /// <summary>The video, the front cover and the screenshot first, then the other images in slot order; a per-game model isn't media to look at here.</summary>
    private static List<GameMediaInfo> Ordered(IReadOnlyList<GameMediaInfo> media)
    {
        var ordered = new List<GameMediaInfo>();
        foreach (var kind in (ReadOnlySpan<string>)[MediaKinds.Video, MediaKinds.Cover, MediaKinds.Screenshot])
        {
            ordered.AddRange(media.Where(m => m.Kind == kind));
        }

        foreach (var kind in MediaKinds.Images)
        {
            if (kind is not (MediaKinds.Cover or MediaKinds.Screenshot))
            {
                ordered.AddRange(media.Where(m => m.Kind == kind));
            }
        }

        return ordered;
    }

    private void LoadThumbnails()
    {
        var items = _items.ToArray();
        var decoder = _ui.Decoder;
        var video = _video;
        var queue = _ui.Queue;
        _ = Task.Run(() =>
        {
            for (var i = 0; i < items.Length && !Volatile.Read(ref _closed); i++)
            {
                var item = items[i];
                string info;
                var texture = item.Kind == MediaKinds.Video
                    ? Thumbnails.LoadVideo(item.Path, ThumbSide, video, out info)
                    : Thumbnails.Load(item.Path, ThumbSide, decoder, out info);
                var card = i;
                queue.Post(() =>
                {
                    if (_closed)
                    {
                        texture?.Dispose();
                    }
                    else
                    {
                        _cards[card].SetImage(texture, info);
                    }
                });
            }
        });
    }

    private void ToggleFavourite()
    {
        if (_saving)
        {
            return;
        }

        _saving = true;
        var favourite = !_game.IsFavourite;
        var (services, key, gameId) = (_services, _game.Key, _game.GameId);
        _ = Task.Run(async () =>
        {
            Loaded? loaded = null;
            string? failure = null;
            try
            {
                await services.Library.SetFavouriteAsync(key, favourite, CancellationToken.None).ConfigureAwait(false);
                loaded = await LoadAsync(services, gameId).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            _ui.Queue.Post(() =>
            {
                _favouriteChanged();
                if (_closed)
                {
                    return;
                }

                _saving = false;
                if (loaded is not null)
                {
                    Show(loaded);
                }

                ShowStatus(failure is not null ? $"Not saved: {failure}" : favourite ? "Added to your favourites." : "Taken out of your favourites.",
                    failure is null ? UiStyle.Good : UiStyle.Bad, 4);
            });
        });
    }

    private static async Task<Loaded?> LoadAsync(AppServices services, long gameId)
    {
        var library = services.Library;
        var game = await library.GetGameAsync(gameId, CancellationToken.None).ConfigureAwait(false);
        if (game is null)
        {
            return null;
        }

        var stats = await library.GetPlayStatsAsync(game.Key, CancellationToken.None).ConfigureAwait(false);
        var media = await library.GetGameMediaInfoAsync(gameId, CancellationToken.None).ConfigureAwait(false);
        return new Loaded(game, DetailsFormatter.GameFields(game, stats, services.Config, DateTimeOffset.Now), media);
    }

    /// <summary>What the panel shows, read and formatted off the main thread.</summary>
    private sealed record Loaded(GameDetails Game, IReadOnlyList<(string Label, string Value)> Fields, IReadOnlyList<GameMediaInfo> Media);

    /// <summary>One image or the video: its thumbnail, its kind, and its size (a video's length).</summary>
    private sealed partial class MediaCard : Button
    {
        public const int CardHeight = 214;

        private readonly TextureRect _image;
        private readonly Label _info;

        public MediaCard(string name, bool video)
        {
            FocusMode = FocusModeEnum.All;
            CustomMinimumSize = new Vector2(196, CardHeight);

            var margins = new MarginContainer { MouseFilter = MouseFilterEnum.Ignore };
            margins.SetAnchorsPreset(LayoutPreset.FullRect);
            foreach (var side in (ReadOnlySpan<string>)["margin_left", "margin_right", "margin_top", "margin_bottom"])
            {
                margins.AddThemeConstantOverride(side, 8);
            }

            AddChild(margins);
            var column = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
            column.AddThemeConstantOverride("separation", 2);
            margins.AddChild(column);

            var frame = new PanelContainer { CustomMinimumSize = new Vector2(0, ThumbSide - 20), SizeFlagsVertical = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
            frame.AddThemeStyleboxOverride("panel", UiStyle.RowBox(new Color(0.02f, 0.03f, 0.1f, 0.9f), new Color("#2E3D86"), 1));
            column.AddChild(frame);
            _image = new TextureRect
            {
                ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
                StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
                MouseFilter = MouseFilterEnum.Ignore,
            };
            frame.AddChild(_image);
            if (video)
            {
                frame.AddChild(new PlayBadge());
            }

            var title = UiStyle.Label(name, new LabelSettings { FontSize = UiStyle.DetailSize + 1, FontColor = UiStyle.Text });
            title.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            column.AddChild(title);
            _info = UiStyle.Label("…", new LabelSettings { FontSize = UiStyle.HintSize, FontColor = UiStyle.Dim });
            _info.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            column.AddChild(_info);
        }

        /// <summary>Main thread: the thumbnail (null clears it) and its caption.</summary>
        public void SetImage(ImageTexture? texture, string? info)
        {
            if (_image.Texture is { } old)
            {
                _image.Texture = null;
                old.Dispose();
            }

            _image.Texture = texture;
            _info.Text = info ?? string.Empty;
        }
    }

    /// <summary>A play triangle in a dark circle, over a video's thumbnail.</summary>
    private sealed partial class PlayBadge : Control
    {
        public PlayBadge()
        {
            MouseFilter = MouseFilterEnum.Ignore;
            SizeFlagsHorizontal = SizeFlags.ShrinkCenter;
            SizeFlagsVertical = SizeFlags.ShrinkCenter;
            CustomMinimumSize = new Vector2(44, 44);
        }

        public override void _Draw()
        {
            var centre = Size / 2;
            DrawCircle(centre, 22, new Color(0, 0, 0.05f, 0.6f));
            DrawColoredPolygon([centre + new Vector2(-7, -11), centre + new Vector2(12, 0), centre + new Vector2(-7, 11)], Colors.White);
        }
    }
}
