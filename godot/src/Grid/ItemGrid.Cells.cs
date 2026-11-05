using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Models;
using Launcher.Core.Models;

namespace Launcher.App.Grid;

public sealed partial class ItemGrid
{
    // ---- Binding --------------------------------------------------------------------------------

    private void VisibleRange(out int first, out int last)
    {
        var rowWorld = _linePitch * _scale * _zoom;
        float above, below;
        if (_horizontal)
        {
            // The carousel's curve draws its far items in, so one more shows each side.
            above = below = _viewHeight * _viewAspect / 2 / rowWorld + (_curved ? 1.5f : 0.5f);
        }
        else
        {
            above = (_viewHeight / 2 - _focusLine) / rowWorld + 0.5f;
            below = (_viewHeight / 2 + _focusLine) / rowWorld + 0.5f;
        }

        first = Math.Max(0, (int)MathF.Floor(_scroll - above));
        last = Math.Min(_rows - 1, (int)MathF.Ceiling(_scroll + below));
    }

    private void BindVisibleRows()
    {
        // The pool's spare rows go ahead of the scroll: one behind, the rest in front.
        VisibleRange(out var first, out var last);
        var spare = Math.Max(0, _poolRows - (last - first + 1));
        var behind = Math.Min(1, spare);
        var from = _scrollVelocity >= 0 ? first - behind : first - (spare - behind);
        from = Math.Clamp(from, 0, Math.Max(0, _rows - _poolRows));
        var to = Math.Min(_rows - 1, from + _poolRows - 1);
        for (var row = from; row <= to; row++)
        {
            var poolRow = row % _poolRows;
            if (_boundRow[poolRow] != row)
            {
                BindRow(poolRow, row);
            }
        }
    }

    private void BindRow(int poolRow, int row)
    {
        _boundRow[poolRow] = row;
        for (var column = 0; column < _columns; column++)
        {
            var cell = poolRow * _columns + column;
            var item = row * _columns + column;
            if (cell == _focusCell)
            {
                _focusCell = -1;
            }

            if (cell == _previousCell)
            {
                _previousCell = -1;
            }

            if (item >= _count)
            {
                HideCell(cell);
                continue;
            }

            _source!.Describe(item, out var info);
            var template = Math.Clamp(info.Template, 0, _templates.Count - 1);
            _cellItem[cell] = item;
            _cellPlain[cell] = info.Plain;
            _cellPhase[cell] = item * 2.39996f % Mathf.Tau;
            ShowModel(cell, template, info.Model ?? _templates[template]);

            _cellBase[cell] = RestTransform(cell);
            SetCellTransform(cell, _cellBase[cell]);
            WriteCustom(cell);
            _atlas.SetTitle(cell, info.Title);
            _cellTitle[cell] = info.Title;
            ResolveSlots(cell, item, refresh: false);
        }

        _labelsVersion++;
    }

    // ---- How a cell is drawn ------------------------------------------------------------------------

    /// <summary>
    /// Puts the cell's model on screen: its template's MultiMesh instance, or a node. A per-game model is fitted to the
    /// cell (scaled down if it's bigger than the theme's templates); a theme's template sets the cell, so it's drawn
    /// as it is.
    /// </summary>
    private void ShowModel(int cell, int template, ItemTemplate model)
    {
        ReleaseNode(cell);
        RemoveInstance(cell);
        _cellModel[cell] = model;
        _cellTemplate[cell] = model.PerGame ? -1 : template;
        _cellFit[cell] = model.PerGame
            ? Math.Min(1, Math.Min(_cellWidth / Math.Max(model.Size.X, 0.01f), _itemHeight / Math.Max(model.Size.Y, 0.01f)))
            : _fit[template];
        if (!model.AlwaysNodes)
        {
            return;
        }

        if (model.Scene is not null)
        {
            UseScene(cell);
            PlayClip(cell, model.HasClip(ModelClip.Idle) ? ClipNames[(int)ModelClip.Idle] : null, 0);
            return;
        }

        var node = _cellMesh[cell];
        node.Mesh = model.Mesh;
        node.MaterialOverride = _modelMaterials.TryGetValue(model, out var material) ? material : MaterialForUnprepared(model);
        node.Visible = true;
        _cellNode[cell] = node;
    }

