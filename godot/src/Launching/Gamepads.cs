using System.Collections.Generic;
using Godot;
using Launcher.Core.Launching.Controllers;

namespace Launcher.App.Launching;

/// <summary>
/// The pads connected when a game is launched, for its emulator's controller setup (ARCHITECTURE.md A5,
/// <c>auto_configure_controllers</c>). Godot reads pads through SDL3, as Eden does, so its GUIDs are the ones Eden
/// sees. Main thread only; called once a launch, never per frame.
/// </summary>
public static class Gamepads
{
    /// <summary>The pad holding A (the press that chose the game), or -1. Call it as the launch is chosen.</summary>
    public static int Pressing()
    {
        foreach (var device in Input.GetConnectedJoypads())
        {
            if (Input.IsJoyButtonPressed(device, JoyButton.A))
            {
                return device;
            }
        }

        return -1;
    }

    /// <summary>The connected pads in device order, with <paramref name="first"/> (a device, or -1) moved to the front.</summary>
    public static List<Gamepad> Snapshot(int first)
    {
        var devices = Input.GetConnectedJoypads();
        var pads = new List<Gamepad>(devices.Count);
        foreach (var device in devices)
        {
            pads.Add(new Gamepad(device, Input.GetJoyName(device), Input.GetJoyGuid(device)));
        }

        pads.Sort((a, b) => a.Device.CompareTo(b.Device));
        var index = pads.FindIndex(pad => pad.Device == first);
        if (index > 0)
        {
            var pad = pads[index];
            pads.RemoveAt(index);
            pads.Insert(0, pad);
        }

        return pads;
    }
}
