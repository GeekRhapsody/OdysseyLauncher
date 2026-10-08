using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Platform;

namespace Launcher.App.Settings;

/// <summary>
/// Graphics (2026-10-08), <c>[display]</c> in settings.toml: the screen mode (exclusive fullscreen, borderless or a
/// window), the resolution (the 3D's in the fullscreen modes, as Godot can't change the display mode; the window's size
/// in a window), the video driver (Direct3D 12 or Vulkan, from the next start: it's written to the
/// <see cref="RenderingOverride"/> beside the executable, and a restart is offered), anisotropic filtering, and the FPS
/// and VRAM readout under the status indicators (<c>[ui] show_performance</c>). A chooses from a list; left and right
/// step through the values. Each change is saved at once, and everything but the driver applies at once.
/// </summary>
public sealed partial class GraphicsPage : ListPanel
{
    /// <summary>The screen modes in the order the page lists them.</summary>
    private static readonly ScreenMode[] Modes = [ScreenMode.Fullscreen, ScreenMode.Borderless, ScreenMode.Windowed];

    private static readonly RenderingDriver[] Drivers = [RenderingDriver.D3D12, RenderingDriver.Vulkan];

    private readonly SettingsController _settings;
    private readonly SettingRow _screenMode;
    private readonly SettingRow _resolution;
    private readonly SettingRow _driver;
    private readonly SettingRow _anisotropy;
    private readonly SettingRow _performance;
    private readonly string _executableDir;
    private readonly string _running;

    /// <summary>An editor run: the override would land beside the editor, so the driver isn't written there.</summary>
    private readonly bool _editorRun;

    // Values saved but not yet applied, so presses in quick succession step on from each other.
    private ScreenMode? _pendingMode;
    private RenderResolution? _pendingResolution;
    private WindowSize? _pendingSize;
    private RenderingDriver? _pendingDriver;
    private int? _pendingAnisotropy;
    private bool? _pendingPerformance;

    public GraphicsPage(SettingsController settings)
        : base("Graphics")
    {
        _settings = settings;
        _executableDir = Path.GetDirectoryName(OS.GetExecutablePath()) ?? ".";
        _running = RenderingServer.GetCurrentRenderingDriverName();
        _editorRun = OS.HasFeature("editor");
        Subtitle = "[display] in settings.toml";

        AddSection("Screen");
        _screenMode = AddRow("Screen mode", activated: ChooseScreenMode);
        _screenMode.Adjuster = direction => Step(Modes, Mode, direction, SaveMode);
        _resolution = AddRow("Resolution", activated: ChooseResolution);
        _resolution.Adjuster = StepResolution;
        AddNote("The menus and text are always drawn at the screen's own resolution.");

        AddSection("Rendering");
        _driver = AddRow("Video driver", activated: ChooseDriver);
        _driver.Adjuster = direction => Step(Drivers, Driver, direction, SaveDriver);
        _anisotropy = AddRow("Anisotropic filtering", activated: ChooseAnisotropy);
        _anisotropy.Adjuster = direction => Step(DisplaySettings.AnisotropicLevels, Anisotropy, direction, SaveAnisotropy);

        AddSection("On screen");
        _performance = AddRow("Show FPS and VRAM", "Top right, under the clock: frames a second and the video memory the app uses",
            activated: () => SavePerformance(!Performance));
        _performance.Adjuster = direction => SavePerformance(direction > 0);

        SetHints("A  Choose     Left Right  Change     B  Back");
        _settings.ConfigApplied += OnConfigApplied;
        Refresh();
    }

    public override void OnClosed() => _settings.ConfigApplied -= OnConfigApplied;

    private void OnConfigApplied(AppConfig config)
    {
        _pendingMode = null;
        _pendingResolution = null;
        _pendingSize = null;
        _pendingDriver = null;
        _pendingAnisotropy = null;
        _pendingPerformance = null;
        Refresh();
    }

    private DisplaySettings Display => _settings.Services.Config.Settings.Display;

