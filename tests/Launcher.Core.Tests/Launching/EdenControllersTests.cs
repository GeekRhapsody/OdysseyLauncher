using System.Text;
using Launcher.Core.Launching.Controllers;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Launching;

public sealed class EdenControllersTests : IDisposable
{
    // GUIDs as Godot reported them on the owner's Steam Deck (2026-10-10): its own controls through SDL's HIDAPI driver,
    // and the Xbox 360 pad Steam Input makes of them. The name's CRC (bytes 2-3) is set.
    private const string DeckGuid = "0300f617de2800000512000000026800";
    private const string Xbox360Guid = "0300fa675e0400008e02000014017801";

    // An Xbox Series pad over Bluetooth, which Eden mapped itself in the owner's qt-config.ini (CRC made up here).
    private const string XboxSeriesGuid = "03001a2b5e040000130b000009057801";
    private const string XboxSeriesEden = "030000005e040000130b000009057801";

    private const string DualSenseGuid = "0500c5824c050000e60c000000016800";
    private const string DirectInputGuid = "03000000790000000600000000000000";

    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private static Gamepad Pad(int device, string guid, string name = "Pad") => new(device, name, guid);

    [Fact]
    public void A_GUID_is_read_as_SDL_does_and_named_as_Eden_names_it()
    {
        var deck = SdlGuid.TryParse(DeckGuid)!;

        Assert.True(deck.HasIds);
        Assert.Equal(0x28de, deck.Vendor);
        Assert.Equal(0x1205, deck.Product);
        Assert.Equal(0x0200, deck.Version);
        Assert.Equal(SdlGuid.Hidapi, deck.Driver);
        Assert.Equal("03000000de2800000512000000026800", deck.ToEdenString());
        Assert.Equal(XboxSeriesEden, SdlGuid.TryParse(XboxSeriesGuid.ToUpperInvariant())!.ToEdenString());
        Assert.Null(SdlGuid.TryParse("not a guid"));
        Assert.Null(SdlGuid.TryParse("0300f617de28000005120000000268"));
    }

    [Fact]
    public void The_mapping_follows_SDL_for_XInput_and_HIDAPI_pads_and_leaves_others_out()
    {
        var xinput = SdlMapping.For(SdlGuid.TryParse(Xbox360Guid)!, out _)!;
        Assert.Equal(new SdlInput(SdlInputKind.Button, 1), Get(xinput, "b"));
        Assert.Equal(new SdlInput(SdlInputKind.Axis, 2), Get(xinput, "lefttrigger"));
        Assert.Equal(new SdlInput(SdlInputKind.Hat, 0, 1), Get(xinput, "dpup"));
        Assert.Equal(new SdlInput(SdlInputKind.Axis, 3), Get(xinput, "rightx"));
        Assert.False(xinput.TryGet("misc1", out _));

        var deck = SdlMapping.For(SdlGuid.TryParse(DeckGuid)!, out _)!;
        Assert.Equal(new SdlInput(SdlInputKind.Button, 0), Get(deck, "a"));
        Assert.Equal(new SdlInput(SdlInputKind.Button, 6), Get(deck, "start"));
        Assert.Equal(new SdlInput(SdlInputKind.Axis, 4), Get(deck, "lefttrigger"));

        // The DualSense's microphone button is SDL's misc1; 8BitDo's face buttons are swapped.
        Assert.Equal(new SdlInput(SdlInputKind.Button, 12), Get(SdlMapping.For(SdlGuid.TryParse(DualSenseGuid)!, out _)!, "misc1"));
        var eightBitDo = SdlMapping.For(SdlGuid.TryParse("03000000c82d00000960000000006800")!, out _)!;
        Assert.Equal(new SdlInput(SdlInputKind.Button, 1), Get(eightBitDo, "a"));

        Assert.Null(SdlMapping.For(SdlGuid.TryParse(DirectInputGuid)!, out var directInput));
        Assert.Contains("DirectInput", directInput, StringComparison.Ordinal);
        Assert.Null(SdlMapping.For(SdlGuid.TryParse("030000007e0500000620000000016801")!, out var joyCon));
        Assert.Contains("Joy-Con", joyCon, StringComparison.Ordinal);
    }

