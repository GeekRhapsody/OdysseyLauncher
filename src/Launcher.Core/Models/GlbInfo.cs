using System.Buffers.Binary;
using System.Text.Json;

namespace Launcher.Core.Models;

/// <summary>
/// What a <c>.glb</c>'s JSON chunk says, read without touching its binary chunk: enough for theme validation to check
/// a template's slot materials before the app loads it. Does file I/O: never on the main thread.
/// </summary>
public static class GlbInfo
{
    private const int MaxJsonBytes = 16 * 1024 * 1024;

    /// <summary>The material names, in file order. False, with a reason, if the file isn't a readable glTF 2.0 binary.</summary>
    public static bool TryReadMaterials(string path, out IReadOnlyList<string> materials, out string? error)
    {
        materials = [];
        try
        {
            using var file = File.OpenRead(path);
            Span<byte> header = stackalloc byte[20];
            if (file.ReadAtLeast(header, header.Length, throwOnEndOfStream: false) < header.Length
                || !header[..4].SequenceEqual("glTF"u8)
                || !header[16..20].SequenceEqual("JSON"u8))
            {
                error = "isn't a glTF binary (.glb)";
                return false;
            }

            if (BinaryPrimitives.ReadUInt32LittleEndian(header[4..]) != 2)
            {
                error = "isn't glTF 2.0";
                return false;
            }

            var length = BinaryPrimitives.ReadInt32LittleEndian(header[12..]);
            if (length <= 0 || length > MaxJsonBytes)
            {
                error = "has a JSON chunk of an unexpected size";
                return false;
            }

            var json = new byte[length];
            if (file.ReadAtLeast(json, length, throwOnEndOfStream: false) < length)
            {
                error = "is cut short";
                return false;
            }

            using var document = JsonDocument.Parse(json);
            var names = new List<string>();
            if (document.RootElement.TryGetProperty("materials", out var list) && list.ValueKind == JsonValueKind.Array)
            {
                foreach (var material in list.EnumerateArray())
                {
                    names.Add(material.TryGetProperty("name", out var name) && name.ValueKind == JsonValueKind.String ? name.GetString()! : string.Empty);
                }
            }

            materials = names;
            error = null;
            return true;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or JsonException)
        {
            error = $"couldn't be read: {e.Message}";
            return false;
        }
    }
}