    private ScreenMode Mode => _pendingMode ?? Display.ScreenMode;

    private RenderResolution Resolution => _pendingResolution ?? Display.RenderResolution;

    private WindowSize CurrentSize => _pendingSize ?? Display.WindowSize;

    private RenderingDriver Driver => _pendingDriver ?? Display.RenderingDriver;

    private int Anisotropy => _pendingAnisotropy ?? Display.AnisotropicFiltering;

    private bool Performance => _pendingPerformance ?? _settings.Services.Config.Settings.Ui.ShowPerformance;

    private void Refresh()
    {
        var mode = Mode;
        _screenMode.Value = ModeTitle(mode);
        _screenMode.Detail = ModeDetail(mode);

        if (mode == ScreenMode.Windowed)
        {
            var size = CurrentSize;
            _resolution.Title = "Window size";
            _resolution.Value = SizeTitle(size);
            var usable = UsableSize();
            _resolution.Detail = size.Width > usable.X || size.Height > usable.Y
                ? $"Bigger than the screen allows, so it's {Math.Min(size.Width, usable.X)}×{Math.Min(size.Height, usable.Y)}"
                : "The window's size; the 3D renders at no more than 1080p";
        }
        else
        {
            var resolution = Resolution;
            _resolution.Title = "3D resolution";
            _resolution.Value = ResolutionTitle(resolution);
            _resolution.Detail = ResolutionDetail(resolution, ScreenHeight());
        }

        var driver = Driver;
        _driver.Value = DriverTitle(driver);
        _driver.Detail = DriverDetail(driver);
        _driver.DetailColour = !_editorRun && DisplayNames.Name(driver) != _running ? UiStyle.Warning : UiStyle.Dim;

        var anisotropy = Anisotropy;
        _anisotropy.Value = AnisotropyTitle(anisotropy);
        _anisotropy.Detail = "Sharper textures on surfaces seen at an angle; 16× is the most graphics cards support";

        var performance = Performance;
        _performance.Value = performance ? "Yes" : "No";
        _performance.ValueColour = performance ? UiStyle.Good : UiStyle.Faint;
    }

    /// <summary>A one-line summary for the settings screen's Graphics row.</summary>
    public static string Summary(DisplaySettings display) =>
        $"{ModeTitle(display.ScreenMode)} · {(display.ScreenMode == ScreenMode.Windowed ? SizeTitle(display.WindowSize) : ResolutionTitle(display.RenderResolution))} · {DriverTitle(display.RenderingDriver)} · {AnisotropyTitle(display.AnisotropicFiltering)}";

    // ---- Screen mode ----------------------------------------------------------------------------------

    private static string ModeTitle(ScreenMode mode) => mode switch
    {
        ScreenMode.Fullscreen => "Fullscreen",
        ScreenMode.Windowed => "Windowed",
        _ => "Borderless",
    };

    private static string ModeDetail(ScreenMode mode) => mode switch
    {
        ScreenMode.Fullscreen => "Exclusive: the screen to itself. Switching to an emulator and back may flash black",
        ScreenMode.Windowed => "A window, of the size below",
        _ => "The default: a window covering the screen, quick to switch to an emulator and back",
    };

    private void ChooseScreenMode()
    {
        var choices = new List<Choice>();
        foreach (var mode in Modes)
        {
            choices.Add(new Choice(DisplayNames.Name(mode), ModeTitle(mode), ModeDetail(mode)));
        }

        Layer.Push(new ChoicePanel("Screen mode", "Saved as [display] screen_mode", choices, DisplayNames.Name(Mode), choice =>
        {
            foreach (var mode in Modes)
            {
                if (DisplayNames.Name(mode) == choice.Id)
                {
                    SaveMode(mode);
                }
            }
        }));
    }

