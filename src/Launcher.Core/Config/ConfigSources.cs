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

    /// <summary>The OS's own built-in settings, merged over <see cref="DefaultSettings"/>: Linux's; none on Windows.</summary>
    public ConfigFile? PlatformSettings { get; init; } = BuiltInDefaults.PlatformSettings;

    /// <summary>The OS's own built-in systems, merged over <see cref="DefaultSystems"/>: Linux's; none on Windows.</summary>
    public ConfigFile? PlatformSystems { get; init; } = BuiltInDefaults.PlatformSystems;

    public ConfigFile? Settings { get; init; }

    public ConfigFile? Systems { get; init; }

    public ConfigFile? Emulators { get; init; }

    /// <summary>
    /// Checks that each emulator's executable and core exist, so a missing install is reported at load with the
    /// systems it affects. Null skips the check (tests, and callers that check later). Does file I/O: the loader
    /// must never run on the main thread.
    /// </summary>
    public Func<string, bool>? FileExists { get; init; } = File.Exists;

    /// <summary>
    /// Which systems the install check covers, by id; null covers every enabled system. The app passes the systems
    /// that have games, so the long built-in list doesn't warn about every emulator the user never installed.
    /// </summary>
    public Func<string, bool>? CheckInstallsFor { get; init; }

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

/// <summary>
/// The defaults embedded in Launcher.Core (<c>Defaults/*.toml</c>, ARCHITECTURE.md A5). Each OS has its own complete
/// emulators file, its programs being other programs in other places; the systems and settings are shared, with
/// Linux's own values (its systems' emulators, the variables its profiles look in) in a file merged over them.
/// </summary>
public static class BuiltInDefaults
{
    public const string WindowsEmulatorsFileName = "emulators.windows.toml";
    public const string LinuxEmulatorsFileName = "emulators.linux.toml";
    public const string LinuxSettingsFileName = "settings.linux.toml";
    public const string LinuxSystemsFileName = "systems.linux.toml";

    public static ConfigFile Settings { get; } = Read(ConfigSources.SettingsFileName);

    public static ConfigFile Systems { get; } = Read(ConfigSources.SystemsFileName);

    public static ConfigFile Emulators { get; } = Read(OperatingSystem.IsWindows() ? WindowsEmulatorsFileName : LinuxEmulatorsFileName);

    public static ConfigFile? PlatformSettings { get; } = OperatingSystem.IsWindows() ? null : Read(LinuxSettingsFileName);

    public static ConfigFile? PlatformSystems { get; } = OperatingSystem.IsWindows() ? null : Read(LinuxSystemsFileName);

    /// <summary>One embedded default by its file name, whatever the OS (the tests read Linux's on Windows).</summary>
    public static ConfigFile Read(string fileName)
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("defaults/" + fileName)
            ?? throw new InvalidOperationException($"The embedded default {fileName} is missing.");
        using var reader = new StreamReader(stream);
        return new ConfigFile("built-in/" + fileName, reader.ReadToEnd());
    }
}
