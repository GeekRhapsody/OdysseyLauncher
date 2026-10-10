using System.Globalization;

namespace Launcher.Core.Launching.Controllers;

public enum SdlInputKind
{
    Button,
    Axis,
    Hat,
}

/// <summary>A raw joystick input that a gamepad element is bound to.</summary>
/// <param name="Index">The button, axis or hat number.</param>
/// <param name="HatMask">For a hat: 1 up, 2 right, 4 down, 8 left.</param>
public readonly record struct SdlInput(SdlInputKind Kind, int Index, int HatMask = 0);

/// <summary>
/// Which raw joystick inputs SDL binds to each gamepad element of a device: a mapping string's elements
/// (<c>a</c> is the south face button, <c>b</c> east, <c>x</c> west, <c>y</c> north). Eden binds raw inputs, which it
/// reads off SDL's mapping when the user picks a pad in its settings, so the launcher works the same mapping out from
/// the pad's GUID (<see cref="For"/>).
/// </summary>
public sealed class SdlMapping
{
    // SDL 3.4.8's mappings, from SDL_gamepad_db.h ("xinput") and SDL_gamepad.c (SDL_CreateMappingForHIDAPIGamepad).
    // SDL is zlib-licensed. On Windows the database has no entry for an XInput or HIDAPI GUID, so these are what
    // Eden's SDL uses for them.
    private const string XInputMapping =
        "a:b0,b:b1,back:b6,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b10,leftshoulder:b4,leftstick:b8,lefttrigger:a2,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b9,righttrigger:a5,rightx:a3,righty:a4,start:b7,x:b2,y:b3";

    private const string HidapiStandard =
        "a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,leftstick:b7,lefttrigger:a4,leftx:a0,lefty:a1,rightshoulder:b10,rightstick:b8,righttrigger:a5,rightx:a2,righty:a3,start:b6,x:b2,y:b3";

    private const string HidapiGameCube =
        "a:b0,b:b2,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,leftstick:b7,lefttrigger:a4,leftx:a0,lefty:a1,rightshoulder:b10,rightstick:b8,righttrigger:a5,rightx:a2,righty:a3,start:b6,x:b1,y:b3";

    private const string HidapiGameCubeAdapter =
        "a:b0,b:b2,dpdown:b6,dpleft:b4,dpright:b5,dpup:b7,lefttrigger:a4,leftx:a0,lefty:a1~,rightshoulder:b9,righttrigger:a5,rightx:a2,righty:a3~,start:b8,x:b1,y:b3,misc3:b11,misc4:b10";

    private const string Switch2GameCube =
        "a:b1,b:b3,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b4,leftshoulder:b6,lefttrigger:a4,leftx:a0,lefty:a1,rightshoulder:b7,righttrigger:a5,rightx:a2,righty:a3,start:b5,x:b0,y:b2,misc1:b8,misc2:b9,misc3:b10,misc4:b11";

    private const string Switch2Pro =
        "a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,leftstick:b7,lefttrigger:a4,leftx:a0,lefty:a1,rightshoulder:b10,rightstick:b8,righttrigger:a5,rightx:a2,righty:a3,start:b6,x:b2,y:b3,misc1:b11,misc2:b12,paddle1:b13,paddle2:b14";

    private const string EightBitDo =
        "a:b1,b:b0,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,leftstick:b7,lefttrigger:a4,leftx:a0,lefty:a1,rightshoulder:b10,rightstick:b8,righttrigger:a5,rightx:a2,righty:a3,start:b6,x:b3,y:b2";

    private const ushort Nintendo = 0x057e;
    private const ushort Sony = 0x054c;
    private const ushort EightBitDoVendor = 0x2dc8;
    private const ushort RaspberryPi = 0x2e8a;
    private const ushort Logitech = 0x046d;

    private readonly Dictionary<string, SdlInput> _bindings;

