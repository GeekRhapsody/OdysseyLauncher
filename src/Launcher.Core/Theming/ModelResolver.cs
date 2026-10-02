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

/// <summary>Where a model candidate comes from, in precedence order (A7).</summary>
public enum ModelLevel
{
    /// <summary><c>DataDir/media/&lt;system&gt;/model/&lt;rel path&gt;.glb</c>, indexed by the scanner.</summary>
    UserGame,

    /// <summary><c>ConfigDir/models/templates/&lt;system&gt;.glb</c>, or for a card <c>ConfigDir/models/systems/&lt;system&gt;.glb</c>.</summary>
    User,

    /// <summary>The user's <c>game_model</c> for the system in systems.toml: a template id in the active theme, else the built-in one.</summary>
    GameModelSetting,

    /// <summary>The active theme's <c>[systems.&lt;id&gt;]</c> entry.</summary>
    ThemeSystem,

    /// <summary>The active theme's <c>[defaults]</c>.</summary>
    ThemeDefault,

    /// <summary>The built-in theme's <c>[systems.&lt;id&gt;]</c> entry (when another theme is active).</summary>
    BuiltInSystem,

    /// <summary>The built-in theme's <c>[defaults]</c>.</summary>
    BuiltInDefault,
}

/// <summary>One model a game or a system card can use, if it loads.</summary>
/// <param name="Origin">
/// <see cref="ThemeOrigin.BuiltIn"/>: a <c>.glb</c> in the app's PCK (<c>res://</c>). <see cref="ThemeOrigin.User"/>: a
/// <c>.glb</c> file on disk (the user's own models, and user themes'). Both are loaded at run time.
/// </param>
/// <param name="Path">A <c>res://</c> path or an absolute file path.</param>
/// <param name="Template">The theme's template, with its slot chains; null for a user model (default chains).</param>
/// <param name="Tint">For a system card: whether its plain materials take the system's colour.</param>
/// <param name="Description">For logs: "theme 'memory-card' template 'dvd_case'".</param>
public sealed record ModelCandidate(ModelLevel Level, ThemeOrigin Origin, string Path, GameTemplate? Template, bool Tint, string Description)
{
    /// <summary>
    /// Two candidates are the same grid template if they load the same file with the same chains and tint: a key that
    /// dedupes them across systems and precedence levels.
    /// </summary>
    public string Key => $"{Path}|{Template?.Id}|{(Tint ? "tint" : "plain")}";

    /// <summary>The slot's chain: the template's, or the default for a user model.</summary>
    public SlotChain ChainFor(int slot, bool systemCard) =>
        systemCard ? SlotChain.ForSystemModel(slot) : Template?.ChainFor(slot) ?? SlotChain.Default(slot);
}

/// <summary>
/// Works out, for each system, which models its games and its card can use, in precedence order (A7), and its look
/// and colour. Pure: the user's model files are listed beforehand (<see cref="UserModels.Find"/>) and per-game models
/// come from the library, so nothing is probed per item.
/// <para>
/// Games: the per-game model; <c>ConfigDir/models/templates/&lt;system&gt;.glb</c>; the user's <c>game_model</c>; the
/// active theme's template for the system; its default template; then the built-in theme's two. Cards:
/// <c>ConfigDir/models/systems/&lt;system&gt;.glb</c>; the active theme's model for the system; its default; then the
/// built-in theme's. The app loads candidates in order and uses the first that loads, so a broken or rejected model
/// falls through to the next.
/// </para>
/// </summary>
public sealed class ModelResolver
{
    private readonly AppConfig _config;
    private readonly UserModels _user;
    private readonly string _dataDir;
    private readonly List<Diagnostic> _diagnostics = [];

