using System.Globalization;
using System.Text;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// The Steam client's state on Linux, from <c>registry.vdf</c>, the text file Steam keeps its registry in off Windows,
/// read for the keys <see cref="Windows.WindowsSteamClient"/> reads from Windows' registry (ARCHITECTURE.md A1, Platform):
/// <list type="bullet">
/// <item><c>Registry/HKLM/Software/Valve/Steam/SteamPID</c>, the running client's process (0 once it has closed), as
/// Windows' <c>ActiveProcess\pid</c>;</item>
/// <item><c>Registry/HKCU/Software/Valve/Steam/RunningAppID</c>, the game it's running now (Linux's Steam has left it
/// 0 since its 2023 interface, Valve's steam-for-linux issue 9672, so the app's own flag usually decides);</item>
/// <item><c>Registry/HKCU/Software/Valve/Steam/Apps/&lt;app id&gt;</c>: <c>installed</c>, <c>Running</c> and
/// <c>Updating</c>, each "0" or "1".</item>
/// </list>
/// Steam's own package keeps the file at <c>~/.steam/registry.vdf</c>, Flathub's at
/// <c>~/.var/app/com.valvesoftware.Steam/.steam/registry.vdf</c>; with both, the one written last is the Steam in use.
/// Keys are matched ignoring case, as Steam's KeyValues match them. A file that can't be read as KeyValues says nothing
/// is running, as a missing one does.
/// </summary>
/// <param name="home">The user's home folder.</param>
/// <param name="proc">The proc file system: <c>/proc</c>, or a test's made-up one.</param>
public sealed class LinuxSteamClient(string home, string proc) : ISteamClient
{
    /// <summary>Far bigger than the registry of a library of thousands of games; a bigger file isn't read.</summary>
    private const long MaxBytes = 8 * 1024 * 1024;

    /// <summary>Deeper than Steam's registry nests (six levels to an app's keys); deeper text isn't read.</summary>
    private const int MaxDepth = 32;

    private readonly string[] _registries =
    [
        Path.Combine(home, ".steam", "registry.vdf"),
        Path.Combine(home, ".var", "app", "com.valvesoftware.Steam", ".steam", "registry.vdf"),
    ];

    /// <summary>The <c>registry.vdf</c> of the Steam in use, or null if Steam has never run for this user.</summary>
    public string? ClientPath => Registry()?.FullName;

    public SteamAppState GetAppState(uint appId)
    {
        var registry = Registry();
        if (registry is null || registry.Length > MaxBytes || Parse(File.ReadAllText(registry.FullName)) is not { } root)
        {
            return default;
        }

        var steam = Find(root, "Registry", "HKCU", "Software", "Valve", "Steam");
        var app = Find(steam, "Apps", appId.ToString(CultureInfo.InvariantCulture));
        return new SteamAppState(
            IsAlive(Number(Find(root, "Registry", "HKLM", "Software", "Valve", "Steam"), "SteamPID")),
            Installed: Number(app, "installed") == 1,
            Running: Number(app, "Running") == 1,
            Current: Number(steam, "RunningAppID") == appId,
            Updating: Number(app, "Updating") == 1);
    }

    private FileInfo? Registry()
    {
        FileInfo? newest = null;
        foreach (var path in _registries)
        {
            var file = new FileInfo(path);
            if (file.Exists && (newest is null || file.LastWriteTimeUtc > newest.LastWriteTimeUtc))
            {
                newest = file;
            }
        }

        return newest;
    }

    private bool IsAlive(uint processId) =>
        processId != 0 && Directory.Exists(Path.Combine(proc, processId.ToString(CultureInfo.InvariantCulture)));

    private static Dictionary<string, object>? Find(Dictionary<string, object>? block, params string[] keys)
    {
        foreach (var key in keys)
        {
            block = block is not null && block.TryGetValue(key, out var value) ? value as Dictionary<string, object> : null;
        }

        return block;
    }

    /// <summary>A key's value as a number, or 0 if it's missing, a block, or not a number.</summary>
    private static uint Number(Dictionary<string, object>? block, string key) =>
        block is not null && block.TryGetValue(key, out var value) && value is string text
            && uint.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out var number)
            ? number
            : 0;

    /// <summary>
    /// Valve's text KeyValues: a key, then a value or a block in braces; keys and values quoted (a backslash escaping the
    /// next character) or bare; <c>//</c> comments. Null for text that isn't that, or nests deeper than <see cref="MaxDepth"/>.
    /// </summary>
    private static Dictionary<string, object>? Parse(string text)
    {
        var tokens = Tokens(text);
        var index = 0;
        return tokens is null ? null : Block(tokens, ref index, depth: 0);
    }

    private static Dictionary<string, object>? Block(List<(string Text, bool Quoted)> tokens, ref int index, int depth)
    {
        var block = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
        while (index < tokens.Count)
        {
            var (key, keyQuoted) = tokens[index++];
            if (!keyQuoted && key == "}")
            {
                return depth > 0 ? block : null;
            }

            if ((!keyQuoted && key == "{") || index == tokens.Count)
            {
                return null;
            }

            var (value, valueQuoted) = tokens[index++];
            if (valueQuoted || value is not ("{" or "}"))
            {
                block[key] = value;
                continue;
            }

            var child = value == "{" && depth < MaxDepth ? Block(tokens, ref index, depth + 1) : null;
            if (child is null)
            {
                return null;
            }

            block[key] = child;
        }

        return depth == 0 ? block : null;
    }

    /// <summary>The text's tokens, a brace being one of its own unless quoted; null for an unclosed quote.</summary>
    private static List<(string Text, bool Quoted)>? Tokens(string text)
    {
        var tokens = new List<(string, bool)>();
        var i = 0;
        while (i < text.Length)
        {
            var c = text[i];
            if (char.IsWhiteSpace(c))
            {
                i++;
            }
            else if (c == '/' && i + 1 < text.Length && text[i + 1] == '/')
            {
                var end = text.IndexOf('\n', i);
                i = end < 0 ? text.Length : end;
            }
            else if (c is '{' or '}')
            {
                tokens.Add((c.ToString(), false));
                i++;
            }
            else if (c == '"')
            {
                if (Quoted(text, ref i) is not { } quoted)
                {
                    return null;
                }

                tokens.Add((quoted, true));
            }
            else
            {
                var start = i;
                while (i < text.Length && !char.IsWhiteSpace(text[i]) && text[i] is not ('{' or '}' or '"'))
                {
                    i++;
                }

                tokens.Add((text[start..i], false));
            }
        }

        return tokens;
    }

    /// <summary>The quoted string starting at <paramref name="i"/>, which is left after its closing quote.</summary>
    private static string? Quoted(string text, ref int i)
    {
        var value = new StringBuilder();
        for (i++; i < text.Length; i++)
        {
            var c = text[i];
            if (c == '"')
            {
                i++;
                return value.ToString();
            }

            if (c == '\\' && i + 1 < text.Length)
            {
                c = text[++i] switch
                {
                    'n' => '\n',
                    't' => '\t',
                    var escaped => escaped,
                };
            }

            value.Append(c);
        }

        return null;
    }
}