    private SdlMapping(Dictionary<string, SdlInput> bindings, string source)
    {
        _bindings = bindings;
        Source = source;
    }

    /// <summary>Where the mapping comes from, for the log.</summary>
    public string Source { get; }

    /// <summary>The input bound to <paramref name="element"/> (<c>a</c>, <c>leftx</c>, <c>dpup</c>...), if any.</summary>
    public bool TryGet(string element, out SdlInput input) => _bindings.TryGetValue(element, out input);

    /// <summary>
    /// Reads a mapping string's elements (<c>a:b0,dpup:h0.1,lefttrigger:a2,...</c>). An axis's range and inversion
    /// (<c>+a2</c>, <c>a1~</c>) are dropped, as Eden drops them; <c>hint:</c> and unreadable entries are skipped.
    /// </summary>
    public static SdlMapping Parse(string mapping, string source)
    {
        ArgumentNullException.ThrowIfNull(mapping);
        var bindings = new Dictionary<string, SdlInput>(StringComparer.Ordinal);
        foreach (var entry in mapping.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            var colon = entry.IndexOf(':', StringComparison.Ordinal);
            if (colon <= 0 || entry.StartsWith("hint:", StringComparison.Ordinal))
            {
                continue;
            }

            if (ParseInput(entry[(colon + 1)..]) is { } input)
            {
                bindings[entry[..colon]] = input;
            }
        }

        return new SdlMapping(bindings, source);
    }

