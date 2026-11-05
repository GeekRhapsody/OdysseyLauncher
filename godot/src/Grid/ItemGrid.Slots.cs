using System;
using Godot;
using Launcher.App.Models;
using Launcher.App.Theming;
using Launcher.Core.Models;
using Launcher.Core.Theming;

namespace Launcher.App.Grid;

public sealed partial class ItemGrid
{
    // ---- Slots ------------------------------------------------------------------------------------

    /// <summary>
    /// Walks each of the cell's model slots down its chain against the item's media. On a refresh, a slot whose
    /// media is the same as before keeps its layer (and its request in flight).
    /// </summary>
    private void ResolveSlots(int cell, int item, bool refresh)
    {
        var model = _cellModel[cell]!;
        for (var slot = 0; slot < Slots; slot++)
        {
            var i = cell * Slots + slot;
            if (model.Chain(slot) is not { } chain)
            {
                ClearSlot(cell, slot);
                continue;
            }

            // A slot the grid has no layers for (a per-game model's slot the theme never fills) shows its fallback.
            var channel = _streamer is null ? -1 : _streamer.Layout.ChannelOf(slot);
            var media = new SourceMedia(_source!, item, channel >= 0);
            var resolution = chain.Resolve(0, ref media);
            if (refresh && resolution.MediaSlot >= 0 && _wanted[i]
                && _source!.TryGetMedia(item, resolution.MediaSlot, out var current) && current == _media[i])
            {
                if (!_textured[i] && _texturesEnabled && _streamer?.HasArrays == true)
                {
                    _streamer.Request(cell, channel, item / _columns, _media[i]);
                }

                continue;
            }

            Apply(cell, slot, channel, resolution, item);
        }

        WriteShape(cell);
    }

    /// <summary>Shows a resolution in a cell's slot: requests its media, or shows its fallback.</summary>
    private void Apply(int cell, int slot, int channel, SlotResolution resolution, int item)
    {
        var i = cell * Slots + slot;
        if (cell == _inspectArtCell)
        {
            _inspectArtStale = true;
        }

        if (_textured[i] && _fade[i] < 1)
        {
            _fadingSlots--;
        }

        _textured[i] = false;
        _fade[i] = 0;
        // Bit 0: the fallback is generated. Bit 1: the art is drawn whole over the fallback, fitted inside the face (the
        // template's fit, or a logo). Bit 2: it's a logo, so it has a margin, and along a spine it's turned.
        var logo = resolution.MediaSlot == MediaSlots.Logo;
        _fallback[i] = (byte)((resolution.Fallback == SlotSourceKind.Generated ? 1 : 0)
            | (logo || _cellModel[cell]?.ShowsWhole(slot) == true ? 2 : 0)
            | (logo ? 4 : 0));
        _next[i] = resolution.Next;
        if (resolution.MediaSlot >= 0 && _source!.TryGetMedia(item, resolution.MediaSlot, out var media))
        {
            _wanted[i] = true;
            _media[i] = media;
            if (_texturesEnabled && _streamer?.HasArrays == true)
            {
                _streamer.Request(cell, channel, item / _columns, media);
            }
        }
        else
        {
            _wanted[i] = false;
            _media[i] = default;
            if (channel >= 0)
            {
                _streamer?.Cancel(cell, channel);
            }
        }

        WriteState(cell, slot);
    }

    private void ClearSlot(int cell, int slot)
    {
        var i = cell * Slots + slot;
        if (_textured[i] && _fade[i] < 1)
        {
            _fadingSlots--;
        }

        _wanted[i] = false;
        _textured[i] = false;
        _fade[i] = 0;
        _media[i] = default;
    }

    private void HideCell(int cell)
    {
        if (cell == _inspectArtCell)
        {
            DropInspectArt();
        }

        ReleaseNode(cell);
        RemoveInstance(cell);
        _cellTemplate[cell] = -1;
        _cellModel[cell] = null;
        WriteShape(cell);
        _cellItem[cell] = -1;
        for (var slot = 0; slot < Slots; slot++)
        {
            ClearSlot(cell, slot);
        }

        _streamer?.CancelCell(cell);
    }

