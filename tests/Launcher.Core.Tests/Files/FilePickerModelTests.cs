using Launcher.Core.Files;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Files;

/// <summary>M7: what the folder and file pickers list, and how they read what the user types.</summary>
public sealed class FilePickerModelTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    [Fact]
    public void Folders_come_first_then_files_in_natural_order()
    {
        _dir.File("list/Disc 10.png");
        _dir.File("list/disc 2.png");
        _dir.File("list/Disc 1.PNG");
        _dir.File("list/b.txt");
        _dir.File("list/zeta/x.png");
        _dir.File("list/Alpha/x.png");
        _dir.File("list/Game 9/x.png");
        _dir.File("list/Game 10/x.png");

        var result = DirectoryListing.List(_dir.Combine("list"), FileFilter.Images, TestContext.Current.CancellationToken);

        Assert.Null(result.Problem);
        Assert.Equal(["Alpha", "Game 9", "Game 10", "zeta", "Disc 1.PNG", "disc 2.png", "Disc 10.png"], result.Entries.Select(e => e.Name));
        Assert.Equal([true, true, true, true, false, false, false], result.Entries.Select(e => e.IsFolder));
        Assert.Equal(1, result.FilteredOut);
    }

    [Fact]
    public void The_folder_picker_lists_folders_only()
    {
        _dir.File("list/a.bin");
        _dir.File("list/sub/a.bin");

        var result = DirectoryListing.List(_dir.Combine("list"), null, TestContext.Current.CancellationToken);

        Assert.Equal(["sub"], result.Entries.Select(e => e.Name));
        Assert.Equal(1, result.FilteredOut);
    }

    [Fact]
    public void Hidden_entries_are_skipped()
    {
        var hidden = _dir.File("list/hidden.png");
        File.SetAttributes(hidden, FileAttributes.Hidden);
        _dir.File("list/shown.png");

        var result = DirectoryListing.List(_dir.Combine("list"), FileFilter.Images, TestContext.Current.CancellationToken);

        Assert.Equal(["shown.png"], result.Entries.Select(e => e.Name));
    }

    [Fact]
    public void A_folder_with_thousands_of_files_is_listed_whole_with_its_progress_counted()
    {
        var folder = _dir.Combine("big");
        Directory.CreateDirectory(folder);
        for (var i = 0; i < 3000; i++)
        {
            File.WriteAllBytes(Path.Combine(folder, $"Game {i}.glb"), []);
        }

        var progress = new ListingProgress();
        var result = DirectoryListing.List(folder, FileFilter.Models, TestContext.Current.CancellationToken, progress);

        Assert.Equal(3000, result.Entries.Count);
        Assert.Equal(3000, progress.Value);
        Assert.Equal("Game 0.glb", result.Entries[0].Name);
        Assert.Equal("Game 2999.glb", result.Entries[^1].Name);
    }

    [Fact]
    public void A_folder_that_cant_be_listed_says_why_instead_of_throwing()
    {
        var missing = DirectoryListing.List(_dir.Combine("gone"), null, TestContext.Current.CancellationToken);
        Assert.True(missing.Failed);
        Assert.Contains("doesn't exist any more", missing.Problem, StringComparison.Ordinal);
        Assert.Empty(missing.Entries);

        // As Windows reports them: ERROR_BAD_NETPATH (a share that's gone), ERROR_NOT_READY (no disc), ERROR_ACCESS_DENIED.
        Assert.Contains("can't be reached", DirectoryListing.Explain(@"\\nas\roms", new IOException("x", unchecked((int)0x80070035))), StringComparison.Ordinal);
        Assert.Contains("Is there a disc", DirectoryListing.Explain(@"E:\", new IOException("x", unchecked((int)0x80070015))), StringComparison.Ordinal);
        Assert.Contains("permission", DirectoryListing.Explain(@"C:\x", new UnauthorizedAccessException()), StringComparison.Ordinal);
    }

    [Fact]
    public void Letter_jumps_go_group_by_group()
    {
        string[] names = ["3D Blast", "Alex Kidd", "Altered Beast", "Bonanza", "Columns", "Columns III", "École"];
        string At(int i) => names[i];

        Assert.Equal(1, LetterJump.Next(names.Length, At, 0));
        Assert.Equal(3, LetterJump.Next(names.Length, At, 1));
        Assert.Equal(6, LetterJump.Next(names.Length, At, 5));
        Assert.Equal(6, LetterJump.Next(names.Length, At, 6));
        Assert.Equal(4, LetterJump.Previous(names.Length, At, 5));
        Assert.Equal(3, LetterJump.Previous(names.Length, At, 4));
        Assert.Equal(1, LetterJump.Previous(names.Length, At, 3));
        Assert.Equal(0, LetterJump.Previous(names.Length, At, 0));
        Assert.Equal('E', LetterJump.GroupOf("École"));
        Assert.Equal('F', LetterJump.GroupOf("_file.png"));
        Assert.Equal('#', LetterJump.GroupOf("+plus"));
    }

    [Fact]
    public void Typed_paths_are_read_the_way_people_type_them()
    {
        var home = _dir.Path;
        var here = _dir.Combine("here");
        Assert.Equal(Path.GetFullPath(Path.Combine(here, "sub")), PathInput.Resolve("sub", here, home).Path);
        Assert.Equal(Path.GetFullPath(_dir.Path), PathInput.Resolve("..", here, home).Path);
        Assert.Equal(Path.GetFullPath(Path.Combine(home, "ROMs")), PathInput.Resolve($"~{Path.DirectorySeparatorChar}ROMs", null, home).Path);
        Assert.NotNull(PathInput.Resolve("   ", here, home).Problem);
        Assert.NotNull(PathInput.Resolve("relative", null, home).Problem);

        if (OperatingSystem.IsWindows())
        {
            Assert.Equal(@"D:\ROMs\Mega Drive", PathInput.Resolve("\"D:/ROMs/Mega Drive\"", null, home).Path);
            Assert.Equal(@"E:\", PathInput.Resolve("E:", null, home).Path);
            Assert.Equal(@"\\nas\roms\md", PathInput.Resolve("//nas/roms/md", null, home).Path);
            Assert.Equal(@"\\nas\roms", PathInput.Resolve(@"\\nas\roms\", null, home).Path?.TrimEnd('\\'));
            Assert.Contains("share's name", PathInput.Resolve(@"\\nas", null, home).Problem, StringComparison.Ordinal);
            Assert.Contains("isn't a valid path", PathInput.Resolve(@"D:\games?", null, home).Problem, StringComparison.Ordinal);
            Assert.Contains("isn't a valid path", PathInput.Resolve(@"D:\a:b", null, home).Problem, StringComparison.Ordinal);
        }
    }

    [Fact]
    public void Going_up_stops_at_a_drive_or_share_root()
    {
        if (OperatingSystem.IsWindows())
        {
            Assert.Equal(@"D:\", PathInput.Parent(@"D:\ROMs"));
            Assert.Equal(@"D:\ROMs", PathInput.Parent(@"D:\ROMs\md\"));
            Assert.Null(PathInput.Parent(@"D:\"));
            Assert.Equal(@"\\nas\roms", PathInput.Parent(@"\\nas\roms\md"));
            Assert.Null(PathInput.Parent(@"\\nas\roms"));
            Assert.Null(PathInput.Parent(@"\\nas\roms\"));
            Assert.Equal("md", PathInput.NameOf(@"\\nas\roms\md"));
            Assert.Equal(@"\\nas\roms", PathInput.NameOf(@"\\nas\roms"));
            Assert.Equal(@"C:\", PathInput.NameOf(@"C:\"));
        }
        else
        {
            Assert.Equal("/home", PathInput.Parent("/home/user"));
            Assert.Null(PathInput.Parent("/"));
        }
    }

    [Fact]
    public void Each_use_remembers_its_last_folder_across_sessions()
    {
        var history = PickerHistory.Load(_dir.Path);
        Assert.Null(history.Get(PickerUses.Emulator));
        history.Set(PickerUses.Emulator, _dir.Combine("Emulators"));
        history.Set(PickerUses.RomRoot, _dir.Combine("ROMs"));
        history.Save();

        var next = PickerHistory.Load(_dir.Path);
        Assert.Equal(_dir.Combine("Emulators"), next.Get(PickerUses.Emulator));
        Assert.Equal(_dir.Combine("ROMs"), next.Get(PickerUses.RomRoot));

        File.WriteAllText(Path.Combine(_dir.Path, PickerHistory.FileName), "{ not json");
        Assert.Null(PickerHistory.Load(_dir.Path).Get(PickerUses.Emulator));
    }

    [Fact]
    public void Drives_and_quick_access_folders_are_listed_without_touching_the_drives()
    {
        var locations = PlatformServices.CreateFileLocations(_dir.Path);

        var quick = locations.QuickAccess();
        Assert.Equal(_dir.Path, quick[0].Path);

        var drives = locations.Drives();
        Assert.NotEmpty(drives);
        if (OperatingSystem.IsWindows())
        {
            var system = Path.GetPathRoot(Environment.SystemDirectory)!;
            var drive = Assert.Single(drives, d => string.Equals(d.Path, system, StringComparison.OrdinalIgnoreCase));
            Assert.Equal(LocationKind.Fixed, drive.Kind);
            Assert.True(drive.Available);
        }
    }
}
