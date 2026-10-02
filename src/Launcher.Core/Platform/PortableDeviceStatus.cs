using System.Net.NetworkInformation;

namespace Launcher.Core.Platform;

/// <summary>
/// Linux, until it's worth doing more: no battery, and the network from .NET's interface list (the first adapter
/// that's up with a gateway; Wi-Fi without its signal).
/// </summary>
public sealed class PortableDeviceStatus : IDeviceStatus
{
    public BatteryState ReadBattery() => BatteryState.None;

    public NetworkState ReadNetwork()
    {
        var wired = false;
        foreach (var adapter in NetworkInterface.GetAllNetworkInterfaces())
        {
            if (adapter.OperationalStatus != OperationalStatus.Up
                || adapter.NetworkInterfaceType is NetworkInterfaceType.Loopback or NetworkInterfaceType.Tunnel
                || adapter.GetIPProperties().GatewayAddresses.Count == 0)
            {
                continue;
            }

            if (adapter.NetworkInterfaceType == NetworkInterfaceType.Wireless80211)
            {
                return new NetworkState(NetworkKind.Wireless);
            }

            wired = true;
        }

        return new NetworkState(wired ? NetworkKind.Wired : NetworkKind.Disconnected);
    }
}
