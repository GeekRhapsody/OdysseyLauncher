using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Launcher.Core.Media;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Renders PDFs with Windows.Data.Pdf, which ships with Windows 10, through raw COM and WinRT vtable slots as
/// <see cref="WicImageDecoder"/> calls WIC: no interop package or projection. The file is opened as a WinRT stream (no
/// <c>StorageFile</c>) and loaded as a <c>PdfDocument</c>, waited for on the calling thread by polling its
/// <c>IAsyncInfo</c>. Pages are drawn by its native renderer (<c>IPdfRendererNative</c>) onto a Direct3D 11 surface on a
/// WARP (software) device each reader makes and frees itself, then copied back to the CPU: its own
/// <c>RenderToStreamAsync</c> draws on a hardware device it keeps for the process's life, which, beside Godot's Direct3D
/// 12 renderer, brings the process down as it exits (exception 0x87A). Slots and IIDs are the Windows SDK's
/// (<c>windows.data.pdf.h</c>, <c>windows.data.pdf.interop.h</c>, <c>asyncinfo.h</c>, <c>d3d11.h</c>, <c>dxgi.h</c>).
/// </summary>
[SupportedOSPlatform("windows")]
public sealed unsafe partial class WindowsPdfRenderer : IPdfRenderer
{
    // IUnknown takes 0-2, IInspectable 3-5.
    private const int SlotQueryInterface = 0;
    private const int SlotRelease = 2;
    private const int SlotStaticsLoadFromStreamAsync = 8;
    private const int SlotDocumentGetPage = 6;
    private const int SlotDocumentGetPageCount = 7;
    private const int SlotPageGetSize = 10;
    private const int SlotAsyncGetResults = 8;
    private const int SlotAsyncInfoGetStatus = 7;
    private const int SlotAsyncInfoGetErrorCode = 8;
    private const int SlotAsyncInfoCancel = 9;
    private const int SlotRendererRenderPageToSurface = 3;
    private const int SlotDeviceCreateTexture2D = 5;
    private const int SlotContextMap = 14;
    private const int SlotContextUnmap = 15;
    private const int SlotContextCopyResource = 47;

    private const int StatusStarted = 0;
    private const int StatusCompleted = 1;
    private const int StatusCanceled = 2;
    private const uint FileAccessRead = 0;
    private const uint InitMultithreaded = 1;
    private const int DriverTypeWarp = 5;
    private const uint CreateDeviceBgraSupport = 0x20;
    private const uint D3D11SdkVersion = 7;
    private const int FormatB8G8R8A8 = 87;
    private const int UsageDefault = 0;
    private const int UsageStaging = 3;
    private const uint BindRenderTarget = 0x20;
    private const uint CpuAccessRead = 0x2_0000;
    private const int MapRead = 1;
    private const int FileNotFound = unchecked((int)0x8007_0002);
    private const int PathNotFound = unchecked((int)0x8007_0003);
    private const int InvalidPassword = unchecked((int)0x8007_0056);
    private const int TimedOut = unchecked((int)0x8000_05B4);
    private const int NoInterface = unchecked((int)0x8000_4002);
    private static readonly TimeSpan Patience = TimeSpan.FromSeconds(60);

    private static readonly Guid IidPdfDocumentStatics = new("433a0b5f-c007-4788-90f2-08143d922599");
    private static readonly Guid IidRandomAccessStream = new("905a0fe1-bc53-11df-8c49-001e4fc686da");
    private static readonly Guid IidAsyncInfo = new("00000036-0000-0000-c000-000000000046");
    private static readonly Guid IidDxgiDevice = new("54ec77fa-1377-44e6-8c32-88fd5f44c84c");
    private static readonly Guid IidDxgiSurface = new("cafcb56c-6ac3-4889-bf47-9e23bbd260ec");

    public IPdfReader? Open(string path, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);

