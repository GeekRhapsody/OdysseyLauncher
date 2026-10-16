using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Ui;
using Launcher.Core.Theming.Downloads;

namespace Launcher.App.Settings;

/// <summary>
/// The theme downloader (Settings, Download themes; A6 Downloading themes), as ES-DE's: every theme the list offers,
/// with its first screenshot, who made it and what the user has of it. A gets it, or, once it's installed, fetches its
/// updates (as ES-DE's A does); X shows its details and screenshots; Y removes it. The list kept from last time shows
/// at once, and is fetched again each time the page opens. A download carries on when the page closes, on its card.
/// </summary>
public sealed partial class ThemeDownloaderPage : ListPanel
{
    public static readonly Vector2 PictureSize = new(192, 108);

    private readonly SettingsController _settings;
    private readonly ThemeDownloader _downloader;
    private readonly Dictionary<string, (SettingRow Row, ThemeStatus Status)> _rows = new(StringComparer.Ordinal);
    private readonly ScreenshotCache _pictures;
    private ThemeListResult? _shown;
    private bool _wasRefreshing;

    public ThemeDownloaderPage(SettingsController settings)
        : base("Download themes")
    {
        _settings = settings;
        _downloader = settings.Themes;
        _pictures = new ScreenshotCache(settings.Ui, PictureSize);
        Subtitle = settings.ThemesList is { } local
            ? $"From {local} · installed in {_downloader.Paths.ThemesDir}"
            : $"From github.com/GeekRhapsody/odyssey-themes · installed in {_downloader.Paths.ThemesDir}";
        SetHints("A  Get or update     X  Details     Y  Remove     B  Back");
        _downloader.Changed += ShowList;
        ShowList();
        _downloader.Refresh();
    }

    public override void OnClosed()
    {
        _downloader.Changed -= ShowList;
        _pictures.Dispose();
    }

    public override bool Handle(NavCommand command)
    {
        if (command is not (NavCommand.Secondary or NavCommand.Alternate))
        {
            return false;
        }

        var focused = GetViewport().GuiGetFocusOwner();
        foreach (var (row, status) in _rows.Values)
        {
            if (row == focused)
            {
                if (command == NavCommand.Alternate)
                {
                    Layer.Push(new ThemeDetailsPanel(_settings, status.Listing.Id));
                }
                else
                {
                    Remove(_settings, this, status);
                }

                return true;
            }
        }

        return false;
    }

    private void ShowList()
    {
        if (_downloader.Refreshing && _downloader.List is null)
        {
            ShowStatus("Reading the list…", UiStyle.Dim);
        }
        else if (_downloader.Refreshing)
        {
            ShowStatus("Checking for new themes and updates…", UiStyle.Dim);
        }
        else if (_wasRefreshing)
        {
            ShowStatus(null);
        }

        _wasRefreshing = _downloader.Refreshing;

        var list = _downloader.List;
        if (list is null)
        {
            return;
        }

        // The same themes: their rows are updated in place (a download's progress, a state), keeping the focus.
        if (_shown is not null && SameThemes(_shown, list) && _shown.RefreshProblem == list.RefreshProblem)
        {
            _shown = list;
            foreach (var status in list.Themes)
            {
                var (row, _) = _rows[status.Listing.Id];
                _rows[status.Listing.Id] = (row, status);
                Describe(row, status);
            }

            return;
        }

        _shown = list;
        ClearRows(out var focusedIndex);
        _rows.Clear();
        if (list.RefreshProblem is not null)
        {
            AddNote($"The list couldn't be brought up to date, so this is the copy from last time. {list.RefreshProblem}", UiStyle.Warning);
        }

        if (list.AppOutdated(_downloader.AppVersion))
        {
            AddNote($"Odyssey Launcher {list.Index.LatestAppVersion} is out: some themes need it.", UiStyle.Warning);
        }

        if (list.Themes.Count == 0)
        {
            AddNote(_downloader.Refreshing ? "Reading the list…" : list.RefreshProblem is null && list.Index.Diagnostics.Count == 0
                ? "The list has no themes yet."
                : "There's no list to show. " + string.Join(" ", list.Index.Diagnostics.Select(d => d.Message)));
        }

        foreach (var status in list.Themes)
        {
            var id = status.Listing.Id;
            var row = AddRow(status.Listing.Name, activated: () => Act(_settings, this, _rows[id].Status));
            row.ShowPicture(PictureSize);
            _rows[id] = (row, status);
            Describe(row, status);
            _pictures.Show(row, status.Listing.Screenshots.Count > 0 ? status.Listing.Screenshots[0].Image : null);
        }

        FocusRow(Math.Max(0, focusedIndex));
    }

    // The same entries, in the same order (a list read again has new records of the same values).
    private static bool SameThemes(ThemeListResult a, ThemeListResult b) =>
        a.Themes.Count == b.Themes.Count && a.Themes.Zip(b.Themes).All(p => SameListing(p.First.Listing, p.Second.Listing));

