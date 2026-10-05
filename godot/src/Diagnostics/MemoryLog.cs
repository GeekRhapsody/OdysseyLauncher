using System;
using System.Globalization;
using System.IO;
using System.Text;
using Godot;

namespace Launcher.App.Diagnostics;

/// <summary>
/// <c>--memory-log</c>: once a second, and at each phase change, appends the app's memory to a CSV: Godot's own video,
/// texture and buffer accounting, the working set, private bytes and the managed heap, with the wall-clock time (to
/// line up with the OS's GPU counters sampled outside the app) and what the app is doing. Runs while the tree is paused
/// and while a game runs (the main loop still iterates then; only drawing stops). Debug only: it allocates per sample.
/// </summary>
public partial class MemoryLog : Node
{
    private const ulong IntervalMs = 1000;

    private readonly StreamWriter _writer;
    private ulong _nextMs;
    private string _phase = "boot";

    public MemoryLog(string path)
    {
        Name = "MemoryLog";
        ProcessMode = ProcessModeEnum.Always;
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        _writer = new StreamWriter(path, append: false, new UTF8Encoding(false)) { AutoFlush = true };
        _writer.WriteLine("utc,ticks_ms,phase,godot_video_mem_mb,godot_texture_mem_mb,godot_buffer_mem_mb,working_set_mb,private_mb,managed_heap_mb");
    }

    /// <summary>What the app is doing from now on; writes a sample at once.</summary>
    public void Mark(string phase)
    {
        _phase = phase;
        Write();
    }

    public override void _Process(double delta)
    {
        if (Time.GetTicksMsec() >= _nextMs)
        {
            Write();
        }
    }

    public override void _ExitTree()
    {
        Write();
        _writer.Dispose();
    }

    private void Write()
    {
        _nextMs = Time.GetTicksMsec() + IntervalMs;
        using var process = System.Diagnostics.Process.GetCurrentProcess();
        process.Refresh();
        const double Mb = 1024.0 * 1024.0;
        _writer.WriteLine(string.Create(CultureInfo.InvariantCulture,
            $"{DateTime.UtcNow:O},{Time.GetTicksMsec()},{_phase},{Performance.GetMonitor(Performance.Monitor.RenderVideoMemUsed) / Mb:0.0},{Performance.GetMonitor(Performance.Monitor.RenderTextureMemUsed) / Mb:0.0},{Performance.GetMonitor(Performance.Monitor.RenderBufferMemUsed) / Mb:0.0},{process.WorkingSet64 / Mb:0.0},{process.PrivateMemorySize64 / Mb:0.0},{GC.GetTotalMemory(false) / Mb:0.0}"));
    }
}
