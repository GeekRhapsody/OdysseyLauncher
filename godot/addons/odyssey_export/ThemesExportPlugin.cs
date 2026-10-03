#if TOOLS
using System;
using System.IO;
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// Copies <c>godot/themes/</c> to <c>themes/</c> beside the exported executable when an export ends (A6 Locations).
/// The app reads its own themes from there, outside the PCK; Godot ignores the folder (its <c>.gdignore</c>), so it's
/// neither imported nor packed. The export's <c>themes/</c> is replaced whole, so a theme or model removed from the
/// project doesn't linger in it.
/// </summary>
[Tool]
public partial class ThemesExportPlugin : EditorExportPlugin
{
    /// <summary>Godot's marker for a folder it ignores; not copied.</summary>
    private const string IgnoreMarker = ".gdignore";

    private string? _exportDir;

    public override string _GetName() => "OdysseyThemes";

    public override void _ExportBegin(string[] features, bool isDebug, string path, uint flags)
    {
        // A preset's path is relative to the project; the command line's is absolute.
        _exportDir = Path.GetDirectoryName(Path.GetFullPath(Path.Combine(ProjectSettings.GlobalizePath("res://"), path)));
    }

    public override void _ExportEnd()
    {
        if (_exportDir is null)
        {
            return;
        }

        var source = ProjectSettings.GlobalizePath("res://" + Launcher.Core.Theming.ThemeLoader.FolderName);
        var target = Path.Combine(_exportDir, Launcher.Core.Theming.ThemeLoader.FolderName);
        _exportDir = null;
        try
        {
            if (Directory.Exists(target))
            {
                Directory.Delete(target, recursive: true);
            }

            var files = Copy(source, target);
            GD.Print($"Odyssey export: copied the themes ({files} files) to {target}");
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            GD.PushError($"Odyssey export: couldn't copy the themes to {target}: {e.Message}. The export can't run without them.");
        }
    }

    private static int Copy(string from, string to)
    {
        Directory.CreateDirectory(to);
        var files = 0;
        foreach (var file in Directory.GetFiles(from))
        {
            if (Path.GetFileName(file) != IgnoreMarker)
            {
                File.Copy(file, Path.Combine(to, Path.GetFileName(file)));
                files++;
            }
        }

        foreach (var folder in Directory.GetDirectories(from))
        {
            files += Copy(folder, Path.Combine(to, Path.GetFileName(folder)));
        }

        return files;
    }
}
#endif
