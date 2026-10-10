using System.Globalization;

namespace Launcher.Core.Launching.Controllers;

/// <summary>One pad given a player.</summary>
/// <param name="Player">0-based, as Eden numbers them (<c>player_0</c> is player 1).</param>
/// <param name="EdenGuid">The GUID Eden names it by (<see cref="SdlGuid.ToEdenString"/>).</param>
/// <param name="Port">Which of the pads with that GUID it is, in the order SDL opens them.</param>
public sealed record EdenPlayer(int Player, Gamepad Pad, SdlGuid Guid, string EdenGuid, int Port, SdlMapping Mapping);

/// <summary>A pad left out, and why (written for the log).</summary>
public sealed record SkippedPad(Gamepad Pad, string Reason);

/// <summary>Which pad plays as whom.</summary>
public sealed record EdenAssignment(IReadOnlyList<EdenPlayer> Players, IReadOnlyList<SkippedPad> Skipped);

/// <summary>
/// Sets Eden's controllers up for the pads connected at launch, as RetroBat does (its emulatorLauncher's
/// <c>Eden.Controllers.cs</c>): Eden doesn't map a pad until it's picked in its own settings, so before each launch the
/// <c>[Controls]</c> section of its <c>qt-config.ini</c> gets one Pro Controller player per pad, bound to the raw
/// inputs Eden itself would choose for it (its SDL driver's <c>GetButtonMappingForDevice</c>, from SDL's mapping:
/// <see cref="SdlMapping"/>). Players beyond the pads are disconnected; everything else in the file is left alone.
/// </summary>
public static class EdenControllers
{
    /// <summary>The <c>controllers</c> value of an emulator profile this sets up.</summary>
    public const string Kind = "eden";

    /// <summary>Eden has 8 players (and a ninth slot for handheld mode, which is left alone).</summary>
    public const int MaxPlayers = 8;

    /// <summary>Beside the config file: the file as it was before the launcher first changed it.</summary>
    public const string BackupSuffix = ".odyssey-backup";

    private const string Controls = "Controls";

    private const ushort Valve = 0x28de;
    private const ushort SteamDeck = 0x1205;

    /// <summary>Eden's button names, each with the SDL gamepad element its SDL driver binds to it (<c>GetDefaultButtonBinding</c>).</summary>
    private static readonly (string Key, string Element)[] Buttons =
    [
        ("button_a", "b"), ("button_b", "a"), ("button_x", "y"), ("button_y", "x"),
        ("button_lstick", "leftstick"), ("button_rstick", "rightstick"),
        ("button_l", "leftshoulder"), ("button_r", "rightshoulder"),
        ("button_zl", "lefttrigger"), ("button_zr", "righttrigger"),
        ("button_plus", "start"), ("button_minus", "back"),
        ("button_dleft", "dpleft"), ("button_dup", "dpup"), ("button_dright", "dpright"), ("button_ddown", "dpdown"),
        ("button_slleft", "leftshoulder"), ("button_srleft", "rightshoulder"),
        ("button_home", "guide"), ("button_screenshot", "misc1"),
        ("button_slright", "leftshoulder"), ("button_srright", "rightshoulder"),
    ];

    /// <summary>
    /// Where Eden keeps <c>qt-config.ini</c> (its <c>common/fs/path_util.cpp</c>): a <c>user</c> folder beside the
    /// executable on Windows (in the working folder elsewhere) makes it portable; otherwise <c>%APPDATA%\eden\config</c>
    /// on Windows and <c>$XDG_CONFIG_HOME/eden</c> elsewhere.
    /// </summary>
    /// <param name="applicationData">The user's roaming application data (<c>Environment.SpecialFolder.ApplicationData</c>).</param>
    public static string ConfigFile(string executable, string workingDirectory, string applicationData)
    {
        ArgumentNullException.ThrowIfNull(executable);
        ArgumentNullException.ThrowIfNull(workingDirectory);
        ArgumentNullException.ThrowIfNull(applicationData);
        var windows = OperatingSystem.IsWindows();
        var portable = Path.Combine(windows ? Path.GetDirectoryName(executable) ?? workingDirectory : workingDirectory, "user");
        if (Directory.Exists(portable))
        {
            return Path.Combine(portable, "config", "qt-config.ini");
        }

        return windows
            ? Path.Combine(applicationData, "eden", "config", "qt-config.ini")
            : Path.Combine(applicationData, "eden", "qt-config.ini");
    }

