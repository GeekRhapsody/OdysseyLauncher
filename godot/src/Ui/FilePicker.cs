using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.Core.Files;
using Launcher.Core.Media;
using Launcher.Core.Platform;

namespace Launcher.App.Ui;

public enum PickerMode
{
    Folder,
    File,
}

/// <summary>What a picker is choosing, and what happens with the choice.</summary>
/// <param name="Use">A <see cref="PickerUses"/> value: each use remembers its own last folder.</param>
/// <param name="Filter">The files a file picker offers (null: every file). Ignored for folders.</param>
/// <param name="Start">Where to start: the current value (a folder, or a file to select), else the use's last folder.</param>
/// <param name="Thumbnails">Show a preview of the selected image.</param>
public sealed record PickerRequest(
    string Title,
    PickerMode Mode,
    string Use,
    Action<string> Chosen,
    FileFilter? Filter = null,
    string? Start = null,
    string? Subtitle = null,
    bool Thumbnails = false,
    Action? Cancelled = null);

/// <summary>
/// The folder and file picker (M7), used everywhere the app asks for a path instead of the OS dialog.
/// <list type="bullet">
/// <item>The top level lists quick-access folders (the user's folder, Desktop, Downloads, the ROM root) and every
/// drive, mapped network drives included (their share, and whether they're connected); volume labels arrive as
/// they're read, so a disconnected share can't hold the list up.</item>
/// <item>A opens a folder (or picks a file), B goes up a level, LB and RB page, LT and RT jump by letter, Y types a
/// path on the on-screen keyboard (<c>\\server\share</c> paths too), and in the folder picker X uses the folder
/// that's open. Mouse: double-click opens, the wheel scrolls, and the buttons along the bottom do the rest.</item>
/// <item>Folders are listed on their own thread, and the list is virtualised, so one with tens of thousands of files
/// stays responsive. A folder that's slow to open (a sleeping NAS) leaves the current one on screen with a note, and
/// B stops waiting for it; one that can't be opened says why.</item>
/// <item>The image picker shows the selected image, decoded and scaled off the main thread.</item>
/// <item>Each use remembers the last folder a pick was made in, across sessions.</item>
/// </list>
/// </summary>
public sealed partial class FilePicker : UiPanel
{
    private const double SlowSeconds = 2.5;
    private const double PreviewDelay = 0.15;
    private const int PreviewSide = 300;
    private static readonly FileFilter AnyFile = new("Files", []);

    private readonly UiContext _context;
    private readonly PickerRequest _request;
    private readonly VirtualList _list;
    private readonly Label _state;
    private readonly LabelSettings _stateSettings = new() { FontSize = UiStyle.DetailSize, FontColor = UiStyle.Dim };
    private readonly TextureRect? _preview;
    private readonly Label? _previewInfo;
    private readonly Button _up;
    private readonly List<FileLocation> _places = [];
    private string? _folder;
    private int _generation;
    private int _rootsGeneration;
    private string? _opening;
    private double _openingSince;
    private double _stateRefreshAt;
    private ListingProgress? _progress;
    private string _summary = string.Empty;
    private double _clock;
    private int _previewGeneration;
    private double _previewDue = -1;
    private string? _previewPath;
    private bool _finished;

