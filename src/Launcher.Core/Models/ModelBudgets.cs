namespace Launcher.Core.Models;

/// <summary>What a model is for, which sets its budget (A7).</summary>
public enum ModelKind
{
    /// <summary>A theme's game template, or the user's <c>ConfigDir/models/templates/&lt;system&gt;.glb</c>.</summary>
    GameTemplate,

    /// <summary>The user's model for one game, <c>&lt;media folder&gt;/&lt;system&gt;/models/&lt;name&gt;.glb</c>.</summary>
    PerGame,

    /// <summary>A system card: a theme's system model, or the user's <c>ConfigDir/models/systems/&lt;system&gt;.glb</c>.</summary>
    SystemModel,
}

/// <summary>
/// A7's budgets for one kind of model. Textures don't count the media a slot shows (that's streamed), only the
/// model's own base colour images (normal, metallic-roughness, occlusion and emissive maps aren't drawn yet, so they
/// cost nothing and don't count). Over budget, a model loads with a warning; more than 2× over a count (triangles, textures,
/// materials, joints, morph targets), it's rejected and the next model in line is used. A texture larger than
/// <see cref="TextureSide"/> is scaled down when the model is processed, so its size never rejects a model.
/// </summary>
public sealed record ModelBudget(int Triangles, int Textures, int TextureSide, int Materials)
{
    /// <summary>Skinning: joints per skin (A7).</summary>
    public const int Joints = 64;

    /// <summary>Morph targets per mesh (A7).</summary>
    public const int MorphTargets = 8;

    public static ModelBudget GameTemplate { get; } = new(2_000, 2, 1024, 4);

    public static ModelBudget PerGame { get; } = new(5_000, 2, 1024, 4);

    public static ModelBudget SystemModel { get; } = new(30_000, 4, 2048, 8);

    public static ModelBudget For(ModelKind kind) => kind switch
    {
        ModelKind.PerGame => PerGame,
        ModelKind.SystemModel => SystemModel,
        _ => GameTemplate,
    };

    public static string Describe(ModelKind kind) => kind switch
    {
        ModelKind.PerGame => "per-game model",
        ModelKind.SystemModel => "system model",
        _ => "game template",
    };
}

/// <summary>The animation clips the launcher plays (A7). Any other clip is ignored.</summary>
public enum ModelClip
{
    /// <summary>Loops while the item isn't focused.</summary>
    Idle,

    /// <summary>Loops while the item is focused.</summary>
    Focused,

    /// <summary>Plays once when the game launches; the emulator starts when it ends, or after 2 s.</summary>
    Launch,
}

public static class ModelClips
{
    public static IReadOnlyList<string> Names { get; } = ["idle", "focused", "launch"];

    /// <summary>
    /// The clip an animation's name makes it, or null. Matching ignores case, a trailing Blender <c>.NNN</c> suffix,
    /// and an object name before a <c>|</c> (Blender's <c>Armature|idle</c>), so <c>Idle.001</c> is the idle clip.
    /// </summary>
    public static ModelClip? OfName(string? name)
    {
        if (string.IsNullOrWhiteSpace(name))
        {
            return null;
        }

        var span = name.AsSpan().Trim();
        var bar = span.LastIndexOf('|');
        if (bar >= 0)
        {
            span = span[(bar + 1)..];
        }

        var dot = span.LastIndexOf('.');
        if (dot > 0 && dot == span.Length - 4 && int.TryParse(span[(dot + 1)..], out _))
        {
            span = span[..dot];
        }

        for (var i = 0; i < Names.Count; i++)
        {
            if (span.Equals(Names[i], StringComparison.OrdinalIgnoreCase))
            {
                return (ModelClip)i;
            }
        }

        return null;
    }
}
