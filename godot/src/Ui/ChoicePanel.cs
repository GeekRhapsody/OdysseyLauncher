using System;
using System.Collections.Generic;
using Godot;

namespace Launcher.App.Ui;

/// <summary>One option of a <see cref="ChoicePanel"/>.</summary>
public sealed record Choice(string Id, string Title, string? Detail = null);

/// <summary>
/// Picks one of a list (M7): a theme, a system's emulator, the default provider. The current choice is marked and
/// focused first; A picks, B leaves it as it was.
/// </summary>
public sealed partial class ChoicePanel : ListPanel
{
    private readonly Action<Choice> _chosen;
    private SettingRow? _current;

    public ChoicePanel(string title, string? subtitle, IReadOnlyList<Choice> choices, string? currentId, Action<Choice> chosen)
        : base(title, new Vector2(820, 640), dimBelow: true)
    {
        _chosen = chosen;
        Subtitle = subtitle;
        foreach (var choice in choices)
        {
            var row = AddRow(choice.Title, choice.Detail, choice.Id == currentId ? "In use" : null, () =>
            {
                Close();
                _chosen(choice);
            });
            if (choice.Id == currentId)
            {
                _current = row;
            }
        }

        SetHints("A  Choose     B  Keep as it is");
    }

    public override Control? DefaultFocus => _current ?? base.DefaultFocus;
}