    private void SaveMode(ScreenMode mode)
    {
        if (mode == Mode)
        {
            return;
        }

        _pendingMode = mode;
        Refresh();

        // screen_mode replaces fullscreen, which a settings.toml from before it may still have.
        Save([
            new ConfigEdit(ConfigFileKind.Settings, ["display", "screen_mode"], DisplayNames.Name(mode)),
            new ConfigEdit(ConfigFileKind.Settings, ["display", "fullscreen"], null),
        ], $"Screen mode: {ModeTitle(mode)}.");
    }

    // ---- Resolution -----------------------------------------------------------------------------------

    private static int ScreenHeight() => DisplayServer.ScreenGetSize(DisplayServer.WindowGetCurrentScreen()).Y;

    private static Vector2I UsableSize() => DisplayServer.ScreenGetUsableRect(DisplayServer.WindowGetCurrentScreen()).Size;

    private static string ResolutionTitle(RenderResolution resolution) =>
        resolution.IsAutomatic ? "Automatic" : resolution.IsNative ? "Native" : resolution.Height.ToString(CultureInfo.InvariantCulture) + "p";

    private static string ResolutionDetail(RenderResolution resolution, int screenHeight)
    {
        var height = (int)Math.Round(resolution.ScaleFor(screenHeight) * screenHeight);
        var what = resolution.IsAutomatic
            ? "At most 1080p"
            : resolution.IsNative
                ? "The screen's own"
                : resolution.Height > screenHeight ? "No more than the screen's" : "Upscaled to the screen";
        return $"{what}: 3D at {height}p on this {screenHeight}p screen";
    }

    private static string SizeTitle(WindowSize size) => $"{size.Width}×{size.Height}";

    /// <summary>Automatic, native, and the presets under the screen's height (and the saved one, if it's another).</summary>
    private List<(Choice Choice, RenderResolution Value)> ResolutionChoices()
    {
        var screen = ScreenHeight();
        var current = Resolution;
        var list = new List<(Choice, RenderResolution)>
        {
            (new Choice("auto", "Automatic", ResolutionDetail(RenderResolution.Automatic, screen)), RenderResolution.Automatic),
            (new Choice("native", "Native", ResolutionDetail(RenderResolution.Native, screen)), RenderResolution.Native),
        };
        foreach (var height in RenderResolution.Presets)
        {
            if (height < screen || height == current.Height)
            {
                var resolution = new RenderResolution(height);
                list.Add((new Choice(height.ToString(CultureInfo.InvariantCulture), ResolutionTitle(resolution), ResolutionDetail(resolution, screen)), resolution));
            }
        }

        if (current.Height > 0 && !Contains(RenderResolution.Presets, current.Height))
        {
            list.Add((new Choice(current.Height.ToString(CultureInfo.InvariantCulture), ResolutionTitle(current), ResolutionDetail(current, screen)), current));
        }

        return list;
    }

    /// <summary>The presets that fit the screen (and the saved one, if it's another).</summary>
    private List<(Choice Choice, WindowSize Value)> SizeChoices()
    {
        var usable = UsableSize();
        var current = CurrentSize;
        var list = new List<(Choice, WindowSize)>();
        var seen = false;
        foreach (var size in WindowSize.Presets)
        {
            if ((size.Width <= usable.X && size.Height <= usable.Y) || size == current)
            {
                list.Add((new Choice(size.ToString(), SizeTitle(size)), size));
                seen |= size == current;
            }
        }

        if (!seen)
        {
            list.Add((new Choice(current.ToString(), SizeTitle(current)), current));
        }

        return list;
    }

    private static bool Contains(IReadOnlyList<int> values, int value)
    {
        foreach (var v in values)
        {
            if (v == value)
            {
                return true;
            }
        }

        return false;
    }

