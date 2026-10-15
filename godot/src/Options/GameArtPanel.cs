using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Scraping;

namespace Launcher.App.Options;

/// <summary>
/// The art chooser (2026-10-15): after "scrape this game" chose a game whose provider has several images of a wanted
/// kind (SteamGridDB's community art), a step per kind (front cover, logo, hero art), each a grid of its images, at most
/// <see cref="ScrapeService.ArtChoiceLimit"/>, the one a scrape would take first. When the game has a file of that kind,
/// "Keep this one" (its image now) comes first and has the focus. A takes the focused tile and goes on to the next kind; after
/// the last, the game is scraped with the chosen game, and each chosen image replaces the game's file of its kind
/// (<see cref="ScrapeService.ScrapeGameWithMatchAsync(GameKey, string, string, IReadOnlyList{ArtChoice}, CancellationToken)"/>).
/// B goes back a step, and from the first back to the match list. Thumbnails are downloaded small and decoded off the
/// main thread, each step's from the top, two at a time, and kept while the panel is open.
/// </summary>
public sealed partial class GameArtPanel : UiPanel
{
    /// <summary>Thumbnails downloaded at once.</summary>
    private const int ThumbsAtOnce = 2;

    private readonly ItemOptions _options;
    private readonly GameDetails _game;
    private readonly string _providerName;
    private readonly IReadOnlyList<Step> _steps;
    private readonly IReadOnlyDictionary<string, string> _current;
    private readonly Action<IReadOnlyList<ArtChoice>> _done;
    private readonly bool _madeUp;

    /// <summary>Each step's pick: an index into its options, or -1 to keep the current file. Unset until it's made.</summary>
    private readonly int?[] _picks;
    private readonly Dictionary<Option, Thumb> _thumbs = [];
    private readonly Dictionary<string, Thumb> _currentThumbs = new(StringComparer.Ordinal);
    private readonly Dictionary<object, Tile> _tiles = [];
    private readonly ScrollContainer _scroll;
    private readonly GridContainer _grid;
    private Control? _focusTarget;
    private int _step;
    private int _generation;
    private CancellationTokenSource? _cancel;
    private bool _closed;

    /// <param name="current">Each kind the game has a file of now, and the file's absolute path.</param>
    /// <param name="done">Gets the chosen images (none for a kind kept) once the last step is taken; the panel has closed by then.</param>
    public GameArtPanel(ItemOptions options, GameDetails game, ArtChoices choices, IReadOnlyDictionary<string, string> current, Action<IReadOnlyList<ArtChoice>> done)
        : this(options, game, ProviderName(choices.Provider), StepsOf(choices), current, done, madeUp: false)
    {
    }

    private GameArtPanel(ItemOptions options, GameDetails game, string providerName, IReadOnlyList<Step> steps, IReadOnlyDictionary<string, string> current,
        Action<IReadOnlyList<ArtChoice>> done, bool madeUp)
        : base(string.Empty, new Vector2(1180, 720))
    {
        _options = options;
        _game = game;
        _providerName = providerName;
        _steps = steps;
        _current = current;
        _done = done;
        _madeUp = madeUp;
        _picks = new int?[steps.Count];

        _scroll = new ScrollContainer
        {
            SizeFlagsVertical = SizeFlags.ExpandFill,
            HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled,
            FollowFocus = true,
            MouseFilter = MouseFilterEnum.Pass,
        };
        Body.AddChild(_scroll);
        var margins = new MarginContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        foreach (var side in (ReadOnlySpan<string>)["margin_left", "margin_right", "margin_top", "margin_bottom"])
        {
            // Room for the focused tile's glow.
            margins.AddThemeConstantOverride(side, 10);
        }

        _scroll.AddChild(margins);
        _grid = new GridContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        _grid.AddThemeConstantOverride("h_separation", 12);
        _grid.AddThemeConstantOverride("v_separation", 12);
        margins.AddChild(_grid);
        SetHints("A  Use this image     B  Back");
        if (madeUp)
        {
            MakeUpThumbs();
        }

        Build();
    }

    public override Control? DefaultFocus => _focusTarget ?? base.DefaultFocus;

    /// <summary>
    /// <c>--open=art</c>: the chooser over made-up images for <paramref name="game"/> (twelve covers, four logos, two heroes,
    /// and a current cover to keep), with made-up thumbnails. Nothing is downloaded, and the last step only logs.
    /// </summary>
    public static GameArtPanel MadeUp(ItemOptions options, GameDetails game)
    {
        static IReadOnlyList<Option> Made(int count, int width, int height, string style) =>
            Enumerable.Range(0, count).Select(i => new Option(null, width, height, i % 3 == 1 ? "blurred" : style)).ToList();

        var steps = new List<Step>
        {
            new(MediaKinds.Cover, Made(12, 660, 930, "alternate")),
            new(MediaKinds.Logo, Made(4, 800, 310, "official")),
            new(MediaKinds.Hero, Made(2, 1920, 620, "alternate")),
        };
        var current = new Dictionary<string, string>(StringComparer.Ordinal) { [MediaKinds.Cover] = "made up" };
        return new GameArtPanel(options, game, "SteamGridDB", steps, current, _ => { }, madeUp: true);
    }

