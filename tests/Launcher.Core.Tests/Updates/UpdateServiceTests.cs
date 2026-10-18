using System.IO.Compression;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using Launcher.Core.Diagnostics;
using Launcher.Core.Tests.TestSupport;
using Launcher.Core.Theming.Downloads;
using Launcher.Core.Updates;

namespace Launcher.Core.Tests.Updates;

public sealed class UpdateServiceTests : IDisposable
{
    private const string Platform = "windows-x86_64";
    private const string Api = "https://api.github.com/repos/GeekRhapsody/OdysseyLauncher/releases";
    private static readonly AppVersion Current = Version("0.16.0");

    private readonly TempDir _dir = new();
    private readonly FakeHttpHandler _http = new();
    private readonly HttpClient _client;

    public UpdateServiceTests()
    {
        _client = new HttpClient(_http, disposeHandler: false);
    }

    public void Dispose()
    {
        Assert.Empty(_http.Unmatched);
        _client.Dispose();
        _http.Dispose();
        _dir.Dispose();
    }

    private string InstallDir => _dir.Combine("Odyssey Launcher");

    private static AppVersion Version(string text) => AppVersion.TryParse(text, out var version) ? version : throw new ArgumentException(text);

    private UpdateService Service(IReleaseSource? source = null) =>
        new(source ?? new GitHubReleaseSource(_client), InstallDir, "OdysseyLauncher.exe", Platform, NullLog.Instance);

    /// <summary>A release as GitHub's API lists it, with its package (and digest, unless null) and optionally its .sha256 file.</summary>
    private static string Release(string version, bool prerelease = false, bool draft = false, string? digest = "", bool checksumFile = false, string platform = Platform)
    {
        var name = $"OdysseyLauncher-{version}-{platform}.zip";
        var digestJson = digest is null ? string.Empty : $"\"digest\": \"sha256:{(digest.Length == 0 ? new string('a', 64) : digest)}\",";
        var checksum = checksumFile
            ? $$""", { "name": "{{name}}.sha256", "size": 100, "browser_download_url": "https://github.com/GeekRhapsody/OdysseyLauncher/releases/download/v{{version}}/{{name}}.sha256" }"""
            : string.Empty;
        return $$"""
            {
              "tag_name": "v{{version}}", "name": "Odyssey Launcher {{version}}", "draft": {{(draft ? "true" : "false")}},
              "prerelease": {{(prerelease ? "true" : "false")}}, "body": "What's new in {{version}}.",
              "html_url": "https://github.com/GeekRhapsody/OdysseyLauncher/releases/tag/v{{version}}",
              "assets": [
                { "name": "{{name}}", "size": 1000, {{digestJson}}
                  "browser_download_url": "https://github.com/GeekRhapsody/OdysseyLauncher/releases/download/v{{version}}/{{name}}" }{{checksum}}
              ]
            }
            """;
    }

    private static string List(params string[] releases) => "[" + string.Join(",", releases) + "]";

    private void ServeList(string json) =>
        _http.On("GET", u => u.AbsoluteUri.StartsWith(Api, StringComparison.Ordinal), _ => FakeHttpHandler.Json(json));

    private void ServeFile(string name, byte[] bytes) =>
        _http.On("GET", u => u.AbsolutePath.EndsWith("/" + name, StringComparison.Ordinal), _ => FakeHttpHandler.Bytes(bytes, "application/octet-stream"));

    /// <summary>A package as the release workflow zips it: one folder, named after the package, with the export in it.</summary>
    private static byte[] Package(string version, Action<ZipArchive>? more = null, bool pck = true)
    {
        using var memory = new MemoryStream();
        using (var zip = new ZipArchive(memory, ZipArchiveMode.Create, leaveOpen: true))
        {
            var root = $"OdysseyLauncher-{version}-{Platform}/";
            Entry(zip, root + "OdysseyLauncher.exe", "new exe " + version);
            if (pck)
            {
                Entry(zip, root + "OdysseyLauncher.pck", "new pck " + version);
            }

            Entry(zip, root + "data_OdysseyLauncher_windows_x86_64/Launcher.Core.dll", "new dll");
            Entry(zip, root + "themes/slab/theme.toml", "name = \"Slab\"");
            more?.Invoke(zip);
        }

        return memory.ToArray();
    }