    [Fact]
    public void Mapping_strings_keep_the_raw_input_and_drop_ranges_and_hints()
    {
        var mapping = SdlMapping.Parse("a:b0,lefty:a1~,righttrigger:+a5,dpup:h0.1,hint:!SDL_X:=1,broken,x:q3", "test");

        Assert.Equal(new SdlInput(SdlInputKind.Axis, 1), Get(mapping, "lefty"));
        Assert.Equal(new SdlInput(SdlInputKind.Axis, 5), Get(mapping, "righttrigger"));
        Assert.Equal(new SdlInput(SdlInputKind.Hat, 0, 1), Get(mapping, "dpup"));
        Assert.False(mapping.TryGet("hint", out _));
        Assert.False(mapping.TryGet("x", out _));
    }

    [Fact]
    public void The_launching_pad_is_player_one_and_ports_count_pads_of_one_GUID_in_device_order()
    {
        // Two identical XInput pads (devices 0 and 3), launched with the second.
        var pads = new[] { Pad(3, Xbox360Guid, "Second"), Pad(0, Xbox360Guid, "First"), Pad(1, DualSenseGuid, "DualSense") };

        var assignment = EdenControllers.Assign(pads, proControllerDriver: false);

        Assert.Empty(assignment.Skipped);
        Assert.Equal(["Second", "First", "DualSense"], assignment.Players.Select(p => p.Pad.Name));
        Assert.Equal([0, 1, 2], assignment.Players.Select(p => p.Player));
        Assert.Equal([1, 0, 0], assignment.Players.Select(p => p.Port));
    }

    [Fact]
    public void A_Steam_Deck_drops_the_Xbox_360_pad_made_of_its_controls()
    {
        var pads = new[] { Pad(1, Xbox360Guid, "XInput Controller"), Pad(0, DeckGuid, "Steam Deck") };

        var assignment = EdenControllers.Assign(pads, proControllerDriver: false);

        Assert.Equal("Steam Deck", Assert.Single(assignment.Players).Pad.Name);
        Assert.Equal("XInput Controller", Assert.Single(assignment.Skipped).Pad.Name);

        // Without the Deck's controls, an Xbox 360 pad is a player like any other.
        Assert.Single(EdenControllers.Assign([pads[0]], proControllerDriver: false).Players);
    }

    [Fact]
    public void Pads_Eden_reads_itself_or_without_a_mapping_are_left_out_and_there_are_at_most_eight_players()
    {
        var pro = Pad(0, "030000007e0500000920000000006800", "Pro Controller");
        Assert.Single(EdenControllers.Assign([pro], proControllerDriver: false).Players);
        Assert.Empty(EdenControllers.Assign([pro], proControllerDriver: true).Players);

        var many = Enumerable.Range(0, 10).Select(i => Pad(i, Xbox360Guid)).Append(Pad(10, DirectInputGuid, "Generic")).ToList();
        var assignment = EdenControllers.Assign(many, proControllerDriver: false);
        Assert.Equal(EdenControllers.MaxPlayers, assignment.Players.Count);
        Assert.Equal(3, assignment.Skipped.Count);
        Assert.Contains(assignment.Skipped, s => s.Pad.Name == "Generic" && s.Reason.Contains("DirectInput", StringComparison.Ordinal));
    }

