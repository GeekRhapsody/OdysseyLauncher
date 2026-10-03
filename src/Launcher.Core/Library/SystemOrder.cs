using Launcher.Core.Config;
using Launcher.Core.Files;

namespace Launcher.Core.Library;

/// <summary>
/// The systems' order (<c>[display] systems_sort</c> and <c>systems_sort_order</c>). Descending reverses what the sort
/// names (the manufacturer, the year, or the name for alphabetical); ties are always broken by name, A to Z, and a
/// system without the manufacturer or year the sort needs comes last either way. Names compare ignoring case, with
/// numbers in order ("PlayStation 2" before "PlayStation 10"). Favourites and Recently played aren't systems: the
/// grid puts them first.
/// </summary>
public static class SystemOrder
{
    /// <summary>Sorts <paramref name="items"/> in place by each one's system.</summary>
    public static void Sort<T>(List<T> items, Func<T, SystemConfig> systemOf, SystemsOrdering ordering)
    {
        ArgumentNullException.ThrowIfNull(items);
        ArgumentNullException.ThrowIfNull(systemOf);
        items.Sort((a, b) => Compare(systemOf(a), systemOf(b), ordering));
    }

    public static int Compare(SystemConfig a, SystemConfig b, SystemsOrdering ordering)
    {
        ArgumentNullException.ThrowIfNull(a);
        ArgumentNullException.ThrowIfNull(b);
        var descending = ordering.Order == SortOrder.Descending;
        var result = ordering.Sort switch
        {
            SystemSort.Manufacturer => ByManufacturer(a, b, descending),
            SystemSort.ReleaseYear => ByYear(a, b, descending),
            SystemSort.ManufacturerYear => ByManufacturer(a, b, descending) is var maker and not 0 ? maker : ByYear(a, b, descending),
            _ => 0,
        };
        if (result != 0)
        {
            return result;
        }

        var byName = NaturalComparer.Instance.Compare(a.Name, b.Name);
        if (byName != 0)
        {
            return ordering.Sort == SystemSort.Alphabetical && descending ? -byName : byName;
        }

        return string.CompareOrdinal(a.Id, b.Id);
    }

    private static int ByManufacturer(SystemConfig a, SystemConfig b, bool descending)
    {
        var x = string.IsNullOrWhiteSpace(a.Manufacturer) ? null : a.Manufacturer;
        var y = string.IsNullOrWhiteSpace(b.Manufacturer) ? null : b.Manufacturer;
        return (x, y) switch
        {
            (null, null) => 0,
            (null, _) => 1,
            (_, null) => -1,
            _ => Direction(NaturalComparer.Instance.Compare(x, y), descending),
        };
    }

    private static int ByYear(SystemConfig a, SystemConfig b, bool descending) => (a.Year, b.Year) switch
    {
        (null, null) => 0,
        (null, _) => 1,
        (_, null) => -1,
        ({ } x, { } y) => Direction(x.CompareTo(y), descending),
    };

    private static int Direction(int result, bool descending) => descending ? -result : result;
}
