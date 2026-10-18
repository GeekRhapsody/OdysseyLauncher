using System.Diagnostics;
using System.Globalization;
using System.Text;

namespace Launcher.Updater;

/// <summary>
/// OdysseyUpdater.exe: installs a staged update once the launcher has quit (docs/ARCHITECTURE.md A1, "Updates"). The
/// launcher copies it into the staging folder (so it never runs from a file it replaces), starts it and quits. It:
/// <list type="number">
/// <item>waits for the launcher's process to end (a minute at most; otherwise nothing is changed);</item>
/// <item>for each file and folder in the package, renames the installed one of that name into the backup folder, then
/// the new one into its place (renames only, all within the launcher's folder, so none is left half done); anything
/// else in the launcher's folder (portable.txt, userdata, override.cfg) stays;</item>
/// <item>if a rename fails (each is tried <c>--attempts</c> times, half a second apart, as an antivirus scanner or the
/// indexer can hold a file a moment after the launcher quits), renames back everything it moved, so the old version is
/// whole again;</item>
/// <item>starts the launcher (the new version, or the old one after a failure) with the arguments after <c>--</c>;</item>
/// <item>deletes the staging folder but itself (the launcher deletes the rest at its next check), unless something
/// couldn't be put back: then the old files wait in the backup folder, with <c>incomplete.txt</c>, and the launcher
/// leaves the folder alone.</item>
/// </list>
/// Every step is logged to <c>--log</c>. Exit code 0 when installed, 1 when not, 2 for bad arguments.
/// </summary>
public static class Program
{
    public const string IncompleteMarker = "incomplete.txt";

    public static int Main(string[] args)
    {
        if (!Options.TryParse(args, out var options, out var problem))
        {
            // No console (a Windows program): a log file is all there is, if one was named.
            if (options?.LogFile is { } log)
            {
                Log(log, $"Update: bad arguments ({problem}).");
            }

            return 2;
        }

        return new Installer(options!).Run();
    }

    internal static void Log(string file, string message)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(file)!);
            var line = string.Create(CultureInfo.InvariantCulture, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} info: {message}{Environment.NewLine}");
            File.AppendAllText(file, line, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            // A log that can't be written never stops the update.
        }
    }
}

/// <summary>The command line: <c>--pid --install --package --backup --staging --exe --cwd --log [--attempts] -- &lt;launcher's arguments&gt;</c>.</summary>
internal sealed record Options(
    int ProcessId,
    string InstallDir,
    string PackageDir,
    string BackupDir,
    string StagingDir,
    string Executable,
    string WorkingDirectory,
    string LogFile,
    int MoveAttempts,
    IReadOnlyList<string> Arguments)
{
    public static bool TryParse(string[] args, out Options? options, out string? problem)
    {
        options = null;
        problem = null;
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        var separator = Array.IndexOf(args, "--");
        var named = separator < 0 ? args : args[..separator];
        for (var i = 0; i < named.Length; i++)
        {
            if (!named[i].StartsWith("--", StringComparison.Ordinal) || i + 1 == named.Length)
            {
                problem = $"'{named[i]}' isn't an option with a value";
                return false;
            }

            values[named[i][2..]] = named[++i];
        }

        string? Path(string name) => values.TryGetValue(name, out var value) && System.IO.Path.IsPathFullyQualified(value) ? value : null;
        var log = Path("log");
        options = new Options(0, string.Empty, string.Empty, string.Empty, string.Empty, string.Empty, string.Empty, log!, 20, []);
        var attempts = 20;
        if (!values.TryGetValue("pid", out var pidText) || !int.TryParse(pidText, NumberStyles.None, CultureInfo.InvariantCulture, out var pid)
            || (values.TryGetValue("attempts", out var attemptsText) && (!int.TryParse(attemptsText, NumberStyles.None, CultureInfo.InvariantCulture, out attempts) || attempts < 1))
            || Path("install") is not { } install || Path("package") is not { } package || Path("backup") is not { } backup
            || Path("staging") is not { } staging || Path("exe") is not { } exe || Path("cwd") is not { } cwd || log is null)
        {
            problem = "it needs --pid, and --install, --package, --backup, --staging, --exe, --cwd and --log as absolute paths";
            return false;
        }

        options = new Options(pid, install, package, backup, staging, exe, cwd, log, attempts, separator < 0 ? [] : args[(separator + 1)..]);
        return true;
    }
}

internal sealed class Installer(Options options)
{
    private sealed record Step(string Name, bool HadOld)
    {
        public bool Placed { get; set; }
    }

    private void Log(string message) => Program.Log(options.LogFile, message);

