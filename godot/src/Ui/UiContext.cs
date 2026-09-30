using System;
using System.Threading;
using System.Threading.Tasks;
using Launcher.App.Boot;
using Launcher.Core.Files;
using Launcher.Core.Media;
using Launcher.Core.Platform;

namespace Launcher.App.Ui;

/// <summary>What the shared UI components need from the app (M7): the layer, the main-thread queue, and the file system.</summary>
public sealed class UiContext
{
    private readonly PickerHistory _unsaved = PickerHistory.InMemory();
    private PickerHistory? _history;

    public UiContext(UiLayer layer, MainThreadQueue queue, IFileLocations locations, string homeDir, string dataDir, Func<string> romRoot, IImageDecoder? decoder)
    {
        Layer = layer;
        Queue = queue;
        Locations = locations;
        HomeDir = homeDir;
        RomRoot = romRoot;
        Decoder = decoder;

        // The pickers' remembered folders are read off the main thread; until then they start at the top.
        _ = Task.Run(() => Volatile.Write(ref _history, PickerHistory.Load(dataDir)));
    }

    public UiLayer Layer { get; }

    public MainThreadQueue Queue { get; }

    public IFileLocations Locations { get; }

    public string HomeDir { get; }

    /// <summary>The configured ROM root, for the pickers' quick-access list (it changes when the user sets it).</summary>
    public Func<string> RomRoot { get; }

    /// <summary>Decodes and scales the image picker's thumbnails (WIC on Windows); null elsewhere, where Godot decodes them.</summary>
    public IImageDecoder? Decoder { get; }

    /// <summary>Each picker use's last folder; saved when a pick is made.</summary>
    public PickerHistory History => Volatile.Read(ref _history) ?? _unsaved;
}
