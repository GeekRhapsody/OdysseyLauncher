using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Launcher.Core.Diagnostics;

/// <summary>Serialises <see cref="BenchReport"/> as indented snake_case JSON.</summary>
public static class BenchReportWriter
{
    public static string Serialize(BenchReport report)
    {
        ArgumentNullException.ThrowIfNull(report);
        return JsonSerializer.Serialize(report, BenchJsonContext.Default.BenchReport).ReplaceLineEndings("\n");
    }

    /// <summary>Writes the report as UTF-8 JSON (no BOM), creating the folder if needed.</summary>
    public static void Write(string path, BenchReport report)
    {
        ArgumentException.ThrowIfNullOrEmpty(path);
        var json = Serialize(report);
        var folder = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(folder))
        {
            Directory.CreateDirectory(folder);
        }

        File.WriteAllText(path, json + "\n", new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
    }
}

[JsonSourceGenerationOptions(WriteIndented = true, PropertyNamingPolicy = JsonKnownNamingPolicy.SnakeCaseLower)]
[JsonSerializable(typeof(BenchReport))]
internal sealed partial class BenchJsonContext : JsonSerializerContext
{
}
