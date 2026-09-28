namespace Launcher.Core.Scraping;

/// <summary>A game's metadata merged from its providers: each field from the first provider, in config order, that has it.</summary>
/// <param name="Sources">The providers that supplied at least one field, in order.</param>
public sealed record MergedMetadata(
    string? Title,
    string? Description,
    string? ReleaseDate,
    string? Developer,
    string? Publisher,
    string? Genre,
    string? Players,
    double? Rating,
    IReadOnlyList<string> Sources)
{
    public bool IsEmpty => Sources.Count == 0;
}

/// <summary>
/// Provider selection (M4): the configured provider answers first, then each fallback, in order, fills only the
/// fields and media still missing, and only from what its capability map says it has. Pure, so the live scrape and
/// the offline restore after a rebuild agree.
/// </summary>
public sealed class ScrapeMerge
{
    private readonly List<(string Provider, ScrapedGame Game, ScraperCapabilities Capabilities)> _results = [];
    private readonly IReadOnlySet<string> _wantedMedia;

    /// <param name="wantedMedia">The media kinds to fill (config's list, less the kinds the user has their own art for).</param>
    public ScrapeMerge(IReadOnlySet<string> wantedMedia) => _wantedMedia = wantedMedia;

    public void Add(string provider, ScrapedGame game, ScraperCapabilities capabilities) => _results.Add((provider, game, capabilities));

    /// <summary>Whether a provider with these capabilities could still add anything.</summary>
    public bool CouldUse(ScraperCapabilities capabilities)
    {
        foreach (var field in capabilities.Fields)
        {
            if (!_results.Any(r => r.Capabilities.Fields.Contains(field) && r.Game.Has(field)))
            {
                return true;
            }
        }

        return MissingMedia().Any(capabilities.Media.Contains);
    }

    /// <summary>The wanted kinds no result offers yet.</summary>
    public IReadOnlySet<string> MissingMedia()
    {
        var missing = new HashSet<string>(_wantedMedia, StringComparer.Ordinal);
        foreach (var (_, game, capabilities) in _results)
        {
            foreach (var media in game.MediaOrEmpty)
            {
                if (capabilities.Media.Contains(media.Kind))
                {
                    missing.Remove(media.Kind);
                }
            }
        }

        return missing;
    }

    public MergedMetadata Metadata()
    {
        var sources = new List<string>();
        T? Pick<T>(MetadataField field, Func<ScrapedGame, T?> read)
        {
            foreach (var (provider, game, capabilities) in _results)
            {
                if (capabilities.Fields.Contains(field) && read(game) is { } value)
                {
                    if (!sources.Contains(provider))
                    {
                        sources.Add(provider);
                    }

                    return value;
                }
            }

            return default;
        }

        var title = Pick(MetadataField.Title, g => g.Title);
        var description = Pick(MetadataField.Description, g => g.Description);
        var releaseDate = Pick(MetadataField.ReleaseDate, g => g.ReleaseDate);
        var developer = Pick(MetadataField.Developer, g => g.Developer);
        var publisher = Pick(MetadataField.Publisher, g => g.Publisher);
        var genre = Pick(MetadataField.Genre, g => g.Genre);
        var players = Pick(MetadataField.Players, g => g.Players);
        double? rating = null;
        foreach (var (provider, game, capabilities) in _results)
        {
            if (capabilities.Fields.Contains(MetadataField.Rating) && game.Rating is { } value)
            {
                rating = value;
                sources.Add(provider);
                break;
            }
        }

        // Keep the config order in Sources, whatever order the fields were picked in.
        var ordered = _results.Select(r => r.Provider).Where(sources.Contains).Distinct(StringComparer.Ordinal).ToList();
        return new MergedMetadata(title, description, releaseDate, developer, publisher, genre, players, rating, ordered);
    }

    /// <summary>Each wanted kind's candidates, in provider order: if a download fails, the next provider's is tried.</summary>
    public IReadOnlyDictionary<string, IReadOnlyList<(string Provider, ScrapedMedia Media)>> MediaCandidates()
    {
        var candidates = new Dictionary<string, IReadOnlyList<(string, ScrapedMedia)>>(StringComparer.Ordinal);
        foreach (var kind in _wantedMedia)
        {
            var list = new List<(string, ScrapedMedia)>();
            foreach (var (provider, game, capabilities) in _results)
            {
                if (!capabilities.Media.Contains(kind))
                {
                    continue;
                }

                foreach (var media in game.MediaOrEmpty)
                {
                    if (media.Kind == kind)
                    {
                        list.Add((provider, media));
                    }
                }
            }

            if (list.Count > 0)
            {
                candidates[kind] = list;
            }
        }

        return candidates;
    }
}
