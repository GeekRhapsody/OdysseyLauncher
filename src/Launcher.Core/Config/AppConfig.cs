namespace Launcher.Core.Config;

/// <summary>The merged, validated configuration. Only enabled, valid entries are present.</summary>
public sealed record AppConfig(
    Settings Settings,
    IReadOnlyList<SystemConfig> Systems,
    IReadOnlyDictionary<string, EmulatorConfig> Emulators)
{
    /// <summary>A linear search: there are a few dozen systems at most, and a cached map would go stale under <c>with</c>.</summary>
    public SystemConfig? FindSystem(string id)
    {
        foreach (var system in Systems)
        {
            if (string.Equals(system.Id, id, StringComparison.Ordinal))
            {
                return system;
            }
        }

        return null;
    }
}

/// <summary><c>settings.toml</c>.</summary>
/// <param name="RomRoot">Absolute, expanded <c>paths.rom_root</c>.</param>
/// <param name="Variables">Expanded <c>[variables]</c>: plain strings, no placeholders left.</param>
public sealed record Settings(
    int Format,
    string RomRoot,
    IReadOnlyDictionary<string, string> Variables,
    DisplaySettings Display,
    ScrapingSettings Scraping);

public sealed record DisplaySettings(string Theme, bool Fullscreen);

public sealed record ScrapingSettings(
    IReadOnlyList<string> Regions,
    IReadOnlyList<string> Languages,
    IReadOnlyList<string> CoverSources);

public enum RomDirSource
{
    /// <summary>
    /// No <c>rom_dirs</c> in config. <see cref="SystemConfig.RomDirs"/> lists the candidates
    /// <c>{rom_root}/&lt;id&gt;</c> then <c>{rom_root}/&lt;alias&gt;</c>..., and the scanner uses the first that exists.
    /// </summary>
    Default,

    /// <summary><c>rom_dirs</c> is set. Every folder is scanned, in order; earlier folders win path collisions.</summary>
    Configured,
}

/// <summary>A <c>[systems.&lt;id&gt;]</c> entry.</summary>
/// <param name="Extensions">Lower-case, each starting with '.'.</param>
/// <param name="RomDirs">Absolute folders; see <see cref="RomDirSource"/>.</param>
/// <param name="Exclude">Glob patterns matched against paths relative to a ROM folder.</param>
public sealed record SystemConfig(
    string Id,
    string Name,
    string? Manufacturer,
    int? Year,
    IReadOnlyList<string> Aliases,
    IReadOnlyList<string> Extensions,
    string Emulator,
    IReadOnlyList<string> AltEmulators,
    string GameModel,
    int? ScreenScraperId,
    IReadOnlyList<string> RomDirs,
    RomDirSource RomDirSource,
    bool Recursive,
    IReadOnlyList<string> Exclude);

/// <summary>An <c>[emulators.&lt;id&gt;]</c> entry.</summary>
/// <param name="Executable">Expanded path, with no placeholders left.</param>
/// <param name="Args">Templates: config variables are expanded, launch placeholders remain (A5).</param>
/// <param name="WorkingDir">Template, like <paramref name="Args"/>.</param>
public sealed record EmulatorConfig(
    string Id,
    string Name,
    string Executable,
    IReadOnlyList<string> Args,
    string WorkingDir);

public sealed record ConfigLoadResult(AppConfig Config, IReadOnlyList<Diagnostic> Diagnostics)
{
    public bool HasErrors => Diagnostics.Any(d => d.IsError);
}

public interface IConfigLoader
{
    /// <summary>Loads, merges and validates. Never throws for user mistakes: they become diagnostics.</summary>
    ConfigLoadResult Load(ConfigSources sources);
}
