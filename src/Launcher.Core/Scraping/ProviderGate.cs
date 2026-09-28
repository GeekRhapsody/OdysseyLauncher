namespace Launcher.Core.Scraping;

/// <summary>Waits: <c>Task.Delay</c> by default, replaced in tests so backoff can be checked without waiting.</summary>
public delegate Task Delay(TimeSpan duration, CancellationToken cancellationToken);

/// <summary>
/// One provider's limits, shared by every request to it: at most <see cref="MaxConcurrency"/> requests in flight,
/// at most <see cref="PerSecond"/> starts a second and <see cref="PerMinute"/> a minute, and a pause after a rate
/// limit (a 429 or Retry-After) that every waiting request honours. The limits can change while it's in use:
/// ScreenScraper reports the account's with each response.
/// </summary>
public sealed class ProviderGate
{
    private readonly object _lock = new();
    private readonly Queue<TaskCompletionSource> _waiting = new();
    private readonly Queue<DateTimeOffset> _startsThisMinute = new();
    private readonly TimeProvider _clock;
    private readonly Delay _delay;
    private int _inFlight;
    private DateTimeOffset _lastStart = DateTimeOffset.MinValue;
    private DateTimeOffset _pausedUntil = DateTimeOffset.MinValue;
    private ProviderException? _closedBy;

    public ProviderGate(string name, int maxConcurrency, double? perSecond, int? perMinute, TimeProvider clock, Delay delay)
    {
        Name = name;
        MaxConcurrency = Math.Max(1, maxConcurrency);
        PerSecond = perSecond;
        PerMinute = perMinute;
        _clock = clock;
        _delay = delay;
    }

    public string Name { get; }

    public int MaxConcurrency { get; private set; }

    public double? PerSecond { get; private set; }

    public int? PerMinute { get; private set; }

    /// <summary>The most requests that were in flight at once: tests check the limit held.</summary>
    public int PeakInFlight { get; private set; }

    public void SetLimits(int maxConcurrency, int? perMinute)
    {
        lock (_lock)
        {
            MaxConcurrency = Math.Max(1, maxConcurrency);
            PerMinute = perMinute is > 0 ? perMinute : null;
            ReleaseWaiters();
        }
    }

    /// <summary>
    /// Refuses every request with <paramref name="reason"/> until its <see cref="ProviderException.Until"/> (forever when
    /// null): a used-up quota or refused credentials, so requests already waiting don't go out and fail too.
    /// </summary>
    public void Close(ProviderException reason)
    {
        lock (_lock)
        {
            _closedBy = reason;
        }
    }

    /// <summary>Holds every request until <paramref name="until"/> (never shortens a longer pause).</summary>
    public void PauseUntil(DateTimeOffset until)
    {
        lock (_lock)
        {
            if (until > _pausedUntil)
            {
                _pausedUntil = until;
            }
        }
    }

    /// <summary>Waits for a slot and for the rate limits; dispose the result when the request is done.</summary>
    public async Task<IDisposable> EnterAsync(CancellationToken cancellationToken)
    {
        while (true)
        {
            TaskCompletionSource? wait = null;
            lock (_lock)
            {
                if (_inFlight < MaxConcurrency)
                {
                    _inFlight++;
                    PeakInFlight = Math.Max(PeakInFlight, _inFlight);
                }
                else
                {
                    wait = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                    _waiting.Enqueue(wait);
                }
            }

            if (wait is null)
            {
                break;
            }

            using (cancellationToken.Register(() => wait.TrySetCanceled(cancellationToken)))
            {
                await wait.Task.ConfigureAwait(false);
            }
        }

        try
        {
            ThrowIfClosed();
            await WaitForRateAsync(cancellationToken).ConfigureAwait(false);
        }
        catch
        {
            Exit();
            throw;
        }

        return new Slot(this);
    }

    private void ThrowIfClosed()
    {
        ProviderException? closed;
        lock (_lock)
        {
            closed = _closedBy;
            if (closed?.Until is { } until && until <= _clock.GetUtcNow())
            {
                _closedBy = closed = null;
            }
        }

        if (closed is not null)
        {
            throw new ProviderException(closed.Provider, closed.Failure, closed.Message, closed.Until);
        }
    }

    private async Task WaitForRateAsync(CancellationToken cancellationToken)
    {
        while (true)
        {
            TimeSpan wait;
            lock (_lock)
            {
                var now = _clock.GetUtcNow();
                wait = _pausedUntil > now ? _pausedUntil - now : TimeSpan.Zero;
                if (PerSecond is { } perSecond && _lastStart != DateTimeOffset.MinValue)
                {
                    var next = _lastStart + TimeSpan.FromSeconds(1 / perSecond);
                    if (next - now > wait)
                    {
                        wait = next - now;
                    }
                }

                while (_startsThisMinute.Count > 0 && now - _startsThisMinute.Peek() >= TimeSpan.FromMinutes(1))
                {
                    _startsThisMinute.Dequeue();
                }

                if (PerMinute is { } perMinute && _startsThisMinute.Count >= perMinute)
                {
                    var next = _startsThisMinute.Peek() + TimeSpan.FromMinutes(1);
                    if (next - now > wait)
                    {
                        wait = next - now;
                    }
                }

                if (wait <= TimeSpan.Zero)
                {
                    _lastStart = now;
                    _startsThisMinute.Enqueue(now);
                    return;
                }
            }

            await _delay(wait, cancellationToken).ConfigureAwait(false);
        }
    }

    private void Exit()
    {
        lock (_lock)
        {
            _inFlight--;
            ReleaseWaiters();
        }
    }

    private void ReleaseWaiters()
    {
        // Wake as many waiters as there are free slots; each re-checks under the lock.
        // A cancelled waiter doesn't use up a slot.
        var free = MaxConcurrency - _inFlight;
        while (free > 0 && _waiting.TryDequeue(out var next))
        {
            if (next.TrySetResult())
            {
                free--;
            }
        }
    }

    private sealed class Slot(ProviderGate gate) : IDisposable
    {
        private int _disposed;

        public void Dispose()
        {
            if (Interlocked.Exchange(ref _disposed, 1) == 0)
            {
                gate.Exit();
            }
        }
    }
}
