using Godot;

namespace Launcher.App.Grid;

/// <summary>
/// The grid's MultiMeshes, all in one format, so the warm-up's instances compile the pipelines the grid's use (A3).
/// </summary>
public static class GridMultiMesh
{
    // The Compatibility renderer (Godot's fallback to OpenGL 3 where Vulkan is missing, as in a VM without a Vulkan
    // driver) multiplies COLOR, which carries the materials (item.gdshader), by an instance colour that reads black
    // when the MultiMesh has none, so there every instance gets white. The Mobile renderer keeps the smaller format.
    private static readonly bool InstanceColours = RenderingServer.GetCurrentRenderingMethod() == "gl_compatibility";

    /// <summary>Main thread: a MultiMesh of the mesh, with that many instances.</summary>
    public static MultiMesh Create(Mesh mesh, int instances)
    {
        var multiMesh = new MultiMesh
        {
            TransformFormat = MultiMesh.TransformFormatEnum.Transform3D,
            UseCustomData = true,
            UseColors = InstanceColours,
            Mesh = mesh,
            InstanceCount = instances,
        };
        for (var i = 0; InstanceColours && i < instances; i++)
        {
            multiMesh.SetInstanceColor(i, Colors.White);
        }

        return multiMesh;
    }
}
