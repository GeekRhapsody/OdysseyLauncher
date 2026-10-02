using System.Text;

namespace Launcher.Core.Scraping;

/// <summary>
/// The credentials this build carries (ARCHITECTURE.md A5, "Secrets"): ScreenScraper's developer ID and password,
/// issued for this software, so users only need their own account. The release workflow writes
/// <c>BuiltInAccounts.Release.g.cs</c> beside this file from the repository's secrets
/// (<c>tools/write-built-in-accounts.ps1</c>) before it builds. That file is gitignored, so the values are never in
/// the repo and a build from source has none: without it, the partial method's call is compiled away.
/// <para>
/// The values are stored XORed with a key made for each build, so they aren't plain text in the DLL. That hides them
/// from a casual search, not from someone determined: anything a client sends can be read off the wire.
/// ScreenScraper can revoke them, and a new release carries new ones.
/// </para>
/// </summary>
internal static partial class BuiltInAccounts
{
    /// <summary>Keyed "section.key", as <see cref="ProviderAccounts.FromValues"/> takes them. Empty in a build from source.</summary>
    public static IReadOnlyDictionary<string, string> Values { get; } = Read();

    /// <summary>For the generated file: <paramref name="data"/> XORed with <paramref name="key"/>, as UTF-8.</summary>
    internal static string Decode(ReadOnlySpan<byte> data, ReadOnlySpan<byte> key)
    {
        if (key.IsEmpty)
        {
            throw new ArgumentException("The key is empty.", nameof(key));
        }

        var bytes = new byte[data.Length];
        for (var i = 0; i < data.Length; i++)
        {
            bytes[i] = (byte)(data[i] ^ key[i % key.Length]);
        }

        return Encoding.UTF8.GetString(bytes);
    }

    private static Dictionary<string, string> Read()
    {
        string? devId = null;
        string? devPassword = null;
        ScreenScraper(ref devId, ref devPassword);
        var values = new Dictionary<string, string>(StringComparer.Ordinal);

        // A pair or nothing: half a pair can't sign in.
        if (!string.IsNullOrWhiteSpace(devId) && !string.IsNullOrWhiteSpace(devPassword))
        {
            values["screenscraper.dev_id"] = devId.Trim();
            values["screenscraper.dev_password"] = devPassword.Trim();
        }

        return values;
    }

    /// <summary>Implemented only by the release's generated file.</summary>
    static partial void ScreenScraper(ref string? devId, ref string? devPassword);
}