    /// <summary>
    /// Gives each pad Eden can use a player, in the order given (the front end puts the pad the game was launched with
    /// first). Left out: a pad without a mapping (<see cref="SdlMapping.For"/>), a Pro Controller when Eden reads them
    /// with its own driver, the Xbox 360 pad Steam Input (or a handheld tool) makes of a Steam Deck's controls when the
    /// Deck's own controls are there too (both would get the same presses), and pads beyond the eighth.
    /// </summary>
    /// <param name="proControllerDriver">Eden's <c>enable_procon_driver</c>.</param>
    public static EdenAssignment Assign(IReadOnlyList<Gamepad> pads, bool proControllerDriver)
    {
        ArgumentNullException.ThrowIfNull(pads);
        var guids = new SdlGuid?[pads.Count];
        var deck = false;
        for (var i = 0; i < pads.Count; i++)
        {
            guids[i] = SdlGuid.TryParse(pads[i].Guid);
            deck |= guids[i] is { Driver: SdlGuid.Hidapi, Vendor: Valve, Product: SteamDeck };
        }

        // Eden numbers the pads of one GUID by the order SDL opened them (its port), whether they're used or not.
        var byDevice = new List<int>(pads.Count);
        for (var i = 0; i < pads.Count; i++)
        {
            byDevice.Add(i);
        }

        byDevice.Sort((a, b) => pads[a].Device.CompareTo(pads[b].Device));
        var ports = new int[pads.Count];
        var seen = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var i in byDevice)
        {
            if (guids[i] is { } guid)
            {
                var edenGuid = guid.ToEdenString();
                seen.TryGetValue(edenGuid, out var port);
                ports[i] = port;
                seen[edenGuid] = port + 1;
            }
        }

        var players = new List<EdenPlayer>();
        var skipped = new List<SkippedPad>();
        for (var i = 0; i < pads.Count; i++)
        {
            var pad = pads[i];
            if (guids[i] is not { } guid)
            {
                skipped.Add(new SkippedPad(pad, $"its GUID '{pad.Guid}' isn't one SDL makes"));
                continue;
            }

            if (deck && guid is { Driver: SdlGuid.XInput, Vendor: 0x045e, Product: 0x028e })
            {
                skipped.Add(new SkippedPad(pad, "it's taken to be the Xbox 360 pad Steam Input or a handheld tool makes of the Steam Deck's controls, which are set up instead"));
                continue;
            }

            if (proControllerDriver && guid.Vendor == 0x057e && guid.Product == 0x2009)
            {
                skipped.Add(new SkippedPad(pad, "Eden reads Pro Controllers with its own driver (enable_procon_driver), so set it up in Eden"));
                continue;
            }

            if (SdlMapping.For(guid, out var unsupported) is not { } mapping)
            {
                skipped.Add(new SkippedPad(pad, unsupported! + "; map it in Eden's own settings"));
                continue;
            }

            if (players.Count == MaxPlayers)
            {
                skipped.Add(new SkippedPad(pad, "Eden has 8 players"));
                continue;
            }

            players.Add(new EdenPlayer(players.Count, pad, guid, guid.ToEdenString(), ports[i], mapping));
        }