        // Each reader initialises WinRT on its thread, and uninitialises it there when it's disposed.
        var initialised = RoInitialize(InitMultithreaded) >= 0;
        nint file = 0, statics = 0, operation = 0, document = 0;
        Device device = default;
        IPdfReader? reader = null;
        try
        {
            int hr;
            fixed (char* name = path)
            {
                var iid = IidRandomAccessStream;
                hr = CreateRandomAccessStreamOnFile(name, FileAccessRead, &iid, &file);
            }

            if (hr < 0)
            {
                error = hr is FileNotFound or PathNotFound ? "the file isn't there" : Failure("open the file", hr);
                return null;
            }

            statics = ActivationFactory("Windows.Data.Pdf.PdfDocument", IidPdfDocumentStatics, out hr);
            if (statics == 0)
            {
                error = Failure("start Windows' PDF reader", hr);
                return null;
            }

            hr = ((delegate* unmanaged<nint, nint, nint*, int>)Slot(statics, SlotStaticsLoadFromStreamAsync))(statics, file, &operation);
            if (hr >= 0)
            {
                hr = Wait(operation);
            }

            if (hr >= 0)
            {
                hr = ((delegate* unmanaged<nint, nint*, int>)Slot(operation, SlotAsyncGetResults))(operation, &document);
            }

            if (hr < 0 || document == 0)
            {
                error = hr == InvalidPassword ? "it's protected by a password" : Failure("read it as a PDF", hr);
                return null;
            }

            uint pages;
            hr = ((delegate* unmanaged<nint, uint*, int>)Slot(document, SlotDocumentGetPageCount))(document, &pages);
            if (hr < 0)
            {
                error = Failure("count its pages", hr);
                return null;
            }

            if (pages == 0)
            {
                error = "it has no pages";
                return null;
            }

            device = Device.Create(out hr);
            if (device.Renderer == 0)
            {
                error = Failure("start the page renderer", hr);
                return null;
            }

            error = null;
            reader = new Reader(document, file, device, (int)pages, initialised);
            document = 0;
            file = 0;
            device = default;
            return reader;
        }
        finally
        {
            device.Release();
            Release(document);
            Release(operation);
            Release(statics);
            Release(file);
            if (reader is null && initialised)
            {
                RoUninitialize();
            }
        }
    }

    private sealed class Reader(nint document, nint file, Device device, int pages, bool initialised) : IPdfReader
    {
        private nint _document = document;
        private nint _file = file;
        private Device _device = device;
        private bool _initialised = initialised;
        private nint _page;
        private int _pageIndex = -1;

        // The render target and its CPU-readable copy, kept while pages come at the same size.
        private nint _target;
        private nint _staging;
        private int _width;
        private int _height;

        public int PageCount { get; } = pages;

        public bool TryGetPageSize(int page, out float width, out float height)
        {
            width = 0;
            height = 0;
            var pdfPage = Page(page, out _);
            if (pdfPage == 0)
            {
                return false;
            }

            Size size;
            if (((delegate* unmanaged<nint, Size*, int>)Slot(pdfPage, SlotPageGetSize))(pdfPage, &size) < 0
                || !(size.Width > 0) || !(size.Height > 0))
            {
                return false;
            }

            width = size.Width;
            height = size.Height;
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

            var pdfPage = Page(page, out error);
            if (pdfPage == 0)
            {
                return false;
            }

            var hr = Textures(width, height);
            if (hr < 0)
            {
                error = Failure("make the page's surface", hr);
                return false;
            }

            var surface = Query(_target, IidDxgiSurface);
            if (surface == 0)
            {
                error = Failure("make the page's surface", NoInterface);
                return false;
            }

            try
            {
                // The whole page (an empty source rectangle), scaled to the size, on white.
                var parameters = new RenderParams
                {
                    DestinationWidth = (uint)width,
                    DestinationHeight = (uint)height,
                    BackgroundR = 1,
                    BackgroundG = 1,
                    BackgroundB = 1,
                    BackgroundA = 1,
                    IgnoreHighContrast = 1,
                };
                hr = ((delegate* unmanaged<nint, nint, nint, Point, RenderParams*, int>)Slot(_device.Renderer, SlotRendererRenderPageToSurface))(
                    _device.Renderer, pdfPage, surface, default, &parameters);
            }
            finally
            {
                Release(surface);
            }

            if (hr < 0)
            {
                error = Failure("render the page", hr);
                return false;
            }

            var context = _device.Context;
            ((delegate* unmanaged<nint, nint, nint, void>)Slot(context, SlotContextCopyResource))(context, _staging, _target);
            MappedSubresource mapped;
            hr = ((delegate* unmanaged<nint, nint, uint, int, uint, MappedSubresource*, int>)Slot(context, SlotContextMap))(
                context, _staging, 0, MapRead, 0, &mapped);
            if (hr < 0)
            {
                error = Failure("read the rendered page", hr);
                return false;
            }

            try
            {
                // BGRA rows at the driver's pitch, to RGBA rows packed; the page is paper, so it's opaque.
                var rowBytes = width * 4;
                for (var y = 0; y < height; y++)
                {
                    var source = new ReadOnlySpan<byte>((byte*)mapped.Data + ((long)y * mapped.RowPitch), rowBytes);
                    var row = rgba.Slice(y * rowBytes, rowBytes);
                    for (var x = 0; x < rowBytes; x += 4)
                    {
                        row[x] = source[x + 2];
                        row[x + 1] = source[x + 1];
                        row[x + 2] = source[x];
                        row[x + 3] = 255;
                    }
                }
            }
            finally
            {
                ((delegate* unmanaged<nint, nint, uint, void>)Slot(context, SlotContextUnmap))(context, _staging, 0);
            }

            return true;
        }

        public void Dispose()
        {
            Release(_page);
            _page = 0;
            _pageIndex = -1;
            ReleaseTextures();
            _device.Release();
            _device = default;
            Release(_document);
            _document = 0;
            Release(_file);
            _file = 0;
            if (_initialised)
            {
                _initialised = false;
                RoUninitialize();
            }
        }

        /// <summary>The page (the reader's: don't release it), kept until another is asked for; 0 if it can't be read.</summary>
        private nint Page(int index, out string? error)
        {
            ObjectDisposedException.ThrowIf(_document == 0, this);
            if (index < 0 || index >= PageCount)
            {
                error = string.Create(CultureInfo.InvariantCulture, $"there's no page {index + 1}");
                return 0;
            }

            error = null;
            if (index == _pageIndex)
            {
                return _page;
            }

            Release(_page);
            _page = 0;
            _pageIndex = -1;
            nint page;
            var hr = ((delegate* unmanaged<nint, uint, nint*, int>)Slot(_document, SlotDocumentGetPage))(_document, (uint)index, &page);
            if (hr < 0 || page == 0)
            {
                error = Failure(string.Create(CultureInfo.InvariantCulture, $"read page {index + 1}"), hr);
                return 0;
            }

            _page = page;
            _pageIndex = index;
            return page;
        }

        /// <summary>The render target and its staging copy at this size, made again only when the size changes.</summary>
        private int Textures(int width, int height)
        {
            if (_target != 0 && width == _width && height == _height)
            {
                return 0;
            }

            ReleaseTextures();
            var description = new Texture2DDescription
            {
                Width = (uint)width,
                Height = (uint)height,
                MipLevels = 1,
                ArraySize = 1,
                Format = FormatB8G8R8A8,
                SampleCount = 1,
                Usage = UsageDefault,
                BindFlags = BindRenderTarget,
            };
            var create = (delegate* unmanaged<nint, Texture2DDescription*, void*, nint*, int>)Slot(_device.Device3D, SlotDeviceCreateTexture2D);
            nint target, staging;
            var hr = create(_device.Device3D, &description, null, &target);
            if (hr < 0)
            {
                return hr;
            }

            description.Usage = UsageStaging;
            description.BindFlags = 0;
            description.CpuAccessFlags = CpuAccessRead;
            hr = create(_device.Device3D, &description, null, &staging);
            if (hr < 0)
            {
                Release(target);
                return hr;
            }

            (_target, _staging, _width, _height) = (target, staging, width, height);
            return 0;
        }

        private void ReleaseTextures()
        {
            Release(_staging);
            Release(_target);
            (_target, _staging, _width, _height) = (0, 0, 0, 0);
        }
    }

    /// <summary>A reader's WARP device, its immediate context, and the PDF renderer drawing on it.</summary>
    private struct Device
    {
        public nint Device3D;
        public nint Context;
        public nint Renderer;

        /// <summary>The device, or none (its parts released) if it can't be made.</summary>
        public static Device Create(out int hr)
        {
            var made = default(Device);
            nint device, context;
            hr = D3D11CreateDevice(0, DriverTypeWarp, 0, CreateDeviceBgraSupport, null, 0, D3D11SdkVersion, &device, null, &context);
            if (hr < 0)
            {
                return made;
            }

            made.Device3D = device;
            made.Context = context;
            var dxgi = Query(device, IidDxgiDevice);
            if (dxgi == 0)
            {
                hr = NoInterface;
                made.Release();
                return made;
            }

            nint renderer;
            hr = PdfCreateRenderer(dxgi, &renderer);
            WindowsPdfRenderer.Release(dxgi);
            if (hr < 0)
            {
                made.Release();
                return made;
            }

            made.Renderer = renderer;
            return made;
        }

        public void Release()
        {
            WindowsPdfRenderer.Release(Renderer);
            WindowsPdfRenderer.Release(Context);
            WindowsPdfRenderer.Release(Device3D);
            this = default;
        }
    }

    /// <summary>Waits for an <c>IAsyncOperation</c> or <c>IAsyncAction</c> to finish; its error, or S_OK (then call its <c>GetResults</c>).</summary>
    private static int Wait(nint asyncOperation)
    {
        var info = Query(asyncOperation, IidAsyncInfo);
        if (info == 0)
        {
            return NoInterface;
        }

        try
        {
            var getStatus = (delegate* unmanaged<nint, int*, int>)Slot(info, SlotAsyncInfoGetStatus);
            var started = Environment.TickCount64;
            var spin = default(SpinWait);
            int status;
            while (true)
            {
                var hr = getStatus(info, &status);
                if (hr < 0)
                {
                    return hr;
                }

                if (status != StatusStarted)
                {
                    break;
                }

                if (Environment.TickCount64 - started > Patience.TotalMilliseconds)
                {
                    _ = ((delegate* unmanaged<nint, int>)Slot(info, SlotAsyncInfoCancel))(info);
                    return TimedOut;
                }

                // Loading takes milliseconds: spin briefly, then sleep a millisecond at a time.
                if (spin.Count < 20)
                {
                    spin.SpinOnce(sleep1Threshold: -1);
                }
                else
                {
                    Thread.Sleep(1);
                }
            }

            if (status == StatusCompleted)
            {
                return 0;
            }

            if (status == StatusCanceled)
            {
                return unchecked((int)0x8000_4004); // E_ABORT
            }

            int error;
            return ((delegate* unmanaged<nint, int*, int>)Slot(info, SlotAsyncInfoGetErrorCode))(info, &error) < 0 || error >= 0
                ? unchecked((int)0x8000_4005) // E_FAIL
                : error;
        }
        finally
        {
            // Not closed: that would refuse the GetResults to come. Releasing it is enough.
            Release(info);
        }
    }

    /// <summary>The runtime class's activation factory as <paramref name="iid"/> (release it), or 0.</summary>
    private static nint ActivationFactory(string className, Guid iid, out int hr)
    {
        nint name;
        fixed (char* chars = className)
        {
            hr = WindowsCreateString(chars, (uint)className.Length, &name);
        }

        if (hr < 0)
        {
            return 0;
        }

        try
        {
            nint factory;
            hr = RoGetActivationFactory(name, &iid, &factory);
            return hr < 0 ? 0 : factory;
        }
        finally
        {
            _ = WindowsDeleteString(name);
        }
    }

    private static nint Query(nint comObject, Guid iid)
    {
        nint result;
        var hr = ((delegate* unmanaged<nint, Guid*, nint*, int>)Slot(comObject, SlotQueryInterface))(comObject, &iid, &result);
        return hr < 0 ? 0 : result;
    }

    private static nint Slot(nint comObject, int slot) => (*(nint**)comObject)[slot];

    private static void Release(nint comObject)
    {
        if (comObject != 0)
        {
            ((delegate* unmanaged<nint, uint>)Slot(comObject, SlotRelease))(comObject);
        }
    }

    private static string Failure(string what, int hr) =>
        string.Create(CultureInfo.InvariantCulture, $"couldn't {what} (Windows error 0x{hr:X8})");

    /// <summary>Windows.Foundation.Size.</summary>
    [StructLayout(LayoutKind.Sequential)]
    private struct Size
    {
        public float Width;
        public float Height;
    }

    /// <summary>POINT.</summary>
    [StructLayout(LayoutKind.Sequential)]
    private struct Point
    {
        public int X;
        public int Y;
    }

    /// <summary>PDF_RENDER_PARAMS: the source rectangle (empty: the whole page), the size, the background, and high contrast.</summary>
    [StructLayout(LayoutKind.Sequential)]
    private struct RenderParams
    {
        public float SourceLeft;
        public float SourceTop;
        public float SourceRight;
        public float SourceBottom;
        public uint DestinationWidth;
        public uint DestinationHeight;
        public float BackgroundR;
        public float BackgroundG;
        public float BackgroundB;
        public float BackgroundA;
        public byte IgnoreHighContrast;
    }

    /// <summary>D3D11_TEXTURE2D_DESC.</summary>
    [StructLayout(LayoutKind.Sequential)]
    private struct Texture2DDescription
    {
        public uint Width;
        public uint Height;
        public uint MipLevels;
        public uint ArraySize;
        public int Format;
        public uint SampleCount;
        public uint SampleQuality;
        public int Usage;
        public uint BindFlags;
        public uint CpuAccessFlags;
        public uint MiscFlags;
    }

    /// <summary>D3D11_MAPPED_SUBRESOURCE.</summary>
    [StructLayout(LayoutKind.Sequential)]
    private struct MappedSubresource
    {
        public void* Data;
        public uint RowPitch;
        public uint DepthPitch;
    }

    /// <summary>S_OK or S_FALSE (already initialised), each to be matched by <see cref="RoUninitialize"/>; RPC_E_CHANGED_MODE (an STA thread, still usable) isn't.</summary>
    [LibraryImport("combase.dll")]
    private static partial int RoInitialize(uint initType);

    [LibraryImport("combase.dll")]
    private static partial void RoUninitialize();

    [LibraryImport("combase.dll")]
    private static partial int RoGetActivationFactory(nint activatableClassId, Guid* iid, nint* factory);

    [LibraryImport("combase.dll")]
    private static partial int WindowsCreateString(char* sourceString, uint length, nint* result);

    [LibraryImport("combase.dll")]
    private static partial int WindowsDeleteString(nint value);

    [LibraryImport("shcore.dll")]
    private static partial int CreateRandomAccessStreamOnFile(char* filePath, uint accessMode, Guid* iid, nint* stream);

    [LibraryImport("d3d11.dll")]
    private static partial int D3D11CreateDevice(nint adapter, int driverType, nint software, uint flags, int* featureLevels, uint featureLevelCount,
        uint sdkVersion, nint* device, int* featureLevel, nint* context);

    [LibraryImport("Windows.Data.Pdf.dll")]
    private static partial int PdfCreateRenderer(nint dxgiDevice, nint* renderer);
}
