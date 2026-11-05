using Godot;
using Launcher.App.Models;
using Launcher.Core.Library;
using Launcher.Core.Theming;

namespace Launcher.App.Grid;

/// <summary>What a grid cell shows. Filled by an <see cref="IGridSource"/>; no strings are built for it.</summary>
public struct CellInfo
{
    public string Title;

    /// <summary>Index into the grid's templates.</summary>
    public int Template;

    /// <summary>
    /// The item's own model (a per-game model, A7 level 1), once it has loaded and been given to
    /// <see cref="ItemGrid.PrepareModel"/>; null to show <see cref="Template"/>. It's drawn on its own node.
    /// </summary>
    public ItemTemplate? Model;

    /// <summary>The colour of a box with no art, or of a system card.</summary>
    public Color Plain;
}

/// <summary>The items a grid shows, in order.</summary>
public interface IGridSource
{
    int Count { get; }

    /// <summary>Main thread, while binding: must not allocate.</summary>
    void Describe(int index, out CellInfo cell);

    /// <summary>
    /// Main thread, while binding: the item's media of the kind in slot number <paramref name="slot"/>
    /// (<see cref="MediaSlots"/>), if it has one. Must not allocate.
    /// </summary>
    bool TryGetMedia(int index, int slot, out MediaRef media);

    /// <summary>
    /// Main thread: the item's video (the <c>video</c> media kind), if it has one and the list was loaded with videos
    /// (a template plays them: A6 Game videos). Must not allocate.
    /// </summary>
    bool TryGetVideo(int index, out MediaRef media);

    /// <summary>Whether any item uses the template (so its MultiMesh is drawn at all).</summary>
    bool UsesTemplate(int template);
}
