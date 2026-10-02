using System;
using System.Threading;
using Godot;
using Launcher.Core.Media;

namespace Launcher.App.Ui;

/// <summary>
/// Plays a game's video (an MP4, through Core's <see cref="IVideoDecoder"/>: Godot plays only Ogg Theora) into a
/// texture, with its sound through an <see cref="AudioStreamGenerator"/>. A thread of its own decodes a few frames
/// ahead, each into an <see cref="Image"/> of its own, and about a second of sound; the main thread, once a frame
/// (<see cref="Tick"/>), feeds the generator, works out the time from the sound actually played (or the frame time
/// without sound), and uploads the frame due, if a new one is. Nothing in <see cref="Tick"/> allocates.
/// </summary>
public sealed class VideoPlayback : IDisposable
{
    private const int Slots = 4;
    private const int AudioBlockFrames = 2048;
    private const float GeneratorSeconds = 0.25f;

    private readonly IVideoDecoder _decoder;
    private readonly string _path;
    private readonly AudioStreamPlayer _player;
    // Never disposed: either side may still signal it after the other has finished with it (a small handle the GC frees).
    private readonly AutoResetEvent _wake = new(false);
    private readonly Image?[] _images = new Image?[Slots];
    private readonly long[] _times = new long[Slots];

    private volatile bool _stop;
    private volatile bool _videoEnded;
    private volatile bool _audioEnded;
    private string? _error;
    private ImageTexture? _texture;
    private long _written;
    private long _read;
    private long _shown = -1;

    // The sound: interleaved stereo, in a ring the thread writes and Tick reads, counted in frames.
    private float[] _ring = [];
    private volatile int _rate;
    private long _ringWritten;
    private long _ringRead;
    private AudioStreamGeneratorPlayback? _generator;
    private int _capacity;
    private long _pushed;
    private bool _audioDrained;

    private double _clock;
    private long _durationTicks;
    private bool _paused;

    /// <param name="player">Plays the sound; the playback gives it a generator when the video has sound.</param>
    public VideoPlayback(IVideoDecoder decoder, string path, AudioStreamPlayer player)
    {
        _decoder = decoder;
        _path = path;
        _player = player;
        var thread = new Thread(Run) { IsBackground = true, Name = "Video playback" };
        thread.Start();
    }

    /// <summary>The picture, once the first frame is decoded; null until then (or if it can't be).</summary>
    public ImageTexture? Texture => Volatile.Read(ref _texture);

    /// <summary>The picture's width over its height, with its pixels' shape; 0 until known.</summary>
    public float Aspect { get; private set; }

    /// <summary>Why it can't play, for the user; null while it can.</summary>
    public string? Error => Volatile.Read(ref _error);

    /// <summary>True once the last frame has shown and the sound has played out.</summary>
    public bool Ended { get; private set; }

    public TimeSpan Position => TimeSpan.FromSeconds(_clock);

    /// <summary>The video's length; zero until known, or if the file doesn't say.</summary>
    public TimeSpan Duration => TimeSpan.FromTicks(Volatile.Read(ref _durationTicks));

    public bool Paused
    {
        get => _paused;
        set
        {
            _paused = value;
            if (_generator is not null)
            {
                _player.StreamPaused = value;
            }
        }
    }

    /// <summary>Stops decoding. The thread lets its readers go itself, so the main thread never waits for it.</summary>
    public void Dispose()
    {
        _stop = true;
        _wake.Set();
        if (_generator is not null)
        {
            _player.Stop();
            _generator = null;
        }
    }

    /// <summary>Main thread, once a frame: the sound fed, the time moved on, and the frame due uploaded.</summary>
    public void Tick(double delta)
    {
        if (_stop || Ended || Texture is not { } texture)
        {
            return;
        }

        if (_rate > 0 && _generator is null && !_audioDrained)
        {
            StartSound();
        }

        var audioTime = -1.0;
        if (_generator is { } generator)
        {
            if (!_paused)
            {
                FeedSound(generator);
            }

            var buffered = Math.Max(0, _capacity - generator.GetFramesAvailable());
            if (_audioEnded && Volatile.Read(ref _ringWritten) == _ringRead && buffered == 0)
            {
                // The sound has played out (it may be shorter than the picture): the frame time carries on.
                _audioDrained = true;
                _player.Stop();
                _generator = null;
            }
            else
            {
                audioTime = (double)(_pushed - buffered) / _rate - AudioServer.GetOutputLatency();
            }
        }

        if (audioTime >= 0)
        {
            _clock = Math.Max(_clock, audioTime);
        }
        else if (!_paused && _generator is null)
        {
            _clock += delta;
        }

        // The latest frame that's due; the ones before it are skipped.
        var written = Volatile.Read(ref _written);
        var due = -1L;
        var clockTicks = (long)(_clock * TimeSpan.TicksPerSecond);
        for (var i = _read; i < written && _times[i % Slots] <= clockTicks; i++)
        {
            due = i;
        }

        if (due >= 0)
        {
            if (due != _shown)
            {
                texture.Update(_images[due % Slots]!);
                _shown = due;
            }

            Volatile.Write(ref _read, due + 1);
            _wake.Set();
        }

        Ended = _videoEnded && Volatile.Read(ref _read) == Volatile.Read(ref _written) && (_rate == 0 || _audioDrained);
    }

