using System;
using System.Globalization;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using Launcher.App.Navigation;
using Launcher.App.Screens;
using Launcher.App.Ui;
using Launcher.Core.Library;

namespace Launcher.App.Options;

/// <summary>
/// Editing a game's title and metadata (M7 part 2). Each field shows what the grid and details show (the user's value,
/// else the scraped one) and where it came from; A types a new value on the on-screen keyboard, checked before it's
/// saved (<see cref="MetadataInput"/>); Y goes back to the scraped value. The user's values are overrides in
/// userdata.db, which scraping never writes, so a re-scrape keeps them; "Clear metadata" removes them.
/// </summary>
public sealed partial class GameMetadataPanel : ListPanel
{
    private static readonly Field[] Fields =
        [Field.Title, Field.Released, Field.Genre, Field.Developer, Field.Publisher, Field.Players, Field.Rating, Field.Description];

    private readonly ItemOptions _options;
    private readonly GameKey _key;
    private readonly SettingRow[] _rows = new SettingRow[Fields.Length];
    private GameMetadataEdit? _edit;
    private int _generation;

    public GameMetadataPanel(ItemOptions options, GameKey key, string title)
        : base(title)
    {
        _options = options;
        _key = key;
        Subtitle = "Title and metadata: yours where you've typed one, else what was scraped";
        for (var i = 0; i < Fields.Length; i++)
        {
            var field = Fields[i];
            _rows[i] = AddRow(Label(field), "Reading…", activated: () => Edit(field));
        }

        AddNote("Your values are kept when the game is scraped again. Clear metadata (in its options) removes them.");
        SetHints("A  Edit     Y  Use the scraped value     B  Back");
        Reload();
    }

    private enum Field
    {
        Title,
        Released,
        Genre,
        Developer,
        Publisher,
        Players,
        Rating,
        Description,
    }

    public override bool Handle(NavCommand command)
    {
        if (command != NavCommand.Favourite)
        {
            return false;
        }

        var focused = GetViewport().GuiGetFocusOwner();
        for (var i = 0; i < _rows.Length; i++)
        {
            if (_rows[i] == focused)
            {
                if (Own(Fields[i]) is null)
                {
                    ShowStatus("That's already the scraped value.", UiStyle.Dim, 3);
                }
                else
                {
                    Save(Fields[i], null);
                }

                return true;
            }
        }

        return false;
    }

    private void Reload()
    {
        var generation = ++_generation;
        var library = _options.Library;
        var key = _key;
        _ = Task.Run(async () =>
        {
            var edit = await library.GetMetadataEditAsync(key, CancellationToken.None).ConfigureAwait(false);
            _options.Ui.Queue.Post(() =>
            {
                if (generation == _generation && IsInstanceValid(this) && edit is not null)
                {
                    _edit = edit;
                    ShowFields();
                }
            });
        });
    }

    private void ShowFields()
    {
        Heading = _edit!.TitleOverride ?? _edit.Title;
        for (var i = 0; i < Fields.Length; i++)
        {
            var field = Fields[i];
            var own = Own(field);
            var scraped = Scraped(field);
            var shown = own ?? scraped;
            var row = _rows[i];
            row.Detail = shown is null ? "None" : Display(field, shown);
            row.DetailColour = shown is null ? UiStyle.Faint : UiStyle.Dim;
            row.Value = own is not null ? "Yours" : scraped is not null ? (field == Field.Title && _edit.Scraped is null ? "File name" : "Scraped") : null;
            row.ValueColour = own is not null ? UiStyle.Good : UiStyle.Accent;
        }
    }

    // ---- Values ----------------------------------------------------------------------------------------

    /// <summary>The user's value as stored (an ISO date, a 0–1 rating as text), or null.</summary>
    private string? Own(Field field)
    {
        var o = _edit?.Overrides;
        return field switch
        {
            Field.Title => _edit?.TitleOverride,
            Field.Description => o?.Description,
            Field.Released => o?.ReleaseDate,
            Field.Developer => o?.Developer,
            Field.Publisher => o?.Publisher,
            Field.Genre => o?.Genre,
            Field.Players => o?.Players,
            Field.Rating => o?.Rating?.ToString(CultureInfo.InvariantCulture),
            _ => null,
        };
    }

    private string? Scraped(Field field)
    {
        var s = _edit?.Scraped;
        return field switch
        {
            Field.Title => _edit?.Title,
            Field.Description => s?.Description,
            Field.Released => s?.ReleaseDate,
            Field.Developer => s?.Developer,
            Field.Publisher => s?.Publisher,
            Field.Genre => s?.Genre,
            Field.Players => s?.Players,
            Field.Rating => s?.Rating?.ToString(CultureInfo.InvariantCulture),
            _ => null,
        };
    }

    /// <summary>A stored value as the details show it.</summary>
    private static string Display(Field field, string value) => field switch
    {
        Field.Released => DetailsFormatter.ReleaseDate(value) ?? value,
        Field.Rating => MetadataInput.FormatRating(double.Parse(value, CultureInfo.InvariantCulture)) + " / 5",
        _ => value,
    };

