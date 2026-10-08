using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Platform;

namespace Launcher.Core.Tests.Diagnostics;

public class DebugOptionsTests
{
    private static readonly string CapturePath = Path.Combine(Path.GetTempPath(), "odyssey", "shot.png");
    private static readonly string BenchPath = Path.Combine(Path.GetTempPath(), "odyssey", "bench.json");

    [Fact]
    public void Open_shows_a_settings_screen_or_component_and_a_picker_can_start_in_a_folder()
    {
        var folder = Path.Combine(Path.GetTempPath(), "odyssey", "pictures");
        var result = DebugOptions.Parse(["--open=Image-Picker", $"--open-path={folder}", "--nav-script=down,menu,x"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal("image-picker", result.Options.Open);
        Assert.Equal(folder, result.Options.OpenPath);
        Assert.Equal(["down", "menu", "x"], result.Options.NavScript);
    }

    [Fact]
    public void The_power_menu_can_be_opened_and_driven()
    {
        var result = DebugOptions.Parse(["--open=power", "--nav-script=power,last"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal("power", result.Options.Open);
        Assert.Equal(["power", "last"], result.Options.NavScript);
    }

    [Fact]
    public void A_games_details_can_be_opened_and_its_media_viewed()
    {
        var result = DebugOptions.Parse(["--open=details", "--start-system=arcade", "--start-index=3", "--nav-script=accept,right,y,favourite"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal("details", result.Options.Open);
        Assert.Equal(["accept", "right", "y", "favourite"], result.Options.NavScript);
    }

    [Fact]
    public void The_running_screen_can_be_opened()
    {
        var result = DebugOptions.Parse(["--open=running"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal("running", result.Options.Open);
    }

    [Fact]
    public void Fake_status_shows_a_made_up_battery_and_network()
    {
        Assert.Null(DebugOptions.Parse([]).Options.FakeStatus);
        (string Value, DeviceStatus Expected)[] cases =
        [
            ("42+/wifi2", new DeviceStatus(new BatteryState(true, 42, true), new NetworkState(NetworkKind.Wireless, 2))),
            ("8/LAN", new DeviceStatus(new BatteryState(true, 8, false), new NetworkState(NetworkKind.Wired))),
            ("none/off", new DeviceStatus(BatteryState.None, new NetworkState(NetworkKind.Disconnected))),
            ("100/wifi0", new DeviceStatus(new BatteryState(true, 100, false), new NetworkState(NetworkKind.Wireless, 0))),
        ];
        foreach (var (value, expected) in cases)
        {
            var result = DebugOptions.Parse([$"--fake-status={value}"]);
            Assert.True(result.IsValid, string.Join("; ", result.Errors));
            Assert.Equal(expected, result.Options.FakeStatus);
        }

        foreach (var bad in (string[])["42", "101/lan", "-5/lan", "42/wifi4", "full/lan", "/lan", "42+/"])
        {
            var result = DebugOptions.Parse([$"--fake-status={bad}"]);
            Assert.False(result.IsValid, bad);
            Assert.Contains("--fake-status needs <battery>/<network>", Assert.Single(result.Errors), StringComparison.Ordinal);
        }
    }

    [Fact]
    public void Layout_overrides_the_display_settings_for_the_run()
    {
        Assert.Null(DebugOptions.Parse([]).Options.Layout);

        var result = DebugOptions.Parse(["--layout=grid:4x2/List"]);
        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        var layout = result.Options.Layout!;
        Assert.Equal(new LayoutOverride(SystemsLayout.Grid, new GridSize(4, 2), GamesLayout.List, null), layout);
        Assert.Equal("grid:4x2/list", layout.ToString());

        // The sizes it names replace settings.toml's; the others stay, and so do a system's own.
        var display = new DisplaySettings("memory-card") { GamesGrid = new GridSize(6, 3) };
        var applied = layout.ApplyTo(display);
        Assert.Equal(SystemsLayout.Grid, applied.SystemsLayout);
        Assert.Equal(new GridSize(4, 2), applied.SystemsGrid);
        Assert.Equal(GamesLayout.List, applied.GamesLayout);
        Assert.Equal(new GridSize(6, 3), applied.GamesGrid);

        foreach (var bad in (string[])["grid", "list/grid", "grid/single", "grid:4/grid", "grid:10x2/grid", "grid/grid:3x7", "grid:-1x2/grid", "grid/grid/grid"])
        {
            var rejected = DebugOptions.Parse([$"--layout={bad}"]);
            Assert.False(rejected.IsValid, bad);
            Assert.Contains("--layout needs <systems>/<games>", Assert.Single(rejected.Errors), StringComparison.Ordinal);
        }
    }

    [Fact]
    public void Open_arguments_are_checked()
    {
        var absolute = Path.Combine(Path.GetTempPath(), "odyssey");
        (string[] Args, string Expected)[] cases =
        [
            (["--open=everything"], "doesn't know 'everything'"),
            ([$"--open-path={absolute}"], "--open-path needs --open=folder-picker"),
            (["--open=folder-picker", "--open-path=relative"], "needs an absolute path"),
        ];

        foreach (var (args, expected) in cases)
        {
            var result = DebugOptions.Parse(args);
            Assert.False(result.IsValid);
            Assert.Contains(result.Errors, e => e.Contains(expected, StringComparison.Ordinal));
        }
    }

    [Fact]
    public void No_arguments_means_no_facilities()
    {
        var result = DebugOptions.Parse([]);

        Assert.True(result.IsValid);
        Assert.False(result.Options.IsActive);
    }

    [Fact]
    public void Capture_uses_the_default_frame_when_none_is_given()
    {
        var result = DebugOptions.Parse([$"--capture={CapturePath}"]);

        Assert.True(result.IsValid);
        Assert.Equal(CapturePath, result.Options.CapturePath);
        Assert.Equal(DebugOptions.DefaultCaptureFrame, result.Options.CaptureFrame);
        Assert.False(result.Options.BenchRequested);
    }

    [Fact]
    public void Capture_and_bench_can_be_combined()
    {
        var result = DebugOptions.Parse(
            [$"--capture={CapturePath}", "--capture-frame=120", $"--bench={BenchPath}", "--bench-frames=300"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal(120, result.Options.CaptureFrame);
        Assert.Equal(BenchPath, result.Options.BenchPath);
        Assert.Equal(300, result.Options.BenchFrames);
    }

    [Fact]
    public void Paths_are_normalised()
    {
        var messy = Path.Combine(Path.GetTempPath(), "odyssey", "..", "odyssey", "shot.png");

        var result = DebugOptions.Parse([$"--capture={messy}"]);

        Assert.Equal(CapturePath, result.Options.CapturePath);
    }

    [Fact]
    public void Unknown_arguments_are_ignored()
    {
        var result = DebugOptions.Parse(["--scan=megadrive", "verbose", $"--bench={BenchPath}"]);

        Assert.True(result.IsValid);
        Assert.True(result.Options.BenchRequested);
    }

    [Theory]
    [InlineData("--capture=shot.png", "absolute path")]
    [InlineData("--capture=", "needs a path")]
    [InlineData("--capture", "needs a value")]
    [InlineData("--bench=bench.json", "absolute path")]
    public void Paths_must_be_given_and_absolute(string arg, string expected)
    {
        var result = DebugOptions.Parse([arg]);

        Assert.False(result.IsValid);
        Assert.Contains(expected, Assert.Single(result.Errors), StringComparison.Ordinal);
        Assert.Same(DebugOptions.None, result.Options);
    }

    [Fact]
    public void Paths_must_have_the_right_extension()
    {
        var result = DebugOptions.Parse([$"--capture={Path.ChangeExtension(CapturePath, ".jpg")}"]);

        Assert.Contains(".png", Assert.Single(result.Errors), StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-5")]
    [InlineData("abc")]
    [InlineData(" 60")]
    [InlineData("1000001")]
    public void Frame_counts_must_be_whole_numbers_in_range(string value)
    {
        var result = DebugOptions.Parse([$"--capture={CapturePath}", $"--capture-frame={value}"]);

        Assert.Contains("whole number", Assert.Single(result.Errors), StringComparison.Ordinal);
    }

    [Fact]
    public void Frame_counts_need_their_facility()
    {
        var result = DebugOptions.Parse(["--capture-frame=10", "--bench-frames=10"]);

        Assert.Equal(2, result.Errors.Count);
    }

    [Fact]
    public void Repeated_arguments_are_rejected()
    {
        var result = DebugOptions.Parse([$"--capture={CapturePath}", $"--capture={CapturePath}"]);

        Assert.Contains("more than once", Assert.Single(result.Errors), StringComparison.Ordinal);
    }

    // ---- --launch, --user-dir, --quit-after-launch -------------------------------------------------

    [Fact]
    public void Launch_names_a_system_and_a_rom_path_that_can_have_spaces_and_further_folders()
    {
        var userDir = Path.Combine(Path.GetTempPath(), "odyssey user");

        var result = DebugOptions.Parse(["--launch=megadrive\\Hacks/Sonic & Knuckles (USA).md", $"--user-dir={userDir}", "--quit-after-launch"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.True(result.Options.LaunchRequested);
        Assert.Equal("megadrive", result.Options.LaunchSystem);
        Assert.Equal("Hacks/Sonic & Knuckles (USA).md", result.Options.LaunchRelPath);
        Assert.Equal(userDir, result.Options.UserDir);
        Assert.True(result.Options.QuitAfterLaunch);
        Assert.False(result.Options.IsActive);
    }

    [Theory]
    [InlineData("--launch=megadrive")]
    [InlineData("--launch=megadrive/")]
    [InlineData("--launch=/Sonic.md")]
    [InlineData("--launch=")]
    public void Launch_needs_both_parts(string arg)
    {
        var result = DebugOptions.Parse([arg]);

        Assert.Contains("needs a system and a ROM path", Assert.Single(result.Errors), StringComparison.Ordinal);
    }

    [Fact]
    public void Quit_after_launch_is_a_switch_that_needs_launch()
    {
        Assert.Contains("needs --launch", Assert.Single(DebugOptions.Parse(["--quit-after-launch"]).Errors), StringComparison.Ordinal);
        Assert.Contains("doesn't take a value", Assert.Single(DebugOptions.Parse(["--launch=a/b", "--quit-after-launch=1"]).Errors), StringComparison.Ordinal);
    }

    [Fact]
    public void The_user_dir_must_be_absolute()
    {
        var result = DebugOptions.Parse(["--user-dir=relative/folder"]);

        Assert.Contains("absolute path", Assert.Single(result.Errors), StringComparison.Ordinal);
    }

    // ---- Bench scenarios and rendering options (M5) ------------------------------------------------

    [Fact]
    public void The_defaults_are_the_boot_scenario_with_textures_bilinear_and_the_upload_cap()
    {
        var options = DebugOptions.Parse([$"--bench={BenchPath}"]).Options;

        Assert.Equal(BenchScenario.Boot, options.BenchScenario);
        Assert.Null(options.BenchSystem);
        Assert.Equal(DebugOptions.DefaultBenchScrollSeconds, options.BenchScrollSeconds);
        Assert.False(options.NoTextures);
        Assert.Null(options.RenderScale);
        Assert.Equal(Upscaler.Bilinear, options.Upscaler);
        Assert.Equal(DebugOptions.DefaultUploadCap, options.UploadCap);
    }

    [Fact]
    public void The_scroll_scenario_takes_a_system_and_a_duration()
    {
        var result = DebugOptions.Parse(
            [$"--bench={BenchPath}", "--bench-scenario=Scroll", "--bench-system=ps2", "--bench-scroll-seconds=30.5", "--no-textures"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal(BenchScenario.Scroll, result.Options.BenchScenario);
        Assert.Equal("ps2", result.Options.BenchSystem);
        Assert.Equal(30.5, result.Options.BenchScrollSeconds);
        Assert.True(result.Options.NoTextures);
    }

    [Theory]
    [InlineData("--bench-scenario=fly", "must be one of boot, scroll")]
    [InlineData("--bench-scroll-seconds=0", "number from 1 to 3600")]
    [InlineData("--bench-system=PS 2", "needs a system id")]
    public void Scenario_values_are_checked(string arg, string expected)
    {
        string[] scenario = arg.StartsWith("--bench-scenario", StringComparison.Ordinal) ? [] : ["--bench-scenario=scroll"];

        var result = DebugOptions.Parse([$"--bench={BenchPath}", .. scenario, arg]);

        Assert.Contains(expected, Assert.Single(result.Errors), StringComparison.Ordinal);
    }

    [Fact]
    public void Scroll_options_need_the_scroll_scenario_and_frames_belong_to_boot()
    {
        Assert.Contains("only applies to --bench-scenario=scroll", Assert.Single(
            DebugOptions.Parse([$"--bench={BenchPath}", "--bench-scenario=boot", "--bench-system=ps2"]).Errors), StringComparison.Ordinal);
        Assert.Contains("needs --bench-scenario=scroll", Assert.Single(
            DebugOptions.Parse([$"--bench={BenchPath}", "--bench-scroll-seconds=5"]).Errors), StringComparison.Ordinal);
        Assert.Contains("only applies to the boot scenario", Assert.Single(
            DebugOptions.Parse([$"--bench={BenchPath}", "--bench-scenario=scroll", "--bench-frames=10"]).Errors), StringComparison.Ordinal);
        Assert.Contains("needs --bench=", Assert.Single(DebugOptions.Parse(["--bench-scenario=scroll"]).Errors), StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("--render-scale=0.5", 0.5, "bilinear", DebugOptions.DefaultUploadCap)]
    [InlineData("--upscaler=FSR", null, "fsr", DebugOptions.DefaultUploadCap)]
    [InlineData("--upload-cap=0", null, "bilinear", 0)]
    [InlineData("--upload-cap=8", null, "bilinear", 8)]
    public void Rendering_options_parse(string arg, double? scale, string upscaler, int cap)
    {
        var result = DebugOptions.Parse([arg]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal(scale, result.Options.RenderScale);
        Assert.Equal(upscaler, result.Options.Upscaler.ToString().ToLowerInvariant());
        Assert.Equal(cap, result.Options.UploadCap);
    }

    [Theory]
    [InlineData("--render-scale=0.1")]
    [InlineData("--render-scale=1.5")]
    [InlineData("--render-scale=half")]
    [InlineData("--upload-cap=65")]
    public void Rendering_options_are_range_checked(string arg)
    {
        Assert.Single(DebugOptions.Parse([arg]).Errors);
    }

    [Fact]
    public void Start_system_and_index_pick_the_first_screen_for_captures()
    {
        var result = DebugOptions.Parse(["--start-system=megadrive", "--start-index=12"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal("megadrive", result.Options.StartSystem);
        Assert.Equal(12, result.Options.StartIndex);
        Assert.Contains("needs --start-system", Assert.Single(DebugOptions.Parse(["--start-index=3"]).Errors), StringComparison.Ordinal);
        Assert.Contains("can't be combined", Assert.Single(
            DebugOptions.Parse([$"--bench={BenchPath}", "--bench-scenario=scroll", "--start-system=nes"]).Errors), StringComparison.Ordinal);
    }

    [Fact]
    public void A_nav_script_is_a_list_of_known_steps()
    {
        var result = DebugOptions.Parse(["--nav-script=Down, right,accept,wait,LetterNext,turn,zoom,back"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal(["down", "right", "accept", "wait", "letternext", "turn", "zoom", "back"], result.Options.NavScript);
        Assert.Contains("doesn't know the step 'jump'", Assert.Single(DebugOptions.Parse(["--nav-script=down,jump"]).Errors), StringComparison.Ordinal);
        Assert.Contains("at least one step", Assert.Single(DebugOptions.Parse(["--nav-script=,"]).Errors), StringComparison.Ordinal);
        Assert.Empty(DebugOptions.Parse([]).Options.NavScript);
    }

    [Fact]
    public void A_theme_can_be_chosen_switched_and_the_overlay_hidden_for_captures()
    {
        var result = DebugOptions.Parse(["--theme=slot-showcase", "--no-overlay", "--nav-script=theme,rescan,wait"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.Equal(("slot-showcase", true), (result.Options.Theme, result.Options.NoOverlay));
        Assert.Equal(["theme", "rescan", "wait"], result.Options.NavScript);
        Assert.Contains("needs a theme id", Assert.Single(DebugOptions.Parse(["--theme=Slot Showcase"]).Errors), StringComparison.Ordinal);
        Assert.Contains("doesn't take a value", Assert.Single(DebugOptions.Parse(["--no-overlay=yes"]).Errors), StringComparison.Ordinal);
        Assert.Null(DebugOptions.Parse([]).Options.Theme);
    }

    [Fact]
    public void Saving_scraping_responses_is_a_one_off_switch_and_off_by_default()
    {
        var result = DebugOptions.Parse(["--save-responses"]);

        Assert.True(result.IsValid, string.Join("; ", result.Errors));
        Assert.True(result.Options.SaveResponses);
        Assert.False(result.Options.IsActive);
        Assert.False(DebugOptions.Parse([]).Options.SaveResponses);
        Assert.Contains("doesn't take a value", Assert.Single(DebugOptions.Parse(["--save-responses=1"]).Errors), StringComparison.Ordinal);
    }
}
