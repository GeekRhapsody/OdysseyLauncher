using System.Globalization;
using Launcher.Core;
using Launcher.Core.Config;
using Launcher.Core.Diagnostics;
using Launcher.Core.Models;
using Launcher.Core.Platform;
using Launcher.Core.Theming;
using Launcher.Core.Theming.Downloads;

/// <summary>
/// <c>inspect-theme</c>, the list owner's check before listing a theme (no network), and <c>themes</c>, the theme
/// downloader from the command line (A6 Downloading themes): the list and each theme are git clones, without credentials.
/// </summary>
internal static class ThemeCommands
{
    /// <summary>Checks a theme folder as the app would load it, its models against the spec and budgets; with --json, prints its covers block.</summary>
    public static int Inspect(string folder, bool json)
    {
        folder = Path.GetFullPath(folder);
        var manifest = Path.Combine(folder, ThemeLoader.ManifestFileName);
        if (!File.Exists(manifest))
        {
            Console.Error.WriteLine($"{manifest} doesn't exist: a theme's repository has its theme.toml at its top.");
            return 1;
        }

        var id = Path.GetFileName(folder.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
        var builtIns = BuiltIns();
        var problems = 0;
        if (!ThemeCatalog.IsValidId(id))
        {
            Console.WriteLine($"error: the folder's name, '{id}', isn't a valid theme id (lower-case letters, digits, '_' and '-'): the list's id names the installed folder, so pick one that is");
            problems++;
        }
        else if (builtIns.Any(s => s.Id == id))
        {
            Console.WriteLine($"error: '{id}' is a built-in theme's id: the list can't offer it");
            problems++;
        }

        var baseResult = ThemeCatalog.LoadBase(builtIns);
        var source = new ThemeSource(id, new ConfigFile(manifest, File.ReadAllText(manifest)), ThemeOrigin.User, folder, new FolderThemeFiles(folder));
        var result = ThemeLoader.Load(source, baseResult.Theme);
        foreach (var diagnostic in result.Diagnostics)
        {
            Console.WriteLine(diagnostic);
            problems += diagnostic.IsError ? 1 : 0;
        }

        if (result.Theme is not { } theme)
        {
            Console.WriteLine("The theme can't be used at all.");
            return 1;
        }

        // Every model the theme ships, against its kind's budget: the app inspects a user theme's models when it loads them.
        var models = theme.Templates.Values.Where(t => t.ThemeId == theme.Id && !t.ModelFromBase).Select(t => (t.Model, ModelKind.GameTemplate))
            .Concat(theme.Systems.Values.Where(s => s.Model is not null).Select(s => (s.Model!, ModelKind.SystemModel)))
            .Concat(theme.Defaults.SystemModel is { } card ? [(card, ModelKind.SystemModel)] : [])
            .Distinct()
            .ToList();
        foreach (var (model, kind) in models)
        {
            var path = theme.PathOf(model);
            var inspection = ModelInspector.Inspect(File.ReadAllBytes(path), kind);
            var report = inspection.Report;
            Console.WriteLine($"{model}: {report.Summary()}");
            foreach (var error in report.Errors)
            {
                Console.WriteLine($"  error: {error}");
                problems++;
            }

            foreach (var warning in report.Warnings)
            {
                Console.WriteLine($"  warning: {warning}");
            }
        }

        var covers = ThemeCovers.Of(theme);
        var size = Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories)
            .Where(f => !f.Contains($"{Path.DirectorySeparatorChar}.git{Path.DirectorySeparatorChar}", StringComparison.Ordinal))
            .Sum(f => new FileInfo(f).Length);
        Console.WriteLine(string.Create(CultureInfo.InvariantCulture,
            $"{theme.Name} by {theme.Author ?? "(no author)"}: {models.Count} model(s), {covers.SystemCards} system card(s) or logo(s), {covers.Templates} template(s), menus {(covers.Menus ? "yes" : "no")}, card videos {(covers.CardVideos ? "yes" : "no")}, game videos {(covers.GameVideos ? "yes" : "no")}; {size / (1024.0 * 1024):0.0} MB"));
        if (json)
        {
            Console.WriteLine("\"covers\": " + ThemeCoversJson.Serialize(covers));
        }

        Console.WriteLine(problems == 0 ? "No errors." : $"{problems} error(s).");
        return problems == 0 ? 0 : 1;
    }