    public FilePicker(UiContext context, PickerRequest request)
        : base(request.Title, new Vector2(1120, 700), PanelPlacement.Centre, dimBelow: true)
    {
        _context = context;
        _request = request;
        Subtitle = request.Subtitle;

        _state = UiStyle.Label(string.Empty, _stateSettings);
        _state.TextOverrunBehavior = TextServer.OverrunBehavior.TrimEllipsis;
        Body.AddChild(_state);

        var middle = new HBoxContainer { SizeFlagsVertical = SizeFlags.ExpandFill, MouseFilter = MouseFilterEnum.Ignore };
        middle.AddThemeConstantOverride("separation", 16);
        Body.AddChild(middle);
        _list = new VirtualList();
        _list.Activated += Activate;
        _list.SelectionChanged += OnSelectionChanged;
        middle.AddChild(_list);

        if (request.Thumbnails)
        {
            var column = new VBoxContainer { CustomMinimumSize = new Vector2(PreviewSide, 0), MouseFilter = MouseFilterEnum.Ignore };
            middle.AddChild(column);
            var frame = new PanelContainer { CustomMinimumSize = new Vector2(PreviewSide, PreviewSide), MouseFilter = MouseFilterEnum.Ignore };
            frame.AddThemeStyleboxOverride("panel", UiStyle.RowBox(new Color(0.02f, 0.03f, 0.1f, 0.9f), new Color("#2E3D86"), 1));
            column.AddChild(frame);
            _preview = new TextureRect { ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize, StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered, MouseFilter = MouseFilterEnum.Ignore };
            frame.AddChild(_preview);
            _previewInfo = UiStyle.Label(string.Empty, UiStyle.Detail, wrap: true);
            _previewInfo.HorizontalAlignment = HorizontalAlignment.Center;
            column.AddChild(_previewInfo);
        }

        var buttons = new HBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        buttons.AddThemeConstantOverride("separation", 10);
        Body.AddChild(buttons);
        _up = FooterButton(buttons, "Up a level", Up);
        FooterButton(buttons, "Type a path", TypePath);
        if (request.Mode == PickerMode.Folder)
        {
            FooterButton(buttons, "Use this folder", UseThisFolder);
        }

        FooterButton(buttons, "Cancel", Cancel);

        SetHints(request.Mode == PickerMode.Folder
            ? "A  Open     B  Up     X  Use this folder     Y  Type a path     LB RB  Page     LT RT  Letter"
            : "A  Open or choose     B  Up     Y  Type a path     LB RB  Page     LT RT  Letter");
    }

    protected override string BackLabel => "Cancel";

    public override Control? DefaultFocus => _list;

    public override void _Ready()
    {
        // From the list, right (or down past its last row) reaches the buttons along the bottom.
        _list.FocusNeighborRight = _list.GetPathTo(_up);
        _list.FocusNeighborBottom = _list.GetPathTo(_up);
    }

    /// <summary>The folder shown, or null for the top level (for the nav script's log and tests).</summary>
    public string? Folder => _folder;

    public static FilePicker Open(UiContext context, PickerRequest request)
    {
        var picker = new FilePicker(context, request);
        context.Layer.Push(picker);
        picker.Start();
        return picker;
    }

    private void Start()
    {
        var start = _request.Start ?? _context.History.Get(_request.Use);
        if (start is null)
        {
            ShowPlaces(null, null);
            return;
        }

        // A file to select (an emulator's current .exe): open its folder with it selected.
        if (_request.Mode == PickerMode.File && Path.HasExtension(start) && (_request.Filter ?? AnyFile).Matches(start))
        {
            OpenFolder(Path.GetDirectoryName(start) ?? start, Path.GetFileName(start));
            return;
        }

        OpenFolder(start, null);
    }

    public override bool Handle(NavCommand command)
    {
        switch (command)
        {
            case NavCommand.Back:
                Up();
                return true;
            case NavCommand.Favourite:
                TypePath();
                return true;
            case NavCommand.Alternate when _request.Mode == PickerMode.Folder:
                UseThisFolder();
                return true;
            case NavCommand.Menu:
                Cancel();
                return true;
        }

        if (!_list.HasFocus())
        {
            return false;
        }

        switch (command)
        {
            case NavCommand.Up:
                _list.Move(-1);
                return true;
            case NavCommand.Down:
                _list.Move(1);
                return true;
            case NavCommand.PageUp:
                _list.Move(-_list.VisibleRows);
                return true;
            case NavCommand.PageDown:
                _list.Move(_list.VisibleRows);
                return true;
            case NavCommand.First:
                _list.Select(0);
                return true;
            case NavCommand.Last:
                _list.Select(_list.Count - 1);
                return true;
            case NavCommand.LetterNext:
                _list.Select(LetterJump.Next(_list.Count, NameAt, _list.SelectedIndex));
                return true;
            case NavCommand.LetterPrevious:
                _list.Select(LetterJump.Previous(_list.Count, NameAt, _list.SelectedIndex));
                return true;
            case NavCommand.Accept:
                _list.Activate();
                return true;
            default:
                return false;
        }
    }

