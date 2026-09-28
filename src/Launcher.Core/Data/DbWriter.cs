using System.Collections.Concurrent;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Data;

/// <summary>
/// The one thread that writes. Microsoft.Data.Sqlite's async API is synchronous, so every write runs as a
/// job on this dedicated thread, on one connection, and callers await a task (ARCHITECTURE.md A1).
/// Continuations never run on the writer thread.
/// </summary>
internal sealed class DbWriter : IDisposable
{
    private readonly BlockingCollection<Action> _jobs = new();
    private readonly Thread _thread;
    private readonly Func<SqliteConnection> _connect;
    private SqliteConnection? _connection;

    public DbWriter(Func<SqliteConnection> connect, string name)
    {
        _connect = connect;
        _thread = new Thread(Loop) { IsBackground = true, Name = name };
        _thread.Start();
    }

    public Task<T> RunAsync<T>(Func<SqliteConnection, T> work, CancellationToken cancellationToken)
    {
        var completion = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (cancellationToken.IsCancellationRequested)
        {
            completion.SetCanceled(cancellationToken);
            return completion.Task;
        }

        _jobs.Add(() =>
        {
            if (cancellationToken.IsCancellationRequested)
            {
                completion.TrySetCanceled(cancellationToken);
                return;
            }

            try
            {
                _connection ??= _connect();
                completion.TrySetResult(work(_connection));
            }
            catch (OperationCanceledException e)
            {
                completion.TrySetCanceled(e.CancellationToken);
            }
            catch (Exception e)
            {
                completion.TrySetException(e);
            }
        });
        return completion.Task;
    }

    /// <summary>Runs <paramref name="work"/> with the writer's connection closed, e.g. to replace the DB file.</summary>
    public Task RunDisconnectedAsync(Action work, CancellationToken cancellationToken)
    {
        return RunAsync<bool>(
            _ =>
            {
                _connection!.Dispose();
                _connection = null;
                work();
                return true;
            },
            cancellationToken);
    }

    public void Dispose()
    {
        _jobs.CompleteAdding();
        _thread.Join();
        _jobs.Dispose();
    }

    private void Loop()
    {
        foreach (var job in _jobs.GetConsumingEnumerable())
        {
            job();
        }

        _connection?.Dispose();
        _connection = null;
    }
}

/// <summary>
/// Read connections for the thread pool. Each one has <c>userdata.db</c> ATTACHed once, when it's opened.
/// <see cref="Exclusive"/> waits for running reads, closes every connection and holds new reads back,
/// so the library file can be swapped.
/// </summary>
internal sealed class ReaderPool(Func<SqliteConnection> connect) : IDisposable
{
    private readonly ConcurrentBag<SqliteConnection> _idle = [];
    private readonly ReaderWriterLockSlim _gate = new(LockRecursionPolicy.NoRecursion);

    public Task<T> RunAsync<T>(Func<SqliteConnection, T> work, CancellationToken cancellationToken) =>
        Task.Run(() => Run(work), cancellationToken);

    public T Run<T>(Func<SqliteConnection, T> work)
    {
        _gate.EnterReadLock();
        try
        {
            if (!_idle.TryTake(out var connection))
            {
                connection = connect();
            }

            try
            {
                return work(connection);
            }
            finally
            {
                _idle.Add(connection);
            }
        }
        finally
        {
            _gate.ExitReadLock();
        }
    }

    public void Exclusive(Action action)
    {
        _gate.EnterWriteLock();
        try
        {
            CloseIdle();
            action();
        }
        finally
        {
            _gate.ExitWriteLock();
        }
    }

    public void Dispose()
    {
        CloseIdle();
        _gate.Dispose();
    }

    private void CloseIdle()
    {
        while (_idle.TryTake(out var connection))
        {
            connection.Dispose();
        }
    }
}
