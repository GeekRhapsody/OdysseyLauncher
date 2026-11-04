using System.Globalization;
using System.Reflection;
using System.Runtime.Versioning;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Linux;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Platform;

/// <summary>
/// The bundled FFmpeg's bindings (L4): their struct offsets and constants against the headers it was built from
/// (<c>ffmpeg-abi.txt</c>, which tools/linux/setup.sh writes with tools/linux/ffmpeg-abi.c and test.sh copies beside
/// the tests), and its libraries loaded from beside Launcher.Core, never the system's.
/// </summary>
public sealed class FfmpegAbiTests
{
    [Fact]
    [SupportedOSPlatform("linux")]
    public void The_bindings_offsets_and_constants_are_the_headers()
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), "Linux-only.");
        var file = Path.Combine(AppContext.BaseDirectory, "ffmpeg-abi.txt");
        Assert.True(File.Exists(file), "no ffmpeg-abi.txt beside the tests: run them with tools/linux/test.sh");

        var headers = File.ReadAllLines(file)
            .Select(line => line.Split(' '))
            .ToDictionary(parts => parts[0], parts => long.Parse(parts[1], CultureInfo.InvariantCulture), StringComparer.Ordinal);
        var bindings = typeof(FfmpegNativeMethods.Abi)
            .GetFields(BindingFlags.Public | BindingFlags.Static)
            .Where(field => field.IsLiteral)
            .ToDictionary(field => field.Name, field => Convert.ToInt64(field.GetRawConstantValue(), CultureInfo.InvariantCulture), StringComparer.Ordinal);

        Assert.Equal(headers.Keys.Order(StringComparer.Ordinal), bindings.Keys.Order(StringComparer.Ordinal));
        foreach (var (name, value) in headers)
        {
            Assert.True(bindings[name] == value, $"{name} is {bindings[name]} in FfmpegNativeMethods.Abi, {value} in FFmpeg's headers");
        }
    }

    [Fact]
    [SupportedOSPlatform("linux")]
    public void FFmpeg_is_loaded_from_beside_Launcher_Core_only()
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), "Linux-only.");
        using (var reader = PlatformServices.CreateVideoDecoder()!.OpenVideo(VideoFixtures.File("red-blue.mp4"), out var error))
        {
            Assert.True(reader is not null, error);
        }

        // Every mapping of an FFmpeg library: none from anywhere else, and all five from here.
        var mapped = File.ReadAllLines("/proc/self/maps")
            .Select(line => line.Split(' ', 6, StringSplitOptions.RemoveEmptyEntries))
            .Where(parts => parts.Length == 6 && Path.GetFileName(parts[5].Trim()) is { } name
                && (name.StartsWith("libav", StringComparison.Ordinal) || name.StartsWith("libsw", StringComparison.Ordinal)))
            .Select(parts => parts[5].Trim())
            .ToHashSet(StringComparer.Ordinal);
        var expected = BundledLibraries.Ffmpeg.Select(file => Path.Combine(AppContext.BaseDirectory, file)).ToHashSet(StringComparer.Ordinal);
        Assert.Equal(expected.Order(StringComparer.Ordinal), mapped.Order(StringComparer.Ordinal));
    }
}
