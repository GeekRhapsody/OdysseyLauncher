using Launcher.Core.Library;

namespace Launcher.Core.Media;

public enum UserArtStatus
{
    /// <summary>The image is the game's now (<see cref="UserArtResult.Path"/>).</summary>
    Set,

    /// <summary>The game's image went (scraped or the user's own); the slot is empty until a scrape fills it.</summary>
    Removed,

    /// <summary>The game had no image of that kind.</summary>
    None,

    /// <summary>The file isn't a PNG, JPEG or WebP image the launcher can read: nothing changed.</summary>
    NotAnImage,

    /// <summary>The game isn't in the library.</summary>
    NotInLibrary,
}

/// <summary>What setting or removing one of a game's images did.</summary>
/// <param name="Path">The image's file as stored, '/'-separated (<c>media/ps2/covers/Game.png</c>).</param>
/// <param name="Message">Why it was refused, for the user.</param>
public sealed record UserArtResult(UserArtStatus Status, string? Path, string? Message = null);

/// <summary>
/// The user's own images for a game (M7's game options panel): one per media kind, chosen with the image picker.
/// <para>
/// Setting one copies the file to the game's name in the media folder,
/// <c>&lt;media folder&gt;/&lt;system&gt;/&lt;folder&gt;/&lt;name&gt;.&lt;ext&gt;</c> (the ROM's name without its extension, as
/// ES-DE names media, so every ROM of that name shares it; A4), replacing the game's files of that kind (a scraped
/// one too: there's one file per kind), bakes its derivative, and indexes it without a ROM scan
/// (<see cref="LibraryService.RefreshMediaAsync"/>, which raises <c>MediaChanged</c>, so the grid shows it at once).
/// Scraping never replaces it.
/// </para>
/// <para>
/// Removing deletes the game's files of that kind (<see cref="MediaStore.FilesOf(string, string, string)"/>), whoever
/// put them there, so every ROM of that name loses it; the slot stays empty until a scrape fills it.
/// </para>
/// It's just files in the folder the scanner indexes, so a rebuild keeps them. Clearing a game's metadata removes them.
/// </summary>
public sealed class UserArtService(LibraryService library, DerivativeService? derivatives)
{
    private readonly LibraryService _library = library ?? throw new ArgumentNullException(nameof(library));

    /// <summary>The game's file for a kind, as stored: <c>media/&lt;system&gt;/&lt;folder&gt;/&lt;name&gt;&lt;ext&gt;</c> (<see cref="MediaStore.PathFor"/>).</summary>
    public static string PathFor(GameKey game, string relPath, string kind, string extension)
    {
        ArgumentNullException.ThrowIfNull(extension);
        return MediaStore.PathFor(game.SystemId, relPath, kind, extension.ToLowerInvariant());
    }

    public async Task<UserArtResult> SetAsync(GameKey game, string kind, string sourceFile, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(sourceFile);
        CheckKind(kind);
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new UserArtResult(UserArtStatus.NotInLibrary, null, Message: $"{game.SystemId}/{game.PathKey} isn't in the library: rescan its system first.");
        }

        var written = await Task.Run(() =>
        {
            var extension = Path.GetExtension(sourceFile).ToLowerInvariant();
            if (!MediaKinds.ImageExtensions.Contains(extension))
            {
                return new UserArtResult(UserArtStatus.NotAnImage, null, Message: $"'{Path.GetFileName(sourceFile)}' isn't a PNG, JPEG or WebP image.");
            }

            try
            {
                if (!ImageHeaders.TryReadSize(sourceFile, out var width, out var height) || width <= 0 || height <= 0)
                {
                    return new UserArtResult(UserArtStatus.NotAnImage, null, Message: $"'{Path.GetFileName(sourceFile)}' isn't an image the launcher can read.");
                }

                return Replace(game, details.RelPath, kind, extension, target =>
                {
                    // Choosing the file that's already there (from the art folder itself) changes nothing.
                    if (!string.Equals(Path.GetFullPath(sourceFile), Path.GetFullPath(target), StringComparison.OrdinalIgnoreCase))
                    {
                        File.Copy(sourceFile, target + ".import.tmp", overwrite: true);
                        return true;
                    }

                    return false;
                });
            }
            catch (Exception e) when (e is IOException or UnauthorizedAccessException)
            {
                return new UserArtResult(UserArtStatus.NotAnImage, null, Message: $"'{Path.GetFileName(sourceFile)}' couldn't be copied: {e.Message}");
            }
        }, cancellationToken).ConfigureAwait(false);

