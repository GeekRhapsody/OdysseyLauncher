using System;
using Launcher.App.Ui;
using Launcher.Core.Config;

namespace Launcher.App.Settings;

/// <summary>
/// Settings, Interface (2026-11-07), <c>[ui]</c> in settings.toml: the status indicators top right, the menus' size and
/// the controls' button icons, and the navigation sounds. A turns a row on or off or chooses from a list; left and right
/// change it in place. Each change is saved and applied at once.
/// </summary>
public sealed partial class InterfacePage : ListPanel
{
    /// <summary><c>[ui] button_icons</c>' values, in <see cref="ButtonIcons"/>' order (A1 Button icons).</summary>
    private static readonly Choice[] ButtonIconChoices =
    [
        new("automatic", "Automatic", "Those of the controller or keyboard you used last"),
        new("xbox", "Xbox"),
        new("playstation", "PlayStation"),
        new("nintendo", "Nintendo", "A Switch's or a Switch 2's: B, the bottom button, confirms"),
        new("gamecube", "GameCube"),
        new("steamdeck", "Steam Deck", "And the new Steam Controller, whose buttons are the same"),
        new("steamcontroller", "Steam Controller (2015)"),
        new("keyboard", "Keyboard"),
    ];

    /// <summary><c>[ui] size</c>'s values, in <see cref="UiSize"/>'s order (A1 UI size).</summary>
    private static readonly Choice[] UiSizeChoices =
    [
        new("small", "Small", "For a monitor on a desk"),
        new("medium", "Medium"),
        new("large", "Large", "For a handheld's small screen, or a television across the room"),
    ];

    private readonly SettingsController _settings;
    private readonly SettingRow _clock;
    private readonly SettingRow _battery;
    private readonly SettingRow _network;
    private readonly SettingRow _uiSize;
    private readonly SettingRow _buttonIcons;
    private readonly SettingRow _sounds;

    public InterfacePage(SettingsController settings)
        : base("Interface")
    {
        _settings = settings;
        Subtitle = "[ui] in settings.toml";

        AddSection("Status bar");
        _clock = AddToggleRow("Clock", $"The time, top right, in your {(OperatingSystem.IsWindows() ? "Windows" : "system's")} time format", "show_clock", ui => ui.ShowClock);
        _battery = AddToggleRow("Battery", "Its charge, top right", "show_battery", ui => ui.ShowBattery);
        _network = AddToggleRow("Network", "Wi-Fi with its signal, a cable, or disconnected", "show_network", ui => ui.ShowNetwork);

        AddSection("Menus");
        _uiSize = AddRow("UI size", "The menus, text and controls: the game and system cards keep their size", activated: ChooseUiSize);
        _uiSize.Adjuster = direction => Step(UiSizeChoices, (int)Ui.Size, direction, SaveUiSize);
        _buttonIcons = AddRow("Button icons", "The buttons the controls along the bottom show", activated: ChooseButtonIcons);
        _buttonIcons.Adjuster = direction => Step(ButtonIconChoices, (int)Ui.ButtonIcons, direction, SaveButtonIcons);

        AddSection("Sound");
        _sounds = AddToggleRow("Navigation sounds", "A tock when the focus moves, a whoosh when you enter a system", "navigation_sounds",
            ui => ui.NavigationSounds, ("on", "off"));

        SetHints(CommonHints.ChooseChangeBack);
        _settings.ConfigApplied += OnConfigApplied;
        Refresh();
    }

    public override void OnRevealed() => Refresh();

    public override void OnClosed() => _settings.ConfigApplied -= OnConfigApplied;

    /// <summary>A one-line summary for the settings' Interface row.</summary>
    public static string Summary(UiSettings ui) =>
        $"{UiSizeChoices[(int)ui.Size].Title} · {ButtonIconChoices[(int)ui.ButtonIcons].Title} button icons · Sounds {(ui.NavigationSounds ? "on" : "off")}";

    private UiSettings Ui => _settings.Services.Config.Settings.Ui;

    private void OnConfigApplied(AppConfig config) => Refresh();

    private void Refresh()
    {
        var ui = Ui;
        ShowToggle(_clock, ui.ShowClock);
        ShowToggle(_battery, ui.ShowBattery);
        ShowToggle(_network, ui.ShowNetwork);
        ShowToggle(_sounds, ui.NavigationSounds);
        _uiSize.Value = UiSizeChoices[(int)ui.Size].Title;
        _buttonIcons.Value = ButtonIconChoices[(int)ui.ButtonIcons].Title;
        if (_settings.DeviceStatus?.Current is { Battery.Present: false })
        {
            _battery.Detail = "This PC has no battery, so it never shows";
        }
    }

    /// <summary>
    /// An on-or-off row: A turns it the other way; left is no, right is yes. It's saved as <c>[ui] key</c>, and the
    /// status says it's <paramref name="words"/>' first or second (by default shown or hidden).
    /// </summary>
    private SettingRow AddToggleRow(string title, string detail, string key, Func<UiSettings, bool> on, (string On, string Off)? words = null)
    {
        var said = words ?? ("shown", "hidden");
        var row = AddRow(title, detail, activated: () => SetToggle(title, key, on, said, null));
        row.Adjuster = direction => SetToggle(title, key, on, said, direction > 0);
        return row;
    }

    private static void ShowToggle(SettingRow row, bool on)
    {
        row.Value = on ? "Yes" : "No";
        row.ValueColour = on ? UiStyle.Good : UiStyle.Faint;
    }

    /// <param name="wanted">On or not; null turns it the other way.</param>
    private void SetToggle(string title, string key, Func<UiSettings, bool> on, (string On, string Off) words, bool? wanted)
    {
        var current = on(Ui);
        var next = wanted ?? !current;
        if (current == next)
        {
            return;
        }

        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["ui", key], next)], $"{title}: {(next ? words.On : words.Off)}.");
    }

    /// <summary>Left and right step through the choices, stopping at the ends.</summary>
    private static void Step(Choice[] choices, int current, int direction, Action<Choice> save)
    {
        var next = Math.Clamp(current + Math.Sign(direction), 0, choices.Length - 1);
        if (next != current)
        {
            save(choices[next]);
        }
    }

    private void ChooseUiSize() =>
        Layer.Push(new ChoicePanel("UI size", "Applied at once, and saved as [ui] size", UiSizeChoices, DisplayNames.Name(Ui.Size), SaveUiSize));

    private void SaveUiSize(Choice choice) =>
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["ui", "size"], choice.Id)], $"UI size: {choice.Title}.");

    private void ChooseButtonIcons() =>
        Layer.Push(new ChoicePanel("Button icons", "Saved as [ui] button_icons", ButtonIconChoices, DisplayNames.Name(Ui.ButtonIcons), SaveButtonIcons));

    private void SaveButtonIcons(Choice choice) =>
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["ui", "button_icons"], choice.Id)], $"Button icons: {choice.Title}.");
}