    /// <summary>Whether two reads of the list say the same about a theme (its records' lists aren't compared by value).</summary>
    public static bool SameListing(ThemeListing a, ThemeListing b) =>
        a.Id == b.Id && a.Url == b.Url && a.Name == b.Name && a.Version == b.Version && a.Deprecated == b.Deprecated
        && a.Screenshots.Select(s => s.Image).SequenceEqual(b.Screenshots.Select(s => s.Image));

    private void Describe(SettingRow row, ThemeStatus status)
    {
        var listing = status.Listing;
        row.Title = listing.New && !status.IsInstalled ? $"{listing.Name}  ·  New" : listing.Name;
        var by = string.IsNullOrEmpty(listing.Author) ? string.Empty : $" · by {listing.Author}";
        row.Detail = StateText(status, _downloader.ActiveThemeId) + by;
        row.DetailColour = listing.Deprecated || status.NeedsNewerApp ? UiStyle.Warning : UiStyle.Dim;
        (row.Value, row.ValueColour) = ActionOf(status);
        row.Modulate = listing.Deprecated ? new Color(1, 1, 1, 0.55f) : Colors.White;
    }

    /// <summary>What A does, as the row's value.</summary>
    private (string Text, Color Colour) ActionOf(ThemeStatus status)
    {
        if (_downloader.Busy == status.Listing.Name)
        {
            return (_downloader.Progress > 0 ? string.Create(CultureInfo.InvariantCulture, $"{_downloader.Progress:P0}") : "…", UiStyle.Accent);
        }

        return status switch
        {
            { NeedsNewerApp: true } => ($"Needs {status.Listing.MinAppVersion}", UiStyle.Warning),
            { State: ThemeInstallState.NotInstalled } => ("Get", UiStyle.Accent),
            { State: ThemeInstallState.ManualInstall or ThemeInstallState.Broken } => ("Replace", UiStyle.Warning),
            _ when status.Listing.Id == _downloader.ActiveThemeId => ("In use", UiStyle.Good),
            _ => ("Installed", UiStyle.Good),
        };
    }

    /// <summary>What the user has of a theme, for its row and its details.</summary>
    public static string StateText(ThemeStatus status, string? activeId)
    {
        var listing = status.Listing;
        var text = status.State switch
        {
            ThemeInstallState.Installed => listing.Id == activeId ? "Installed, and the theme in use" : "Installed",
            ThemeInstallState.ManualInstall => $"Another theme is in its folder, '{listing.Id}': A replaces it, keeping a copy",
            ThemeInstallState.Broken => "Its download was interrupted: A downloads it again",
            _ when status.NeedsNewerApp => $"Needs Odyssey Launcher {listing.MinAppVersion} or later",
            _ => "Not installed",
        };
        if (status.LocalChanges)
        {
            text += ", with changes of your own";
        }

        if (listing.Deprecated)
        {
            text += " · Leaving the list soon";
        }

        return text;
    }

    /// <summary>A on a theme (its row, or its details' first row): get it, replace what's in its folder, or update it.</summary>
    public static void Act(SettingsController settings, UiPanel from, ThemeStatus status)
    {
        var downloader = settings.Themes;
        var listing = status.Listing;
        if (downloader.Busy is { } busy)
        {
            from.ShowStatus(busy == listing.Name ? $"{listing.Name} is on its way." : $"Wait for {busy} to finish first.", UiStyle.Dim, 4);
            return;
        }

        if (status.NeedsNewerApp)
        {
            ConfirmDialog.Tell(settings.Layer, $"{listing.Name} needs a newer launcher",
                $"This version of {listing.Name} needs Odyssey Launcher {listing.MinAppVersion} or later. Update the launcher, then get it here.");
            return;
        }

        switch (status.State)
        {
            case ThemeInstallState.NotInstalled:
                downloader.Install(listing, replace: false);
                return;
            case ThemeInstallState.ManualInstall or ThemeInstallState.Broken:
                var folder = Path.Combine(downloader.Paths.ThemesDir, listing.Id);
                ConfirmDialog.Ask(settings.Layer, $"Replace what's in {listing.Id}?",
                    (status.State == ThemeInstallState.Broken
                        ? $"{folder} holds an interrupted download of {listing.Name}."
                        : $"{folder} holds a theme the downloader didn't put there.")
                    + $"\n\nIt will be moved to {downloader.Paths.BackupsDir}, and {listing.Name} downloaded in its place.",
                    "Replace it", "Keep it", yes =>
                    {
                        if (yes)
                        {
                            downloader.Install(listing, replace: true);
                        }
                    }, destructive: true);
                return;
        }

        // Installed: its updates, fetched now (the user's own changes are asked about if an update would overwrite them).
        downloader.Update(listing, discardChanges: false);
    }

