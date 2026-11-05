using System;
using Godot;
using Launcher.Core.Models;

namespace Launcher.App.Grid;

public sealed partial class ItemGrid
{
    // ---- Labels ---------------------------------------------------------------------------------

    /// <summary>
    /// A grid with labels: each bound cell's label goes under its item's foot, as the camera shows it. The focused item
    /// (and the one it left, easing back) grows and comes nearer, so its label moves down out of its way. Counts a change
    /// only when a label moved. Allocates nothing.
    /// </summary>
    private void UpdateLabels()
    {
        if (!_labels)
        {
            return;
        }

        var moved = false;
        var gap = _itemHeight * LabelGap;
        for (var cell = 0; cell < _maxCells; cell++)
        {
            if (_cellItem[cell] < 0)
            {
                continue;
            }

            var foot = FlatOrigin(cell);
            foot.Y -= gap;
            var at = Project(foot, out var nearer);
            var blend = cell == _focusCell ? _focusBlend : cell == _previousCell ? _previousBlend : 0;
            if (blend > 0)
            {
                var focused = FocusedFoot(cell, blend, cell == _focusCell ? _inspectBlend : _previousInspect);
                focused.Y -= gap;
                at.Y = Math.Max(at.Y, Project(focused, out _).Y);
            }

            var scale = _zoom * nearer;
            if (at != _labelAt[cell] || scale != _labelScale[cell])
            {
                _labelAt[cell] = at;
                _labelScale[cell] = scale;
                moved = true;
            }
        }

        if (moved)
        {
            _labelsVersion++;
        }
    }

    /// <summary>
    /// The foot of a focused item (or of one easing back), as <see cref="FocusTransform"/> draws it but without the
    /// player's turn or a launch: lower by its growth, and lifted towards the camera.
    /// </summary>
    private Vector3 FocusedFoot(int cell, float blend, float inspect)
    {
        var eased = blend * blend * (3 - 2 * blend);
        var inspected = inspect * inspect * (3 - 2 * inspect);
        var scale = 1 + (FocusScale - 1) * eased * (1 - inspected);
        var rest = _cellBase[cell].Origin;
        return new Vector3(rest.X, rest.Y + HalfHeight(cell) * _cellCurve[cell] * (1 - scale), rest.Z + _focusLift * eased * (1 - inspected));
    }

    /// <summary>
    /// Where a point in the grid's root shows, as shares of the view's width and height from its top left, through the
    /// camera (Main's: on the z axis, <see cref="_cameraDistance"/> from the grid's plane, whose height the view's is);
    /// <paramref name="nearer"/> is how much bigger its depth draws it than the plane would.
    /// </summary>
    private Vector2 Project(Vector3 local, out float nearer)
    {
        var world = _rootOrigin + local * (_scale * _zoom);
        nearer = _cameraDistance / Math.Max(_cameraDistance - world.Z, 0.01f);
        return new Vector2(0.5f + world.X * nearer / (_viewHeight * _viewAspect), 0.5f - world.Y * nearer / _viewHeight);
    }

    // ---- Motion ---------------------------------------------------------------------------------

    /// <summary>A critically damped spring towards the target row.</summary>
    private void SmoothScroll(float dt)
    {
        if (_scroll == _targetScroll && _scrollVelocity == 0)
        {
            return;
        }

        var omega = 2.0f / ScrollSmoothTime;
        var x = omega * dt;
        var decay = 1.0f / (1.0f + x + 0.48f * x * x + 0.235f * x * x * x);
        var change = _scroll - _targetScroll;
        var temp = (_scrollVelocity + omega * change) * dt;
        _scrollVelocity = (_scrollVelocity - omega * temp) * decay;
        _scroll = _targetScroll + (change + temp) * decay;
        if (MathF.Abs(_scroll - _targetScroll) < 0.0005f && MathF.Abs(_scrollVelocity) < 0.001f)
        {
            _scroll = _targetScroll;
            _scrollVelocity = 0;
        }

        _rootDirty = true;
    }

    private void UpdateRoot()
    {
        if (!_rootDirty)
        {
            return;
        }

        _rootDirty = false;
        var scale = _scale * _zoom;
        var origin = _horizontal
            ? _offset + new Vector3(-_scroll * _linePitch * scale, _focusLine, 0)
            : _offset + new Vector3(_crossOffset, _focusLine + _scroll * _linePitch * scale, 0);
        _rootOrigin = origin;
        _root.Transform = new Transform3D(Basis.Identity.Scaled(new Vector3(scale, scale, scale)), origin);
    }

