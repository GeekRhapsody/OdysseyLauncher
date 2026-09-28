using Launcher.Core.Diagnostics;

namespace Launcher.Core.Tests.Diagnostics;

public class DebugOptionsTests
{
    private static readonly string CapturePath = Path.Combine(Path.GetTempPath(), "odyssey", "shot.png");
    private static readonly string BenchPath = Path.Combine(Path.GetTempPath(), "odyssey", "bench.json");

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
}
