using Launcher.Core.Config;

namespace Launcher.App.Grid;

/// <summary>How an <see cref="ItemGrid"/> lays its items out.</summary>
public enum GridShape
{
    /// <summary>Rows and columns, scrolling down (the default).</summary>
    Grid,

    /// <summary>One row, scrolling sideways, the focused item in the middle and its neighbours turned and smaller.</summary>
    Carousel,

    /// <summary>One item at a time in the middle, filling the screen; the next is a screen to the right.</summary>
    Single,

    /// <summary>One column on the right of the screen, an item at a time, scrolling down beside a list of titles.</summary>
    List,
}

/// <summary>
/// An <see cref="ItemGrid"/>'s layout: its shape, and for <see cref="GridShape.Grid"/> its columns and the rows that fit
/// the view's height (0 for either is automatic), and whether each item's title is shown under it (<see cref="Labels"/>).
/// </summary>
public readonly record struct GridLayout(GridShape Shape, int Columns = 0, int Rows = 0, bool Labels = false)
{
    public static GridLayout Systems(DisplaySettings display) => display.SystemsLayout switch
    {
        SystemsLayout.Carousel => new GridLayout(GridShape.Carousel),
        SystemsLayout.Single => new GridLayout(GridShape.Single),
        _ => new GridLayout(GridShape.Grid, display.SystemsGrid.Columns, display.SystemsGrid.Rows, display.SystemsLayout == SystemsLayout.GridWithLabels),
    };

    /// <param name="system">The system shown, for its own layout and grid size; null for Favourites, Recently played and All games.</param>
    public static GridLayout Games(DisplaySettings display, SystemConfig? system)
    {
        var size = display.GamesGridFor(system);
        return display.GamesLayoutFor(system) switch
        {
            GamesLayout.Carousel => new GridLayout(GridShape.Carousel),
            GamesLayout.List => new GridLayout(GridShape.List),
            var layout => new GridLayout(GridShape.Grid, size.Columns, size.Rows, layout == GamesLayout.GridWithLabels),
        };
    }

    public override string ToString()
    {
        var name = Labels ? "grid_with_labels" : Shape.ToString().ToLowerInvariant();
        return Shape == GridShape.Grid && (Columns > 0 || Rows > 0)
            ? $"{name} {(Columns > 0 ? Columns.ToString(System.Globalization.CultureInfo.InvariantCulture) : "auto")}x{(Rows > 0 ? Rows.ToString(System.Globalization.CultureInfo.InvariantCulture) : "auto")}"
            : name;
    }
}
