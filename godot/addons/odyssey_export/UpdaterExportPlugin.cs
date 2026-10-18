#if TOOLS
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// Publishes the update helper (<c>src/Launcher.Updater</c>, <c>OdysseyUpdater.exe</c>) with Native AOT when a Windows
/// export ends, and puts it beside the exported executable (docs/ARCHITECTURE.md A1 "Updates"): one file, needing no
/// .NET on the user's PC. Native AOT needs the Visual Studio C++ build tools (on the owner's PC and GitHub's Windows
/// runners). If it fails, the export has no helper and can't update itself: the error says why, and the release
/// workflow refuses an export without it.
/// </summary>
[Tool]
public partial class UpdaterExportPlugin : EditorExportPlugin
{
    private const string HelperFileName = "OdysseyUpdater.exe";
    private static readonly TimeSpan Timeout = TimeSpan.FromMinutes(10);

    private string? _exportDir;

    public override string _GetName() => "OdysseyUpdater";

    public override void _ExportBegin(string[] features, bool isDebug, string path, uint flags)
    {
        // A preset's path is relative to the project; the command line's is absolute.
        _exportDir = Array.IndexOf(features, "windows") >= 0
            ? Path.GetDirectoryName(Path.GetFullPath(Path.Combine(ProjectSettings.GlobalizePath("res://"), path)))
            : null;
    }

    public override void _ExportEnd()
    {
        if (_exportDir is null)
        {
            return;
        }

        var exportDir = _exportDir;
        _exportDir = null;
        var repo = Path.GetFullPath(Path.Combine(ProjectSettings.GlobalizePath("res://"), ".."));
        var project = Path.Combine(repo, "src", "Launcher.Updater", "Launcher.Updater.csproj");
        var output = Path.Combine(repo, "artifacts", "updater");
        var start = new ProcessStartInfo("dotnet")
        {
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = repo,
        };
        foreach (var argument in new[] { "publish", project, "-c", "ExportRelease", "-r", "win-x64", "-o", output, "-nologo" })
        {
            start.ArgumentList.Add(argument);
        }

        // As in the release workflow: build servers would inherit the output pipes and keep this waiting.
        start.Environment["MSBUILDDISABLENODEREUSE"] = "1";
        start.Environment["DOTNET_CLI_USE_MSBUILD_SERVER"] = "0";
        start.Environment["UseSharedCompilation"] = "false";
        // Visual Studio 18's vcvarsall.bat runs vswhere.exe from PATH, and the AOT compiler's targets read its "not
        // recognised" message as the linker's folder: put the installer's folder (where vswhere.exe is) first.
        var installer = Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.ProgramFilesX86), "Microsoft Visual Studio", "Installer");
        start.Environment["PATH"] = installer + Path.PathSeparator + System.Environment.GetEnvironmentVariable("PATH");
        try
        {
            using var process = Process.Start(start)!;
            var stdout = process.StandardOutput.ReadToEndAsync();
            var stderr = process.StandardError.ReadToEndAsync();
            if (!process.WaitForExit(Timeout))
            {
                process.Kill(entireProcessTree: true);
                GD.PushError($"Odyssey export: publishing {HelperFileName} took over {Timeout.TotalMinutes:0} minutes, so the export has no update helper.");
                return;
            }

            var log = stdout.Result + stderr.Result;
            var helper = Path.Combine(output, HelperFileName);
            if (process.ExitCode != 0 || !File.Exists(helper))
            {
                GD.PushError($"Odyssey export: publishing {HelperFileName} failed (exit code {process.ExitCode}), so the export has no update helper. Native AOT needs the Visual Studio C++ build tools.\n{Tail(log)}");
                return;
            }

            File.Copy(helper, Path.Combine(exportDir, HelperFileName), overwrite: true);
            GD.Print($"Odyssey export: published {HelperFileName} ({new FileInfo(helper).Length / 1024} KB, Native AOT) to {exportDir}");
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or System.ComponentModel.Win32Exception or InvalidOperationException)
        {
            GD.PushError($"Odyssey export: couldn't publish {HelperFileName} ({e.Message}), so the export has no update helper.");
        }
    }

    private static string Tail(string log)
    {
        var lines = new List<string>(log.Split('\n'));
        return string.Join('\n', lines.GetRange(Math.Max(0, lines.Count - 20), Math.Min(20, lines.Count)));
    }
}
#endif
