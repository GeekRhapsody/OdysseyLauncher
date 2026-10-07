using Launcher.Core.Config;

namespace Launcher.Core.Theming;

/// <summary>
/// The user's own per-system models (A7), found by folder convention: <c>ConfigDir/models/templates/&lt;system&gt;.glb</c>
/// (a game template for every game of the system) and <c>ConfigDir/models/systems/&lt;system&gt;.glb</c> (the system's
/// card). Per-game models are in the media folder instead, indexed by the scanner (media kind <c>model</c>), since there
/// can be thousands.
/// </summary>
public sealed record UserModels(string ConfigDir, IReadOnlySet<string> Templates, IReadOnlySet<string> Systems)
{
    public const string FolderName = "models";

    public static UserModels None(string configDir) => new(configDir, new HashSet<string>(), new HashSet<string>());

    /// <summary>Lists both folders. Does file I/O: never on the main thread.</summary>
    public static UserModels Find(string configDir)
    {
        ArgumentNullException.ThrowIfNull(configDir);
        return new UserModels(configDir, List(Path.Combine(configDir, FolderName, "templates")), List(Path.Combine(configDir, FolderName, "systems")));

        static HashSet<string> List(string folder)
        {
            var ids = new HashSet<string>(StringComparer.Ordinal);
            if (!Directory.Exists(folder))
            {
                return ids;
            }

            try
            {
                foreach (var file in Directory.EnumerateFiles(folder, "*.glb"))
                {
                    ids.Add(Path.GetFileNameWithoutExtension(file).ToLowerInvariant());
                }
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                // An unreadable folder has no models.
            }

            return ids;
        }
    }

    public string TemplatePath(string systemId) => Path.Combine(ConfigDir, FolderName, "templates", systemId + ".glb");

    public string SystemPath(string systemId) => Path.Combine(ConfigDir, FolderName, "systems", systemId + ".glb");
}

/// <summary>A card's logo file (<see cref="ModelResolver.LogoOf"/>).</summary>
/// <param name="ThemeId">The theme it's in.</param>
/// <param name="Relative">Its path in that theme, '/'-separated.</param>
/// <param name="Path">An absolute file path.</param>
public sealed record LogoFile(string ThemeId, string Relative, string Path)
{
    /// <summary>What its derivative is named by: the theme and the path in it, wherever the theme's folder is.</summary>
    public string Key => $"{ThemeId}/{Relative}";
}

/// <summary>Where a model candidate comes from, in precedence order (A7).</summary>
public enum ModelLevel
{
    /// <summary><c>&lt;media folder&gt;/&lt;system&gt;/models/&lt;name&gt;.glb</c>, indexed by the scanner.</summary>
    UserGame,

    /// <summary>The template the user chose for the game (<c>game_overrides.template</c>, 2026-10-07): a template id in the active theme, else the base theme.</summary>
    GameChoice,

    /// <summary><c>ConfigDir/models/templates/&lt;system&gt;.glb</c>, or for a card <c>ConfigDir/models/systems/&lt;system&gt;.glb</c>.</summary>
    User,

    /// <summary>The user's <c>game_model</c> for the system in systems.toml: a template id in the active theme, else the base theme.</summary>
    GameModelSetting,

    /// <summary>The active theme's <c>[systems.&lt;id&gt;]</c> entry.</summary>
    ThemeSystem,

    /// <summary>The active theme's <c>[defaults]</c>.</summary>
    ThemeDefault,

    /// <summary>The base theme's <c>[systems.&lt;id&gt;]</c> entry (when another theme is active).</summary>
    BaseSystem,

    /// <summary>The base theme's <c>[defaults]</c>.</summary>
    BaseDefault,
}

