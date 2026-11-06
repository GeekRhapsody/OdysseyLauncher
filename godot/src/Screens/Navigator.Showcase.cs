using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Ui;
using Launcher.Core.Library;
using Launcher.Core.Media;

namespace Launcher.App.Screens;

/// <summary>The showcase layout's images (A1 Grid, "Showcase"): read for the focused game when the focus rests.</summary>
public sealed partial class Navigator
{
    // The longest side the images are decoded at (they're never enlarged): a 1080p screen's width for the hero art, which
    // fills the screen, and about what the logo and the screenshot take up on one.
    private const int HeroSide = 1920;
    private const int LogoSide = 640;
    private const int ScreenshotSide = 1280;

    private static readonly string[] ShowcaseKinds = [MediaKinds.Logo, MediaKinds.Screenshot, MediaKinds.Hero];

    private IImageDecoder? _showcaseDecoder;

    /// <summary>Worker thread: decodes the game's images and hands them to the panel, stopping if the focus moves on.</summary>
    private async Task LoadShowcaseArtAsync(long key, IImageDecoder decoder, CancellationToken token)
    {
        var library = _services.Library;
        var rows = await library.GetGameMediaAsync([key], ShowcaseKinds, token).ConfigureAwait(false);
        if (Volatile.Read(ref _focusKey) != key)
        {
            return;
        }

        var art = new ShowcaseArt(
            key,
            Decode(rows, MediaKinds.Logo, LogoSide, decoder),
            Decode(rows, MediaKinds.Screenshot, ScreenshotSide, decoder),
            Decode(rows, MediaKinds.Hero, HeroSide, decoder));
        _queue.Post(() => _overlay.Showcase.ShowArt(art, _focusKey));
    }

    private ImageTexture? Decode(IReadOnlyList<GameMediaRow> rows, string kind, int side, IImageDecoder decoder)
    {
        foreach (var row in rows)
        {
            if (row.Kind != kind)
            {
                continue;
            }

            var texture = Thumbnails.Load(_services.Library.MediaPath(row.Media.Path), side, decoder, out var info);
            if (texture is null)
            {
                GD.PushWarning($"Showcase: {row.Media.Path}: {info}");
            }

            return texture;
        }

        return null;
    }

    /// <summary>Main thread: the focused game's images are read again if the media that changed may be its own.</summary>
    private void RefreshShowcaseArt(IReadOnlyList<GameKey>? games)
    {
        if (_overlay.Showcase.Visible && (games is null || (_focusedGame is { } game && Contains(games, game.Key))))
        {
            _overlay.Showcase.ForgetArt();
            _detailsDue = _clock;
        }
    }

    private static bool Contains(IReadOnlyList<GameKey> games, GameKey key)
    {
        foreach (var game in games)
        {
            if (game == key)
            {
                return true;
            }
        }

        return false;
    }

    private IImageDecoder ShowcaseDecoder() => _showcaseDecoder ??= AppServices.CreateImageDecoder();
}
