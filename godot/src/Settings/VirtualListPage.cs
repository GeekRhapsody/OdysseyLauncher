using Launcher.App.Navigation;
using Launcher.App.Screens;
using Launcher.App.Ui;
using Launcher.Core.Config;

namespace Launcher.App.Settings;

/// <summary>
/// Favourites' or All games' options (2026-11-10): how its games are shown and sorted, its own or the Appearance
/// page's, in settings.toml's <c>[display.favourites]</c> or <c>[display.all_games]</c>. X on its card opens it, and Menu
/// in its games. Recently played has none: it's always newest first, in the Appearance page's view.
/// </summary>
public sealed partial class VirtualListPage : GamesViewPanel
{
    private static readonly Hint[] Hints = [new("Change", Prompt.Accept), new("Default", Prompt.Secondary), new("Back", Prompt.Back)];

    private readonly SettingsController _settings;
    private readonly bool _favourites;

    /// <param name="id"><see cref="Navigator.FavouritesId"/> or <see cref="Navigator.AllGamesId"/>.</param>
    public VirtualListPage(SettingsController settings, string id)
        : base(NameOf(id), settings, ConfigFileKind.Settings,
            ["display", id == Navigator.FavouritesId ? ConfigLoader.FavouritesView : ConfigLoader.AllGamesView])
    {
        _settings = settings;
        _favourites = id == Navigator.FavouritesId;
        Build();
        SetHints(Hints);
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    public override bool Handle(NavCommand command) =>
        command == NavCommand.Secondary && ResetGamesView(GetViewport().GuiGetFocusOwner());

    private static string NameOf(string id) => id == Navigator.FavouritesId ? "Favourites" : "All games";

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var display = _settings.Services.Config.Settings.Display;
        AddSection("Games view");
        AddGamesViewRows(_favourites ? "Favourites'" : "All games'", _favourites ? display.Favourites : display.AllGames);
    }
}
