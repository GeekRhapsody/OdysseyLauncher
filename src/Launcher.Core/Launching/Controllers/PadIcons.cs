using Launcher.Core.Config;

namespace Launcher.Core.Launching.Controllers;

/// <summary>
/// Which buttons a pad has, for the controls' hints (docs/ARCHITECTURE.md A1, "Button icons"), from its SDL GUID.
/// The hints show the glyph at each button's position (Godot's <c>JoyButton.A</c> is the bottom face button on every
/// pad), so a Nintendo-labelled pad's confirm button shows as its B.
/// </summary>
public static class PadIcons
{
    private const ushort Sony = 0x054c;

    /// <summary>
    /// PlayStation for Sony's pads; GameCube for GameCube pads (<see cref="SdlMapping.IsGameCube"/>); Nintendo for those
    /// labelled as a Switch's (<see cref="SdlMapping.HasNintendoLabels"/>: a Switch 2's too); the Steam Deck for its own
    /// controls, for the new Steam Controller (the same buttons) and, while the Deck's controls are connected
    /// (<paramref name="deckConnected"/>), for the Xbox 360 pad Steam Input makes of them (as <see cref="EdenControllers"/>
    /// takes it to be); the Steam Controller for the 2015 one; Xbox for anything else.
    /// </summary>
    public static ButtonIcons Of(SdlGuid guid, bool deckConnected)
    {
        ArgumentNullException.ThrowIfNull(guid);
        if (guid.HasIds && guid.Vendor == Sony)
        {
            return ButtonIcons.PlayStation;
        }

        if (SdlMapping.IsGameCube(guid))
        {
            return ButtonIcons.GameCube;
        }

        if (SdlMapping.HasNintendoLabels(guid))
        {
            return ButtonIcons.Nintendo;
        }

        if (guid.IsSteamDeck || guid.IsNewSteamController || (deckConnected && guid.IsXInput360))
        {
            return ButtonIcons.SteamDeck;
        }

        return guid.IsSteamController ? ButtonIcons.SteamController : ButtonIcons.Xbox;
    }
}
