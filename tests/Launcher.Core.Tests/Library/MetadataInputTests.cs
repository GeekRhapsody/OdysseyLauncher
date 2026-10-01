using Launcher.Core.Library;

namespace Launcher.Core.Tests.Library;

public sealed class MetadataInputTests
{
    [Theory]
    [InlineData("1994", "1994")]
    [InlineData(" 1994 ", "1994")]
    [InlineData("1994-02", "1994-02")]
    [InlineData("02/1994", "1994-02")]
    [InlineData("2/1994", "1994-02")]
    [InlineData("February 1994", "1994-02")]
    [InlineData("feb 1994", "1994-02")]
    [InlineData("1994-02-24", "1994-02-24")]
    [InlineData("24/02/1994", "1994-02-24")]
    [InlineData("24.2.1994", "1994-02-24")]
    [InlineData("24 February 1994", "1994-02-24")]
    [InlineData("29/02/1996", "1996-02-29")]
    public void Release_dates_are_stored_as_precise_as_they_were_typed(string typed, string stored)
    {
        Assert.Equal(stored, MetadataInput.ParseReleaseDate(typed));
        Assert.Null(MetadataInput.CheckReleaseDate(typed));
    }

    [Theory]
    [InlineData("94")]
    [InlineData("13/1994")]
    [InlineData("31/02/1994")]
    [InlineData("29/02/1995")]
    [InlineData("ma 1994")]
    [InlineData("1994-02-24-01")]
    [InlineData("soon")]
    public void Anything_else_isnt_a_release_date(string typed)
    {
        Assert.Null(MetadataInput.ParseReleaseDate(typed));
        Assert.NotNull(MetadataInput.CheckReleaseDate(typed));
    }

    [Theory]
    [InlineData("5", 1.0)]
    [InlineData("4.5", 0.9)]
    [InlineData("4,5", 0.9)]
    [InlineData("4.5 / 5", 0.9)]
    [InlineData("8/10", 0.8)]
    [InlineData("90%", 0.9)]
    [InlineData("0", 0.0)]
    public void Ratings_are_out_of_five_unless_said_otherwise(string typed, double stored)
    {
        Assert.Equal(stored, MetadataInput.ParseRating(typed)!.Value, 4);
        Assert.Null(MetadataInput.CheckRating(typed));
    }

    [Theory]
    [InlineData("6")]
    [InlineData("-1")]
    [InlineData("101%")]
    [InlineData("4/0")]
    [InlineData("great")]
    public void Ratings_out_of_range_are_refused(string typed)
    {
        Assert.Null(MetadataInput.ParseRating(typed));
        Assert.NotNull(MetadataInput.CheckRating(typed));
    }

    [Fact]
    public void A_rating_is_shown_for_editing_out_of_five()
    {
        Assert.Equal("4.5", MetadataInput.FormatRating(0.9));
        Assert.Equal("4", MetadataInput.FormatRating(0.8));
    }

    [Fact]
    public void Empty_entries_are_accepted_as_use_the_scraped_value()
    {
        Assert.Null(MetadataInput.CheckReleaseDate(" "));
        Assert.Null(MetadataInput.CheckRating(string.Empty));
        Assert.Null(MetadataInput.CheckTitle(string.Empty));
    }

    [Fact]
    public void Lines_must_be_single_and_short_enough()
    {
        Assert.NotNull(MetadataInput.CheckTitle("Two\nlines"));
        Assert.NotNull(MetadataInput.CheckTitle(new string('a', MetadataInput.MaxTitleLength + 1)));
        Assert.Null(MetadataInput.CheckTitle(new string('a', MetadataInput.MaxTitleLength)));
        Assert.NotNull(MetadataInput.CheckPlayers("1 to 4 players, or 8 with a multitap"));
        Assert.Null(MetadataInput.CheckPlayers("1-4"));
        Assert.NotNull(MetadataInput.CheckDescription(new string('a', MetadataInput.MaxDescriptionLength + 1)));
    }
}
