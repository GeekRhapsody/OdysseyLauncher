namespace Launcher.Core.Media;

/// <summary>
/// Renders a game's manual (the <c>manual</c> kind: a PDF) page by page for its manual viewer and thumbnails, through
/// the OS (Windows: Windows.Data.Pdf). A reader is used on one thread, the one that opened it, and never on Godot's
/// main thread: opening and rendering block.
/// </summary>
public interface IPdfRenderer
{
    /// <summary>The document; null, with the reason in <paramref name="error"/>, when it can't be read.</summary>
    IPdfReader? Open(string path, out string? error);
}

/// <summary>A PDF document, rendered a page at a time.</summary>
public interface IPdfReader : IDisposable
{
    int PageCount { get; }

    /// <summary>
    /// The page's size as the document lays it out (device-independent pixels, 96 to the inch), turned as it's shown;
    /// false if the page can't be read.
    /// </summary>
    bool TryGetPageSize(int page, out float width, out float height);

    /// <summary>
    /// Renders the whole page scaled to <paramref name="width"/> × <paramref name="height"/>, as RGBA8 (top row first,
    /// opaque, on white paper). False, with the reason in <paramref name="error"/>, if it can't be.
    /// </summary>
    bool TryRender(int page, int width, int height, Span<byte> rgba, out string? error);
}
