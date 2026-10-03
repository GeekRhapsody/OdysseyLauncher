#if TOOLS
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// The editor plugin that adds <see cref="ThemesExportPlugin"/>, so every export (the editor's, and
/// <c>--export-release</c> from the command line) puts the app's themes beside the executable. Editor builds only.
/// </summary>
[Tool]
public partial class OdysseyExportPlugin : EditorPlugin
{
    private ThemesExportPlugin? _themes;

    public override void _EnterTree()
    {
        _themes = new ThemesExportPlugin();
        AddExportPlugin(_themes);
    }

    public override void _ExitTree()
    {
        if (_themes is not null)
        {
            RemoveExportPlugin(_themes);
            _themes = null;
        }
    }
}
#endif
