namespace Launcher.Core.Theming;

public enum SlotSourceKind
{
    /// <summary>The game's media of a kind, if it has it.</summary>
    Media,

    /// <summary>The launcher draws the slot (<see cref="MediaSlots.HasGenerator"/>).</summary>
    Generated,

    /// <summary>The material's own texture (or its base colour), as authored in the model.</summary>
    Authored,
}

/// <summary>One entry of a fallback chain.</summary>
/// <param name="Slot">The media kind's slot number for <see cref="SlotSourceKind.Media"/>; -1 otherwise.</param>
public readonly record struct SlotSource(SlotSourceKind Kind, int Slot)
{
    public static SlotSource Generated => new(SlotSourceKind.Generated, -1);

    public static SlotSource Authored => new(SlotSourceKind.Authored, -1);

    public static SlotSource Media(int slot) => new(SlotSourceKind.Media, slot);

    /// <summary>As written in a theme: a media kind, <c>generated</c> or <c>authored</c>.</summary>
    public override string ToString() => Kind switch
    {
        SlotSourceKind.Media => MediaSlots.Names[Slot],
        SlotSourceKind.Generated => "generated",
        _ => "authored",
    };
}

/// <summary>Where a game's media availability comes from, for <see cref="SlotChain.Resolve"/> (a struct, so resolving allocates nothing).</summary>
public interface IMediaAvailability
{
    /// <summary>Whether the game has media of the kind in slot number <paramref name="slot"/>.</summary>
    bool Has(int slot);
}

/// <summary>What a slot shows for one game.</summary>
/// <param name="MediaSlot">The media kind to show (a slot number), or -1 for none.</param>
/// <param name="Fallback">
/// What shows when there's no media, and while the media loads: the first <c>generated</c> or <c>authored</c> entry
/// after the media's, or <c>authored</c> when the chain ends.
/// </param>
/// <param name="Next">Where to carry on if the media turns out unusable (its derivative is missing or broken).</param>
public readonly record struct SlotResolution(int MediaSlot, SlotSourceKind Fallback, int Next);

/// <summary>
/// A slot's fallback chain (A7): the sources tried in order for each game, e.g. <c>back = ["back", "screenshot",
/// "generated"]</c>. Media kinds are tried until the game has one; <c>generated</c> or <c>authored</c> ends the chain;
/// and every chain ends, implicitly, with the material's authored texture.
/// </summary>
public sealed record SlotChain(int Slot, IReadOnlyList<SlotSource> Sources)
{
    /// <summary>A game template slot with no chain in its theme: the slot's own media, then generated if the launcher can draw it.</summary>
    public static SlotChain Default(int slot) => MediaSlots.HasGenerator(slot)
        ? new SlotChain(slot, [SlotSource.Media(slot), SlotSource.Generated])
        : new SlotChain(slot, [SlotSource.Media(slot)]);

    /// <summary>A system model's slot: systems have no media, so it's generated if it can be, else authored.</summary>
    public static SlotChain ForSystemModel(int slot) => MediaSlots.HasGenerator(slot)
        ? new SlotChain(slot, [SlotSource.Generated])
        : new SlotChain(slot, []);

    /// <summary>Whether any entry is a media kind (so the slot needs a texture layer per cell).</summary>
    public bool UsesMedia
    {
        get
        {
            foreach (var source in Sources)
            {
                if (source.Kind == SlotSourceKind.Media)
                {
                    return true;
                }
            }

            return false;
        }
    }

    /// <summary>
    /// Walks the chain from entry <paramref name="from"/>: the first media kind the game has wins, and a
    /// <c>generated</c> or <c>authored</c> entry stops the walk. Allocates nothing.
    /// </summary>
    public SlotResolution Resolve<TMedia>(int from, ref TMedia media)
        where TMedia : struct, IMediaAvailability
    {
        var count = Sources.Count;
        for (var i = Math.Max(from, 0); i < count; i++)
        {
            var source = Sources[i];
            if (source.Kind != SlotSourceKind.Media)
            {
                return new SlotResolution(-1, source.Kind, count);
            }

            if (!media.Has(source.Slot))
            {
                continue;
            }

            var fallback = SlotSourceKind.Authored;
            for (var j = i + 1; j < count; j++)
            {
                if (Sources[j].Kind != SlotSourceKind.Media)
                {
                    fallback = Sources[j].Kind;
                    break;
                }
            }

            return new SlotResolution(source.Slot, fallback, i + 1);
        }

        return new SlotResolution(-1, SlotSourceKind.Authored, count);
    }

    /// <summary>Chains are equal when they list the same sources in the same order.</summary>
    public bool Equals(SlotChain? other) => other is not null && other.Slot == Slot && other.Sources.SequenceEqual(Sources);

    public override int GetHashCode()
    {
        var hash = new HashCode();
        hash.Add(Slot);
        foreach (var source in Sources)
        {
            hash.Add(source);
        }

        return hash.ToHashCode();
    }

    public override string ToString() => $"{MediaSlots.Names[Slot]} = [{string.Join(", ", Sources.Select(s => $"\"{s}\""))}]";
}
