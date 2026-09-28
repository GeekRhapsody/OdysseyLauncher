using Launcher.Core.Scanning;

namespace Launcher.Core.Tests.Scanning;

public class TitleParserTests
{
    [Theory]
    [InlineData("Super Mario World (USA)", "Super Mario World", "USA", null, null, null, null)]
    [InlineData("Sonic the Hedgehog (USA, Europe)", "Sonic the Hedgehog", "USA, Europe", null, null, null, null)]
    [InlineData("Legend of Zelda, The - A Link to the Past (USA)", "The Legend of Zelda - A Link to the Past", "USA", null, null, null, null)]
    [InlineData("Addams Family, The (Europe) (En,Fr,De)", "The Addams Family", "Europe", "En,Fr,De", null, null, null)]
    [InlineData("Street Fighter II' - Special Champion Edition (Europe) (Rev 1)", "Street Fighter II' - Special Champion Edition", "Europe", null, "Rev 1", null, null)]
    [InlineData("Pokemon - Red Version (USA, Europe) (SGB Enhanced)", "Pokemon - Red Version", "USA, Europe", null, null, null, "(SGB Enhanced)")]
    [InlineData("Final Fantasy VII (USA) (Disc 2)", "Final Fantasy VII (Disc 2)", "USA", null, null, 2, null)]
    [InlineData("Metal Gear Solid (Europe) (En,Fr,De,Es,It) (Disc 1) (Rev A)", "Metal Gear Solid (Disc 1)", "Europe", "En,Fr,De,Es,It", "Rev A", 1, null)]
    [InlineData("Castlevania (USA) (Beta) [b1]", "Castlevania", "USA", null, null, null, "(Beta) [b1]")]
    [InlineData("Tetris (World) (v1.1)", "Tetris", "World", null, "v1.1", null, null)]
    [InlineData("Streets of Rage (U) [!]", "Streets of Rage", "U", null, null, null, "[!]")]
    [InlineData("[BIOS] PlayStation (USA) (v3.0)", "PlayStation", "USA", null, "v3.0", null, "[BIOS]")]
    [InlineData("Some Homebrew", "Some Homebrew", null, null, null, null, null)]
    [InlineData("Some_Homebrew_Game", "Some Homebrew Game", null, null, null, null, null)]
    [InlineData("(Demo)", "(Demo)", null, null, null, null, null)]
    [InlineData("Gran Turismo 2 (USA) (Disc 1) (Arcade Mode) (Rev 1)", "Gran Turismo 2 (Disc 1)", "USA", null, "Rev 1", 1, "(Arcade Mode)")]
    [InlineData("Mario Kart, Le (France)", "Le Mario Kart", "France", null, null, null, null)]
    [InlineData("Aventure, L' (France)", "L'Aventure", "France", null, null, null, null)]
    public void Cleans_No_Intro_and_Redump_names(
        string name, string title, string? region, string? languages, string? revision, int? disc, string? tags)
    {
        var info = TitleParser.Parse(name);

        Assert.Equal(title, info.Title);
        Assert.Equal(region, info.Region);
        Assert.Equal(languages, info.Languages);
        Assert.Equal(revision, info.Revision);
        Assert.Equal(disc, info.Disc);
        Assert.Equal(tags, info.Tags);
    }

    [Fact]
    public void Only_the_first_region_group_is_the_region()
    {
        var info = TitleParser.Parse("Game (Japan) (USA)");

        Assert.Equal("Japan", info.Region);
        Assert.Equal("(USA)", info.Tags);
    }

    [Fact]
    public void Parentheses_inside_a_title_are_kept()
    {
        Assert.Equal("Tom (and Jerry) Adventures", TitleParser.Parse("Tom (and Jerry) Adventures (USA)").Title);
    }

    [Fact]
    public void Sort_keys_ignore_a_leading_article_case_and_accents()
    {
        Assert.Equal(TitleParser.SortKey("Legend of Zelda"), TitleParser.SortKey("The Legend of Zelda"));
        Assert.Equal(TitleParser.SortKey("pokemon"), TitleParser.SortKey("Pokémon"));
        Assert.Equal("boy and his blob", TitleParser.SortKey("A Boy and His Blob"));
    }

    [Fact]
    public void Sort_keys_order_numbers_naturally()
    {
        string[] titles = ["Mega Man 10", "Mega Man", "Mega Man 2", "Mega Man X", "Mega Man 9", "Mega Man 007"];

        var sorted = titles.OrderBy(TitleParser.SortKey, StringComparer.Ordinal).ToArray();

        Assert.Equal(["Mega Man", "Mega Man 2", "Mega Man 007", "Mega Man 9", "Mega Man 10", "Mega Man X"], sorted);
    }

    [Fact]
    public void Discs_of_one_game_sort_together_in_order()
    {
        var disc10 = TitleParser.Parse("Game (USA) (Disc 10)").SortTitle;
        var disc2 = TitleParser.Parse("Game (USA) (Disc 2)").SortTitle;
        var sequel = TitleParser.Parse("Game 2 (USA)").SortTitle;

        Assert.True(string.CompareOrdinal(disc2, disc10) < 0);
        Assert.True(string.CompareOrdinal(disc10, sequel) < 0);
    }
}
