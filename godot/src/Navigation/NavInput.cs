using System;
using Godot;

namespace Launcher.App.Navigation;

/// <summary>What the player asked for this frame.</summary>
public enum NavCommand
{
    None,
    Up,
    Down,
    Left,
    Right,
    PageUp,
    PageDown,
    LetterPrevious,
    LetterNext,
    First,
    Last,
    Accept,
    Back,

    /// <summary>Y, or I: the focused game's details in the games grid; a list's second action in the settings screens.</summary>
    Secondary,

    /// <summary>L3 (pressing the left stick), or F: the focused game's favourite, in the games grid and its details.</summary>
    Favourite,

    /// <summary>F5: rescan in the grids.</summary>
    Rescan,

    /// <summary>T: switch to the next theme for this session (M6; the settings screen chooses and saves one from M7).</summary>
    NextTheme,

    /// <summary>Menu (Start) or F1: opens and closes the settings screen (M7); "done" on the on-screen keyboard.</summary>
    Menu,

    /// <summary>
    /// X, or O or the menu key: a screen's third action (an item's options in the grids, M7; the on-screen keyboard's
    /// space; the folder picker's "use this folder").
    /// </summary>
    Alternate,

    /// <summary>View (Select) or P: the power menu in the grids (restart, shut down or sleep the system, or quit).</summary>
    Power,
}

/// <summary>
/// Keyboard and gamepad navigation, polled once per frame. Polling, not <c>_Input</c>: every event reaching C#
/// allocates, and the Deck's controls send joypad motion all the time (docs/perf/m3-launching.md).
/// <para>
/// Held moves repeat and accelerate: the first repeat comes after <see cref="RepeatDelay"/>, then the interval
/// shrinks from <see cref="RepeatSlowest"/> to <see cref="RepeatFastest"/> over <see cref="RampSeconds"/> of holding.
/// </para>
/// <para>
/// Each command is two input actions, one for the keyboard and one for gamepads (M7), so a screen that takes typing
/// (the on-screen keyboard) can leave the keyboard out and still be driven by the pad. Godot's own <c>ui_*</c>
/// navigation actions are emptied at boot: the settings screens move focus from these commands, with the same
/// repeat, so a held D-pad repeats and nothing moves twice.
/// </para>
/// </summary>
public sealed class NavInput
{
    public const double RepeatDelay = 0.32;
    public const double RepeatSlowest = 0.12;
    public const double RepeatFastest = 0.035;
    public const double RampSeconds = 1.4;
    private const float StickDeadzone = 0.5f;

    private static readonly Binding[] Repeating =
    [
        new("nav_up", NavCommand.Up), new("nav_down", NavCommand.Down), new("nav_left", NavCommand.Left), new("nav_right", NavCommand.Right),
        new("nav_page_up", NavCommand.PageUp), new("nav_page_down", NavCommand.PageDown),
        new("nav_letter_previous", NavCommand.LetterPrevious), new("nav_letter_next", NavCommand.LetterNext),
    ];

    private static readonly Binding[] Presses =
    [
        new("nav_accept", NavCommand.Accept), new("nav_back", NavCommand.Back), new("nav_secondary", NavCommand.Secondary),
        new("nav_first", NavCommand.First), new("nav_last", NavCommand.Last), new("nav_rescan", NavCommand.Rescan),
        new("nav_next_theme", NavCommand.NextTheme), new("nav_menu", NavCommand.Menu), new("nav_alternate", NavCommand.Alternate),
        new("nav_power", NavCommand.Power), new("nav_favourite", NavCommand.Favourite),
    ];

    /// <summary>Godot's GUI navigation, which the settings screens replace with <see cref="NavCommand"/>s.</summary>
    private static readonly string[] GodotNavigation =
    [
        "ui_accept", "ui_select", "ui_cancel", "ui_up", "ui_down", "ui_left", "ui_right", "ui_page_up", "ui_page_down", "ui_home", "ui_end",
    ];

    private NavCommand _held;
    private double _heldFor;
    private double _nextRepeat;
    private bool _wasBlocked;

    /// <summary>How long the current move has been held, for the grid's scroll feel.</summary>
    public double HeldSeconds => _held == NavCommand.None ? 0 : _heldFor;

    /// <summary>
    /// Adds the <c>nav_*</c> actions to the input map, once at boot: arrows, Enter/Space, Escape/Backspace and the
    /// rest on the keyboard; the D-pad, left stick (and its click), A/B/X/Y, shoulders, triggers, View and Menu on a gamepad.
    /// </summary>
    public static void RegisterActions()
    {
        Add(0, [Key.Up], [JoyButton.DpadUp], (JoyAxis.LeftY, -1));
        Add(1, [Key.Down], [JoyButton.DpadDown], (JoyAxis.LeftY, 1));
        Add(2, [Key.Left], [JoyButton.DpadLeft], (JoyAxis.LeftX, -1));
        Add(3, [Key.Right], [JoyButton.DpadRight], (JoyAxis.LeftX, 1));
        Add(4, [Key.Pageup], [JoyButton.LeftShoulder]);
        Add(5, [Key.Pagedown], [JoyButton.RightShoulder]);
        Add(6, [Key.Bracketleft], [], (JoyAxis.TriggerLeft, 1));
        Add(7, [Key.Bracketright], [], (JoyAxis.TriggerRight, 1));
        AddPress(0, [Key.Enter, Key.KpEnter, Key.Space], [JoyButton.A]);
        AddPress(1, [Key.Escape, Key.Backspace], [JoyButton.B]);
        AddPress(2, [Key.I], [JoyButton.Y]);
        AddPress(3, [Key.Home], []);
        AddPress(4, [Key.End], []);
        AddPress(5, [Key.F5], []);
        AddPress(6, [Key.T], []);
        AddPress(7, [Key.F1], [JoyButton.Start]);
        AddPress(8, [Key.O, Key.Menu], [JoyButton.X]);
        AddPress(9, [Key.P], [JoyButton.Back]);
        AddPress(10, [Key.F], [JoyButton.LeftStick]);

        foreach (var action in GodotNavigation)
        {
            if (InputMap.HasAction(action))
            {
                InputMap.ActionEraseEvents(action);
            }
        }
    }

