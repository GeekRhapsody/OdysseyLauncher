using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Files;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Theming;

namespace Launcher.App.Options;

/// <summary>
/// A game's images (M7 part 2): a card per media slot (front cover, back cover, spine, box texture, disc or cartridge
/// label, screenshot, logo, hero art), each with its current image, its file in the media folder (or none), and whether
/// the game's model shows that slot. A chooses the user's own image with the image picker, replacing the slot's file;
/// Y deletes the slot's file, scraped or not, so a scrape can fill it again. The media folder doesn't say where a file
/// came from (A4). The grid rebinds the game's slots as soon as a change is indexed (the library's MediaChanged),
/// keeping its model.
/// </summary>
public sealed partial class GameMediaPanel : UiPanel
{
    private const int ThumbSide = 150;

    private readonly ItemOptions _options;
    private readonly GameDetails _game;
    private readonly SlotCard[] _cards = new SlotCard[MediaSlots.Count];
    private IReadOnlyList<GameMediaInfo> _rows = [];
    private int _generation;
    private bool _closed;

    public GameMediaPanel(ItemOptions options, GameDetails game)
        : base($"Images for {game.Title}", new Vector2(1180, 720))
    {
        _options = options;
        _game = game;
        Subtitle = "Choose your own for any slot. Scraping only fills empty slots, so it never replaces one";

        var grid = new GridContainer { Columns = 4, SizeFlagsVertical = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        grid.AddThemeConstantOverride("h_separation", 12);
        grid.AddThemeConstantOverride("v_separation", 12);
        Body.AddChild(grid);
        var shown = ShownSlots();
        for (var slot = 0; slot < MediaSlots.Count; slot++)
        {
            var kind = MediaSlots.Names[slot];
            var card = new SlotCard(kind, shown[slot]);
            card.Pressed += () => Pick(kind);
            grid.AddChild(card);
            _cards[slot] = card;
        }

        SetHints("A  Choose an image     Y  Remove it     B  Back");
        _options.Library.MediaChanged += OnMediaChanged;
        Reload();
    }

    /// <summary>What a slot is, for people: <c>box_texture</c> is "Box texture".</summary>
    public static string SlotName(string kind) => kind switch
    {
        MediaKinds.Cover => "Front cover",
        MediaKinds.Back => "Back cover",
        MediaKinds.Spine => "Spine",
        MediaKinds.BoxTexture => "Box texture",
        MediaKinds.Label => "Disc or cartridge label",
        MediaKinds.Screenshot => "Screenshot",
        MediaKinds.Logo => "Logo",
        MediaKinds.Hero => "Hero art",
        MediaKinds.Video => "Video",
        MediaKinds.Manual => "Manual",
        _ => kind,
    };

    public override void OnClosed()
    {
        _closed = true;
        _options.Library.MediaChanged -= OnMediaChanged;
        foreach (var card in _cards)
        {
            card.SetImage(null, null);
        }
    }

    public override bool Handle(NavCommand command)
    {
        if (command != NavCommand.Secondary)
        {
            return false;
        }

        var focused = GetViewport().GuiGetFocusOwner();
        foreach (var card in _cards)
        {
            if (card == focused)
            {
                Remove(card.Kind);
                return true;
            }
        }

        return false;
    }

    /// <summary>Which slots its system's template shows (a game with its own model may show others).</summary>
    private bool[] ShownSlots()
    {
        var shown = new bool[MediaSlots.Count];
        var theme = _options.Theme;
        var templates = theme.GameTemplates;
        if (templates.Count == 0)
        {
            return shown;
        }

        var template = templates[Math.Clamp(theme.GameTemplateOf(_game.Key.SystemId), 0, templates.Count - 1)];
        for (var slot = 0; slot < shown.Length; slot++)
        {
            shown[slot] = template.HasSlot(slot);
        }

        return shown;
    }

    /// <summary>A worker thread: the library's media changed (an image set or removed here, a scrape, a clear).</summary>
    private void OnMediaChanged(object? sender, MediaChangedEventArgs e)
    {
        if (e.Games is null || e.Games.Contains(_game.Key))
        {
            _options.Ui.Queue.Post(() =>
            {
                if (!_closed)
                {
                    Reload();
                }
            });
        }
    }

    /// <summary>Reads the game's media rows, then decodes a thumbnail of each on a worker, one after another.</summary>
    private void Reload()
    {
        var generation = ++_generation;
        var options = _options;
        var gameId = _game.GameId;
        var library = options.Settings.Services.Library;
        var decoder = options.Ui.Decoder;
        _ = Task.Run(async () =>
        {
            IReadOnlyList<GameMediaInfo> rows;
            try
            {
                rows = await options.Library.GetGameMediaInfoAsync(gameId, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                GD.PushWarning($"Options: couldn't read the game's images: {e.Message}");
                return;
            }

            options.Ui.Queue.Post(() =>
            {
                if (generation == _generation && !_closed)
                {
                    _rows = rows;
                    ShowSources();
                }
            });

            foreach (var row in rows)
            {
                if (MediaSlots.IndexOf(row.Kind) is not (var slot and >= 0) || Volatile.Read(ref _generation) != generation)
                {
                    continue;
                }

                var file = library.MediaPath(row.Media.Path);
                var texture = Thumbnails.Load(file, ThumbSide, decoder, out var info);
                options.Ui.Queue.Post(() =>
                {
                    if (generation == _generation && !_closed)
                    {
                        _cards[slot].SetImage(texture, info);
                    }
                    else
                    {
                        texture?.Dispose();
                    }
                });
            }
        });
    }

    private void ShowSources()
    {
        var found = new GameMediaInfo?[MediaSlots.Count];
        foreach (var row in _rows)
        {
            if (MediaSlots.IndexOf(row.Kind) is var slot and >= 0)
            {
                found[slot] = row;
            }
        }

        for (var slot = 0; slot < _cards.Length; slot++)
        {
            _cards[slot].SetSource(found[slot]);
        }
    }

    private void Pick(string kind)
    {
        FilePicker.Open(_options.Ui, new PickerRequest(
            $"{SlotName(kind)} for {_game.Title}",
            PickerMode.File,
            PickerUses.Image,
            file => Set(kind, file),
            Filter: FileFilter.Images,
            Subtitle: "A PNG, JPEG or WebP image. It's copied into the media folder, so the original can go",
            Thumbnails: true));
    }

    private void Set(string kind, string file)
    {
        ShowStatus($"Adding the {SlotName(kind).ToLowerInvariant()}…", UiStyle.Dim);
        var options = _options;
        var key = _game.Key;
        _ = Task.Run(async () =>
        {
            UserArtResult result;
            try
            {
                result = await options.Art.SetAsync(key, kind, file, CancellationToken.None).ConfigureAwait(false);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                result = new UserArtResult(UserArtStatus.NotAnImage, null, Message: e.Message);
            }

            options.Ui.Queue.Post(() =>
            {
                GD.Print($"Options: {key.SystemId}/{key.PathKey} {kind}: {result.Status}{(result.Path is null ? string.Empty : $" ({result.Path})")}.");
                if (_closed)
                {
                    return;
                }

                if (result.Status == UserArtStatus.Set)
                {
                    ShowStatus($"{SlotName(kind)}: yours now.", UiStyle.Good, 5);
                }
                else
                {
                    ShowStatus(null);
                    ConfirmDialog.Tell(Layer, "Image not used", result.Message ?? "It couldn't be used.");
                }

                Reload();
            });
        });
    }

    private void Remove(string kind)
    {
        var slot = MediaSlots.IndexOf(kind);
        GameMediaInfo? row = null;
        foreach (var r in _rows)
        {
            if (r.Kind == kind)
            {
                row = r;
            }
        }

        if (row is null)
        {
            ShowStatus($"There's no {SlotName(kind).ToLowerInvariant()} to remove.", UiStyle.Dim, 5);
            return;
        }

        var options = _options;
        var key = _game.Key;
        ConfirmDialog.Ask(Layer, $"Remove your {SlotName(kind).ToLowerInvariant()}?",
            $"{row.Media.Path} is deleted from the media folder. The slot stays empty until the game is scraped again.",
            "Remove it", "Keep it", yes =>
            {
                if (!yes)
                {
                    return;
                }

                _ = Task.Run(async () =>
                {
                    var result = await options.Art.RemoveAsync(key, kind, CancellationToken.None).ConfigureAwait(false);
                    options.Ui.Queue.Post(() =>
                    {
                        if (_closed)
                        {
                            return;
                        }

                        ShowStatus(result.Status switch
                        {
                            UserArtStatus.Removed => "Removed. Scraping the game can fill the slot again.",
                            _ => "There was nothing to remove.",
                        }, result.Status == UserArtStatus.Removed ? UiStyle.Good : UiStyle.Warning, 6);
                        _cards[slot].SetImage(null, null);
                        Reload();
                    });
                });
            }, destructive: true);
    }

    /// <summary>One media slot: its image, its name, where the image came from, and its size.</summary>
    private sealed partial class SlotCard : Button
    {
        private readonly TextureRect _image;
        private readonly Label _source;
        private readonly Label _info;
        private readonly LabelSettings _sourceSettings = new() { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Dim };

        public SlotCard(string kind, bool onModel)
        {
            Kind = kind;
            Name = "Slot_" + kind;
            FocusMode = FocusModeEnum.All;
            CustomMinimumSize = new Vector2(268, 268);
            SizeFlagsHorizontal = SizeFlags.ExpandFill;

            var margins = new MarginContainer { MouseFilter = MouseFilterEnum.Ignore };
            margins.SetAnchorsPreset(LayoutPreset.FullRect);
            foreach (var side in (ReadOnlySpan<string>)["margin_left", "margin_right", "margin_top", "margin_bottom"])
            {
                margins.AddThemeConstantOverride(side, 10);
            }

            AddChild(margins);
            var column = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
            column.AddThemeConstantOverride("separation", 2);
            margins.AddChild(column);

            var frame = new PanelContainer { CustomMinimumSize = new Vector2(0, ThumbSide + 8), MouseFilter = MouseFilterEnum.Ignore };
            frame.AddThemeStyleboxOverride("panel", UiStyle.RowBox(new Color(0.02f, 0.03f, 0.1f, 0.9f), new Color("#2E3D86"), 1));
            column.AddChild(frame);
            _image = new TextureRect
            {
                ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
                StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
                MouseFilter = MouseFilterEnum.Ignore,
            };
            frame.AddChild(_image);

            var title = UiStyle.Label(SlotName(kind), new LabelSettings { FontSize = UiStyle.RowSize - 2, FontColor = UiStyle.Text });
            title.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            column.AddChild(title);
            _source = UiStyle.Label("…", _sourceSettings);
            _source.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            column.AddChild(_source);
            _info = UiStyle.Label(onModel ? "On its model" : "Not on its model", new LabelSettings { FontSize = UiStyle.DetailSize - 2, FontColor = onModel ? UiStyle.Accent : UiStyle.Faint });
            _info.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            column.AddChild(_info);
            OnModel = onModel;
        }

        public string Kind { get; }

        private bool OnModel { get; }

        public void SetSource(GameMediaInfo? row)
        {
            if (row is null)
            {
                _source.Text = "None";
                _sourceSettings.FontColor = UiStyle.Faint;
                SetImage(null, null);
                return;
            }

            _source.Text = Path.GetFileName(row.Media.Path);
            _sourceSettings.FontColor = UiStyle.Dim;
        }

        /// <summary>Main thread: the thumbnail (null clears it) and its size.</summary>
        public void SetImage(ImageTexture? texture, string? info)
        {
            if (_image.Texture is { } old)
            {
                _image.Texture = null;
                old.Dispose();
            }

            _image.Texture = texture;
            _info.Text = (OnModel ? "On its model" : "Not on its model") + (string.IsNullOrEmpty(info) ? string.Empty : " · " + info);
        }
    }
}
