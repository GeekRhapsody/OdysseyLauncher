using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Text.Json;

namespace Launcher.FakeEmulator;

/// <summary>
/// A stand-in emulator for the launch tests. Its own options can sit anywhere among the arguments, and are logged
/// with the rest:
/// <list type="bullet">
/// <item><c>--fake-log=&lt;path&gt;</c>: write the arguments, working folder and raw command line as UTF-8 JSON,
/// before anything else.</item>
/// <item><c>--fake-sleep=&lt;ms&gt;</c>: wait before exiting.</item>
/// <item><c>--fake-spawn=&lt;ms&gt;</c>: start a copy of itself that sleeps that long, then exit at once without
/// waiting for it, as a stub launcher does. With <c>--fake-log</c>, the copy logs to the same path plus ".child".</item>
/// <item><c>--fake-start=&lt;program&gt;</c>: start that program with every argument after a literal <c>--</c>, then
/// exit at once: a stub launcher in front of a real emulator, for the manual focus test.</item>
/// <item><c>--fake-exit=&lt;code&gt;</c>: the exit code (default 0).</item>
/// </list>
/// Nothing after <c>--</c> is read as an option.
/// </summary>
public static class Program
{
    public static int Main(string[] args)
    {
        string? log = null;
        var sleepMs = 0;
        int? spawnMs = null;
        string? start = null;
        var exitCode = 0;
        var separator = Array.IndexOf(args, "--");
        var options = separator < 0 ? args : args[..separator];
        foreach (var arg in options)
        {
            if (Option(arg, "--fake-start=") is { } program)
            {
                start = program;
            }
            else if (Option(arg, "--fake-log=") is { } path)
            {
                log = path;
            }
            else if (Option(arg, "--fake-sleep=") is { } sleep)
            {
                sleepMs = int.Parse(sleep, CultureInfo.InvariantCulture);
            }
            else if (Option(arg, "--fake-spawn=") is { } spawn)
            {
                spawnMs = int.Parse(spawn, CultureInfo.InvariantCulture);
            }
            else if (Option(arg, "--fake-exit=") is { } code)
            {
                exitCode = int.Parse(code, CultureInfo.InvariantCulture);
            }
        }

        if (log is not null)
        {
            WriteLog(log, args);
        }

        if (spawnMs is { } childSleep)
        {
            var child = new ProcessStartInfo(Environment.ProcessPath!) { UseShellExecute = false };
            child.ArgumentList.Add($"--fake-sleep={childSleep.ToString(CultureInfo.InvariantCulture)}");
            if (log is not null)
            {
                child.ArgumentList.Add($"--fake-log={log}.child");
            }

            using var process = Process.Start(child);
        }

        if (start is not null)
        {
            var real = new ProcessStartInfo(start) { UseShellExecute = false, WorkingDirectory = Path.GetDirectoryName(start) };
            foreach (var arg in separator < 0 ? [] : args[(separator + 1)..])
            {
                real.ArgumentList.Add(arg);
            }

            using var process = Process.Start(real);
        }

        if (sleepMs > 0)
        {
            Thread.Sleep(sleepMs);
        }

        return exitCode;
    }

    private static string? Option(string arg, string prefix) =>
        arg.StartsWith(prefix, StringComparison.Ordinal) ? arg[prefix.Length..] : null;

    /// <summary>Written to a temporary file and moved into place, so a reader never sees half a log.</summary>
    private static void WriteLog(string path, string[] args)
    {
        var json = JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["args"] = args,
            ["cwd"] = Environment.CurrentDirectory,
            ["commandLine"] = Environment.CommandLine,
            ["processId"] = Environment.ProcessId,
        });
        var temp = path + ".tmp";
        File.WriteAllText(temp, json, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
        File.Move(temp, path, overwrite: true);
    }
}
