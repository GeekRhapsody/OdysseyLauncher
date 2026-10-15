using System;
using System.Diagnostics;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Theming;

namespace Launcher.App.Ui;

/// <summary>
/// Gives the menus the active theme's look (A6 Menus): its palette at once, through <see cref="UiStyle.Apply"/>, and
/// its font once loaded. A font is read and parsed on the thread pool (<see cref="FontFile.LoadDynamicFont"/>), never
/// on the main thread, and the menus keep the font they have until it's ready; then its glyphs at the menus' main
/// sizes are drawn once, a part a frame, so opening a menu doesn't rasterise them. A theme without a font costs none
/// of this.
/// </summary>
public static partial class MenuLook
{
    /// <summary>The menus' main sizes: rows, details and titles. Others rasterise when first drawn, as they always have.</summary>
    private static readonly int[] WarmSizes = [UiStyle.RowSize, UiStyle.DetailSize, UiStyle.TitleSize];

    private static MainThreadQueue? _queue;
    private static Node? _host;
    private static string? _font;
    private static FontFile? _loaded;

    /// <summary>Main thread, once at boot: where loaded fonts are handed back, and the node their warm-up runs under.</summary>
    public static void Init(MainThreadQueue queue, Node host)
    {
        _queue = queue;
        _host = host;
    }

    /// <summary>Main thread: the menus take <paramref name="menu"/>'s colours now, and its font when it has loaded.</summary>
    public static void Use(ThemeMenu menu)
    {
        var clock = Stopwatch.StartNew();
        UiStyle.Apply(MenuPalette.For(menu));
        GD.Print(FormattableString.Invariant($"Menus: {(menu.SetsColour ? "the theme's colours" : "the launcher's own colours")}, applied in {clock.Elapsed.TotalMilliseconds:0.00} ms."));
        if (menu.Font == _font)
        {
            return;
        }

        _font = menu.Font;
        if (menu.Font is not { } path)
        {
            UiStyle.SetFont(null);
            Release();
            return;
        }

        var queue = _queue;
        _ = Task.Run(() =>
        {
            if (!GodotWork.TryEnter())
            {
                return;
            }

            var loading = Stopwatch.StartNew();
            var font = new FontFile();
            Error error;
            try
            {
                error = font.LoadDynamicFont(path);
            }
            finally
            {
                GodotWork.Exit();
            }

            var loadMs = loading.Elapsed.TotalMilliseconds;
            queue?.Post(() => Loaded(path, error == Error.Ok ? font : null, error, loadMs));
        });
    }

    private static void Loaded(string path, FontFile? font, Error error, double loadMs)
    {
        if (path != _font)
        {
            // Another theme was chosen while it loaded.
            return;
        }

        if (font is null)
        {
            GD.PushWarning($"Menus: the font '{path}' couldn't be loaded ({error}); the default font is used.");
            UiStyle.SetFont(null);
            Release();
            return;
        }

        var clock = Stopwatch.StartNew();
        UiStyle.SetFont(font);
        Release();
        _loaded = font;
        GD.Print(FormattableString.Invariant($"Menus: the font '{path}' loaded in {loadMs:0.0} ms on a worker, applied in {clock.Elapsed.TotalMilliseconds:0.00} ms."));
        _host?.AddChild(new GlyphWarmUp(font));
    }

    /// <summary>
    /// Lets the previous font go now rather than at the next full collection: its glyphs' textures (a few MB per size)
    /// are freed once the labels that drew with it have laid out again.
    /// </summary>
    private static void Release()
    {
        _loaded?.Dispose();
        _loaded = null;
    }

    /// <summary>Draws printable ASCII in the theme's font at <see cref="WarmSizes"/>, a third of it a frame, then frees itself.</summary>
    private sealed partial class GlyphWarmUp(Font font) : Node
    {
        private const int Chunks = 3;
        private SubViewport? _viewport;
        private int _step;

        public override void _Process(double delta)
        {
            _viewport?.QueueFree();
            _viewport = null;
            if (_step >= WarmSizes.Length * Chunks || UiStyle.Font != font)
            {
                QueueFree();
                return;
            }

            var size = WarmSizes[_step / Chunks];
            var chunk = _step % Chunks;
            _step++;
            var text = new System.Text.StringBuilder(32);
            for (var c = 0x20 + (chunk * 32); c < Math.Min(0x7F, 0x20 + ((chunk + 1) * 32)); c++)
            {
                text.Append((char)c);
            }

            _viewport = new SubViewport { Size = new Vector2I(16, 16), RenderTargetUpdateMode = SubViewport.UpdateMode.Once, TransparentBg = true, Disable3D = true };
            _viewport.AddChild(new Label { Text = text.ToString(), Theme = UiStyle.Theme, LabelSettings = new LabelSettings { FontSize = size } });
            AddChild(_viewport);
        }
    }
}
