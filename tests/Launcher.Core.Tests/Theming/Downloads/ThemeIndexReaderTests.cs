using Launcher.Core.Config;
using Launcher.Core.Theming.Downloads;

namespace Launcher.Core.Tests.Theming.Downloads;

public sealed class ThemeIndexReaderTests
{
    private static readonly string ListFolder = Path.Combine(Path.GetTempPath(), "list");
    private static readonly string[] Reserved = ["memory-card", "console", "slab"];

    private static ThemeIndex Read(string json) => ThemeIndexReader.Read(json, "themes.json", ListFolder, Reserved);

    private static string Entry(string id, string extra = "", string url = "https://github.com/someone/odyssey-x.git") =>
        $$"""{ "id": "{{id}}", "name": "{{id.ToUpperInvariant()}}", "url": "{{url}}"{{extra}} }""";

    private static string List(params string[] entries) =>
        $$"""{ "format": 1, "latest_app_version": "0.17.0", "themes": [{{string.Join(",", entries)}}] }""";

    [Fact]
    public void Entries_are_read_sorted_by_name_with_their_screenshots_inside_the_list()
    {
        var index = Read("""
            {
              // Comments and trailing commas are allowed: the owner edits it by hand.
              "format": 1,
              "latest_app_version": "0.17.0",
              "themes": [
                {
                  "id": "zebra", "name": "Zebra", "author": "Someone", "description": "Stripes.",
                  "url": "https://github.com/someone/zebra.git",
                  "version": "1.2.0", "min_app_version": "0.16.0", "new": true,
                  "covers": { "system_cards": 42, "templates": 3, "menus": true, "card_videos": false, "game_videos": true },
                  "screenshots": [
                    { "image": "screenshots//zebra//01.webp", "caption": "Systems" },
                    { "image": "../outside.webp", "caption": "Escapes" },
                    { "image": "screenshots/zebra/02.webp", "caption": "" },
                  ],
                },
                // An entry from before 2026-10-16 may still pin a commit: it's ignored, and the theme follows its branch.
                { "id": "aardvark", "name": "Aardvark", "url": "https://gitlab.com/x/aardvark", "commit": "0123456789abcdef0123456789abcdef01234567", "deprecated": true },
              ],
            }
            """);

        Assert.Equal("0.17.0", index.LatestAppVersion);
        Assert.Equal(["aardvark", "zebra"], index.Themes.Select(t => t.Id));
        var zebra = index.Themes[1];
        Assert.Equal(("Zebra", "Someone", "Stripes.", "1.2.0", "0.16.0", true, false),
            (zebra.Name, zebra.Author, zebra.Description, zebra.Version, zebra.MinAppVersion, zebra.New, zebra.Deprecated));
        Assert.Equal(new ThemeCovers(42, 3, true, false, true), zebra.Covers);
        var shot = Assert.Single(zebra.Screenshots);
        Assert.Equal((Path.Combine(ListFolder, "screenshots", "zebra", "01.webp"), "Systems"), (shot.Image, shot.Caption));
        Assert.True(index.Themes[0].Deprecated);

        // covers is optional: a theme that doesn't say what it brings is listed all the same.
        Assert.Null(index.Themes[0].Covers);

        // The two bad screenshots are left out, each with a warning.
        Assert.Equal(2, index.Diagnostics.Count(d => d.Key == "themes[0].screenshots"));
    }

