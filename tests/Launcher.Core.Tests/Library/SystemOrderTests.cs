using Launcher.Core.Config;
using Launcher.Core.Library;

namespace Launcher.Core.Tests.Library;

public sealed class SystemOrderTests
{
    private static readonly SystemConfig[] Systems =
    [
        System("ps2", "PlayStation 2", "Sony", 2000),
        System("megadrive", "Mega Drive", "Sega", 1988),
        System("psx", "PlayStation", "Sony", 1994),
        System("homebrew", "Homebrew", null, null),
        System("snes", "Super Nintendo Entertainment System", "Nintendo", 1990),
        System("nes", "Nintendo Entertainment System", "Nintendo", 1983),
        System("ports", "Ports", null, 2001),
        System("ps10", "PlayStation 10", "Sony", null),
    ];

    private static SystemConfig System(string id, string name, string? manufacturer, int? year) =>
        new(id, name, manufacturer, year, [], [".bin"], "emu", [], null, null, [], RomDirSource.Default, true, []);

    private static string[] Sorted(SystemSort sort, SortOrder order = SortOrder.Ascending)
    {
        var list = Systems.ToList();
        SystemOrder.Sort(list, s => s, new SystemsOrdering(sort, order));
        return [.. list.Select(s => s.Id)];
    }

    [Fact]
    public void Alphabetical_sorts_by_name_with_numbers_in_order_and_descending_reverses_it()
    {
        Assert.Equal(["homebrew", "megadrive", "nes", "psx", "ps2", "ps10", "ports", "snes"], Sorted(SystemSort.Alphabetical));
        Assert.Equal(["snes", "ports", "ps10", "ps2", "psx", "nes", "megadrive", "homebrew"], Sorted(SystemSort.Alphabetical, SortOrder.Descending));
    }

    [Fact]
    public void By_manufacturer_groups_them_by_name_and_those_without_one_come_last()
    {
        Assert.Equal(["nes", "snes", "megadrive", "psx", "ps2", "ps10", "homebrew", "ports"], Sorted(SystemSort.Manufacturer));

        // Descending reverses the manufacturers; within one, and among those without one, it's still by name.
        Assert.Equal(["psx", "ps2", "ps10", "megadrive", "nes", "snes", "homebrew", "ports"], Sorted(SystemSort.Manufacturer, SortOrder.Descending));
    }

    [Fact]
    public void By_release_year_puts_those_without_one_last_either_way()
    {
        Assert.Equal(["nes", "megadrive", "snes", "psx", "ps2", "ports", "homebrew", "ps10"], Sorted(SystemSort.ReleaseYear));
        Assert.Equal(["ports", "ps2", "psx", "snes", "megadrive", "nes", "homebrew", "ps10"], Sorted(SystemSort.ReleaseYear, SortOrder.Descending));
    }

    [Fact]
    public void By_manufacturer_then_year_orders_each_manufacturers_systems_by_year()
    {
        Assert.Equal(["nes", "snes", "megadrive", "psx", "ps2", "ps10", "ports", "homebrew"], Sorted(SystemSort.ManufacturerYear));
        Assert.Equal(["ps2", "psx", "ps10", "megadrive", "snes", "nes", "ports", "homebrew"], Sorted(SystemSort.ManufacturerYear, SortOrder.Descending));
    }

    [Fact]
    public void A_tie_on_everything_but_the_id_is_still_a_stable_order()
    {
        var a = System("a", "Same", "Maker", 1990);
        var b = System("b", "Same", "Maker", 1990);
        foreach (var sort in Enum.GetValues<SystemSort>())
        {
            Assert.True(SystemOrder.Compare(a, b, new SystemsOrdering(sort, SortOrder.Descending)) < 0);
            Assert.Equal(0, SystemOrder.Compare(a, a, new SystemsOrdering(sort, SortOrder.Ascending)));
        }
    }
}
