using System;
using System.Globalization;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Platform;

namespace Launcher.App.Screens;

/// <summary>
/// The status indicators, top right: the network (Wi-Fi with its bars, a cable, or disconnected), the battery's charge
/// (only on a device with one) and the time, each switched on or off by <c>[ui]</c> in settings.toml. They're on their
/// own layer above the settings screens, so a change made there shows at once. The row is an
/// <see cref="HBoxContainer"/> growing leftwards from the right margin, which leaves hidden indicators out of its
/// layout: whatever is shown sits together against the right edge. The device's state comes from a
/// <see cref="DeviceStatusMonitor"/> (only when it changes); the clock is checked once a second in <see cref="Tick"/>,
/// and its text is made only when the minute changes.
/// </summary>
public sealed partial class StatusBar : CanvasLayer
{
    /// <summary>Above the settings screens (<see cref="UiLayer"/> is 4).</summary>
    public const int CanvasLayerIndex = 5;

    private const float Margin = 44;
    private const float IconSize = 22;
    private const string IconFolder = "res://icons/status/";

    private static readonly Color TextColour = new("#B8C4E6");

    /// <summary>The Wi-Fi arcs a weak signal doesn't reach, drawn faintly behind its bars (as phones do).</summary>
    private static readonly Color UnlitColour = new(TextColour, 0.3f);

    /// <summary>Indexed by <see cref="BatteryLevel"/>, then the Wi-Fi bars 0–3, then off and the cable.</summary>
    private static readonly string[] IconFiles =
    [
        "battery-full", "battery-medium", "battery-low", "battery-warning", "battery-charging",
        "wifi-zero", "wifi-low", "wifi-high", "wifi", "wifi-off", "ethernet-port",
    ];

    private const int WifiIcons = 5;
    private const int WifiFullIcon = 8;
    private const int WifiOffIcon = 9;
    private const int WiredIcon = 10;

    private readonly TextureRect _networkIcon;
    private readonly TextureRect _networkBars;
    private readonly HBoxContainer _battery;
    private readonly TextureRect _batteryIcon;
    private readonly Label _batteryText;
    private readonly Label _clock;
    private readonly string[] _percentTexts = new string[101];
    private readonly Texture2D?[] _icons;
    private UiSettings _settings = new();
    private DeviceStatus _status = DeviceStatus.Unknown;
    private double _sinceClockCheck;
    private int _shownMinute = -1;

