using System;
using System.Collections.Generic;
using System.Globalization;
using System.Threading;
using Launcher.App.Boot;

namespace Launcher.App.Ui;

public enum JobState
{
    Running,
    Finished,
    Failed,
    Cancelled,
}

/// <summary>
/// A long operation the user can watch and cancel (M7): a rescan or a scrape. Its progress is written from worker
/// threads (the library's and scrape service's events) and read on the main thread; a change schedules one refresh
/// at most, however many events arrive in a frame.
/// </summary>
public sealed class BackgroundJob
{
    private readonly BackgroundJobs _owner;
    private readonly Action? _cancel;
    private int _done;
    private int _total;
    private int _failed;
    private string? _note;

    internal BackgroundJob(BackgroundJobs owner, int id, string kind, string title, Action? cancel)
    {
        _owner = owner;
        Id = id;
        Kind = kind;
        Title = title;
        _cancel = cancel;
    }

    public int Id { get; }

    /// <summary>"scan" or "scrape".</summary>
    public string Kind { get; }

    public string Title { get; }

    public int Done => Volatile.Read(ref _done);

    public int Total => Volatile.Read(ref _total);

    public int Failed => Volatile.Read(ref _failed);

    /// <summary>What the job is doing now, or something the user should know (a provider skipped).</summary>
    public string? Note => Volatile.Read(ref _note);

    /// <summary>What the numbers count: "systems", "games".</summary>
    public string Unit { get; init; } = "items";

    public JobState State { get; internal set; }

    /// <summary>How it ended, written for the user; null while it runs.</summary>
    public string? Outcome { get; internal set; }

    public bool CanCancel => _cancel is not null && State == JobState.Running && !Cancelling;

    public bool Cancelling { get; private set; }

    internal double EndedAt { get; set; }

    /// <summary>0 to 1; 0 while the total isn't known.</summary>
    public double Fraction => Total > 0 ? Math.Clamp((double)Done / Total, 0, 1) : 0;

    /// <summary>"412 of 3,000 games, 3 failed", or the note.</summary>
    public string Describe()
    {
        if (State != JobState.Running)
        {
            return Outcome ?? string.Empty;
        }

        if (Cancelling)
        {
            return "Stopping…";
        }

        var total = Total;
        var text = total > 0
            ? string.Create(CultureInfo.InvariantCulture, $"{Done:N0} of {total:N0} {Unit}")
            : "Starting…";
        if (Failed > 0)
        {
            text += string.Create(CultureInfo.InvariantCulture, $", {Failed:N0} failed");
        }

        return text;
    }

    /// <summary>Any thread.</summary>
    public void Report(int done, int total, int failed = 0)
    {
        Volatile.Write(ref _done, done);
        Volatile.Write(ref _total, total);
        Volatile.Write(ref _failed, failed);
        _owner.MarkChanged();
    }

    /// <summary>Any thread.</summary>
    public void SetNote(string? note)
    {
        Volatile.Write(ref _note, note);
        _owner.MarkChanged();
    }

    /// <summary>Main thread.</summary>
    public void Cancel()
    {
        if (!CanCancel)
        {
            return;
        }

        Cancelling = true;
        _cancel!();
        _owner.MarkChanged();
    }
}

/// <summary>The jobs running now, and the ones that just ended (kept a few seconds so their outcome can be read).</summary>
public sealed class BackgroundJobs(MainThreadQueue queue)
{
    public const double KeepEndedSeconds = 8;

    private readonly List<BackgroundJob> _jobs = [];
    private int _nextId;
    private int _refreshPending;
    private double _clock;

    /// <summary>Main thread: a job started, progressed or ended.</summary>
    public event Action? Changed;

    public IReadOnlyList<BackgroundJob> Jobs => _jobs;

    /// <summary>Main thread.</summary>
    public BackgroundJob Start(string kind, string title, string unit, Action? cancel)
    {
        var job = new BackgroundJob(this, ++_nextId, kind, title, cancel) { Unit = unit };
        _jobs.Add(job);
        Changed?.Invoke();
        return job;
    }

    /// <summary>Main thread.</summary>
    public void End(BackgroundJob job, JobState state, string outcome)
    {
        job.State = state;
        job.Outcome = outcome;
        job.EndedAt = _clock;
        Changed?.Invoke();
    }

    public BackgroundJob? Running(string kind)
    {
        foreach (var job in _jobs)
        {
            if (job.Kind == kind && job.State == JobState.Running)
            {
                return job;
            }
        }

        return null;
    }

    /// <summary>Main thread, once a frame: forgets jobs that ended a while ago.</summary>
    public void Tick(double delta)
    {
        _clock += delta;
        for (var i = _jobs.Count - 1; i >= 0; i--)
        {
            if (_jobs[i].State != JobState.Running && _clock - _jobs[i].EndedAt > KeepEndedSeconds)
            {
                _jobs.RemoveAt(i);
                Changed?.Invoke();
            }
        }
    }

    /// <summary>Any thread: one refresh on the main thread, however many changes come before it.</summary>
    internal void MarkChanged()
    {
        if (Interlocked.Exchange(ref _refreshPending, 1) == 0)
        {
            queue.Post(() =>
            {
                Volatile.Write(ref _refreshPending, 0);
                Changed?.Invoke();
            });
        }
    }
}
