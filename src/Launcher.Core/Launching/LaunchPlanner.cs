using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.Core.Launching;

/// <summary>What to run for one launch: every placeholder is expanded and each argument is final.</summary>
/// <param name="Executable">Absolute path.</param>
/// <param name="Arguments">
/// One entry per argument, exactly as the emulator should see it in its <c>argv</c>. The process runner does the
/// OS's quoting; nothing here is quoted.
/// </param>
/// <param name="Core">The profile's expanded <c>core</c>, if it has one, so the launch can check that it exists.</param>
/// <param name="RunFile">
/// The profile runs the game's own file (A5 <c>run_file</c>): <paramref name="Executable"/> is the ROM, with no
/// arguments. The process runner starts it the way Windows would open it (a program, a shortcut, or a script), and
/// never through a command line that includes anything but its own path.
/// </param>
/// <param name="Detached">
/// A <paramref name="RunFile"/> plan whose file hands the game to another program that runs it (a Steam shortcut):
/// the runner opens the file as the shell would, and doesn't follow what that starts. The launch service follows
/// the game another way (<see cref="SteamGame"/>).
/// </param>
public sealed record LaunchPlan(
    string EmulatorId,
    string EmulatorName,
    string Executable,
    IReadOnlyList<string> Arguments,
    string WorkingDirectory,
    string? Core,
    bool RunFile = false,
    bool Detached = false);

/// <summary>A plan, or the reason there isn't one.</summary>
public sealed record LaunchPlanResult(LaunchPlan? Plan, string? Error)
{
    public bool IsOk => Plan is not null;
}

/// <summary>
/// Resolves a game's emulator profile and expands its templates (ARCHITECTURE.md A5). Pure: no file system and
/// no clock, so every rule is unit-tested. The launch service checks that the files exist.
/// </summary>
public static class LaunchPlanner
{
    /// <summary>
    /// The emulator is, in order: <paramref name="emulatorOverride"/> (chosen for this launch), the game's own
    /// override from userdata.db, then the system's <c>emulator</c>. A named emulator that isn't configured is an
    /// error rather than a silent fallback, because the game may only work with the one it names.
    /// </summary>
    public static LaunchPlanResult Plan(AppConfig config, GameDetails game, string? emulatorOverride = null)
    {
        ArgumentNullException.ThrowIfNull(config);
        ArgumentNullException.ThrowIfNull(game);

        var system = config.FindSystem(game.Key.SystemId);
        if (system is null)
        {
            return Fail($"The system '{game.Key.SystemId}' isn't enabled in systems.toml.");
        }

        var emulatorId = emulatorOverride ?? game.EmulatorOverride ?? system.Emulator;
        if (!config.Emulators.TryGetValue(emulatorId, out var emulator))
        {
            var source = emulatorOverride is not null
                ? "was chosen for this launch"
                : game.EmulatorOverride is not null ? "is set for this game" : $"is {system.Name}'s emulator";
            return Fail($"The emulator '{emulatorId}' {source}, but it isn't configured, or it's disabled or has errors. " +
                "Check emulators.toml, or pick another emulator.");
        }

        return Plan(emulator, system.Id, game.RomPath);
    }

    /// <summary>Expands <paramref name="emulator"/>'s templates for one ROM.</summary>
    /// <param name="romPath">Absolute path.</param>
    public static LaunchPlanResult Plan(EmulatorConfig emulator, string systemId, string romPath)
    {
        ArgumentNullException.ThrowIfNull(emulator);
        ArgumentNullException.ThrowIfNull(systemId);
        ArgumentNullException.ThrowIfNull(romPath);

        var rom = Path.GetFullPath(romPath);
        var values = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["rom"] = rom,
            ["rom_dir"] = Path.GetDirectoryName(rom) ?? rom,
            ["rom_file"] = Path.GetFileName(rom),
            ["rom_stem"] = Path.GetFileNameWithoutExtension(rom),
            ["system"] = systemId,
            ["emulator"] = emulator.RunFile ? rom : emulator.Executable,
            ["emulator_dir"] = Path.GetDirectoryName(emulator.RunFile ? rom : emulator.Executable) ?? rom,
        };
        if (emulator.Core is not null)
        {
            values["core"] = emulator.Core;
        }

        var arguments = new List<string>(emulator.Args.Count);
        foreach (var template in emulator.Args)
        {
            var (argument, error) = Expand(template, values);
            if (error is not null)
            {
                return Fail($"emulators.{emulator.Id}.args: {error}");
            }

            arguments.Add(argument!);
        }

        var (workingDir, wdError) = Expand(emulator.WorkingDir, values);
        if (wdError is not null)
        {
            return Fail($"emulators.{emulator.Id}.working_dir: {wdError}");
        }

        return new LaunchPlanResult(
            new LaunchPlan(
                emulator.Id, emulator.Name, emulator.RunFile ? rom : emulator.Executable, arguments, workingDir!, emulator.Core,
                emulator.RunFile),
            null);
    }

    /// <summary>
    /// Single-pass expansion: values are inserted as they are, and never re-read, so a ROM named <c>{x}.zip</c>
    /// stays literal. <c>{{</c> and <c>}}</c> become single braces. An argument can't contain a NUL character,
    /// because the OS would cut it short there.
    /// </summary>
    public static (string? Value, string? Error) Expand(string template, IReadOnlyDictionary<string, string> values)
    {
        ArgumentNullException.ThrowIfNull(template);
        ArgumentNullException.ThrowIfNull(values);

        var parts = new List<TemplatePart>();
        if (Template.TryParse(template, parts) is { } syntaxError)
        {
            return (null, syntaxError);
        }

        var result = new StringBuilder(template.Length + 64);
        foreach (var part in parts)
        {
            if (!part.IsPlaceholder)
            {
                result.Append(part.Text);
            }
            else if (values.TryGetValue(part.Text, out var value))
            {
                result.Append(value);
            }
            else
            {
                return (null, part.Text == "core"
                    ? "{core} is used, but this profile has no core"
                    : $"unknown placeholder {{{part.Text}}}");
            }
        }

        var expanded = result.ToString();
        return expanded.Contains('\0', StringComparison.Ordinal)
            ? (null, "an argument contains a NUL character")
            : (expanded, null);
    }

    private static LaunchPlanResult Fail(string error) => new(null, error);
}
