using System.Globalization;
using System.Runtime.Versioning;
using Launcher.Core.Media;
using static Launcher.Core.Platform.Linux.PdfiumNativeMethods;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// Renders manuals with the PDFium the AppImage carries (L4, the owner's choice: pdfium-binaries' build). It gives the
/// app what <c>WindowsPdfRenderer</c> does on Windows: page sizes in device-independent pixels, turned as shown, and
/// each page drawn whole, scaled to the size asked for, on white paper, as opaque RGBA straight into the caller's
/// buffer (PDFium writes BGRA with its bytes reversed). PDFium isn't thread-safe, so every call into it, from every
/// reader, takes one lock: two readers on two threads take turns, where Windows renders them at once. The library is
/// loaded by the first manual opened (<see cref="BundledLibraries"/>).
/// </summary>
[SupportedOSPlatform("linux")]
public sealed unsafe class PdfiumRenderer : IPdfRenderer
{
    private static readonly object Gate = new();
    private static bool _initialised;

    public IPdfReader? Open(string path, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (!File.Exists(path))
        {
            error = "the file isn't there";
            return null;
        }

        error = BundledLibraries.Load(BundledLibraries.Pdfium);
        if (error is not null)
        {
            return null;
        }

        lock (Gate)
        {
            if (!_initialised)
            {
                InitLibrary();
                _initialised = true;
            }

            var document = LoadDocument(path, null);
            if (document == 0)
            {
                error = Explain("read it as a PDF", GetLastError());
                return null;
            }

            var pages = GetPageCount(document);
            if (pages > 0)
            {
                return new Reader(document, pages);
            }

            CloseDocument(document);
            error = "it has no pages";
            return null;
        }
    }

    private static string Explain(string what, nuint code) => (int)code switch
    {
        ErrorPassword => "it's protected by a password",
        ErrorFile => "the file couldn't be opened",
        ErrorFormat => $"couldn't {what} (it isn't one, or it's damaged)",
        ErrorSecurity => $"couldn't {what} (its security scheme isn't supported)",
        ErrorPage => $"couldn't {what} (a page is missing or damaged)",
        _ => string.Create(CultureInfo.InvariantCulture, $"couldn't {what} (PDFium error {code})"),
    };

    private sealed class Reader(nint document, int pages) : IPdfReader
    {
        private nint _document = document;

        /// <summary>The page last rendered, kept until another is asked for.</summary>
        private nint _page;
        private int _pageIndex = -1;

        public int PageCount { get; } = pages;

        public bool TryGetPageSize(int page, out float width, out float height)
        {
            (width, height) = (0, 0);
            ObjectDisposedException.ThrowIf(_document == 0, this);
            if (page < 0 || page >= PageCount)
            {
                return false;
            }

            SizeF size;
            lock (Gate)
            {
                if (GetPageSizeByIndex(_document, page, &size) == 0)
                {
                    return false;
                }
            }

            if (!(size.Width > 0) || !(size.Height > 0))
            {
                return false;
            }

            // Points (1/72 inch) to device-independent pixels (1/96), as Windows gives them.
            (width, height) = (size.Width * 96 / 72, size.Height * 96 / 72);
            return true;
        }

        public bool TryRender(int page, int width, int height, Span<byte> rgba, out string? error)
        {
            ArgumentOutOfRangeException.ThrowIfNegativeOrZero(width);
            ArgumentOutOfRangeException.ThrowIfNegativeOrZero(height);
            if (rgba.Length < width * height * 4)
            {
                throw new ArgumentException("the buffer is too small", nameof(rgba));
            }

            ObjectDisposedException.ThrowIf(_document == 0, this);
            if (page < 0 || page >= PageCount)
            {
                error = string.Create(CultureInfo.InvariantCulture, $"there's no page {page + 1}");
                return false;
            }

            lock (Gate)
            {
                error = Load(page) ?? Render(width, height, rgba);
            }

            return error is null;
        }

        public void Dispose()
        {
            lock (Gate)
            {
                if (_page != 0)
                {
                    ClosePage(_page);
                }

                if (_document != 0)
                {
                    CloseDocument(_document);
                }
            }

            (_page, _pageIndex, _document) = (0, -1, 0);
        }

        /// <summary>Makes <paramref name="index"/> the current page; null, or why it can't be read. Under the lock.</summary>
        private string? Load(int index)
        {
            if (index == _pageIndex)
            {
                return null;
            }

            if (_page != 0)
            {
                ClosePage(_page);
            }

            _page = LoadPage(_document, index);
            _pageIndex = _page == 0 ? -1 : index;
            return _page == 0 ? Explain(string.Create(CultureInfo.InvariantCulture, $"read page {index + 1}"), GetLastError()) : null;
        }

        /// <summary>The current page, whole, into <paramref name="rgba"/>; null, or why it couldn't be. Under the lock.</summary>
        private string? Render(int width, int height, Span<byte> rgba)
        {
            fixed (byte* pixels = rgba)
            {
                var bitmap = BitmapCreate(width, height, BitmapBgra, pixels, width * 4);
                if (bitmap == 0)
                {
                    return "couldn't make the page's bitmap";
                }

                _ = BitmapFillRect(bitmap, 0, 0, width, height, 0xFFFF_FFFF);
                RenderPageBitmap(bitmap, _page, 0, 0, width, height, 0, RenderAnnotations | RenderReverseByteOrder);
                BitmapDestroy(bitmap);
                return null;
            }
        }
    }
}