    public int Run()
    {
        Log($"Update: waiting for the launcher (process {options.ProcessId}) to quit.");
        if (!WaitForLauncher())
        {
            Log("Update: the launcher was still running after a minute, so nothing was changed.");
            return 1;
        }

        var done = new List<Step>();
        Exception? failure = null;
        try
        {
            Directory.CreateDirectory(options.BackupDir);
            foreach (var entry in new DirectoryInfo(options.PackageDir).EnumerateFileSystemInfos())
            {
                var target = Path.Combine(options.InstallDir, entry.Name);
                var step = new Step(entry.Name, Path.Exists(target));
                if (step.HadOld)
                {
                    Move(target, Path.Combine(options.BackupDir, entry.Name));
                }

                done.Add(step);
                Move(entry.FullName, target);
                step.Placed = true;
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            failure = e;
        }

        var clean = true;
        if (failure is not null)
        {
            Log($"Update: installing failed ({failure.Message}), so the old version is put back.");
            for (var i = done.Count - 1; i >= 0; i--)
            {
                var step = done[i];
                var target = Path.Combine(options.InstallDir, step.Name);
                try
                {
                    if (step.Placed)
                    {
                        Move(target, Path.Combine(options.PackageDir, step.Name));
                    }

                    if (step.HadOld)
                    {
                        Move(Path.Combine(options.BackupDir, step.Name), target);
                    }
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException)
                {
                    clean = false;
                    Log($"Update: {step.Name} couldn't be put back ({e.Message}). The old one is in {options.BackupDir}.");
                }
            }
        }
        else
        {
            Log($"Update: installed {done.Count} file(s) and folder(s) in {options.InstallDir}.");
        }

        StartLauncher();
        if (clean)
        {
            DeleteStaging();
        }
        else
        {
            try
            {
                File.WriteAllText(Path.Combine(options.StagingDir, Program.IncompleteMarker), $"The old version's files that couldn't be put back are in {options.BackupDir}.");
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                Log($"Update: {Program.IncompleteMarker} couldn't be written ({e.Message}).");
            }
        }

        return failure is null ? 0 : 1;
    }

    /// <summary>True once the launcher's process has ended (or the id is another program's now: the launcher has gone).</summary>
    private bool WaitForLauncher()
    {
        Process process;
        try
        {
            process = Process.GetProcessById(options.ProcessId);
        }
        catch (ArgumentException)
        {
            return true;
        }

        using (process)
        {
            try
            {
                var path = process.MainModule?.FileName;
                if (path is not null && !string.Equals(Path.GetFullPath(path), Path.GetFullPath(options.Executable), StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            catch (Exception e) when (e is System.ComponentModel.Win32Exception or InvalidOperationException)
            {
                // Exited meanwhile, or not ours to read: wait on it either way.
            }

            try
            {
                return process.WaitForExit(60_000);
            }
            catch (InvalidOperationException)
            {
                return true;
            }
        }
    }

    /// <summary>A rename, tried again half a second apart: an antivirus scanner or the indexer can hold a file a moment.</summary>
    private void Move(string from, string to)
    {
        for (var attempt = 1; ; attempt++)
        {
            try
            {
                if (Directory.Exists(from))
                {
                    Directory.Move(from, to);
                }
                else
                {
                    File.Move(from, to);
                }

                return;
            }
            catch (Exception e) when ((e is IOException or UnauthorizedAccessException) && attempt < options.MoveAttempts)
            {
                Thread.Sleep(500);
            }
        }
    }

    private void StartLauncher()
    {
        try
        {
            var start = new ProcessStartInfo(options.Executable)
            {
                UseShellExecute = false,
                WorkingDirectory = Directory.Exists(options.WorkingDirectory) ? options.WorkingDirectory : options.InstallDir,
            };
            foreach (var argument in options.Arguments)
            {
                start.ArgumentList.Add(argument);
            }

            using var process = Process.Start(start);
            Log($"Update: started {options.Executable}.");
        }
        catch (Exception e) when (e is System.ComponentModel.Win32Exception or IOException or InvalidOperationException)
        {
            Log($"Update: the launcher couldn't be started ({e.Message}).");
        }
    }

    /// <summary>
    /// Everything in the staging folder but this program, which is running from it (and can't delete itself): the
    /// launcher deletes what's left at its next check.
    /// </summary>
    private void DeleteStaging()
    {
        var self = Environment.ProcessPath is { } path ? Path.GetFullPath(path) : null;
        var left = 0;
        try
        {
            foreach (var entry in new DirectoryInfo(options.StagingDir).EnumerateFileSystemInfos())
            {
                if (string.Equals(entry.FullName, self, StringComparison.OrdinalIgnoreCase))
                {
                    left++;
                    continue;
                }

                try
                {
                    if (entry is DirectoryInfo folder)
                    {
                        folder.Delete(recursive: true);
                    }
                    else
                    {
                        entry.Delete();
                    }
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException)
                {
                    // A plain build's own .dll, loaded; or a file someone holds open.
                    left++;
                }
            }

            if (left == 0)
            {
                Directory.Delete(options.StagingDir);
            }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            Log($"Update: the staging folder couldn't be deleted ({e.Message}); the launcher deletes it at its next check.");
        }
    }
}