    private void UpdateFocus(float dt)
    {
        var cell = CellOf(_focus);
        if (cell != _focusCell)
        {
            if (_focusCell >= 0)
            {
                if (_previousCell >= 0)
                {
                    var replaced = _previousCell;
                    SetCellTransform(replaced, _cellBase[replaced]);
                    UseBatched(replaced);
                    _previousCell = -1;
                }

                _previousCell = _focusCell;
                _previousBlend = _focusBlend;
                _previousInspect = _inspectBlend;
                OnFocusLeave(_previousCell);
            }

            // The item left takes the player's turn and inspection with it, to ease back as it blends out; the new one
            // starts square, where it rests.
            _previousYaw = _turnYaw;
            _previousPitch = _turnPitch;
            _turnYaw = _turnPitch = _swayTime = 0;
            _turned = false;
            _inspecting = false;
            _inspectBlend = 0;
            _focusCell = cell;
            _focusBlend = 0;
            _focusTime = 0;
            _labelsVersion++;
            if (_previousCell >= 0)
            {
                WriteCustom(_previousCell);
            }

            if (_focusCell >= 0)
            {
                OnFocusEnter(_focusCell);
                WriteCustom(_focusCell);
            }
        }

        _focusTime += dt;
        if (!_turned)
        {
            _swayTime += dt;
        }

        if (_focusCell >= 0)
        {
            _focusBlend = Math.Min(1, _focusBlend + dt * FocusBlendPerSecond);
            _inspectBlend = Mathf.MoveToward(_inspectBlend, _inspecting ? 1 : 0, dt * InspectBlendPerSecond);
            var launch = 0f;
            if (_launchTime >= 0)
            {
                _launchTime += dt;
                launch = Math.Min(1, _launchTime / LaunchFallbackSeconds);
            }

            SetCellTransform(_focusCell, FocusTransform(_focusCell, _focusBlend, _swayTime, launch, _turnYaw, _turnPitch, _inspectBlend));
        }

        if (_previousCell >= 0)
        {
            _previousBlend = Math.Max(0, _previousBlend - dt * FocusBlendPerSecond);
            _previousInspect = Math.Max(0, _previousInspect - dt * InspectBlendPerSecond);
            SetCellTransform(_previousCell, FocusTransform(_previousCell, _previousBlend, 0, 0, _previousYaw, _previousPitch, _previousInspect));

            // A batched model's clip has blended back to rest by now (ClipBlendSeconds), so it can rejoin its MultiMesh.
            if (_previousBlend <= 0 && _previousInspect <= 0 && _focusTime >= ClipBlendSeconds)
            {
                UseBatched(_previousCell);
                _previousCell = -1;
            }
        }
    }

