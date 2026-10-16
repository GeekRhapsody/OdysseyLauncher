using LibGit2Sharp;

namespace Launcher.Core.Theming.Downloads;

/// <summary>
/// <see cref="IGitClient"/> over LibGit2Sharp (libgit2, native, shipped with the package). The only class that touches
/// LibGit2Sharp's types, so its assembly and libgit2 load only when the theme downloader is first used, never at boot.
/// </summary>
public sealed class LibGit2Client : IGitClient
{
    // IsValid doesn't search the folders above, so a theme kept inside another repository's tree isn't one.
    public bool IsRepository(string folder) => Directory.Exists(folder) && Repository.IsValid(folder);

    public void Clone(string url, string folder, IProgress<GitProgress>? progress, CancellationToken cancellation)
    {
        cancellation.ThrowIfCancellationRequested();
        // No checkout yet: the clone's own config comes first, so the user's git settings (core.autocrlf) can't change
        // the files from what the list's owner tested. The caller checks out the commit it wants.
        var options = new CloneOptions(FetchOptionsFor(progress, cancellation)) { RecurseSubmodules = false, Checkout = false };
        Run(() =>
        {
            Repository.Clone(url, folder, options);
            using var repo = new Repository(folder);
            repo.Config.Set("core.autocrlf", false);
            repo.Config.Set("core.eol", "lf");
            repo.Config.Set("core.safecrlf", false);
        }, cancellation);
    }

    public void Fetch(string folder, IProgress<GitProgress>? progress, CancellationToken cancellation)
    {
        cancellation.ThrowIfCancellationRequested();
        Run(() =>
        {
            using var repo = new Repository(folder);
            var origin = repo.Network.Remotes["origin"] ?? throw new GitException("The theme's folder has no 'origin' to update from");
            var refSpecs = origin.FetchRefSpecs.Select(r => r.Specification).ToList();
            var options = FetchOptionsFor(progress, cancellation);
            options.Prune = true;
            Commands.Fetch(repo, origin.Name, refSpecs, options, "odyssey: fetch");
        }, cancellation);
    }

    public string? HeadCommit(string folder) => Run(() =>
    {
        using var repo = new Repository(folder);
        return repo.Head.Tip?.Sha;
    }, CancellationToken.None);

    public string? OriginUrl(string folder) => Run(() =>
    {
        using var repo = new Repository(folder);
        return repo.Network.Remotes["origin"]?.Url;
    }, CancellationToken.None);

    public bool HasCommit(string folder, string commit) => Run(() =>
    {
        using var repo = new Repository(folder);
        return repo.Lookup<Commit>(commit) is not null;
    }, CancellationToken.None);

    public bool HasLocalChanges(string folder) => Run(() =>
    {
        using var repo = new Repository(folder);
        var status = repo.RetrieveStatus(new StatusOptions { IncludeUntracked = false, IncludeIgnored = false, RecurseUntrackedDirs = false });
        return status.IsDirty;
    }, CancellationToken.None);

    public bool HasTrackedFiles(string folder) => Run(() =>
    {
        using var repo = new Repository(folder);
        return repo.Index.Count > 0;
    }, CancellationToken.None);

    public void CheckOut(string folder, string commit) => Run(() =>
    {
        using var repo = new Repository(folder);
        var target = repo.Lookup<Commit>(commit)
            ?? throw new GitException($"The theme's repository doesn't have the listed version (commit {commit[..Math.Min(7, commit.Length)]})");
        Commands.Checkout(repo, target, new CheckoutOptions { CheckoutModifiers = CheckoutModifiers.Force });
    }, CancellationToken.None);

    public void ResetToRemote(string folder) => Run(() =>
    {
        using var repo = new Repository(folder);
        var tip = repo.Head.TrackedBranch?.Tip
            ?? (repo.Refs["refs/remotes/origin/HEAD"]?.ResolveToDirectReference()?.Target as Commit)
            ?? throw new GitException("The list's folder has no branch to update");
        repo.Reset(ResetMode.Hard, tip);
    }, CancellationToken.None);

    private static FetchOptions FetchOptionsFor(IProgress<GitProgress>? progress, CancellationToken cancellation)
    {
        var options = new FetchOptions
        {
            OnTransferProgress = p =>
            {
                progress?.Report(new GitProgress(p.ReceivedObjects, p.TotalObjects, p.ReceivedBytes));
                return !cancellation.IsCancellationRequested;
            },
            TagFetchMode = TagFetchMode.All,
        };
        options.ProxyOptions.ProxyType = ProxyType.Auto;
        return options;
    }

    private static void Run(Action action, CancellationToken cancellation) => Run<object?>(() =>
    {
        action();
        return null;
    }, cancellation);

    private static T Run<T>(Func<T> action, CancellationToken cancellation)
    {
        try
        {
            return action();
        }
        catch (UserCancelledException e)
        {
            throw new OperationCanceledException("Cancelled", e, cancellation);
        }
        catch (RepositoryNotFoundException e)
        {
            throw new GitException("It isn't a git repository", e);
        }
        catch (LibGit2SharpException e) when (cancellation.IsCancellationRequested)
        {
            throw new OperationCanceledException("Cancelled", e, cancellation);
        }
        catch (LibGit2SharpException e)
        {
            throw new GitException(Explain(e.Message), e);
        }
    }

    // libgit2's messages, made readable where they're cryptic.
    private static string Explain(string message)
    {
        message = message.Trim();
        if (message.Contains("authentication", StringComparison.OrdinalIgnoreCase)
            || message.Contains("401", StringComparison.Ordinal)
            || message.Contains("403", StringComparison.Ordinal))
        {
            return "The repository asks for a sign-in: it's private, or gone (" + message + ")";
        }

        if (message.Contains("resolve", StringComparison.OrdinalIgnoreCase)
            || message.Contains("connect", StringComparison.OrdinalIgnoreCase))
        {
            return "Couldn't reach the server: check the network (" + message + ")";
        }

        return message;
    }
}
