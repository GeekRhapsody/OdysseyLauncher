using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using static Launcher.Core.Platform.Windows.NativeMethods;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// The battery from <c>GetSystemPowerStatus</c>, and the network from the interface table (<c>GetIfTable2</c>): the
/// connection is the default route's interface (<c>GetBestInterface</c>, which only reads the routing table) when it's
/// a connected hardware adapter, else the first connected Wi-Fi adapter, else the first connected Ethernet one, so a
/// VPN or a Hyper-V switch over the real adapter still shows the real link. A Wi-Fi connection's signal comes from the
/// WLAN service (<c>WlanQueryInterface</c>); without it, the bars are unknown. Native memory only: nothing managed is
/// allocated per read. Reads are serialised by <see cref="DeviceStatusMonitor"/>.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed unsafe class WindowsDeviceStatus : IDeviceStatus, IDisposable
{
    /// <summary>8.8.8.8, the same in either byte order: a public address, so its route is the default route.</summary>
    private const uint PublicAddress = 0x0808_0808;

    private nint _wlan;
    private bool _wlanUnavailable;

    public BatteryState ReadBattery()
    {
        if (!GetSystemPowerStatus(out var status) || status.BatteryFlag is BatteryFlagNoSystemBattery or BatteryFlagUnknown)
        {
            return BatteryState.None;
        }

        var percent = status.BatteryLifePercent == BatteryPercentUnknown ? -1 : Math.Min((int)status.BatteryLifePercent, 100);
        return new BatteryState(true, percent, status.AcLineStatus == AcLineOnline);
    }

    public NetworkState ReadNetwork()
    {
        if (GetIfTable2(out var table) != 0 || table == 0)
        {
            return NetworkState.Unknown;
        }

        try
        {
            var count = *(uint*)table;
            var rows = (MibIfRow2*)(table + IfTable2RowsOffset);
            var best = GetBestInterface(PublicAddress, out var index) == 0 ? index : 0u;
            MibIfRow2* chosen = null;
            MibIfRow2* wifi = null;
            MibIfRow2* wired = null;
            for (var i = 0; i < count; i++)
            {
                var row = rows + i;
                if (!IsConnectedAdapter(row))
                {
                    continue;
                }

                if (best != 0 && row->InterfaceIndex == best)
                {
                    chosen = row;
                    break;
                }

                if (IsWifi(row))
                {
                    wifi = wifi == null ? row : wifi;
                }
                else if (row->Type == IfTypeEthernetCsmacd)
                {
                    wired = wired == null ? row : wired;
                }
            }

            chosen = chosen != null ? chosen : wifi != null ? wifi : wired;
            if (chosen == null)
            {
                return new NetworkState(NetworkKind.Disconnected);
            }

            return IsWifi(chosen)
                ? new NetworkState(NetworkKind.Wireless, DeviceStatus.SignalBars(SignalQuality(chosen->InterfaceGuid)))
                : new NetworkState(NetworkKind.Wired);
        }
        finally
        {
            FreeMibTable(table);
        }
    }

    /// <summary>A physical adapter, up and with its medium connected (Wi-Fi associated, a cable in).</summary>
    private static bool IsConnectedAdapter(MibIfRow2* row) =>
        (row->Flags & IfFlagHardwareInterface) != 0
        && row->OperStatus == IfOperStatusUp
        && row->MediaConnectState == MediaConnectStateConnected
        && (row->Type is IfTypeEthernetCsmacd or IfTypeIeee80211 || row->PhysicalMediumType == NdisPhysicalMediumNative80211);

    private static bool IsWifi(MibIfRow2* row) =>
        row->Type == IfTypeIeee80211 || row->PhysicalMediumType == NdisPhysicalMediumNative80211;

    /// <summary>The connection's signal quality, 0–100, or −1 when the WLAN service can't say.</summary>
    private int SignalQuality(Guid adapter)
    {
        if (!OpenWlan())
        {
            return -1;
        }

        if (WlanQueryInterface(_wlan, adapter, WlanIntfOpcodeCurrentConnection, 0, out var size, out var data, 0) != 0 || data == 0)
        {
            return -1;
        }

        try
        {
            if (size < WlanConnectionSignalQualityOffset + sizeof(uint) || *(uint*)data != WlanInterfaceStateConnected)
            {
                return -1;
            }

            return (int)Math.Min(*(uint*)(data + WlanConnectionSignalQualityOffset), 100u);
        }
        finally
        {
            WlanFreeMemory(data);
        }
    }

    /// <summary>Opens the WLAN client handle once; false for good when the service or its DLL is missing.</summary>
    private bool OpenWlan()
    {
        if (_wlan != 0)
        {
            return true;
        }

        if (_wlanUnavailable)
        {
            return false;
        }

        try
        {
            if (WlanOpenHandle(WlanClientVersion2, 0, out _, out var handle) == 0)
            {
                _wlan = handle;
                return true;
            }
        }
        catch (DllNotFoundException)
        {
            // Windows Server without the Wireless LAN feature.
        }
        catch (EntryPointNotFoundException)
        {
        }

        _wlanUnavailable = true;
        return false;
    }

    public void Dispose()
    {
        if (_wlan != 0)
        {
            _ = WlanCloseHandle(_wlan, 0);
            _wlan = 0;
        }
    }

    /// <summary>For tests: every row of the interface table, as (index, type, connected hardware adapter).</summary>
    internal static List<(uint Index, uint Type, bool ConnectedAdapter)> ReadInterfaceTable()
    {
        var result = new List<(uint, uint, bool)>();
        if (GetIfTable2(out var table) != 0)
        {
            throw new InvalidOperationException("GetIfTable2 failed.");
        }

        try
        {
            var count = *(uint*)table;
            var rows = (MibIfRow2*)(table + IfTable2RowsOffset);
            for (var i = 0; i < count; i++)
            {
                result.Add((rows[i].InterfaceIndex, rows[i].Type, IsConnectedAdapter(rows + i)));
            }
        }
        finally
        {
            FreeMibTable(table);
        }

        return result;
    }

    /// <summary>For tests: the size the struct is laid out with.</summary>
    internal static int RowSize => Marshal.SizeOf<MibIfRow2>();
}
