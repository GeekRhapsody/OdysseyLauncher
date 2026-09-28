using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using Godot;

namespace Launcher.App.Boot;

/// <summary>
/// Work for the main thread, posted from any thread and run within a per-frame time budget (A1 Platform glue, A3).
/// Results of background work reach nodes through here, not through plain <c>await</c> continuations: Godot's
/// SynchronizationContext runs every pending continuation each frame, with no budget.
/// </summary>
public sealed class MainThreadQueue
{
    /// <summary>The share of a 60 Hz frame queued work may take before the rest waits for the next frame.</summary>
    public const double DefaultBudgetMs = 3.0;

    private readonly ConcurrentQueue<Action> _queue = new();

    /// <summary>Thread-safe. The action runs on the main thread in a later frame.</summary>
    public void Post(Action action) => _queue.Enqueue(action);

    /// <summary>Main thread, once per frame: runs queued work until the queue is empty or the budget is spent.</summary>
    public void Drain(double budgetMs = DefaultBudgetMs)
    {
        if (_queue.IsEmpty)
        {
            return;
        }

        var start = Stopwatch.GetTimestamp();
        while (_queue.TryDequeue(out var action))
        {
            try
            {
                action();
            }
            catch (Exception e)
            {
                GD.PushError($"Main-thread work failed: {e}");
            }

            if (Stopwatch.GetElapsedTime(start).TotalMilliseconds >= budgetMs)
            {
                return;
            }
        }
    }
}
