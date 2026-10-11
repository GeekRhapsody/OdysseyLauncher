using System;
using System.Threading;
using Godot;
using Launcher.App.Boot;
using Launcher.Core.Media;

namespace Launcher.App.Grid;

/// <summary>
/// Plays a focused system card's video from its theme (A6 Card videos) into a texture: muted, and timed by the card's
/// focused clip, so that the picture keeps step with the model. The grid passes the clip's position each frame
/// (<see cref="Tick"/>); when it goes back (the clip looped), the video starts again from its first frame. A video
/// shorter than the clip holds its last frame until then; a longer one is cut there.
/// <para>
/// A thread of its own opens the file and decodes a few frames ahead, each into an <see cref="Image"/> of its own,
/// stamped with the loop it belongs to; the main thread uploads the frame due, if a new one is. Nothing in
/// <see cref="Tick"/> allocates.
/// </para>
/// </summary>
public sealed class CardVideo : IDisposable
{
    private const int Slots = 4;

    private readonly IVideoDecoder _decoder;
    private readonly string _path;
    // Never disposed: either side may still signal it after the other has finished with it (a small handle the GC frees).
    private readonly AutoResetEvent _wake = new(false);
    private readonly Image?[] _images = new Image?[Slots];
    private readonly long[] _times = new long[Slots];
    private readonly long[] _loops = new long[Slots];

    private volatile bool _stop;
    private ImageTexture? _texture;
    private long _durationTicks;
    private long _written;
    private long _read;
    private long _shown = -1;

    // The loop the clip is in, which the thread decodes for: it starts again from the first frame when this moves on.
    private long _loop;
    private double _lastPosition = -1;

    public CardVideo(IVideoDecoder decoder, string path)
    {
        _decoder = decoder;
        _path = path;
        var thread = new Thread(Run) { IsBackground = true, Name = "Card video" };
        thread.Start();
    }

    /// <summary>The picture, once the first frame is decoded; null until then, or if the video can't be read.</summary>
    public ImageTexture? Texture => Volatile.Read(ref _texture);

    /// <summary>The video's length in seconds; 0 until known, or if the file doesn't say.</summary>
    public double Duration => Volatile.Read(ref _durationTicks) / (double)TimeSpan.TicksPerSecond;

    /// <summary>Stops decoding. The thread lets its reader go itself, so the main thread never waits for it.</summary>
    public void Dispose()
    {
        _stop = true;
        _wake.Set();
    }

    /// <summary>Main thread, once a frame: <paramref name="position"/> is the time into the clip, in seconds.</summary>
    public void Tick(double position)
    {
        if (_stop || Texture is not { } texture)
        {
            return;
        }

        if (position < _lastPosition)
        {
            Volatile.Write(ref _loop, _loop + 1);    // the main thread is its only writer
            _wake.Set();
        }

        _lastPosition = position;

        // The latest frame that's due: an earlier loop's frames are all past, and are skipped without being shown.
        var written = Volatile.Read(ref _written);
        var now = (long)(position * TimeSpan.TicksPerSecond);
        var due = -1L;
        for (var i = _read; i < written; i++)
        {
            var slot = i % Slots;
            if (_loops[slot] > _loop || (_loops[slot] == _loop && _times[slot] > now))
            {
                break;
            }

            due = i;
        }

        if (due < 0)
        {
            return;
        }

        if (due != _shown && _loops[due % Slots] == _loop)
        {
            texture.Update(_images[due % Slots]!);
            _shown = due;
        }

        Volatile.Write(ref _read, due + 1);
        _wake.Set();
    }

    // ---- The decoding thread ------------------------------------------------------------------------

    private void Run()
    {
        // The thread calls into Godot (its images) for its whole run, so the app waits for it as it quits (GodotWork).
        if (!GodotWork.TryEnter())
        {
            return;
        }

        IVideoReader? video = null;
        try
        {
            video = _decoder.OpenVideo(_path, out var error);
            if (video is null)
            {
                GD.PushWarning($"Card video: {_path}: {error ?? "it can't be read"}");
                return;
            }

            Volatile.Write(ref _durationTicks, video.Duration.Ticks);
            var (width, height) = (video.Width, video.Height);
            var frame = new byte[width * height * 4];
            for (var i = 0; i < Slots; i++)
            {
                _images[i] = Image.CreateEmpty(width, height, false, Image.Format.Rgba8);
            }

            var loop = 0L;
            var ended = false;
            while (!_stop && !GodotWork.Quitting)
            {
                var wanted = Volatile.Read(ref _loop);
                if (wanted != loop)
                {
                    // The clip looped: from the first frame again (a reader that can't seek is opened again).
                    loop = wanted;
                    ended = false;
                    if (!video.Seek(TimeSpan.Zero))
                    {
                        video.Dispose();
                        video = _decoder.OpenVideo(_path, out error);
                        if (video is null)
                        {
                            GD.PushWarning($"Card video: {_path}: {error ?? "it can't be read again"}");
                            return;
                        }
                    }
                }

                if (ended || Volatile.Read(ref _written) - Volatile.Read(ref _read) >= Slots)
                {
                    _wake.WaitOne(20);
                    continue;
                }

                switch (video.ReadFrame(frame, out var time))
                {
                    case VideoFrameResult.Frame:
                        var slot = (int)(_written % Slots);
                        _images[slot]!.SetData(width, height, false, Image.Format.Rgba8, frame);
                        _times[slot] = time.Ticks;
                        _loops[slot] = loop;
                        if (Volatile.Read(ref _texture) is null)
                        {
                            // Made here: creating a texture on the main thread can stall it (A3).
                            Volatile.Write(ref _texture, ImageTexture.CreateFromImage(_images[slot]));
                        }

                        Volatile.Write(ref _written, _written + 1);
                        break;
                    case VideoFrameResult.Failed:
                        GD.PushWarning($"Card video: {_path}: {video.Error}");
                        return;
                    default:
                        // The end, or a change of size part way through: hold the last frame until the clip loops.
                        ended = true;
                        break;
                }
            }
        }
        catch (Exception e)
        {
            GD.PushError($"Card video: {_path}: {e.Message}");
        }
        finally
        {
            video?.Dispose();
            if (_stop || GodotWork.Quitting)
            {
                foreach (var image in _images)
                {
                    image?.Dispose();
                }

                Volatile.Read(ref _texture)?.Dispose();
            }

            GodotWork.Exit();
        }
    }
}
