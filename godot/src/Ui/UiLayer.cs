using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Navigation;

namespace Launcher.App.Ui;

/// <summary>
/// Hosts the settings screens and their dialogs (M7) as a stack of <see cref="UiPanel"/>s over the dimmed grid, and
/// drives them: once a frame it polls <see cref="NavInput"/> (the same commands and repeat as the grids) and gives the
/// top panel the command, then does what's left itself: moves the focus with <see cref="Control.FindValidFocusNeighbor"/>,
/// presses the focused button, goes back. Panels under the top one can't take focus or clicks. The mouse works
/// through Godot's own GUI events; Godot's keyboard and gamepad navigation actions are emptied (NavInput), so
/// nothing moves twice. While the stack is empty, the layer is hidden and costs nothing.
/// </summary>
public sealed partial class UiLayer : CanvasLayer
{
    /// <summary>Rows a page up or down moves the focus in a list of rows.</summary>
    public const int PageRows = 6;

    private readonly List<UiPanel> _stack = [];
    private readonly NavInput _input = new();
    private readonly ColorRect _dim;

    public UiLayer()
    {
        Name = "Ui";
        Layer = 4;
        Visible = false;
        _dim = new ColorRect { Color = new Color(0.0f, 0.0f, 0.03f, 0.62f), MouseFilter = Control.MouseFilterEnum.Stop };
        _dim.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(_dim);
    }

    /// <summary>The first panel opened: the grid's input and overlay step aside.</summary>
    public event Action? Opened;

    /// <summary>The last panel closed: the grid has the input again.</summary>
    public event Action? AllClosed;

    public bool IsOpen => _stack.Count > 0;

    public UiPanel? Top => _stack.Count > 0 ? _stack[^1] : null;

    /// <summary>True while input is blocked for the whole app (a game running).</summary>
    public Func<bool>? Blocked { get; set; }

    /// <summary>Shows <paramref name="panel"/> on top, focused. Main thread.</summary>
    public void Push(UiPanel panel)
    {
        if (Top is { } below)
        {
            below.LastFocus = GetViewport().GuiGetFocusOwner() is { } owner && below.IsAncestorOf(owner) ? owner : below.LastFocus;
            below.FocusBehaviorRecursive = Control.FocusBehaviorRecursiveEnum.Disabled;
            below.MouseBehaviorRecursive = Control.MouseBehaviorRecursiveEnum.Disabled;
            if (!panel.IsDialog)
            {
                below.Visible = false;
            }
        }

        panel.Layer = this;
        _stack.Add(panel);
        AddChild(panel);
        if (!Visible)
        {
            Visible = true;
            Opened?.Invoke();
        }
        _input.Reset();
        Callable.From(panel.FocusDefault).CallDeferred();
    }

    /// <summary>Takes <paramref name="panel"/> (and anything above it) off the stack and frees it.</summary>
    public void Pop(UiPanel panel)
    {
        var index = _stack.IndexOf(panel);
        if (index < 0)
        {
            return;
        }

        for (var i = _stack.Count - 1; i >= index; i--)
        {
            var closing = _stack[i];
            _stack.RemoveAt(i);
            RemoveChild(closing);
            closing.OnClosed();
            closing.QueueFree();
        }

        _input.Reset();
        if (Top is { } top)
        {
            top.Visible = true;
            top.FocusBehaviorRecursive = Control.FocusBehaviorRecursiveEnum.Inherited;
            top.MouseBehaviorRecursive = Control.MouseBehaviorRecursiveEnum.Inherited;
            top.OnRevealed();
            Callable.From(top.FocusDefault).CallDeferred();
            return;
        }

        Visible = false;
        GetViewport().GuiReleaseFocus();
        AllClosed?.Invoke();
    }

    /// <summary>Closes every panel.</summary>
    public void CloseAll()
    {
        if (_stack.Count > 0)
        {
            Pop(_stack[0]);
        }
    }

    /// <summary>Main thread, once a frame (called by Main, before the grids).</summary>
    public void Update(double delta)
    {
        if (Top is not { } top)
        {
            return;
        }

        top.Tick(delta);
        var command = _input.Poll(delta, Blocked?.Invoke() ?? false, keyboard: !top.CapturesKeyboard);
        if (command != NavCommand.None)
        {
            Run(command);
        }
    }

    /// <summary>One command to the top panel, from the controller or keyboard, or from <c>--nav-script</c>.</summary>
    public void Run(NavCommand command)
    {
        if (Top is not { } top || top.Handle(command))
        {
            return;
        }

        var focused = GetViewport().GuiGetFocusOwner();
        if (focused is null || !top.IsAncestorOf(focused))
        {
            top.FocusDefault();
            if (command is NavCommand.Up or NavCommand.Down or NavCommand.Left or NavCommand.Right)
            {
                return;
            }

            focused = GetViewport().GuiGetFocusOwner();
        }

        switch (command)
        {
            case NavCommand.Up:
                Move(top, focused, Side.Top);
                break;
            case NavCommand.Down:
                Move(top, focused, Side.Bottom);
                break;
            case NavCommand.Left:
                if (focused is SettingRow { CanAdjust: true } left)
                {
                    left.Adjust(-1);
                }
                else
                {
                    Move(top, focused, Side.Left);
                }

                break;
            case NavCommand.Right:
                if (focused is SettingRow { CanAdjust: true } right)
                {
                    right.Adjust(1);
                }
                else
                {
                    Move(top, focused, Side.Right);
                }

                break;
            case NavCommand.PageUp or NavCommand.PageDown:
                for (var i = 0; i < PageRows && focused is not null; i++)
                {
                    focused = Move(top, focused, command == NavCommand.PageUp ? Side.Top : Side.Bottom);
                }

                break;
            case NavCommand.First:
                UiPanel.FirstFocusable(top)?.GrabFocus();
                break;
            case NavCommand.Last:
                UiPanel.LastFocusable(top)?.GrabFocus();
                break;
            case NavCommand.Accept:
                if (focused is BaseButton { Disabled: false } button)
                {
                    button.EmitSignal(BaseButton.SignalName.Pressed);
                }

                break;
            case NavCommand.Back:
                top.GoBack();
                break;
            case NavCommand.Menu:
                CloseAll();
                break;
        }
    }

    /// <summary>Moves the focus to the neighbour on <paramref name="side"/> inside the top panel; returns the new focus.</summary>
    private static Control? Move(UiPanel top, Control? from, Side side)
    {
        if (from is null)
        {
            return null;
        }

        var next = from.FindValidFocusNeighbor(side);
        if (next is null || !top.IsAncestorOf(next))
        {
            return from;
        }

        next.GrabFocus();
        return next;
    }
}
