using System.Reflection;

namespace Launcher.Core;

/// <summary>Build information for Launcher.Core.</summary>
public static class CoreInfo
{
    /// <summary>
    /// Informational version, e.g. <c>0.1.0+&lt;commit sha&gt;</c> once the repository has commits.
    /// </summary>
    public static string Version { get; } = InformationalVersionOf(typeof(CoreInfo).Assembly);

    /// <summary>Returns an assembly's informational version, falling back to its assembly version.</summary>
    public static string InformationalVersionOf(Assembly assembly)
    {
        ArgumentNullException.ThrowIfNull(assembly);
        return assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion
            ?? assembly.GetName().Version?.ToString()
            ?? "unknown";
    }
}