    private void StartSound()
    {
        _player.Stream = new AudioStreamGenerator
        {
            MixRateMode = AudioStreamGenerator.AudioStreamGeneratorMixRate.Custom,
            MixRate = _rate,
            BufferLength = GeneratorSeconds,
        };
        _player.Play();
        _generator = _player.GetStreamPlayback() as AudioStreamGeneratorPlayback;
        if (_generator is null)
        {
            _audioDrained = true;
            return;
        }

        _capacity = _generator.GetFramesAvailable();
        _player.StreamPaused = _paused;
    }

    private void FeedSound(AudioStreamGeneratorPlayback generator)
    {
        var available = Volatile.Read(ref _ringWritten) - _ringRead;
        var count = Math.Min(available, generator.GetFramesAvailable());
        if (count <= 0)
        {
            return;
        }

        var frames = _ring.Length / 2;
        for (var i = 0; i < count; i++)
        {
            var at = (int)((_ringRead + i) % frames) * 2;
            generator.PushFrame(new Vector2(_ring[at], _ring[at + 1]));
        }

        _pushed += count;
        Volatile.Write(ref _ringRead, _ringRead + count);
        _wake.Set();
    }

    // ---- The decoding thread ------------------------------------------------------------------------

    private void Run()
    {
        IVideoReader? video = null;
        IAudioReader? audio = null;
        try
        {
            video = _decoder.OpenVideo(_path, out var error);
            if (video is null)
            {
                Volatile.Write(ref _error, error ?? "it can't be read");
                return;
            }

            Volatile.Write(ref _durationTicks, video.Duration.Ticks);
            audio = _decoder.OpenAudio(_path, out _);
            var (width, height) = (video.Width, video.Height);
            var frame = new byte[width * height * 4];
            for (var i = 0; i < Slots; i++)
            {
                _images[i] = Image.CreateEmpty(width, height, false, Image.Format.Rgba8);
            }

            if (audio is not null)
            {
                _ring = new float[audio.SampleRate * 2];
            }

            float[] block = audio is null ? [] : new float[AudioBlockFrames * audio.Channels];
            var first = true;
            while (!_stop)
            {
                var progressed = false;
                if (!_videoEnded && Volatile.Read(ref _written) - Volatile.Read(ref _read) < Slots)
                {
                    progressed = true;
                    switch (video.ReadFrame(frame, out var time))
                    {
                        case VideoFrameResult.Frame:
                            var slot = (int)(_written % Slots);
                            _images[slot]!.SetData(width, height, false, Image.Format.Rgba8, frame);
                            _times[slot] = time.Ticks;
                            if (first)
                            {
                                // Made here: creating a texture on the main thread can stall it (A3).
                                first = false;
                                Aspect = (float)(width * video.PixelAspect / height);
                                _rate = audio?.SampleRate ?? 0;
                                Volatile.Write(ref _texture, ImageTexture.CreateFromImage(_images[slot]));
                            }

                            Volatile.Write(ref _written, _written + 1);
                            break;
                        case VideoFrameResult.Resized:
                            GD.PushWarning($"Video: {_path} changed size part way through, so it stops there.");
                            _videoEnded = true;
                            break;
                        case VideoFrameResult.Failed:
                            GD.PushWarning($"Video: {_path}: {video.Error}");
                            if (first)
                            {
                                Volatile.Write(ref _error, video.Error);
                            }

                            _videoEnded = true;
                            break;
                        default:
                            _videoEnded = true;
                            break;
                    }
                }

                if (audio is not null && !_audioEnded && !first && FreeFrames() >= AudioBlockFrames)
                {
                    progressed = true;
                    ReadSound(audio, block);
                }

                if (!progressed)
                {
                    _wake.WaitOne(20);
                }
            }
        }
        catch (Exception e)
        {
            GD.PushError($"Video: {_path}: {e.Message}");
            Volatile.Write(ref _error, e.Message);
        }
        finally
        {
            _audioEnded = _videoEnded = true;
            audio?.Dispose();
            video?.Dispose();
            if (_stop)
            {
                foreach (var image in _images)
                {
                    image?.Dispose();
                }

                Volatile.Read(ref _texture)?.Dispose();
            }
        }
    }

    private long FreeFrames() => _ring.Length / 2 - (_ringWritten - Volatile.Read(ref _ringRead));

    /// <summary>One block of sound into the ring, as stereo: mono doubled, more channels than two keep the front pair.</summary>
    private void ReadSound(IAudioReader audio, float[] block)
    {
        var read = audio.Read(block);
        if (read <= 0)
        {
            if (read < 0)
            {
                GD.PushWarning($"Video: {_path}'s sound: {audio.Error}");
            }

            _audioEnded = true;
            return;
        }

        var channels = audio.Channels;
        var frames = _ring.Length / 2;
        var count = read / channels;
        for (var i = 0; i < count; i++)
        {
            var at = (int)((_ringWritten + i) % frames) * 2;
            var left = block[i * channels];
            _ring[at] = left;
            _ring[at + 1] = channels > 1 ? block[i * channels + 1] : left;
        }

        Volatile.Write(ref _ringWritten, _ringWritten + count);
    }
}
