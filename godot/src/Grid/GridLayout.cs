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
/// the view's height (0 for either is automatic).
/// </summary>
public readonly record struct GridLayout(GridShape Shape, int Columns = 0, int Rows = 0)
{
    public static GridLayout Systems(DisplaySettings display) => display.SystemsLayout switch
    {
        SystemsLayout.Carousel => new GridLayout(GridShape.Carousel),
        SystemsLayout.Single => new GridLayout(GridShape.Single),
        _ => new GridLayout(GridShape.Grid, display.SystemsGrid.Columns, display.SystemsGrid.Rows),
    };

    /// <param name="system">The system shown, for its own layout and grid size; null for Favourites and Recently played.</param>
    public static GridLayout Games(DisplaySettings display, SystemConfig? system)
    {
        var size = display.GamesGridFor(system);
        return display.GamesLayoutFor(system) switch
        {
            GamesLayout.Carousel => new GridLayout(GridShape.Carousel),
            GamesLayout.List => new GridLayout(GridShape.List),
            _ => new GridLayout(GridShape.Grid, size.Columns, size.Rows),
        };
    }

    public override string ToString() => Shape == GridShape.Grid && (Columns > 0 || Rows > 0)
        ? $"grid {(Columns > 0 ? Columns.ToString(System.Globalization.CultureInfo.InvariantCulture) : "auto")}x{(Rows > 0 ? Rows.ToString(System.Globalization.CultureInfo.InvariantCulture) : "auto")}"
        : Shape.ToString().ToLowerInvariant();
}