    private static void Entry(ZipArchive zip, string name, string content)
    {
        using var writer = new StreamWriter(zip.CreateEntry(name).Open(), Encoding.UTF8);
        writer.Write(content);
    }

    private static string Sha256(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    private void InstallOld()
    {
        _dir.File("Odyssey Launcher/OdysseyLauncher.exe", "old exe");
        _dir.File("Odyssey Launcher/OdysseyLauncher.pck", "old pck");
        _dir.File("Odyssey Launcher/portable.txt");
        _dir.File("Odyssey Launcher/userdata/library.db", "the user's library");
    }

    // ---- The releases list -------------------------------------------------------------------------------

    [Fact]
    public void The_newest_release_newer_than_this_one_is_offered()
    {
        var releases = ReleaseFeed.Parse(List(Release("0.15.0"), Release("0.17.0"), Release("0.16.1")), Platform);

        Assert.Equal(Version("0.17.0"), ReleaseFeed.Newest(releases, Current)?.Version);
        Assert.Null(ReleaseFeed.Newest(releases, Version("0.17.0")));
        Assert.Null(ReleaseFeed.Newest(releases, Version("0.18.0")));
    }

    [Fact]
    public void Pre_releases_are_offered_only_to_a_pre_release()
    {
        var releases = ReleaseFeed.Parse(List(Release("0.16.1"), Release("0.17.0-beta.2", prerelease: true), Release("0.17.0-beta.1", prerelease: true)), Platform);

        Assert.Equal(Version("0.16.1"), ReleaseFeed.Newest(releases, Current)?.Version);
        Assert.Equal(Version("0.17.0-beta.2"), ReleaseFeed.Newest(releases, Version("0.17.0-beta.1"))?.Version);
    }

    [Fact]
    public void Drafts_other_platforms_and_tags_that_arent_versions_are_left_out()
    {
        var json = List(
            Release("0.18.0", draft: true),
            Release("0.17.0", platform: "linux-x86_64"),
            """{ "tag_name": "nightly", "assets": [] }""",
            """{ "tag_name": "v0.17.1" }""",
            "42",
            Release("0.16.1"));

        var releases = ReleaseFeed.Parse(json, Platform);

        var release = Assert.Single(releases);
        Assert.Equal(Version("0.16.1"), release.Version);
        Assert.Equal("v0.16.1", release.Tag);
        Assert.Equal("Odyssey Launcher 0.16.1", release.Title);
        Assert.Equal("What's new in 0.16.1.", release.Notes);
        Assert.Equal(new string('a', 64), release.Package.Sha256);
        Assert.Equal(1000, release.Package.Size);
    }

    [Fact]
    public void A_download_url_must_be_https_or_relative_to_a_local_feed()
    {
        var json = """
            [{ "tag_name": "v0.17.0", "assets": [{ "name": "OdysseyLauncher-0.17.0-windows-x86_64.zip", "browser_download_url": "OdysseyLauncher-0.17.0-windows-x86_64.zip" }] },
             { "tag_name": "v0.16.1", "assets": [{ "name": "OdysseyLauncher-0.16.1-windows-x86_64.zip", "browser_download_url": "http://example.com/OdysseyLauncher-0.16.1-windows-x86_64.zip" }] }]
            """;

        Assert.Empty(ReleaseFeed.Parse(json, Platform));
        var local = ReleaseFeed.Parse(json, Platform, new Uri(_dir.Path + Path.DirectorySeparatorChar));
        Assert.Equal(Path.Combine(_dir.Path, "OdysseyLauncher-0.17.0-windows-x86_64.zip"), local[0].Package.Url.LocalPath);
    }

    [Fact]
    public void A_checksum_file_is_read_as_sha256sum_writes_it()
    {
        var hex = new string('B', 64);

        Assert.Equal(new string('b', 64), Checksums.FromChecksumFile($"﻿{hex}  OdysseyLauncher-0.17.0-windows-x86_64.zip"));
        Assert.Equal(new string('b', 64), Checksums.FromChecksumFile(hex));
        Assert.Null(Checksums.FromChecksumFile("not a checksum"));
        Assert.Null(Checksums.FromChecksumFile(hex[..63]));
    }

    [Fact]
    public void Generated_release_notes_are_summed_up_as_plain_lines()
    {
        var notes = """
            ## What's Changed
            * PSP model by @GeekRhapsody in https://github.com/GeekRhapsody/OdysseyLauncher/pull/12
            * **Check for updates** in the settings
            - A very long line that goes on and on about what changed in the launcher, far longer than one line of the dialog should be
            * Four
            * Five
            * Six

            **Full Changelog**: https://github.com/GeekRhapsody/OdysseyLauncher/compare/v0.16.0...v0.17.0
            """;

        var summary = ReleaseFeed.Summary(notes, maxLines: 3, maxLength: 60);

        Assert.Equal(4, summary.Count);
        Assert.Equal("• PSP model", summary[0]);
        Assert.Equal("• Check for updates in the settings", summary[1]);
        Assert.StartsWith("• A very long line", summary[2], StringComparison.Ordinal);
        Assert.InRange(summary[2].Length, 50, 62);
        Assert.EndsWith("…", summary[2], StringComparison.Ordinal);
        Assert.Equal("…and 3 more.", summary[3]);
        Assert.Empty(ReleaseFeed.Summary(string.Empty));
    }

    // ---- Checking -------------------------------------------------------------------------------------

    [Fact]
    public async Task A_check_asks_GitHub_for_the_releases()
    {
        ServeList(List(Release("0.17.0"), Release("0.16.0")));

        var check = await Service().CheckAsync(Current, TestContext.Current.CancellationToken);

        Assert.Equal(Version("0.17.0"), check.Available?.Version);
        var request = Assert.Single(_http.Requests);
        Assert.StartsWith(Api, request.Uri.AbsoluteUri, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Up_to_date_is_no_release_to_offer()
    {
        ServeList(List(Release("0.16.0"), Release("0.15.0")));

        var check = await Service().CheckAsync(Current, TestContext.Current.CancellationToken);

        Assert.Null(check.Available);
        Assert.Equal(Current, check.Current);
    }

    [Fact]
    public async Task GitHubs_rate_limit_is_explained()
    {
        _http.On("GET", u => u.AbsoluteUri.StartsWith(Api, StringComparison.Ordinal), _ =>
        {
            var response = FakeHttpHandler.Text("rate limited", HttpStatusCode.Forbidden);
            response.Headers.Add("X-RateLimit-Remaining", "0");
            return response;
        });

        var e = await Assert.ThrowsAsync<UpdateException>(() => Service().CheckAsync(Current, TestContext.Current.CancellationToken));

        Assert.Contains("60 checks an hour", e.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Offline_is_explained()
    {
        _http.Offline = true;

        var e = await Assert.ThrowsAsync<UpdateException>(() => Service().CheckAsync(Current, TestContext.Current.CancellationToken));

        Assert.Contains("couldn't be reached", e.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_list_that_isnt_json_is_explained()
    {
        ServeList("<html>");

        var e = await Assert.ThrowsAsync<UpdateException>(() => Service().CheckAsync(Current, TestContext.Current.CancellationToken));

        Assert.Contains("couldn't be read", e.Message, StringComparison.Ordinal);
    }

    // ---- Downloading ----------------------------------------------------------------------------------

    [Fact]
    public async Task A_download_is_checked_and_unpacked_beside_the_launcher()
    {
        InstallOld();
        var zip = Package("0.17.0");
        ServeList(List(Release("0.17.0", digest: Sha256(zip))));
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip", zip);
        _dir.File("Odyssey Launcher/.odyssey-update/new/stale.txt", "from an earlier try");
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);
        var progress = new List<UpdateProgress>();

        var staged = await service.DownloadAsync(check.Available!, new SyncProgress(progress), TestContext.Current.CancellationToken);

        Assert.Equal(Path.Combine(InstallDir, ".odyssey-update"), staged.StagingDir);
        Assert.Equal(Path.Combine(InstallDir, ".odyssey-update", "new", "OdysseyLauncher-0.17.0-windows-x86_64"), staged.PackageDir);
        Assert.Equal("new pck 0.17.0", File.ReadAllText(Path.Combine(staged.PackageDir, "OdysseyLauncher.pck")));
        Assert.True(File.Exists(Path.Combine(staged.PackageDir, "themes", "slab", "theme.toml")));
        Assert.False(File.Exists(Path.Combine(staged.StagingDir, "new", "stale.txt")));
        Assert.False(File.Exists(Path.Combine(staged.StagingDir, "OdysseyLauncher-0.17.0-windows-x86_64.zip")));
        Assert.Equal("old pck", File.ReadAllText(Path.Combine(InstallDir, "OdysseyLauncher.pck")));
        Assert.Contains(progress, p => p.Stage == UpdateStage.Downloading && p.Done == zip.Length && p.Total == zip.Length);
        Assert.Contains(progress, p => p.Stage == UpdateStage.Extracting && p.Done == p.Total);
    }

    [Fact]
    public async Task Without_a_digest_the_releases_checksum_file_is_used()
    {
        InstallOld();
        var zip = Package("0.17.0");
        ServeList(List(Release("0.17.0", digest: null, checksumFile: true)));
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip", zip);
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip.sha256", Encoding.ASCII.GetBytes($"{Sha256(zip)}  OdysseyLauncher-0.17.0-windows-x86_64.zip"));
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);

        var staged = await service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken);

        Assert.True(File.Exists(Path.Combine(staged.PackageDir, "OdysseyLauncher.exe")));
    }

    [Fact]
    public async Task A_release_with_no_checksum_isnt_downloaded()
    {
        InstallOld();
        ServeList(List(Release("0.17.0", digest: null)));
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);

        var e = await Assert.ThrowsAsync<UpdateException>(() => service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken));

        Assert.Contains("no checksum", e.Message, StringComparison.Ordinal);
        Assert.Single(_http.Requests);
    }

    [Fact]
    public async Task A_download_that_doesnt_match_its_checksum_is_refused()
    {
        InstallOld();
        ServeList(List(Release("0.17.0", digest: new string('0', 64))));
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip", Package("0.17.0"));
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);

        var e = await Assert.ThrowsAsync<UpdateException>(() => service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken));

        Assert.Contains("doesn't match its checksum", e.Message, StringComparison.Ordinal);
        Assert.False(Directory.Exists(Path.Combine(service.StagingDir, "new")));
        Assert.Equal("old pck", File.ReadAllText(Path.Combine(InstallDir, "OdysseyLauncher.pck")));
    }

