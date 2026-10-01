using Launcher.Core.Launching;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Launching;

/// <summary>A Steam game's <c>.url</c> shortcut names its app id; anything else isn't a Steam game.</summary>
public sealed class SteamShortcutTests : IDisposable
{
    /// <summary>As Steam writes it (Manage, Add desktop shortcut), with CRLF line endings.</summary>
    private const string SteamMade =
        "[{000214A0-0000-0000-C000-000000000046}]\r\nProp3=19,0\r\n[InternetShortcut]\r\nIDList=\r\nIconIndex=0\r\n" +
        "URL=steam://rungameid/1260320\r\nIconFile=C:\\Program Files (x86)\\Steam\\steam\\games\\b772d8b3.ico\r\n";

    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    [Fact]
    public void The_shortcut_steam_makes_names_its_app_id()
    {
        Assert.Equal(1260320u, SteamShortcut.ParseAppId(SteamMade));
    }

    [Theory]
    [InlineData("steam://rungameid/220", 220u)]
    [InlineData("STEAM://RunGameID/220", 220u)]
    [InlineData("steam://run/220", 220u)]
    [InlineData("steam://run/220//-novid", 220u)]
    [InlineData("steam://launch/220/dialog", 220u)]
    [InlineData("steam://rungameid/220?x=1", 220u)]
    public void Each_url_that_runs_a_game_names_its_app_id(string url, uint appId)
    {
        Assert.Equal(appId, SteamShortcut.AppIdOf(url));
    }

    [Theory]
    [InlineData("steam://rungameid/12000845423472672768")]   // a non-Steam game added to Steam: a 64-bit game id
    [InlineData("steam://rungameid/")]
    [InlineData("steam://rungameid/0")]
    [InlineData("steam://rungameid/-5")]
    [InlineData("steam://store/220")]
    [InlineData("steam://install/220")]
    [InlineData("com.epicgames.launcher://apps/Fortnite?action=launch")]
    [InlineData("https://store.steampowered.com/app/220")]
    public void Other_urls_arent_steam_games(string url)
    {
        Assert.Null(SteamShortcut.AppIdOf(url));
    }

    [Theory]
    [InlineData("[Other]\nURL=steam://rungameid/220\n")]
    [InlineData("URL=steam://rungameid/220\n")]
    [InlineData("[InternetShortcut]\nIconFile=steam://rungameid/220\n")]
    [InlineData("")]
    public void Only_the_internet_shortcut_sections_url_counts(string text)
    {
        Assert.Null(SteamShortcut.ParseAppId(text));
    }

    [Fact]
    public void A_url_key_written_loosely_still_counts()
    {
        Assert.Equal(70u, SteamShortcut.ParseAppId("[internetshortcut]\n  url = steam://rungameid/70  \n"));
    }

    [Fact]
    public void The_file_is_read_only_for_a_url_shortcut()
    {
        var url = _dir.File("steam/Party Animals ü & co.url", SteamMade);
        var lnk = _dir.File("steam/Party Animals.lnk", SteamMade);

        Assert.Equal(1260320u, SteamShortcut.ReadAppId(url));
        Assert.Null(SteamShortcut.ReadAppId(lnk));
        Assert.Null(SteamShortcut.ReadAppId(_dir.Combine("steam", "gone.url")));
    }

    [Fact]
    public void A_file_too_big_to_be_a_shortcut_isnt_read()
    {
        var big = _dir.File("steam/big.url", SteamMade + new string('#', 70_000));

        Assert.Null(SteamShortcut.ReadAppId(big));
    }
}
