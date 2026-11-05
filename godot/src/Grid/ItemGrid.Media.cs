using System;
using Godot;
using Launcher.App.Models;
using Launcher.App.Textures;
using Launcher.App.Theming;
using Launcher.App.Ui;
using Launcher.Core.Media;

namespace Launcher.App.Grid;

public sealed partial class ItemGrid
{
    // ---- Card videos ------------------------------------------------------------------------------

    /// <summary>
    /// Decodes the focused card's video (A6 Card videos), or in a grid of games the focused game's (A6 Game videos);
    /// null for none: a platform without a decoder, whose cards show their <c>video</c> material's own texture and whose
    /// games their art.
    /// </summary>
    public IVideoDecoder? VideoDecoder { get; set; }

    /// <summary>
    /// Once a frame: the focused card plays its video while the grid shows and nothing covers it
    /// (<see cref="VideosSuspended"/>), on its <c>video</c> material's texture, timed by its focused clip (or, without
    /// one, by its own clock); anything else stops it and puts the texture back.
    /// </summary>
    private void UpdateVideo(float dt)
    {
        var cell = _focusCell;
        var model = cell >= 0 && Visible && !VideosSuspended && VideoDecoder is not null ? _cellModel[cell] : null;
        if (model is null || !model.HasVideo)
        {
            StopVideo();
            return;
        }

        if (_video is null || cell != _videoCell || model != _videoModel)
        {
            StopVideo();
            _video = new CardVideo(VideoDecoder!, model.VideoPath!);
            _videoCell = cell;
            _videoModel = model;
            _videoClock = 0;
        }

        double position;
        if (_cellScene[cell]?.Player is { } player && player.IsPlaying())
        {
            position = player.CurrentAnimationPosition;
        }
        else
        {
            _videoClock += dt;
            var duration = _video.Duration;
            if (duration > 0 && _videoClock >= duration)
            {
                _videoClock -= duration;
            }

            position = _videoClock;
        }

        _video.Tick(position);
        if (_videoMaterial is null && _video.Texture is { } texture && MaterialOf(cell, model) is { } material)
        {
            material.SetShaderParameter(ShaderParams.Authored[model.VideoTexture], texture);
            _videoMaterial = material;
        }
    }

    private void StopVideo()
    {
        if (_video is null)
        {
            return;
        }

        if (_videoMaterial is not null && _videoModel is not null)
        {
            _videoMaterial.SetShaderParameter(ShaderParams.Authored[_videoModel.VideoTexture], _videoModel.Authored[_videoModel.VideoTexture]);
        }

        // Not waited for: as the app quits, Main waits for its thread with the rest of the work calling into Godot (GodotWork).
        _video.Dispose();

        _video = null;
        _videoMaterial = null;
        _videoModel = null;
        _videoCell = -1;
    }

    /// <summary>The material the cell's model is drawn with (its template's, or its own node's).</summary>
    private ShaderMaterial? MaterialOf(int cell, ItemTemplate model) =>
        _cellTemplate[cell] >= 0 ? _materials[_templateMaterial[_cellTemplate[cell]]]
        : _modelMaterials.TryGetValue(model, out var material) ? material : null;

    public override void _ExitTree()
    {
        StopVideo();
        StopGameVideo();
        DropInspectArt();
    }

    // ---- Game videos ------------------------------------------------------------------------------

    private const float GameVideoFadeSeconds = 0.25f;

    private static readonly Vector4 NoGameVideo = new(-1, -1, 1, 0);

    /// <summary>
    /// Holds videos off while something covers the grid (a settings screen, a system's or a game's details or options):
    /// a game's, so no sound plays under it, and the focused card's, whose details play it on a view of their own
    /// (<see cref="Screens.ModelView"/>). The owner sets it each frame. A video stops, and starts again (a game's after
    /// its delay) once this is cleared.
    /// </summary>
    public bool VideosSuspended { get; set; }