    public override void GoBack()
    {
        if (_step == 0)
        {
            Close();
            return;
        }

        _step--;
        Build();
    }

    public override void OnClosed()
    {
        _closed = true;
        _cancel?.Cancel();
        _generation++;
        foreach (var thumb in _thumbs.Values.Concat(_currentThumbs.Values))
        {
            thumb.Texture?.Dispose();
        }

        _thumbs.Clear();
        _currentThumbs.Clear();
    }

    private static IReadOnlyList<Step> StepsOf(ArtChoices choices) =>
        choices.Kinds.Select(k => new Step(k.Kind, k.Choices.Select(c => new Option(c, c.Width, c.Height, c.Style)).ToList())).ToList();

    private static string ProviderName(string provider) => provider switch
    {
        ScraperIds.SteamGridDb => "SteamGridDB",
        ScraperIds.ScreenScraper => "ScreenScraper",
        ScraperIds.Igdb => "IGDB",
        ScraperIds.Steam => "the Steam store",
        _ => provider,
    };

    // ---- A step ---------------------------------------------------------------------------------------

    /// <summary>Main thread: the current step's tiles, the focus on its pick, else on keeping the current file, else on the first image.</summary>
    private void Build()
    {
        var step = _steps[_step];
        var look = Look.Of(step.Kind, _current.ContainsKey(step.Kind));
        var name = GameMediaPanel.SlotName(step.Kind);
        Heading = $"{name} for {_game.Title}";
        Subtitle = string.Create(CultureInfo.InvariantCulture,
            $"Step {_step + 1} of {_steps.Count} · {step.Options.Count} from {_providerName}. The one you choose replaces the game's {name.ToLowerInvariant()}");

        foreach (var child in _grid.GetChildren())
        {
            _grid.RemoveChild(child);
            child.QueueFree();
        }

        _tiles.Clear();
        _grid.Columns = look.Columns;
        _focusTarget = null;
        var pick = _picks[_step];
        if (_current.TryGetValue(step.Kind, out var currentFile))
        {
            var keep = AddTile(look, "Keep this one", "Yours now", -1, pick);
            _tiles[step.Kind] = keep;
            if (_currentThumbs.TryGetValue(step.Kind, out var thumb))
            {
                keep.SetImage(thumb.Texture, thumb.Loaded ? thumb.Caption : "…");
            }
            else if (!_madeUp)
            {
                LoadCurrent(step.Kind, currentFile, look);
            }

            _focusTarget = pick is null or -1 ? keep : null;
        }

        for (var i = 0; i < step.Options.Count; i++)
        {
            var option = step.Options[i];
            // The number and size above, the style below: short lines, for the narrow tiles beside "Keep this one".
            var title = option.Width > 0 && option.Height > 0
                ? string.Create(CultureInfo.InvariantCulture, $"{i + 1} · {option.Width} × {option.Height}")
                : string.Create(CultureInfo.InvariantCulture, $"{i + 1}");
            var tile = AddTile(look, title, option.Style ?? string.Empty, i, pick);
            _tiles[option] = tile;
            if (_thumbs.TryGetValue(option, out var thumb))
            {
                tile.SetImage(thumb.Texture, thumb.Loaded ? thumb.Caption : "…");
            }
            else
            {
                tile.SetImage(null, "…");
            }

            if (_focusTarget is null && (pick is null || pick == i))
            {
                _focusTarget = tile;
            }
        }

        _scroll.ScrollVertical = 0;
        if (IsInsideTree())
        {
            _focusTarget?.CallDeferred(Control.MethodName.GrabFocus);
        }

        LoadThumbs(step, look);
    }

    private Tile AddTile(Look look, string title, string detail, int index, int? pick)
    {
        var tile = new Tile(look, title, detail, chosen: pick == index);
        tile.Pressed += () => Pick(index);
        _grid.AddChild(tile);
        return tile;
    }

