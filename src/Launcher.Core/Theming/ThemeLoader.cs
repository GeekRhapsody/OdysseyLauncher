using Launcher.Core.Config;
using Launcher.Core.Models;

namespace Launcher.Core.Theming;

/// <summary>The files a theme's manifest names, by their paths relative to the theme's folder.</summary>
public interface IThemeFiles
{
    bool Exists(string relativePath);

    /// <summary>
    /// The <c>.glb</c>'s material names, or null when this theme's models aren't inspected before loading (a built-in
    /// theme's, which Core's tests check instead). A read failure gives null with <paramref name="error"/> set.
    /// </summary>
    IReadOnlyList<string>? MaterialsOf(string relativePath, out string? error);
}

/// <summary>A theme folder on disk. Does file I/O: never on the main thread.</summary>
/// <param name="inspect">
/// Whether its models' materials are read when the manifest loads: false for a built-in theme, whose models Core's
/// tests check instead.
/// </param>
public sealed class FolderThemeFiles(string folder, bool inspect = true) : IThemeFiles
{
    public string Folder { get; } = folder;

    public bool Exists(string relativePath) => File.Exists(PathOf(relativePath));

    public IReadOnlyList<string>? MaterialsOf(string relativePath, out string? error)
    {
        error = null;
        return inspect && GlbInfo.TryReadMaterials(PathOf(relativePath), out var materials, out error) ? materials : null;
    }

    private string PathOf(string relativePath) => Path.Combine(Folder, relativePath.Replace('/', Path.DirectorySeparatorChar));
}

/// <summary>One theme to load: its manifest's text and where its files are.</summary>
/// <param name="Folder">For <see cref="Theme.Folder"/>: an absolute path.</param>
public sealed record ThemeSource(string Id, ConfigFile Manifest, ThemeOrigin Origin, string Folder, IThemeFiles Files);

/// <param name="Theme">Null when the manifest can't be used at all (a syntax error, an unsupported format, or no usable look).</param>
public sealed record ThemeLoadResult(Theme? Theme, IReadOnlyList<Diagnostic> Diagnostics);

/// <summary>
/// Loads and validates a theme manifest (<c>themes/&lt;id&gt;/theme.toml</c>, A6). Like config, it never throws for a
/// user mistake: every problem is a diagnostic naming the file, line, column and key, and a bad entry is left out
/// (a template, a system's model) or falls back (a look block to the base theme's).
/// <para>
/// Every theme builds on the base theme (memory-card, <see cref="ThemeCatalog.BaseId"/>): what it leaves out is the
/// base's. Its look blocks and <c>look_transition_ms</c> default to the base's; <c>game_template</c> may name one of
/// the base's templates; and a <c>[templates.&lt;id&gt;]</c> with a base template's id extends it, each key it leaves
/// out (the model, the shape, a slot's chain or fit) being the base's.
/// </para>
/// </summary>
public static class ThemeLoader
{
    public const string ManifestFileName = "theme.toml";
    public const string FolderName = "themes";
    public const int SupportedFormat = 1;
    public const int DefaultLookTransitionMs = 300;

    private static readonly string[] RootKeys = ["format", "name", "author", "look_transition_ms", "look", "defaults", "templates", "systems"];
    private static readonly string[] LookKeys = ["background", "ambient", "lights"];
    private static readonly string[] BackgroundKeys = ["top_left", "top_right", "bottom_left", "bottom_right"];
    private static readonly string[] AmbientKeys = ["colour", "energy"];
    private static readonly string[] LightKeys = ["direction", "colour", "energy"];
    private static readonly string[] DefaultsKeys = ["system_model", "tint_system_model", "game_template"];
    private static readonly string[] TemplateKeys = ["model", "slots", "shape", "fit"];
    private static readonly string[] Shapes = ["model", "media"];
    private static readonly string[] Fits = ["crop", "whole"];
    private static readonly string[] SystemKeys = ["model", "tint", "game_template", "colour", "look"];
    private static readonly string[] SourceKeywords = ["generated", "authored"];