    /// <summary>Y on a theme: deletes its folder, asked first. The theme in use can't be: another is chosen first.</summary>
    public static void Remove(SettingsController settings, UiPanel from, ThemeStatus status)
    {
        var downloader = settings.Themes;
        var listing = status.Listing;
        if (status.State == ThemeInstallState.NotInstalled)
        {
            from.ShowStatus($"{listing.Name} isn't installed.", UiStyle.Dim, 4);
            return;
        }

        if (downloader.Busy is { } busy)
        {
            from.ShowStatus($"Wait for {busy} to finish first.", UiStyle.Dim, 4);
            return;
        }

        if (listing.Id == downloader.ActiveThemeId)
        {
            ConfirmDialog.Tell(settings.Layer, $"{listing.Name} is in use", "Choose another theme under Theme first, then remove it.");
            return;
        }

        var folder = Path.Combine(downloader.Paths.ThemesDir, listing.Id);
        ConfirmDialog.Ask(settings.Layer, $"Remove {listing.Name}?",
            $"{folder} is deleted{(status.State == ThemeInstallState.Installed ? ", with any changes you made to it" : ": it isn't the listed theme, but a theme of the same name")}. You can get {listing.Name} again here.",
            "Remove it", "Keep it", yes =>
            {
                if (yes)
                {
                    downloader.Remove(listing);
                }
            }, destructive: true);
    }

    /// <summary>What a theme brings, from the list's <c>covers</c>: "42 system cards, 3 templates, its own menus".</summary>
    public static string CoversText(ThemeCovers? covers)
    {
        if (covers is null)
        {
            return "The list doesn't say";
        }

        var parts = new List<string>();
        if (covers.SystemCards > 0)
        {
            parts.Add(covers.SystemCards == 1 ? "1 system card" : string.Create(CultureInfo.InvariantCulture, $"{covers.SystemCards} system cards"));
        }

        if (covers.Templates > 0)
        {
            parts.Add(covers.Templates == 1 ? "1 game template" : string.Create(CultureInfo.InvariantCulture, $"{covers.Templates} game templates"));
        }

        if (covers.Menus)
        {
            parts.Add("its own menus");
        }

        if (covers.CardVideos)
        {
            parts.Add("videos on its cards");
        }

        if (covers.GameVideos)
        {
            parts.Add("games' videos");
        }

        return parts.Count == 0 ? "A look of its own (colours and lights)" : string.Join(", ", parts);
    }

    /// <summary>
    /// The screenshots shown on a page's rows: each decoded on a worker (one after another) to fit its frame, and kept
    /// while the page is open; disposed with it.
    /// </summary>
    public sealed class ScreenshotCache(UiContext ui, Vector2 size) : IDisposable
    {
        private readonly Dictionary<string, ImageTexture?> _textures = new(StringComparer.Ordinal);
        private readonly Dictionary<string, List<SettingRow>> _waiting = new(StringComparer.Ordinal);
        private readonly Queue<string> _queue = new();
        private bool _loading;
        private bool _disposed;

        /// <summary>Main thread: fills <paramref name="row"/>'s picture with the image, now or once it's decoded.</summary>
        public void Show(SettingRow row, string? path)
        {
            if (path is null)
            {
                row.SetPicture(null, "No picture");
                return;
            }

            if (_textures.TryGetValue(path, out var texture))
            {
                row.SetPicture(texture, "No picture");
                return;
            }

            row.SetPicture(null, "…");
            if (!_waiting.TryGetValue(path, out var rows))
            {
                _waiting[path] = rows = [];
                _queue.Enqueue(path);
            }

            rows.Add(row);
            LoadNext();
        }

        private void LoadNext()
        {
            if (_loading || _queue.Count == 0 || _disposed)
            {
                return;
            }

            _loading = true;
            var path = _queue.Dequeue();
            var side = (int)Math.Max(size.X, size.Y) * 2;
            var decoder = ui.Decoder;
            _ = Task.Run(() =>
            {
                var texture = File.Exists(path) ? Thumbnails.Load(path, side, decoder, out _) : null;
                ui.Queue.Post(() =>
                {
                    _loading = false;
                    if (_disposed)
                    {
                        texture?.Dispose();
                        return;
                    }

                    _textures[path] = texture;
                    if (_waiting.Remove(path, out var rows))
                    {
                        foreach (var row in rows)
                        {
                            if (GodotObject.IsInstanceValid(row))
                            {
                                row.SetPicture(texture, "No picture");
                            }
                        }
                    }

                    LoadNext();
                });
            });
        }

        public void Dispose()
        {
            _disposed = true;
            foreach (var texture in _textures.Values)
            {
                texture?.Dispose();
            }

            _textures.Clear();
            _waiting.Clear();
            _queue.Clear();
        }
    }
}