    /// <summary>A tile taken: on to the next kind, or, after the last, the scrape with every choice.</summary>
    private void Pick(int index)
    {
        if (_closed)
        {
            return;
        }

        _picks[_step] = index;
        if (_step + 1 < _steps.Count)
        {
            _step++;
            Build();
            return;
        }

        var chosen = new List<ArtChoice>();
        var log = new List<string>();
        for (var i = 0; i < _steps.Count; i++)
        {
            var p = _picks[i] ?? -1;
            log.Add(p < 0 ? $"{_steps[i].Kind} kept" : string.Create(CultureInfo.InvariantCulture, $"{_steps[i].Kind} {p + 1}"));
            if (p >= 0 && _steps[i].Options[p].Choice is { } choice)
            {
                chosen.Add(choice);
            }
        }

        GD.Print($"Art: {_game.Key.SystemId}/{_game.Key.PathKey}: {string.Join(", ", log)}{(_madeUp ? " (made up: nothing is scraped)" : string.Empty)}");
        Close();
        _done(chosen);
    }

    // ---- Thumbnails -----------------------------------------------------------------------------------

    /// <summary>Main thread: downloads the step's thumbnails not loaded yet, from the top, on a worker.</summary>
    private void LoadThumbs(Step step, Look look)
    {
        _cancel?.Cancel();
        if (_madeUp)
        {
            return;
        }

        var cancel = new CancellationTokenSource();
        _cancel = cancel;
        var generation = ++_generation;
        foreach (var key in _thumbs.Where(t => !t.Value.Loaded).Select(t => t.Key).ToList())
        {
            _thumbs.Remove(key);
        }

        var wanted = new List<Option>();
        foreach (var option in step.Options)
        {
            if (option.Choice is not null && !_thumbs.ContainsKey(option))
            {
                _thumbs[option] = new Thumb();
                wanted.Add(option);
            }
        }

        if (wanted.Count == 0)
        {
            return;
        }

        var jobs = _options.Jobs;
        var queue = _options.Ui.Queue;
        var fit = look.Decode;
        _ = Task.Run(async () =>
        {
            try
            {
                var parallel = new ParallelOptions { MaxDegreeOfParallelism = ThumbsAtOnce, CancellationToken = cancel.Token };
                await Parallel.ForEachAsync(wanted, parallel, async (option, token) =>
                {
                    ImageTexture? texture;
                    string? caption;
                    try
                    {
                        var bytes = await jobs.GetArtThumbAsync(option.Choice!, token).ConfigureAwait(false);
                        texture = bytes is null ? null : Thumbnails.FromBytes(bytes, fit);
                        caption = texture is null ? "No image" : null;
                    }
                    catch (OperationCanceledException)
                    {
                        return;
                    }
                    catch (Exception e)
                    {
                        GD.PushWarning($"Art: {option.Choice}: {e.Message}");
                        texture = null;
                        caption = "Not loaded";
                    }

                    queue.Post(() => ThumbLoaded(generation, option, texture, caption));
                }).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                // Another step, or the panel closed.
            }
        });
    }

    /// <summary>Main thread: a thumbnail downloaded and decoded (null: none, with why in <paramref name="caption"/>).</summary>
    private void ThumbLoaded(int generation, Option option, ImageTexture? texture, string? caption)
    {
        if (generation != _generation || _closed || !_thumbs.TryGetValue(option, out var thumb) || thumb.Loaded)
        {
            texture?.Dispose();
            return;
        }

        thumb.Loaded = true;
        thumb.Texture = texture;
        thumb.Caption = caption;
        if (_tiles.TryGetValue(option, out var tile) && IsInstanceValid(tile))
        {
            tile.SetImage(texture, caption);
        }
    }

    /// <summary>Main thread: decodes the game's own file of <paramref name="kind"/> on a worker, for the tile that keeps it.</summary>
    private void LoadCurrent(string kind, string file, Look look)
    {
        var thumb = new Thumb();
        _currentThumbs[kind] = thumb;
        var decoder = _options.Ui.Decoder;
        var queue = _options.Ui.Queue;
        var side = Math.Max(look.Decode.X, look.Decode.Y);
        _ = Task.Run(() =>
        {
            var texture = Thumbnails.Load(file, side, decoder, out _);
            queue.Post(() =>
            {
                if (_closed)
                {
                    texture?.Dispose();
                    return;
                }

                thumb.Loaded = true;
                thumb.Texture = texture;
                thumb.Caption = texture is null ? "Not loaded" : null;
                if (_tiles.TryGetValue(kind, out var tile) && IsInstanceValid(tile))
                {
                    tile.SetImage(texture, thumb.Caption);
                }
            });
        });
    }

