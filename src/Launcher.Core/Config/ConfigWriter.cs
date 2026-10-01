using System.Text;
using Launcher.Core.Scraping;

namespace Launcher.Core.Config;

/// <summary>The user's config files the settings screen writes (A5).</summary>
public enum ConfigFileKind
{
    Settings,
    Systems,
    Emulators,

    /// <summary><c>secrets.toml</c>: the scraping credentials, and the only file they're ever written to.</summary>
    Secrets,
}

/// <summary>One change to a user config file.</summary>
/// <param name="Path">The dotted key, as segments: <c>["systems", "snes", "rom_dirs"]</c>.</param>
/// <param name="Value">A <see cref="string"/>, <see cref="bool"/>, <see cref="long"/> or list of strings; null removes the key, so the built-in default applies again.</param>
public sealed record ConfigEdit(ConfigFileKind File, IReadOnlyList<string> Path, object? Value);

/// <summary>What <see cref="ConfigWriter.Save"/> did.</summary>
/// <param name="Problem">Why nothing was saved, written for the user; null when the edits were saved (or changed nothing).</param>
/// <param name="ChangedFiles">The files written: empty when every edit matched what the files already said.</param>
/// <param name="Config">Config as it now is (every file, with the edits); null when <paramref name="Problem"/> is set.</param>
/// <param name="Accounts">The credentials as they now are, when secrets.toml was edited.</param>
public sealed record ConfigSaveResult(
    string? Problem,
    IReadOnlyList<string> ChangedFiles,
    ConfigLoadResult? Config,
    AccountsLoadResult? Accounts)
{
    public bool Saved => Problem is null;
}

/// <summary>
/// Writes the settings screen's changes to the user's TOML files (M7), through <see cref="TomlEditor"/> so the user's
/// comments and layout survive, and with only what differs from the built-in defaults:
/// <list type="bullet">
/// <item>A key the file doesn't have is added only if the new value differs from the default.</item>
/// <item>A key set back to its default is removed, unless its line has a comment of the user's (then it's updated).</item>
/// <item>A null value removes the key (the default applies again).</item>
/// </list>
/// Before anything is written, the edited files are validated as the app would load them: an edit that makes config
/// report an error it didn't before (an unknown emulator, a bad placeholder, a wrong type) is refused and nothing is
/// written. Files are replaced atomically (a temporary file, then a move), keeping a byte order mark if they had one.
/// Credentials go to <c>secrets.toml</c> only, and no message quotes them.
/// <para>Does file I/O: never on the main thread.</para>
/// </summary>
public sealed class ConfigWriter(string configDir, string homeDir)
{
    private static readonly UTF8Encoding Utf8NoBom = new(false);

    /// <summary>For the reloaded config's install checks; null skips them (tests).</summary>
    public Func<string, bool>? FileExists { get; init; } = File.Exists;

    /// <summary>Which systems the reloaded config's install checks cover (<see cref="ConfigSources.CheckInstallsFor"/>); null covers all.</summary>
    public Func<string, bool>? CheckInstallsFor { get; init; }

    /// <summary>Reads <c>ODYSSEY_*</c> variables for the reloaded credentials.</summary>
    public Func<string, string?> Environment { get; init; } = System.Environment.GetEnvironmentVariable;

    public string ConfigDir { get; } = configDir ?? throw new ArgumentNullException(nameof(configDir));

    public static string FileName(ConfigFileKind kind) => kind switch
    {
        ConfigFileKind.Settings => ConfigSources.SettingsFileName,
        ConfigFileKind.Systems => ConfigSources.SystemsFileName,
        ConfigFileKind.Emulators => ConfigSources.EmulatorsFileName,
        _ => ProviderAccounts.FileName,
    };

    public string PathOf(ConfigFileKind kind) => Path.Combine(ConfigDir, FileName(kind));

    /// <summary>
    /// A folder or file path as config should hold it: '/' separators on Windows (as A5 recommends; <c>//server/share</c>
    /// still names a share), with braces doubled so a folder named <c>{x}</c> isn't read as a placeholder.
    /// </summary>
    public static string PathValue(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        var value = OperatingSystem.IsWindows() ? path.Replace('\\', '/') : path;
        return Template.Escape(value);
    }

    /// <summary>Loads config from the user's files, as the app does at boot.</summary>
    public ConfigLoadResult Load() =>
        new ConfigLoader().Load(ConfigSources.FromDirectory(ConfigDir, homeDir) with { FileExists = FileExists, CheckInstallsFor = CheckInstallsFor });

