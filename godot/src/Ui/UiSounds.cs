using Godot;
using Launcher.App.Boot;

namespace Launcher.App.Ui;

/// <summary>
/// The navigation sounds (2026-10-10): a tock when the focus moves to another system or game, and a whoosh when a system
/// is entered, while <c>[ui] navigation_sounds</c> is on (the default). The files are <c>res://sounds/</c>, made by
/// <c>tools/ui-sounds/make_sounds.py</c>; they're loaded on the thread pool (<see cref="LoadStreams"/>) and this node is
/// made in the warm-up, so nothing sounds before then. Both play on the master bus, which is muted while a game runs.
/// <para>
/// A held move repeats the tock up to every 35 ms, so it has voices to overlap rather than cutting itself off, and each
/// play's pitch varies by up to 3% (an <see cref="AudioStreamRandomizer"/>), so a long scroll doesn't drone. Playing
/// allocates nothing, and the setting is read at each play, so a change in the settings applies at once.
/// </para>
/// </summary>
public sealed partial class UiSounds : Node
{
    private const string Folder = "res://sounds/";
    private const int TockVoices = 4;
    private const float TockPitchRange = 1.03f;

    private readonly AppServices _services;
    private readonly AudioStreamPlayer _tock;
    private readonly AudioStreamPlayer _whoosh;
    private readonly bool _hasTock;
    private readonly bool _hasWhoosh;

    /// <param name="streams">From <see cref="LoadStreams"/>; a sound that didn't load stays silent.</param>
    public UiSounds(AppServices services, (AudioStream? Tock, AudioStream? Whoosh) streams)
    {
        Name = "UiSounds";
        _services = services;
        _tock = new AudioStreamPlayer { Name = "Tock", MaxPolyphony = TockVoices };
        if (streams.Tock is { } tock)
        {
            var varied = new AudioStreamRandomizer { RandomPitch = TockPitchRange };
            varied.AddStream(0, tock);
            _tock.Stream = varied;
            _hasTock = true;
        }

        _whoosh = new AudioStreamPlayer { Name = "Whoosh", Stream = streams.Whoosh };
        _hasWhoosh = streams.Whoosh is not null;
        AddChild(_tock);
        AddChild(_whoosh);
    }

    /// <summary>The two sounds' streams. Thread pool: loading them reads the files.</summary>
    public static (AudioStream? Tock, AudioStream? Whoosh) LoadStreams() =>
        (ResourceLoader.Load<AudioStream>(Folder + "nav_tock.wav"), ResourceLoader.Load<AudioStream>(Folder + "nav_whoosh.wav"));

    private bool On => _services.Config.Settings.Ui.NavigationSounds;

    /// <summary>The focus moved to another system or game. Main thread.</summary>
    public void Tock()
    {
        if (_hasTock && On)
        {
            _tock.Play();
        }
    }

    /// <summary>A system (or Favourites, or Recently played) is being entered. Main thread.</summary>
    public void Whoosh()
    {
        if (_hasWhoosh && On)
        {
            _whoosh.Play();
        }
    }
}