    /// <param name="icons">From <see cref="LoadIcons"/>.</param>
    public StatusBar(Texture2D?[] icons)
    {
        Name = "StatusBar";
        Layer = CanvasLayerIndex;
        _icons = icons;

        var root = new Control { MouseFilter = Control.MouseFilterEnum.Ignore };
        root.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(root);

        var row = new HBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore, Alignment = BoxContainer.AlignmentMode.End };
        row.AddThemeConstantOverride("separation", 16);
        row.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.TopRight);
        row.GrowHorizontal = Control.GrowDirection.Begin;
        row.OffsetRight = -Margin;
        row.OffsetTop = 18;
        row.OffsetBottom = 44;
        root.AddChild(row);

        var text = new LabelSettings { FontSize = 18, FontColor = Colors.White, ShadowColor = new Color(0, 0, 0, 0.6f), ShadowSize = 4, ShadowOffset = Vector2.Zero };
        _networkIcon = Icon();
        _networkIcon.Modulate = Colors.White;
        row.AddChild(_networkIcon);
        _networkBars = Icon();
        _networkBars.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.FullRect);
        _networkIcon.AddChild(_networkBars);

        _battery = new HBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore, Visible = false };
        _battery.AddThemeConstantOverride("separation", 5);
        _batteryIcon = Icon();
        _batteryIcon.Visible = true;
        _battery.AddChild(_batteryIcon);
        _batteryText = new Label { LabelSettings = text, Modulate = TextColour, MouseFilter = Control.MouseFilterEnum.Ignore, SizeFlagsVertical = Control.SizeFlags.ShrinkCenter };
        _battery.AddChild(_batteryText);
        row.AddChild(_battery);

        _clock = new Label { LabelSettings = text, Modulate = TextColour, MouseFilter = Control.MouseFilterEnum.Ignore, SizeFlagsVertical = Control.SizeFlags.ShrinkCenter, Visible = false };
        row.AddChild(_clock);
    }

    /// <summary>Any thread but the main one: the icons, for the constructor (a missing one is null, and doesn't show).</summary>
    public static Texture2D?[] LoadIcons()
    {
        var icons = new Texture2D?[IconFiles.Length];
        for (var i = 0; i < icons.Length; i++)
        {
            icons[i] = ResourceLoader.Load<Texture2D>(IconFolder + IconFiles[i] + ".svg");
        }

        return icons;
    }

    /// <summary>Main thread: which indicators are switched on (<c>[ui]</c>).</summary>
    public void Apply(UiSettings settings)
    {
        _settings = settings;
        Refresh();
    }

    /// <summary>Main thread: the device's state changed.</summary>
    public void Show(DeviceStatus status)
    {
        _status = status;
        Refresh();
    }

    /// <summary>Main thread, each frame: once a second, checks whether the minute has changed. No allocation until it has.</summary>
    public void Tick(double delta)
    {
        _sinceClockCheck += delta;
        if (_sinceClockCheck < 1 || !_clock.Visible)
        {
            return;
        }

        _sinceClockCheck = 0;
        UpdateClock(false);
    }

    private void UpdateClock(bool force)
    {
        var now = DateTime.Now;
        var minute = (now.Hour * 60) + now.Minute;
        if (!force && minute == _shownMinute)
        {
            return;
        }

        _shownMinute = minute;
        _clock.Text = now.ToString("t", CultureInfo.CurrentCulture);
    }

    private void Refresh()
    {
        var clock = _settings.ShowClock;
        if (clock && !_clock.Visible)
        {
            UpdateClock(true);
        }

        _clock.Visible = clock;

        var battery = _status.Battery;
        var showBattery = _settings.ShowBattery && battery.Present;
        if (showBattery)
        {
            var level = DeviceStatus.LevelOf(battery);
            SetIcon(_batteryIcon, (int)level);
            _batteryIcon.Modulate = level switch
            {
                BatteryLevel.Warning => UiStyle.Bad,
                BatteryLevel.Charging => UiStyle.Good,
                _ => TextColour,
            };
            _batteryText.Visible = battery.Percent >= 0;
            if (battery.Percent >= 0)
            {
                _batteryText.Text = _percentTexts[battery.Percent] ??= battery.Percent.ToString(CultureInfo.CurrentCulture) + "%";
            }
        }

        _battery.Visible = showBattery;

        var network = _status.Network;
        var showNetwork = _settings.ShowNetwork && network.Kind != NetworkKind.Unknown;
        if (showNetwork)
        {
            // A Wi-Fi signal below full: every arc faintly, its bars over them.
            var bars = network.SignalBars is >= 0 and <= 3 ? network.SignalBars : 3;
            var partial = network.Kind == NetworkKind.Wireless && bars < 3;
            SetIcon(_networkIcon, network.Kind switch
            {
                NetworkKind.Wired => WiredIcon,
                NetworkKind.Wireless => WifiFullIcon,
                _ => WifiOffIcon,
            });
            _networkIcon.SelfModulate = partial ? UnlitColour : network.Kind == NetworkKind.Disconnected ? UiStyle.Faint : TextColour;
            if (partial)
            {
                SetIcon(_networkBars, WifiIcons + bars);
            }

            _networkBars.Visible = partial && _networkBars.Texture is not null;
        }

        _networkIcon.Visible = showNetwork && _networkIcon.Texture is not null;
        _batteryIcon.Visible = _batteryIcon.Texture is not null;
    }

    private void SetIcon(TextureRect rect, int index)
    {
        if (_icons[index] is { } texture && rect.Texture != texture)
        {
            rect.Texture = texture;
        }
    }

    private static TextureRect Icon() => new()
    {
        CustomMinimumSize = new Vector2(IconSize, IconSize),
        ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
        StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
        TextureFilter = CanvasItem.TextureFilterEnum.LinearWithMipmaps,
        SizeFlagsVertical = Control.SizeFlags.ShrinkCenter,
        MouseFilter = Control.MouseFilterEnum.Ignore,
        Modulate = TextColour,
        Visible = false,
    };
}
