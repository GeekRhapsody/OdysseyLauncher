using System;
using Godot;

namespace Launcher.App.Ui;

/// <summary>
/// One row of a settings list (M7): a button with a title, an optional second line (a path, a status) and a value on
/// the right, and from 2026-10-07 an optional picture before them (a search hit's cover). A (or a click) activates it;
/// a row that can be adjusted also takes left and right (a choice cycled in place, as the default provider is).
/// </summary>
public sealed partial class SettingRow : Button
{
    /// <summary>The picture's frame: dark, a thin border, the picture a few pixels in.</summary>
    private static readonly StyleBoxFlat PictureFrame = MakePictureFrame();

    private readonly HBoxContainer _line;
    private readonly Label _title;
    private readonly Label _detail;
    private readonly Label _value;
    private readonly LabelSettings _valueSettings;
    private readonly LabelSettings _detailSettings;
    private TextureRect? _picture;
    private Label? _pictureCaption;
    private float _pictureHeight;

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
        _line = row;

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
            UpdateHeight();
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

    /// <summary>
    /// Puts a picture frame of <paramref name="size"/> before the text (a search hit's cover), the row made tall enough
    /// for it. <see cref="SetPicture"/> fills it; until then it's empty.
    /// </summary>
    public void ShowPicture(Vector2 size)
    {
        if (_picture is not null)
        {
            return;
        }

        var frame = new PanelContainer { CustomMinimumSize = size, SizeFlagsVertical = SizeFlags.ShrinkCenter, MouseFilter = MouseFilterEnum.Ignore };
        frame.AddThemeStyleboxOverride("panel", PictureFrame);
        _picture = new TextureRect
        {
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
            MouseFilter = MouseFilterEnum.Ignore,
        };
        frame.AddChild(_picture);
        _pictureCaption = UiStyle.Label(string.Empty, new LabelSettings { FontSize = UiStyle.HintSize - 2, FontColor = UiStyle.Faint }, wrap: true);
        _pictureCaption.HorizontalAlignment = HorizontalAlignment.Center;
        _pictureCaption.VerticalAlignment = VerticalAlignment.Center;
        frame.AddChild(_pictureCaption);
        _line.AddChild(frame);
        _line.MoveChild(frame, 0);
        _pictureHeight = size.Y;
        UpdateHeight();
    }

    /// <summary>
    /// The picture (<see cref="ShowPicture"/>), or, when <paramref name="texture"/> is null, <paramref name="caption"/>
    /// in its frame ("No cover"). The row doesn't own the texture.
    /// </summary>
    public void SetPicture(Texture2D? texture, string? caption = null)
    {
        if (_picture is null || _pictureCaption is null)
        {
            return;
        }

        _picture.Texture = texture;
        _pictureCaption.Text = texture is null ? caption ?? string.Empty : string.Empty;
    }

    private void UpdateHeight()
    {
        var text = _detail.Visible ? 66 : 46;
        CustomMinimumSize = new Vector2(0, Math.Max(text, _pictureHeight + 12));
    }

    private static StyleBoxFlat MakePictureFrame()
    {
        var box = UiStyle.RowBox(new Color(0.02f, 0.03f, 0.1f, 0.9f), new Color("#2E3D86"), 1);
        box.SetCornerRadiusAll(4);
        box.SetContentMarginAll(3);
        return box;
    }

    /// <summary>Left (−1) or right (+1) on the row; null when it can't be adjusted, and the focus moves instead.</summary>
    public Action<int>? Adjuster { get; set; }

    public bool CanAdjust => Adjuster is not null && !Disabled;

    public void Adjust(int direction) => Adjuster?.Invoke(direction);
}
