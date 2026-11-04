using System.Globalization;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// The battery and the network from the kernel's files, as Windows' <c>WindowsDeviceStatus</c> reads them from its
/// APIs. The battery is the first system battery in <c>/sys/class/power_supply</c> (<c>type</c> Battery, its
/// <c>scope</c> not Device: a pad's battery is listed there too), plugged in when a Mains or USB supply is online,
/// or, with none listed, when the battery isn't discharging. The connection is the default route's interface
/// (<c>/proc/net/route</c>) when it's a connected hardware adapter (it has a <c>device</c>, and its <c>operstate</c>
/// is up), else the first connected Wi-Fi adapter, else the first other connected one, so a VPN or a container's
/// bridge doesn't hide the real link. Wi-Fi is an adapter with <c>wireless</c> or <c>phy80211</c>; its signal is the
/// level in <c>/proc/net/wireless</c>, in dBm, made 0–100 as NetworkManager does (2 × (dBm + 100)).
/// </summary>
/// <param name="root">The file system's root: <c>/</c>, or a test's made-up one.</param>
public sealed class LinuxDeviceStatus(string root) : IDeviceStatus
{
    /// <summary>RTF_UP in a route's flags.</summary>
    private const int RouteUp = 0x1;

    private readonly string _powerSupplies = Path.Combine(root, "sys", "class", "power_supply");
    private readonly string _interfaces = Path.Combine(root, "sys", "class", "net");
    private readonly string _routes = Path.Combine(root, "proc", "net", "route");
    private readonly string _wireless = Path.Combine(root, "proc", "net", "wireless");

    public BatteryState ReadBattery()
    {
        string[] supplies;
        try
        {
            supplies = Directory.GetFileSystemEntries(_powerSupplies);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return BatteryState.None;
        }

        Array.Sort(supplies, StringComparer.Ordinal);
        string? battery = null;
        bool? mains = null;
        foreach (var supply in supplies)
        {
            switch (Read(supply, "type"))
            {
                case "Mains" or "USB":
                    mains = mains == true || Read(supply, "online") == "1";
                    break;
                case "Battery" when battery is null && Read(supply, "scope") != "Device" && Read(supply, "present") != "0":
                    battery = supply;
                    break;
            }
        }

        if (battery is null)
        {
            return BatteryState.None;
        }

        var percent = int.TryParse(Read(battery, "capacity"), NumberStyles.Integer, CultureInfo.InvariantCulture, out var capacity)
            ? Math.Clamp(capacity, 0, 100)
            : -1;
        var pluggedIn = mains ?? Read(battery, "status") is "Charging" or "Full" or "Not charging";
        return new BatteryState(true, percent, pluggedIn);
    }

    public NetworkState ReadNetwork()
    {
        string[] interfaces;
        try
        {
            interfaces = Directory.GetFileSystemEntries(_interfaces);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return NetworkState.Unknown;
        }

        Array.Sort(interfaces, StringComparer.Ordinal);
        var best = DefaultRouteInterface();
        string? chosen = null;
        string? wifi = null;
        string? wired = null;
        foreach (var adapter in interfaces)
        {
            if (!Directory.Exists(Path.Combine(adapter, "device")) || Read(adapter, "operstate") != "up")
            {
                continue;
            }

            var name = Path.GetFileName(adapter);
            if (name == best)
            {
                chosen = adapter;
                break;
            }

            if (IsWifi(adapter))
            {
                wifi ??= adapter;
            }
            else
            {
                wired ??= adapter;
            }
        }

        chosen ??= wifi ?? wired;
        if (chosen is null)
        {
            return new NetworkState(NetworkKind.Disconnected);
        }

        return IsWifi(chosen)
            ? new NetworkState(NetworkKind.Wireless, DeviceStatus.SignalBars(SignalQuality(Path.GetFileName(chosen))))
            : new NetworkState(NetworkKind.Wired);
    }

    private static bool IsWifi(string adapter) =>
        Directory.Exists(Path.Combine(adapter, "wireless")) || Directory.Exists(Path.Combine(adapter, "phy80211"));

    /// <summary>A one-line attribute file's value, trimmed, or null when it can't be read (a supply that's gone, say).</summary>
    private static string? Read(string folder, string name)
    {
        try
        {
            return File.ReadAllText(Path.Combine(folder, name)).Trim();
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    /// <summary>The interface of the IPv4 default route with the lowest metric, or null.</summary>
    private string? DefaultRouteInterface()
    {
        string[] lines;
        try
        {
            lines = File.ReadAllLines(_routes);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return null;
        }

        // Iface Destination Gateway Flags RefCnt Use Metric Mask ..., in hex; the first line is the header.
        string? best = null;
        var bestMetric = int.MaxValue;
        foreach (var line in lines.AsSpan(Math.Min(1, lines.Length)))
        {
            var fields = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
            if (fields.Length < 8
                || fields[1] != "00000000"
                || fields[7] != "00000000"
                || !int.TryParse(fields[3], NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var flags)
                || (flags & RouteUp) == 0
                || !int.TryParse(fields[6], NumberStyles.Integer, CultureInfo.InvariantCulture, out var metric)
                || metric >= bestMetric)
            {
                continue;
            }

            best = fields[0];
            bestMetric = metric;
        }

        return best;
    }

    /// <summary>The adapter's signal quality, 0–100, from its level in dBm; −1 when it isn't listed or isn't in dBm.</summary>
    private int SignalQuality(string adapter)
    {
        string[] lines;
        try
        {
            lines = File.ReadAllLines(_wireless);
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            return -1;
        }

        // " wlan0: 0000   54.  -56.  -256  ...": status, then quality's link, level and noise, each ending in '.'
        // when it's been updated. A level of 0 or more isn't in dBm (an old driver's own scale): unknown.
        foreach (var line in lines)
        {
            var colon = line.IndexOf(':', StringComparison.Ordinal);
            if (colon < 0 || !line.AsSpan(0, colon).Trim().SequenceEqual(adapter))
            {
                continue;
            }

            var fields = line[(colon + 1)..].Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
            return fields.Length >= 3
                && int.TryParse(fields[2].TrimEnd('.'), NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out var level)
                && level < 0
                ? Math.Clamp(2 * (level + 100), 0, 100)
                : -1;
        }

        return -1;
    }
}