    /// <summary>
    /// Once a frame: once a game whose template plays videos (<see cref="ItemTemplate.GameVideoSlot"/>) has been focused
    /// for its template's delay, its video plays on that slot's face, with its sound, fading in over the art, and loops.
    /// Moving the focus, launching, hiding or covering the grid stops it, and the art shows again. Only the focused game
    /// ever plays, and only through the shader's uniforms on its template's material, which pick out its cell: the other
    /// games drawn with that material keep their art.
    /// </summary>
    private void UpdateGameVideo(float dt)
    {
        var cell = _focusCell;
        var item = cell >= 0 ? _cellItem[cell] : -1;
        var model = item >= 0 ? _cellModel[cell] : null;
        if (model is not { GameVideoSlot: >= 0 } || VideoDecoder is not { } decoder || _streamer is null || _videoSound is null
            || !Visible || VideosSuspended || _launchTime >= 0)
        {
            StopGameVideo();
            _gameVideoCell = -1;
            return;
        }

        if (cell != _gameVideoCell || item != _gameVideoItem || model != _gameVideoModel)
        {
            StopGameVideo();
            _gameVideoCell = cell;
            _gameVideoItem = item;
            _gameVideoModel = model;
            _gameVideoWait = 0;
            _gameVideoDone = false;
        }

        if (_gameVideo is null)
        {
            _gameVideoWait += dt;
            if (_gameVideoDone || _gameVideoWait < model.GameVideoDelay)
            {
                return;
            }

            if (!_source!.TryGetVideo(item, out var media))
            {
                _gameVideoDone = true;
                return;
            }

            _gameVideoPath = MediaFolder.FullPath(_streamer.MediaDir, media.Path);
            _gameVideo = new VideoPlayback(decoder, _gameVideoPath, _videoSound);
            _gameVideoFade = 0;
        }

        // An ended video starts again: the next playback opens while the last frame holds, and takes over with its first.
        if (_gameVideo.Ended && _gameVideoNext is null)
        {
            _gameVideoNext = new VideoPlayback(decoder, _gameVideoPath!, _videoSound);
        }

        if (_gameVideoNext is { } next)
        {
            next.Tick(dt);
            if (next.Texture is not null || next.Error is not null)
            {
                _gameVideo.Dispose();
                _gameVideo = next;
                _gameVideoNext = null;
            }
        }
        else
        {
            _gameVideo.Tick(dt);
        }

        if (_gameVideo.Error is not null)
        {
            GD.PushWarning($"Game video: {_gameVideoPath}: {_gameVideo.Error}");
            StopGameVideo();
            _gameVideoDone = true;
            return;
        }

        if (_gameVideo.Texture is not { } texture || MaterialOf(cell, model) is not { } material)
        {
            return;
        }

        var changed = false;
        if (material != _gameVideoMaterial || texture != _gameVideoTexture)
        {
            _gameVideoMaterial?.SetShaderParameter(ShaderParams.VideoState, NoGameVideo);
            material.SetShaderParameter(ShaderParams.VideoFrame, texture);
            material.SetShaderParameter(ShaderParams.VideoWhole, model.ShowsWhole(model.GameVideoSlot));
            _gameVideoMaterial = material;
            _gameVideoTexture = texture;
            changed = true;
        }

        if (_gameVideoFade < 1 || changed)
        {
            _gameVideoFade = Math.Min(1, _gameVideoFade + dt / GameVideoFadeSeconds);
            material.SetShaderParameter(ShaderParams.VideoState, new Vector4(cell, model.GameVideoSlot, _gameVideo.Aspect, _gameVideoFade));
        }
    }

    /// <summary>Stops the game's video and its sound, and shows the slot's art again.</summary>
    private void StopGameVideo()
    {
        if (_gameVideoMaterial is { } material)
        {
            material.SetShaderParameter(ShaderParams.VideoState, NoGameVideo);
            material.SetShaderParameter(ShaderParams.VideoFrame, default(Variant));
        }

        // Not waited for: as the app quits, Main waits for their threads with the rest of the work calling into Godot (GodotWork).
        _gameVideo?.Dispose();
        _gameVideoNext?.Dispose();
        _gameVideo = null;
        _gameVideoNext = null;
        _gameVideoMaterial = null;
        _gameVideoTexture = null;
    }

