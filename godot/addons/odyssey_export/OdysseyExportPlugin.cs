#if TOOLS
using Godot;

namespace Launcher.App.Tools;

/// <summary>
/// The editor plugin that adds <see cref="ThemesExportPlugin"/> and <see cref="UpdaterExportPlugin"/>, so every export
/// (the editor's, and <c>--export-release</c> from the command line) puts the app's themes and the update helper beside
/// the executable. Editor builds only.
/// </summary>
[Tool]
public partial class OdysseyExportPlugin : EditorPlugin
{
    private ThemesExportPlugin? _themes;
    private UpdaterExportPlugin? _updater;

    public override void _EnterTree()
    {
        _themes = new ThemesExportPlugin();
        AddExportPlugin(_themes);
        _updater = new UpdaterExportPlugin();
        AddExportPlugin(_updater);
    }

    public override void _ExitTree()
    {
        if (_themes is not null)
        {
            RemoveExportPlugin(_themes);
            _themes = null;
        }

        if (_updater is not null)
        {
            RemoveExportPlugin(_updater);
            _updater = null;
        }
    }
}
#endif
