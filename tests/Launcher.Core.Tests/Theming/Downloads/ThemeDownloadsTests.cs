using Launcher.Core.Diagnostics;
using Launcher.Core.Tests.TestSupport;
using Launcher.Core.Theming;
using Launcher.Core.Theming.Downloads;
using LibGit2Sharp;

namespace Launcher.Core.Tests.Theming.Downloads;

/// <summary>
/// Theme downloads against git repositories made in a temp folder, cloned by their paths: no test touches the network.
/// </summary>
public sealed class ThemeDownloadsTests : IDisposable
{
    private static readonly string[] Reserved = ["memory-card", "console", "slab"];
    private static readonly Theme Base = ThemeFixtures.Base;

    private readonly TempDir _dir = new();
    private readonly ThemeDownloadPaths _paths;
    private readonly LibGit2Client _git = new();
    private readonly ManualClock _clock = new(new DateTimeOffset(2026, 10, 16, 12, 0, 0, TimeSpan.Zero));

    public ThemeDownloadsTests()
    {
        _paths = new ThemeDownloadPaths(_dir.Combine("config", "themes"), _dir.Combine("config", "themes-staging"),
            _dir.Combine("data", "theme-backups"), _dir.Combine("cache", "themes-list"));
    }

    public void Dispose() => _dir.Dispose();

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private string Installed(string id) => Path.Combine(_paths.ThemesDir, id);

    private ThemeDownloads Downloads(IGitClient? git = null, string? listUrl = null, string? localList = null, AppVersion? app = null) =>
        new(git ?? _git, _paths, Reserved, NullLog.Instance, listUrl, localList, app, _clock);

    private static ThemeListing Listing(Upstream upstream, string commit, string? minApp = null) =>
        new("neon", "Neon", "Someone", string.Empty, upstream.Url, commit, null, minApp, false, false, null, []);

    [Fact]
    public async Task Installing_clones_the_pinned_commit_into_the_themes_folder()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var pinned = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"), ("readme.txt", "one"));
        upstream.Commit("Neon 2, not tested yet", ("readme.txt", "two"));

        var result = await Downloads().InstallAsync(Listing(upstream, pinned), Base, replace: false, cancellation: Ct);

        Assert.Equal((ThemeInstallState.Installed, pinned, false, false),
            (result.Status.State, result.Status.InstalledCommit, result.Status.UpdateAvailable, result.Status.LocalChanges));
        Assert.Equal("one", File.ReadAllText(Path.Combine(Installed("neon"), "readme.txt")));
        Assert.Empty(result.Diagnostics);
        Assert.Null(result.BackupFolder);
        Assert.False(Directory.Exists(_paths.StagingDir));