    public override void GoBack() => Cancel();

    public override void Tick(double delta)
    {
        base.Tick(delta);
        _clock += delta;
        if (_opening is not null && _clock >= _stateRefreshAt)
        {
            _stateRefreshAt = _clock + 0.25;
            RefreshState();
        }

        if (_previewDue >= 0 && _clock >= _previewDue)
        {
            _previewDue = -1;
            LoadPreview(_previewPath);
        }
    }

    public override void OnClosed()
    {
        _generation++;
        _previewGeneration++;
        if (!_finished)
        {
            _finished = true;
            _request.Cancelled?.Invoke();
        }
    }

    // ---- The top level: places and drives ----------------------------------------------------------

    /// <summary>Lists the quick-access folders and drives (on a worker: even that checks folders exist), then their labels.</summary>
    private void ShowPlaces(string? select, string? problem)
    {
        var generation = ++_generation;
        var roots = ++_rootsGeneration;
        _opening = null;
        _list.Waiting = false;
        var locations = _context.Locations;
        var romRoot = _context.RomRoot();
        _ = Task.Run(() =>
        {
            var places = new List<FileLocation>();
            places.AddRange(locations.QuickAccess());
            if (Directory.Exists(romRoot) && !places.Exists(p => string.Equals(p.Path, romRoot, StringComparison.OrdinalIgnoreCase)))
            {
                places.Insert(Math.Min(1, places.Count), new FileLocation(romRoot, "ROM folder", LocationKind.Folder, romRoot));
            }

            places.AddRange(locations.Drives());
            _context.Queue.Post(() => PlacesListed(generation, roots, places, select, problem));
        });
    }

    private void PlacesListed(int generation, int roots, List<FileLocation> places, string? select, string? problem)
    {
        if (generation != _generation || _finished)
        {
            return;
        }

        _folder = null;
        _places.Clear();
        _places.AddRange(places);
        Subtitle = _request.Subtitle ?? "Places and drives";
        var selected = select is null ? 0 : Math.Max(0, _places.FindIndex(p => string.Equals(p.Path, select, StringComparison.OrdinalIgnoreCase)));
        _list.SetItems(PlaceItems(), selected);
        _summary = "Choose a place or drive to start from.";
        ShowListState(problem);
        _up.Disabled = true;

        // Labels can take tens of seconds on a disconnected share: each is read on its own thread, and shown when it comes.
        for (var i = 0; i < _places.Count; i++)
        {
            var place = _places[i];
            if (place.Kind == LocationKind.Folder)
            {
                continue;
            }

            _ = Task.Factory.StartNew(() =>
            {
                var label = _context.Locations.VolumeLabel(place.Path);
                if (label is not null)
                {
                    _context.Queue.Post(() => LabelRead(roots, place.Path, label));
                }
            }, CancellationToken.None, TaskCreationOptions.LongRunning, TaskScheduler.Default);
        }
    }

    private void LabelRead(int roots, string path, string label)
    {
        if (roots != _rootsGeneration || _folder is not null || _finished)
        {
            return;
        }

        var index = _places.FindIndex(p => p.Path == path);
        if (index < 0)
        {
            return;
        }

        var place = _places[index];
        var letter = place.Path.TrimEnd('\\', '/');
        _places[index] = place with { Label = $"{label} ({letter})" };
        _list.UpdateItems(PlaceItems());
    }

    private List<ListItem> PlaceItems()
    {
        var items = new List<ListItem>(_places.Count);
        foreach (var place in _places)
        {
            var kind = !place.Available ? ItemKind.Unavailable : place.Kind switch
            {
                LocationKind.Folder => ItemKind.Place,
                LocationKind.Network => ItemKind.Network,
                _ => ItemKind.Drive,
            };
            items.Add(new ListItem(place.Label, place.Kind == LocationKind.Folder ? place.Path : place.Detail, kind, place.Path));
        }

        return items;
    }

    // ---- Folders ------------------------------------------------------------------------------------