    /// <param name="baseTheme">
    /// The base theme, for whatever the theme leaves out or gets wrong. Null when loading the base theme itself, whose
    /// look must be complete.
    /// </param>
    public static ThemeLoadResult Load(ThemeSource source, Theme? baseTheme)
    {
        ArgumentNullException.ThrowIfNull(source);
        var diagnostics = new List<Diagnostic>();
        var root = source.Origin == ThemeOrigin.BuiltIn
            ? TomlTree.ParseBuiltIn(source.Manifest.Text, source.Manifest.Source, diagnostics)
            : TomlTree.Parse(source.Manifest.Text, source.Manifest.Source, diagnostics);
        if (root is null)
        {
            return new ThemeLoadResult(null, diagnostics);
        }

        var run = new Run(source, baseTheme, new TomlValidator(diagnostics));
        return new ThemeLoadResult(run.Read(root), diagnostics);
    }

    private sealed class Run(ThemeSource source, Theme? baseTheme, TomlValidator v)
    {
        private static readonly Dictionary<string, GameTemplate> NoTemplates = new(StringComparer.Ordinal);

        private IReadOnlyDictionary<string, GameTemplate> BaseTemplates => baseTheme?.Templates ?? NoTemplates;

        public Theme? Read(TomlTableNode root)
        {
            var fallback = baseTheme?.Look;
            v.WarnUnknownKeys(root, string.Empty, RootKeys);
            var errors = v.ErrorCount;
            v.CheckFormat(root, SupportedFormat);
            if (v.ErrorCount > errors)
            {
                return null;
            }

            var name = v.NonEmptyString(root, string.Empty, "name");
            if (name is null && !root.Contains("name"))
            {
                v.Error(root, "name", "a theme needs a name, e.g. name = \"Memory Card\"");
            }

            var author = v.String(root, string.Empty, "author");
            var transition = (int?)v.Integer(root, string.Empty, "look_transition_ms", 0, 5000) ?? baseTheme?.LookTransitionMs ?? DefaultLookTransitionMs;

            var lookTable = v.Table(root, string.Empty, "look");
            if (lookTable is null && fallback is null)
            {
                v.Error(root, "look", "the base theme needs a [look] with a background, an ambient colour and lights");
                return null;
            }

            var look = ReadLook(lookTable, "look", fallback, root);
            if (look is null)
            {
                return null;
            }

            var templates = ReadTemplates(v.Table(root, string.Empty, "templates"));
            var defaults = ReadDefaults(v.Table(root, string.Empty, "defaults"), templates);
            var systems = ReadSystems(v.Table(root, string.Empty, "systems"), templates, look);
            return new Theme(source.Id, name ?? source.Id, author, source.Origin, source.Folder, transition, look, defaults, templates, systems);
        }

        // ---- Looks ---------------------------------------------------------------------------------

        /// <summary>Each block the table has replaces the base's whole (A6); a missing or bad block keeps the base's.</summary>
        private Look? ReadLook(TomlTableNode? table, string prefix, Look? baseLook, TomlNode at)
        {
            if (table is not null)
            {
                v.WarnUnknownKeys(table, prefix, LookKeys);
            }

            LookBackground? background = null;
            if (table is not null && v.Table(table, prefix, "background") is { } backgroundTable)
            {
                background = ReadBackground(backgroundTable, prefix + ".background");
            }

            LookAmbient? ambient = null;
            if (table is not null && v.Table(table, prefix, "ambient") is { } ambientTable)
            {
                ambient = ReadAmbient(ambientTable, prefix + ".ambient");
            }

            IReadOnlyList<LookLight>? lights = null;
            if (table is not null && table.TryGet("lights", out var lightsNode))
            {
                lights = ReadLights(lightsNode, prefix + ".lights");
            }

            background ??= baseLook?.Background;
            ambient ??= baseLook?.Ambient;
            lights ??= baseLook?.Lights;
            if (background is null || ambient is null || lights is null)
            {
                var missing = new List<string>(3);
                if (background is null)
                {
                    missing.Add("background");
                }

                if (ambient is null)
                {
                    missing.Add("ambient");
                }

                if (lights is null)
                {
                    missing.Add("lights");
                }

                v.Error(table ?? at, prefix, $"the look is incomplete: it needs a valid {string.Join(", ", missing)}");
                return null;
            }

            return new Look(background, ambient, lights);
        }

        private LookBackground? ReadBackground(TomlTableNode table, string prefix)
        {
            v.WarnUnknownKeys(table, prefix, BackgroundKeys);
            var corners = new Rgb[4];
            var ok = true;
            for (var i = 0; i < BackgroundKeys.Length; i++)
            {
                if (Colour(table, prefix, BackgroundKeys[i], required: true) is { } colour)
                {
                    corners[i] = colour;
                }
                else
                {
                    ok = false;
                }
            }

            return ok ? new LookBackground(corners[0], corners[1], corners[2], corners[3]) : null;
        }

