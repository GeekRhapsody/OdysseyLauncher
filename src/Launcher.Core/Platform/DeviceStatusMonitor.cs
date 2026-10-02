using System.Net.NetworkInformation;

namespace Launcher.Core.Platform;

/// <summary>
/// Polls an <see cref="IDeviceStatus"/> on the thread pool for the status indicators: every
/// <see cref="DefaultInterval"/>, and at once when the system says an address changed (a cable pulled, Wi-Fi joined).
/// <see cref="Changed"/> is raised only when the snapshot differs from the last one, so a Wi-Fi signal moving within
/// its bar, or a battery between whole percents, costs nothing downstream. Paused while a game runs.
/// </summary>
public sealed class DeviceStatusMonitor : IDisposable
{
    public static readonly TimeSpan DefaultInterval = TimeSpan.FromSeconds(10);

    private readonly IDeviceStatus _source;
    private readonly TimeSpan _interval;
    private readonly Timer _timer;
    private readonly object _polling = new();
    private readonly object _gate = new();
    private DeviceStatus? _last;
    private bool _started;
    private bool _paused;
    private bool _disposed;

    public DeviceStatusMonitor(IDeviceStatus source, TimeSpan? interval = null)
    {
        ArgumentNullException.ThrowIfNull(source);
        _source = source;
        _interval = interval ?? DefaultInterval;
        _timer = new Timer(_ => PollNow(), null, Timeout.Infinite, Timeout.Infinite);
    }

    /// <summary>Raised on a worker thread with the new snapshot, only when it differs from the last.</summary>
    public event Action<DeviceStatus>? Changed;

    /// <summary>The last snapshot read, or null before the first poll.</summary>
    public DeviceStatus? Current
    {
        get
        {
            lock (_gate)
            {
                return _last;
            }
        }
    }

    /// <summary>Polls at once, then every interval.</summary>
    public void Start()
    {
        lock (_gate)
        {
            if (_started || _disposed)
            {
                return;
            }

            _started = true;
            NetworkChange.NetworkAddressChanged += OnAddressChanged;
            if (!_paused)
            {
                _timer.Change(TimeSpan.Zero, _interval);
            }
        }
    }

    /// <summary>Stops polling (while a game runs).</summary>
    public void Pause()
    {
        lock (_gate)
        {
            _paused = true;
            if (!_disposed)
            {
                _timer.Change(Timeout.Infinite, Timeout.Infinite);
            }
        }
    }

    /// <summary>Polls at once, then every interval again.</summary>
    public void Resume()
    {
        lock (_gate)
        {
            _paused = false;
            if (_started && !_disposed)
            {
                _timer.Change(TimeSpan.Zero, _interval);
            }
        }
    }

    /// <summary>Reads the state once, unless paused or already reading, and raises <see cref="Changed"/> if it differs.</summary>
    internal void PollNow()
    {
        if (!Monitor.TryEnter(_polling))
        {
            return;
        }

        try
        {
            lock (_gate)
            {
                if (_paused || _disposed)
                {
                    return;
                }
            }

            var status = new DeviceStatus(Read(_source.ReadBattery, BatteryState.None), Read(_source.ReadNetwork, NetworkState.Unknown));
            lock (_gate)
            {
                if (_last == status)
                {
                    return;
                }

                _last = status;
            }

            Changed?.Invoke(status);
        }
        finally
        {
            Monitor.Exit(_polling);
        }
    }

    /// <summary>A state that can't be read is shown as unknown: the indicators never take the app down.</summary>
    private static T Read<T>(Func<T> read, T fallback)
    {
        try
        {
            return read();
        }
        catch (Exception)
        {
            return fallback;
        }
    }

    private void OnAddressChanged(object? sender, EventArgs e)
    {
        lock (_gate)
        {
            if (!_paused && !_disposed)
            {
                _timer.Change(TimeSpan.Zero, _interval);
            }
        }
    }

    public void Dispose()
    {
        lock (_gate)
        {
            if (_disposed)
            {
                return;
            }

            _disposed = true;
            if (_started)
            {
                NetworkChange.NetworkAddressChanged -= OnAddressChanged;
            }
        }

        _timer.Dispose();

        // After any poll still reading, which may be using the source's handles.
        lock (_polling)
        {
            (_source as IDisposable)?.Dispose();
        }
    }
}