        // The catalog finds it as any user theme.
        Assert.Equal("neon", Assert.Single(ThemeCatalog.UserSources(_paths.ThemesDir, [])).Id);
    }

    [Fact]
    public async Task A_new_pinned_commit_is_an_update_known_without_fetching_and_untracked_files_survive_it()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var first = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"), ("readme.txt", "one"));
        var downloads = Downloads();
        await downloads.InstallAsync(Listing(upstream, first), Base, replace: false, cancellation: Ct);
        File.WriteAllText(Path.Combine(Installed("neon"), "mine.txt"), "the user's own");
        var second = upstream.Commit("Neon 2", ("readme.txt", "two"));

        var status = await downloads.InspectAsync(Listing(upstream, second), cancellation: Ct);
        Assert.Equal((ThemeInstallState.Installed, first, true, false),
            (status.State, status.InstalledCommit, status.UpdateAvailable, status.LocalChanges));

        var result = await downloads.UpdateAsync(Listing(upstream, second), Base, discardChanges: false, cancellation: Ct);

        Assert.Equal((second, false), (result.Status.InstalledCommit, result.Status.UpdateAvailable));
        Assert.Equal("two", File.ReadAllText(Path.Combine(Installed("neon"), "readme.txt")));
        Assert.Equal("the user's own", File.ReadAllText(Path.Combine(Installed("neon"), "mine.txt")));
    }

    [Fact]
    public async Task Changes_to_tracked_files_are_overwritten_only_when_the_user_says_so()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var first = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"), ("readme.txt", "one"));
        var downloads = Downloads();
        await downloads.InstallAsync(Listing(upstream, first), Base, replace: false, cancellation: Ct);
        File.WriteAllText(Path.Combine(Installed("neon"), "readme.txt"), "edited");
        var second = upstream.Commit("Neon 2", ("readme.txt", "two"));

        Assert.True((await downloads.InspectAsync(Listing(upstream, second), cancellation: Ct)).LocalChanges);
        var refused = await Assert.ThrowsAsync<GitException>(() => downloads.UpdateAsync(Listing(upstream, second), Base, discardChanges: false, cancellation: Ct));
        Assert.Contains("changes of your own", refused.Message, StringComparison.Ordinal);
        Assert.Equal("edited", File.ReadAllText(Path.Combine(Installed("neon"), "readme.txt")));

        var result = await downloads.UpdateAsync(Listing(upstream, second), Base, discardChanges: true, cancellation: Ct);

        Assert.Equal((second, false), (result.Status.InstalledCommit, result.Status.LocalChanges));
        Assert.Equal("two", File.ReadAllText(Path.Combine(Installed("neon"), "readme.txt")));
    }

    [Fact]
    public async Task A_theme_put_there_by_hand_is_replaced_only_when_asked_and_kept_in_the_backups()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var pinned = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"));
        _dir.File("config/themes/neon/theme.toml", "name = \"My Neon\"\n");
        var downloads = Downloads();

        Assert.Equal(ThemeInstallState.ManualInstall, (await downloads.InspectAsync(Listing(upstream, pinned), cancellation: Ct)).State);
        await Assert.ThrowsAsync<GitException>(() => downloads.InstallAsync(Listing(upstream, pinned), Base, replace: false, cancellation: Ct));
        Assert.Equal("name = \"My Neon\"\n", File.ReadAllText(Path.Combine(Installed("neon"), "theme.toml")));

        var result = await downloads.InstallAsync(Listing(upstream, pinned), Base, replace: true, cancellation: Ct);

        Assert.Equal(ThemeInstallState.Installed, result.Status.State);
        // Named by the local time it was replaced.
        Assert.Equal(Path.Combine(_paths.BackupsDir, $"neon-{_clock.GetLocalNow():yyyyMMdd-HHmmss}"), result.BackupFolder);
        Assert.Equal("name = \"My Neon\"\n", File.ReadAllText(Path.Combine(result.BackupFolder!, "theme.toml")));
        Assert.Equal("name = \"Neon\"\n", File.ReadAllText(Path.Combine(Installed("neon"), "theme.toml")));
    }

    [Fact]
    public async Task A_clone_of_another_repository_or_an_empty_one_isnt_the_listed_theme()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var pinned = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"));
        using var fork = new Upstream(_dir.Combine("upstream", "fork"));
        fork.Commit("Fork", ("theme.toml", "name = \"Neon fork\"\n"));
        Repository.Clone(fork.Url, Installed("neon"));
        var downloads = Downloads();

        Assert.Equal(ThemeInstallState.ManualInstall, (await downloads.InspectAsync(Listing(upstream, pinned), cancellation: Ct)).State);

        // A clone interrupted before its first checkout: the listed origin, but nothing in it.
        FolderTreeDelete(Installed("neon"));
        using (var empty = new Repository(Repository.Init(Installed("neon"))))
        {
            empty.Network.Remotes.Add("origin", upstream.Url);
        }

        Assert.Equal(ThemeInstallState.Broken, (await downloads.InspectAsync(Listing(upstream, pinned), cancellation: Ct)).State);
    }

    [Fact]
    public async Task An_interrupted_clone_never_reaches_the_themes_folder_and_is_cleared_next_time()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var pinned = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"));
        var downloads = Downloads(new InterruptedClone(_git));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => downloads.InstallAsync(Listing(upstream, pinned), Base, replace: false, cancellation: Ct));

        Assert.False(Directory.Exists(Installed("neon")));
        Assert.False(Directory.Exists(_paths.StagingDir));

        // A quit mid-clone leaves the staging folder; opening the downloader clears it.
        _dir.File("config/themes-staging/neon/theme.toml", "name = \"Half\"\n");
        _dir.File("list/themes.json", "{ \"format\": 1, \"themes\": [] }");
        await Downloads(localList: _dir.Combine("list")).RefreshAsync(cancellation: Ct);
        Assert.False(Directory.Exists(_paths.StagingDir));
    }

    [Fact]
    public async Task Removing_deletes_the_clone_with_its_read_only_objects()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var pinned = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"));
        var downloads = Downloads();
        await downloads.InstallAsync(Listing(upstream, pinned), Base, replace: false, cancellation: Ct);
        Assert.Contains(Directory.EnumerateFiles(Path.Combine(Installed("neon"), ".git", "objects"), "*", SearchOption.AllDirectories),
            f => File.GetAttributes(f).HasFlag(FileAttributes.ReadOnly));

        var status = await downloads.RemoveAsync(Listing(upstream, pinned), cancellation: Ct);

        Assert.Equal(ThemeInstallState.NotInstalled, status.State);
        Assert.False(Directory.Exists(Installed("neon")));
    }

    [Fact]
    public async Task A_version_the_launcher_cant_use_is_refused_and_an_update_to_one_rolled_back()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var good = upstream.Commit("Neon 1", ("theme.toml", "name = \"Neon\"\n"));
        var future = upstream.Commit("Neon for a later launcher", ("theme.toml", "format = 2\nname = \"Neon\"\n"));
        var downloads = Downloads();

        var refused = await Assert.ThrowsAsync<GitException>(() => downloads.InstallAsync(Listing(upstream, future), Base, replace: false, cancellation: Ct));
        Assert.Contains("can't be used by this version", refused.Message, StringComparison.Ordinal);
        Assert.False(Directory.Exists(Installed("neon")));

        await downloads.InstallAsync(Listing(upstream, good), Base, replace: false, cancellation: Ct);
        await Assert.ThrowsAsync<GitException>(() => downloads.UpdateAsync(Listing(upstream, future), Base, discardChanges: false, cancellation: Ct));
        Assert.Equal(good, (await downloads.InspectAsync(Listing(upstream, good), cancellation: Ct)).InstalledCommit);
    }

    [Fact]
    public async Task A_repository_without_a_manifest_at_its_top_or_needing_a_newer_launcher_isnt_installed()
    {
        using var upstream = new Upstream(_dir.Combine("upstream", "neon"));
        var nested = upstream.Commit("Theme in a subfolder", ("neon/theme.toml", "name = \"Neon\"\n"));
        var downloads = Downloads(app: AppVersion.TryParse("0.16.0", out var app) ? app : null);

        var noManifest = await Assert.ThrowsAsync<GitException>(() => downloads.InstallAsync(Listing(upstream, nested), Base, replace: false, cancellation: Ct));
        Assert.Contains("no theme.toml at its top", noManifest.Message, StringComparison.Ordinal);

        var tooNew = Listing(upstream, nested, minApp: "0.17.0");
        Assert.True((await downloads.InspectAsync(tooNew, cancellation: Ct)).NeedsNewerApp);
        var refused = await Assert.ThrowsAsync<GitException>(() => downloads.InstallAsync(tooNew, Base, replace: false, cancellation: Ct));
        Assert.Contains("needs Odyssey Launcher 0.17.0", refused.Message, StringComparison.Ordinal);
        Assert.False(Directory.Exists(Installed("neon")));
    }

    [Fact]
    public async Task The_list_is_cloned_then_refreshed_and_last_times_copy_is_read_offline()
    {
        using var list = new Upstream(_dir.Combine("upstream", "list"));
        list.Commit("One theme", ("themes.json", ListJson("neon")), ("screenshots/neon/01.webp", "x"));
        var downloads = Downloads(listUrl: list.Url);

        Assert.Empty((await downloads.ReadCachedAsync(cancellation: Ct)).Themes);
        var first = await downloads.RefreshAsync(cancellation: Ct);
        Assert.Equal((true, null), (first.Refreshed, first.RefreshProblem));
        Assert.Equal(["neon"], first.Themes.Select(t => t.Listing.Id));
        Assert.Equal(Path.Combine(_paths.ListDir, "screenshots", "neon", "01.webp"), first.Index.Themes[0].Screenshots[0].Image);
        Assert.True(File.Exists(first.Index.Themes[0].Screenshots[0].Image));

        // A change made to the clone is discarded, as ES-DE does.
        File.WriteAllText(Path.Combine(_paths.ListDir, "themes.json"), "broken");
        list.Commit("Two themes", ("themes.json", ListJson("neon", "retro")));
        var second = await downloads.RefreshAsync(cancellation: Ct);
        Assert.Equal(["neon", "retro"], second.Themes.Select(t => t.Listing.Id));

        // Offline: the list from last time, and why it's not newer.
        list.Dispose();
        FolderTreeDelete(list.Folder);
        var offline = await downloads.RefreshAsync(cancellation: Ct);
        Assert.False(offline.Refreshed);
        Assert.NotNull(offline.RefreshProblem);
        Assert.Equal(["neon", "retro"], offline.Themes.Select(t => t.Listing.Id));
    }

    [Fact]
    public void The_list_says_when_the_launcher_is_older_than_its_latest_release()
    {
        var index = new ThemeIndex("0.17.0", [], []);
        var result = new ThemeListResult(index, [], null, true);

        Assert.True(result.AppOutdated(AppVersion.TryParse("0.16.0", out var old) ? old : null));
        Assert.False(result.AppOutdated(AppVersion.TryParse("0.17.0", out var same) ? same : null));
        Assert.False(result.AppOutdated(null));
    }

    [Theory]
    [InlineData("https://github.com/a/b.git", "https://github.com/a/b", true)]
    [InlineData("https://github.com/A/B/", "https://github.com/a/b.git", true)]
    [InlineData("https://github.com/a/b.git", "https://github.com/a/c.git", false)]
    public void Repository_urls_are_compared_loosely(string a, string b, bool same) =>
        Assert.Equal(same, ThemeInventory.SameRepository(a, b));

    private static string ListJson(params string[] ids) =>
        "{ \"format\": 1, \"themes\": [" + string.Join(",", ids.Select(id =>
            $"{{ \"id\": \"{id}\", \"name\": \"{id}\", \"url\": \"https://example.invalid/{id}.git\", \"commit\": \"{new string('a', 40)}\", " +
            $"\"screenshots\": [{{ \"image\": \"screenshots/{id}/01.webp\", \"caption\": \"Systems\" }}] }}")) + "] }";

    private static void FolderTreeDelete(string folder)
    {
        foreach (var file in Directory.EnumerateFiles(folder, "*", new EnumerationOptions { RecurseSubdirectories = true, AttributesToSkip = 0 }))
        {
            File.SetAttributes(file, FileAttributes.Normal);
        }

        Directory.Delete(folder, recursive: true);
    }

    /// <summary>A theme's (or the list's) repository, committed to by the test.</summary>
    private sealed class Upstream : IDisposable
    {
        private static readonly Signature Author = new("Theme Author", "author@example.invalid", new DateTimeOffset(2026, 10, 1, 0, 0, 0, TimeSpan.Zero));
        private readonly Repository _repo;

        public Upstream(string folder)
        {
            Folder = folder;
            Directory.CreateDirectory(folder);
            _repo = new Repository(Repository.Init(folder));
        }

        public string Folder { get; }

        /// <summary>A file URL (a bare path that's gone looks to libgit2 like an ssh address).</summary>
        public string Url => new Uri(Folder).AbsoluteUri;

        public string Commit(string message, params (string Path, string Text)[] files)
        {
            foreach (var (path, text) in files)
            {
                var full = Path.Combine(Folder, path.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(full)!);
                File.WriteAllText(full, text);
                Commands.Stage(_repo, path);
            }

            return _repo.Commit(message, Author, Author).Sha;
        }

        public void Dispose() => _repo.Dispose();
    }

    /// <summary>A clone that's cancelled halfway, leaving files behind as libgit2 would.</summary>
    private sealed class InterruptedClone(IGitClient inner) : IGitClient
    {
        public void Clone(string url, string folder, IProgress<GitProgress>? progress, CancellationToken cancellation)
        {
            Directory.CreateDirectory(Path.Combine(folder, ".git"));
            File.WriteAllText(Path.Combine(folder, ".git", "HEAD"), "ref: refs/heads/main\n");
            throw new OperationCanceledException();
        }

        public bool IsRepository(string folder) => inner.IsRepository(folder);

        public void Fetch(string folder, IProgress<GitProgress>? progress, CancellationToken cancellation) => inner.Fetch(folder, progress, cancellation);

        public string? HeadCommit(string folder) => inner.HeadCommit(folder);

        public string? OriginUrl(string folder) => inner.OriginUrl(folder);

        public bool HasCommit(string folder, string commit) => inner.HasCommit(folder, commit);

        public bool HasLocalChanges(string folder) => inner.HasLocalChanges(folder);

        public bool HasTrackedFiles(string folder) => inner.HasTrackedFiles(folder);

        public void CheckOut(string folder, string commit) => inner.CheckOut(folder, commit);

        public void ResetToRemote(string folder) => inner.ResetToRemote(folder);
    }
}
