using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// The PDFium calls <see cref="PdfiumRenderer"/> makes (<c>fpdfview.h</c>), bound by hand (no package), to the library
/// the AppImage carries (<see cref="BundledLibraries"/>): call <see cref="BundledLibraries.Load"/> with
/// <see cref="BundledLibraries.Pdfium"/> first. PDFium isn't thread-safe: every call is made under one lock.
/// </summary>
[SupportedOSPlatform("linux")]
internal static unsafe partial class PdfiumNativeMethods
{
    public const int ErrorFile = 2;
    public const int ErrorFormat = 3;
    public const int ErrorPassword = 4;
    public const int ErrorSecurity = 5;
    public const int ErrorPage = 6;
    public const int BitmapBgra = 4;
    public const int RenderAnnotations = 0x01;
    public const int RenderReverseByteOrder = 0x10;

    private const string Pdfium = BundledLibraries.Prefix + "libpdfium.so";

    [StructLayout(LayoutKind.Sequential)]
    public struct SizeF
    {
        public float Width;
        public float Height;
    }

    [LibraryImport(Pdfium, EntryPoint = "FPDF_InitLibrary")]
    public static partial void InitLibrary();

    [LibraryImport(Pdfium, EntryPoint = "FPDF_LoadDocument", StringMarshalling = StringMarshalling.Utf8)]
    public static partial nint LoadDocument(string path, string? password);

    [LibraryImport(Pdfium, EntryPoint = "FPDF_GetLastError")]
    public static partial nuint GetLastError();

    [LibraryImport(Pdfium, EntryPoint = "FPDF_GetPageCount")]
    public static partial int GetPageCount(nint document);

    [LibraryImport(Pdfium, EntryPoint = "FPDF_GetPageSizeByIndexF")]
    public static partial int GetPageSizeByIndex(nint document, int index, SizeF* size);

    [LibraryImport(Pdfium, EntryPoint = "FPDF_LoadPage")]
    public static partial nint LoadPage(nint document, int index);

    [LibraryImport(Pdfium, EntryPoint = "FPDF_ClosePage")]
    public static partial void ClosePage(nint page);

    [LibraryImport(Pdfium, EntryPoint = "FPDF_CloseDocument")]
    public static partial void CloseDocument(nint document);

    [LibraryImport(Pdfium, EntryPoint = "FPDFBitmap_CreateEx")]
    public static partial nint BitmapCreate(int width, int height, int format, void* firstScan, int stride);

    [LibraryImport(Pdfium, EntryPoint = "FPDFBitmap_FillRect")]
    public static partial int BitmapFillRect(nint bitmap, int left, int top, int width, int height, uint colour);

    [LibraryImport(Pdfium, EntryPoint = "FPDF_RenderPageBitmap")]
    public static partial void RenderPageBitmap(nint bitmap, nint page, int left, int top, int width, int height, int rotate, int flags);

    [LibraryImport(Pdfium, EntryPoint = "FPDFBitmap_Destroy")]
    public static partial void BitmapDestroy(nint bitmap);
}
