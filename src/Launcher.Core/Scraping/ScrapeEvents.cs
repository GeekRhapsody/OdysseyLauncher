using Launcher.Core.Library;

namespace Launcher.Core.Scraping;

public sealed class ScrapeProgressEventArgs(long batchId, string kind, int total, int done, int failed, GameKey? current) : EventArgs
{
    public long BatchId { get; } = batchId;

    public string Kind { get; } = kind;

    public int Total { get; } = total;

    public int Done { get; } = done;

    public int Failed { get; } = failed;

    /// <summary>The game being started; null when the event reports one finishing.</summary>
    public GameKey? Current { get; } = current;
}

public sealed class ScrapeGameEventArgs(long batchId, ScrapeGameResult result) : EventArgs
{
    public long BatchId { get; } = batchId;

    public ScrapeGameResult Result { get; } = result;
}

public sealed class ScrapeBatchEventArgs(ScrapeBatchResult result) : EventArgs
{
    public ScrapeBatchResult Result { get; } = result;
}

public sealed class ProviderNoticeEventArgs(ProviderNotice notice) : EventArgs
{
    public ProviderNotice Notice { get; } = notice;
}
