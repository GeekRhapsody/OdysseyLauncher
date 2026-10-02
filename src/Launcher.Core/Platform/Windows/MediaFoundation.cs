using System.Globalization;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Media Foundation through raw COM vtable slots, as <see cref="WicImageDecoder"/> calls WIC: no interop package.
/// Only what the video decoder (and its tests' MP4 writer) uses. Every call needs <see cref="Startup"/> on the thread
/// first, and a matching <see cref="Shutdown"/> when done.
/// </summary>
[SupportedOSPlatform("windows")]
internal static unsafe partial class MediaFoundation
{
    // IUnknown.
    public const int SlotQueryInterface = 0;
    public const int SlotRelease = 2;

    // IMFAttributes (and IMFMediaType, IMFSample, which extend it).
    public const int SlotGetUInt32 = 7;
    public const int SlotGetUInt64 = 8;
    public const int SlotGetBlob = 15;
    public const int SlotSetUInt32 = 21;
    public const int SlotSetUInt64 = 22;
    public const int SlotSetGuid = 24;

    // IMFSample.
    public const int SlotSampleSetTime = 36;
    public const int SlotSampleSetDuration = 38;
    public const int SlotSampleToContiguousBuffer = 41;
    public const int SlotSampleAddBuffer = 42;

    // IMFMediaBuffer.
    public const int SlotBufferLock = 3;
    public const int SlotBufferUnlock = 4;
    public const int SlotBufferSetCurrentLength = 6;

    // IMF2DBuffer.
    public const int SlotLock2D = 3;
    public const int SlotUnlock2D = 4;

    // IMFSourceReader.
    public const int SlotReaderSetStreamSelection = 4;
    public const int SlotReaderGetCurrentMediaType = 6;
    public const int SlotReaderSetCurrentMediaType = 7;
    public const int SlotReaderSetCurrentPosition = 8;
    public const int SlotReaderReadSample = 9;
    public const int SlotReaderGetPresentationAttribute = 12;

    // IMFSinkWriter (the tests' MP4 writer).
    public const int SlotWriterAddStream = 3;
    public const int SlotWriterSetInputMediaType = 4;
    public const int SlotWriterBeginWriting = 5;
    public const int SlotWriterWriteSample = 6;
    public const int SlotWriterFinalize = 11;

    public const uint FirstVideoStream = 0xFFFF_FFFC;
    public const uint FirstAudioStream = 0xFFFF_FFFD;
    public const uint AllStreams = 0xFFFF_FFFE;
    public const uint MediaSource = 0xFFFF_FFFF;

    public const uint ReaderFlagError = 0x1;
    public const uint ReaderFlagEndOfStream = 0x2;
    public const uint ReaderFlagCurrentTypeChanged = 0x20;

    private const uint Version = 0x0002_0070;
    private const int InvalidStreamNumber = unchecked((int)0xC00D_36B3);
    private const int UnsupportedByteStream = unchecked((int)0xC00D_36C4);
    private const int CodecNotFound = unchecked((int)0xC00D_5212);
    private const int FileNotFound = unchecked((int)0x8007_0002);

    public static readonly Guid ReaderEnableAdvancedVideoProcessing = new("0f81da2c-b537-4672-a8b2-a681b17307a3");
    public static readonly Guid MajorType = new("48eba18e-f8c9-4687-bf11-0a74c9f96a8f");
    public static readonly Guid Subtype = new("f7e34c9a-42e8-4714-b74b-cb29d72c35e5");
    public static readonly Guid FrameSize = new("1652c33d-d6b2-4012-b834-72030849a37d");
    public static readonly Guid FrameRate = new("c459a2e8-3d2c-4e44-b132-fee5156c7bb0");
    public static readonly Guid DefaultStride = new("644b4e48-1e02-4516-b0eb-c01ca9d49ac6");
    public static readonly Guid PixelAspectRatio = new("c6376a1e-8d0a-4027-be45-6d9a0ad39bb6");
    public static readonly Guid MinimumDisplayAperture = new("d7388766-18fe-48c6-a177-ee894867c8c4");
    public static readonly Guid InterlaceMode = new("e2724bb8-e676-4806-b4b2-a8d6efb44ccd");
    public static readonly Guid AverageBitrate = new("20332624-fb0d-4d9e-bd0d-cbf6786c102e");
    public static readonly Guid AudioChannels = new("37e48bf5-645e-4c5b-89de-ada9e29b696a");
    public static readonly Guid AudioSampleRate = new("5faeeae7-0290-4c31-9e8a-c534f68d9dba");
    public static readonly Guid AudioBitsPerSample = new("f2deb57f-40fa-4764-aa33-ed4f2d1ff669");
    public static readonly Guid AudioBlockAlignment = new("322de230-9eeb-43bd-ab7a-ff412251541d");
    public static readonly Guid AudioAverageBytesPerSecond = new("1aab75c8-cfef-451c-ab95-ac034b8e1731");
    public static readonly Guid PresentationDuration = new("6c990d33-bb8e-477a-8598-0d5d96fcd88a");
    public static readonly Guid Video = new("73646976-0000-0010-8000-00aa00389b71");
    public static readonly Guid Audio = new("73647561-0000-0010-8000-00aa00389b71");
    public static readonly Guid VideoRgb32 = new("00000016-0000-0010-8000-00aa00389b71");
    public static readonly Guid VideoH264 = new("34363248-0000-0010-8000-00aa00389b71");
    public static readonly Guid AudioFloat = new("00000003-0000-0010-8000-00aa00389b71");
    public static readonly Guid AudioPcm = new("00000001-0000-0010-8000-00aa00389b71");
    public static readonly Guid AudioAac = new("00001610-0000-0010-8000-00aa00389b71");
    public static readonly Guid Buffer2D = new("7dc9d5f9-9ed9-44ec-9bbf-0600bb589fbb");

