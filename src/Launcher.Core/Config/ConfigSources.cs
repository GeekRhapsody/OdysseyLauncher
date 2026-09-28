using System.Reflection;

namespace Launcher.Core.Config;

/// <summary>The text of one config file, and the name diagnostics use for it.</summary>
public sealed record ConfigFile(string Source, string Text);

/// <summary>
/// Everything the loader reads. Parsers take text rather than paths, so the app can also feed files
/// from its PCK. Missing user files are null; the defaults are the embedded ones unless replaced.
/// </summary>
public sealed record ConfigSources
{
    public const string SettingsFileName = "settings.toml";
    public const string SystemsFileName = "systems.toml";
    public const string EmulatorsFileName = "emulators.toml";

    /// <summary>Resolves <c>{home}</c>.</summary>
    public required string HomeDir { get; init; }

    /// <summary>Relative paths in config resolve against this folder (A5).</summary>
    public required string ConfigDir { get; init; }

    public ConfigFile DefaultSettings { get; init; } = BuiltInDefaults.Settings;

    public ConfigFile DefaultSystems { get; init; } = BuiltInDefaults.Systems;

    public ConfigFile DefaultEmulators { get; init; } = BuiltInDefaults.Emulators;

    public ConfigFile? Settings { get; init; }

    public ConfigFile? Systems { get; init; }

    public ConfigFile? Emulators { get; init; }

    /// <summary>Reads the user's files from <paramref name="configDir"/>. Does file I/O: never call it on the main thread.</summary>
    public static ConfigSources FromDirectory(string configDir, string homeDir)
    {
        ArgumentNullException.ThrowIfNull(configDir);
        ArgumentNullException.ThrowIfNull(homeDir);
        return new ConfigSources
        {
            HomeDir = homeDir,
            ConfigDir = configDir,
            Settings = ReadIfExists(Path.Combine(configDir, SettingsFileName)),
            Systems = ReadIfExists(Path.Combine(configDir, SystemsFileName)),
            Emulators = ReadIfExists(Path.Combine(configDir, EmulatorsFileName)),
        };
    }

    private static ConfigFile? ReadIfExists(string path) =>
        File.Exists(path) ? new ConfigFile(path, File.ReadAllText(path)) : null;
}

/// <summary>The defaults embedded in Launcher.Core (<c>Defaults/*.toml</c>).</summary>
public static class BuiltInDefaults
{
    public static ConfigFile Settings { get; } = Load(ConfigSources.SettingsFileName);

    public static ConfigFile Systems { get; } = Load(ConfigSources.SystemsFileName);

    public static ConfigFile Emulators { get; } = Load(ConfigSources.EmulatorsFileName);

    private static ConfigFile Load(string fileName)
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("defaults/" + fileName)
            ?? throw new InvalidOperationException($"The embedded default {fileName} is missing.");
        using var reader = new StreamReader(stream);
        return new ConfigFile("built-in/" + fileName, reader.ReadToEnd());
    }
}
