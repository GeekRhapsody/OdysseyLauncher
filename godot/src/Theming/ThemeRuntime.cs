using System;
using System.Collections.Generic;
using Godot;
using Launcher.App.Grid;
using Launcher.App.Models;
using Launcher.App.Screens;
using Launcher.Core.Config;
using Launcher.Core.Platform;
using Launcher.Core.Theming;
using ConfigFile = Launcher.Core.Config.ConfigFile;
using Theme = Launcher.Core.Theming.Theme;
using ThemeLook = Launcher.Core.Theming.Look;

namespace Launcher.App.Theming;

/// <summary>
/// A theme resolved for the enabled systems (A6, A7): the themes, and each system's model candidates in precedence
/// order, for its games and its card. Built on the thread pool (it reads the manifests and lists the user's model
/// folders); nothing in it touches Godot's scene.
/// </summary>
public sealed class ThemePlan
{
    /// <summary>The key of the Favourites and Recently played cards, which have no system.</summary>
    public const string VirtualCards = "";

    private ThemePlan(ThemeSet themes, ModelResolver resolver, IReadOnlyList<Diagnostic> diagnostics, AppConfig config, PlatformPaths paths)
    {
        Paths = paths;
        Themes = themes;
        Resolver = resolver;
        Diagnostics = diagnostics;
        foreach (var system in config.Systems)
        {
            GameCandidates[system.Id] = resolver.GameTemplates(system.Id);
            CardCandidates[system.Id] = resolver.SystemModels(system.Id);
        }

        CardCandidates[VirtualCards] = resolver.SystemModels(null);
    }

    public ThemeSet Themes { get; }

    /// <summary>The folders it was resolved from (the model cache and log live there too).</summary>
    public PlatformPaths Paths { get; }

    public Theme Active => Themes.Active;

    public ModelResolver Resolver { get; }

    /// <summary>The manifests' problems and the resolver's.</summary>
    public IReadOnlyList<Diagnostic> Diagnostics { get; }

    public Dictionary<string, IReadOnlyList<ModelCandidate>> GameCandidates { get; } = new(StringComparer.Ordinal);

    public Dictionary<string, IReadOnlyList<ModelCandidate>> CardCandidates { get; } = new(StringComparer.Ordinal);

    /// <summary>
    /// The built-in themes' manifests (<c>res://themes/&lt;id&gt;/theme.toml</c>), read through Godot's file access so it
    /// works from the PCK. Thread pool only: it does file I/O.
    /// </summary>
    public static List<ThemeSource> BuiltInSources()
    {
        var sources = new List<ThemeSource>();
        const string Root = "res://" + ThemeLoader.FolderName;
        foreach (var id in DirAccess.GetDirectoriesAt(Root))
        {
            var folder = $"{Root}/{id}";
            var manifest = $"{folder}/{ThemeLoader.ManifestFileName}";
            if (!FileAccess.FileExists(manifest))
            {
                continue;
            }

            sources.Add(new ThemeSource(id, new ConfigFile($"built-in/themes/{id}/{ThemeLoader.ManifestFileName}", FileAccess.GetFileAsString(manifest)),
                ThemeOrigin.BuiltIn, folder, new BuiltInThemeFiles()));
        }

        return sources;
    }

    /// <summary>Loads and resolves the theme <paramref name="themeId"/> names. Thread pool only.</summary>
    /// <param name="builtIn">The built-in theme, if it's already loaded (at boot, while config loads).</param>
    public static ThemePlan Build(AppConfig config, PlatformPaths paths, string themeId, IReadOnlyList<ThemeSource> builtIns, ThemeLoadResult? builtIn = null)
    {
        var diagnostics = new List<Diagnostic>();
        var users = ThemeCatalog.UserSources(System.IO.Path.Combine(paths.ConfigDir, ThemeLoader.FolderName), diagnostics);
        var themes = ThemeCatalog.Load(builtIns, users, themeId, diagnostics, builtIn);
        var resolver = new ModelResolver(themes.Active, themes.BuiltIn, UserModels.Find(paths.ConfigDir), config, paths.DataDir);
        diagnostics.AddRange(resolver.Diagnostics);
        return new ThemePlan(themes, resolver, diagnostics, config, paths);
    }

    /// <summary>
    /// A built-in theme in the PCK. Its models aren't inspected or checked for here (a missing one fails to load and
    /// the next candidate is used): the committed built-in theme is checked against its files by Core's tests.
    /// </summary>
    private sealed class BuiltInThemeFiles : IThemeFiles
    {
        public bool Exists(string relativePath) => true;

        public IReadOnlyList<string>? MaterialsOf(string relativePath, out string? error)
        {
            error = null;
            return null;
        }
    }
}

/// <summary>
/// Main thread: loads a <see cref="ThemePlan"/>'s models, trying each system's candidates in order until one loads, and
/// then gives the grids their templates, the slot layout, and each system's look and colour.
/// </summary>
public sealed class ThemeRuntime
{
    private readonly ModelLoader _loader;
    private readonly Dictionary<string, int> _gameChoice = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _cardChoice = new(StringComparer.Ordinal);
    private readonly List<ItemTemplate> _gameTemplates = [];
    private readonly List<ItemTemplate> _cardTemplates = [];
    private readonly Dictionary<string, int> _gameTemplateOf = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _cardTemplateOf = new(StringComparer.Ordinal);

    public ThemeRuntime(ThemePlan plan, ModelLoader loader)
    {
        Plan = plan;
        _loader = loader;
        foreach (var system in plan.GameCandidates.Keys)
        {
            _gameChoice[system] = 0;
        }

        foreach (var system in plan.CardCandidates.Keys)
        {
            _cardChoice[system] = 0;
        }
    }

