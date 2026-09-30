using System.Buffers.Binary;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Launcher.Core.Models;

/// <summary>
/// A glTF 2.0 binary (<c>.glb</c>) split into its JSON (as a mutable tree) and its binary chunk, and written back.
/// Reading checks only the container (header, chunk types and lengths); <see cref="ModelInspector"/> checks what the
/// JSON says. Nothing here touches the file system.
/// </summary>
public sealed class GlbFile
{
    /// <summary>A model file larger than this isn't read at all (A7's budgets make a real one a few MB).</summary>
    public const int MaxBytes = 256 * 1024 * 1024;

    private const uint Magic = 0x46546C67; // "glTF"
    private const uint JsonChunk = 0x4E4F534A; // "JSON"
    private const uint BinChunk = 0x004E4942; // "BIN\0"

    private GlbFile(JsonObject json, byte[] binary)
    {
        Json = json;
        Binary = binary;
    }

    /// <summary>The glTF JSON, editable.</summary>
    public JsonObject Json { get; }

    /// <summary>The binary chunk (buffer 0), or empty.</summary>
    public byte[] Binary { get; private set; }

    /// <summary>Whether the bytes start like a GLB (the magic number), without reading further.</summary>
    public static bool LooksLikeGlb(ReadOnlySpan<byte> data) => data.Length >= 4 && BinaryPrimitives.ReadUInt32LittleEndian(data) == Magic;

    /// <summary>Splits a GLB. False, with a reason for the user, if it isn't a readable glTF 2.0 binary.</summary>
    public static bool TryRead(ReadOnlySpan<byte> data, out GlbFile? file, out string? error)
    {
        file = null;
        if (data.Length < 20 || BinaryPrimitives.ReadUInt32LittleEndian(data) != Magic)
        {
            error = "isn't a glTF binary (.glb)";
            return false;
        }

        if (BinaryPrimitives.ReadUInt32LittleEndian(data[4..]) != 2)
        {
            error = "isn't glTF 2.0 (only version 2 is supported)";
            return false;
        }

        var declared = BinaryPrimitives.ReadUInt32LittleEndian(data[8..]);
        if (declared > data.Length || declared < 20)
        {
            error = "is cut short (its header gives a length longer than the file)";
            return false;
        }

        data = data[..(int)declared];
        var offset = 12;
        JsonObject? json = null;
        byte[]? binary = null;
        while (offset + 8 <= data.Length)
        {
            var length = BinaryPrimitives.ReadUInt32LittleEndian(data[offset..]);
            var type = BinaryPrimitives.ReadUInt32LittleEndian(data[(offset + 4)..]);
            offset += 8;
            if (length > data.Length - offset)
            {
                error = "is cut short (a chunk runs past the end of the file)";
                return false;
            }

            var chunk = data.Slice(offset, (int)length);
            offset += (int)length;
            if (json is null)
            {
                if (type != JsonChunk)
                {
                    error = "doesn't start with a JSON chunk";
                    return false;
                }

                try
                {
                    json = JsonNode.Parse(chunk, new JsonNodeOptions { PropertyNameCaseInsensitive = false }, new JsonDocumentOptions { MaxDepth = 256 }) as JsonObject;
                }
                catch (JsonException e)
                {
                    error = $"has JSON that can't be read ({e.Message})";
                    return false;
                }

                if (json is null)
                {
                    error = "has a JSON chunk that isn't an object";
                    return false;
                }
            }
            else if (type == BinChunk && binary is null)
            {
                binary = chunk.ToArray();
            }

            // Chunks of other types are skipped, as the spec says.
        }

        if (json is null)
        {
            error = "has no JSON chunk";
            return false;
        }

        file = new GlbFile(json, binary ?? []);
        error = null;
        return true;
    }

    /// <summary>A GLB from a JSON tree and a binary chunk (<see cref="GltfBuilder"/>).</summary>
    public static GlbFile Create(JsonObject json, byte[] binary) => new(json, binary);

    /// <summary>Replaces the binary chunk; buffer 0's <c>byteLength</c> follows it.</summary>
    public void SetBinary(byte[] binary)
    {
        Binary = binary;
        if (Json["buffers"] is JsonArray { Count: > 0 } buffers && buffers[0] is JsonObject buffer)
        {
            buffer["byteLength"] = binary.Length;
        }
    }

    /// <summary>The GLB bytes: the JSON chunk padded with spaces, the binary chunk with zeros, both to 4 bytes.</summary>
    public byte[] Write()
    {
        var json = Encoding.UTF8.GetBytes(Json.ToJsonString());
        var jsonLength = Align(json.Length);
        var binLength = Binary.Length == 0 ? 0 : Align(Binary.Length);
        var total = 12 + 8 + jsonLength + (binLength > 0 ? 8 + binLength : 0);
        var output = new byte[total];
        var span = output.AsSpan();
        BinaryPrimitives.WriteUInt32LittleEndian(span, Magic);
        BinaryPrimitives.WriteUInt32LittleEndian(span[4..], 2);
        BinaryPrimitives.WriteUInt32LittleEndian(span[8..], (uint)total);
        BinaryPrimitives.WriteUInt32LittleEndian(span[12..], (uint)jsonLength);
        BinaryPrimitives.WriteUInt32LittleEndian(span[16..], JsonChunk);
        json.CopyTo(span[20..]);
        span.Slice(20 + json.Length, jsonLength - json.Length).Fill((byte)' ');
        if (binLength > 0)
        {
            var at = 20 + jsonLength;
            BinaryPrimitives.WriteUInt32LittleEndian(span[at..], (uint)binLength);
            BinaryPrimitives.WriteUInt32LittleEndian(span[(at + 4)..], BinChunk);
            Binary.CopyTo(span[(at + 8)..]);
        }

        return output;
    }

    internal static int Align(int length) => (length + 3) & ~3;
}
