using System.Collections.Generic;
using Godot;

namespace Launcher.App.Ui;

/// <summary>
/// The progress of long operations, over the grid (M7): a card per job, top right, with a bar, what it's counted and
/// its note. It never takes the focus, so browsing carries on while a scan or scrape runs, and it has no buttons: the
/// settings screen's Library section cancels a job. A finished job shows its outcome for a few seconds. It only changes when a job does, never per frame.
/// </summary>
public sealed partial class JobsHud : CanvasLayer
{
    private const float Width = 380;

    private readonly BackgroundJobs _jobs;
    private readonly VBoxContainer _cards;

    public JobsHud(BackgroundJobs jobs)
    {
        Name = "Jobs";
        Layer = 2;
        _jobs = jobs;
        var root = new Control { MouseFilter = Control.MouseFilterEnum.Ignore, Theme = UiStyle.Theme };
        root.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        AddChild(root);
        _cards = new VBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
        _cards.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.TopRight);
        _cards.OffsetLeft = -44 - Width;
        _cards.OffsetRight = -44;
        _cards.OffsetTop = 96; // under the status indicators and "Favourite"
        _cards.AddThemeConstantOverride("separation", 8);
        root.AddChild(_cards);
        jobs.Changed += Rebuild;
    }

    public override void _ExitTree() => _jobs.Changed -= Rebuild;

    private void Rebuild()
    {
        foreach (var child in _cards.GetChildren())
        {
            _cards.RemoveChild(child);
            child.QueueFree();
        }

        foreach (var job in _jobs.Jobs)
        {
            _cards.AddChild(Card(job));
        }
    }

    private static PanelContainer Card(BackgroundJob job)
    {
        var card = new PanelContainer { MouseFilter = Control.MouseFilterEnum.Ignore, CustomMinimumSize = new Vector2(Width, 0) };
        var box = UiStyle.PanelBox(10);
        box.ContentMarginLeft = box.ContentMarginRight = 16;
        box.ContentMarginTop = box.ContentMarginBottom = 10;
        box.ShadowSize = 10;
        card.AddThemeStyleboxOverride("panel", box);
        var column = new VBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
        column.AddThemeConstantOverride("separation", 4);
        card.AddChild(column);

        var top = new HBoxContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
        column.AddChild(top);
        var title = UiStyle.Label(job.Title, new LabelSettings { FontSize = 16, FontColor = UiStyle.Text });
        title.SizeFlagsHorizontal = Control.SizeFlags.ExpandFill;
        title.ClipText = true;
        title.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
        top.AddChild(title);
        if (job.State == JobState.Running)
        {
            column.AddChild(Bar(job.Fraction));
        }

        var colour = job.State switch
        {
            JobState.Running => UiStyle.Dim,
            JobState.Finished => UiStyle.Good,
            _ => UiStyle.Warning,
        };
        column.AddChild(UiStyle.Label(job.Describe(), new LabelSettings { FontSize = 14, FontColor = colour }, wrap: true));
        if (job.State == JobState.Running && job.Note is { } note)
        {
            column.AddChild(UiStyle.Label(note, new LabelSettings { FontSize = 13, FontColor = UiStyle.Faint }, wrap: true));
        }

        return card;
    }

    /// <summary>A slim progress bar (also used by the settings screen's job rows).</summary>
    public static ProgressBar Bar(double fraction) => new()
    {
        MinValue = 0,
        MaxValue = 1,
        Step = 0,
        Value = fraction,
        ShowPercentage = false,
        CustomMinimumSize = new Vector2(0, 8),
        MouseFilter = Control.MouseFilterEnum.Ignore,
    };

    /// <summary>For tests and captures.</summary>
    public IReadOnlyList<BackgroundJob> Shown => _jobs.Jobs;
}
