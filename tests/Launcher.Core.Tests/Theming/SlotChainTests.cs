using Launcher.Core.Theming;

namespace Launcher.Core.Tests.Theming;

public sealed class SlotChainTests
{
    /// <summary>The media kinds a game has, as slot numbers.</summary>
    private readonly struct Game(params int[] slots) : IMediaAvailability
    {
        private readonly int[] _slots = slots;

        public bool Has(int slot) => _slots is not null && Array.IndexOf(_slots, slot) >= 0;
    }

    private static SlotChain Chain(int slot, params SlotSource[] sources) => new(slot, sources);

    private static SlotResolution Resolve(SlotChain chain, Game media, int from = 0) => chain.Resolve(from, ref media);

    private static readonly SlotChain Back = Chain(
        MediaSlots.Back, SlotSource.Media(MediaSlots.Back), SlotSource.Media(MediaSlots.Screenshot), SlotSource.Generated);

    [Fact]
    public void The_first_media_kind_the_game_has_wins_and_the_next_non_media_entry_shows_until_it_loads()
    {
        Assert.Equal(new SlotResolution(MediaSlots.Back, SlotSourceKind.Generated, 1), Resolve(Back, new Game(MediaSlots.Back, MediaSlots.Screenshot)));
        Assert.Equal(new SlotResolution(MediaSlots.Screenshot, SlotSourceKind.Generated, 2), Resolve(Back, new Game(MediaSlots.Screenshot)));
    }

    [Fact]
    public void Missing_media_falls_through_to_generated()
    {
        Assert.Equal(new SlotResolution(-1, SlotSourceKind.Generated, 3), Resolve(Back, new Game(MediaSlots.Cover)));
    }

    [Fact]
    public void Media_that_turns_out_unusable_carries_on_from_the_next_entry()
    {
        // The back's derivative is missing: resolving again from Next tries the screenshot.
        var first = Resolve(Back, new Game(MediaSlots.Back, MediaSlots.Screenshot));
        Assert.Equal(new SlotResolution(MediaSlots.Screenshot, SlotSourceKind.Generated, 2), Resolve(Back, new Game(MediaSlots.Back, MediaSlots.Screenshot), first.Next));

        var second = Resolve(Back, new Game(MediaSlots.Screenshot), 1);
        Assert.Equal(new SlotResolution(-1, SlotSourceKind.Generated, 3), Resolve(Back, new Game(MediaSlots.Screenshot), second.Next));
    }

    [Fact]
    public void Every_chain_ends_with_the_authored_texture()
    {
        var screenshot = Chain(MediaSlots.Screenshot, SlotSource.Media(MediaSlots.Screenshot), SlotSource.Media(MediaSlots.Hero));
        Assert.Equal(new SlotResolution(-1, SlotSourceKind.Authored, 2), Resolve(screenshot, new Game()));
        Assert.Equal(new SlotResolution(MediaSlots.Hero, SlotSourceKind.Authored, 2), Resolve(screenshot, new Game(MediaSlots.Hero)));
        Assert.Equal(new SlotResolution(-1, SlotSourceKind.Authored, 0), Resolve(Chain(MediaSlots.Logo), new Game(MediaSlots.Logo)));
    }

    [Fact]
    public void A_non_media_entry_stops_the_walk_even_if_media_come_after_it()
    {
        var chain = Chain(MediaSlots.Back, SlotSource.Authored, SlotSource.Media(MediaSlots.Back));
        Assert.Equal(new SlotResolution(-1, SlotSourceKind.Authored, 2), Resolve(chain, new Game(MediaSlots.Back)));
    }

    [Fact]
    public void Default_chains_try_the_slots_own_kind_then_generated_where_the_launcher_can_draw_it()
    {
        Assert.Equal([SlotSource.Media(MediaSlots.Cover), SlotSource.Generated], SlotChain.Default(MediaSlots.Cover).Sources);
        Assert.Equal([SlotSource.Media(MediaSlots.Label), SlotSource.Generated], SlotChain.Default(MediaSlots.Label).Sources);
        Assert.Equal([SlotSource.Media(MediaSlots.Hero)], SlotChain.Default(MediaSlots.Hero).Sources);
        Assert.True(SlotChain.Default(MediaSlots.Hero).UsesMedia);

        // System cards have no media: generated if possible, else the authored texture.
        Assert.Equal([SlotSource.Generated], SlotChain.ForSystemModel(MediaSlots.Label).Sources);
        Assert.Empty(SlotChain.ForSystemModel(MediaSlots.Logo).Sources);
        Assert.False(SlotChain.ForSystemModel(MediaSlots.Cover).UsesMedia);
    }

    [Fact]
    public void Media_is_standardised_to_512_for_the_cover_and_256_for_every_other_slot()
    {
        Assert.Equal(512, MediaSlots.TextureSize(MediaSlots.Cover));
        for (var slot = 1; slot < MediaSlots.Count; slot++)
        {
            Assert.Equal(256, MediaSlots.TextureSize(slot));
        }
    }
}