/// <summary>One model a game or a system card can use, if it loads.</summary>
/// <param name="Origin">
/// <see cref="ThemeOrigin.BuiltIn"/>: a <c>.glb</c> in the app's themes folder, trusted. <see cref="ThemeOrigin.User"/>: a
/// <c>.glb</c> the user put there (their own models, and user themes'), inspected before it loads.
/// </param>
/// <param name="Path">An absolute file path.</param>
/// <param name="Template">The theme's template, with its slot chains; null for a user model (default chains).</param>
/// <param name="Tint">For a system card: whether its plain materials take the system's colour.</param>
/// <param name="Description">For logs: "theme 'memory-card' template 'dvd_case'".</param>
/// <param name="CardSlots">
/// For a system card: the chains its theme gives its slots (<c>[systems.&lt;id&gt;.slots]</c> over
/// <c>[defaults.system_slots]</c>); a slot it doesn't list uses <see cref="SlotChain.ForSystemModel"/>. Null for none.
/// </param>
public sealed record ModelCandidate(
    ModelLevel Level,
    ThemeOrigin Origin,
    string Path,
    GameTemplate? Template,
    bool Tint,
    string Description,
    IReadOnlyDictionary<int, SlotChain>? CardSlots = null)
{
    /// <summary>
    /// Two candidates are the same grid template if they load the same file with the same chains and tint: a key that
    /// dedupes them across systems and precedence levels. A theme's template extending the base's has the same file and
    /// id but its own chains, so the declaring theme is part of it; a card's chains are written out, since two systems
    /// can share a model and not its chains.
    /// </summary>
    public string Key => CardSlots is { Count: > 0 } slots
        ? $"{Path}|{Template?.ThemeId}:{Template?.Id}|{(Tint ? "tint" : "plain")}|{string.Join("; ", slots.OrderBy(s => s.Key).Select(s => s.Value))}"
        : $"{Path}|{Template?.ThemeId}:{Template?.Id}|{(Tint ? "tint" : "plain")}";

    /// <summary>The slot's chain: for a card its theme's, else the template's, or the default for a user model.</summary>
    public SlotChain ChainFor(int slot, bool systemCard) =>
        systemCard
            ? CardSlots is not null && CardSlots.TryGetValue(slot, out var chain) ? chain : SlotChain.ForSystemModel(slot)
            : Template?.ChainFor(slot) ?? SlotChain.Default(slot);
}

/// <summary>
/// Works out, for each system, which models its games and its card can use, in precedence order (A7), and its look
/// and colour. Pure: the user's model files are listed beforehand (<see cref="UserModels.Find"/>) and per-game models
/// come from the library, so nothing is probed per item.
/// <para>
/// Games: the per-game model; the game's chosen template (<see cref="GameChoice"/>); <c>ConfigDir/models/templates/&lt;system&gt;.glb</c>; the user's <c>game_model</c>; the
/// active theme's template for the system; its default template; then the base theme's two. Cards:
/// <c>ConfigDir/models/systems/&lt;system&gt;.glb</c>; the active theme's model for the system; its default; then the
/// base theme's. The app loads candidates in order and uses the first that loads, so a broken or rejected model
/// falls through to the next. A theme's template id may be its own or the base theme's.
/// </para>
/// </summary>
public sealed class ModelResolver
{
    private readonly AppConfig _config;
    private readonly UserModels _user;
    private readonly string _mediaDir;
    private readonly List<Diagnostic> _diagnostics = [];

