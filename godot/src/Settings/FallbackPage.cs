using System.Collections.Generic;
using System.Linq;
using Godot;
using Launcher.App.Ui;
using Launcher.Core.Config;
using Launcher.Core.Scraping;

namespace Launcher.App.Settings;

/// <summary>
/// The fallback providers and their order (M7): each is asked, in order, only for what the ones before it didn't
/// have.
/// </summary>
public sealed partial class FallbackPage : OrderedListPage
{
    private readonly SettingsController _settings;

    public FallbackPage(SettingsController settings)
        : base("Fallbacks", new Vector2(860, 560))
    {
        _settings = settings;
        Subtitle = "Asked in order, for what the default provider didn't have";
        Build();
        _settings.ConfigApplied += Rebuild;
    }

    public override void OnClosed() => _settings.ConfigApplied -= Rebuild;

    protected override void Build()
    {
        var scraping = _settings.Services.Config.Settings.Scraping;
        AddNote($"{ScrapingPage.NameOf(scraping.Provider)} is the default, so it's asked first. Change that on the Scraping page.");

        // The fallbacks in order, then the providers that are off.
        var order = scraping.Fallback.Concat(ConfigLoader.Scrapers.Where(p => p != scraping.Provider && !scraping.Fallback.Contains(p))).ToList();
        for (var i = 0; i < order.Count; i++)
        {
            var id = order[i];
            AddItem(id, ScrapingPage.NameOf(id), ScrapingPage.AboutOf(id), scraping.Fallback.Contains(id) ? i + 1 : 0);
        }
    }

    protected override void Toggle(string id)
    {
        var fallback = _settings.Services.Config.Settings.Scraping.Fallback.ToList();
        if (!fallback.Remove(id))
        {
            fallback.Add(id);
        }

        Save(fallback, fallback.Contains(id) ? $"{ScrapingPage.NameOf(id)} is a fallback now." : $"{ScrapingPage.NameOf(id)} isn't asked any more.");
    }

    protected override void Move(string id, int direction)
    {
        var fallback = _settings.Services.Config.Settings.Scraping.Fallback.ToList();
        var index = fallback.IndexOf(id);
        var target = index + direction;
        if (index < 0 || target < 0 || target >= fallback.Count)
        {
            return;
        }

        (fallback[index], fallback[target]) = (fallback[target], fallback[index]);
        Save(fallback, $"{ScrapingPage.NameOf(id)} is asked {Ordinal(target + 1)} among the fallbacks now.");
    }

    private void Save(List<string> fallback, string saved)
    {
        var provider = _settings.Services.Config.Settings.Scraping.Provider;
        if (ConfigInput.CheckProviders(provider, fallback) is { } problem)
        {
            ShowStatus(problem, UiStyle.Bad, 5);
            return;
        }

        _settings.Save(this, [new ConfigEdit(ConfigFileKind.Settings, ["scraping", "fallback"], fallback)], saved);
    }
}