    private void SetArrays(ShaderMaterial material)
    {
        material.SetShaderParameter(ShaderParams.SlotsLarge, _streamer?.Large is { } large ? large : default(Variant));
        material.SetShaderParameter(ShaderParams.SlotsSmall, _streamer?.Small is { } small ? small : default(Variant));
    }

    /// <summary>
    /// One texel per cell and slot: (fallback: 1 generated, 0 authored, plus 2 for art drawn whole and 4 for a logo;
    /// media aspect or 0; fade; layer).
    /// </summary>
    private void WriteState(int cell, int slot)
    {
        var i = cell * Slots + slot;
        var aspect = 0f;
        var layer = 0f;
        if (_wanted[i])
        {
            aspect = _media[i].Aspect > 0 ? _media[i].Aspect : _cellModel[cell]?.SlotAspect(slot) ?? 1;
            var channel = _streamer!.Layout.ChannelOf(slot);
            layer = _streamer.Layout.LayerOf(cell, channel);
        }

        _stateImage.SetPixel(slot, cell, new Color(_fallback[i], aspect, _textured[i] ? _fade[i] : 0, layer));
        _stateDirty = true;
    }

    /// <summary>
    /// Main thread, binding a list: the widest and tallest of its reshaped boxes (A6 shape = "media"), each with the
    /// larger of its width and height 1, so the cells fit them. Lists without such a template skip the walk.
    /// </summary>
    private void FindEnvelope(IGridSource source)
    {
        _envelopeWidth = 0;
        _envelopeHeight = 0;
        var any = false;
        for (var t = 0; t < _templates.Count; t++)
        {
            any |= _templates[t].ShapeFromMedia && source.UsesTemplate(t);
        }

        if (!any)
        {
            return;
        }

        for (var item = 0; item < source.Count; item++)
        {
            source.Describe(item, out var info);
            var template = _templates[Math.Clamp(info.Template, 0, _templates.Count - 1)];
            if (info.Model is not null || !template.ShapeFromMedia)
            {
                continue;
            }

            var front = source.TryGetMedia(item, template.ShapeSlot, out var media) ? media.Aspect : 0;
            var (width, height) = BoxShape.Unit(RestOf(template), front);
            _envelopeWidth = Math.Max(_envelopeWidth, width);
            _envelopeHeight = Math.Max(_envelopeHeight, height);
        }
    }

    private static BoxSize RestOf(ItemTemplate template) => new(template.Size.X, template.Size.Y, template.Size.Z);

    /// <summary>
    /// A reshaped box's two texels (item.gdshader), from its game's front and spine (<see cref="BoxShape"/>): how much
    /// each half of the rest mesh moves out (half the width's growth, the height's, half the depth's) and the height
    /// above which a vertex is in the top half; then the faces' new aspects (front and back, spine: on the sides as deep
    /// over high as the box, or for a template whose spine face is wider than high, on the top and bottom, as wide over
    /// deep), and which slot is the front (the cover, or a flat card's screenshot). Zeros for every other cell, which
    /// the shader leaves as it is.
    /// </summary>
    private void WriteShape(int cell)
    {
        var item = _cellItem[cell];
        if (_cellModel[cell] is not { ShapeFromMedia: true } model || item < 0 || _source is null)
        {
            if (_shaped[cell])
            {
                _stateImage.SetPixel(ShapeColumn, cell, default);
                _stateImage.SetPixel(ShapeColumn + 1, cell, default);
                _shaped[cell] = false;
                _stateDirty = true;
            }

            return;
        }

        var rest = RestOf(model);
        var size = ShapeOf(item, model);
        _stateImage.SetPixel(ShapeColumn, cell, new Color(
            (size.Width - rest.Width) / 2, size.Height - rest.Height, (size.Depth - rest.Depth) / 2, rest.Height / 2));
        var spineFace = model.SlotAspect(MediaSlots.Spine) > 1 ? size.Width / size.Depth : size.Depth / size.Height;
        _stateImage.SetPixel(ShapeColumn + 1, cell, new Color(size.Width / size.Height, spineFace, model.ShapeSlot, 0));
        _shaped[cell] = true;
        _stateDirty = true;
    }

