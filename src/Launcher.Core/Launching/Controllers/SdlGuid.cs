using System.Globalization;

namespace Launcher.Core.Launching.Controllers;

/// <summary>
/// An SDL3 joystick GUID (SDL_joystick.c, <c>SDL_CreateJoystickGUID</c> and <c>SDL_GetJoystickGUIDInfo</c>): 16 bytes,
/// the bus and the name's CRC-16, then the vendor, 0, the product, 0 and the version (each 16 bits, little-endian),
/// then the driver's signature (<c>'x'</c> XInput, <c>'h'</c> HIDAPI, <c>'r'</c> RawInput, <c>'w'</c> Windows.Gaming.Input,
/// 0 DirectInput) and a byte of the driver's own (XInput's device subtype, a Nintendo controller's type). A device
/// without a vendor id has part of its name where the ids would be.
/// </summary>
public sealed class SdlGuid
{
    public const byte XInput = (byte)'x';
    public const byte Hidapi = (byte)'h';

    /// <summary><c>SDL_HARDWARE_BUS_VIRTUAL</c>.</summary>
    private const ushort VirtualBus = 0xFF;

    private readonly byte[] _bytes;

    private SdlGuid(byte[] bytes)
    {
        _bytes = bytes;
        var bus = Word(0);
        HasIds = (bus < ' ' || bus == VirtualBus) && Word(6) == 0 && Word(10) == 0;
        Vendor = HasIds ? Word(4) : (ushort)0;
        Product = HasIds ? Word(8) : (ushort)0;
        Version = HasIds ? Word(12) : (ushort)0;
    }

    /// <summary>True when the GUID carries a vendor and product id (the standard form).</summary>
    public bool HasIds { get; }

    public ushort Vendor { get; }

    public ushort Product { get; }

    public ushort Version { get; }

    /// <summary>Byte 14: which SDL driver opened the device.</summary>
    public byte Driver => _bytes[14];

    /// <summary>Byte 15: the driver's own data.</summary>
    public byte DriverData => _bytes[15];

    /// <summary>Null unless <paramref name="text"/> is 32 hex digits.</summary>
    public static SdlGuid? TryParse(string? text)
    {
        if (text is null || text.Length != 32)
        {
            return null;
        }

        try
        {
            return new SdlGuid(Convert.FromHexString(text));
        }
        catch (FormatException)
        {
            return null;
        }
    }

    /// <summary>
    /// The GUID as Eden names the device (its SDL driver's <c>GetGUID</c>): the name's CRC cleared, in lower-case hex.
    /// </summary>
    public string ToEdenString()
    {
        Span<byte> bytes = stackalloc byte[16];
        _bytes.CopyTo(bytes);
        bytes[2] = 0;
        bytes[3] = 0;
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }

    /// <summary>For the log: <c>045e:028e</c>.</summary>
    public string Ids => string.Create(CultureInfo.InvariantCulture, $"{Vendor:x4}:{Product:x4}");

    private ushort Word(int offset) => (ushort)(_bytes[offset] | (_bytes[offset + 1] << 8));
}
