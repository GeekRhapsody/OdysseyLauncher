using System.Globalization;
using System.Text;

namespace Launcher.Core.Tests.TestSupport;

/// <summary>
/// Writes small, valid PDFs by hand, so the manual tests need no fixture file: each page is white with its colour
/// filling its top-left quarter and its number in Helvetica (one of the standard fonts, so nothing is embedded).
/// </summary>
internal static class TestPdfs
{
    /// <summary>A page's size in points (72 to the inch) and the colour of its top-left quarter.</summary>
    public sealed record Page(int Width, int Height, (byte R, byte G, byte B) Colour);

    public static void Write(string path, params Page[] pages) => File.WriteAllBytes(path, Bytes(pages));

    public static byte[] Bytes(params Page[] pages)
    {
        ArgumentOutOfRangeException.ThrowIfZero(pages.Length);
        var pdf = new StringBuilder("%PDF-1.4\n");
        var offsets = new List<int>();
        void Object(string body)
        {
            offsets.Add(Encoding.ASCII.GetByteCount(pdf.ToString()));
            pdf.Append(CultureInfo.InvariantCulture, $"{offsets.Count} 0 obj\n{body}\nendobj\n");
        }

        // 1 the catalogue, 2 the page tree, 3 the font, then each page and its contents.
        var kids = string.Join(' ', pages.Select((_, i) => string.Create(CultureInfo.InvariantCulture, $"{4 + (i * 2)} 0 R")));
        Object("<< /Type /Catalog /Pages 2 0 R >>");
        Object(string.Create(CultureInfo.InvariantCulture, $"<< /Type /Pages /Kids [{kids}] /Count {pages.Length} >>"));
        Object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
        for (var i = 0; i < pages.Length; i++)
        {
            var page = pages[i];
            var (r, g, b) = page.Colour;
            var contents = string.Create(
                CultureInfo.InvariantCulture,
                $"{r / 255.0:0.###} {g / 255.0:0.###} {b / 255.0:0.###} rg 0 {page.Height / 2} {page.Width / 2} {page.Height - (page.Height / 2)} re f\n"
                + $"0 0 0 rg BT /F1 {page.Height / 8} Tf {page.Width * 0.55:0} {page.Height * 0.1:0} Td (Page {i + 1}) Tj ET\n");
            Object(string.Create(
                CultureInfo.InvariantCulture,
                $"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page.Width} {page.Height}] /Resources << /Font << /F1 3 0 R >> >> /Contents {5 + (i * 2)} 0 R >>"));
            Object(string.Create(CultureInfo.InvariantCulture, $"<< /Length {Encoding.ASCII.GetByteCount(contents)} >>\nstream\n{contents}endstream"));
        }

        var xref = Encoding.ASCII.GetByteCount(pdf.ToString());
        pdf.Append(CultureInfo.InvariantCulture, $"xref\n0 {offsets.Count + 1}\n0000000000 65535 f \n");
        foreach (var offset in offsets)
        {
            pdf.Append(CultureInfo.InvariantCulture, $"{offset:D10} 00000 n \n");
        }

        pdf.Append(CultureInfo.InvariantCulture, $"trailer\n<< /Size {offsets.Count + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n");
        return Encoding.ASCII.GetBytes(pdf.ToString());
    }
}