        private LookAmbient? ReadAmbient(TomlTableNode table, string prefix)
        {
            v.WarnUnknownKeys(table, prefix, AmbientKeys);
            var colour = Colour(table, prefix, "colour", required: true);
            var energy = v.Number(table, prefix, "energy", 0, 16) ?? 1.0;
            return colour is { } c ? new LookAmbient(c, (float)energy) : null;
        }

        private List<LookLight>? ReadLights(TomlNode node, string prefix)
        {
            if (node is not TomlArrayNode array)
            {
                v.Error(node, prefix, $"expected [[{prefix}]] tables, found {TomlNode.KindName(node.Kind)}");
                return null;
            }

            if (array.Items.Count is < 1 or > 3)
            {
                v.Error(node, prefix, $"a look has 1 to 3 directional lights, as icon.sys does; this has {array.Items.Count}");
                return null;
            }

            var lights = new List<LookLight>(array.Items.Count);
            for (var i = 0; i < array.Items.Count; i++)
            {
                var key = $"{prefix}[{i}]";
                if (array.Items[i] is not TomlTableNode light)
                {
                    v.Error(array.Items[i], key, $"expected a table, found {TomlNode.KindName(array.Items[i].Kind)}");
                    return null;
                }

                v.WarnUnknownKeys(light, key, LightKeys);
                var direction = Direction(light, key);
                var colour = Colour(light, key, "colour", required: false) ?? new Rgb(255, 255, 255);
                var energy = v.Number(light, key, "energy", 0, 16) ?? 1.0;
                if (direction is null)
                {
                    return null;
                }

                lights.Add(new LookLight(direction.Value, colour, (float)energy));
            }

            return lights;
        }

        private LightDirection? Direction(TomlTableNode light, string prefix)
        {
            var key = prefix + ".direction";
            if (!light.TryGet("direction", out var node))
            {
                v.Error(light, key, "a light needs a direction, e.g. direction = [-0.5, -0.4, -0.75]");
                return null;
            }

            if (node is not TomlArrayNode { Items.Count: 3 } array)
            {
                v.Error(node, key, "expected three numbers: [x, y, z] in view space (+X right, +Y up, +Z towards the viewer)");
                return null;
            }

            var xyz = new double[3];
            for (var i = 0; i < 3; i++)
            {
                if (!TomlValidator.TryNumber(array.Items[i], out xyz[i]))
                {
                    v.Error(array.Items[i], key, $"expected a number, found {TomlNode.KindName(array.Items[i].Kind)}");
                    return null;
                }
            }

            if (xyz[0] == 0 && xyz[1] == 0 && xyz[2] == 0)
            {
                v.Error(node, key, "the direction can't be zero");
                return null;
            }

            return new LightDirection((float)xyz[0], (float)xyz[1], (float)xyz[2]);
        }

        private Rgb? Colour(TomlTableNode table, string prefix, string key, bool required)
        {
            var path = TomlValidator.Join(prefix, key);
            if (!table.TryGet(key, out var node))
            {
                if (required)
                {
                    v.Error(table, path, "missing: write it as \"#RRGGBB\"");
                }

                return null;
            }

            if (node is TomlScalar { Kind: TomlKind.String, Value: string text } && Rgb.TryParse(text, out var colour))
            {
                return colour;
            }

            v.Error(node, path, node is TomlScalar { Kind: TomlKind.String, Value: string bad }
                ? $"'{bad}' isn't a colour: write it as \"#RRGGBB\" (sRGB)"
                : $"expected a colour string like \"#1B1F4A\", found {TomlNode.KindName(node.Kind)}");
            return null;
        }

        // ---- Templates -----------------------------------------------------------------------------

