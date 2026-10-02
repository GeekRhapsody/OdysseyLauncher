using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Scraping;

namespace Launcher.Core.Tests.Scraping;

public sealed class BuiltInAccountsTests
{
    private static readonly Dictionary<string, string> BuiltIn = new(StringComparer.Ordinal)
    {
        ["screenscraper.dev_id"] = "built-dev",
        ["screenscraper.dev_password"] = "built-pass",
    };

    [Fact]
    public void Built_in_credentials_are_used_beside_the_users_own_account()
    {
        var text = """
            [screenscraper]
            username = "me"
            password = "mine"
            """;

        var accounts = ProviderAccounts.Parse(text, "secrets.toml", _ => null, BuiltIn).Accounts;

        Assert.Equal("built-dev", accounts.ScreenScraperDevId);
        Assert.Equal("built-pass", accounts.ScreenScraperDevPassword);
        Assert.Equal("me", accounts.ScreenScraperUsername);
        Assert.Equal(CredentialSource.BuiltIn, accounts.SourceOf("screenscraper", "dev_id"));
        Assert.Equal(CredentialSource.File, accounts.SourceOf("screenscraper", "username"));

        // The redactor is built from Values, so the built-in ones are masked like the rest.
        Assert.Contains("built-pass", accounts.Values);
        Assert.DoesNotContain("built-pass", accounts.ToString(), StringComparison.Ordinal);
    }

    [Fact]
    public void The_built_in_pair_wins_over_the_file_and_the_environment_which_are_told_so()
    {
        var text = """
            [screenscraper]
            dev_id = "own-dev"
            """;
        var environment = new Dictionary<string, string> { ["ODYSSEY_SCREENSCRAPER_DEV_PASSWORD"] = "own-pass" };

        var result = ProviderAccounts.Parse(text, "secrets.toml", name => environment.GetValueOrDefault(name), BuiltIn);

        var accounts = result.Accounts;
        Assert.Equal("built-dev", accounts.ScreenScraperDevId);
        Assert.Equal("built-pass", accounts.ScreenScraperDevPassword);
        Assert.Equal(CredentialSource.BuiltIn, accounts.SourceOf("screenscraper", "dev_password"));
        Assert.DoesNotContain("own-dev", accounts.Values);
        Assert.DoesNotContain("own-pass", accounts.Values);
        Assert.Equal(2, result.Diagnostics.Count);
        Assert.All(result.Diagnostics, d => Assert.Equal(Severity.Info, d.Severity));
        Assert.Contains(result.Diagnostics, d => d.Key == "screenscraper.dev_id" && d.Line == 2);
        Assert.Contains(result.Diagnostics, d => d.Key == "screenscraper.dev_password" && d.Source == "ODYSSEY_SCREENSCRAPER_DEV_PASSWORD");
        Assert.All(result.Diagnostics, d => Assert.DoesNotContain("own-", d.ToString(), StringComparison.Ordinal));
    }

    [Fact]
    public void Without_built_in_credentials_the_users_own_developer_credentials_are_used()
    {
        var text = """
            [screenscraper]
            dev_id = "own-dev"
            dev_password = "own-pass"
            """;

        var result = ProviderAccounts.Parse(text, "secrets.toml", _ => null, new Dictionary<string, string>());

        Assert.Empty(result.Diagnostics);
        Assert.Equal("own-dev", result.Accounts.ScreenScraperDevId);
        Assert.Equal(CredentialSource.File, result.Accounts.SourceOf("screenscraper", "dev_password"));
    }

    [Fact]
    public void Without_being_asked_for_them_loading_ignores_the_built_in_credentials()
    {
        var accounts = ProviderAccounts.Parse(null, "secrets.toml", _ => null).Accounts;

        Assert.Empty(accounts.Values);
    }

    [Fact]
    public void Decode_reverses_the_scrambling_the_release_script_does()
    {
        var plain = Encoding.UTF8.GetBytes("pâss-wörd 1");
        byte[] key = [0x5A, 0xC3, 0x01];
        var data = new byte[plain.Length];
        for (var i = 0; i < plain.Length; i++)
        {
            data[i] = (byte)(plain[i] ^ key[i % key.Length]);
        }

        Assert.Equal("pâss-wörd 1", BuiltInAccounts.Decode(data, key));
    }

    [Fact]
    public void This_build_carries_a_pair_or_nothing_and_a_release_carries_the_pair()
    {
        var values = ProviderAccounts.BuiltIn;

        Assert.True(values.Count is 0 or 2);
        if (values.Count == 2)
        {
            Assert.False(string.IsNullOrWhiteSpace(values["screenscraper.dev_id"]));
            Assert.False(string.IsNullOrWhiteSpace(values["screenscraper.dev_password"]));
        }

        // The release workflow sets this when it has written BuiltInAccounts.Release.g.cs, to check it was compiled in.
        if (Environment.GetEnvironmentVariable("ODYSSEY_EXPECT_BUILT_IN_ACCOUNTS") == "true")
        {
            Assert.Equal(2, values.Count);
        }
    }
}
