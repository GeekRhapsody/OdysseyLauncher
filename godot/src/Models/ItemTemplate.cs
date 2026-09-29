using Godot;
using Launcher.Core.Theming;

namespace Launcher.App.Models;

/// <summary>
/// A model remapped onto the launcher's one item shader (A7): every surface merged into one, so a MultiMesh of it is a
/// single draw call. Per vertex, COLOR carries the material's base colour (linear) and roughness, and UV2 the face
/// code (which media slot the material is, and which of the template's authored textures it samples) and the face's
/// aspect ratio. Built by <see cref="ModelConverter"/>; shared by every grid cell that uses it.
/// </summary>
public sealed class ItemTemplate
{
    /// <summary>Authored textures a template's materials can sample (the shader's <c>authored_1..4</c>). A7's budget is 4 materials.</summary>
    public const int MaxAuthoredTextures = 4;

    private readonly SlotChain?[] _chains;
    private readonly float[] _slotAspects;

    public ItemTemplate(ModelCandidate candidate, bool systemCard, ConvertedModel model)
    {
        Key = candidate.Key;
        Description = candidate.Description;
        Tint = candidate.Tint;
        Mesh = model.Mesh!;
        Size = model.Size;
        Authored = model.Authored;
        _slotAspects = model.SlotAspects;
        _chains = new SlotChain?[MediaSlots.Count];
        for (var slot = 0; slot < MediaSlots.Count; slot++)
        {
            if (model.SlotAspects[slot] > 0)
            {
                _chains[slot] = candidate.ChainFor(slot, systemCard);
            }
        }
    }

    /// <summary><see cref="ModelCandidate.Key"/>: the file, its chains and its tint.</summary>
    public string Key { get; }

    public string Description { get; }

    public ArrayMesh Mesh { get; }

    /// <summary>The bounding box: the model stands on y = 0, centred on x and z, its largest side 1 m.</summary>
    public Vector3 Size { get; }

    /// <summary>A system card whose plain materials take the system's colour.</summary>
    public bool Tint { get; }

    /// <summary>The textures its materials were authored with, by the index their faces carry.</summary>
    public Texture2D?[] Authored { get; }

    /// <summary>Whether the model has a material for the slot.</summary>
    public bool HasSlot(int slot) => _chains[slot] is not null;

    /// <summary>The slot's fallback chain, or null when the model has no such material.</summary>
    public SlotChain? Chain(int slot) => _chains[slot];

    /// <summary>The slot face's width over its height (0 when the model has no such material).</summary>
    public float SlotAspect(int slot) => _slotAspects[slot];
}
