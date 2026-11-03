using System.Text;

namespace Launcher.Core.Config;

public sealed partial class ConfigLoader
{
    private sealed partial class Run
    {
        // ---- Variables and templates -------------------------------------------------------------

        /// <summary>Resolves a <c>[variables]</c> entry, recursively. Null means it has an error (already reported).</summary>
        private string? ResolveVariable(string name, List<string> chain)
        {
            if (_variables.TryGetValue(name, out var done))
            {
                return done;
            }

            var key = "variables." + name;
            if (_rawVariables is null || !_rawVariables.TryGet(name, out var node))
            {
                return null;
            }

            if (chain.Contains(name))
            {
                var cycle = string.Join(" -> ", chain.SkipWhile(n => n != name).Append(name));
                Error(node, key, $"variables refer to each other in a cycle: {cycle}");
                foreach (var member in chain.SkipWhile(n => n != name))
                {
                    _variables[member] = null;
                }

                return null;
            }

            if (!Template.IsValidName(name))
            {
                Error(node, key, "variable names can only use letters, digits, '_' and '-'");
                _variables[name] = null;
                return null;
            }

            if (Template.BuiltInVariables.Contains(name) || Template.LaunchPlaceholders.Contains(name))
            {
                Error(node, key, $"'{name}' is a built-in placeholder, so it can't be redefined");
                _variables[name] = null;
                return null;
            }

            if (node is not TomlScalar { Kind: TomlKind.String, Value: string raw })
            {
                Error(node, key, $"expected a string, found {TomlNode.KindName(node.Kind)}");
                _variables[name] = null;
                return null;
            }

            if (Template.TryParse(raw, _parts) is { } syntaxError)
            {
                Error(node, key, syntaxError);
                _variables[name] = null;
                return null;
            }

            var parts = _parts.ToArray();
            var result = new StringBuilder();
            chain.Add(name);
            foreach (var part in parts)
            {
                if (!part.IsPlaceholder)
                {
                    result.Append(part.Text);
                    continue;
                }

                if (part.Text == "home")
                {
                    result.Append(sources.HomeDir);
                    continue;
                }

                if (part.Text == "rom_root" || Template.LaunchPlaceholders.Contains(part.Text))
                {
                    Error(node, key, $"{{{part.Text}}} can't be used in [variables]; only {{home}} and other variables can");
                    chain.RemoveAt(chain.Count - 1);
                    _variables[name] = null;
                    return null;
                }

                if (_rawVariables.Contains(part.Text))
                {
                    var value = ResolveVariable(part.Text, chain);
                    if (value is null)
                    {
                        if (!_variables.ContainsKey(name))
                        {
                            Error(node, key, $"{{{part.Text}}} couldn't be resolved (see its own error)");
                            _variables[name] = null;
                        }

                        chain.RemoveAt(chain.Count - 1);
                        return null;
                    }

                    result.Append(value);
                    continue;
                }

                Error(node, key, $"unknown placeholder {{{part.Text}}}{Suggest(part.Text, VariableNames())}");
                chain.RemoveAt(chain.Count - 1);
                _variables[name] = null;
                return null;
            }

            chain.RemoveAt(chain.Count - 1);
            var resolved = result.ToString();
            _variables[name] = resolved;
            return resolved;
        }

        private List<string> VariableNames()
        {
            var names = new List<string> { "home", "rom_root" };
            if (_rawVariables is not null)
            {
                names.AddRange(_rawVariables.Keys);
            }

            return names;
        }

        /// <summary>
        /// Expands config variables in <paramref name="raw"/>. When <paramref name="keepLaunchPlaceholders"/>
        /// is true the result is still a template: literals are re-escaped and launch placeholders stay.
        /// Otherwise launch placeholders are errors and the result is plain text. Null means an error was reported.
        /// </summary>
        private string? Expand(string raw, TomlNode at, string key, bool keepLaunchPlaceholders, bool allowRomRoot)
        {
            if (Template.TryParse(raw, _parts) is { } syntaxError)
            {
                Error(at, key, syntaxError);
                return null;
            }

            var result = new StringBuilder();
            foreach (var part in _parts)
            {
                if (!part.IsPlaceholder)
                {
                    result.Append(keepLaunchPlaceholders ? Template.Escape(part.Text) : part.Text);
                    continue;
                }

                string? value;
                if (part.Text == "home")
                {
                    value = sources.HomeDir;
                }
                else if (part.Text == "rom_root" && allowRomRoot)
                {
                    value = _romRoot;
                }
                else if (Template.LaunchPlaceholders.Contains(part.Text))
                {
                    if (!keepLaunchPlaceholders)
                    {
                        Error(at, key, $"{{{part.Text}}} is only known at launch time, so it can't be used here");
                        return null;
                    }

                    result.Append('{').Append(part.Text).Append('}');
                    continue;
                }
                else if (_rawVariables is not null && _rawVariables.Contains(part.Text))
                {
                    value = ResolveVariable(part.Text, []);
                    if (value is null)
                    {
                        Error(at, key, $"variable {{{part.Text}}} has an error (see variables.{part.Text})");
                        return null;
                    }
                }
                else
                {
                    var known = VariableNames();
                    if (!allowRomRoot)
                    {
                        known.Remove("rom_root");
                    }

                    if (keepLaunchPlaceholders)
                    {
                        known.AddRange(Template.LaunchPlaceholders);
                    }

                    Error(at, key, part.Text == "rom_root"
                        ? "{rom_root} can't be used here"
                        : $"unknown placeholder {{{part.Text}}}{Suggest(part.Text, known)}. Define it under [variables] in settings.toml");
                    return null;
                }

                result.Append(keepLaunchPlaceholders ? Template.Escape(value) : value);
            }

            return result.ToString();
        }

        /// <summary>Expands a path and makes it absolute (relative paths resolve against ConfigDir).</summary>
        private string? ExpandPath(string raw, TomlNode at, string key, bool allowRomRoot)
        {
            var expanded = Expand(raw, at, key, keepLaunchPlaceholders: false, allowRomRoot);
            if (expanded is null)
            {
                return null;
            }

            if (expanded.Length == 0)
            {
                Error(at, key, "the path is empty");
                return null;
            }

            try
            {
                return Path.GetFullPath(Path.IsPathRooted(expanded) ? expanded : Path.Combine(sources.ConfigDir, expanded));
            }
            catch (Exception e) when (e is ArgumentException or NotSupportedException or PathTooLongException)
            {
                Error(at, key, $"'{expanded}' isn't a valid path: {e.Message}");
                return null;
            }
        }
    }
}