        private Dictionary<string, GameTemplate> ReadTemplates(TomlTableNode? table)
        {
            var templates = new Dictionary<string, GameTemplate>(StringComparer.Ordinal);
            if (table is null)
            {
                return templates;
            }

            foreach (var id in table.Keys)
            {
                table.TryGet(id, out var node);
                var prefix = "templates." + id;
                if (node is not TomlTableNode entry)
                {
                    v.Error(node, prefix, $"expected a table, found {TomlNode.KindName(node.Kind)}");
                    continue;
                }

                var errors = v.ErrorCount;
                if (!TomlValidator.IsValidId(id))
                {
                    v.Error(entry, prefix, "template ids can only use lower-case letters, digits, '_' and '-'");
                }

                v.WarnUnknownKeys(entry, prefix, TemplateKeys);

                // A base template's id extends it: every key left out is the base's, the model included.
                BaseTemplates.TryGetValue(id, out var extended);
                var model = ModelPath(entry, prefix, "model", required: extended is null);
                var modelFromBase = false;
                if (model is null && extended is not null && !entry.Contains("model"))
                {
                    model = extended.Model;
                    modelFromBase = true;
                }

                // A bad chain falls back to the slot's default chain (or the base's); only a bad model leaves the template out.
                var slots = extended is null ? new Dictionary<int, SlotChain>() : new Dictionary<int, SlotChain>(extended.Slots);
                var beforeSlots = v.ErrorCount;
                if (v.Table(entry, prefix, "slots") is { } slotsTable)
                {
                    ReadSlots(slotsTable, prefix + ".slots", slots);
                }

                // A bad fit leaves its slot as it was (cropped, or the base's), as a bad chain does.
                var whole = extended?.WholeSlots is { } baseWhole ? new HashSet<int>(baseWhole) : new HashSet<int>();
                if (v.Table(entry, prefix, "fit") is { } fitTable)
                {
                    ReadFit(fitTable, prefix + ".fit", whole);
                }

                var slotErrors = v.ErrorCount - beforeSlots;

                // A bad shape falls back to the model's own (or the base's), as a bad chain does.
                var beforeShape = v.ErrorCount;
                var shapeFromMedia = extended is null || entry.Contains("shape") ? ReadShape(entry, prefix) : extended.ShapeFromMedia;
                var shapeErrors = v.ErrorCount - beforeShape;

                // The base's model is checked by Core's tests, not here.
                if (model is not null && !modelFromBase && CheckMaterials(entry, prefix, model, slots) is { } present)
                {
                    if (shapeFromMedia && !present[MediaSlots.Cover])
                    {
                        entry.TryGet("shape", out var shapeNode);
                        v.Warning(shapeNode, prefix + ".shape", $"'{model}' has no 'cover' material, so its shape can't follow the cover; it keeps its own");
                        shapeFromMedia = false;
                    }

                    foreach (var slot in whole)
                    {
                        if (!present[slot])
                        {
                            entry.TryGet("fit", out var fitNode);
                            v.Warning(fitNode, $"{prefix}.fit.{MediaSlots.Names[slot]}", $"'{model}' has no '{MediaSlots.Names[slot]}' material, so this is never used");
                        }
                    }
                }

                if (v.ErrorCount - slotErrors - shapeErrors > errors || model is null)
                {
                    v.Info(entry, prefix, "this template is left out until its errors are fixed; systems that use it fall back to the next model in line");
                    continue;
                }

                templates[id] = new GameTemplate(id, model, slots, shapeFromMedia, whole.Count > 0 ? whole : null, source.Id, modelFromBase);
            }

            return templates;
        }

        private void ReadSlots(TomlTableNode table, string prefix, Dictionary<int, SlotChain> slots)
        {
            foreach (var name in table.Keys)
            {
                table.TryGet(name, out var node);
                var key = $"{prefix}.{name}";
                var slot = MediaSlots.IndexOf(name);
                if (slot < 0)
                {
                    v.Error(node, key, $"'{name}' isn't a media slot{TomlValidator.Suggest(name, MediaSlots.Names)}. The slots are {string.Join(", ", MediaSlots.Names)}");
                    continue;
                }

                if (v.StringArray(node, key) is not { } entries)
                {
                    continue;
                }

                var sources = new List<SlotSource>(entries.Count);
                var ended = false;
                var ok = true;
                foreach (var entry in entries)
                {
                    SlotSource source;
                    if (entry == "generated")
                    {
                        if (!MediaSlots.HasGenerator(slot))
                        {
                            v.Error(node, key, $"the launcher can't draw a {name}: 'generated' is only for cover, back, spine and label");
                            ok = false;
                            continue;
                        }

                        source = SlotSource.Generated;
                    }
                    else if (entry == "authored")
                    {
                        source = SlotSource.Authored;
                    }
                    else if (MediaSlots.IndexOf(entry) is var kind and >= 0)
                    {
                        source = SlotSource.Media(kind);
                    }
                    else
                    {
                        v.Error(node, key, $"unknown source '{entry}'{TomlValidator.Suggest(entry, [.. MediaSlots.Names, .. SourceKeywords])}. Use media kinds ({string.Join(", ", MediaSlots.Names)}), \"generated\" or \"authored\"");
                        ok = false;
                        continue;
                    }

                    if (ended)
                    {
                        v.Warning(node, key, $"'{entry}' comes after '{sources[^1]}', which always shows, so it's never used");
                        continue;
                    }

                    if (sources.Contains(source))
                    {
                        v.Warning(node, key, $"'{entry}' is listed twice");
                        continue;
                    }

                    sources.Add(source);
                    ended = source.Kind != SlotSourceKind.Media;
                }

                if (ok)
                {
                    slots[slot] = new SlotChain(slot, sources);
                }
            }
        }