    // ---- The inspected game's art ------------------------------------------------------------------

    private const float InspectArtFadeSeconds = 0.15f;

    private static readonly Vector4 NoInspectArt = new(-1, 0, 0, 0);

    /// <summary>
    /// The inspected game's slot art at <see cref="InspectTextures.Size"/> (A3): asked for when it's inspected, faded in
    /// over the grid's layers once it's made, kept while the item eases back to its place, and freed once it's there.
    /// </summary>
    private void UpdateInspectArt(float dt)
    {
        if (_inspectArt is null)
        {
            return;
        }

        var want = !_texturesEnabled ? -1
            : _focusCell >= 0 && _inspecting ? _focusCell
            : _inspectArtCell >= 0 && IsInspected(_inspectArtCell) ? _inspectArtCell
            : -1;
        if (want != _inspectArtCell || _inspectArtStale)
        {
            DropInspectArt();
            if (want >= 0)
            {
                RequestInspectArt(want);
            }
        }

        if (_inspectArtCell < 0)
        {
            return;
        }

        if (_inspectArtShown is null)
        {
            if (!_inspectArt.TryTake(out var art))
            {
                return;
            }

            _inspectArtShown = art;
            _inspectArtFade = 0;
        }

        if (_cellModel[_inspectArtCell] is not { } model || MaterialOf(_inspectArtCell, model) is not { } material)
        {
            return;
        }

        var changed = false;
        if (material != _inspectArtMaterial)
        {
            ClearInspectArtMaterial();

            // Disposed at once: a Variant holding an object keeps a reference until the GC finalises it, and this array
            // is freed as soon as the item is back in its place.
            using (var texture = Variant.CreateFrom(_inspectArtShown!.Texture))
            {
                material.SetShaderParameter(ShaderParams.SlotsInspect, texture);
            }

            material.SetShaderParameter(ShaderParams.InspectLayersLow, _inspectArtShown.LayersLow);
            material.SetShaderParameter(ShaderParams.InspectLayersHigh, _inspectArtShown.LayersHigh);
            _inspectArtMaterial = material;
            changed = true;
        }

        if (_inspectArtFade < 1 || changed)
        {
            _inspectArtFade = Math.Min(1, _inspectArtFade + dt / InspectArtFadeSeconds);
            material.SetShaderParameter(ShaderParams.InspectState, new Vector4(_inspectArtCell, _inspectArtFade, 0, 0));
        }
    }

    /// <summary>Asks for the cell's art: every slot that shows media, from its source file.</summary>
    private void RequestInspectArt(int cell)
    {
        var count = 0;
        for (var slot = 0; slot < Slots; slot++)
        {
            var i = cell * Slots + slot;
            if (_wanted[i] && _media[i].Path is { } path)
            {
                _inspectSlots[count] = slot;
                _inspectPaths[count] = MediaFolder.FullPath(_streamer!.MediaDir, path);
                count++;
            }
        }

        _inspectArtCell = cell;
        _inspectArtStale = false;
        if (count > 0)
        {
            _inspectArt!.Request(cell, _inspectSlots.AsSpan(0, count), _inspectPaths.AsSpan(0, count));
        }
    }

    /// <summary>Drops the inspected game's art (and any request for it), and shows the grid's layers again.</summary>
    private void DropInspectArt()
    {
        if (_inspectArtCell < 0)
        {
            return;
        }

        _inspectArt?.Cancel();
        ClearInspectArtMaterial();
        _inspectArtShown?.Texture.Dispose();
        _inspectArtShown = null;
        _inspectArtCell = -1;
        _inspectArtStale = false;
        _inspectArtFade = 0;
    }

    private void ClearInspectArtMaterial()
    {
        if (_inspectArtMaterial is { } material)
        {
            material.SetShaderParameter(ShaderParams.InspectState, NoInspectArt);
            material.SetShaderParameter(ShaderParams.SlotsInspect, default(Variant));
        }

        _inspectArtMaterial = null;
    }
}
