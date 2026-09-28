using System.Reflection;
using System.Text.Json;

namespace Launcher.Core.Tests.TestSupport;

/// <summary>The tests/FakeEmulator app, built alongside the tests (see its Program.cs for its options).</summary>
public static class FakeEmulator
{
    public static string ExeName { get; } = OperatingSystem.IsWindows() ? "FakeEmulator.exe" : "FakeEmulator";

    /// <summary>Its build output, from the test project's <c>FakeEmulatorDir</c> metadata.</summary>
    public static string OutputDir { get; } = Path.GetFullPath(
        typeof(FakeEmulator).Assembly.GetCustomAttributes<AssemblyMetadataAttribute>().Single(a => a.Key == "FakeEmulatorDir").Value!);

    /// <summary>
    /// Copies the fake into <paramref name="folder"/> as <paramref name="exeName"/>, so tests can put it at paths
    /// with spaces and non-ASCII characters. The .NET app host finds FakeEmulator.dll by name, so the exe can be renamed.
    /// </summary>
    public static string InstallAt(string folder, string? exeName = null)
    {
        Directory.CreateDirectory(folder);
        foreach (var file in Directory.GetFiles(OutputDir))
        {
            var name = Path.GetFileName(file);
            var target = name == ExeName && exeName is not null ? exeName : name;
            File.Copy(file, Path.Combine(folder, target), overwrite: true);
        }

        return Path.Combine(folder, exeName ?? ExeName);
    }

    public static FakeLog ReadLog(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var root = document.RootElement;
        return new FakeLog(
            root.GetProperty("args").EnumerateArray().Select(a => a.GetString()!).ToArray(),
            root.GetProperty("cwd").GetString()!,
            root.GetProperty("commandLine").GetString()!,
            root.GetProperty("processId").GetInt32());
    }
}

/// <summary>What the fake emulator saw.</summary>
public sealed record FakeLog(string[] Args, string WorkingDirectory, string CommandLine, int ProcessId);
