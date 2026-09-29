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
    Favourite,
    Rescan,

    /// <summary>Switch to the next theme (M6; the settings screen will choose one in M7).</summary>
    NextTheme,
}

/// <summary>
/// Keyboard and gamepad navigation, polled once per frame. Polling, not <c>_Input</c>: every event reaching C#
/// allocates, and the Deck's controls send joypad motion all the time (docs/perf/m3-launching.md).
/// <para>
/// Held moves repeat and accelerate: the first repeat comes after <see cref="RepeatDelay"/>, then the interval
/// shrinks from <see cref="RepeatSlowest"/> to <see cref="RepeatFastest"/> over <see cref="RampSeconds"/> of holding.
/// </para>
/// </summary>
public sealed class NavInput
{
    public const double RepeatDelay = 0.32;
    public const double RepeatSlowest = 0.12;
    public const double RepeatFastest = 0.035;
    public const double RampSeconds = 1.4;
    private const float StickDeadzone = 0.5f;

    private static readonly StringName Up = "nav_up";
    private static readonly StringName Down = "nav_down";
    private static readonly StringName Left = "nav_left";
    private static readonly StringName Right = "nav_right";
    private static readonly StringName PageUp = "nav_page_up";
    private static readonly StringName PageDown = "nav_page_down";
    private static readonly StringName LetterPrevious = "nav_letter_previous";
    private static readonly StringName LetterNext = "nav_letter_next";
    private static readonly StringName First = "nav_first";
    private static readonly StringName Last = "nav_last";
    private static readonly StringName Accept = "nav_accept";
    private static readonly StringName Back = "nav_back";
    private static readonly StringName Favourite = "nav_favourite";
    private static readonly StringName Rescan = "nav_rescan";
    private static readonly StringName NextTheme = "nav_next_theme";

    private static readonly (StringName Action, NavCommand Command)[] Repeating =
    [
        (Up, NavCommand.Up), (Down, NavCommand.Down), (Left, NavCommand.Left), (Right, NavCommand.Right),
        (PageUp, NavCommand.PageUp), (PageDown, NavCommand.PageDown),
        (LetterPrevious, NavCommand.LetterPrevious), (LetterNext, NavCommand.LetterNext),
    ];

    private static readonly (StringName Action, NavCommand Command)[] Presses =
    [
        (Accept, NavCommand.Accept), (Back, NavCommand.Back), (Favourite, NavCommand.Favourite),
        (First, NavCommand.First), (Last, NavCommand.Last), (Rescan, NavCommand.Rescan), (NextTheme, NavCommand.NextTheme),
    ];

    private NavCommand _held;
    private double _heldFor;
    private double _nextRepeat;
    private bool _wasBlocked;

    /// <summary>How long the current move has been held, for the grid's scroll feel.</summary>
    public double HeldSeconds => _held == NavCommand.None ? 0 : _heldFor;

    /// <summary>
    /// Adds the <c>nav_*</c> actions to the input map, once at boot: arrows, Enter/Space, Escape/Backspace and the
    /// rest on the keyboard; the D-pad, left stick, A/B/Y, shoulders, triggers, View and Menu on a gamepad.
    /// </summary>
    public static void RegisterActions()
    {
        Add(Up, [Key.Up], [JoyButton.DpadUp], (JoyAxis.LeftY, -1));
        Add(Down, [Key.Down], [JoyButton.DpadDown], (JoyAxis.LeftY, 1));
        Add(Left, [Key.Left], [JoyButton.DpadLeft], (JoyAxis.LeftX, -1));
        Add(Right, [Key.Right], [JoyButton.DpadRight], (JoyAxis.LeftX, 1));
        Add(PageUp, [Key.Pageup], [JoyButton.LeftShoulder]);
        Add(PageDown, [Key.Pagedown], [JoyButton.RightShoulder]);
        Add(LetterPrevious, [Key.Bracketleft], [], (JoyAxis.TriggerLeft, 1));
        Add(LetterNext, [Key.Bracketright], [], (JoyAxis.TriggerRight, 1));
        Add(First, [Key.Home], []);
        Add(Last, [Key.End], []);
        Add(Accept, [Key.Enter, Key.KpEnter, Key.Space], [JoyButton.A]);
        Add(Back, [Key.Escape, Key.Backspace], [JoyButton.B]);
        Add(Favourite, [Key.F], [JoyButton.Y]);
        Add(Rescan, [Key.F5], [JoyButton.Back]);
        Add(NextTheme, [Key.T], [JoyButton.Start]);
    }

    private static void Add(StringName action, Key[] keys, JoyButton[] buttons, (JoyAxis Axis, float Direction)? axis = null)
    {
        if (InputMap.HasAction(action))
        {
            return;
        }

        InputMap.AddAction(action, StickDeadzone);
        foreach (var key in keys)
        {
            InputMap.ActionAddEvent(action, new InputEventKey { PhysicalKeycode = key });
        }

        foreach (var button in buttons)
        {
            InputMap.ActionAddEvent(action, new InputEventJoypadButton { ButtonIndex = button, Device = -1 });
        }

        if (axis is { } a)
        {
            InputMap.ActionAddEvent(action, new InputEventJoypadMotion { Axis = a.Axis, AxisValue = a.Direction, Device = -1 });
        }
    }

    /// <summary>
    /// Main thread, once per frame: the command for this frame. While <paramref name="blocked"/> (a game is running,
    /// or has just ended) everything is ignored, and a button still held when it ends doesn't count as a new press.
    /// </summary>
    public NavCommand Poll(double delta, bool blocked)
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
            if (AnyPressed())
            {
                return NavCommand.None;
            }

            _wasBlocked = false;
        }

        foreach (var (action, command) in Presses)
        {
            if (Godot.Input.IsActionJustPressed(action))
            {
                _held = NavCommand.None;
                return command;
            }
        }

        var current = NavCommand.None;
        foreach (var (action, command) in Repeating)
        {
            if (Godot.Input.IsActionPressed(action))
            {
                current = command;
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

    private static bool AnyPressed()
    {
        foreach (var (action, _) in Repeating)
        {
            if (Godot.Input.IsActionPressed(action))
            {
                return true;
            }
        }

        foreach (var (action, _) in Presses)
        {
            if (Godot.Input.IsActionPressed(action))
            {
                return true;
            }
        }

        return false;
    }
}