    /// <summary>Applies <paramref name="edits"/> and writes the files they change, or nothing if any edit is refused.</summary>
    public ConfigSaveResult Save(IReadOnlyList<ConfigEdit> edits)
    {
        ArgumentNullException.ThrowIfNull(edits);
        var before = new Dictionary<ConfigFileKind, FileText>();
        foreach (var kind in Enum.GetValues<ConfigFileKind>())
        {
            before[kind] = Read(kind);
        }

        var after = new Dictionary<ConfigFileKind, string?>();
        foreach (var group in edits.GroupBy(e => e.File))
        {
            var kind = group.Key;
            var original = before[kind];
            var editor = TomlEditor.Parse(original.Text ?? NewFileHeader(kind), PathOf(kind), out var syntax);
            if (editor is null)
            {
                return Refused($"{FileName(kind)} has a TOML syntax error at line {syntax!.Line}, column {syntax.Column}, so it can't be changed safely. Fix it by hand first (or delete the file to go back to the defaults).");
            }

            var defaults = Defaults(kind);
            try
            {
                foreach (var edit in group)
                {
                    Apply(editor, defaults, edit);
                }
            }
            catch (TomlEditException e)
            {
                return Refused($"{FileName(kind)}: {e.Message}");
            }

            var text = editor.ToString();
            if (text != (original.Text ?? NewFileHeader(kind)))
            {
                after[kind] = text;
            }
        }

        if (after.Count == 0)
        {
            return new ConfigSaveResult(null, [], null, null);
        }

        // Validate before writing anything: the edited files must load with no error the originals didn't have.
        ConfigLoadResult? config = null;
        if (after.Keys.Any(k => k != ConfigFileKind.Secrets))
        {
            var old = new ConfigLoader().Load(Sources(before, new Dictionary<ConfigFileKind, string?>()));
            config = new ConfigLoader().Load(Sources(before, after));
            var known = new HashSet<(string, string, string)>(old.Diagnostics.Where(d => d.IsError).Select(d => (d.Source, d.Key, d.Message)));
            if (config.Diagnostics.FirstOrDefault(d => d.IsError && !known.Contains((d.Source, d.Key, d.Message))) is { } problem)
            {
                return Refused($"Not saved: {(problem.Key.Length > 0 ? problem.Key + ": " : string.Empty)}{problem.Message}.");
            }
        }

        AccountsLoadResult? accounts = null;
        if (after.TryGetValue(ConfigFileKind.Secrets, out var secrets))
        {
            accounts = ProviderAccounts.Parse(secrets, PathOf(ConfigFileKind.Secrets), Environment);
            if (accounts.Diagnostics.FirstOrDefault(d => d.IsError) is { } problem)
            {
                return Refused($"Not saved: {problem.Key}: {problem.Message}.");
            }
        }

        Directory.CreateDirectory(ConfigDir);
        var written = new List<string>();
        foreach (var (kind, text) in after)
        {
            var path = PathOf(kind);
            WriteAtomically(path, text!, before[kind].Bom);
            written.Add(path);
        }

        return new ConfigSaveResult(null, written, config ?? Load(), accounts);
    }

    private static ConfigSaveResult Refused(string problem) => new(problem, [], null, null);

    private static void Apply(TomlEditor editor, TomlEditor? defaults, ConfigEdit edit)
    {
        if (edit.Value is null)
        {
            editor.Remove(edit.Path);
            return;
        }

        var value = edit.Value is int i ? (long)i : edit.Value;
        var present = editor.Contains(edit.Path);
        if (present && Same(editor.Get(edit.Path), value))
        {
            return;
        }

        var isDefault = defaults is not null && Same(defaults.Get(edit.Path), value);
        if (isDefault && !present)
        {
            return;
        }

        if (isDefault && !editor.HasTrailingComment(edit.Path))
        {
            editor.Remove(edit.Path);
            return;
        }

        editor.Set(edit.Path, value);
    }

    private static bool Same(object? a, object? b) => (a, b) switch
    {
        (IEnumerable<string> x, IEnumerable<string> y) => x.SequenceEqual(y, StringComparer.Ordinal),
        (null, _) or (_, null) => false,
        _ => a.Equals(b),
    };

    private static TomlEditor? Defaults(ConfigFileKind kind)
    {
        var file = kind switch
        {
            ConfigFileKind.Settings => BuiltInDefaults.Settings,
            ConfigFileKind.Systems => BuiltInDefaults.Systems,
            ConfigFileKind.Emulators => BuiltInDefaults.Emulators,
            _ => null,
        };
        return file is null ? null : TomlEditor.Parse(file.Text, file.Source, out _);
    }

    private static string NewFileHeader(ConfigFileKind kind) => kind switch
    {
        ConfigFileKind.Secrets =>
            "# Scraping credentials (ARCHITECTURE.md A5). Keep this file private: the launcher never logs, saves or shows\n" +
            "# these values anywhere else. ODYSSEY_* environment variables override them.\n",
        _ =>
            $"# Your {FileName(kind)}: only what differs from the built-in defaults. The settings screen writes here and\n" +
            "# keeps your comments; you can edit it by hand too.\nformat = 1\n",
    };

    private ConfigSources Sources(Dictionary<ConfigFileKind, FileText> before, Dictionary<ConfigFileKind, string?> after)
    {
        ConfigFile? File(ConfigFileKind kind)
        {
            var text = after.TryGetValue(kind, out var edited) ? edited : before[kind].Text;
            return text is null ? null : new ConfigFile(PathOf(kind), text);
        }

        return new ConfigSources
        {
            HomeDir = homeDir,
            ConfigDir = ConfigDir,
            Settings = File(ConfigFileKind.Settings),
            Systems = File(ConfigFileKind.Systems),
            Emulators = File(ConfigFileKind.Emulators),
            FileExists = FileExists,
            CheckInstallsFor = CheckInstallsFor,
        };
    }

    private readonly record struct FileText(string? Text, bool Bom);

    private FileText Read(ConfigFileKind kind)
    {
        var path = PathOf(kind);
        if (!System.IO.File.Exists(path))
        {
            return new FileText(null, false);
        }

        var bytes = System.IO.File.ReadAllBytes(path);
        var bom = bytes.AsSpan().StartsWith((ReadOnlySpan<byte>)[0xEF, 0xBB, 0xBF]);
        return new FileText(Encoding.UTF8.GetString(bom ? bytes.AsSpan(3) : bytes), bom);
    }

    private static void WriteAtomically(string path, string text, bool bom)
    {
        var temporary = path + ".saving";
        using (var stream = new FileStream(temporary, FileMode.Create, FileAccess.Write, FileShare.None))
        {
            if (bom)
            {
                stream.Write([0xEF, 0xBB, 0xBF]);
            }

            stream.Write(Utf8NoBom.GetBytes(text));
            stream.Flush(flushToDisk: true);
        }

        System.IO.File.Move(temporary, path, overwrite: true);
    }
}
