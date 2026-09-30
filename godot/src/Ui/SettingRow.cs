using System;
using Godot;

namespace Launcher.App.Ui;

/// <summary>
/// One row of a settings list (M7): a button with a title, an optional second line (a path, a status) and a value on
/// the right. A (or a click) activates it; a row that can be adjusted also takes left and right (a choice cycled in
/// place, as the default provider is).
/// </summary>
public sealed partial class SettingRow : Button
{
    private readonly Label _title;
    private readonly Label _detail;
    private readonly Label _value;
    private readonly LabelSettings _valueSettings;
    private readonly LabelSettings _detailSettings;

    public SettingRow(string title, string? detail = null, string? value = null, Action? activated = null)
    {
        FocusMode = FocusModeEnum.All;
        SizeFlagsHorizontal = SizeFlags.ExpandFill;
        ClipContents = true;

        var margins = new MarginContainer { MouseFilter = MouseFilterEnum.Ignore };
        margins.SetAnchorsPreset(LayoutPreset.FullRect);
        margins.AddThemeConstantOverride("margin_left", 16);
        margins.AddThemeConstantOverride("margin_right", 16);
        margins.AddThemeConstantOverride("margin_top", 6);
        margins.AddThemeConstantOverride("margin_bottom", 6);
        AddChild(margins);

        var row = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        row.AddThemeConstantOverride("separation", 16);
        margins.AddChild(row);

        var text = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, Alignment = BoxContainer.AlignmentMode.Center, MouseFilter = MouseFilterEnum.Ignore };
        text.AddThemeConstantOverride("separation", 0);
        row.AddChild(text);
        _title = UiStyle.Label(title, new LabelSettings { FontSize = UiStyle.RowSize, FontColor = UiStyle.Text });
        _title.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
        _title.ClipText = true;
        text.AddChild(_title);
        _detailSettings = new LabelSettings { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Dim };
        _detail = UiStyle.Label(string.Empty, _detailSettings);
        _detail.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
        _detail.ClipText = true;
        text.AddChild(_detail);

        _valueSettings = new LabelSettings { FontSize = UiStyle.DetailSize + 1, FontColor = UiStyle.Accent };
        _value = UiStyle.Label(string.Empty, _valueSettings);
        _value.HorizontalAlignment = HorizontalAlignment.Right;
        _value.VerticalAlignment = VerticalAlignment.Center;
        _value.SizeFlagsVertical = SizeFlags.Fill;
        row.AddChild(_value);

        Detail = detail;
        Value = value;
        if (activated is not null)
        {
            Pressed += activated;
        }
    }

    public string Title
    {
        get => _title.Text;
        set => _title.Text = value;
    }

    /// <summary>The second line; null hides it (and makes the row shorter).</summary>
    public string? Detail
    {
        get => _detail.Visible ? _detail.Text : null;
        set
        {
            _detail.Text = value ?? string.Empty;
            _detail.Visible = !string.IsNullOrEmpty(value);
            CustomMinimumSize = new Vector2(0, _detail.Visible ? 66 : 46);
        }
    }

    public string? Value
    {
        get => _value.Text;
        set => _value.Text = value ?? string.Empty;
    }

    public Color ValueColour
    {
        set => _valueSettings.FontColor = value;
    }

    public Color DetailColour
    {
        set => _detailSettings.FontColor = value;
    }

    /// <summary>Left (−1) or right (+1) on the row; null when it can't be adjusted, and the focus moves instead.</summary>
    public Action<int>? Adjuster { get; set; }

    public bool CanAdjust => Adjuster is not null && !Disabled;

    public void Adjust(int direction) => Adjuster?.Invoke(direction);
}
