using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Boot;
using Launcher.App.Navigation;
using Launcher.App.Theming;
using Launcher.App.Ui;
using Launcher.Core.Library;

namespace Launcher.App.Screens;

/// <summary>
/// A system's details (Y on a system in the grid): its card's model, large (<see cref="ModelView"/>, in the system's
/// look), beside its whole description and every field the app has for it (<see cref="DetailsFormatter.SystemFields"/>).
/// Favourites and Recently played show their description and how many games they hold. The right stick, or left and
/// right, turn the model; up and down scroll the details; Y or B goes back. Read and formatted off the main thread
/// before it opens, as a game's details are (<see cref="GameDetailsPanel"/>).
/// </summary>
public sealed partial class SystemDetailsPanel : UiPanel
{
    private const float ScrollStep = 60;
    private const float ModelWidth = 500;

    private readonly ModelView _model;
    private readonly PanelContainer _info;
    private readonly ScrollContainer _infoScroll;

    private SystemDetailsPanel(Loaded loaded, ThemeRuntime theme)
        : base(loaded.Entry.Name, new Vector2(1220, 700))
    {
        var entry = loaded.Entry;
        Subtitle = entry.Subtitle;
        var row = new HBoxContainer { SizeFlagsVertical = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        row.AddThemeConstantOverride("separation", 16);
        Body.AddChild(row);

        // The card's model, in the system's look, as it stands in the grid when focused.
        var frame = new PanelContainer { CustomMinimumSize = new Vector2(ModelWidth, 0), MouseFilter = MouseFilterEnum.Ignore };
        var border = UiStyle.RowBox(new Color(0, 0, 0, 0), new Color("#2E3D86"), 1);
        border.ContentMarginLeft = border.ContentMarginRight = border.ContentMarginTop = border.ContentMarginBottom = 1;
        frame.AddThemeStyleboxOverride("panel", border);
        row.AddChild(frame);
        var templates = theme.CardTemplates;
        _model = ModelView.Show(
            frame, templates[Math.Clamp(entry.Template, 0, templates.Count - 1)], entry.Name, entry.Colour,
            theme.LookFor(entry.Virtual == VirtualKind.None ? entry.Id : null));

        // The description and the fields: one focusable block that up and down scroll.
        _info = new PanelContainer
        {
            FocusMode = FocusModeEnum.All,
            SizeFlagsHorizontal = SizeFlags.ExpandFill,
            SizeFlagsVertical = SizeFlags.ExpandFill,
            MouseFilter = MouseFilterEnum.Pass,
        };
        _info.AddThemeStyleboxOverride("panel", InfoBox(false));
        _info.FocusEntered += () => _info.AddThemeStyleboxOverride("panel", InfoBox(true));
        _info.FocusExited += () => _info.AddThemeStyleboxOverride("panel", InfoBox(false));
        row.AddChild(_info);
        _infoScroll = new ScrollContainer { HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled, FollowFocus = false };
        _info.AddChild(_infoScroll);
        var column = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        column.AddThemeConstantOverride("separation", 8);
        _infoScroll.AddChild(column);

        var description = UiStyle.Label(
            string.IsNullOrWhiteSpace(loaded.Description) ? "No description." : loaded.Description.Trim(),
            string.IsNullOrWhiteSpace(loaded.Description) ? UiStyle.Detail : UiStyle.Body, wrap: true);
        description.SizeFlagsHorizontal = SizeFlags.ExpandFill;
        column.AddChild(description);
        column.AddChild(Section("Details"));
        var fields = new GridContainer { Columns = 2, MouseFilter = MouseFilterEnum.Ignore };
        fields.AddThemeConstantOverride("h_separation", 16);
        fields.AddThemeConstantOverride("v_separation", 4);
        column.AddChild(fields);
        foreach (var (label, value) in loaded.Fields)
        {
            AddField(fields, label, value);
        }

        SetHints("Up Down  Scroll the details     Left Right / right stick  Turn the model     B / Y  Back");
    }

    public override Control? DefaultFocus => _info;

    /// <summary>
    /// Formats the card's fields off the main thread (counting Favourites' or Recently played's games there), then
    /// opens its details. Main thread.
    /// </summary>
    /// <param name="theme">The theme the grids show, read again when the panel opens (its card's model and look).</param>
    public static void Open(UiContext ui, AppServices services, Func<ThemeRuntime> theme, SystemEntry entry)
    {
        // The theme's descriptions of the models in use already exist: reading them formats nothing.
        var current = theme();
        var cardModel = entry.Virtual == VirtualKind.None ? current.CardModelInUse(entry.Id)?.Description : null;
        var gamesModel = entry.Virtual == VirtualKind.None ? current.GameModelInUse(entry.Id)?.Description : null;
        _ = Task.Run(async () =>
        {
            Loaded? loaded = null;
            try
            {
                loaded = await LoadAsync(services, entry, cardModel, gamesModel).ConfigureAwait(false);
            }
            catch (Exception e)
            {
                GD.PushError($"Details: couldn't read {entry.Id}: {e.Message}");
            }

            ui.Queue.Post(() =>
            {
                if (loaded is not null && !ui.Layer.IsOpen)
                {
                    ui.Layer.Push(new SystemDetailsPanel(loaded, theme()));
                }
            });
        });
    }

    public override bool Handle(NavCommand command)
    {
        switch (command)
        {
            case NavCommand.Secondary:
                Close();
                return true;
            case NavCommand.Left or NavCommand.Right:
                _model.Step(command == NavCommand.Left ? -1 : 1);
                return true;
            case NavCommand.Up or NavCommand.Down or NavCommand.PageUp or NavCommand.PageDown:
                Scroll(command);
                return true;
            default:
                return false;
        }
    }

    public override void Tick(double delta)
    {
        base.Tick(delta);
        _model.Tick((float)delta);
    }

    /// <summary>The model view is kept for the next details screen, under the layer, hidden and not rendering.</summary>
    public override void OnClosed() => _model.Park(Layer);

    private void Scroll(NavCommand command)
    {
        var bar = _infoScroll.GetVScrollBar();
        var page = Math.Max(ScrollStep, _infoScroll.Size.Y - ScrollStep);
        var step = command switch
        {
            NavCommand.Up => -ScrollStep,
            NavCommand.Down => ScrollStep,
            NavCommand.PageUp => -page,
            _ => page,
        };
        var bottom = Math.Max(0, bar.MaxValue - bar.Page);
        _infoScroll.ScrollVertical = (int)Math.Clamp(_infoScroll.ScrollVertical + step, 0, bottom);
    }

    private static void AddField(GridContainer grid, string label, string value)
    {
        var key = UiStyle.Label(label, KeyStyle);
        key.CustomMinimumSize = new Vector2(120, 0);
        key.SizeFlagsVertical = SizeFlags.ShrinkBegin;
        grid.AddChild(key);

        // A line each (a list of emulators or folders), so a path, which has no spaces to break at, can break anywhere
        // rather than after its drive's colon, and the words of a line under it still break between words.
        var lines = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill, CustomMinimumSize = new Vector2(300, 0), MouseFilter = MouseFilterEnum.Ignore };
        lines.AddThemeConstantOverride("separation", 0);
        grid.AddChild(lines);
        foreach (var line in value.Split('\n'))
        {
            var text = UiStyle.Label(line, ValueStyle, wrap: true);
            if (line.AsSpan().IndexOfAny('\\', '/') >= 0)
            {
                text.AutowrapMode = TextServer.AutowrapMode.Arbitrary;
            }

            lines.AddChild(text);
        }
    }

