namespace Launcher.Core.Tests;

public class ArchitectureTests
{
    [Fact]
    public void Core_does_not_reference_Godot()
    {
        var references = typeof(CoreInfo).Assembly.GetReferencedAssemblies();

        Assert.DoesNotContain(
            references,
            reference => reference.Name?.StartsWith("Godot", StringComparison.OrdinalIgnoreCase) == true);
    }

    [Fact]
    public void Core_reports_the_repository_version()
    {
        Assert.StartsWith("0.9.0", CoreInfo.Version, StringComparison.Ordinal);
    }
}