    private void ChooseResolution()
    {
        if (Mode == ScreenMode.Windowed)
        {
            var sizes = SizeChoices();
            Layer.Push(new ChoicePanel("Window size", "Saved as [display] window_size", ChoicesOf(sizes), CurrentSize.ToString(), choice =>
            {
                foreach (var (option, size) in sizes)
                {
                    if (option.Id == choice.Id)
                    {
                        SaveSize(size);
                    }
                }
            }));
            return;
        }

        var resolutions = ResolutionChoices();
        Layer.Push(new ChoicePanel("3D resolution", "Saved as [display] render_resolution", ChoicesOf(resolutions), IdOf(Resolution), choice =>
        {
            foreach (var (option, resolution) in resolutions)
            {
                if (option.Id == choice.Id)
                {
                    SaveResolution(resolution);
                }
            }
        }));
    }

    private void StepResolution(int direction)
    {
        if (Mode == ScreenMode.Windowed)
        {
            var sizes = SizeChoices();
            var at = IndexOf(sizes, CurrentSize);
            var next = Math.Clamp(at + Math.Sign(direction), 0, sizes.Count - 1);
            if (next != at)
            {
                SaveSize(sizes[next].Value);
            }

            return;
        }

        var resolutions = ResolutionChoices();
        var index = IndexOf(resolutions, Resolution);
        var to = Math.Clamp(index + Math.Sign(direction), 0, resolutions.Count - 1);
        if (to != index)
        {
            SaveResolution(resolutions[to].Value);
        }
    }

    private static string IdOf(RenderResolution resolution) =>
        resolution.IsAutomatic ? "auto" : resolution.IsNative ? "native" : resolution.Height.ToString(CultureInfo.InvariantCulture);

    private void SaveResolution(RenderResolution resolution)
    {
        if (resolution == Resolution)
        {
            return;
        }

        _pendingResolution = resolution;
        Refresh();
        Save([new ConfigEdit(ConfigFileKind.Settings, ["display", "render_resolution"], resolution.ConfigValue)], $"3D resolution: {ResolutionTitle(resolution)}.");
    }

    private void SaveSize(WindowSize size)
    {
        if (size == CurrentSize)
        {
            return;
        }

        _pendingSize = size;
        Refresh();
        Save([new ConfigEdit(ConfigFileKind.Settings, ["display", "window_size"], size.ToString())], $"Window size: {SizeTitle(size)}.");
    }

    // ---- Video driver ---------------------------------------------------------------------------------

    private static string DriverTitle(RenderingDriver driver) => driver == RenderingDriver.Vulkan ? "Vulkan" : "Direct3D 12";

    private string DriverDetail(RenderingDriver driver)
    {
        if (_editorRun)
        {
            return $"Running {RunningTitle()}. Used by exported builds only: an editor run takes --rendering-driver";
        }

        return DisplayNames.Name(driver) == _running
            ? "Running now"
            : $"From the next start (running {RunningTitle()} now)";
    }

    private string RunningTitle() =>
        DisplayNames.TryParse(_running, out RenderingDriver running) ? DriverTitle(running) : _running;

    private void ChooseDriver()
    {
        var choices = new List<Choice>();
        foreach (var driver in Drivers)
        {
            choices.Add(new Choice(DisplayNames.Name(driver), DriverTitle(driver), driver == RenderingDriver.D3D12 ? "The default" : null));
        }

        Layer.Push(new ChoicePanel("Video driver", "Saved as [display] rendering_driver; used from the next start", choices, DisplayNames.Name(Driver), choice =>
        {
            if (DisplayNames.TryParse(choice.Id, out RenderingDriver driver))
            {
                SaveDriver(driver);
            }
        }));
    }

