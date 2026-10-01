using System.Globalization;
using System.Text.Json.Nodes;
using Launcher.Core.Media;

namespace Launcher.Core.Models;

/// <summary>A processed model: the bytes to load (null when rejected) and what the inspector said.</summary>
public sealed record ProcessedModel(byte[]? Glb, ModelReport Report);

/// <summary>
/// Makes a user's <c>.glb</c> fit its budget (A7): it's inspected (<see cref="ModelInspector"/>), rejected if it's
/// broken or more than 2× over a count, and every texture larger than the budget's side is scaled down (decoded and
/// scaled by the OS, <see cref="IImageDecoder"/>, and written back as PNG). The result is what the app loads, from
/// <see cref="ModelCache"/> or the import service's copy. Never throws for a bad file. Does file I/O (a scratch file
/// per scaled texture, since the OS decoder reads files), so never on the main thread.
/// </summary>
public static class ModelProcessor
{
    /// <summary>Bump when processing changes, so cached models are processed again.</summary>
    public const int Version = 2;

    public static ProcessedModel Process(ReadOnlySpan<byte> data, ModelKind kind, IImageDecoder? decoder, string scratchDir)
    {
        ArgumentNullException.ThrowIfNull(scratchDir);
        var inspection = ModelInspector.Inspect(data, kind);
        if (!inspection.Report.Accepted || !GlbFile.TryRead(data, out var file, out _))
        {
            return new ProcessedModel(null, inspection.Report);
        }

        var side = ModelBudget.For(kind).TextureSide;
        var oversized = inspection.Images.Where(i => i.Used && Math.Max(i.Width, i.Height) > side).ToList();
        if (oversized.Count == 0)
        {
            return new ProcessedModel(data.ToArray(), inspection.Report);
        }

        var notes = new List<string>();
        var warnings = new List<string>();
        var replaced = new Dictionary<int, byte[]>();
        if (decoder is null)
        {
            warnings.Add(string.Create(CultureInfo.InvariantCulture,
                $"{oversized.Count} texture(s) are over {side}², and this platform can't scale them down, so they're used as they are"));
        }
        else
        {
            foreach (var image in oversized)
            {
                var scale = (double)side / Math.Max(image.Width, image.Height);
                var width = Math.Max(1, (int)Math.Round(image.Width * scale));
                var height = Math.Max(1, (int)Math.Round(image.Height * scale));
                if (Scale(file!, image, width, height, decoder, scratchDir, out var png, out var error))
                {
                    replaced[image.BufferView] = png;
                    if (file!.Json["images"] is JsonArray images && images[image.Index] is JsonObject entry)
                    {
                        entry["mimeType"] = "image/png";
                    }

                    notes.Add(string.Create(CultureInfo.InvariantCulture,
                        $"image {image.Index} was scaled down from {image.Width}×{image.Height} to {width}×{height}"));
                }
                else
                {
                    warnings.Add(string.Create(CultureInfo.InvariantCulture,
                        $"image {image.Index} ({image.Width}×{image.Height}) couldn't be scaled down ({error}), so it's used as it is"));
                }
            }
        }

        if (replaced.Count == 0)
        {
            return new ProcessedModel(data.ToArray(), Append(inspection.Report, warnings, notes));
        }

        Repack(file!, replaced);
        var output = file!.Write();
        var final = ModelInspector.Inspect(output, kind).Report;
        return final.Accepted
            ? new ProcessedModel(output, Append(final, warnings, notes))
            : new ProcessedModel(null, final);
    }

    private static ModelReport Append(ModelReport report, List<string> warnings, List<string> notes) =>
        warnings.Count == 0 && notes.Count == 0
            ? report
            : report with { Warnings = [.. report.Warnings, .. warnings], Notes = [.. report.Notes, .. notes] };

    private static bool Scale(GlbFile file, ModelImage image, int width, int height, IImageDecoder decoder, string scratchDir, out byte[] png, out string? error)
    {
        png = [];
        var scratch = Path.Combine(scratchDir, $"scale-{Guid.NewGuid():N}{(image.MimeType == "image/png" ? ".png" : ".jpg")}");
        try
        {
            Directory.CreateDirectory(scratchDir);
            File.WriteAllBytes(scratch, ModelInspector.ImageBytes(file, image.Index).ToArray());
            var rgba = new byte[width * height * 4];
            if (!decoder.TryDecodeScaled(scratch, width, height, rgba, out error))
            {
                return false;
            }

            png = PngEncoder.Encode(rgba, width, height);
            return true;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            error = e.Message;
            return false;
        }
        finally
        {
            try
            {
                File.Delete(scratch);
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                // A scratch file left behind is harmless.
            }
        }
    }

    /// <summary>
    /// Rebuilds the binary chunk view by view, each on a 4-byte boundary, with the replaced views' new bytes; every
    /// accessor keeps its offset within its view, so nothing else changes.
    /// </summary>
    private static void Repack(GlbFile file, Dictionary<int, byte[]> replaced)
    {
        using var binary = new MemoryStream();
        var views = file.Json["bufferViews"] as JsonArray ?? [];
        for (var i = 0; i < views.Count; i++)
        {
            if (views[i] is not JsonObject view)
            {
                continue;
            }

            var bytes = replaced.TryGetValue(i, out var png) ? png : ModelInspector.ViewBytes(file, i).ToArray();
            while (binary.Length % 4 != 0)
            {
                binary.WriteByte(0);
            }

            view["byteOffset"] = (int)binary.Length;
            view["byteLength"] = bytes.Length;
            if (replaced.ContainsKey(i))
            {
                view.Remove("byteStride");
            }

            binary.Write(bytes);
        }

        while (binary.Length % 4 != 0)
        {
            binary.WriteByte(0);
        }

        file.SetBinary(binary.ToArray());
    }
}
