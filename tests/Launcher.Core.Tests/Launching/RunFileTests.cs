using System.Diagnostics;
using Launcher.Core.Config;
using Launcher.Core.Launching;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Launching;

/// <summary>Profiles with <c>run_file = true</c> run the game's own file (a program, a script or a shortcut), never through cmd.exe's argument parsing.</summary>
public sealed class RunFileTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private static ConfigLoadResult Load(string emulators) =>
        new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = "C:/home",
            ConfigDir = "C:/config",
            Emulators = new ConfigFile("user/emulators.toml", emulators),
            FileExists = null,
        });

    // ---- Config ---------------------------------------------------------------------------------

    [Fact]
    public void A_run_file_profile_needs_no_program_and_works_in_the_games_folder()
    {
        var result = Load("""
            [emulators.shortcut]
            name = "Shortcut"
            run_file = true
            """);

        Assert.Empty(result.Diagnostics);
        var profile = result.Config.Emulators["shortcut"];
        Assert.True(profile.RunFile);
        Assert.Equal(string.Empty, profile.Executable);
        Assert.Empty(profile.Args);
        Assert.Equal("{rom_dir}", profile.WorkingDir);
        Assert.Equal("Runs the game's own file", profile.ProgramText);
    }

    [Theory]
    [InlineData("executable = \"C:/x/x.exe\"", "emulators.shortcut.executable")]
    [InlineData("args = [\"{rom}\"]", "emulators.shortcut.args")]
    [InlineData("core = \"C:/x/core.dll\"", "emulators.shortcut.core")]
    public void A_run_file_profile_with_a_program_core_or_arguments_is_an_error_and_is_disabled(string extra, string key)
    {
        var result = Load($"""
            [emulators.shortcut]
            name = "Shortcut"
            run_file = true
            {extra}
            """);

        Assert.Contains(result.Diagnostics, d => d.Severity == Severity.Error && d.Key == key
            && d.Message.Contains("run_file profile runs the game's own file", StringComparison.Ordinal));
        Assert.False(result.Config.Emulators.ContainsKey("shortcut"));
    }

    [Fact]
    public void A_new_run_file_profile_still_needs_a_name()
    {
        var result = Load("""
            [emulators.shortcut]
            run_file = true
            """);

        Assert.Contains(result.Diagnostics, d => d.Severity == Severity.Error && d.Message.Contains("missing: name", StringComparison.Ordinal));
        Assert.False(result.Config.Emulators.ContainsKey("shortcut"));
    }

    [Fact]
    public void The_install_check_skips_run_file_profiles_and_the_built_in_one_is_there()
    {
        var checkedPaths = new List<string>();
        var result = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = "C:/home",
            ConfigDir = "C:/config",
            FileExists = path =>
            {
                checkedPaths.Add(path);
                return false;
            },
        });

        var runFile = result.Config.Emulators["run-file"];
        Assert.True(runFile.RunFile);
        Assert.DoesNotContain(result.Diagnostics, d => d.Key.StartsWith("emulators.run-file", StringComparison.Ordinal));
        Assert.DoesNotContain(string.Empty, checkedPaths);
        Assert.Equal("run-file", result.Config.FindSystem("ports")!.Emulator);
    }

    // ---- Planning -------------------------------------------------------------------------------

    [Fact]
    public void A_run_file_plan_runs_the_rom_itself_with_no_arguments_in_its_folder()
    {
        var profile = Load("""
            [emulators.shortcut]
            name = "Shortcut"
            run_file = true
            """).Config.Emulators["shortcut"];
        var rom = _dir.File("ROMs/ports/Sonic & Knuckles/start.bat");

        var plan = LaunchPlanner.Plan(profile, "ports", rom).Plan!;

        Assert.True(plan.RunFile);
        Assert.Equal(Path.GetFullPath(rom), plan.Executable);
        Assert.Empty(plan.Arguments);
        Assert.Equal(Path.GetDirectoryName(Path.GetFullPath(rom)), plan.WorkingDirectory);
        Assert.Null(plan.Core);
    }

    // ---- The Windows runner ---------------------------------------------------------------------

    private static async Task<ProcessOutcome> RunToEnd(LaunchPlan plan)
    {
        using var running = PlatformServices.CreateProcessRunner().Start(plan);
        return await running.Completion.WaitAsync(TimeSpan.FromSeconds(30), TestContext.Current.CancellationToken);
    }

    [Fact]
    public async Task A_batch_file_whose_name_has_shell_characters_runs_as_itself_and_runs_nothing_else()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Batch files and cmd.exe are Windows-only.");
        var folder = _dir.Combine("ROMs", "ports");
        Directory.CreateDirectory(folder);
        var script = Path.Combine(folder, "Sonic & copy NUL pwned.txt & Knuckles (Zone) ^ 100 ! 'n'.bat");
        await File.WriteAllTextAsync(script, "@echo off\r\necho ran> \"%~dp0ran.txt\"\r\nexit /b 7\r\n", TestContext.Current.CancellationToken);

        var outcome = await RunToEnd(new LaunchPlan("run-file", "Run", script, [], folder, null, RunFile: true));

        Assert.Equal(7, outcome.ExitCode);
        Assert.True(File.Exists(Path.Combine(folder, "ran.txt")), "the batch file ran");
        Assert.False(File.Exists(Path.Combine(folder, "pwned.txt")), "nothing after '&' in the name ran");
        Assert.False(File.Exists(Path.Combine(Directory.GetCurrentDirectory(), "pwned.txt")));
    }

    [Fact]
    public async Task A_script_with_a_percent_sign_in_its_path_is_refused_because_cmd_would_expand_it()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Batch files and cmd.exe are Windows-only.");
        var folder = _dir.Combine("ROMs", "ports");
        Directory.CreateDirectory(folder);
        var script = Path.Combine(folder, "100% Orange Juice.bat");
        await File.WriteAllTextAsync(script, "@exit /b 0\r\n", TestContext.Current.CancellationToken);

        var failure = Assert.Throws<ProcessStartException>(() =>
            PlatformServices.CreateProcessRunner().Start(new LaunchPlan("run-file", "Run", script, [], folder, null, RunFile: true)));

        Assert.Contains("% in its path", failure.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_program_runs_as_itself_and_its_exit_code_comes_back()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Windows-only.");
        var exe = FakeEmulator.InstallAt(_dir.Combine("Programs ü", "Game"), "Game ü.exe");
        var folder = Path.GetDirectoryName(exe)!;

        // The fake exits 0 with no arguments; its working folder is the one the plan names.
        var outcome = await RunToEnd(new LaunchPlan("run-file", "Run", exe, [], folder, null, RunFile: true));

        Assert.Equal(0, outcome.ExitCode);
    }

    [Fact]
    public async Task A_shortcut_is_opened_by_the_shell_and_the_program_it_starts_is_followed_to_its_end()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Shortcuts are Windows-only.");
        var folder = _dir.Combine("ROMs", "ports");
        Directory.CreateDirectory(folder);
        var shortcut = Path.Combine(folder, "Game ü & co.lnk");
        MakeShortcut(shortcut, Path.Combine(Environment.SystemDirectory, "cmd.exe"), "/c exit 5");

        var outcome = await RunToEnd(new LaunchPlan("run-file", "Run", shortcut, [], folder, null, RunFile: true));

        Assert.Equal(5, outcome.ExitCode);
        Assert.True(outcome.Elapsed < TimeSpan.FromSeconds(20));
    }

    [Fact]
    public async Task A_detached_file_is_opened_by_the_shell_and_what_it_starts_isnt_followed()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Shortcuts are Windows-only.");
        var folder = _dir.Combine("ROMs", "steam");
        Directory.CreateDirectory(folder);
        var shortcut = Path.Combine(folder, "Hands over.lnk");
        var marker = Path.Combine(folder, "ran.txt");
        MakeShortcut(shortcut, Path.Combine(Environment.SystemDirectory, "cmd.exe"), $"/c ping -n 4 127.0.0.1 >NUL & echo ran> \"{marker}\" & exit 5");

        var outcome = await RunToEnd(new LaunchPlan("run-file", "Steam", shortcut, [], folder, null, RunFile: true, Detached: true));

        // Ended at once with nothing followed, while what the shell started runs on (about 3 s).
        Assert.Equal(new ProcessOutcome(0, outcome.Elapsed, false), outcome);
        Assert.True(outcome.Elapsed < TimeSpan.FromSeconds(2), $"took {outcome.Elapsed}");
        Assert.False(File.Exists(marker));
        var deadline = Stopwatch.StartNew();
        while (!File.Exists(marker) && deadline.Elapsed < TimeSpan.FromSeconds(20))
        {
            await Task.Delay(100, TestContext.Current.CancellationToken);
        }

        Assert.True(File.Exists(marker), "the shortcut's program ran");
    }

    [Fact]
    public void A_file_the_shell_cannot_open_is_a_readable_start_failure()
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "Windows error mapping.");
        var folder = _dir.Combine("ROMs", "ports");
        Directory.CreateDirectory(folder);
        var missing = Path.Combine(folder, "gone.lnk");

        var failure = Assert.Throws<ProcessStartException>(() =>
            PlatformServices.CreateProcessRunner().Start(new LaunchPlan("run-file", "Run", missing, [], folder, null, RunFile: true)));

        Assert.Contains(missing, failure.Message, StringComparison.Ordinal);
    }

    private static void MakeShortcut(string path, string target, string arguments)
    {
        var script = $"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{path.Replace("'", "''")}');" +
            $"$s.TargetPath='{target.Replace("'", "''")}';$s.Arguments='{arguments}';$s.WindowStyle=7;$s.Save()";
        var info = new ProcessStartInfo("powershell.exe")
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardError = true,
        };
        info.ArgumentList.Add("-NoProfile");
        info.ArgumentList.Add("-NonInteractive");
        info.ArgumentList.Add("-Command");
        info.ArgumentList.Add(script);
        using var process = Process.Start(info)!;
        var error = process.StandardError.ReadToEnd();
        process.WaitForExit();
        Assert.True(process.ExitCode == 0 && File.Exists(path), $"couldn't make the shortcut: {error}");
    }
}