        /// <summary>
        /// <c>[templates.&lt;id&gt;.fit]</c>: per slot, <c>"crop"</c> (fill the face, the default) or <c>"whole"</c>
        /// (fitted inside it, over the slot's fallback).
        /// </summary>
        private void ReadFit(TomlTableNode table, string prefix, HashSet<int> whole)
        {
            foreach (var name in table.Keys)
            {
                table.TryGet(name, out var node);
                var key = $"{prefix}.{name}";
                var slot = MediaSlots.IndexOf(name);
                if (slot < 0)
                {
                    v.Error(node, key, $"'{name}' isn't a media slot{TomlValidator.Suggest(name, MediaSlots.Names)}. The slots are {string.Join(", ", MediaSlots.Names)}");
                    continue;
                }

                var fit = v.String(table, prefix, name);
                if (fit == "whole")
                {
                    whole.Add(slot);
                }
                else if (fit == "crop")
                {
                    whole.Remove(slot);
                }
                else if (fit is not null)
                {
                    v.Error(node, key, $"unknown fit '{fit}'{TomlValidator.Suggest(fit, Fits)}: use \"crop\" (fill the face) or \"whole\" (fitted inside it)");
                }
            }
        }

        /// <summary>
        /// A template's model must be a readable <c>.glb</c>; it needn't have a cover or any slot (M6: a CRT with only a
        /// screenshot is fine), but a chain for a slot the model doesn't have is never used.
        /// </summary>
        /// <summary><c>shape</c>: true for <c>"media"</c>; false for <c>"model"</c> (the default) or a bad value.</summary>
        private bool ReadShape(TomlTableNode entry, string prefix)
        {
            var shape = v.String(entry, prefix, "shape");
            if (shape is null || shape == "model")
            {
                return false;
            }

            if (shape == "media")
            {
                return true;
            }

            entry.TryGet("shape", out var node);
            v.Error(node, prefix + ".shape", $"unknown shape '{shape}'{TomlValidator.Suggest(shape, Shapes)}: use \"model\" (the model's own) or \"media\" (from each game's cover and spine)");
            return false;
        }

        /// <summary>Which slots the model has, read from its file; null when it can't be read (a built-in theme's model).</summary>
        private bool[]? CheckMaterials(TomlTableNode entry, string prefix, string model, Dictionary<int, SlotChain> slots)
        {
            var materials = source.Files.MaterialsOf(model, out var error);
            entry.TryGet("model", out var modelNode);
            if (materials is null)
            {
                if (error is not null)
                {
                    v.Error(modelNode, prefix + ".model", $"'{model}' {error}");
                }

                return null;
            }

            var present = new bool[MediaSlots.Count];
            foreach (var material in materials)
            {
                if (MediaSlots.OfMaterial(material) is var slot and >= 0)
                {
                    present[slot] = true;
                }
            }

            foreach (var slot in slots.Keys)
            {
                if (!present[slot])
                {
                    entry.TryGet("slots", out var slotsNode);
                    v.Warning(slotsNode, $"{prefix}.slots.{MediaSlots.Names[slot]}", $"'{model}' has no '{MediaSlots.Names[slot]}' material, so this chain is never used");
                }
            }

            return present;
        }