        return new EdenAssignment(players, skipped);
    }

    /// <summary>
    /// Writes <paramref name="players"/> into <paramref name="ini"/>'s <c>[Controls]</c>: each player connected as a
    /// Pro Controller with every button, stick and (for a pad with a gyro) motion bound; the other players up to the
    /// eighth disconnected. Every value is written with <c>\default=false</c>, which makes Eden read it. RawInput is
    /// turned off if it's on, since Eden then names XInput pads differently.
    /// </summary>
    internal static void Apply(IniText ini, IReadOnlyList<EdenPlayer> players)
    {
        if (IsOn(ini, "enable_raw_input", false))
        {
            Write(ini, "enable_raw_input", "false");
        }

        foreach (var player in players)
        {
            var prefix = Prefix(player.Player);
            Write(ini, prefix + "connected", "true");
            Write(ini, prefix + "type", "0");
            foreach (var (key, element) in Buttons)
            {
                Write(ini, prefix + key, player.Mapping.TryGet(element, out var input) ? Quote(ButtonParam(player, input)) : "[empty]");
            }

            Write(ini, prefix + "lstick", Stick(player, "leftx", "lefty"));
            Write(ini, prefix + "rstick", Stick(player, "rightx", "righty"));
            var motion = HasGyro(player.Guid) ? Quote(Param(player, "motion:0")) : "[empty]";
            Write(ini, prefix + "motionleft", motion);
            Write(ini, prefix + "motionright", motion);
        }

        for (var player = players.Count; player < MaxPlayers; player++)
        {
            Write(ini, Prefix(player) + "connected", "false");
        }
    }

    /// <summary>
    /// Sets the controllers up in the <c>qt-config.ini</c> at <paramref name="configFile"/> (created if missing; the
    /// first time it's changed, a copy of it is kept beside it, <see cref="BackupSuffix"/>). The file is left as it is
    /// when no pad can be set up. Blocks on file I/O: not on the main thread.
    /// </summary>
    public static ControllerSetup Configure(string configFile, IReadOnlyList<Gamepad> pads)
    {
        ArgumentNullException.ThrowIfNull(configFile);
        ArgumentNullException.ThrowIfNull(pads);
        var exists = File.Exists(configFile);
        var ini = IniText.Parse(exists ? File.ReadAllBytes(configFile) : []);
        var assignment = Assign(pads, IsOn(ini, "enable_procon_driver", false));
        if (assignment.Players.Count == 0)
        {
            return new ControllerSetup(configFile, assignment, Written: false);
        }

        Apply(ini, assignment.Players);
        Directory.CreateDirectory(Path.GetDirectoryName(configFile)!);
        var backup = configFile + BackupSuffix;
        if (exists && !File.Exists(backup))
        {
            File.Copy(configFile, backup);
        }

        // Written beside it and moved over it, so Eden never reads half a file.
        var temporary = configFile + ".odyssey-tmp";
        File.WriteAllBytes(temporary, ini.ToBytes());
        File.Move(temporary, configFile, overwrite: true);
        return new ControllerSetup(configFile, assignment, Written: true);
    }

    private static string Prefix(int player) => string.Create(CultureInfo.InvariantCulture, $"player_{player}_");

    private static void Write(IniText ini, string key, string value)
    {
        ini.Set(Controls, key + "\\default", "false");
        ini.Set(Controls, key, value);
    }

    /// <summary>A boolean as Eden reads it: its default when <c>\default</c> is true or the key is missing.</summary>
    private static bool IsOn(IniText ini, string key, bool defaultValue)
    {
        if (string.Equals(ini.Get(Controls, key + "\\default"), "true", StringComparison.OrdinalIgnoreCase))
        {
            return defaultValue;
        }

        return ini.Get(Controls, key) is { } value ? value.Equals("true", StringComparison.OrdinalIgnoreCase) : defaultValue;
    }

    /// <summary>Eden's SDL driver's <c>BuildParamPackageForBinding</c>.</summary>
    private static string ButtonParam(EdenPlayer player, SdlInput input) => input.Kind switch
    {
        SdlInputKind.Button => Param(player, string.Create(CultureInfo.InvariantCulture, $"button:{input.Index}")),
        SdlInputKind.Axis => Param(player, string.Create(CultureInfo.InvariantCulture, $"axis:{input.Index},threshold:0.5,invert:+")),
        _ => Param(player, string.Create(CultureInfo.InvariantCulture, $"hat:{input.Index},direction:{HatDirection(input.HatMask)}")),
    };

    /// <summary>Its <c>BuildParamPackageForAnalog</c>, with no centre offset; Eden's default deadzone and range apply.</summary>
    private static string Stick(EdenPlayer player, string x, string y) =>
        player.Mapping.TryGet(x, out var axisX) && axisX.Kind == SdlInputKind.Axis
        && player.Mapping.TryGet(y, out var axisY) && axisY.Kind == SdlInputKind.Axis
            ? Quote(Param(player, string.Create(CultureInfo.InvariantCulture,
                $"axis_x:{axisX.Index},axis_y:{axisY.Index},offset_x:0.000000,offset_y:0.000000,invert_x:+,invert_y:+")))
            : "[empty]";

    private static string Param(EdenPlayer player, string rest) =>
        string.Create(CultureInfo.InvariantCulture, $"engine:sdl,port:{player.Port},guid:{player.EdenGuid},{rest}");

    private static string HatDirection(int mask) => mask switch
    {
        1 => "up",
        2 => "right",
        4 => "down",
        _ => "left",
    };

    /// <summary>Eden quotes a value with commas or colons in it (its <c>AdjustOutputString</c>).</summary>
    private static string Quote(string value) => "\"" + value + "\"";

    /// <summary>HIDAPI pads SDL reads a gyro from: PlayStation, Switch Pro (and Switch 2 Pro), the Steam Deck and Steam Controller.</summary>
    private static bool HasGyro(SdlGuid guid) =>
        guid.Driver == SdlGuid.Hidapi
        && (guid.Vendor == 0x054c
            || (guid.Vendor == 0x057e && guid.Product is 0x2009 or 0x2069)
            || (!guid.HasIds && guid.Vendor == 0)
            || (guid.Vendor == Valve && guid.Product is SteamDeck or 0x1102 or 0x1142));
}

/// <summary>What a controller setup did, for the log.</summary>
/// <param name="ConfigFile">The emulator's config file.</param>
/// <param name="Written">False when no pad could be set up, so the file wasn't touched.</param>
public sealed record ControllerSetup(string ConfigFile, EdenAssignment Assignment, bool Written)
{
    /// <summary>One line: who plays as whom, and what was left out.</summary>
    public string Describe()
    {
        var text = new System.Text.StringBuilder();
        if (Assignment.Players.Count == 0)
        {
            text.Append(Assignment.Skipped.Count == 0 ? "no controller is connected" : "no connected controller can be set up");
        }
        else
        {
            foreach (var player in Assignment.Players)
            {
                text.Append(text.Length == 0 ? string.Empty : "; ")
                    .Append(CultureInfo.InvariantCulture, $"player {player.Player + 1} {player.Pad.Name} ({player.Guid.Ids}, {player.Mapping.Source}")
                    .Append(player.Port > 0 ? string.Create(CultureInfo.InvariantCulture, $", port {player.Port})") : ")");
            }
        }

        foreach (var skipped in Assignment.Skipped)
        {
            text.Append("; left out ").Append(skipped.Pad.Name).Append(": ").Append(skipped.Reason);
        }

        text.Append(Written ? $", in {ConfigFile}" : $"; {ConfigFile} left as it was");
        return text.ToString();
    }
}