    private static void Add(int index, Key[] keys, JoyButton[] buttons, (JoyAxis Axis, float Direction)? axis = null) =>
        Register(Repeating[index], keys, buttons, axis);

    private static void AddPress(int index, Key[] keys, JoyButton[] buttons) => Register(Presses[index], keys, buttons, null);

    private static void Register(Binding binding, Key[] keys, JoyButton[] buttons, (JoyAxis Axis, float Direction)? axis)
    {
        if (InputMap.HasAction(binding.Keys))
        {
            return;
        }

        InputMap.AddAction(binding.Keys, StickDeadzone);
        InputMap.AddAction(binding.Pad, StickDeadzone);
        foreach (var key in keys)
        {
            InputMap.ActionAddEvent(binding.Keys, new InputEventKey { PhysicalKeycode = key });
        }

        foreach (var button in buttons)
        {
            InputMap.ActionAddEvent(binding.Pad, new InputEventJoypadButton { ButtonIndex = button, Device = -1 });
        }

        if (axis is { } a)
        {
            InputMap.ActionAddEvent(binding.Pad, new InputEventJoypadMotion { Axis = a.Axis, AxisValue = a.Direction, Device = -1 });
        }
    }

    /// <summary>
    /// Main thread, once per frame: the command for this frame. While <paramref name="blocked"/> (a game is running,
    /// or has just ended) everything is ignored, and a button still held when it ends doesn't count as a new press.
    /// </summary>
    /// <param name="keyboard">False while the keyboard types text (the on-screen keyboard): only gamepads navigate.</param>
    public NavCommand Poll(double delta, bool blocked, bool keyboard = true)
    {
        if (blocked)
        {
            _held = NavCommand.None;
            _wasBlocked = true;
            return NavCommand.None;
        }

        if (_wasBlocked)
        {
            // Wait for everything to be let go first.
            if (AnyPressed(keyboard))
            {
                return NavCommand.None;
            }

            _wasBlocked = false;
        }

        foreach (var binding in Presses)
        {
            if (Godot.Input.IsActionJustPressed(binding.Pad) || (keyboard && Godot.Input.IsActionJustPressed(binding.Keys)))
            {
                _held = NavCommand.None;
                return binding.Command;
            }
        }

        var current = NavCommand.None;
        foreach (var binding in Repeating)
        {
            if (Godot.Input.IsActionPressed(binding.Pad) || (keyboard && Godot.Input.IsActionPressed(binding.Keys)))
            {
                current = binding.Command;
                break;
            }
        }

        if (current == NavCommand.None)
        {
            _held = NavCommand.None;
            return NavCommand.None;
        }

        if (current != _held)
        {
            _held = current;
            _heldFor = 0;
            _nextRepeat = RepeatDelay;
            return current;
        }

        _heldFor += delta;
        if (_heldFor < _nextRepeat)
        {
            return NavCommand.None;
        }

        var ramp = Math.Clamp((_heldFor - RepeatDelay) / RampSeconds, 0, 1);
        _nextRepeat += RepeatSlowest + (RepeatFastest - RepeatSlowest) * ramp;

        // After a long frame, don't burst: one move per frame, and the schedule catches up.
        if (_nextRepeat < _heldFor)
        {
            _nextRepeat = _heldFor;
        }

        return current;
    }

    /// <summary>Forgets a held move, so a screen that just opened doesn't repeat the press that opened it.</summary>
    public void Reset()
    {
        _held = NavCommand.None;
        _wasBlocked = true;
    }

    private static bool AnyPressed(bool keyboard)
    {
        foreach (var binding in Repeating)
        {
            if (Godot.Input.IsActionPressed(binding.Pad) || (keyboard && Godot.Input.IsActionPressed(binding.Keys)))
            {
                return true;
            }
        }

        foreach (var binding in Presses)
        {
            if (Godot.Input.IsActionPressed(binding.Pad) || (keyboard && Godot.Input.IsActionPressed(binding.Keys)))
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>A command's two actions, their names cached as <see cref="StringName"/>s.</summary>
    private sealed class Binding(string name, NavCommand command)
    {
        public StringName Keys { get; } = name;

        public StringName Pad { get; } = name + "_pad";

        public NavCommand Command { get; } = command;
    }
}