    /// <summary>COM (multithreaded, unless the thread already chose) and Media Foundation for this thread; null or why not.</summary>
    public static string? Startup()
    {
        try
        {
            // S_FALSE (already initialised) and RPC_E_CHANGED_MODE (an STA thread) both leave COM usable.
            _ = CoInitializeEx(0, 0);
            var hr = MFStartup(Version, 0);
            return hr < 0 ? Failure("start Media Foundation", hr) : null;
        }
        catch (Exception e) when (e is DllNotFoundException or EntryPointNotFoundException)
        {
            // Windows N editions ship without it.
            return "Windows Media Foundation isn't installed (an N edition of Windows needs the Media Feature Pack)";
        }
    }

    public static void Shutdown() => _ = MFShutdown();

    /// <summary>A source reader for one stream of the file, its other streams switched off; 0, with the reason, when it can't.</summary>
    public static nint OpenReader(string path, uint stream, bool videoProcessing, out string? error)
    {
        nint attributes = 0, reader = 0;
        try
        {
            var hr = MFCreateAttributes(&attributes, 1);
            if (hr >= 0 && videoProcessing)
            {
                // Colour conversion (the decoder's YUV to RGB) and the picture's aperture, done by Media Foundation.
                hr = SetUInt32(attributes, ReaderEnableAdvancedVideoProcessing, 1);
            }

            if (hr < 0)
            {
                error = Failure("set up the reader", hr);
                return 0;
            }

            fixed (char* url = path)
            {
                hr = MFCreateSourceReaderFromURL(url, attributes, &reader);
            }

            if (hr < 0)
            {
                error = hr switch
                {
                    FileNotFound => "the file doesn't exist",
                    UnsupportedByteStream => "it isn't a video Windows can read",
                    _ => Failure("open the file", hr),
                };
                return 0;
            }

            hr = ((delegate* unmanaged<nint, uint, int, int>)Slot(reader, SlotReaderSetStreamSelection))(reader, AllStreams, 0);
            if (hr >= 0)
            {
                hr = ((delegate* unmanaged<nint, uint, int, int>)Slot(reader, SlotReaderSetStreamSelection))(reader, stream, 1);
            }

            if (hr < 0)
            {
                error = hr == InvalidStreamNumber ? stream == FirstAudioStream ? "it has no sound" : "it has no picture" : Failure("choose the stream", hr);
                return 0;
            }

            error = null;
            var opened = reader;
            reader = 0;
            return opened;
        }
        finally
        {
            Release(reader);
            Release(attributes);
        }
    }

    /// <summary>Asks the reader to decode <paramref name="stream"/> to <paramref name="subtype"/>; null or why not.</summary>
    public static string? SetOutputType(nint reader, uint stream, Guid major, Guid subtype)
    {
        nint type = 0;
        try
        {
            var hr = MFCreateMediaType(&type);
            if (hr >= 0)
            {
                hr = SetGuid(type, MajorType, major);
            }

            if (hr >= 0)
            {
                hr = SetGuid(type, Subtype, subtype);
            }

            if (hr >= 0)
            {
                hr = ((delegate* unmanaged<nint, uint, uint*, nint, int>)Slot(reader, SlotReaderSetCurrentMediaType))(reader, stream, null, type);
            }

            return hr switch
            {
                >= 0 => null,
                CodecNotFound => "Windows has no decoder for its format",
                _ => Failure("decode it", hr),
            };
        }
        finally
        {
            Release(type);
        }
    }

    /// <summary>The stream's current output type (release it); 0 if it can't be read.</summary>
    public static nint CurrentType(nint reader, uint stream)
    {
        nint type;
        var hr = ((delegate* unmanaged<nint, uint, nint*, int>)Slot(reader, SlotReaderGetCurrentMediaType))(reader, stream, &type);
        return hr < 0 ? 0 : type;
    }

    /// <summary>The next sample of the stream (release it; 0 with no error at a gap or the end), its flags and time.</summary>
    public static int ReadSample(nint reader, uint stream, out uint flags, out long time, out nint sample)
    {
        uint actual, readerFlags;
        long timestamp;
        nint result;
        var hr = ((delegate* unmanaged<nint, uint, uint, uint*, uint*, long*, nint*, int>)Slot(reader, SlotReaderReadSample))(
            reader, stream, 0, &actual, &readerFlags, &timestamp, &result);
        flags = readerFlags;
        time = timestamp;
        sample = hr < 0 ? 0 : result;
        return hr;
    }