    /// <param name="active">The theme settings.toml names (or the base theme).</param>
    /// <param name="baseTheme">The base theme, always the last resort.</param>
    /// <param name="dataDir">DataDir: the media folder, which per-game models' stored paths stand in, is <paramref name="config"/>'s or <c>DataDir/media</c>.</param>
    public ModelResolver(Theme active, Theme baseTheme, UserModels user, AppConfig config, string dataDir)
    {
        Active = active ?? throw new ArgumentNullException(nameof(active));
        Base = baseTheme ?? throw new ArgumentNullException(nameof(baseTheme));
        _user = user ?? throw new ArgumentNullException(nameof(user));
        _config = config ?? throw new ArgumentNullException(nameof(config));
        _mediaDir = Media.MediaFolder.Of(config.Settings, dataDir ?? throw new ArgumentNullException(nameof(dataDir)));
        foreach (var system in config.Systems)
        {
            if (system.GameModel is { } id && !active.Templates.ContainsKey(id) && !baseTheme.Templates.ContainsKey(id))
            {
                var known = active.Templates.Keys.Concat(baseTheme.Templates.Keys).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal).ToList();
                _diagnostics.Add(new Diagnostic(Severity.Warning, Path.Combine(user.ConfigDir, ConfigSources.SystemsFileName), 0, 0,
                    $"systems.{system.Id}.game_model",
                    $"no template '{id}' in the theme '{active.Id}' or the base theme, so the theme's choice is used. The templates are {string.Join(", ", known)}"));
            }
        }
    }

    public Theme Active { get; }

    public Theme Base { get; }

    /// <summary>Problems found while resolving (a <c>game_model</c> no theme defines).</summary>
    public IReadOnlyList<Diagnostic> Diagnostics => _diagnostics;

    /// <summary>The system-level candidates for its games (every level but the per-game model), best first, without repeats.</summary>
    public IReadOnlyList<ModelCandidate> GameTemplates(string systemId)
    {
        ArgumentNullException.ThrowIfNull(systemId);
        var candidates = new List<ModelCandidate>();
        if (_user.Templates.Contains(systemId))
        {
            candidates.Add(new ModelCandidate(ModelLevel.User, ThemeOrigin.User, _user.TemplatePath(systemId), null, false,
                $"your models/templates/{systemId}.glb"));
        }

        if (_config.FindSystem(systemId)?.GameModel is { } gameModel && TemplateOf(Active, gameModel) is { } chosen)
        {
            Add(ModelLevel.GameModelSetting, chosen, $"game_model '{gameModel}'");
        }

        foreach (var (theme, systemLevel, defaultLevel) in Themes())
        {
            if (theme.Systems.TryGetValue(systemId, out var entry) && entry.GameTemplate is { } id && TemplateOf(theme, id) is { } assigned)
            {
                Add(systemLevel, assigned, $"[systems.{systemId}]");
            }

            if (theme.Defaults.GameTemplate is { } fallback && TemplateOf(theme, fallback) is { } byDefault)
            {
                Add(defaultLevel, byDefault, "[defaults]");
            }
        }

        return candidates;

        void Add(ModelLevel level, GameTemplate template, string where)
        {
            var candidate = CandidateFor(level, template, where);
            if (!candidates.Exists(c => c.Key == candidate.Key))
            {
                candidates.Add(candidate);
            }
        }
    }

    /// <summary>
    /// The template the user chose for one game (2026-10-07): <paramref name="id"/> in the active theme (its own, or its
    /// extension of the base's), else in the base theme; null when neither has it, and the game shows its system's.
    /// </summary>
    public ModelCandidate? GameChoice(string id)
    {
        ArgumentNullException.ThrowIfNull(id);
        return TemplateOf(Active, id) is { } template ? CandidateFor(ModelLevel.GameChoice, template, "chosen for a game") : null;
    }

    /// <summary>The per-game model, from its <c>media</c> row (kind <c>model</c>, a stored path: <c>media/...</c>).</summary>
    public ModelCandidate PerGame(string relativePath)
    {
        ArgumentNullException.ThrowIfNull(relativePath);
        return new ModelCandidate(ModelLevel.UserGame, ThemeOrigin.User,
            Path.GetFullPath(Media.MediaFolder.FullPath(_mediaDir, relativePath)), null, false,
            $"your {relativePath}");
    }

    /// <summary>
    /// The candidates for a system's card, best first, without repeats. Null for Favourites and Recently played. Each
    /// carries the chains of the theme whose model it is; the user's own card takes the active theme's.
    /// </summary>
    public IReadOnlyList<ModelCandidate> SystemModels(string? systemId)
    {
        var candidates = new List<ModelCandidate>();
        if (systemId is not null && _user.Systems.Contains(systemId))
        {
            candidates.Add(new ModelCandidate(ModelLevel.User, ThemeOrigin.User, _user.SystemPath(systemId), null, false,
                $"your models/systems/{systemId}.glb", CardSlotsOf(Active, systemId)));
        }

        foreach (var (theme, systemLevel, defaultLevel) in Themes())
        {
            ThemeSystem? entry = null;
            if (systemId is not null && theme.Systems.TryGetValue(systemId, out entry) && entry.Model is { } model)
            {
                Add(systemLevel, theme, model, entry.Tint ?? false, $"[systems.{systemId}]");
            }

            if (theme.Defaults.SystemModel is { } fallback)
            {
                Add(defaultLevel, theme, fallback, entry?.Tint ?? theme.Defaults.TintSystemModel, "[defaults]");
            }
        }

        return candidates;

        void Add(ModelLevel level, Theme theme, string model, bool tint, string where)
        {
            var candidate = new ModelCandidate(level, theme.Origin, theme.PathOf(model), null, tint, $"theme '{theme.Id}' {model} ({where})",
                CardSlotsOf(theme, systemId));
            if (!candidates.Exists(c => c.Key == candidate.Key))
            {
                candidates.Add(candidate);
            }
        }
    }

    /// <summary>
    /// A card's image (A6 <c>logos/</c>): the active theme's for the system (or <c>favourites</c>, <c>recently_played</c>),
    /// else the base theme's; null when neither has one.
    /// </summary>
    public LogoFile? LogoOf(string id)
    {
        ArgumentNullException.ThrowIfNull(id);
        foreach (var (theme, _, _) in Themes())
        {
            if (theme.Logos.TryGetValue(id, out var logo))
            {
                return new LogoFile(theme.Id, logo, theme.PathOf(logo));
            }
        }

        return null;
    }

    /// <summary>The system's colour (its card's tint and its plain boxes'): the active theme's, else the base theme's.</summary>
    public Rgb? ColourOf(string systemId) =>
        Active.Systems.TryGetValue(systemId, out var entry) && entry.Colour is { } colour ? colour
        : Base.Systems.TryGetValue(systemId, out var inBase) ? inBase.Colour : null;

    /// <summary>The active theme's look for a system's games (null: the systems grid).</summary>
    public Look LookFor(string? systemId) => Active.LookFor(systemId);

    /// <summary>
    /// A template id as <paramref name="theme"/> names it: its own template (which may extend the base's), else the base
    /// theme's; null when neither has it.
    /// </summary>
    public GameTemplate? TemplateOf(Theme theme, string id)
    {
        ArgumentNullException.ThrowIfNull(theme);
        ArgumentNullException.ThrowIfNull(id);
        return theme.Templates.TryGetValue(id, out var own) ? own : Base.Templates.GetValueOrDefault(id);
    }

    private ModelCandidate CandidateFor(ModelLevel level, GameTemplate template, string where)
    {
        // The model's file is in the base theme's folder when the template is the base's, or extends it without a model.
        var folder = template.ModelFromBase || template.ThemeId != Active.Id ? Base : Active;
        return new ModelCandidate(level, folder.Origin, folder.PathOf(template.Model), template, false,
            $"theme '{template.ThemeId}' template '{template.Id}' ({where})");
    }

    /// <summary>A theme's chains for a system's card: <c>[systems.&lt;id&gt;.slots]</c> over <c>[defaults.system_slots]</c>.</summary>
    private static IReadOnlyDictionary<int, SlotChain>? CardSlotsOf(Theme theme, string? systemId)
    {
        var own = systemId is not null && theme.Systems.TryGetValue(systemId, out var entry) ? entry.Slots : null;
        if (own is null)
        {
            return theme.Defaults.SystemSlots.Count > 0 ? theme.Defaults.SystemSlots : null;
        }

        var merged = new Dictionary<int, SlotChain>(theme.Defaults.SystemSlots);
        foreach (var (slot, chain) in own)
        {
            merged[slot] = chain;
        }

        return merged;
    }

    private IEnumerable<(Theme Theme, ModelLevel System, ModelLevel Default)> Themes()
    {
        yield return (Active, ModelLevel.ThemeSystem, ModelLevel.ThemeDefault);
        if (!ReferenceEquals(Active, Base))
        {
            yield return (Base, ModelLevel.BaseSystem, ModelLevel.BaseDefault);
        }
    }
}
