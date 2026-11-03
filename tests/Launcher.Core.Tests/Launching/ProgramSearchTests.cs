using Launcher.Core.Config;
using Launcher.Core.Launching;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Launching;

public class ProgramSearchTests
{
    [Fact]
    public void The_first_place_that_has_the_file_wins()
    {
        using var dir = new TempDir();
        var second = dir.File("b/emu");
        var third = dir.File("c/emu");

        var found = ProgramSearch.System.Find([dir.Combine("a", "emu"), second, third]);

        Assert.Equal(second, found);
        Assert.Null(ProgramSearch.System.Find([dir.Combine("a", "emu")]));
    }

    [Fact]
    public void A_bare_name_is_looked_for_in_the_PATHs_rooted_folders_in_order()
    {
        using var dir = new TempDir();
        var bin = dir.Combine("bin");
        var program = dir.File("bin/emu");
        dir.File("first/emu");
        var path = string.Join(Path.PathSeparator, ["relative", dir.Combine("empty"), bin, dir.Combine("first")]);

        Assert.Equal(program, new ProgramSearch(File.Exists, path).Find(["emu"]));
        Assert.Null(new ProgramSearch(File.Exists, null).Find(["emu"]));
        Assert.Null(new ProgramSearch(File.Exists, "relative-only").Find(["emu"]));
    }

    [Fact]
    public void A_wildcard_in_a_file_name_finds_the_most_recently_written_match()
    {
        using var dir = new TempDir();
        dir.File("Apps/Emu-1.0.AppImage", modifiedUtc: new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        var newest = dir.File("Apps/Emu-0.9.AppImage", modifiedUtc: new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        dir.File("Apps/Other-2.0.AppImage", modifiedUtc: new DateTime(2027, 1, 1, 0, 0, 0, DateTimeKind.Utc));

        Assert.Equal(newest, ProgramSearch.System.Find([dir.Combine("Apps", "Emu-*.AppImage")]));
        Assert.Null(ProgramSearch.System.Find([dir.Combine("Missing", "Emu-*.AppImage")]));
        Assert.Null(ProgramSearch.System.Find([dir.Combine("A*", "Emu-1.0.AppImage")]));
    }

    [Fact]
    public void Resolve_gives_the_found_program_and_core_and_says_what_wasnt_found()
    {
        using var dir = new TempDir();
        var program = dir.File("b/emu");
        var core = dir.File("cores/core.so");
        var emulator = new EmulatorConfig(
            "x", "X", dir.Combine("a", "emu"), ["{rom}"], "{emulator_dir}", dir.Combine("missing", "core.so"),
            Programs: [dir.Combine("a", "emu"), program], Cores: [dir.Combine("missing", "core.so"), core]);

        var (found, programFound, coreFound) = ProgramSearch.System.Resolve(emulator);

        Assert.True(programFound);
        Assert.True(coreFound);
        Assert.Equal(program, found.Executable);
        Assert.Equal(core, found.Core);

        var (missing, noProgram, noCore) = ProgramSearch.System.Resolve(emulator with { Programs = null, Cores = null });
        Assert.False(noProgram);
        Assert.False(noCore);
        Assert.Equal(dir.Combine("a", "emu"), missing.Executable);
    }
}
