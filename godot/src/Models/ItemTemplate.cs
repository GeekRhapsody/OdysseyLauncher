using Godot;
using Launcher.Core.Models;
using Launcher.Core.Theming;

namespace Launcher.App.Models;

/// <summary>
/// A model remapped onto the launcher's one item shader (A7): every surface merged into one, so a MultiMesh of it is a
/// single draw call. Per vertex, COLOR carries the material's base colour (linear) and roughness, and UV2 the face
/// code (which media slot the material is, and which of the template's authored textures it samples) and the face's
/// aspect ratio. A model with idle, focused or launch clips also has its node tree (<see cref="Scene"/>), which the
/// grid duplicates for the cells that play a clip. Built by <see cref="ModelConverter"/>; shared by every grid cell
/// that uses it.
/// </summary>
public sealed class ItemTemplate
{
    /// <summary>Authored textures a template's materials can sample (the shader's <c>authored_1..4</c>). A7's budget is 4 materials.</summary>
    public const int MaxAuthoredTextures = 4;

    private readonly SlotChain?[] _chains;
    private readonly bool[] _whole;
    private readonly float[] _slotAspects;
    private readonly Animation?[] _clips;

    public ItemTemplate(ModelCandidate candidate, bool systemCard, ConvertedModel model)
    {
        Key = candidate.Key;
        Path = candidate.Path;
        Description = candidate.Description;
        Tint = candidate.Tint;
        PerGame = candidate.Level == ModelLevel.UserGame;

        // A6 shape = "media": only for a static game template, whose one merged mesh the shader reshapes.
        ShapeFromMedia = !systemCard && !PerGame && candidate.Template?.ShapeFromMedia == true && model.Scene is null;
        ShapeSlot = model.SlotAspects[MediaSlots.Cover] > 0 || model.SlotAspects[MediaSlots.Screenshot] <= 0 ? MediaSlots.Cover : MediaSlots.Screenshot;
        Mesh = model.Mesh;
        Scene = model.Scene;
        Size = model.Size;
        Triangles = model.Triangles;
        Authored = model.Authored;
        _clips = model.Clips;
        _slotAspects = model.SlotAspects;
        _chains = new SlotChain?[MediaSlots.Count];
        _whole = new bool[MediaSlots.Count];
        for (var slot = 0; slot < MediaSlots.Count; slot++)
        {
            if (model.SlotAspects[slot] > 0)
            {
                _chains[slot] = candidate.ChainFor(slot, systemCard);
                _whole[slot] = !systemCard && candidate.Template?.ShowsWhole(slot) == true;
            }
        }

        LaunchSeconds = ModelConverter.LaunchSeconds(model.Clips[(int)ModelClip.Launch]);
    }

    /// <summary><see cref="ModelCandidate.Key"/>: the file, its chains and its tint.</summary>
    public string Key { get; }

    /// <summary>The file it was loaded from.</summary>
    public string Path { get; }

    public string Description { get; }

    /// <summary>The merged rest-pose mesh.</summary>
    public ArrayMesh Mesh { get; }

    /// <summary>The node tree, for a model with clips (not in the scene tree: duplicate it). Null for a static model.</summary>
    public Node3D? Scene { get; }

    /// <summary>The bounding box: the model stands on y = 0, centred on x and z, its largest side 1 m.</summary>
    public Vector3 Size { get; }

    public int Triangles { get; }

    /// <summary>A system card whose plain materials take the system's colour.</summary>
    public bool Tint { get; }

    /// <summary>One game's own model (A7 level 1): drawn on its own node, never in a template's MultiMesh.</summary>
    public bool PerGame { get; }

    /// <summary>
    /// Each game's box takes its shape from its cover and spine (<see cref="BoxShape"/>; the grid reshapes the mesh in
    /// the item shader). Only a static game template's.
    /// </summary>
    public bool ShapeFromMedia { get; }

    /// <summary>
    /// The front slot a reshaped box takes its proportions from: the cover, or for a model with no cover but a
    /// screenshot (a flat screenshot card), the screenshot.
    /// </summary>
    public int ShapeSlot { get; }

    /// <summary>The textures its materials were authored with, by the index their faces carry.</summary>
    public Texture2D?[] Authored { get; }

    /// <summary>How long the launch clip plays before the emulator starts (at most 2 s); 0 without one.</summary>
    public float LaunchSeconds { get; }

    public bool HasClip(ModelClip clip) => Scene is not null && _clips[(int)clip] is not null;

    /// <summary>
    /// A model with an idle clip plays it in every cell, so it's always drawn as nodes; one with only focused or launch
    /// clips is batched, and the focused cell swaps to a node while it plays them.
    /// </summary>
    public bool AlwaysNodes => PerGame || HasClip(ModelClip.Idle);

    /// <summary>Whether the focused cell needs its node tree (to play a focused or launch clip).</summary>
    public bool FocusNodes => HasClip(ModelClip.Focused) || HasClip(ModelClip.Launch);

    /// <summary>Whether the model has a material for the slot.</summary>
    public bool HasSlot(int slot) => _chains[slot] is not null;

    /// <summary>The slot's fallback chain, or null when the model has no such material.</summary>
    public SlotChain? Chain(int slot) => _chains[slot];

    /// <summary>Whether the slot's art is drawn whole, fitted inside the face (its template's <c>fit = "whole"</c>).</summary>
    public bool ShowsWhole(int slot) => _whole[slot];

    /// <summary>The slot face's width over its height (0 when the model has no such material).</summary>
    public float SlotAspect(int slot) => _slotAspects[slot];
}