    /// <summary>
    /// Lists <paramref name="folder"/> on its own thread (a share can block a directory read for many seconds, which
    /// nothing can interrupt), keeping the current folder on screen until it's in. A newer request, or B, supersedes it.
    /// </summary>
    private void OpenFolder(string folder, string? select)
    {
        var generation = ++_generation;
        _opening = folder;
        _openingSince = _clock;
        _stateRefreshAt = _clock + 0.3;
        var progress = _progress = new ListingProgress();
        var filter = _request.Mode == PickerMode.Folder ? null : _request.Filter ?? AnyFile;
        var mode = _request.Mode;
        var thread = new Thread(() =>
        {
            var target = folder;
            var selecting = select;

            // A typed path can name a file: open its folder with it selected.
            if (!Directory.Exists(target) && File.Exists(target))
            {
                selecting = Path.GetFileName(target);
                target = Path.GetDirectoryName(target) ?? target;
            }

            var result = DirectoryListing.List(target, filter, CancellationToken.None, progress);
            var items = new List<ListItem>(result.Entries.Count);
            foreach (var entry in result.Entries)
            {
                items.Add(entry.IsFolder
                    ? new ListItem(entry.Name, null, ItemKind.Folder)
                    : new ListItem(entry.Name, UiStyle.Size(entry.SizeBytes), ItemKind.File));
            }

            var summary = Summary(result, mode);
            _context.Queue.Post(() => Listed(generation, result, items, selecting, summary));
        })
        {
            IsBackground = true,
            Name = "Picker listing",
            Priority = ThreadPriority.BelowNormal,
        };
        thread.Start();
    }

    private void Listed(int generation, DirectoryListingResult result, List<ListItem> items, string? select, string summary)
    {
        if (generation != _generation || _finished)
        {
            return;
        }

        _opening = null;
        _list.Waiting = false;
        if (result.Failed)
        {
            if (_folder is null && _places.Count == 0)
            {
                // The start folder is gone (an unplugged drive): start from the top, saying why.
                ShowPlaces(null, result.Problem);
                return;
            }

            ShowListState(result.Problem);
            return;
        }

        _folder = result.Folder;
        Subtitle = _folder;
        var selected = 0;
        if (select is not null)
        {
            selected = Math.Max(0, items.FindIndex(i => string.Equals(i.Name, select, StringComparison.OrdinalIgnoreCase)));
        }

        _list.SetItems(items, selected);
        _summary = summary;
        ShowListState(null);
        _up.Disabled = false;
    }

    private static string Summary(DirectoryListingResult result, PickerMode mode)
    {
        int folders = 0, files = 0;
        foreach (var entry in result.Entries)
        {
            if (entry.IsFolder)
            {
                folders++;
            }
            else
            {
                files++;
            }
        }

        var text = mode == PickerMode.Folder
            ? Count(folders, "folder")
            : $"{Count(folders, "folder")}, {Count(files, "file")}";
        if (result.FilteredOut > 0)
        {
            text += mode == PickerMode.Folder
                ? $" ({Count(result.FilteredOut, "file")} not shown)"
                : $" ({Count(result.FilteredOut, "other file")} not shown)";
        }

        return result.Entries.Count == 0 ? text + ". Nothing to open here." : text + ".";
    }

    private static string Count(int count, string noun) =>
        string.Create(CultureInfo.InvariantCulture, $"{count:N0} {noun}{(count == 1 ? string.Empty : "s")}");

    private void RefreshState()
    {
        if (_opening is null)
        {
            return;
        }

        var waited = _clock - _openingSince;
        var read = _progress?.Value ?? 0;
        _state.Text = waited < SlowSeconds
            ? $"Opening {_opening}…"
            : string.Create(CultureInfo.InvariantCulture,
                $"Still opening {_opening} ({read:N0} read so far, {waited:0} s). A network folder can take a while; B stops waiting.");
        _stateSettings.FontColor = waited < SlowSeconds ? UiStyle.Dim : UiStyle.Warning;
        _list.Waiting = waited >= 0.3;
    }

    private void ShowListState(string? problem)
    {
        _state.Text = problem ?? _summary;
        _stateSettings.FontColor = problem is null ? UiStyle.Dim : UiStyle.Bad;
    }

    // ---- Actions ------------------------------------------------------------------------------------

