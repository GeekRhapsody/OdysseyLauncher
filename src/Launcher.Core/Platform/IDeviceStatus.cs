namespace Launcher.Core.Platform;

/// <summary>The battery, as the status indicators show it.</summary>
/// <param name="Present">False on a device without a battery (a desktop PC), or when it can't be read.</param>
/// <param name="Percent">The charge, 0 to 100, or −1 when the system doesn't know it.</param>
/// <param name="PluggedIn">On mains power (charging, or full and held there).</param>
public readonly record struct BatteryState(bool Present, int Percent, bool PluggedIn)
{
    public static BatteryState None => default;
}

public enum NetworkKind
{
    /// <summary>It couldn't be read: the network indicator hides.</summary>
    Unknown,
    Disconnected,

    /// <summary>A cable (Ethernet).</summary>
    Wired,
    Wireless,
}

/// <param name="SignalBars">For Wi-Fi, 0 to 3 (<see cref="DeviceStatus.SignalBars"/>); −1 when unknown or not Wi-Fi.</param>
public readonly record struct NetworkState(NetworkKind Kind, int SignalBars = -1)
{
    public static NetworkState Unknown => new(NetworkKind.Unknown);
}

/// <summary>The battery icon for a <see cref="BatteryState"/>.</summary>
public enum BatteryLevel
{
    Full,
    Medium,
    Low,

    /// <summary>10% or less, on battery.</summary>
    Warning,

    /// <summary>Plugged in and not yet full.</summary>
    Charging,
}

/// <summary>What the status indicators show: one snapshot, compared whole to tell whether anything changed.</summary>
public readonly record struct DeviceStatus(BatteryState Battery, NetworkState Network)
{
    public static DeviceStatus Unknown => new(BatteryState.None, NetworkState.Unknown);

    /// <summary>Wi-Fi signal quality (0–100, as Windows reports it) as bars: 0 below 25, then one more every 25.</summary>
    public static int SignalBars(int qualityPercent) => qualityPercent switch
    {
        < 0 => -1,
        < 25 => 0,
        < 50 => 1,
        < 75 => 2,
        _ => 3,
    };

    /// <summary>Which battery icon shows: charging while plugged in and not full, a warning at 10% or less.</summary>
    public static BatteryLevel LevelOf(BatteryState battery)
    {
        if (battery.PluggedIn && battery.Percent is < 100)
        {
            return BatteryLevel.Charging;
        }

        return battery.Percent switch
        {
            < 0 => BatteryLevel.Full,
            <= 10 => battery.PluggedIn ? BatteryLevel.Low : BatteryLevel.Warning,
            <= 35 => BatteryLevel.Low,
            <= 70 => BatteryLevel.Medium,
            _ => BatteryLevel.Full,
        };
    }
}

/// <summary>
/// Reads the battery and the network for the status indicators (top right). Called on a worker thread, a few times a
/// minute (<see cref="DeviceStatusMonitor"/>); never throws for a state it can't read.
/// </summary>
public interface IDeviceStatus
{
    BatteryState ReadBattery();

    NetworkState ReadNetwork();
}

/// <summary>A made-up state, for captures (<c>--fake-status</c>).</summary>
public sealed class FixedDeviceStatus(DeviceStatus status) : IDeviceStatus
{
    public BatteryState ReadBattery() => status.Battery;

    public NetworkState ReadNetwork() => status.Network;
}