    public static async Task<int> RunAsync(IPlatformPaths paths, string? listFolder, IReadOnlyList<string> arguments, bool replace, bool discardChanges, CancellationToken cancellation)
    {
        var builtIns = BuiltIns();
        var baseTheme = ThemeCatalog.LoadBase(builtIns).Theme;
        var downloads = new ThemeDownloads(new LibGit2Client(), ThemeDownloadPaths.For(paths), builtIns.Select(s => s.Id).ToList(), new QuietLog(),
            localList: listFolder, appVersion: AppVersion.Current);
        var progress = new Progress();
        var verb = arguments.Count > 0 ? arguments[0] : "list";
        Console.WriteLine($"Themes: {downloads.Paths.ThemesDir}");
        Console.WriteLine(listFolder is null ? $"List:   {ThemeDownloads.DefaultListUrl} ({downloads.ListFolder})" : $"List:   {listFolder}");
        var list = await downloads.RefreshAsync(progress, cancellation);
        progress.End();
        if (list.RefreshProblem is not null)
        {
            Console.Error.WriteLine($"Couldn't refresh the list ({list.RefreshProblem}): showing the copy from last time.");
        }

        foreach (var diagnostic in list.Index.Diagnostics)
        {
            Console.Error.WriteLine(diagnostic);
        }

        if (list.AppOutdated(downloads.AppVersion))
        {
            Console.WriteLine($"Odyssey Launcher {list.Index.LatestAppVersion} is out: some themes may need it.");
        }

        if (verb == "list")
        {
            foreach (var status in list.Themes)
            {
                Console.WriteLine($"  {status.Listing.Id,-24} {status.Listing.Name,-24} {Describe(status)}");
            }

            Console.WriteLine(list.Themes.Count == 0 ? "The list has no themes." : $"{list.Themes.Count} theme(s).");
            return 0;
        }

        if (arguments.Count < 2)
        {
            throw new ArgumentException("Give the theme's id: themes install|update|remove <id>.");
        }

        var listing = list.Themes.FirstOrDefault(t => t.Listing.Id == arguments[1])?.Listing
            ?? throw new ArgumentException($"The list has no theme '{arguments[1]}'.");
        try
        {
            switch (verb)
            {
                case "install":
                    {
                        var result = await downloads.InstallAsync(listing, baseTheme, replace, progress, cancellation);
                        progress.End();
                        Report(result);
                        return 0;
                    }

                case "update":
                    {
                        var result = await downloads.UpdateAsync(listing, baseTheme, discardChanges, progress, cancellation);
                        progress.End();
                        Report(result);
                        return 0;
                    }

                case "remove":
                    Console.WriteLine($"{listing.Name}: {Describe(await downloads.RemoveAsync(listing, cancellation))}");
                    return 0;
                default:
                    throw new ArgumentException($"Unknown: themes {verb}. Use list, install, update or remove.");
            }
        }
        catch (ThemeChangesException e)
        {
            progress.End();
            Console.Error.WriteLine(e.Message);
            Console.Error.WriteLine("  --discard-changes overwrites them (files git doesn't track stay).");
            return 1;
        }
        catch (GitException e)
        {
            progress.End();
            Console.Error.WriteLine(e.Message);
            if (e.Message.Contains("already a theme", StringComparison.Ordinal))
            {
                Console.Error.WriteLine("  --replace moves it to the backups folder and installs the listed theme.");
            }

            return 1;
        }
    }

    private static void Report(ThemeOperationResult result)
    {
        Console.WriteLine($"{result.Status.Listing.Name}: {(result.Updated ? string.Empty : "up to date; ")}{Describe(result.Status)}");
        if (result.BackupFolder is not null)
        {
            Console.WriteLine($"  The theme that was there is in {result.BackupFolder}");
        }

        foreach (var diagnostic in result.Diagnostics)
        {
            Console.WriteLine($"  {diagnostic}");
        }
    }

    private static string Describe(ThemeStatus status)
    {
        var state = status.State switch
        {
            ThemeInstallState.Installed => $"installed ({status.InstalledCommit?[..7]})",
            ThemeInstallState.ManualInstall => "another theme of that id is installed (--replace)",
            ThemeInstallState.Broken => "broken: an interrupted download (--replace)",
            _ => status.Listing.New ? "not installed (new)" : "not installed",
        };
        var notes = new List<string>();
        if (status.LocalChanges)
        {
            notes.Add("changes of your own");
        }

        if (status.NeedsNewerApp)
        {
            notes.Add($"needs {status.Listing.MinAppVersion}");
        }

        if (status.Listing.Deprecated)
        {
            notes.Add("leaving the list");
        }

        return notes.Count == 0 ? state : $"{state}; {string.Join(", ", notes)}";
    }

    // The app's own themes: beside the executable in an export, else the repository's godot/themes.
    private static List<ThemeSource> BuiltIns()
    {
        var beside = Path.Combine(AppContext.BaseDirectory, ThemeLoader.FolderName);
        var folder = Directory.Exists(Path.Combine(beside, ThemeCatalog.BaseId)) ? beside : null;
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); folder is null && dir is not null; dir = dir.Parent)
        {
            var candidate = Path.Combine(dir.FullName, "godot", ThemeLoader.FolderName);
            if (Directory.Exists(Path.Combine(candidate, ThemeCatalog.BaseId)))
            {
                folder = candidate;
            }
        }

        if (folder is null)
        {
            throw new ArgumentException("The app's themes (memory-card, the base) weren't found beside odyssey-scrape or in the repository's godot/themes.");
        }

        return ThemeCatalog.BuiltInSources(folder, []);
    }

    private sealed class QuietLog : ILog
    {
        public void Write(LogLevel level, string message)
        {
            if (level != LogLevel.Info)
            {
                Console.Error.WriteLine($"  {level}: {message}");
            }
        }
    }

    /// <summary>A download's progress, a line every 10%.</summary>
    private sealed class Progress : IProgress<GitProgress>
    {
        private int _shown = -1;

        public void Report(GitProgress value)
        {
            var step = (int)(value.Fraction * 10);
            if (value.TotalObjects > 0 && step != _shown)
            {
                _shown = step;
                Console.WriteLine(string.Create(CultureInfo.InvariantCulture, $"  {step * 10}% ({value.ReceivedObjects}/{value.TotalObjects} objects, {value.ReceivedBytes / 1024.0 / 1024:0.0} MB)"));
            }
        }

        public void End() => _shown = -1;
    }
}