    private void Activate(int index)
    {
        if (_list.Items[index] is not { } item)
        {
            return;
        }

        if (_folder is null)
        {
            OpenFolder(item.Path!, null);
            return;
        }

        var path = Path.Combine(_folder, item.Name);
        if (item.Kind == ItemKind.Folder)
        {
            OpenFolder(path, null);
        }
        else if (_request.Mode == PickerMode.File)
        {
            Choose(path, _folder);
        }
    }

    private void Up()
    {
        if (_opening is not null)
        {
            // Stop waiting for a slow folder: the one on screen stays (or the top level, if nothing was shown yet).
            var abandoned = _opening;
            _generation++;
            _opening = null;
            _list.Waiting = false;
            if (_folder is null && _places.Count == 0)
            {
                ShowPlaces(null, $"Stopped waiting for {abandoned}.");
            }
            else
            {
                ShowListState(null);
            }

            return;
        }

        if (_folder is null)
        {
            Cancel();
            return;
        }

        var parent = PathInput.Parent(_folder);
        if (parent is null)
        {
            ShowPlaces(_folder, null);
        }
        else
        {
            OpenFolder(parent, PathInput.NameOf(_folder));
        }
    }

    private void TypePath()
    {
        var home = _context.HomeDir;
        var here = _folder;
        OnScreenKeyboard.Open(Layer, new KeyboardRequest(
            "Type a path",
            here ?? string.Empty,
            text =>
            {
                if (PathInput.Resolve(text, here, home).Path is { } path)
                {
                    OpenFolder(path, null);
                }
            },
            Placeholder: OperatingSystem.IsWindows() ? @"D:\ROMs or \\nas\roms" : "/home/me/ROMs",
            Subtitle: _request.Mode == PickerMode.Folder ? "A folder, or a network share (\\\\server\\share)" : "A folder, or the file itself",
            Validate: text => PathInput.Resolve(text, here, home).Problem));
    }

    private void UseThisFolder()
    {
        if (_folder is null)
        {
            ShowListState("Open a folder first, then use it.");
            return;
        }

        Choose(_folder, _folder);
    }

    private void Choose(string path, string folder)
    {
        if (_finished)
        {
            return;
        }

        _finished = true;
        var history = _context.History;
        history.Set(_request.Use, folder);
        _ = Task.Run(history.Save);
        Close();
        _request.Chosen(path);
    }

    private void Cancel()
    {
        if (_finished)
        {
            return;
        }

        _finished = true;
        Close();
        _request.Cancelled?.Invoke();
    }

    private string NameAt(int index) => _list.Items[index].Name;

    private static Button FooterButton(HBoxContainer buttons, string text, Action action)
    {
        var button = new Button { Text = text, CustomMinimumSize = new Vector2(170, 44), FocusMode = FocusModeEnum.All };
        button.Pressed += action;
        buttons.AddChild(button);
        return button;
    }

    // ---- The image preview ---------------------------------------------------------------------------

    private void OnSelectionChanged(int index)
    {
        if (_preview is null)
        {
            return;
        }

        var item = index >= 0 && index < _list.Count ? _list.Items[index] : null;
        _previewPath = _folder is not null && item is { Kind: ItemKind.File } ? Path.Combine(_folder, item.Name) : null;
        _previewDue = _clock + PreviewDelay;
    }

    /// <summary>Decodes and scales the image on a worker (never on the main thread), then shows it if it's still selected.</summary>
    private void LoadPreview(string? path)
    {
        var generation = ++_previewGeneration;
        if (path is null)
        {
            ShowPreview(null, string.Empty);
            return;
        }

        var decoder = _context.Decoder;
        _ = Task.Run(() =>
        {
            var texture = Thumbnails.Load(path, PreviewSide, decoder, out var info);
            _context.Queue.Post(() =>
            {
                if (generation == _previewGeneration && !_finished)
                {
                    ShowPreview(texture, info);
                }
                else
                {
                    texture?.Dispose();
                }
            });
        });
    }

    private void ShowPreview(ImageTexture? texture, string info)
    {
        if (_preview!.Texture is { } old)
        {
            _preview.Texture = null;
            old.Dispose();
        }

        _preview.Texture = texture;
        _previewInfo!.Text = info;
    }
}