    /// <param name="active">The theme settings.toml names (or the built-in one).</param>
    /// <param name="builtIn">The built-in default theme, always the last resort.</param>
    /// <param name="dataDir">Where the media folder is, which per-game models' paths are relative to.</param>
    public ModelResolver(Theme active, Theme builtIn, UserModels user, AppConfig config, string dataDir)
    {
        Active = active ?? throw new ArgumentNullException(nameof(active));
        BuiltIn = builtIn ?? throw new ArgumentNullException(nameof(builtIn));
        _user = user ?? throw new ArgumentNullException(nameof(user));
        _config = config ?? throw new ArgumentNullException(nameof(config));
        _dataDir = dataDir ?? throw new ArgumentNullException(nameof(dataDir));
        foreach (var system in config.Systems)
        {
            if (system.GameModel is { } id && !active.Templates.ContainsKey(id) && !builtIn.Templates.ContainsKey(id))
            {
                var known = active.Templates.Keys.Concat(builtIn.Templates.Keys).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal).ToList();
                _diagnostics.Add(new Diagnostic(Severity.Warning, Path.Combine(user.ConfigDir, ConfigSources.SystemsFileName), 0, 0,
                    $"systems.{system.Id}.game_model",
                    $"no template '{id}' in the theme '{active.Id}' or the built-in theme, so the theme's choice is used. The templates are {string.Join(", ", known)}"));
            }
        }
    }

    public Theme Active { get; }

    public Theme BuiltIn { get; }

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

        if (_config.FindSystem(systemId)?.GameModel is { } gameModel)
        {
            var owner = Active.Templates.ContainsKey(gameModel) ? Active : BuiltIn.Templates.ContainsKey(gameModel) ? BuiltIn : null;
            if (owner is not null)
            {
                Add(ModelLevel.GameModelSetting, owner, owner.Templates[gameModel], $"game_model '{gameModel}'");
            }
        }

        foreach (var (theme, systemLevel, defaultLevel) in Themes())
        {
            if (theme.Systems.TryGetValue(systemId, out var entry) && entry.GameTemplate is { } id)
            {
                Add(systemLevel, theme, theme.Templates[id], $"[systems.{systemId}]");
            }

            if (theme.Defaults.GameTemplate is { } fallback)
            {
                Add(defaultLevel, theme, theme.Templates[fallback], "[defaults]");
            }
        }

        return candidates;

        void Add(ModelLevel level, Theme theme, GameTemplate template, string where)
        {
            var candidate = new ModelCandidate(level, theme.Origin, theme.PathOf(template.Model), template, false,
                $"theme '{theme.Id}' template '{template.Id}' ({where})");
            if (!candidates.Exists(c => c.Key == candidate.Key))
            {
                candidates.Add(candidate);
            }
        }
    }

    /// <summary>The per-game model, from its <c>media</c> row (kind <c>model</c>, a path relative to DataDir).</summary>
    public ModelCandidate PerGame(string relativePath)
    {
        ArgumentNullException.ThrowIfNull(relativePath);
        return new ModelCandidate(ModelLevel.UserGame, ThemeOrigin.User,
            Path.GetFullPath(Path.Combine(_dataDir, relativePath.Replace('/', Path.DirectorySeparatorChar))), null, false,
            $"your {relativePath}");
    }

    /// <summary>The candidates for a system's card, best first, without repeats. Null for Favourites and Recently played.</summary>
    public IReadOnlyList<ModelCandidate> SystemModels(string? systemId)
    {
        var candidates = new List<ModelCandidate>();
        if (systemId is not null && _user.Systems.Contains(systemId))
        {
            candidates.Add(new ModelCandidate(ModelLevel.User, ThemeOrigin.User, _user.SystemPath(systemId), null, false,
                $"your models/systems/{systemId}.glb"));
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
            var candidate = new ModelCandidate(level, theme.Origin, theme.PathOf(model), null, tint, $"theme '{theme.Id}' {model} ({where})");
            if (!candidates.Exists(c => c.Key == candidate.Key))
            {
                candidates.Add(candidate);
            }
        }
    }

    /// <summary>The system's colour (its card's tint and its plain boxes'): the active theme's, else the built-in theme's.</summary>
    public Rgb? ColourOf(string systemId) =>
        Active.Systems.TryGetValue(systemId, out var entry) && entry.Colour is { } colour ? colour
        : BuiltIn.Systems.TryGetValue(systemId, out var builtIn) ? builtIn.Colour : null;

    /// <summary>The active theme's look for a system's games (null: the systems grid).</summary>
    public Look LookFor(string? systemId) => Active.LookFor(systemId);

    private IEnumerable<(Theme Theme, ModelLevel System, ModelLevel Default)> Themes()
    {
        yield return (Active, ModelLevel.ThemeSystem, ModelLevel.ThemeDefault);
        if (!ReferenceEquals(Active, BuiltIn))
        {
            yield return (BuiltIn, ModelLevel.BuiltInSystem, ModelLevel.BuiltInDefault);
        }
    }
}