    private static readonly LabelSettings KeyStyle = new() { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Dim };

    private static readonly LabelSettings ValueStyle = new() { FontSize = UiStyle.DetailSize + 1, FontColor = UiStyle.Text };

    private static Label Section(string text)
    {
        var label = UiStyle.Label(text.ToUpperInvariant(), UiStyle.Section);
        label.CustomMinimumSize = new Vector2(0, 26);
        label.VerticalAlignment = VerticalAlignment.Bottom;
        return label;
    }

    private static StyleBoxFlat InfoBox(bool focused)
    {
        var box = UiStyle.RowBox(focused ? new Color(0.1f, 0.15f, 0.4f, 0.45f) : new Color(0.06f, 0.09f, 0.25f, 0.3f), focused ? UiStyle.Accent : default, focused ? 2 : 0, focused ? 8 : 0);
        box.ContentMarginLeft = box.ContentMarginRight = 18;
        box.ContentMarginTop = box.ContentMarginBottom = 12;
        return box;
    }

    private static async Task<Loaded> LoadAsync(AppServices services, SystemEntry entry, string? cardModel, string? gamesModel)
    {
        if (entry.Virtual == VirtualKind.None)
        {
            var fields = DetailsFormatter.SystemFields(entry.System!, entry.Summary, services.Config, cardModel, gamesModel, DateTimeOffset.Now);
            return new Loaded(entry, entry.System!.Description, fields);
        }

        // Favourites and Recently played: their games, counted, and the systems they come from.
        var library = services.Library;
        IReadOnlyList<VirtualGameRow> games = entry.Virtual == VirtualKind.Favourites
            ? await library.GetFavouritesAsync(CancellationToken.None).ConfigureAwait(false)
            : await library.GetRecentlyPlayedAsync(Navigator.RecentlyPlayedLimit, CancellationToken.None).ConfigureAwait(false);
        var systems = new HashSet<string>(StringComparer.Ordinal);
        foreach (var game in games)
        {
            systems.Add(game.SystemId);
        }

        return new Loaded(entry, DetailsFormatter.VirtualDescription(entry.Virtual), DetailsFormatter.VirtualFields(games.Count, systems.Count));
    }

    /// <summary>What the panel shows, read and formatted off the main thread.</summary>
    private sealed record Loaded(SystemEntry Entry, string? Description, IReadOnlyList<(string Label, string Value)> Fields);
}