    [Fact]
    public void The_bindings_match_what_Eden_wrote_for_the_same_pad()
    {
        // The owner's qt-config.ini after mapping an Xbox Series pad in Eden's own settings.
        var file = _dir.File("eden/config/qt-config.ini", """
            [Controls]
            player_0_button_a\default=false
            player_0_button_a="engine:sdl,guid:030000005e040000130b000009057801,port:0,button:1"
            player_0_button_zl\default=false
            player_0_button_zl="engine:sdl,guid:030000005e040000130b000009057801,threshold:0.5,port:0,axis:2,invert:+"
            player_0_button_dup\default=false
            player_0_button_dup="engine:sdl,guid:030000005e040000130b000009057801,hat:0,port:0,direction:up"
            player_0_lstick\default=false
            player_0_lstick="axis_x:0,engine:sdl,guid:030000005e040000130b000009057801,offset_x:-0.001190,invert_y:+,invert_x:+,port:0,axis_y:1,offset_y:0.028474"
            """);
        var eden = ReadControls(file);

        EdenControllers.Configure(file, [Pad(0, XboxSeriesGuid, "Xbox Series")]);

        var ours = ReadControls(file);
        foreach (var key in (string[])["player_0_button_a", "player_0_button_zl", "player_0_button_dup"])
        {
            Assert.Equal(Params(eden[key]), Params(ours[key]));
        }

        var stick = Params(ours["player_0_lstick"]);
        foreach (var (name, value) in Params(eden["player_0_lstick"]).Where(p => !p.Key.StartsWith("offset", StringComparison.Ordinal)))
        {
            Assert.Equal(value, stick[name]);
        }
    }

    [Fact]
    public void Configuring_sets_every_player_key_keeps_the_rest_and_backs_the_file_up_once()
    {
        var original = "[UI]\r\ntheme=dark\r\n\r\n[Controls]\r\nPLAYER_0_BUTTON_A=\"engine:keyboard,code:67,toggle:0\"\r\n" +
            "player_0_button_a=\"stale duplicate\"\r\nplayer_3_connected=true\r\nenable_raw_input\\default=false\r\nenable_raw_input=true\r\n" +
            "\r\n[System]\r\nlanguage_index=1\r\n";
        var file = _dir.Combine("user", "config", "qt-config.ini");
        Directory.CreateDirectory(Path.GetDirectoryName(file)!);
        File.WriteAllBytes(file, [0xEF, 0xBB, 0xBF, .. Encoding.UTF8.GetBytes(original)]);

        var setup = EdenControllers.Configure(file, [Pad(0, DeckGuid, "Steam Deck"), Pad(1, Xbox360Guid, "XInput Controller")]);

        Assert.True(setup.Written);
        Assert.Contains("player 1 Steam Deck (28de:1205, SDL's HIDAPI mapping)", setup.Describe(), StringComparison.Ordinal);
        var bytes = File.ReadAllBytes(file);
        Assert.Equal([0xEF, 0xBB, 0xBF], bytes[..3]);
        var text = Encoding.UTF8.GetString(bytes, 3, bytes.Length - 3);
        Assert.DoesNotContain("\n", text.Replace("\r\n", string.Empty, StringComparison.Ordinal), StringComparison.Ordinal);
        Assert.StartsWith("[UI]\r\ntheme=dark\r\n\r\n[Controls]\r\nplayer_0_button_a=\"engine:sdl,port:0,guid:03000000de2800000512000000026800,button:1\"\r\n", text, StringComparison.Ordinal);
        Assert.EndsWith("\r\n\r\n[System]\r\nlanguage_index=1\r\n", text, StringComparison.Ordinal);
        Assert.DoesNotContain("stale duplicate", text, StringComparison.Ordinal);

        var controls = ReadControls(file);
        Assert.Equal("true", controls["player_0_connected"]);
        Assert.Equal("false", controls["player_0_connected\\default"]);
        Assert.Equal("0", controls["player_0_type"]);
        Assert.Equal("engine:sdl,port:0,guid:03000000de2800000512000000026800,axis_x:0,axis_y:1,offset_x:0.000000,offset_y:0.000000,invert_x:+,invert_y:+", controls["player_0_lstick"]);
        Assert.Equal("engine:sdl,port:0,guid:03000000de2800000512000000026800,motion:0", controls["player_0_motionleft"]);
        Assert.Equal("[empty]", controls["player_0_button_screenshot"]);

        // The Xbox 360 pad made of the Deck's controls is left out, so player 2 and on are disconnected.
        Assert.Equal("false", controls["player_1_connected"]);
        Assert.Equal("false", controls["player_3_connected"]);
        Assert.Equal("false", controls["player_7_connected"]);
        Assert.False(controls.ContainsKey("player_8_connected"));
        Assert.Equal("false", controls["enable_raw_input"]);

        // The backup is the file as it was before the launcher first changed it.
        var backup = file + EdenControllers.BackupSuffix;
        Assert.Equal(original, Encoding.UTF8.GetString(File.ReadAllBytes(backup)[3..]));
        EdenControllers.Configure(file, [Pad(0, Xbox360Guid, "Xbox")]);
        Assert.Equal(original, Encoding.UTF8.GetString(File.ReadAllBytes(backup)[3..]));
        Assert.Equal("engine:sdl,port:0,guid:030000005e0400008e02000014017801,hat:0,direction:up", ReadControls(file)["player_0_button_dup"]);
        Assert.False(File.Exists(file + ".odyssey-tmp"));
    }

