using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Config;
using Launcher.Core.Launching.Controllers;

namespace Launcher.App.Navigation;

/// <summary>What a hint asks for: a command's button, or two (LB RB), on the device in use.</summary>
public enum Prompt
{
    Accept,
    Back,

    /// <summary>Y, or I.</summary>
    Secondary,

    /// <summary>X, or O.</summary>
    Alternate,

    /// <summary>Menu (Start), or F1.</summary>
    Menu,

    /// <summary>View (Select), or P.</summary>
    Power,

    /// <summary>L3, or F.</summary>
    Favourite,

    /// <summary>R3, or Z.</summary>
    Inspect,

    /// <summary>LB and RB, or Page Up and Page Down.</summary>
    Pages,

    /// <summary>LT and RT, or [ and ].</summary>
    Letters,

    UpDown,
    LeftRight,

    /// <summary>The right stick, or W, A, S and D.</summary>
    RightStick,

    /// <summary>LT alone (the on-screen keyboard's shift); nothing on the keyboard.</summary>
    Shift,

    /// <summary>RT alone (the on-screen keyboard's symbols); nothing on the keyboard.</summary>
    Symbols,
}

/// <summary>
/// The buttons the controls' hints show (docs/ARCHITECTURE.md A1, "Button icons"): those of the device last used
/// (<see cref="Kind"/>), unless <c>[ui] button_icons</c> or <c>--button-icons</c> chooses a kind, and their glyphs
/// (<c>res://icons/prompts/</c>, Kenney's CC0 Input Prompts, by <c>tools/button-prompts/prepare.py</c>). Main thread,
/// except <see cref="LoadGlyphs"/>.
/// <para>
/// <see cref="NavInput"/> reports each new command (<see cref="Saw"/>): from the keyboard, the kind is the keyboard's;
/// from a pad, it's that pad's (<see cref="PadIcons"/>, from its GUID). The connected pads' kinds are kept as pads come
/// and go, so a command costs a few comparisons and allocates nothing.
/// </para>
/// </summary>
public static class ButtonPrompts
{
    private const string Folder = "res://icons/prompts/";
    private const float AxisPressed = 0.5f;

    /// <summary>The kinds with glyphs, in <see cref="ButtonIcons"/>' order from Xbox; the folder of each.</summary>
    private static readonly string[] Folders = ["xbox", "playstation", "nintendo", "gamecube", "steamdeck", "steamcontroller", "keyboard"];

    // Each prompt's glyphs, by Prompt. A pad's are named by position (a is the bottom face button), so every pad has the
    // same names; a pad without a button has no file for it (Load).
    private static readonly string[][] PadGlyphs =
    [
        ["a"], ["b"], ["y"], ["x"], ["menu"], ["view"], ["l3"], ["r3"], ["lb", "rb"], ["lt", "rt"],
        ["dpad_vertical"], ["dpad_horizontal"], ["stick_r"], ["lt"], ["rt"],
    ];

    private static readonly string[][] KeyGlyphs =
    [
        ["enter"], ["escape"], ["i"], ["o"], ["f1"], ["p"], ["f"], ["z"], ["page_up", "page_down"], ["bracket_open", "bracket_close"],
        ["arrows_vertical"], ["arrows_horizontal"], ["w", "a", "s", "d"], [], [],
    ];

    private static readonly List<(long Device, ButtonIcons Icons)> Pads = [];
    private static Texture2D[][][]? _glyphs;
    private static ButtonIcons _chosen = ButtonIcons.Automatic;
    private static ButtonIcons _seen = ButtonIcons.Keyboard;
    private static ButtonIcons _lastPad = ButtonIcons.Xbox;
    private static bool _samePads = true;

    /// <summary>The kind, the glyphs, or the pads changed: hints show their glyphs again.</summary>
    public static event Action? Changed;

    /// <summary>The buttons the hints show now: never <see cref="ButtonIcons.Automatic"/>.</summary>
    public static ButtonIcons Kind => _chosen == ButtonIcons.Automatic ? _seen : _chosen;

    /// <summary>A pad's kind: <see cref="Kind"/>, or while that's the keyboard, the pad last used (Xbox before any).</summary>
    public static ButtonIcons PadKind => Kind == ButtonIcons.Keyboard ? _lastPad : Kind;

    /// <summary>Main thread, once at boot: follows the pads as they come and go; the first connected one is the kind until something is pressed.</summary>
    public static void Start()
    {
        Input.JoyConnectionChanged += (_, _) => ReadPads();
        ReadPads();
        if (Pads.Count > 0)
        {
            _seen = Pads[0].Icons;
            _lastPad = _seen;
        }
    }

    /// <summary>Main thread: the kind <c>[ui] button_icons</c> (or <c>--button-icons</c>, which wins) chooses, or automatic.</summary>
    public static void Choose(ButtonIcons chosen)
    {
        var before = Kind;
        _chosen = chosen;
        if (Kind != before)
        {
            Changed?.Invoke();
        }
    }