    /// <summary>
    /// A reshaped box's size for its item's front (the cover, or the screenshot: <see cref="ItemTemplate.ShapeSlot"/>)
    /// and spine (<see cref="BoxShape.Fit"/>), in model units.
    /// </summary>
    private BoxSize ShapeOf(int item, ItemTemplate model)
    {
        var front = _source!.TryGetMedia(item, model.ShapeSlot, out var frontMedia) ? frontMedia.Aspect : 0;
        var spine = _source.TryGetMedia(item, MediaSlots.Spine, out var spineMedia) ? spineMedia.Aspect : 0;
        return BoxShape.Fit(RestOf(model), front, spine, _envelopeWidth, _envelopeHeight);
    }

    /// <summary>
    /// The cell's model's size as drawn, in model units before the cell's fit: a reshaped box's (<see cref="WriteShape"/>:
    /// it still stands on its origin, centred), else the model's.
    /// </summary>
    private Vector3 DrawnSize(int cell)
    {
        if (_cellModel[cell] is not { } model)
        {
            return Vector3.One;
        }

        if (!_shaped[cell] || _source is null || _cellItem[cell] < 0)
        {
            return model.Size;
        }

        var size = ShapeOf(_cellItem[cell], model);
        return new Vector3(size.Width, size.Height, size.Depth);
    }

    /// <summary>Whether the cell's item is inspected, or still on its way there or back.</summary>
    private bool IsInspected(int cell) =>
        cell >= 0 && ((cell == _focusCell && (_inspecting || _inspectBlend > 0)) || (cell == _previousCell && _previousInspect > 0));

    /// <summary>
    /// The cell's per-instance data (item.gdshader): the cell, the plain colour packed into one channel, the idle phase
    /// (-1: focused), and 1 when a clip animates it (so the shader doesn't bob it too).
    /// </summary>
    private void WriteCustom(int cell)
    {
        if (_cellModel[cell] is not { } model)
        {
            return;
        }

        var phase = cell == _focusCell ? -1 : _cellPhase[cell];
        var plain = _cellPlain[cell];
        var packed = (Math.Clamp(plain.R8, 0, 255) << 16) | (Math.Clamp(plain.G8, 0, 255) << 8) | Math.Clamp(plain.B8, 0, 255);
        var animated = model.HasClip(ModelClip.Idle) && _cellScene[cell] is not null ? 1 : 0;

        // A node's data goes through an instance uniform as a Vector4: Godot converts a Color given to one from sRGB
        // to linear, which would scramble the cell and the packed colour.
        var node = new Vector4(cell, packed, phase, animated);
        if (_cellScene[cell] is { } scene)
        {
            foreach (var geometry in scene.Geometry)
            {
                geometry.SetInstanceShaderParameter(ShaderParams.NodeCustom, node);
            }
        }
        else if (_cellNode[cell] is MeshInstance3D mesh)
        {
            mesh.SetInstanceShaderParameter(ShaderParams.NodeCustom, node);
        }
        else
        {
            _cellData[cell] = new Color(cell, packed, phase, animated);
            if (_cellInstance[cell] >= 0 && _multiMeshes[_cellTemplate[cell]] is { } multiMesh)
            {
                multiMesh.SetInstanceCustomData(_cellInstance[cell], _cellData[cell]);
            }
        }
    }

    private int CellOf(int item)
    {
        if (item < 0 || _columns == 0 || _boundRow.Length == 0)
        {
            return -1;
        }

        var row = item / _columns;
        var poolRow = row % _poolRows;
        return _boundRow[poolRow] == row ? poolRow * _columns + item % _columns : -1;
    }

