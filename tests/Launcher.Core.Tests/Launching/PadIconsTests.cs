using Launcher.Core.Config;
using Launcher.Core.Launching.Controllers;

namespace Launcher.Core.Tests.Launching;

public sealed class PadIconsTests
{
    // The Deck's two GUIDs are those Godot reported on the owner's Steam Deck (EdenControllersTests).
    private const string Deck = "0300f617de2800000512000000026800";
    private const string Xbox360 = "0300fa675e0400008e02000014017801";

    [Theory]
    [InlineData("03001a2b5e040000130b000009057801", ButtonIcons.Xbox)]          // Xbox Series pad, XInput
    [InlineData("0500c5824c050000e60c000000016800", ButtonIcons.PlayStation)]   // DualSense, HIDAPI
    [InlineData("030000007e0500000920000000006800", ButtonIcons.Nintendo)]      // Switch Pro, HIDAPI
    [InlineData("03000000c82d00000960000000006800", ButtonIcons.Nintendo)]      // 8BitDo Pro 3 in Switch mode
    [InlineData("030000007e0500006920000000006800", ButtonIcons.Nintendo)]      // Switch 2 Pro: a Switch's buttons
    [InlineData("030000007e0500003703000000006800", ButtonIcons.GameCube)]      // GameCube adapter
    [InlineData("03000000790000004318000000006800", ButtonIcons.GameCube)]      // EVORETRO GameCube adapter
    [InlineData("030000007e0500007320000000006800", ButtonIcons.GameCube)]      // Switch 2 GameCube controller
    [InlineData("03000000de2800000211000000006800", ButtonIcons.SteamController)] // 2015 Steam Controller, wired
    [InlineData("03000000de2800004211000000006800", ButtonIcons.SteamController)] // 2015 Steam Controller, wireless
    [InlineData("03000000de2800000213000000006800", ButtonIcons.SteamDeck)]     // New Steam Controller: the Deck's buttons
    [InlineData("03000000de2800000413000000006800", ButtonIcons.SteamDeck)]     // New Steam Controller's dongle
    [InlineData("03000000de280000ff11000000007801", ButtonIcons.Xbox)]          // Steam's virtual gamepad
    [InlineData("03000000790000000600000000000000", ButtonIcons.Xbox)]          // A DirectInput pad
    [InlineData(Deck, ButtonIcons.SteamDeck)]
    [InlineData(Xbox360, ButtonIcons.Xbox)]
    public void A_pad_shows_the_buttons_its_guid_names(string guid, ButtonIcons expected) =>
        Assert.Equal(expected, PadIcons.Of(SdlGuid.TryParse(guid)!, deckConnected: false));

    [Fact]
    public void Steam_inputs_xbox_360_pad_is_the_decks_controls_while_the_deck_is_there()
    {
        Assert.Equal(ButtonIcons.SteamDeck, PadIcons.Of(SdlGuid.TryParse(Xbox360)!, deckConnected: true));

        // Another XInput pad beside the Deck is still an Xbox pad.
        Assert.Equal(ButtonIcons.Xbox, PadIcons.Of(SdlGuid.TryParse("03001a2b5e040000130b000009057801")!, deckConnected: true));
    }
}
