using System.Collections.Generic;
using System.IO;
using System.Linq;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Screens;
using Launcher.App.Ui;
using Launcher.Core.Theming.Downloads;

namespace Launcher.App.Settings;

/// <summary>
/// A listed theme's details (X in the theme downloader): its description, who made it, its version, what it brings,
/// where it comes from and what the user has of it, then its screenshots, each opening full screen on A. Its first row
/// does what A does in the list (get it, or check for updates). Follows the downloader, so a download's progress and its outcome show here too.
/// </summary>
public sealed partial class ThemeDetailsPanel : ListPanel
{
    private static readonly Vector2 ScreenshotSize = new(320, 180);

    private readonly SettingsController _settings;
    private readonly ThemeDownloader _downloader;
    private readonly string _id;
    private readonly ThemeDownloaderPage.ScreenshotCache _pictures;
    private ThemeStatus? _shown;

    public ThemeDetailsPanel(SettingsController settings, string id)
        : base("Theme")
    {
        _settings = settings;
        _downloader = settings.Themes;
        _id = id;
        _pictures = new ThemeDownloaderPage.ScreenshotCache(settings.Ui, ScreenshotSize);
        SetHints("A  Choose     Y  Remove     B  Back");
        _downloader.Changed += ShowTheme;
        ShowTheme();
    }

    public override void OnClosed()
    {
        _downloader.Changed -= ShowTheme;
        _pictures.Dispose();
    }

    public override bool Handle(NavCommand command)
    {
        if (command == NavCommand.Secondary && Status() is { } status)
        {
            ThemeDownloaderPage.Remove(_settings, this, status);
            return true;
        }

        return false;
    }

    private ThemeStatus? Status() => _downloader.List?.Themes.FirstOrDefault(t => t.Listing.Id == _id);

    private void ShowTheme()
    {
        var status = Status();
        if (status is null)
        {
            Close();
            return;
        }

        var listing = status.Listing;
        var rebuild = _shown is null || !ThemeDownloaderPage.SameListing(_shown.Listing, listing) || _shown.InstalledCommit != status.InstalledCommit;
        _shown = status;
        Heading = listing.Name;
        Subtitle = string.IsNullOrEmpty(listing.Author) ? null : $"By {listing.Author}";
        if (!rebuild && Rows.GetChildCount() > 0 && FirstFocusable(Rows) is SettingRow first)
        {
            // A state or progress change: the first row says it; the rest is the list's and hasn't changed.
            DescribeAction(first, status);
            return;
        }

        ClearRows(out var focused);
        if (!string.IsNullOrWhiteSpace(listing.Description))
        {
            AddNote(listing.Description, UiStyle.Text);
        }

        var action = AddRow(listing.Name, activated: () =>
        {
            if (Status() is { } current)
            {
                ThemeDownloaderPage.Act(_settings, this, current);
            }
        });
        DescribeAction(action, status);

        AddSection("About");
        if (listing.Version is not null)
        {
            AddRow("Version", listing.Version);
        }

        if (status.InstalledCommit is { Length: >= 7 } commit)
        {
            AddRow("Installed", $"Commit {commit[..7]}, from its repository's default branch");
        }

        // covers is optional: a theme that doesn't say what it brings has no row for it.
        if (listing.Covers is { } covers)
        {
            AddRow("What it brings", ThemeDownloaderPage.CoversText(covers));
        }
        if (listing.MinAppVersion is not null)
        {
            AddRow("Needs", $"Odyssey Launcher {listing.MinAppVersion} or later");
        }

        AddRow("Repository", listing.Url);
        AddRow("Folder", Path.Combine(_downloader.Paths.ThemesDir, listing.Id));

        if (listing.Screenshots.Count > 0)
        {
            AddSection("Screenshots");
            var items = listing.Screenshots
                .Select(s => new MediaViewer.Item("screenshot", s.Image, $"{listing.Name}: {s.Caption}"))
                .ToList();
            for (var i = 0; i < listing.Screenshots.Count; i++)
            {
                var index = i;
                var shot = listing.Screenshots[i];
                var row = AddRow(shot.Caption, "A  Full screen", activated: () => Layer.Push(new MediaViewer(_settings.Ui, null, items, index)));
                row.ShowPicture(ScreenshotSize);
                _pictures.Show(row, shot.Image);
            }
        }

        FocusRow(focused < 0 ? 0 : focused);
    }

    private void DescribeAction(SettingRow row, ThemeStatus status)
    {
        var listing = status.Listing;
        var busy = _downloader.Busy == listing.Name;
        row.Title = busy
            ? $"Downloading {listing.Name}"
            : status switch
            {
                { NeedsNewerApp: true } => "Can't be installed yet",
                { State: ThemeInstallState.NotInstalled } => $"Get {listing.Name}",
                { State: ThemeInstallState.ManualInstall or ThemeInstallState.Broken } => $"Replace what's in its folder with {listing.Name}",
                _ => "Check for updates",
            };
        row.Detail = ThemeDownloaderPage.StateText(status, _downloader.ActiveThemeId);
        row.DetailColour = listing.Deprecated || status.NeedsNewerApp ? UiStyle.Warning : UiStyle.Dim;
        row.Value = busy && _downloader.Progress > 0 ? $"{_downloader.Progress:P0}" : busy ? "…" : null;
        row.ValueColour = UiStyle.Accent;
    }
}