    public ThemePlan Plan { get; }

    /// <summary>True once every system has a loaded model for its games and its card.</summary>
    public bool Ready { get; private set; }

    public IReadOnlyList<ItemTemplate> GameTemplates => _gameTemplates;

    public IReadOnlyList<ItemTemplate> CardTemplates => _cardTemplates;

    /// <summary>Which slots the games grid streams media for.</summary>
    public SlotLayout Layout { get; private set; } = SlotLayout.Empty;

    public float TransitionSeconds => Plan.Active.LookTransitionMs / 1000f;

    /// <summary>Main thread, each frame until <see cref="Ready"/>: advances loading. True when it has just become ready.</summary>
    public bool Poll()
    {
        if (Ready)
        {
            return false;
        }

        _loader.Poll();
        var waiting = Advance(Plan.GameCandidates, _gameChoice, systemCard: false)
            | Advance(Plan.CardCandidates, _cardChoice, systemCard: true);
        if (waiting)
        {
            return false;
        }

        Collect(Plan.GameCandidates, _gameChoice, false, _gameTemplates, _gameTemplateOf);
        Collect(Plan.CardCandidates, _cardChoice, true, _cardTemplates, _cardTemplateOf);
        if (_gameTemplates.Count == 0 || _cardTemplates.Count == 0)
        {
            throw new InvalidOperationException($"No model of the theme '{Plan.Active.Id}' or the built-in theme could be loaded (see the warnings above).");
        }

        Layout = new SlotLayout(_gameTemplates);
        Ready = true;
        return true;
    }

    /// <summary>The games grid template index for a system's games (the first template for a system it doesn't know).</summary>
    public int GameTemplateOf(string systemId) => _gameTemplateOf.TryGetValue(systemId, out var t) ? t : 0;

    /// <summary>The systems grid template index for a card; null for Favourites and Recently played.</summary>
    public int CardTemplateOf(string? systemId) =>
        _cardTemplateOf.TryGetValue(systemId ?? ThemePlan.VirtualCards, out var t) ? t : _cardTemplateOf[ThemePlan.VirtualCards];

    /// <summary>The candidate a system's games use, once ready (the options panel says which: M7); null if none loaded.</summary>
    public ModelCandidate? GameModelInUse(string systemId) => InUse(Plan.GameCandidates, _gameChoice, systemId);

    /// <summary>The candidate a system's card uses, once ready; null if none loaded.</summary>
    public ModelCandidate? CardModelInUse(string systemId) => InUse(Plan.CardCandidates, _cardChoice, systemId);

    private static ModelCandidate? InUse(Dictionary<string, IReadOnlyList<ModelCandidate>> lists, Dictionary<string, int> choice, string systemId) =>
        lists.TryGetValue(systemId, out var candidates) && choice.TryGetValue(systemId, out var index) && index < candidates.Count
            ? candidates[index]
            : null;

    public ThemeLook LookFor(string? systemId) => Plan.Resolver.LookFor(systemId);

    /// <summary>A system's colour: the theme's, else one made from its id.</summary>
    public Color ColourOf(string systemId) => Palette.ForSystem(Plan.Resolver.ColourOf(systemId), systemId);

    /// <summary>Main thread: starts loading a per-game model (DataDir-relative path) and says where it stands.</summary>
    public ModelState RequestPerGame(string relativePath) => _loader.Request(Plan.Resolver.PerGame(relativePath), systemCard: false);

    /// <summary>The loaded per-game model, or null.</summary>
    public ItemTemplate? PerGame(string relativePath) => _loader.Get(Plan.Resolver.PerGame(relativePath), systemCard: false);

    /// <summary>The per-game model's file, as the loader knows it.</summary>
    public string PerGamePath(string relativePath) => Plan.Resolver.PerGame(relativePath).Path;

    /// <summary>Main thread: a per-game model's file changed, so it's loaded (and processed) again when next requested.</summary>
    public void ForgetPerGame(string relativePath) => _loader.ReleasePerGame(PerGamePath(relativePath));

    /// <summary>Main thread, each frame while per-game models load.</summary>
    public bool PollLoads() => (_loader.Pending > 0 || _loader.HasResults) && _loader.Poll();

    /// <summary>Requests each list's current candidate; moves past failed ones. True while any is still loading.</summary>
    private bool Advance(Dictionary<string, IReadOnlyList<ModelCandidate>> lists, Dictionary<string, int> choice, bool systemCard)
    {
        var waiting = false;
        foreach (var (system, candidates) in lists)
        {
            while (choice[system] < candidates.Count)
            {
                var state = _loader.Request(candidates[choice[system]], systemCard);
                if (state == ModelState.Failed)
                {
                    choice[system]++;
                    continue;
                }

                waiting |= state == ModelState.Loading;
                break;
            }
        }

        return waiting;
    }

    private void Collect(
        Dictionary<string, IReadOnlyList<ModelCandidate>> lists, Dictionary<string, int> choice, bool systemCard,
        List<ItemTemplate> templates, Dictionary<string, int> indexOf)
    {
        foreach (var (system, candidates) in lists)
        {
            if (choice[system] >= candidates.Count)
            {
                GD.PushWarning($"Themes: no model for {(system.Length == 0 ? "the virtual systems' cards" : system)} could be loaded; another system's is used.");
                continue;
            }

            var template = _loader.Get(candidates[choice[system]], systemCard)!;
            var index = templates.IndexOf(template);
            if (index < 0)
            {
                index = templates.Count;
                templates.Add(template);
            }

            indexOf[system] = index;
        }

        if (!indexOf.ContainsKey(ThemePlan.VirtualCards) && systemCard && templates.Count > 0)
        {
            indexOf[ThemePlan.VirtualCards] = 0;
        }
    }
}
