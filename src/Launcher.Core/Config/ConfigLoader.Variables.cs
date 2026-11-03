using System.Text;

namespace Launcher.Core.Config;

public sealed partial class ConfigLoader
{
    private sealed partial class Run
    {
        // ---- Variables and templates -------------------------------------------------------------

        /// <summary>
        /// Resolves a <c>[variables]</c> entry, recursively. Null means it has an error (already reported), or it's a list
        /// (<see cref="IsList"/>), whose places are in <c>_lists</c>.
        /// </summary>
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

            if (node is TomlArrayNode array)
            {
                _variables[name] = null;
                _lists[name] = ResolveList(name, key, array, chain);
                return null;
            }

            if (node is not TomlScalar { Kind: TomlKind.String, Value: string raw })
            {
                Error(node, key, $"expected a string or an array of strings, found {TomlNode.KindName(node.Kind)}");
                _variables[name] = null;
                return null;
            }

            chain.Add(name);
            var resolved = ResolveText(name, raw, node, key, chain);
            chain.RemoveAt(chain.Count - 1);
            _variables[name] = resolved;
            return resolved;
        }

        /// <summary>A list variable's places (A5 Finding programs), each resolved as a string variable is; null on an error.</summary>
        private List<string>? ResolveList(string name, string key, TomlArrayNode array, List<string> chain)
        {
            var places = new List<string>(array.Items.Count);
            chain.Add(name);
            foreach (var item in array.Items)
            {
                if (item is not TomlScalar { Kind: TomlKind.String, Value: string raw })
                {
                    Error(item, key, $"expected an array of strings, but an item is {TomlNode.KindName(item.Kind)}");
                    places = null;
                    break;
                }

                if (ResolveText(name, raw, item, key, chain) is not { } place)
                {
                    places = null;
                    break;
                }

                places.Add(place);
            }

            chain.RemoveAt(chain.Count - 1);
            return places;
        }

        /// <summary>
        /// A string variable's text (or one of a list's items) with <c>{home}</c> and other string variables expanded.
        /// Null means an error, reported here unless a cycle through <paramref name="name"/> already was.
        /// </summary>
        private string? ResolveText(string name, string raw, TomlNode node, string key, List<string> chain)
        {
            if (Template.TryParse(raw, _parts) is { } syntaxError)
            {
                Error(node, key, syntaxError);
                return null;
            }

            var parts = _parts.ToArray();
            var result = new StringBuilder();
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
                    return null;
                }

                if (IsList(part.Text))
                {
                    Error(node, key, $"{{{part.Text}}} is a list of places, so only an emulator's executable and core can use it");
                    return null;
                }

                if (_rawVariables!.Contains(part.Text))
                {
                    var value = ResolveVariable(part.Text, chain);
                    if (value is null)
                    {
                        if (!_variables.ContainsKey(name))
                        {
                            Error(node, key, $"{{{part.Text}}} couldn't be resolved (see its own error)");
                        }

                        return null;
                    }

                    result.Append(value);
                    continue;
                }

                Error(node, key, $"unknown placeholder {{{part.Text}}}{Suggest(part.Text, VariableNames())}");
                return null;
            }

            return result.ToString();
        }

        /// <summary>Whether <c>[variables]</c> defines <paramref name="name"/> as a list of places.</summary>
        private bool IsList(string name) =>
            _rawVariables is not null && _rawVariables.TryGet(name, out var node) && node is TomlArrayNode;

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
                else if (IsList(part.Text))
                {
                    Error(at, key, $"{{{part.Text}}} is a list of places, so only an emulator's executable and core can use it");
                    return null;
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
            return expanded is null ? null : FullPath(expanded, at, key);
        }

        private string? FullPath(string expanded, TomlNode at, string key)
        {
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

        /// <summary>
        /// An emulator's <c>executable</c> or <c>core</c>: the places to look, in order (A5 Finding programs). It's a
        /// string or an array of strings; an entry using a list variable is one place for each of its items (one list
        /// variable an entry). A bare name stays as it is, to be looked for on the PATH; anything else is made absolute.
        /// <paramref name="listVariable"/> is the list variable a single entry uses. Null means an error was reported.
        /// </summary>
        private List<string>? Places(TomlNode node, string key, out string? listVariable)
        {
            listVariable = null;
            List<string>? entries = node switch
            {
                TomlArrayNode => StringArray(node, key, string.Empty),
                TomlScalar { Kind: TomlKind.String, Value: string single } => [single],
                _ => null,
            };
            if (entries is null)
            {
                if (node is not TomlArrayNode)
                {
                    Error(node, key, $"expected a string or an array of strings, found {TomlNode.KindName(node.Kind)}");
                }

                return null;
            }

            if (entries.Count == 0)
            {
                Error(node, key, "the list has no places to look");
                return null;
            }

            var places = new List<string>();
            foreach (var entry in entries)
            {
                if (!AddPlaces(entry, node, key, places, out var used))
                {
                    return null;
                }

                listVariable = entries.Count == 1 ? used : null;
            }

            return places;
        }

        /// <summary>Adds one entry's places to <paramref name="places"/>; false means an error was reported.</summary>
        private bool AddPlaces(string entry, TomlNode node, string key, List<string> places, out string? listVariable)
        {
            listVariable = null;
            if (Template.TryParse(entry, _parts) is { } syntaxError)
            {
                Error(node, key, syntaxError);
                return false;
            }

            var parts = _parts.ToArray();
            foreach (var part in parts)
            {
                if (!part.IsPlaceholder || !IsList(part.Text) || part.Text == listVariable)
                {
                    continue;
                }

                if (listVariable is not null)
                {
                    Error(node, key, $"'{entry}' uses two lists of places ({{{listVariable}}} and {{{part.Text}}}); an entry can use one");
                    return false;
                }

                listVariable = part.Text;
            }

            if (listVariable is null)
            {
                return AddPlace(entry, node, key, places);
            }

            ResolveVariable(listVariable, []);
            if (_lists.GetValueOrDefault(listVariable) is not { } items)
            {
                Error(node, key, $"variable {{{listVariable}}} has an error (see variables.{listVariable})");
                return false;
            }

            foreach (var item in items)
            {
                var text = new StringBuilder();
                foreach (var part in parts)
                {
                    text.Append(!part.IsPlaceholder ? Template.Escape(part.Text)
                        : part.Text == listVariable ? Template.Escape(item)
                        : "{" + part.Text + "}");
                }

                if (!AddPlace(text.ToString(), node, key, places))
                {
                    return false;
                }
            }

            return true;
        }

        private bool AddPlace(string entry, TomlNode node, string key, List<string> places)
        {
            var expanded = Expand(entry, node, key, keepLaunchPlaceholders: false, allowRomRoot: true);
            var place = expanded is null ? null
                : Launching.ProgramSearch.IsBareName(expanded) ? expanded
                : FullPath(expanded, node, key);
            if (place is null)
            {
                return false;
            }

            places.Add(place);
            return true;
        }
    }
}
