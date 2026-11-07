using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Config;

namespace Launcher.App.Settings;

/// <summary>
/// The problems in the config files (About, 2026-11-07): every error and warning, each its file, line and key over its
/// message, in a page as wide as the window allows. It scrolls (up and down, LB and RB) instead of being drawn smaller,
/// as a dialog this tall would be.
/// </summary>
public sealed partial class ConfigProblemsPanel : UiPanel
{
    private const float ScrollStep = 60;

    private static readonly Hint[] Hints = [new("Scroll", Prompt.UpDown), new("Close", Prompt.Accept, Prompt.Back)];

    private readonly ScrollContainer _scroll;

    public ConfigProblemsPanel(IReadOnlyList<Diagnostic> problems)
        : base("Problems in your config files", new Vector2(1600, 1000), PanelPlacement.Centre, dimBelow: true)
    {
        var errors = problems.Count(p => p.IsError);
        var warnings = problems.Count - errors;
        var counts = errors == 0 ? Count(warnings, "warning") : warnings == 0 ? Count(errors, "error") : $"{Count(errors, "error")}, {Count(warnings, "warning")}";
        Subtitle = $"{counts} · Fix them in the files named, or change the setting in Settings";

        _scroll = new ScrollContainer { HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled, FollowFocus = false, SizeFlagsVertical = SizeFlags.ExpandFill };
        Body.AddChild(_scroll);
        var column = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        column.AddThemeConstantOverride("separation", 4);
        _scroll.AddChild(column);

        foreach (var problem in problems)
        {
            var where = new LabelSettings { FontSize = UiStyle.DetailSize, FontColor = problem.IsError ? UiStyle.Bad : UiStyle.Warning };
            column.AddChild(UiStyle.Label(Where(problem), where, wrap: true));
            // Messages are written to follow "key: " in the log, so they start in lower case.
            var message = problem.Message.Length == 0 ? problem.Message : char.ToUpperInvariant(problem.Message[0]) + problem.Message[1..];
            column.AddChild(UiStyle.Label(message, UiStyle.Body, wrap: true));
            column.AddChild(new Control { CustomMinimumSize = new Vector2(0, 14), MouseFilter = MouseFilterEnum.Ignore });
        }

        SetHints(Hints);
    }

    public override bool Handle(NavCommand command)
    {
        switch (command)
        {
            case NavCommand.Accept:
                Close();
                return true;
            case NavCommand.Up or NavCommand.Down or NavCommand.PageUp or NavCommand.PageDown:
                Scroll(command);
                return true;
            default:
                return false;
        }
    }

    private void Scroll(NavCommand command)
    {
        var bar = _scroll.GetVScrollBar();
        var page = Math.Max(ScrollStep, _scroll.Size.Y - ScrollStep);
        var step = command switch
        {
            NavCommand.Up => -ScrollStep,
            NavCommand.Down => ScrollStep,
            NavCommand.PageUp => -page,
            _ => page,
        };
        var bottom = Math.Max(0, bar.MaxValue - bar.Page);
        _scroll.ScrollVertical = (int)Math.Clamp(_scroll.ScrollVertical + step, 0, bottom);
    }

    /// <summary>"Warning · built-in/emulators.windows.toml, line 112 · emulators.dolphin.executable".</summary>
    private static string Where(Diagnostic problem)
    {
        var severity = problem.IsError ? "Error" : "Warning";
        var line = problem.Line > 0 ? string.Create(CultureInfo.InvariantCulture, $", line {problem.Line}") : string.Empty;
        var key = problem.Key.Length > 0 ? $" · {problem.Key}" : string.Empty;
        return $"{severity} · {problem.Source}{line}{key}";
    }

    private static string Count(int value, string what) =>
        value == 1 ? $"1 {what}" : string.Create(CultureInfo.InvariantCulture, $"{value} {what}s");
}
