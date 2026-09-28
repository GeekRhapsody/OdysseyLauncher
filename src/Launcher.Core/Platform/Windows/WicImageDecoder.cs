using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using Launcher.Core.Media;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Decodes PNG, JPEG and WebP with the Windows Imaging Component, which ships with Windows (WebP since Windows 10
/// 1809), and scales with its high-quality cubic filter. COM is called through raw vtable slots, so there's no
/// interop package and nothing to register. Each thread keeps its own factory.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed unsafe partial class WicImageDecoder : IImageDecoder
{
    // Vtable slots (IUnknown takes 0-2).
    private const int SlotRelease = 2;
    private const int SlotFactoryCreateDecoderFromFilename = 3;
    private const int SlotFactoryCreateFormatConverter = 10;
    private const int SlotFactoryCreateBitmapScaler = 11;
    private const int SlotDecoderGetFrame = 13;
    private const int SlotSourceGetSize = 3;
    private const int SlotSourceCopyPixels = 7;
    private const int SlotConverterInitialize = 8;
    private const int SlotScalerInitialize = 8;

    private const uint GenericRead = 0x8000_0000;
    private const int DecodeMetadataCacheOnDemand = 0;
    private const int InterpolationFant = 3;
    private const int InterpolationHighQualityCubic = 4;
    private const int ComponentNotFound = unchecked((int)0x8898_2F50);

    private static readonly Guid ClsidImagingFactory = new("cacaf262-9370-4615-a13b-9f5539da4c0a");
    private static readonly Guid IidImagingFactory = new("ec5ec8a9-c395-4314-9c77-54d7a935ff70");
    private static readonly Guid PixelFormat32bppRgba = new("f5c7ad2d-6a8d-43dd-a7a8-a29935261ae9");

    [ThreadStatic]
    private static nint t_factory;

    public bool TryDecodeScaled(string path, int width, int height, Span<byte> rgba, out string? error)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(width);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(height);
        var bytes = (uint)(width * height * 4);
        if (rgba.Length < bytes)
        {
            throw new ArgumentException("the buffer is too small", nameof(rgba));
        }

        var factory = Factory(out error);
        if (factory == 0)
        {
            return false;
        }

        nint decoder = 0, frame = 0, converter = 0, scaler = 0;
        try
        {
            int hr;
            fixed (char* name = path)
            {
                hr = ((delegate* unmanaged<nint, char*, Guid*, uint, int, nint*, int>)Slot(factory, SlotFactoryCreateDecoderFromFilename))(
                    factory, name, null, GenericRead, DecodeMetadataCacheOnDemand, &decoder);
            }

            if (hr < 0)
            {
                error = hr == ComponentNotFound ? "no Windows codec can read this image" : Failure("open", hr);
                return false;
            }

            hr = ((delegate* unmanaged<nint, uint, nint*, int>)Slot(decoder, SlotDecoderGetFrame))(decoder, 0, &frame);
            if (hr < 0)
            {
                error = Failure("read the first frame", hr);
                return false;
            }

            uint sourceWidth, sourceHeight;
            hr = ((delegate* unmanaged<nint, uint*, uint*, int>)Slot(frame, SlotSourceGetSize))(frame, &sourceWidth, &sourceHeight);
            if (hr < 0 || sourceWidth == 0 || sourceHeight == 0)
            {
                error = Failure("read the size", hr);
                return false;
            }

            hr = ((delegate* unmanaged<nint, nint*, int>)Slot(factory, SlotFactoryCreateFormatConverter))(factory, &converter);
            if (hr >= 0)
            {
                var format = PixelFormat32bppRgba;
                hr = ((delegate* unmanaged<nint, nint, Guid*, int, nint, double, int, int>)Slot(converter, SlotConverterInitialize))(
                    converter, frame, &format, 0, 0, 0.0, 0);
            }

            if (hr < 0)
            {
                error = Failure("convert to RGBA", hr);
                return false;
            }

            hr = ((delegate* unmanaged<nint, nint*, int>)Slot(factory, SlotFactoryCreateBitmapScaler))(factory, &scaler);
            if (hr >= 0)
            {
                var initialise = (delegate* unmanaged<nint, nint, uint, uint, int, int>)Slot(scaler, SlotScalerInitialize);
                hr = initialise(scaler, converter, (uint)width, (uint)height, InterpolationHighQualityCubic);
                if (hr < 0)
                {
                    // High-quality cubic needs Windows 10; Fant is the best filter before it.
                    hr = initialise(scaler, converter, (uint)width, (uint)height, InterpolationFant);
                }
            }

            if (hr < 0)
            {
                error = Failure("scale", hr);
                return false;
            }

            fixed (byte* pixels = rgba)
            {
                hr = ((delegate* unmanaged<nint, void*, uint, uint, byte*, int>)Slot(scaler, SlotSourceCopyPixels))(
                    scaler, null, (uint)(width * 4), bytes, pixels);
            }

            if (hr < 0)
            {
                error = Failure("decode", hr);
                return false;
            }

            error = null;
            return true;
        }
        finally
        {
            Release(scaler);
            Release(converter);
            Release(frame);
            Release(decoder);
        }
    }

    private static nint Factory(out string? error)
    {
        error = null;
        if (t_factory != 0)
        {
            return t_factory;
        }

        // S_FALSE (already initialised) and RPC_E_CHANGED_MODE (an STA thread) both leave COM usable.
        _ = CoInitializeEx(0, 0);
        var clsid = ClsidImagingFactory;
        var iid = IidImagingFactory;
        nint factory;
        var hr = CoCreateInstance(&clsid, 0, 1, &iid, &factory);
        if (hr < 0)
        {
            error = Failure("create the WIC factory", hr);
            return 0;
        }

        t_factory = factory;
        return factory;
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
        string.Create(CultureInfo.InvariantCulture, $"couldn't {what} (WIC error 0x{hr:X8})");

    [LibraryImport("ole32.dll")]
    private static partial int CoInitializeEx(nint reserved, uint coInit);

    [LibraryImport("ole32.dll")]
    private static partial int CoCreateInstance(Guid* clsid, nint outer, uint context, Guid* iid, nint* result);
}
