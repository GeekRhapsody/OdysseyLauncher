using System;
using System.Collections.Generic;
using System.Globalization;
using Launcher.App.Ui;
using Launcher.Core.Config;

namespace Launcher.App.Settings;

/// <summary>
/// Settings, Systems (2026-11-07): every enabled system, those with games first, each opening its <see cref="SystemPage"/>
/// (its ROM folders, emulator, games view, models, scraping and gamelist import), as X on its card does. The ROM root is
/// on the Library page.
/// </summary>
public sealed partial class SystemsPage : ListPanel
{
    private readonly SettingsController _settings;

    public SystemsPage(SettingsController settings)
        : base("Systems")
    {
        _settings = settings;
        Subtitle = "Each system's ROM folders, emulator, games view and models";
        Build();
        SetHints(CommonHints.ChooseBack);
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    public override void OnRevealed() => Rebuild(_settings.Services.Config);

    private void Rebuild(AppConfig config)
    {
        ClearRows(out var focused);
        Build();
        FocusRow(focused);
    }

    private void Build()
    {
        var config = _settings.Services.Config;
        var games = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var summary in _settings.Services.Systems)
        {
            games[summary.SystemId] = summary.GameCount;
        }

        AddNote("X on a system's card opens the same page.");
        AddSection("Your systems");
        var withGames = 0;
        foreach (var system in config.Systems)
        {
            if (games.GetValueOrDefault(system.Id) > 0)
            {
                AddSystem(config, system, games[system.Id]);
                withGames++;
            }
        }

        if (withGames == 0)
        {
            AddNote("None has games yet: put them in their folders under the ROM root (Library), then rescan.");
        }

        AddSection("Other systems");
        foreach (var system in config.Systems)
        {
            if (games.GetValueOrDefault(system.Id) == 0)
            {
                AddSystem(config, system, 0);
            }
        }
    }

    private void AddSystem(AppConfig config, SystemConfig system, int games)
    {
        var emulator = config.Emulators.TryGetValue(system.Emulator, out var profile) ? profile.Name : system.Emulator;
        var detail = system.RomDirSource == RomDirSource.Configured ? $"{emulator} · ROM folders of its own" : emulator;
        var value = games == 0 ? null : games == 1 ? "1 game" : games.ToString("N0", CultureInfo.CurrentCulture) + " games";
        var id = system.Id;
        AddRow(system.Name, detail, value, () => Layer.Push(new SystemPage(_settings, id)));
    }
}
