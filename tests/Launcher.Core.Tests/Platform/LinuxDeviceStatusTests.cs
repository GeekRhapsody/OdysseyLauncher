using Launcher.Core.Platform;
using Launcher.Core.Platform.Linux;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Platform;

/// <summary>The status indicators on Linux, read from a made-up <c>/sys</c> and <c>/proc</c>: these run on every OS.</summary>
public sealed class LinuxDeviceStatusTests : IDisposable
{
    private const string RouteHeader = "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n";

    private const string WirelessHeader =
        "Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE\n"
        + " face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22\n";

    private readonly TempDir _root = new();

    public void Dispose() => _root.Dispose();

    [Fact]
    public void A_laptop_battery_charging_on_mains()
    {
        Supply("AC", ("type", "Mains"), ("online", "1"));
        Supply("BAT0", ("type", "Battery"), ("scope", "System"), ("present", "1"), ("capacity", "57"), ("status", "Charging"));

        Assert.Equal(new BatteryState(true, 57, true), Status().ReadBattery());
    }

    [Fact]
    public void A_mains_supply_that_is_offline_means_on_battery_whatever_the_battery_says()
    {
        Supply("ACAD", ("type", "Mains"), ("online", "0"));
        Supply("BAT1", ("type", "Battery"), ("capacity", "9"), ("status", "Not charging"));

        Assert.Equal(new BatteryState(true, 9, false), Status().ReadBattery());
    }

    [Theory]
    [InlineData("Discharging", false)]
    [InlineData("Full", true)]
    [InlineData("Charging", true)]
    public void Without_a_mains_supply_the_battery_status_says_whether_it_is_plugged_in(string status, bool pluggedIn)
    {
        Supply("BAT0", ("type", "Battery"), ("capacity", "100"), ("status", status));

        Assert.Equal(new BatteryState(true, 100, pluggedIn), Status().ReadBattery());
    }

    [Fact]
    public void A_pad_battery_is_not_the_computers()
    {
        Supply("AC", ("type", "Mains"), ("online", "1"));
        Supply("ps-controller-battery-0", ("type", "Battery"), ("scope", "Device"), ("capacity", "40"));

        Assert.Equal(BatteryState.None, Status().ReadBattery());
    }

    [Fact]
    public void A_battery_without_a_charge_and_an_empty_bay()
    {
        Supply("BAT0", ("type", "Battery"), ("present", "0"), ("capacity", "0"));
        Supply("BAT1", ("type", "Battery"), ("status", "Discharging"));

        Assert.Equal(new BatteryState(true, -1, false), Status().ReadBattery());
    }

    [Fact]
    public void No_power_supplies_means_no_battery() => Assert.Equal(BatteryState.None, Status().ReadBattery());

    [Theory]
    [InlineData("-56.", 3)]
    [InlineData("-70.", 2)]
    [InlineData("-80.", 1)]
    [InlineData("-95.", 0)]
    [InlineData("200.", -1)]
    public void The_default_route_over_wifi_shows_its_signal(string level, int bars)
    {
        Adapter("wlan0", wifi: true);
        Adapter("docker0", hardware: false);
        _root.File("proc/net/route", RouteHeader + "wlan0\t00000000\t0101A8C0\t0003\t0\t0\t600\t00000000\t0\t0\t0\n");
        _root.File("proc/net/wireless", WirelessHeader + $" wlan0: 0000   54.  {level}  -256        0      0      0      0      0        0\n");

        Assert.Equal(new NetworkState(NetworkKind.Wireless, bars), Status().ReadNetwork());
    }

    [Fact]
    public void A_vpn_default_route_shows_the_real_link_wifi_before_a_cable()
    {
        Adapter("enp3s0");
        Adapter("tun0", hardware: false);
        Adapter("wlp2s0", wifi: true);
        _root.File(
            "proc/net/route",
            RouteHeader
            + "tun0\t00000000\t00000000\t0001\t0\t0\t50\t00000000\t0\t0\t0\n"
            + "enp3s0\t00000000\t0101A8C0\t0003\t0\t0\t100\t00000000\t0\t0\t0\n");

        // tun0's route wins but isn't hardware, so the first connected Wi-Fi shows, its signal unknown (not listed).
        Assert.Equal(new NetworkState(NetworkKind.Wireless, -1), Status().ReadNetwork());
    }

    [Fact]
    public void The_lowest_metric_default_route_wins()
    {
        Adapter("enp3s0");
        Adapter("wlan0", wifi: true);
        _root.File(
            "proc/net/route",
            RouteHeader
            + "wlan0\t00000000\t0101A8C0\t0003\t0\t0\t600\t00000000\t0\t0\t0\n"
            + "enp3s0\t00000000\t0101A8C0\t0003\t0\t0\t100\t00000000\t0\t0\t0\n");

        Assert.Equal(new NetworkState(NetworkKind.Wired), Status().ReadNetwork());
    }

    [Fact]
    public void Adapters_that_are_down_mean_disconnected()
    {
        Adapter("enp3s0", up: false);
        Adapter("wlan0", wifi: true, up: false);
        Adapter("lo", hardware: false);

        Assert.Equal(new NetworkState(NetworkKind.Disconnected), Status().ReadNetwork());
    }

    [Fact]
    public void Without_the_interface_list_the_network_is_unknown() => Assert.Equal(NetworkState.Unknown, Status().ReadNetwork());

    [Fact]
    public void This_machine_is_read()
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), "Reads the real /sys and /proc.");

        var status = new LinuxDeviceStatus("/");

        _ = status.ReadBattery();
        Assert.NotEqual(NetworkKind.Unknown, status.ReadNetwork().Kind);
    }

    private LinuxDeviceStatus Status() => new(_root.Path);

    private void Supply(string name, params (string File, string Value)[] attributes)
    {
        foreach (var (file, value) in attributes)
        {
            _root.File($"sys/class/power_supply/{name}/{file}", value + "\n");
        }
    }

    private void Adapter(string name, bool wifi = false, bool hardware = true, bool up = true)
    {
        _root.File($"sys/class/net/{name}/operstate", up ? "up\n" : "down\n");
        if (hardware)
        {
            Directory.CreateDirectory(_root.Combine("sys", "class", "net", name, "device"));
        }

        if (wifi)
        {
            Directory.CreateDirectory(_root.Combine("sys", "class", "net", name, "phy80211"));
        }
    }
}