    /// <summary>
    /// The focused item lifts towards the camera and grows a little (always), and sways to show its spine (as much as
    /// the theme's <c>focus_sway</c> says) unless a focused clip animates it; launching, it spins up and flies forward unless a launch clip plays instead (A7's
    /// procedural fallbacks). The player's turn (<see cref="Turn"/>) is about its middle, and blends with the focus.
    /// Inspected (<paramref name="inspect"/>, 0 to 1), it rests in the middle of the view, large (<see cref="Inspected"/>),
    /// instead of in its cell, without the lift and growth (which that place already has).
    /// </summary>
    private Transform3D FocusTransform(int cell, float blend, float time, float launch, float yaw, float pitch, float inspect)
    {
        var model = _cellModel[cell];
        var rest = _cellBase[cell];
        var eased = blend * blend * (3 - 2 * blend);
        var restOrigin = rest.Origin;
        var grow = 1f;
        var inspected = 0f;
        var size = Vector3.One;
        if (inspect > 0 || yaw != 0 || pitch != 0)
        {
            size = DrawnSize(cell);
        }

        if (inspect > 0)
        {
            inspected = inspect * inspect * (3 - 2 * inspect);
            var (origin, factor) = Inspected(cell, size);
            restOrigin = restOrigin.Lerp(origin, inspected);
            grow = 1 + (factor - 1) * inspected;
        }

        var scale = 1 + (FocusScale - 1) * eased * (1 - inspected);

        // Inspected, it faces the camera (only the player turns it): swaying that close, its near edge would leave the view.
        var angle = model?.HasClip(ModelClip.Focused) == true ? 0 : (0.3f + 0.3f * MathF.Sin(time * 1.1f)) * _focusSway * eased * (1 - inspected);
        var lift = _focusLift * eased * (1 - inspected);
        if (launch > 0 && model?.HasClip(ModelClip.Launch) != true)
        {
            var e = launch * launch;
            angle += e * Mathf.Tau * 1.5f;
            lift += e * 2.2f * _focusLift / FocusLift;
            scale += e * 0.3f;
        }

        var scaled = grow * scale;
        var basis = new Basis(Vector3.Up, angle) * rest.Basis.Scaled(new Vector3(scaled, scaled, scaled));

        // Round its vertical, then towards or away from the camera, about its middle (it stands on its origin), so it
        // turns in place.
        var pivot = Vector3.Zero;
        if (yaw != 0 || pitch != 0)
        {
            var turn = new Basis(Vector3.Right, pitch * eased) * new Basis(Vector3.Up, yaw * eased);
            var middle = basis * new Vector3(0, size.Y / 2, 0);
            pivot = middle - turn * middle;
            basis = turn * basis;
        }

        // Coming towards the camera, an item would drift outwards in perspective (off screen at the edge columns), so
        // it's pulled in to stay where it was on screen; launching, it flies towards the middle.
        var rootScale = _scale * _zoom;
        var toCamera = Math.Clamp(1 - lift * rootScale / _cameraDistance, 0.2f, 1);
        var x = ((_rootOrigin.X + restOrigin.X * rootScale) * toCamera - _rootOrigin.X) / rootScale;
        var y = restOrigin.Y + HalfHeight(cell) * _cellCurve[cell] * grow * (1 - scale);
        return new Transform3D(basis, new Vector3(x, y, restOrigin.Z + lift) + pivot);
    }

    /// <summary>
    /// Where the cell's item rests when inspected, in the grid's root, and how much it grows from its rest size: its
    /// middle on the camera's axis, its front <see cref="InspectHeight"/> of the view tall (or <see cref="InspectWidth"/>
    /// of it wide, if that's smaller), and far enough in front of the other items that turned round its vertical it
    /// doesn't touch them.
    /// </summary>
    /// <param name="size">The model's size as drawn (<see cref="DrawnSize"/>), in model units.</param>
    private (Vector3 Origin, float Grow) Inspected(int cell, Vector3 size)
    {
        var rootScale = _scale * _zoom;
        var restScale = _cellFit[cell] * _cellCurve[cell];

        // How far it reaches from its vertical, turned any way round it, and how far its front is from its middle.
        var reach = MathF.Sqrt(size.X * size.X + size.Z * size.Z) / 2;
        var near = reach + size.Z / 2;

        // The other items come no nearer the camera than this (world z): a focused one's lift and half the cell.
        var front = _rootOrigin.Z + (_focusLift + Math.Max(_cellWidth, _itemHeight) / 2) * rootScale;
        var depth = _cameraDistance - front;
        var tall = InspectHeight * _viewHeight;
        var wide = InspectWidth * _viewHeight * _viewAspect;

        // World units per model unit, k: the view at depth z is viewHeight × (D − z) / D tall; the middle stands reach × k
        // in front of the others, and the front near × k, so the front's height fills `tall` of the view there.
        var k = Math.Min(
            tall * depth / (_cameraDistance * Math.Max(size.Y, 0.01f) + tall * near),
            wide * depth / (_cameraDistance * Math.Max(size.X, 0.01f) + wide * near));
        var middle = (new Vector3(0, 0, front + reach * k) - _rootOrigin) / rootScale;
        var grow = k / (Math.Max(restScale, 0.0001f) * rootScale);
        return (middle - new Vector3(0, size.Y / 2 * restScale * grow, 0), grow);
    }

    private void SetCellTransform(int cell, Transform3D transform)
    {
        if (_cellNode[cell] is { } node)
        {
            node.Transform = transform;
        }
        else if (_cellTemplate[cell] >= 0 && _multiMeshes[_cellTemplate[cell]] is not null)
        {
            PlaceInstance(cell, transform);
        }
    }