    /// <summary>Where the bound cell's item stands, before the carousel's curve: its line along the scroll, and its column.</summary>
    private Vector3 FlatOrigin(int cell)
    {
        var item = _cellItem[cell];
        var row = item / _columns;
        if (_horizontal)
        {
            return new Vector3(row * _linePitch, -_itemHeight / 2, 0);
        }

        // A grid of one part-filled row is centred; otherwise rows fill from the left.
        var shown = _rows == 1 ? _count : _columns;
        var x = (item % _columns - (shown - 1) / 2.0f) * _pitchX;
        return new Vector3(x, -row * _linePitch - _itemHeight / 2, 0);
    }

    /// <summary>
    /// Half the cell's model's height as drawn (fitted), about which it's centred in the cell, shrinks on a carousel's
    /// curve and grows when focused. A reshaped box counts as the cell's height: boxes stand on the row's floor.
    /// </summary>
    private float HalfHeight(int cell) =>
        _cellModel[cell] is { ShapeFromMedia: false } model
            ? Math.Min(model.Size.Y * _cellFit[cell], _itemHeight) / 2
            : _itemHeight / 2;

    /// <summary>The bound cell's resting transform: fitted, centred in the cell's height, and on a carousel's curve.</summary>
    private Transform3D RestTransform(int cell)
    {
        var origin = FlatOrigin(cell);
        if (_curved)
        {
            return CurvedTransform(cell, origin);
        }

        _cellCurve[cell] = 1;
        var fit = _cellFit[cell];
        origin.Y += _itemHeight / 2 - HalfHeight(cell);
        return new Transform3D(Basis.Identity.Scaled(new Vector3(fit, fit, fit)), origin);
    }

    /// <summary>
    /// A carousel's item, by its places from the middle: within a place it shrinks to the size of its neighbours, and
    /// it turns towards the middle and steps back the further away it is (its centre staying on the line).
    /// </summary>
    private Transform3D CurvedTransform(int cell, Vector3 origin)
    {
        var places = origin.X / _linePitch - _scroll;
        var away = MathF.Abs(places);
        var curve = 1 - CarouselShrink * Math.Min(away, 1);
        _cellCurve[cell] = curve;
        var fit = _cellFit[cell] * curve;
        var turn = -Math.Clamp(places, -1.5f, 1.5f) * CarouselTurn;
        var back = -CarouselDepth * Math.Min(away, 3) * _itemHeight;
        return new Transform3D(
            new Basis(Vector3.Up, turn).Scaled(new Vector3(fit, fit, fit)),
            new Vector3(origin.X, origin.Y + _itemHeight / 2 - HalfHeight(cell) * curve, back));
    }

    /// <summary>A carousel's items take their places on its curve again whenever it scrolls (the focused ones follow in <see cref="UpdateFocus"/>).</summary>
    private void UpdateCurve()
    {
        if (!_curved || _scroll == _curveScroll)
        {
            return;
        }

        _curveScroll = _scroll;
        for (var cell = 0; cell < _maxCells; cell++)
        {
            if (_cellItem[cell] < 0)
            {
                continue;
            }

            _cellBase[cell] = CurvedTransform(cell, FlatOrigin(cell));
            if (cell != _focusCell && cell != _previousCell)
            {
                SetCellTransform(cell, _cellBase[cell]);
            }
        }
    }

    /// <summary>
    /// What media an item has, for <see cref="SlotChain.Resolve"/>: a struct, so resolving allocates nothing. With no
    /// layers for the slot, nothing counts, so the chain ends at its fallback.
    /// </summary>
    private readonly struct SourceMedia(IGridSource source, int item, bool canShow) : IMediaAvailability
    {
        public bool Has(int slot) => canShow && source.TryGetMedia(item, slot, out _);
    }
}