    [Theory]
    [InlineData("Neon", "isn't a valid theme id")]
    [InlineData("console", "is a built-in theme's id")]
    [InlineData("memory-card", "is a built-in theme's id")]
    public void An_entry_with_an_id_it_cant_have_is_left_out(string id, string problem)
    {
        var index = Read(List(Entry(id), Entry("good")));

        Assert.Equal(["good"], index.Themes.Select(t => t.Id));
        var diagnostic = Assert.Single(index.Diagnostics);
        Assert.Equal((Severity.Warning, "themes[0]"), (diagnostic.Severity, diagnostic.Key));
        Assert.Contains(problem, diagnostic.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("http://github.com/someone/x.git", "", "isn't an https URL")]
    [InlineData("C:/themes/x", "", "isn't an https URL")]
    [InlineData("https://github.com/someone/x.git", ", \"min_app_version\": \"soon\"", "isn't a version")]
    public void An_entry_with_a_bad_url_or_version_is_left_out(string url, string extra, string problem)
    {
        var index = Read(List(Entry("x", extra, url)));

        Assert.Empty(index.Themes);
        Assert.Contains(problem, Assert.Single(index.Diagnostics).Message, StringComparison.Ordinal);
    }

    [Fact]
    public void A_local_list_may_name_file_repositories_to_test_a_list_before_publishing_it()
    {
        var json = List(Entry("x", url: "file:///C:/themes/x"));

        Assert.Empty(Read(json).Themes);
        Assert.Single(ThemeIndexReader.Read(json, "themes.json", ListFolder, Reserved, allowFileUrls: true).Themes);
    }

    [Fact]
    public void The_made_up_list_for_captures_reads_cleanly_and_its_screenshots_are_there()
    {
        var folder = Path.Combine(ThemeFixtures.RepoRoot, "tests", "themes-list");
        var index = ThemeIndexReader.Read(File.ReadAllText(Path.Combine(folder, ThemeIndexReader.FileName)), "themes.json", folder, Reserved);

        Assert.Empty(index.Diagnostics);
        Assert.Equal(["carbon", "crystal", "living-room", "tomorrow"], index.Themes.Select(t => t.Id));
        Assert.All(index.Themes.SelectMany(t => t.Screenshots), s => Assert.True(File.Exists(s.Image), s.Image));
    }

    [Fact]
    public void A_theme_listed_twice_keeps_its_first_entry()
    {
        var index = Read(List(Entry("x"), Entry("x")));

        Assert.Single(index.Themes);
        Assert.Contains("listed twice", Assert.Single(index.Diagnostics).Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("{ \"format\": 2, \"themes\": [] }", "format 2 isn't supported")]
    [InlineData("{ \"format\": 1, \"themes\": [", "isn't valid JSON")]
    [InlineData("null", "is empty")]
    public void A_list_it_cant_read_is_empty_with_an_error(string json, string problem)
    {
        var index = Read(json);

        Assert.Empty(index.Themes);
        var diagnostic = Assert.Single(index.Diagnostics);
        Assert.True(diagnostic.IsError);
        Assert.Contains(problem, diagnostic.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Covers_count_a_logo_a_system_names_once()
    {
        // Slab's 171 images: logos/astrocade.webp is Bally Astrocade's ([systems.astrocde] logo), not a system "astrocade".
        var covers = ThemeCovers.Of(ThemeFixtures.Load(ThemeFixtures.SlabFolder));

        Assert.Equal(Directory.GetFiles(Path.Combine(ThemeFixtures.SlabFolder, "logos")).Length, covers.SystemCards);
        Assert.Equal((0, true), (covers.Templates, covers.Menus));
    }

    [Fact]
    public void Covers_are_written_as_the_lists_block()
    {
        var json = ThemeCoversJson.Serialize(new ThemeCovers(42, 3, true, false, true));

        Assert.Equal("""
            {
              "system_cards": 42,
              "templates": 3,
              "menus": true,
              "card_videos": false,
              "game_videos": true
            }
            """.ReplaceLineEndings("\n"), json);
    }
}

public sealed class AppVersionTests
{
    [Theory]
    [InlineData("0.16.0", "0.17.0")]
    [InlineData("0.16.9", "0.16.10")]
    [InlineData("0.17.0-beta.1", "0.17.0")]
    [InlineData("0.17.0-beta.1", "0.17.0-beta.2")]
    [InlineData("0.17.0-beta.2", "0.17.0-beta.10")]
    [InlineData("0.17.0-alpha", "0.17.0-beta")]
    [InlineData("0.17.0-beta", "0.17.0-beta.1")]
    [InlineData("1.2", "1.2.1")]
    public void Versions_are_ordered_as_releases_are(string older, string newer)
    {
        Assert.True(AppVersion.TryParse(older, out var a));
        Assert.True(AppVersion.TryParse(newer, out var b));
        Assert.True(a < b);
        Assert.True(b > a);
    }

    [Fact]
    public void Build_metadata_is_ignored()
    {
        Assert.True(AppVersion.TryParse("0.16.0+8b583d8dae80", out var version));

        Assert.Equal("0.16.0", version.ToString());
        Assert.True(AppVersion.TryParse("0.16.0", out var plain));
        Assert.Equal(0, version.CompareTo(plain));
    }

    [Theory]
    [InlineData("")]
    [InlineData("soon")]
    [InlineData("1")]
    [InlineData("1.2.3.4")]
    [InlineData("1.x.0")]
    [InlineData("1.2.0-")]
    public void Anything_else_isnt_a_version(string text) => Assert.False(AppVersion.TryParse(text, out _));
}