        return await IndexAsync(game, written, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Makes <paramref name="image"/> (PNG, JPEG or WebP bytes: an image the user chose from a provider's, 2026-10-15)
    /// the game's file of <paramref name="kind"/>, as <see cref="SetAsync(GameKey, string, string, CancellationToken)"/> does
    /// with a file.
    /// </summary>
    public async Task<UserArtResult> SetAsync(GameKey game, string kind, ReadOnlyMemory<byte> image, CancellationToken cancellationToken)
    {
        CheckKind(kind);
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new UserArtResult(UserArtStatus.NotInLibrary, null, Message: $"{game.SystemId}/{game.PathKey} isn't in the library: rescan its system first.");
        }

        var written = await Task.Run(() =>
        {
            int width, height;
            using (var stream = new MemoryStream(image.ToArray(), writable: false))
            {
                if (ImageFormats.Sniff(image.Span) is not { } extension || !ImageHeaders.TryReadSize(stream, out width, out height) || width <= 0 || height <= 0)
                {
                    return new UserArtResult(UserArtStatus.NotAnImage, null, Message: "It isn't a PNG, JPEG or WebP image the launcher can read.");
                }

                try
                {
                    return Replace(game, details.RelPath, kind, extension, target =>
                    {
                        File.WriteAllBytes(target + ".import.tmp", image.ToArray());
                        return true;
                    });
                }
                catch (Exception e) when (e is IOException or UnauthorizedAccessException)
                {
                    return new UserArtResult(UserArtStatus.NotAnImage, null, Message: $"It couldn't be saved: {e.Message}");
                }
            }
        }, cancellationToken).ConfigureAwait(false);

        return await IndexAsync(game, written, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>
    /// Worker thread: <paramref name="write"/> writes the image to the path it's given plus <c>.import.tmp</c> (false: it's
    /// the file already), which is moved over the game's file of <paramref name="kind"/>; the game's other files of that
    /// kind go.
    /// </summary>
    private UserArtResult Replace(GameKey game, string relPath, string kind, string extension, Func<string, bool> write)
    {
        var relative = PathFor(game, relPath, kind, extension);
        var target = Full(relative);
        Directory.CreateDirectory(Path.GetDirectoryName(target)!);
        if (write(target))
        {
            File.Move(target + ".import.tmp", target, overwrite: true);
        }

        // One image per kind: the game's file in another format, or named after its whole ROM name, would be a second one.
        foreach (var other in OwnFiles(relPath, game.SystemId, kind))
        {
            if (!string.Equals(other, relative, StringComparison.Ordinal))
            {
                File.Delete(Full(other));
            }
        }

        return new UserArtResult(UserArtStatus.Set, relative);
    }

    /// <summary>A set image's derivative is baked and it's indexed (raising <c>MediaChanged</c>); a refusal is returned as it is.</summary>
    private async Task<UserArtResult> IndexAsync(GameKey game, UserArtResult written, CancellationToken cancellationToken)
    {
        if (written.Status != UserArtStatus.Set)
        {
            return written;
        }

        // The derivative first, so the grid can show the image as soon as the index says it's there.
        var info = new FileInfo(Full(written.Path!));
        if (derivatives is not null)
        {
            await derivatives.BakeAsync(written.Path!, info.Length, new DateTimeOffset(info.LastWriteTimeUtc).ToUnixTimeMilliseconds(), cancellationToken).ConfigureAwait(false);
        }

        await _library.RefreshMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
        return written;
    }

    /// <summary>Removes the game's own image of <paramref name="kind"/>, scraped or the user's.</summary>
    public async Task<UserArtResult> RemoveAsync(GameKey game, string kind, CancellationToken cancellationToken)
    {
        CheckKind(kind);
        var details = await _library.GetGameAsync(game, cancellationToken).ConfigureAwait(false);
        if (details is null)
        {
            return new UserArtResult(UserArtStatus.NotInLibrary, null);
        }

        var removed = await Task.Run(() =>
        {
            var files = OwnFiles(details.RelPath, game.SystemId, kind);
            foreach (var file in files)
            {
                File.Delete(Full(file));
            }

            return files.Count > 0 ? files[0] : null;
        }, cancellationToken).ConfigureAwait(false);

        if (removed is null)
        {
            return new UserArtResult(UserArtStatus.None, null);
        }

        await _library.RefreshMediaAsync(game.SystemId, cancellationToken).ConfigureAwait(false);
        return new UserArtResult(UserArtStatus.Removed, removed);
    }

    /// <summary>The game's files of a kind (its name with or without the ROM's extension, any image extension), as stored.</summary>
    private IReadOnlyList<string> OwnFiles(string relPath, string systemId, string kind) =>
        new MediaStore(_library.MediaDir).FilesOf(systemId, relPath, kind);

    private string Full(string relative) => _library.MediaPath(relative);

    private static void CheckKind(string kind)
    {
        if (!MediaKinds.Images.Contains(kind))
        {
            throw new ArgumentException($"'{kind}' isn't an image kind.", nameof(kind));
        }
    }
}
