using Launcher.Core.Media;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Media;

/// <summary>The media folder's location (2026-10-04): <c>[paths] media</c>, stored paths that don't name it, and moving it.</summary>
public sealed class MediaFolderTests : IDisposable
{
    private static readonly DateTime Modified = new(2024, 5, 6, 7, 8, 9, DateTimeKind.Utc);

    private readonly TempDir _dir = new();

    private string From => _dir.Combine("data", "media");

    private string To => _dir.Combine("Launcher media");

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    public void Dispose() => _dir.Dispose();

    /// <summary>A file in the old media folder, with a fixed time (a derivative's key has it).</summary>
    private string Old(string relativePath, string content = "x") => _dir.File("data/media/" + relativePath, content, Modified);

    private string[] FilesIn(string folder) =>
        Directory.Exists(folder)
            ? Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories).Select(f => Path.GetRelativePath(folder, f).Replace('\\', '/')).Order(StringComparer.Ordinal).ToArray()
            : [];

    [Fact]
    public void A_stored_path_names_the_media_folder_as_media_wherever_it_is()
    {
        var folder = _dir.Combine("E", "Art");

        Assert.Equal(Path.Combine(folder, "ps2", "cover", "Game.iso.png"), MediaFolder.FullPath(folder, "media/ps2/cover/Game.iso.png"));
        Assert.Equal(Path.Combine(folder, "ps2", "cover", "Game.iso.png"), MediaFolder.FullPath(folder, @"media\ps2\cover\Game.iso.png"));
        Assert.Equal(Path.Combine(folder, "mediaeval", "x.png"), MediaFolder.FullPath(folder, "mediaeval/x.png"));
        Assert.Equal(Path.Combine(_dir.Path, "media"), MediaFolder.Default(_dir.Path));
    }

    [Fact]
    public void Folders_compare_in_full_and_nesting_is_by_whole_names()
    {
        Assert.True(MediaFolder.Same(_dir.Combine("a"), _dir.Combine("a") + Path.DirectorySeparatorChar));
        Assert.True(MediaFolder.Inside(_dir.Combine("a", "b"), _dir.Combine("a")));
        Assert.False(MediaFolder.Inside(_dir.Combine("ab"), _dir.Combine("a")));
        Assert.False(MediaFolder.Inside(_dir.Combine("a"), _dir.Combine("a")));
        if (OperatingSystem.IsWindows())
        {
            Assert.True(MediaFolder.Same(@"C:\Media", @"c:\media\"));
            Assert.True(MediaFolder.Inside(@"D:\Media", @"D:\"));
        }
    }

    [Fact]
    public void The_media_folder_cant_move_into_itself_or_into_a_folder_holding_it()
    {
        Assert.Null(MediaFolderMove.Problem(From, To));
        Assert.Contains("already", MediaFolderMove.Problem(From, From + Path.DirectorySeparatorChar), StringComparison.Ordinal);
        Assert.Contains("inside the media folder", MediaFolderMove.Problem(From, Path.Combine(From, "ps2")), StringComparison.Ordinal);
        Assert.Contains("The media folder is inside", MediaFolderMove.Problem(From, _dir.Combine("data")), StringComparison.Ordinal);
        Assert.Contains("full path", MediaFolderMove.Problem(From, "relative"), StringComparison.Ordinal);
    }

    [Fact]
    public void A_plan_counts_every_file_but_hidden_and_system_ones_and_a_missing_folder_has_none()
    {
        Old("ps2/cover/Game.iso.png", "12345");
        Old("ps2/video/Game.iso.mp4", "123");
        Old("notes.txt", "1");
        var hidden = Old("ps2/cover/Thumbs.db");
        File.SetAttributes(hidden, FileAttributes.Hidden | FileAttributes.System);

        var plan = MediaFolderMove.Plan(From, To, Ct);

        Assert.Equal(["notes.txt", "ps2/cover/Game.iso.png", "ps2/video/Game.iso.mp4"], plan.Files.Select(f => f.RelativePath.Replace('\\', '/')));
        Assert.Equal(9, plan.Bytes);
        Assert.True(plan.SameVolume);
        Assert.Empty(MediaFolderMove.Plan(_dir.Combine("nowhere"), To, Ct).Files);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void Moving_keeps_each_files_path_and_time_and_finishing_empties_the_old_folder(bool sameVolume)
    {
        Old("ps2/cover/Game.iso.png", "cover");
        Old("ps2/model/Sub/Game B.chd.glb", "glTF");
        Old("snes/video/Game.sfc.mp4", "video");
        // A copy (another drive) leaves the originals until the new folder is in use.
        var plan = MediaFolderMove.Plan(From, To, Ct) with { SameVolume = sameVolume };
        var reports = new List<MediaMoveProgress>();

        var move = MediaFolderMove.Move(plan, new Collect(reports), Ct);

        string[] all = ["ps2/cover/Game.iso.png", "ps2/model/Sub/Game B.chd.glb", "snes/video/Game.sfc.mp4"];
        Assert.Equal(all, FilesIn(To));
        Assert.Equal(sameVolume ? [] : all, FilesIn(From));
        Assert.Equal("video", File.ReadAllText(Path.Combine(To, "snes", "video", "Game.sfc.mp4")));
        Assert.All(all, f => Assert.Equal(Modified, File.GetLastWriteTimeUtc(Path.Combine(To, f))));
        Assert.Equal((3, 0), (move.Moved, move.AlreadyThere));
        Assert.Equal(new MediaMoveProgress(3, 3, 14, 14), reports[^1]);

        Assert.Equal(0, move.Finish());

        Assert.Empty(FilesIn(From));
        Assert.Empty(Directory.EnumerateFileSystemEntries(From));
        Assert.True(Directory.Exists(From));
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void Undoing_puts_every_file_back_and_removes_the_folders_the_move_made(bool sameVolume)
    {
        Old("ps2/cover/Game.iso.png", "cover");
        Old("snes/logo/Game.sfc.png", "logo");
        _dir.File("Launcher media/readme.txt", "the user's");
        var plan = MediaFolderMove.Plan(From, To, Ct) with { SameVolume = sameVolume };
        var move = MediaFolderMove.Move(plan, null, Ct);

        Assert.Equal(0, move.Undo());

        Assert.Equal(["ps2/cover/Game.iso.png", "snes/logo/Game.sfc.png"], FilesIn(From));
        Assert.Equal(["readme.txt"], FilesIn(To));
        Assert.Empty(Directory.GetDirectories(To));
    }

    [Fact]
    public void A_file_the_new_folder_has_already_is_kept_there_and_its_original_stays()
    {
        Old("ps2/cover/Game.iso.png", "old");
        Old("ps2/logo/Game.iso.png", "logo");
        _dir.File("Launcher media/ps2/cover/Game.iso.png", "new");

        var move = MediaFolderMove.Move(MediaFolderMove.Plan(From, To, Ct), null, Ct);
        move.Finish();

        Assert.Equal((1, 1), (move.Moved, move.AlreadyThere));
        Assert.Equal("new", File.ReadAllText(Path.Combine(To, "ps2", "cover", "Game.iso.png")));
        Assert.Equal(["ps2/cover/Game.iso.png"], FilesIn(From));
        Assert.Equal("old", File.ReadAllText(Path.Combine(From, "ps2", "cover", "Game.iso.png")));
    }

    [Fact]
    public void A_cancelled_move_puts_back_what_it_had_moved()
    {
        Old("a/cover/1.png");
        Old("a/cover/2.png");
        Old("a/cover/3.png");
        using var cancel = new CancellationTokenSource();
        var plan = MediaFolderMove.Plan(From, To, Ct);

        Assert.Throws<OperationCanceledException>(() => MediaFolderMove.Move(plan, new Cancel(cancel, after: 2), cancel.Token));

        Assert.Equal(["a/cover/1.png", "a/cover/2.png", "a/cover/3.png"], FilesIn(From));
        Assert.Empty(FilesIn(To));
    }

    [Fact]
    public void A_file_that_cant_be_moved_puts_back_the_rest_and_fails()
    {
        Old("a/cover/1.png");
        Old("b/cover/2.png");
        // A file where the move needs a folder: "b" can't be made in the new folder.
        _dir.File("Launcher media/b", "in the way");
        var plan = MediaFolderMove.Plan(From, To, Ct);

        Assert.ThrowsAny<IOException>(() => MediaFolderMove.Move(plan, null, Ct));

        Assert.Equal(["a/cover/1.png", "b/cover/2.png"], FilesIn(From));
        Assert.Equal(["b"], FilesIn(To));
    }

    private sealed class Collect(List<MediaMoveProgress> reports) : IProgress<MediaMoveProgress>
    {
        public void Report(MediaMoveProgress value) => reports.Add(value);
    }

    private sealed class Cancel(CancellationTokenSource source, int after) : IProgress<MediaMoveProgress>
    {
        public void Report(MediaMoveProgress value)
        {
            if (value.Files == after)
            {
                source.Cancel();
            }
        }
    }
}
