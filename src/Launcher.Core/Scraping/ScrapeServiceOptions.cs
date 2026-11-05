using Launcher.Core.Diagnostics;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Platform;

namespace Launcher.Core.Scraping;

/// <summary>What <see cref="ScrapeService"/> needs. Tests replace the HTTP handler, clock, delay and providers.</summary>
public sealed class ScrapeServiceOptions
{
    public required LibraryService Library { get; init; }

    public required IPlatformPaths Paths { get; init; }

    public required ProviderAccounts Accounts { get; init; }

    /// <summary>Null uses a real <c>SocketsHttpHandler</c>.</summary>
    public HttpMessageHandler? HttpHandler { get; init; }

    public TimeProvider Clock { get; init; } = TimeProvider.System;

    /// <summary>Null waits for real (<see cref="ScraperHttp.RealDelay"/>).</summary>
    public Delay? Delay { get; init; }

    public RetryPolicy Retry { get; init; } = RetryPolicy.Default;

    public ILog Log { get; init; } = NullLog.Instance;

    /// <summary>Null: no derivatives are baked (a platform without a decoder).</summary>
    public IImageDecoder? ImageDecoder { get; init; }

    /// <summary>POC (direct source images): scraped images get no derivative (<see cref="DerivativeService.SkipLibraryBakes"/>).</summary>
    public bool SkipDerivatives { get; init; }

    /// <summary>Null builds the real providers.</summary>
    public IReadOnlyList<IScraper>? Scrapers { get; init; }

    /// <summary>
    /// The local copy of LaunchBox's database the LaunchBox provider reads. Null: the service makes its own, in
    /// <c>CacheDir/launchbox</c>, and disposes it. The app shares one between its services, so one update runs at a
    /// time and its progress is shown once.
    /// </summary>
    public LaunchBoxDatabase? LaunchBox { get; init; }

    /// <summary>Games worked on at once, at most. Each provider still keeps to its own limit.</summary>
    public int MaxWorkers { get; init; } = 8;

    /// <summary>
    /// Saves each provider's response in <c>scraped/responses/</c> (credentials redacted), for debugging a scrape:
    /// off unless the app or <c>odyssey-scrape</c> is started with <c>--save-responses</c> (A4).
    /// </summary>
    public bool SaveResponses { get; init; }
}
