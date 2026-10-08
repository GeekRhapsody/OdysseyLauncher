using Launcher.Core.Config;
using Launcher.Core.Platform;

namespace Launcher.Core.Tests.Platform;

public sealed class RenderingOverrideTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "odyssey-override-" + Guid.NewGuid().ToString("N"));

    public RenderingOverrideTests() => Directory.CreateDirectory(_dir);

    public void Dispose() => Directory.Delete(_dir, recursive: true);

    private string FilePath => Path.Combine(_dir, RenderingOverride.FileName);

    [Fact]
    public void Vulkan_makes_a_file_with_the_driver_line()
    {
        Assert.Equal("[rendering]\nrendering_device/driver.windows=\"vulkan\"\n", RenderingOverride.Merge(null, RenderingDriver.Vulkan));
    }

    [Fact]
    public void D3d12_with_no_file_makes_none()
    {
        Assert.Null(RenderingOverride.Merge(null, RenderingDriver.D3D12));
    }

    [Fact]
    public void D3d12_takes_the_line_out_and_keeps_the_rest()
    {
        var existing = "[display]\nwindow/vsync/vsync_mode=0\n\n[rendering]\nrendering_device/driver.windows=\"vulkan\"\nanti_aliasing/quality/msaa_3d=1\n";

        var merged = RenderingOverride.Merge(existing, RenderingDriver.D3D12);

        Assert.Equal("[display]\nwindow/vsync/vsync_mode=0\n\n[rendering]\nanti_aliasing/quality/msaa_3d=1\n", merged);
        Assert.Null(RenderingOverride.DriverIn(merged!));
    }

    [Fact]
    public void D3d12_removes_a_file_that_held_only_the_driver()
    {
        var vulkan = RenderingOverride.Merge(null, RenderingDriver.Vulkan)!;
        Assert.Null(RenderingOverride.Merge(vulkan, RenderingDriver.D3D12));
    }

    [Fact]
    public void Vulkan_goes_into_an_existing_rendering_section_once()
    {
        var existing = "[rendering]\r\nrendering_device/driver.windows=\"d3d12\"\r\nanti_aliasing/quality/msaa_3d=1\r\n";

        var merged = RenderingOverride.Merge(existing, RenderingDriver.Vulkan)!;

        Assert.Equal("[rendering]\nrendering_device/driver.windows=\"vulkan\"\nanti_aliasing/quality/msaa_3d=1\n", merged);
        Assert.Equal(RenderingDriver.Vulkan, RenderingOverride.DriverIn(merged));
        Assert.Equal(merged, RenderingOverride.Merge(merged, RenderingDriver.Vulkan));
    }

    [Fact]
    public void A_driver_key_in_another_section_is_left_alone()
    {
        var existing = "[other]\nrendering_device/driver.windows=\"x\"\n";

        Assert.Null(RenderingOverride.DriverIn(existing));
        Assert.Equal(existing, RenderingOverride.Merge(existing, RenderingDriver.D3D12));
    }

    [Fact]
    public void Write_and_read_round_trip_through_the_file()
    {
        Assert.Null(RenderingOverride.Read(_dir));

        Assert.Null(RenderingOverride.Write(_dir, RenderingDriver.Vulkan));
        Assert.Equal(RenderingDriver.Vulkan, RenderingOverride.Read(_dir));

        Assert.Null(RenderingOverride.Write(_dir, RenderingDriver.D3D12));
        Assert.False(File.Exists(FilePath));
        Assert.Null(RenderingOverride.Read(_dir));
    }

    [Fact]
    public void Write_says_why_it_failed()
    {
        var missing = Path.Combine(_dir, "missing");

        var problem = RenderingOverride.Write(missing, RenderingDriver.Vulkan);

        Assert.NotNull(problem);
        Assert.Contains(RenderingOverride.FileName, problem, StringComparison.Ordinal);
    }
}
