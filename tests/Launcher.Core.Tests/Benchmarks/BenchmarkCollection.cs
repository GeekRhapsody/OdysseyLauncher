namespace Launcher.Core.Tests.Benchmarks;

/// <summary>Benchmarks run on their own, after the parallel tests, so other tests don't skew their times.</summary>
[CollectionDefinition(nameof(BenchmarkCollection), DisableParallelization = true)]
public sealed class BenchmarkCollection;