    [Fact]
    public void A_missing_file_is_created_and_no_usable_pad_leaves_the_file_alone()
    {
        var file = _dir.Combine("appdata", "eden", "config", "qt-config.ini");

        var none = EdenControllers.Configure(file, [Pad(0, DirectInputGuid, "Generic")]);
        Assert.False(none.Written);
        Assert.False(File.Exists(file));
        Assert.Contains("no connected controller can be set up", none.Describe(), StringComparison.Ordinal);

        EdenControllers.Configure(file, [Pad(0, DualSenseGuid, "DualSense")]);
        Assert.Equal("engine:sdl,port:0,guid:050000004c050000e60c000000016800,button:12", ReadControls(file)["player_0_button_screenshot"]);
        Assert.False(File.Exists(file + EdenControllers.BackupSuffix));
    }

    [Fact]
    public void Edens_config_is_beside_it_when_it_has_a_user_folder_else_in_application_data()
    {
        var exe = _dir.File("Eden/eden.exe");
        var appData = _dir.Combine("Roaming");

        var global = EdenControllers.ConfigFile(exe, _dir.Combine("Eden"), appData);
        Directory.CreateDirectory(_dir.Combine("Eden", "user"));
        var portable = EdenControllers.ConfigFile(exe, _dir.Combine("Eden"), appData);

        Assert.Equal(OperatingSystem.IsWindows() ? Path.Combine(appData, "eden", "config", "qt-config.ini") : Path.Combine(appData, "eden", "qt-config.ini"), global);
        Assert.Equal(_dir.Combine("Eden", "user", "config", "qt-config.ini"), portable);
    }

    private static SdlInput Get(SdlMapping mapping, string element)
    {
        Assert.True(mapping.TryGet(element, out var input), element);
        return input;
    }

    /// <summary>The [Controls] keys, read as Eden reads them (SimpleIni, quotes removed).</summary>
    private static Dictionary<string, string> ReadControls(string file)
    {
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var inControls = false;
        foreach (var raw in File.ReadAllLines(file))
        {
            var line = raw.Trim();
            if (line.StartsWith('['))
            {
                inControls = line == "[Controls]";
            }
            else if (inControls && line.IndexOf('=', StringComparison.Ordinal) is > 0 and var equals)
            {
                values.TryAdd(line[..equals], line[(equals + 1)..].Replace("\"", string.Empty, StringComparison.Ordinal));
            }
        }

        return values;
    }

    /// <summary>A ParamPackage's keys and values, in any order.</summary>
    private static Dictionary<string, string> Params(string value) =>
        value.Split(',').Select(p => p.Split(':', 2)).ToDictionary(p => p[0], p => p[1], StringComparer.Ordinal);
}
