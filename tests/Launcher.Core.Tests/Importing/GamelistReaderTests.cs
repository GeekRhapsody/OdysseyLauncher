using System.Text;
using Launcher.Core.Importing;
using Launcher.Core.Media;

namespace Launcher.Core.Tests.Importing;

public sealed class GamelistReaderTests
{
    // The shape of a real ES-DE gamelist (S:\Nintendo Entertainment System\gamelist.xml), trimmed.
    private const string Nes = """
        <?xml version="1.0"?>
        <gameList>
        	<game id="1726">
        		<path>./720 Degrees (USA).zip</path>
        		<name>720 Degrees</name>
        		<desc>You're a skateboarder in Skate City.
        Visit skate shops scattered around the park.
        </desc>
        		<genre>Sports / Skateboard</genre>
        		<image>./images/720 Degrees (USA)-image.png</image>
        		<video>./videos/720 Degrees (USA)-video.mp4</video>
        		<marquee>./images/720 Degrees (USA)-marquee.png</marquee>
        		<thumbnail>./images/720 Degrees (USA)-thumb.png</thumbnail>
        		<manual>./manuals/720 Degrees (USA)-manual.pdf</manual>
        		<rating>0.55</rating>
        		<releasedate>19891101T000000</releasedate>
        		<developer>Atari</developer>
        		<publisher>Mindscape International</publisher>
        		<players>1-4</players>
        		<md5>6026ebe9ec9e971374acab76c161805f</md5>
        		<scrap name="ScreenScraper" date="20260529T090149" />
        	</game>
        	<game>
        		<path>./Malasombra (World) (En,Es) (Digital) (Aftermarket) (Unl).zip</path>
        		<name>Malasombra (World) (En,Es) (Digital) (Aftermarket) (Unl)</name>
        		<md5>fc465bb2d29e1049e0358253bbcba50a</md5>
        		<scrap name="ScreenScraper" date="20260530T142833" />
        	</game>
        	<folder>
        		<path>./Hacks</path>
        		<name>Hacks</name>
        	</folder>
        </gameList>
        """;

    private static GamelistReadResult Read(string xml) =>
        GamelistReader.Read(new MemoryStream(Encoding.UTF8.GetBytes(xml)), "gamelist.xml");

    [Fact]
    public void Reads_each_game_with_its_metadata_and_media_mapped_to_kinds()
    {
        var result = Read(Nes);

        Assert.Null(result.Error);
        Assert.Equal(2, result.Games.Count);
        var game = result.Games[0];
        Assert.Equal("./720 Degrees (USA).zip", game.Path);
        Assert.Equal("720 Degrees", game.Name);
        Assert.Equal("You're a skateboarder in Skate City.\nVisit skate shops scattered around the park.", game.Description);
        Assert.Equal("Sports / Skateboard", game.Genre);
        Assert.Equal("1989-11-01", game.ReleaseDate);
        Assert.Equal("Atari", game.Developer);
        Assert.Equal("Mindscape International", game.Publisher);
        Assert.Equal("1-4", game.Players);
        Assert.Equal(0.55, game.Rating);
        Assert.Equal("1726", game.ScreenScraperId);
        Assert.False(game.Favourite);
        Assert.Equal(
            [
                new GamelistMedia(MediaKinds.Cover, "./images/720 Degrees (USA)-thumb.png"),
                new GamelistMedia(MediaKinds.Screenshot, "./images/720 Degrees (USA)-image.png"),
                new GamelistMedia(MediaKinds.Logo, "./images/720 Degrees (USA)-marquee.png"),
                new GamelistMedia(MediaKinds.Video, "./videos/720 Degrees (USA)-video.mp4"),
            ],
            game.Media);

        // No id attribute: no ScreenScraper match, whatever scraped it.
        Assert.Null(result.Games[1].ScreenScraperId);
        Assert.Empty(result.Games[1].Media);
    }

    [Fact]
    public void Reads_ES_DEs_two_roots_and_its_user_flags()
    {
        var result = Read("""
            <?xml version="1.0"?>
            <alternativeEmulator>
                <label>Mesen</label>
            </alternativeEmulator>
            <gameList>
                <game>
                    <path>./Sub/Zelda.nes</path>
                    <name>The   Legend
                      of Zelda</name>
                    <favorite>true</favorite>
                    <hidden>true</hidden>
                    <rating>0</rating>
                </game>
            </gameList>
            """);

        Assert.Null(result.Error);
        var game = Assert.Single(result.Games);
        Assert.Equal("./Sub/Zelda.nes", game.Path);
        Assert.Equal("The Legend of Zelda", game.Name);
        Assert.True(game.Favourite);
        Assert.True(game.Hidden);
        Assert.Null(game.Rating);
    }

    [Fact]
    public void An_id_counts_as_ScreenScrapers_only_when_ScreenScraper_scraped_the_game()
    {
        var result = Read("""
            <gameList>
                <game id="99"><path>a.nes</path><scrap name="TheGamesDB" date="20260101T000000" /></game>
                <game id="abc"><path>b.nes</path><scrap name="ScreenScraper" /></game>
                <game id="0"><path>c.nes</path><scrap name="ScreenScraper" /></game>
                <game id="42"><path>d.nes</path><scrap name="screenscraper" /></game>
            </gameList>
            """);

        Assert.Equal([null, null, null, "42"], result.Games.Select(g => g.ScreenScraperId));
    }

    [Theory]
    [InlineData("19891101T000000", "1989-11-01")]
    [InlineData("19890000T000000", "1989")]
    [InlineData("19891100T000000", "1989-11")]
    [InlineData("19890231T000000", null)]
    [InlineData("19891301T000000", null)]
    [InlineData("not-a-date-time", null)]
    [InlineData("1994-02-24", "1994-02-24")]
    [InlineData("1994", "1994")]
    public void Release_dates_become_ISO_8601_as_precise_as_known(string text, string? expected)
    {
        Assert.Equal(expected, GamelistReader.ReleaseDate(text));
    }

    [Fact]
    public void Values_the_launcher_couldnt_take_are_left_out()
    {
        var result = Read($"""
            <gameList>
                <game>
                    <path>a.nes</path>
                    <name>{new string('x', 201)}</name>
                    <players>{new string('1', 21)}</players>
                    <rating>1.7</rating>
                    <thumbnail>   </thumbnail>
                </game>
                <game><name>No path</name></game>
            </gameList>
            """);

        var game = Assert.Single(result.Games);
        Assert.Null(game.Name);
        Assert.Null(game.Players);
        Assert.Equal(1, game.Rating);
        Assert.Empty(game.Media);
    }

    [Fact]
    public void A_bad_file_is_an_error_not_an_exception()
    {
        Assert.NotNull(Read("<gameList><game><path>a.nes</path></gameList>").Error);
        Assert.NotNull(Read("""<?xml version="1.0"?><!DOCTYPE gameList [<!ENTITY x "y">]><gameList></gameList>""").Error);
        Assert.Empty(Read("<gameList><game><path>a.nes</path></gameList>").Games);
    }
}