    /// <summary>
    /// Saves the driver, writing the override the next start reads first (on the thread pool, as the save's check: if
    /// it can't be written, nothing is saved and the dialog says why). Then offers to restart into it.
    /// </summary>
    private void SaveDriver(RenderingDriver driver)
    {
        if (driver == Driver)
        {
            return;
        }

        _pendingDriver = driver;
        Refresh();
        var executableDir = _executableDir;
        Func<string?>? writeOverride = _editorRun ? null : () => RenderingOverride.Write(executableDir, driver);
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["display", "rendering_driver"], DisplayNames.Name(driver))],
            $"Video driver: {DriverTitle(driver)}.",
            result =>
            {
                if (result.Saved && !_editorRun && DisplayNames.Name(driver) != _running && Layer?.Top == this)
                {
                    OfferRestart(driver);
                }
            },
            writeOverride);
    }

    private void OfferRestart(RenderingDriver driver) =>
        ConfirmDialog.Ask(Layer, "Restart now?", $"{DriverTitle(driver)} is used from the next start. Restart the launcher now to use it?",
            "Restart now", "Later", yes =>
            {
                if (!yes)
                {
                    return;
                }

                // The same command line, without any driver it chose (OS.GetCmdlineArgs leaves out the engine's own).
                var args = new List<string>(OS.GetCmdlineArgs());
                var user = OS.GetCmdlineUserArgs();
                if (user.Length > 0)
                {
                    args.Add("--");
                    args.AddRange(user);
                }

                GD.Print($"Display: restarting for {DisplayNames.Name(driver)}.");
                OS.SetRestartOnExit(true, args.ToArray());
                GetTree().Quit();
            });

    // ---- Anisotropic filtering ------------------------------------------------------------------------

    private static string AnisotropyTitle(int samples) => samples == 0 ? "Off" : samples.ToString(CultureInfo.InvariantCulture) + "×";

    private void ChooseAnisotropy()
    {
        var choices = new List<Choice>();
        foreach (var level in DisplaySettings.AnisotropicLevels)
        {
            choices.Add(new Choice(level.ToString(CultureInfo.InvariantCulture), AnisotropyTitle(level), level == 16 ? "The default" : null));
        }

        Layer.Push(new ChoicePanel("Anisotropic filtering", "Saved as [display] anisotropic_filtering", choices, Anisotropy.ToString(CultureInfo.InvariantCulture), choice =>
            SaveAnisotropy(int.Parse(choice.Id, CultureInfo.InvariantCulture))));
    }

    private void SaveAnisotropy(int samples)
    {
        if (samples == Anisotropy)
        {
            return;
        }

        _pendingAnisotropy = samples;
        Refresh();
        Save([new ConfigEdit(ConfigFileKind.Settings, ["display", "anisotropic_filtering"], (long)samples)], $"Anisotropic filtering: {AnisotropyTitle(samples)}.");
    }

    // ---- Performance readout --------------------------------------------------------------------------

    private void SavePerformance(bool on)
    {
        if (on == Performance)
        {
            return;
        }

        _pendingPerformance = on;
        Refresh();
        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["ui", "show_performance"], on)], on ? "FPS and VRAM: shown." : "FPS and VRAM: hidden.");
    }

    // ---- Helpers --------------------------------------------------------------------------------------

    private void Save(IReadOnlyList<ConfigEdit> edits, string saved) => _settings.Save(this, edits, saved);

    /// <summary>Steps <paramref name="current"/> through <paramref name="values"/>, saving the next one if there is one.</summary>
    private static void Step<T>(IReadOnlyList<T> values, T current, int direction, Action<T> save)
    {
        var at = 0;
        for (var i = 0; i < values.Count; i++)
        {
            if (EqualityComparer<T>.Default.Equals(values[i], current))
            {
                at = i;
            }
        }

        var next = Math.Clamp(at + Math.Sign(direction), 0, values.Count - 1);
        if (next != at)
        {
            save(values[next]);
        }
    }

    private static List<Choice> ChoicesOf<T>(List<(Choice Choice, T Value)> options)
    {
        var choices = new List<Choice>(options.Count);
        foreach (var (choice, _) in options)
        {
            choices.Add(choice);
        }

        return choices;
    }

    private static int IndexOf<T>(List<(Choice Choice, T Value)> options, T value)
    {
        for (var i = 0; i < options.Count; i++)
        {
            if (EqualityComparer<T>.Default.Equals(options[i].Value, value))
            {
                return i;
            }
        }

        return 0;
    }
}
