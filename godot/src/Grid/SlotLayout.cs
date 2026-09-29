using System.Collections.Generic;
using Launcher.App.Models;
using Launcher.Core.Theming;

namespace Launcher.App.Grid;

/// <summary>
/// Which media slots a grid's templates show media in, and where each slot's texture layers are (A3, M6). Only a slot
/// whose chain names a media kind in some template gets layers ("load only the slots a template uses"). Media is
/// standardised to one size per slot (<see cref="MediaSlots.TextureSize"/>): the cover's layers are 512² and live in
/// the large array; every other slot's are 256² (mip 1 of the same derivative) in the small array. Each pool cell has
/// one layer per channel: layer = cell × (the class's channel count) + the channel's index in its class.
/// </summary>
public sealed class SlotLayout
{
    public static SlotLayout Empty { get; } = new([]);

    private readonly int[] _channelOf = new int[MediaSlots.Count];
    private readonly string[] _kinds;

    public SlotLayout(IEnumerable<ItemTemplate> templates)
    {
        var used = new bool[MediaSlots.Count];
        var kinds = new List<string>();
        foreach (var template in templates)
        {
            for (var slot = 0; slot < MediaSlots.Count; slot++)
            {
                if (template.Chain(slot) is not { UsesMedia: true } chain)
                {
                    continue;
                }

                used[slot] = true;
                foreach (var source in chain.Sources)
                {
                    if (source.Kind == SlotSourceKind.Media && !kinds.Contains(MediaSlots.Names[source.Slot]))
                    {
                        kinds.Add(MediaSlots.Names[source.Slot]);
                    }
                }
            }
        }

        var slots = new List<int>();
        for (var slot = 0; slot < MediaSlots.Count; slot++)
        {
            _channelOf[slot] = -1;
            if (!used[slot])
            {
                continue;
            }

            _channelOf[slot] = slots.Count;
            slots.Add(slot);
        }

        Slots = slots.ToArray();
        ClassIndex = new int[Slots.Length];
        for (var channel = 0; channel < Slots.Length; channel++)
        {
            if (IsLarge(channel))
            {
                ClassIndex[channel] = LargeCount++;
            }
            else
            {
                ClassIndex[channel] = SmallCount++;
            }
        }

        // Per-game models (media kind "model") are fetched with the slot media whenever a grid shows games.
        kinds.Add(Launcher.Core.Media.MediaKinds.Model);
        _kinds = kinds.ToArray();
    }

    /// <summary>The slot of each channel.</summary>
    public int[] Slots { get; }

    public int ChannelCount => Slots.Length;

    /// <summary>Each channel's index within its class array.</summary>
    public int[] ClassIndex { get; }

    public int LargeCount { get; }

    public int SmallCount { get; }

    /// <summary>The media kinds to fetch for these templates' chains, plus per-game models.</summary>
    public IReadOnlyList<string> MediaKinds => _kinds;

    /// <summary>The slot's channel, or -1 when no template shows media in it.</summary>
    public int ChannelOf(int slot) => _channelOf[slot];

    /// <summary>The cover-class channels use 512² layers; the rest 256².</summary>
    public bool IsLarge(int channel) => MediaSlots.TextureSize(Slots[channel]) == MediaSlots.TextureSize(MediaSlots.Cover);

    /// <summary>The layer of a cell's channel in its class array.</summary>
    public int LayerOf(int cell, int channel) => cell * (IsLarge(channel) ? LargeCount : SmallCount) + ClassIndex[channel];

    /// <summary>For logs and the bench report: "cover (512), back, spine (256)".</summary>
    public override string ToString()
    {
        var names = new List<string>();
        foreach (var slot in Slots)
        {
            names.Add($"{MediaSlots.Names[slot]} ({MediaSlots.TextureSize(slot)}²)");
        }

        return names.Count == 0 ? "no media slots" : string.Join(", ", names);
    }
}