    [Fact]
    public async Task A_zip_entry_outside_its_folder_is_refused()
    {
        InstallOld();
        var zip = Package("0.17.0", z => Entry(z, "../escaped.txt", "outside"));
        ServeList(List(Release("0.17.0", digest: Sha256(zip))));
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip", zip);
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);

        var e = await Assert.ThrowsAsync<UpdateException>(() => service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken));

        Assert.Contains("outside its folder", e.Message, StringComparison.Ordinal);
        Assert.False(File.Exists(Path.Combine(service.StagingDir, "escaped.txt")));
    }

    [Theory]
    [InlineData("userdata/library.db")]
    [InlineData("portable.txt")]
    [InlineData("override.cfg")]
    public async Task A_package_that_would_replace_the_users_files_is_refused(string file)
    {
        InstallOld();
        var zip = Package("0.17.0", z => Entry(z, $"OdysseyLauncher-0.17.0-{Platform}/{file}", "not yours"));
        ServeList(List(Release("0.17.0", digest: Sha256(zip))));
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip", zip);
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);

        var e = await Assert.ThrowsAsync<UpdateException>(() => service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken));

        Assert.Contains("which would replace yours", e.Message, StringComparison.Ordinal);
        Assert.Equal("the user's library", File.ReadAllText(Path.Combine(InstallDir, "userdata", "library.db")));
    }

    [Fact]
    public async Task A_package_without_the_launchers_pck_is_refused()
    {
        InstallOld();
        var zip = Package("0.17.0", pck: false);
        ServeList(List(Release("0.17.0", digest: Sha256(zip))));
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip", zip);
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);

        var e = await Assert.ThrowsAsync<UpdateException>(() => service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken));

        Assert.Contains("no OdysseyLauncher.pck", e.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task A_package_without_the_installers_helper_is_refused()
    {
        InstallOld();
        var without = Package("0.17.0");
        var with = Package("0.17.0", z => Entry(z, $"OdysseyLauncher-0.17.0-{Platform}/OdysseyUpdater.exe", "helper"));
        ServeList(List(Release("0.17.0", digest: Sha256(without)), Release("0.17.1", digest: Sha256(with))));
        ServeFile("OdysseyLauncher-0.17.0-windows-x86_64.zip", without);
        ServeFile("OdysseyLauncher-0.17.1-windows-x86_64.zip", with);
        var service = new UpdateService(new GitHubReleaseSource(_client), InstallDir, "OdysseyLauncher.exe", Platform, NullLog.Instance, "OdysseyUpdater.exe");
        var releases = ReleaseFeed.Parse(List(Release("0.17.0", digest: Sha256(without)), Release("0.17.1", digest: Sha256(with))), Platform);

        var e = await Assert.ThrowsAsync<UpdateException>(() => service.DownloadAsync(releases[0], null, TestContext.Current.CancellationToken));
        var staged = await service.DownloadAsync(releases[1], null, TestContext.Current.CancellationToken);

        Assert.Contains("no OdysseyUpdater.exe", e.Message, StringComparison.Ordinal);
        Assert.True(File.Exists(Path.Combine(staged.PackageDir, "OdysseyUpdater.exe")));
    }

    [Fact]
    public async Task A_local_feed_is_read_from_its_folder()
    {
        InstallOld();
        var feed = _dir.Combine("feed");
        Directory.CreateDirectory(feed);
        var zip = Package("0.17.0");
        File.WriteAllBytes(Path.Combine(feed, "OdysseyLauncher-0.17.0-windows-x86_64.zip"), zip);
        File.WriteAllText(Path.Combine(feed, LocalReleaseSource.ListFileName), $$"""
            [{ "tag_name": "v0.17.0", "assets": [{ "name": "OdysseyLauncher-0.17.0-windows-x86_64.zip", "size": {{zip.Length}},
               "digest": "sha256:{{Sha256(zip)}}", "browser_download_url": "OdysseyLauncher-0.17.0-windows-x86_64.zip" }] }]
            """);
        var service = Service(new LocalReleaseSource(feed));

        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);
        var staged = await service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken);

        Assert.Equal("new exe 0.17.0", File.ReadAllText(Path.Combine(staged.PackageDir, "OdysseyLauncher.exe")));
        Assert.Empty(_http.Requests);
    }

    [Fact]
    public async Task Old_files_an_update_couldnt_put_back_are_kept_and_block_the_next_update()
    {
        InstallOld();
        _dir.File("Odyssey Launcher/.odyssey-update/old/OdysseyLauncher.pck", "old pck, not put back");
        _dir.File("Odyssey Launcher/.odyssey-update/incomplete.txt", "see old");
        var zip = Package("0.17.0");
        ServeList(List(Release("0.17.0", digest: Sha256(zip))));
        var service = Service();
        var check = await service.CheckAsync(Current, TestContext.Current.CancellationToken);

        service.DeleteStaging();
        var e = await Assert.ThrowsAsync<UpdateException>(() => service.DownloadAsync(check.Available!, null, TestContext.Current.CancellationToken));

        Assert.Contains("couldn't put every file of the old version back", e.Message, StringComparison.Ordinal);
        Assert.True(File.Exists(Path.Combine(service.StagingDir, "old", "OdysseyLauncher.pck")));
    }

    [Fact]
    public void A_folder_that_can_be_written_to_says_so()
    {
        InstallOld();

        Assert.Null(Service().CheckWritable());
        Assert.NotNull(new UpdateService(new GitHubReleaseSource(_client), _dir.Combine("missing", "folder"), "OdysseyLauncher.exe", Platform, NullLog.Instance).CheckWritable());
    }

    /// <summary>Reports on the caller's thread (<see cref="Progress{T}"/> posts, so a test could miss the last report).</summary>
    private sealed class SyncProgress(List<UpdateProgress> reports) : IProgress<UpdateProgress>
    {
        public void Report(UpdateProgress value)
        {
            lock (reports)
            {
                reports.Add(value);
            }
        }
    }
}
