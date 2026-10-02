using System.Net.NetworkInformation;
using System.Runtime.InteropServices;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Windows;

namespace Launcher.Core.Tests.Platform;

/// <summary>The status indicators' state: levels, change detection, and the Windows reads.</summary>
public sealed class DeviceStatusTests
{
    [Theory]
    [InlineData(-1, -1)]
    [InlineData(0, 0)]
    [InlineData(24, 0)]
    [InlineData(25, 1)]
    [InlineData(49, 1)]
    [InlineData(50, 2)]
    [InlineData(74, 2)]
    [InlineData(75, 3)]
    [InlineData(100, 3)]
    public void Signal_quality_becomes_bars(int quality, int bars) => Assert.Equal(bars, DeviceStatus.SignalBars(quality));

    [Theory]
    [InlineData(100, false, BatteryLevel.Full)]
    [InlineData(71, false, BatteryLevel.Full)]
    [InlineData(70, false, BatteryLevel.Medium)]
    [InlineData(36, false, BatteryLevel.Medium)]
    [InlineData(35, false, BatteryLevel.Low)]
    [InlineData(11, false, BatteryLevel.Low)]
    [InlineData(10, false, BatteryLevel.Warning)]
    [InlineData(0, false, BatteryLevel.Warning)]
    [InlineData(10, true, BatteryLevel.Charging)]
    [InlineData(99, true, BatteryLevel.Charging)]
    [InlineData(100, true, BatteryLevel.Full)]
    [InlineData(-1, false, BatteryLevel.Full)]
    public void The_battery_icon_follows_the_charge(int percent, bool pluggedIn, BatteryLevel level) =>
        Assert.Equal(level, DeviceStatus.LevelOf(new BatteryState(true, percent, pluggedIn)));

    [Fact]
    public void The_monitor_reports_only_changes_and_nothing_while_paused()
    {
        var source = new Scripted { Battery = new BatteryState(true, 80, false), Network = new NetworkState(NetworkKind.Wireless, 3) };
        using var monitor = new DeviceStatusMonitor(source);
        var seen = new List<DeviceStatus>();
        monitor.Changed += seen.Add;

        Assert.Null(monitor.Current);
        monitor.PollNow();
        monitor.PollNow();
        Assert.Single(seen);
        Assert.Equal(new DeviceStatus(source.Battery, source.Network), monitor.Current);

        source.Network = new NetworkState(NetworkKind.Disconnected);
        monitor.PollNow();
        Assert.Equal(2, seen.Count);
        Assert.Equal(NetworkKind.Disconnected, seen[1].Network.Kind);

        monitor.Pause();
        source.Battery = new BatteryState(true, 79, false);
        monitor.PollNow();
        Assert.Equal(2, seen.Count);
        Assert.Equal(3, source.Reads);
    }

    [Fact]
    public void A_read_that_throws_is_shown_as_unknown()
    {
        using var monitor = new DeviceStatusMonitor(new Scripted { Throws = true });
        DeviceStatus? seen = null;
        monitor.Changed += status => seen = status;

        monitor.PollNow();

        Assert.Equal(DeviceStatus.Unknown, seen);
    }

    [Fact]
    public void A_started_monitor_polls_at_once_and_again_on_resume()
    {
        var source = new Scripted { Battery = new BatteryState(true, 50, true), Network = new NetworkState(NetworkKind.Wired) };
        using var monitor = new DeviceStatusMonitor(source, TimeSpan.FromHours(1));
        using var changed = new SemaphoreSlim(0);
        monitor.Changed += _ => changed.Release();

        monitor.Start();
        Assert.True(changed.Wait(TimeSpan.FromSeconds(10), TestContext.Current.CancellationToken));

        monitor.Pause();
        source.Network = new NetworkState(NetworkKind.Disconnected);
        monitor.Resume();
        Assert.True(changed.Wait(TimeSpan.FromSeconds(10), TestContext.Current.CancellationToken));
        Assert.Equal(NetworkKind.Disconnected, monitor.Current!.Value.Network.Kind);
    }

    [Fact]
    public void The_windows_interface_table_is_read_at_the_right_offsets()
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        Assert.Equal(1352, WindowsDeviceStatus.RowSize);
        Assert.Equal(8, (int)Marshal.OffsetOf<NativeMethods.MibIfRow2>(nameof(NativeMethods.MibIfRow2.InterfaceIndex)));

        // Every adapter .NET lists with an IPv4 index is in the table at that index, with the same type, so the row
        // size (the stride) and the index and type offsets are right.
        var rows = WindowsDeviceStatus.ReadInterfaceTable();
        var checkedAny = false;
        foreach (var adapter in NetworkInterface.GetAllNetworkInterfaces())
        {
            if (!adapter.Supports(NetworkInterfaceComponent.IPv4) || adapter.GetIPProperties().GetIPv4Properties() is not { } ipv4)
            {
                continue;
            }

            var row = Assert.Single(rows, r => r.Index == (uint)ipv4.Index);
            Assert.Equal((uint)adapter.NetworkInterfaceType, row.Type);
            checkedAny = true;
        }

        Assert.True(checkedAny);

        // Loopback is software: never the connection.
        Assert.Contains(rows, r => r.Type == 24 && !r.ConnectedAdapter);
    }

    [Fact]
    public void The_windows_reads_never_throw()
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        using var status = new WindowsDeviceStatus();
        var battery = status.ReadBattery();
        var network = status.ReadNetwork();

        Assert.InRange(battery.Percent, -1, 100);
        Assert.NotEqual(NetworkKind.Unknown, network.Kind);
        Assert.InRange(network.SignalBars, -1, 3);
        Assert.True(network.Kind == NetworkKind.Wireless || network.SignalBars == -1);
    }

    private sealed class Scripted : IDeviceStatus
    {
        public BatteryState Battery { get; set; }

        public NetworkState Network { get; set; }

        public bool Throws { get; set; }

        public int Reads { get; private set; }

        public BatteryState ReadBattery()
        {
            Reads++;
            return Throws ? throw new InvalidOperationException("no") : Battery;
        }

        public NetworkState ReadNetwork() => Throws ? throw new InvalidOperationException("no") : Network;
    }
}