    /// <summary>A model shown before <see cref="PrepareModel"/> (a template with an idle clip is always prepared).</summary>
    private ShaderMaterial MaterialForUnprepared(ItemTemplate model)
    {
        PrepareModel(model);
        return _modelMaterials[model];
    }

    /// <summary>Draws the cell with a copy of its model's node tree (from the model's pool), hiding its batched instance.</summary>
    private void UseScene(int cell)
    {
        if (_cellScene[cell] is not null || _cellModel[cell] is not { Scene: not null } model)
        {
            return;
        }

        RemoveInstance(cell);
        if (_cellNode[cell] is MeshInstance3D mesh)
        {
            mesh.Visible = false;
            mesh.Mesh = null;
        }

        if (!_scenePools.TryGetValue(model, out var pool))
        {
            _scenePools[model] = pool = new Stack<SceneInstance>();
        }

        if (!pool.TryPop(out var scene))
        {
            scene = Instantiate(model);
        }

        var material = _cellTemplate[cell] >= 0 ? _materials[_templateMaterial[_cellTemplate[cell]]]
            : _modelMaterials.TryGetValue(model, out var prepared) ? prepared : MaterialForUnprepared(model);
        foreach (var geometry in scene.Geometry)
        {
            geometry.MaterialOverride = material;
        }

        scene.Root.Visible = true;
        _cellScene[cell] = scene;
        _cellNode[cell] = scene.Root;
        scene.Root.Transform = _cellBase[cell];
        WriteCustom(cell);
    }

    /// <summary>Allocates: only the first time a model's node tree is needed in a cell (then it's pooled).</summary>
    private SceneInstance Instantiate(ItemTemplate model)
    {
        var root = (Node3D)model.Scene!.Duplicate();
        root.Visible = false;
        var geometry = new List<GeometryInstance3D>();
        AnimationPlayer? player = null;
        Collect(root);
        _root.AddChild(root);
        return new SceneInstance(model, root, [.. geometry], player);

        void Collect(Node node)
        {
            if (node is GeometryInstance3D g)
            {
                geometry.Add(g);
            }

            if (node is AnimationPlayer p)
            {
                player ??= p;
            }

            foreach (var child in node.GetChildren())
            {
                Collect(child);
            }
        }
    }

    /// <summary>Back to the MultiMesh (a batched model's cell whose clip has blended back to its rest pose).</summary>
    private void UseBatched(int cell)
    {
        var template = _cellTemplate[cell];
        if (_cellScene[cell] is null || template < 0 || _multiMeshes[template] is null)
        {
            return;
        }

        ReleaseNode(cell);
        PlaceInstance(cell, _cellBase[cell]);
        WriteCustom(cell);
    }

    private void ReleaseNode(int cell)
    {
        if (_cellScene[cell] is { } scene)
        {
            scene.Player?.Stop();
            scene.Root.Visible = false;
            _scenePools[scene.Template].Push(scene);
            _cellScene[cell] = null;
        }
        else if (_cellNode[cell] is MeshInstance3D mesh)
        {
            mesh.Visible = false;
            mesh.Mesh = null;
        }

        _cellNode[cell] = null;
    }

    private void PlayClip(int cell, StringName? clip, float blend)
    {
        if (_cellScene[cell]?.Player is not { } player)
        {
            return;
        }

        if (clip is null)
        {
            player.Stop();
        }
        else
        {
            player.Play(clip, blend);
        }
    }

    private void OnFocusEnter(int cell)
    {
        if (_cellModel[cell] is not { } model || _launchTime >= 0)
        {
            return;
        }

        if (model.FocusNodes)
        {
            UseScene(cell);
        }

        if (model.HasClip(ModelClip.Focused))
        {
            PlayClip(cell, ClipNames[(int)ModelClip.Focused], ClipBlendSeconds);
        }
    }

    private void OnFocusLeave(int cell)
    {
        if (_cellModel[cell] is not { } model || _cellScene[cell] is null)
        {
            return;
        }

        PlayClip(cell, model.HasClip(ModelClip.Idle) ? ClipNames[(int)ModelClip.Idle] : RestClip, ClipBlendSeconds);
    }
}