        /// <summary>A <c>.glb</c> inside the theme's folder that exists.</summary>
        private string? ModelPath(TomlTableNode table, string prefix, string key, bool required)
        {
            var path = TomlValidator.Join(prefix, key);
            if (!table.TryGet(key, out var node))
            {
                if (required)
                {
                    v.Error(table, path, "missing: the model's .glb, relative to the theme's folder, e.g. \"models/templates/dvd_case.glb\"");
                }

                return null;
            }

            if (v.String(table, prefix, key) is not { } raw)
            {
                return null;
            }

            var relative = raw.Replace('\\', '/');
            while (relative.StartsWith("./", StringComparison.Ordinal))
            {
                relative = relative[2..];
            }

            if (relative.Length == 0 || relative.StartsWith('/') || relative.Contains(':', StringComparison.Ordinal)
                || relative.Split('/').Contains(".."))
            {
                v.Error(node, path, $"'{raw}' must be a path inside the theme's folder, e.g. \"models/systems/ps2.glb\"");
                return null;
            }

            if (!relative.EndsWith(".glb", StringComparison.OrdinalIgnoreCase))
            {
                v.Error(node, path, $"'{raw}' isn't a .glb: models are glTF 2.0 binaries (A7)");
                return null;
            }

            if (!source.Files.Exists(relative))
            {
                v.Error(node, path, $"'{raw}' doesn't exist in the theme's folder");
                return null;
            }

            return relative;
        }

        // ---- Defaults and systems ------------------------------------------------------------------

        private ThemeDefaults ReadDefaults(TomlTableNode? table, Dictionary<string, GameTemplate> templates)
        {
            if (table is null)
            {
                return new ThemeDefaults(null, false, null);
            }

            v.WarnUnknownKeys(table, "defaults", DefaultsKeys);
            var model = ModelPath(table, "defaults", "system_model", required: false);
            var tint = v.Bool(table, "defaults", "tint_system_model") ?? false;
            var template = TemplateId(table, "defaults", templates);
            return new ThemeDefaults(model, tint, template);
        }

        private Dictionary<string, ThemeSystem> ReadSystems(TomlTableNode? table, Dictionary<string, GameTemplate> templates, Look look)
        {
            var systems = new Dictionary<string, ThemeSystem>(StringComparer.Ordinal);
            if (table is null)
            {
                return systems;
            }

            foreach (var id in table.Keys)
            {
                table.TryGet(id, out var node);
                var prefix = "systems." + id;
                if (node is not TomlTableNode entry)
                {
                    v.Error(node, prefix, $"expected a table, found {TomlNode.KindName(node.Kind)}");
                    continue;
                }

                if (!TomlValidator.IsValidId(id))
                {
                    v.Error(entry, prefix, "system ids can only use lower-case letters, digits, '_' and '-'");
                    continue;
                }

                v.WarnUnknownKeys(entry, prefix, SystemKeys);
                var model = ModelPath(entry, prefix, "model", required: false);
                var tint = v.Bool(entry, prefix, "tint");
                var template = TemplateId(entry, prefix, templates);
                var colour = Colour(entry, prefix, "colour", required: false);
                var systemLook = v.Table(entry, prefix, "look") is { } lookTable ? ReadLook(lookTable, prefix + ".look", look, entry) ?? look : look;
                systems[id] = new ThemeSystem(id, model, tint, template, colour, systemLook);
            }

            return systems;
        }

        private string? TemplateId(TomlTableNode table, string prefix, Dictionary<string, GameTemplate> templates)
        {
            if (v.String(table, prefix, "game_template") is not { } id)
            {
                return null;
            }

            if (templates.ContainsKey(id) || BaseTemplates.ContainsKey(id))
            {
                return id;
            }

            table.TryGet("game_template", out var node);

            // A model's path where its template's id belongs: say how a .glb becomes a template.
            if (id.EndsWith(".glb", StringComparison.OrdinalIgnoreCase) || id.Contains('/', StringComparison.Ordinal))
            {
                var name = Path.GetFileNameWithoutExtension(id).ToLowerInvariant();
                v.Error(node, prefix + ".game_template",
                    $"'{id}' is a model, but game_template names a template: declare it with [templates.{name}] and model = \"{id}\" " +
                    $"(and shape = \"media\" for a box shaped by each game's art), then write game_template = \"{name}\"; the next model in line is used");
                return null;
            }

            var known = templates.Keys.Concat(BaseTemplates.Keys).Distinct(StringComparer.Ordinal).Order(StringComparer.Ordinal).ToList();
            v.Error(node, prefix + ".game_template",
                $"no template '{id}' in this theme or the base theme{TomlValidator.Suggest(id, known)}; the next model in line is used");
            return null;
        }
    }
}