    /// <summary>Any thread (the warm-up's thread pool): every kind's glyphs, each prompt's in order. Null if the app is quitting.</summary>
    public static Texture2D[][][]? LoadGlyphs()
    {
        if (!GodotWork.TryEnter())
        {
            return null;
        }

        try
        {
            var glyphs = new Texture2D[Folders.Length][][];
            for (var kind = 0; kind < Folders.Length; kind++)
            {
                var table = Folders[kind] == "keyboard" ? KeyGlyphs : PadGlyphs;
                glyphs[kind] = new Texture2D[table.Length][];
                for (var prompt = 0; prompt < table.Length; prompt++)
                {
                    glyphs[kind][prompt] = Load(Folders[kind], table[prompt]);
                }
            }

            return glyphs;
        }
        finally
        {
            GodotWork.Exit();
        }
    }

    /// <summary>
    /// A prompt's glyphs in <paramref name="folder"/>; none if the kind lacks any of them (a GameCube pad has no LB, so
    /// no "LB RB" for paging), so a hint never shows half its buttons.
    /// </summary>
    private static Texture2D[] Load(string folder, string[] names)
    {
        var textures = new Texture2D[names.Length];
        for (var i = 0; i < names.Length; i++)
        {
            var path = $"{Folder}{folder}/{names[i]}.svg";
            if (!ResourceLoader.Exists(path))
            {
                return [];
            }

            textures[i] = ResourceLoader.Load<Texture2D>(path);
        }

        return textures;
    }

    /// <summary>Main thread: the glyphs <see cref="LoadGlyphs"/> made. Hints show text alone until then.</summary>
    public static void UseGlyphs(Texture2D[][][] glyphs)
    {
        _glyphs = glyphs;
        Changed?.Invoke();
    }

    /// <summary>Main thread: <paramref name="prompt"/>'s glyphs for <paramref name="kind"/> (not automatic); empty before they're loaded, or when it has none.</summary>
    public static Texture2D[] Glyphs(ButtonIcons kind, Prompt prompt) =>
        _glyphs is { } glyphs ? glyphs[(int)kind - 1][(int)prompt] : [];

    /// <summary>
    /// Main thread, on each new command (not a held one's repeats): it came from a pad, or the keyboard. Allocates
    /// nothing; tells <see cref="Changed"/> only when the kind changes.
    /// </summary>
    public static void Saw(bool fromPad)
    {
        var seen = fromPad ? PressingPad() : ButtonIcons.Keyboard;
        if (seen == _seen)
        {
            return;
        }

        var before = Kind;
        _seen = seen;
        if (fromPad)
        {
            _lastPad = seen;
        }

        if (Kind != before)
        {
            Changed?.Invoke();
        }
    }

    /// <summary>The kind of the pad pressing something: when the connected pads differ, the first with a button down or an axis pushed.</summary>
    private static ButtonIcons PressingPad()
    {
        if (_samePads)
        {
            return Pads.Count > 0 ? Pads[0].Icons : _lastPad;
        }

        foreach (var (device, icons) in Pads)
        {
            if (Pressing((int)device))
            {
                return icons;
            }
        }

        return _lastPad;
    }

    private static bool Pressing(int device)
    {
        for (var button = 0; button < (int)JoyButton.SdlMax; button++)
        {
            if (Input.IsJoyButtonPressed(device, (JoyButton)button))
            {
                return true;
            }
        }

        for (var axis = 0; axis < (int)JoyAxis.SdlMax; axis++)
        {
            if (Math.Abs(Input.GetJoyAxis(device, (JoyAxis)axis)) > AxisPressed)
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>The connected pads' kinds, again: at boot and when one comes or goes.</summary>
    private static void ReadPads()
    {
        Pads.Clear();
        var devices = Input.GetConnectedJoypads();
        var guids = new SdlGuid?[devices.Count];
        var deck = false;
        for (var i = 0; i < devices.Count; i++)
        {
            guids[i] = SdlGuid.TryParse(Input.GetJoyGuid(devices[i]));
            deck |= guids[i] is { IsSteamDeck: true };
        }

        for (var i = 0; i < devices.Count; i++)
        {
            // A GUID SDL didn't make (none on some platforms) is taken to be an Xbox-style pad.
            var icons = guids[i] is { } guid ? PadIcons.Of(guid, deck) : ButtonIcons.Xbox;
            Pads.Add((devices[i], icons));
            GD.Print($"Button icons: pad {devices[i]}, '{Input.GetJoyName(devices[i])}' ({Input.GetJoyGuid(devices[i])}), shows {DisplayNames.Name(icons)}.");
        }

        _samePads = true;
        foreach (var pad in Pads)
        {
            _samePads &= pad.Icons == Pads[0].Icons;
        }
    }
}