    /// <summary>
    /// The mapping Eden's SDL (3.4, with its hints) gives the device, worked out as SDL does from the GUID: SDL's
    /// XInput mapping for an XInput pad, or the mapping SDL generates for a HIDAPI pad from its vendor, product and
    /// type. Null for anything else, with the reason in <paramref name="unsupported"/>: a DirectInput pad's mapping is
    /// in SDL's controller database, which the launcher doesn't carry, and Joy-Cons need pairing.
    /// </summary>
    public static SdlMapping? For(SdlGuid guid, out string? unsupported)
    {
        ArgumentNullException.ThrowIfNull(guid);
        unsupported = null;
        if (guid.Driver == SdlGuid.XInput)
        {
            return Parse(XInputMapping, "SDL's XInput mapping");
        }

        if (guid.Driver != SdlGuid.Hidapi)
        {
            unsupported = guid.Driver switch
            {
                0 => "it's a DirectInput device, whose mapping is in SDL's controller database",
                (byte)'r' or (byte)'w' or (byte)'g' => "it's read through RawInput, Windows.Gaming.Input or GameInput, which Eden doesn't use",
                _ => "SDL reads it through a driver the launcher doesn't know",
            };
            return null;
        }

        var vendor = guid.Vendor;
        var product = guid.Product;
        if (vendor == Logitech)
        {
            unsupported = "it's a Logitech wheel, which SDL doesn't treat as a controller";
            return null;
        }

        if (vendor == RaspberryPi && product is 0x10c6 or 0x10df or 0x10dd or 0x10e0 or 0x10e5)
        {
            unsupported = "it's an SInput controller, whose layout depends on the model";
            return null;
        }

        if ((vendor == Nintendo && product == 0x0337) || (vendor == 0x0079 && product is 0x1843 or 0x1844 or 0x1846))
        {
            return Parse(HidapiGameCubeAdapter, "SDL's GameCube adapter mapping");
        }

        if (vendor == Nintendo)
        {
            switch (product)
            {
                case 0x2073:
                    return Parse(Switch2GameCube, "SDL's Switch 2 GameCube controller mapping");
                case 0x2069:
                    return Parse(Switch2Pro, "SDL's Switch 2 Pro Controller mapping");
                case 0x2066 or 0x2067 or 0x2068:
                    unsupported = "it's a Switch 2 Joy-Con: pair Joy-Cons in Eden's own settings";
                    return null;
            }

            switch (guid.DriverData)
            {
                case 1 or 2:
                    unsupported = "it's a Joy-Con: Eden reads Joy-Cons with its own driver, so pair them in its settings";
                    return null;
                case 7:
                    return Parse("a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,leftshoulder:b9,rightshoulder:b10,start:b6", "SDL's Famicom controller mapping");
                case 8:
                    return Parse("a:b0,b:b1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,leftshoulder:b9,rightshoulder:b10", "SDL's Famicom controller mapping");
                case 9 or 10:
                    return Parse("a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,leftshoulder:b9,rightshoulder:b10,start:b6", "SDL's NES controller mapping");
                case 11:
                    return Parse("a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,leftshoulder:b9,lefttrigger:a4,rightshoulder:b10,righttrigger:a5,start:b6,x:b2,y:b3", "SDL's SNES controller mapping");
                case 12:
                    return Parse("a:b0,b:b1,back:b3,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,lefttrigger:a4,leftx:a0,lefty:a1,misc1:b11,misc2:b4,rightshoulder:b10,righttrigger:b7,start:b6,x:a5,y:b2", "SDL's N64 controller mapping");
                case 13:
                    return Parse("a:b0,b:b1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,leftshoulder:b9,rightshoulder:b10,righttrigger:a5,start:b6,x:b2,y:b3,misc1:b11", "SDL's Mega Drive controller mapping");
                case 128:
                    return Parse("a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,start:b6,x:b2,y:b3", "SDL's Wii Remote mapping");
                case 129:
                    return Parse("a:b0,b:b1,back:b4,dpdown:b12,dpleft:b13,dpright:b14,dpup:b11,guide:b5,leftshoulder:b9,lefttrigger:a4,leftx:a0,lefty:a1,start:b6,x:b2,y:b3", "SDL's Wii Remote and Nunchuk mapping");
            }
        }

        if (vendor == EightBitDoVendor && product is 0x6000 or 0x6100 or 0x6001 or 0x6101 or 0x6003 or 0x6006 or 0x6009)
        {
            return Parse(EightBitDo, "SDL's 8BitDo mapping");
        }

        if ((vendor == 0x0926 && product == 0x8888) || (vendor == 0x0e6f && product == 0x0185)
            || (vendor == 0x1a34 && product == 0xf705) || (vendor == 0x20d6 && product == 0xa711))
        {
            return Parse(HidapiGameCube, "SDL's GameCube-style controller mapping");
        }

        // The standard layout, and the extra button Eden uses (misc1, its Screenshot) where SDL adds one.
        var misc1 = (vendor, product) switch
        {
            (Nintendo, 0x2009) or (0, 0) => ",misc1:b11",
            (Sony, 0x0ce6) or (Sony, 0x0df2) => ",misc1:b12",
            (0x18d1, 0x9400) or (0x0955, 0x7210) or (0x0955, 0x7214) => ",misc1:b11",
            _ => string.Empty,
        };
        return Parse(HidapiStandard + misc1, "SDL's HIDAPI mapping");
    }

    private static SdlInput? ParseInput(string text)
    {
        if (text.Length < 2)
        {
            return null;
        }

        if (text[0] is '+' or '-')
        {
            text = text[1..];
        }

        text = text.TrimEnd('~');
        if (text.Length < 2)
        {
            return null;
        }

        switch (text[0])
        {
            case 'b' when Number(text[1..]) is { } button:
                return new SdlInput(SdlInputKind.Button, button);
            case 'a' when Number(text[1..]) is { } axis:
                return new SdlInput(SdlInputKind.Axis, axis);
            case 'h':
                var dot = text.IndexOf('.', StringComparison.Ordinal);
                return dot > 1 && Number(text[1..dot]) is { } hat && Number(text[(dot + 1)..]) is { } mask
                    ? new SdlInput(SdlInputKind.Hat, hat, mask)
                    : null;
            default:
                return null;
        }
    }

    private static int? Number(string text) =>
        int.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out var value) ? value : null;
}