    /// <summary><c>--open=art</c>: a gradient for each made-up image, in a colour of each one's own, and grey for the current cover.</summary>
    private void MakeUpThumbs()
    {
        for (var s = 0; s < _steps.Count; s++)
        {
            var look = Look.Of(_steps[s].Kind, _current.ContainsKey(_steps[s].Kind));
            for (var i = 0; i < _steps[s].Options.Count; i++)
            {
                var hue = ((s * 0.31f) + (i * 0.083f)) % 1f;
                _thumbs[_steps[s].Options[i]] = new Thumb { Loaded = true, Texture = Gradient(look.Frame, hue, 0.6f) };
            }

            if (_current.ContainsKey(_steps[s].Kind))
            {
                _currentThumbs[_steps[s].Kind] = new Thumb { Loaded = true, Texture = Gradient(look.Frame, 0, 0) };
            }
        }

        static ImageTexture Gradient(Vector2 size, float hue, float saturation)
        {
            var image = Image.CreateEmpty((int)size.X / 2, (int)size.Y / 2, false, Image.Format.Rgba8);
            for (var y = 0; y < image.GetHeight(); y++)
            {
                image.FillRect(new Rect2I(0, y, image.GetWidth(), 1), Color.FromHsv(hue, saturation, 0.9f - (0.5f * y / image.GetHeight())));
            }

            var texture = ImageTexture.CreateFromImage(image);
            image.Dispose();
            return texture;
        }
    }

    // ---- Types ----------------------------------------------------------------------------------------

    /// <summary>One image to choose; <see cref="Choice"/> is null for a made-up one (<c>--open=art</c>). Compared by reference: made-up ones are alike.</summary>
    private sealed class Option(ArtChoice? choice, int width, int height, string? style)
    {
        public ArtChoice? Choice { get; } = choice;

        public int Width { get; } = width;

        public int Height { get; } = height;

        public string? Style { get; } = style;
    }

    private sealed record Step(string Kind, IReadOnlyList<Option> Options);

    /// <summary>
    /// How a kind's tiles are laid out: covers are tall, logos and heroes wide. The covers fill two rows: twelve in six
    /// columns, or seven narrower ones when "Keep this one" makes thirteen.
    /// </summary>
    private readonly record struct Look(int Columns, Vector2 Frame)
    {
        /// <summary>What a thumbnail is scaled down to fit when decoded: twice its frame, for a window larger than the UI's 1280×800.</summary>
        public Vector2I Decode => new((int)Frame.X * 2, (int)Frame.Y * 2);

        public static Look Of(string kind, bool keep) => kind switch
        {
            MediaKinds.Cover when keep => new Look(7, new Vector2(124, 175)),
            MediaKinds.Cover => new Look(6, new Vector2(144, 203)),
            MediaKinds.Hero => new Look(3, new Vector2(334, 108)),
            _ => new Look(4, new Vector2(244, 110)),
        };
    }

    /// <summary>A thumbnail: loading, loaded (its texture), or none (and why).</summary>
    private sealed class Thumb
    {
        public bool Loaded { get; set; }

        public ImageTexture? Texture { get; set; }

        public string? Caption { get; set; }
    }

    /// <summary>One image's tile: its thumbnail (or why there's none), its number and its size and style.</summary>
    private sealed partial class Tile : Button
    {
        private readonly TextureRect _image;
        private readonly Label _caption;

        public Tile(Look look, string title, string detail, bool chosen)
        {
            FocusMode = FocusModeEnum.All;
            SizeFlagsHorizontal = SizeFlags.ExpandFill;
            CustomMinimumSize = new Vector2(look.Frame.X + 16, look.Frame.Y + 58);

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

            var frame = new PanelContainer { CustomMinimumSize = look.Frame, MouseFilter = MouseFilterEnum.Ignore };
            frame.AddThemeStyleboxOverride("panel", UiStyle.FrameBox());
            column.AddChild(frame);
            _image = new TextureRect
            {
                ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
                StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
                MouseFilter = MouseFilterEnum.Ignore,
            };
            frame.AddChild(_image);
            _caption = UiStyle.Label(string.Empty, new LabelSettings { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Faint });
            _caption.HorizontalAlignment = HorizontalAlignment.Center;
            _caption.VerticalAlignment = VerticalAlignment.Center;
            frame.AddChild(_caption);

            var heading = UiStyle.Label(title, new LabelSettings { FontSize = UiStyle.RowSize - 4, FontColor = chosen ? UiStyle.Good : UiStyle.Text });
            heading.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            column.AddChild(heading);
            var info = UiStyle.Label(chosen ? "Your choice" : detail,
                new LabelSettings { FontSize = UiStyle.DetailSize - 2, FontColor = chosen ? UiStyle.Good : UiStyle.Dim });
            info.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
            column.AddChild(info);
        }

        /// <summary>Main thread: the thumbnail, or none with a caption saying why. The panel owns the texture.</summary>
        public void SetImage(ImageTexture? texture, string? caption)
        {
            _image.Texture = texture;
            _caption.Text = texture is null ? caption ?? string.Empty : string.Empty;
        }
    }
}