    /// <summary>
    /// Draws the cell with an instance of its template's MultiMesh at <paramref name="transform"/>: the one it has, or
    /// the next unused one, which then counts as visible. The MultiMesh's node shows only while it has instances in use.
    /// </summary>
    private void PlaceInstance(int cell, Transform3D transform)
    {
        var template = _cellTemplate[cell];
        var multiMesh = _multiMeshes[template]!;
        var instance = _cellInstance[cell];
        if (instance < 0)
        {
            instance = _instancesUsed[template];
            _instancesUsed[template] = instance + 1;
            _instanceCell[template][instance] = cell;
            _cellInstance[cell] = instance;
            multiMesh.SetInstanceCustomData(instance, _cellData[cell]);
            multiMesh.VisibleInstanceCount = instance + 1;

            // An empty MultiMesh has no bounds, and while it has none the renderer keeps its node's last transform (the
            // grid scrolls on without it), and takes its new bounds only the frame after its first instance: drawn in
            // that frame, the instance was where the grid had been (2026-10-27). Shown again, the node sends both now.
            if (instance == 0)
            {
                _instances[template]!.Visible = true;
            }
        }

        _cellDrawn[cell] = transform;
        multiMesh.SetInstanceTransform(instance, transform);
    }

    /// <summary>
    /// Stops drawing the cell with its template's MultiMesh (it's hidden, drawn as a node, or changing template): the
    /// last instance in use takes its place, so the ones in use stay the first.
    /// </summary>
    private void RemoveInstance(int cell)
    {
        var instance = _cellInstance[cell];
        var template = _cellTemplate[cell];
        if (instance < 0 || template < 0 || template >= _multiMeshes.Count || _multiMeshes[template] is not { } multiMesh)
        {
            _cellInstance[cell] = -1;
            return;
        }

        _cellInstance[cell] = -1;
        var last = _instancesUsed[template] - 1;
        if (instance != last)
        {
            var moved = _instanceCell[template][last];
            _instanceCell[template][instance] = moved;
            _cellInstance[moved] = instance;
            multiMesh.SetInstanceTransform(instance, _cellDrawn[moved]);
            multiMesh.SetInstanceCustomData(instance, _cellData[moved]);
        }

        multiMesh.SetInstanceTransform(last, Hidden);
        _instancesUsed[template] = last;
        multiMesh.VisibleInstanceCount = last;
        if (last == 0)
        {
            _instances[template]!.Visible = false;
        }
    }

    private void AnimateFades(float dt)
    {
        if (_fadingSlots <= 0)
        {
            _fadingSlots = 0;
            return;
        }

        var step = dt / FadeSeconds;
        for (var i = 0; i < _textured.Length; i++)
        {
            if (_textured[i] && _fade[i] < 1)
            {
                _fade[i] = Math.Min(1, _fade[i] + step);
                if (_fade[i] >= 1)
                {
                    _fadingSlots--;
                }

                WriteState(i / Slots, i % Slots);
            }
        }
    }

    private void MeasureTexturing()
    {
        // The rows whose centre is on screen.
        var rowWorld = _linePitch * _scale * _zoom;
        var before = _horizontal ? _viewHeight * _viewAspect / 2 : _viewHeight / 2 - _focusLine;
        var after = _horizontal ? before : _viewHeight / 2 + _focusLine;
        var first = Math.Max(0, (int)MathF.Ceiling(_scroll - before / rowWorld));
        var last = Math.Min(_rows - 1, (int)MathF.Floor(_scroll + after / rowWorld));
        var wanting = 0;
        var textured = 0;
        for (var row = first; row <= last; row++)
        {
            var poolRow = row % _poolRows;
            if (_boundRow[poolRow] != row)
            {
                continue;
            }

            for (var column = 0; column < _columns; column++)
            {
                var cell = poolRow * _columns + column;
                if (_cellItem[cell] < 0)
                {
                    continue;
                }

                for (var i = cell * Slots; i < (cell + 1) * Slots; i++)
                {
                    if (_wanted[i])
                    {
                        wanting++;
                        if (_textured[i])
                        {
                            textured++;
                        }
                    }
                }
            }
        }

        AnyVisibleArt = wanting > 0;
        VisibleTexturedFraction = wanting == 0 ? 1 : (float)textured / wanting;
        if (!VisibleTextured && textured == wanting && _source is not null)
        {
            VisibleTextured = true;
        }
    }
}
