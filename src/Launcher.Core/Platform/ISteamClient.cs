namespace Launcher.Core.Platform;

/// <summary>
/// What the Steam client says about one app (ARCHITECTURE.md A1, Launching). Steam starts its games itself, so a
/// Steam shortcut's game is followed through these, not through a process the launcher started.
/// </summary>
/// <param name="ClientRunning">The Steam client is running.</param>
/// <param name="Installed">Steam says the app is installed.</param>
/// <param name="Running">
/// The app's own running flag. Steam can leave it set after the game has gone, so it's trusted only once it has
/// been seen clear (<see cref="Launching.SteamGame"/>).
/// </param>
/// <param name="Current">Steam's current game is this app.</param>
/// <param name="Updating">Steam is downloading or installing the app.</param>
public readonly record struct SteamAppState(bool ClientRunning, bool Installed, bool Running, bool Current, bool Updating);

/// <summary>Reads the Steam client's state. Cheap, with no network; any thread, but not the main thread (Windows: the registry).</summary>
public interface ISteamClient
{
    /// <summary>The Steam client's program, or null if Steam isn't installed for this user.</summary>
    string? ClientPath { get; }

    /// <summary>What Steam says about <paramref name="appId"/> right now.</summary>
    SteamAppState GetAppState(uint appId);
}