    /// <summary>A stored value as the keyboard starts with it, in the form the user types.</summary>
    private static string Editable(Field field, string value)
    {
        switch (field)
        {
            case Field.Released:
                var parts = value.Split('-');
                return parts.Length switch
                {
                    3 => $"{parts[2]}/{parts[1]}/{parts[0]}",
                    2 => $"{parts[1]}/{parts[0]}",
                    _ => value,
                };
            case Field.Rating:
                return MetadataInput.FormatRating(double.Parse(value, CultureInfo.InvariantCulture));
            default:
                return value;
        }
    }

    private static string Label(Field field) => field switch
    {
        Field.Title => "Title",
        Field.Released => "Released",
        Field.Genre => "Genre",
        Field.Developer => "Developer",
        Field.Publisher => "Publisher",
        Field.Players => "Players",
        Field.Rating => "Rating",
        _ => "Description",
    };

    private static (string? Placeholder, string Subtitle, Func<string, string?> Check) Input(Field field) => field switch
    {
        Field.Title => ("The game's name", "Shown in the grid, and used to search for it when scraping", MetadataInput.CheckTitle),
        Field.Released => ("24/02/1994", "A year, a month and year, or a day: 1994, 02/1994, 24/02/1994", MetadataInput.CheckReleaseDate),
        Field.Players => ("1-2", "How many can play: 1, 1-2, 1-4", MetadataInput.CheckPlayers),
        Field.Rating => ("4.5", "Out of 5 (4.5), or a percentage (90%)", MetadataInput.CheckRating),
        Field.Description => (null, "One paragraph", MetadataInput.CheckDescription),
        _ => (null, "Leave it empty to use the scraped value", MetadataInput.CheckField),
    };

    // ---- Editing ---------------------------------------------------------------------------------------

    private void Edit(Field field)
    {
        if (_edit is null)
        {
            return;
        }

        var current = Own(field) ?? Scraped(field);
        var (placeholder, subtitle, check) = Input(field);
        OnScreenKeyboard.Open(Layer, new KeyboardRequest(
            $"{Label(field)} for {_edit.TitleOverride ?? _edit.Title}",
            current is null ? string.Empty : Editable(field, current),
            text => Save(field, text),
            Placeholder: placeholder,
            Subtitle: subtitle + ". Empty: the scraped value",
            Validate: check));
    }

    /// <summary>
    /// Saves the user's value for <paramref name="field"/> (null or empty: none, so the scraped value shows). A value
    /// the same as the scraped one isn't kept as the user's, so a later scrape can still update it.
    /// </summary>
    private void Save(Field field, string? text)
    {
        var edit = _edit!;
        var trimmed = string.IsNullOrWhiteSpace(text) ? null : text.Trim();
        string? stored = field switch
        {
            Field.Released => trimmed is null ? null : MetadataInput.ParseReleaseDate(trimmed),
            Field.Rating => trimmed is null ? null : MetadataInput.ParseRating(trimmed)?.ToString(CultureInfo.InvariantCulture),
            _ => trimmed,
        };
        if (stored is not null && (field == Field.Rating
                ? Scraped(field) is { } s && Math.Abs(double.Parse(s, CultureInfo.InvariantCulture) - double.Parse(stored, CultureInfo.InvariantCulture)) < 0.0005
                : string.Equals(stored, Scraped(field), StringComparison.Ordinal)))
        {
            stored = null;
        }

        if (string.Equals(stored, Own(field), StringComparison.Ordinal))
        {
            ShowStatus("No change.", UiStyle.Dim, 3);
            return;
        }

        var o = edit.Overrides;
        var key = _key;
        var library = _options.Library;
        Func<Task> write = field switch
        {
            Field.Title => () => library.SetTitleOverrideAsync(key, stored, CancellationToken.None),
            Field.Description => () => library.SetMetadataOverrideAsync(key, o with { Description = stored }, CancellationToken.None),
            Field.Released => () => library.SetMetadataOverrideAsync(key, o with { ReleaseDate = stored }, CancellationToken.None),
            Field.Developer => () => library.SetMetadataOverrideAsync(key, o with { Developer = stored }, CancellationToken.None),
            Field.Publisher => () => library.SetMetadataOverrideAsync(key, o with { Publisher = stored }, CancellationToken.None),
            Field.Genre => () => library.SetMetadataOverrideAsync(key, o with { Genre = stored }, CancellationToken.None),
            Field.Players => () => library.SetMetadataOverrideAsync(key, o with { Players = stored }, CancellationToken.None),
            _ => () => library.SetMetadataOverrideAsync(key, o with { Rating = stored is null ? null : double.Parse(stored, CultureInfo.InvariantCulture) }, CancellationToken.None),
        };

        ShowStatus("Saving…", UiStyle.Dim);
        _ = Task.Run(async () =>
        {
            string? failure = null;
            try
            {
                await write().ConfigureAwait(false);
            }
            catch (Exception e)
            {
                failure = e.Message;
            }

            _options.Ui.Queue.Post(() =>
            {
                _options.GameEdited(key);
                if (!IsInstanceValid(this))
                {
                    return;
                }

                GD.Print($"Options: {key.SystemId}/{key.PathKey}: {Label(field).ToLowerInvariant()} {(stored is null ? "back to the scraped value" : "saved")}.");
                ShowStatus(failure is not null ? $"Not saved: {failure}" : stored is null ? $"{Label(field)}: the scraped value again." : $"{Label(field)} saved.",
                    failure is null ? UiStyle.Good : UiStyle.Bad, 4);
                Reload();
            });
        });
    }
}