    /// <summary>Moves the reader to <paramref name="ticks"/> (100 ns units).</summary>
    public static int SetPosition(nint reader, long ticks)
    {
        var variant = new PropVariant { Type = 20, Value = ticks };
        var timeFormat = Guid.Empty;
        return ((delegate* unmanaged<nint, Guid*, PropVariant*, int>)Slot(reader, SlotReaderSetCurrentPosition))(reader, &timeFormat, &variant);
    }

    /// <summary>The file's length in 100 ns units, or 0.</summary>
    public static long Duration(nint reader)
    {
        var variant = default(PropVariant);
        var key = PresentationDuration;
        var hr = ((delegate* unmanaged<nint, uint, Guid*, PropVariant*, int>)Slot(reader, SlotReaderGetPresentationAttribute))(reader, MediaSource, &key, &variant);

        // VT_UI8 needs no clearing.
        return hr >= 0 && variant.Type == 21 ? variant.Value : 0;
    }

    public static int GetUInt32(nint attributes, Guid key, out uint value)
    {
        uint result;
        var hr = ((delegate* unmanaged<nint, Guid*, uint*, int>)Slot(attributes, SlotGetUInt32))(attributes, &key, &result);
        value = result;
        return hr;
    }

    public static int GetUInt64(nint attributes, Guid key, out ulong value)
    {
        ulong result;
        var hr = ((delegate* unmanaged<nint, Guid*, ulong*, int>)Slot(attributes, SlotGetUInt64))(attributes, &key, &result);
        value = result;
        return hr;
    }

    public static int GetBlob(nint attributes, Guid key, Span<byte> blob, out uint size)
    {
        uint length;
        int hr;
        fixed (byte* bytes = blob)
        {
            hr = ((delegate* unmanaged<nint, Guid*, byte*, uint, uint*, int>)Slot(attributes, SlotGetBlob))(attributes, &key, bytes, (uint)blob.Length, &length);
        }

        size = length;
        return hr;
    }

    public static int SetUInt32(nint attributes, Guid key, uint value) =>
        ((delegate* unmanaged<nint, Guid*, uint, int>)Slot(attributes, SlotSetUInt32))(attributes, &key, value);

    public static int SetUInt64(nint attributes, Guid key, ulong value) =>
        ((delegate* unmanaged<nint, Guid*, ulong, int>)Slot(attributes, SlotSetUInt64))(attributes, &key, value);

    public static int SetGuid(nint attributes, Guid key, Guid value) =>
        ((delegate* unmanaged<nint, Guid*, Guid*, int>)Slot(attributes, SlotSetGuid))(attributes, &key, &value);

    /// <summary>The object's <paramref name="iid"/> interface (release it), or 0.</summary>
    public static nint Query(nint comObject, Guid iid)
    {
        nint result;
        var hr = ((delegate* unmanaged<nint, Guid*, nint*, int>)Slot(comObject, SlotQueryInterface))(comObject, &iid, &result);
        return hr < 0 ? 0 : result;
    }

    public static nint Slot(nint comObject, int slot) => (*(nint**)comObject)[slot];

    public static void Release(nint comObject)
    {
        if (comObject != 0)
        {
            ((delegate* unmanaged<nint, uint>)Slot(comObject, SlotRelease))(comObject);
        }
    }

    public static string Failure(string what, int hr) =>
        string.Create(CultureInfo.InvariantCulture, $"couldn't {what} (Media Foundation error 0x{hr:X8})");

    /// <summary>A PROPVARIANT holding a 64-bit integer (the only kind used here): the type, padding, then the value.</summary>
    [StructLayout(LayoutKind.Explicit, Size = 24)]
    public struct PropVariant
    {
        [FieldOffset(0)]
        public ushort Type;

        [FieldOffset(8)]
        public long Value;
    }

    [LibraryImport("ole32.dll")]
    private static partial int CoInitializeEx(nint reserved, uint coInit);

    [LibraryImport("mfplat.dll")]
    private static partial int MFStartup(uint version, uint flags);

    [LibraryImport("mfplat.dll")]
    private static partial int MFShutdown();

    [LibraryImport("mfplat.dll")]
    public static partial int MFCreateAttributes(nint* attributes, uint initialSize);

    [LibraryImport("mfplat.dll")]
    public static partial int MFCreateMediaType(nint* type);

    [LibraryImport("mfplat.dll")]
    public static partial int MFCreateSample(nint* sample);

    [LibraryImport("mfplat.dll")]
    public static partial int MFCreateMemoryBuffer(uint length, nint* buffer);

    [LibraryImport("mfreadwrite.dll")]
    private static partial int MFCreateSourceReaderFromURL(char* url, nint attributes, nint* reader);

    [LibraryImport("mfreadwrite.dll")]
    public static partial int MFCreateSinkWriterFromURL(char* url, nint byteStream, nint attributes, nint* writer);
}
