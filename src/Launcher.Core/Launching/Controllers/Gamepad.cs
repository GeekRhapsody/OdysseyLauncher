namespace Launcher.Core.Launching.Controllers;

/// <summary>
/// A controller connected when a game is launched, as the front end's SDL3 reports it (Godot reads pads through SDL3,
/// as Eden does, so the two see the same devices with the same GUIDs).
/// </summary>
/// <param name="Device">
/// The front end's device number. The emulator's SDL opens pads in the order they were connected, which this follows,
/// so it orders pads of one GUID (Eden's <c>port</c>).
/// </param>
/// <param name="Name">For the log.</param>
/// <param name="Guid">SDL's GUID as 32 hex digits (<c>SDL_GUIDToString</c>, Godot's <c>Input.GetJoyGuid</c>).</param>
public sealed record Gamepad(int Device, string Name, string Guid);
