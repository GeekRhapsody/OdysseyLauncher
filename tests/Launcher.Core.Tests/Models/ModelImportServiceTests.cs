using System.IO.Compression;
using System.Text;
using Launcher.Core.Config;
using Launcher.Core.Library;
using Launcher.Core.Media;
using Launcher.Core.Models;
using Launcher.Core.Platform;
using Launcher.Core.Tests.TestSupport;
using Microsoft.Data.Sqlite;

namespace Launcher.Core.Tests.Models;

public sealed class ModelImportServiceTests : IAsyncLifetime
{
    private readonly TempDir _dir = new();
    private PlatformPaths _paths = null!;
    private LibraryService _library = null!;
    private ModelImportService _service = null!;

    private static CancellationToken Ct => TestContext.Current.CancellationToken;

    private static readonly GameKey Game = new("ps2", "sub/crimson odyssey (europe).iso");

    public async ValueTask InitializeAsync()
    {
        _paths = PlatformPaths.InOneFolder(_dir.Combine("user"), _dir.Path);
        var config = new ConfigLoader().Load(new ConfigSources
        {
            HomeDir = _dir.Path,
            ConfigDir = _paths.ConfigDir,
            FileExists = null,
            Settings = new ConfigFile("settings.toml", $"[paths]\nrom_root = '{_dir.Combine("ROMs")}'\n"),
        }).Config;
        _library = await LibraryService.OpenAsync(config, _paths.DataDir, null, Ct);
        _library.IndexMedia = true;
        _dir.File("ROMs/ps2/Sub/Crimson Odyssey (Europe).iso", "rom");
        _dir.File("ROMs/ps2/Other.iso", "rom");
        await _library.RescanAsync("ps2", null, Ct);
        _service = new ModelImportService(_library, _paths, null);
    }

    public ValueTask DisposeAsync()
    {
        _library.Dispose();
        SqliteConnection.ClearAllPools();
        _dir.Dispose();
        return ValueTask.CompletedTask;
    }

    private string Source(string name, byte[] content) => ModelFixtures.Write(_dir, "downloads/" + name, content);

    private async Task<IReadOnlyList<GameMediaRow>> Models() => await _library.GetGameMediaAsync("ps2", [MediaKinds.Model], Ct);

    [Fact]
    public async Task A_glb_goes_into_the_games_model_slot_and_is_indexed_at_once()
    {
        var changes = new List<IReadOnlyList<GameKey>?>();
        _library.MediaChanged += (_, e) => changes.Add(e.Games);

        var result = await _service.ImportGameModelAsync(Game, Source("tv.glb", ModelFixtures.Model(800, ["screenshot", "body"])), Ct);

        Assert.Equal(ModelImportStatus.Imported, result.Status);
        Assert.Equal("media/ps2/model/Sub/Crimson Odyssey (Europe).iso.glb", result.ModelPath);
        Assert.False(result.Converted);
        Assert.True(File.Exists(Path.Combine(_paths.DataDir, "media", "ps2", "model", "Sub", "Crimson Odyssey (Europe).iso.glb")));
        Assert.Equal(result.ModelPath, Assert.Single(await Models()).Media.Path);
        Assert.Equal([Game], Assert.Single(changes)!);

        // The cache already has it, so the app doesn't process it again.
        var cached = new ModelCache(_paths.CacheDir, null, null).Get(Path.Combine(_paths.DataDir, result.ModelPath!), ModelKind.PerGame);
        Assert.True(cached.FromCache);
        Assert.Contains(ModelLog.ReadRecent(_paths.DataDir), l => l.Contains("Imported as media/ps2/model/", StringComparison.Ordinal));
        Assert.Equal(result.ModelPath, (await _service.GetGameModelAsync(Game, Ct))!.Value.Path);
    }

    [Fact]
    public async Task An_obj_zip_is_converted_first()
    {
        using var memory = new MemoryStream();
        using (var zip = new ZipArchive(memory, ZipArchiveMode.Create, leaveOpen: true))
        {
            using var obj = zip.CreateEntry("tv.obj").Open();
            obj.Write(Encoding.UTF8.GetBytes("v -1 0 0\nv 1 0 0\nv 1 1.5 0\nv -1 1.5 0\nusemtl screenshot\nf 1 2 3 4\n"));
        }

        var result = await _service.ImportGameModelAsync(Game, Source("tv.zip", memory.ToArray()), Ct);

        Assert.Equal(ModelImportStatus.Imported, result.Status);
        Assert.True(result.Converted);
        Assert.Equal(["screenshot"], result.Report!.Slots);
        Assert.Empty(result.Messages);
    }

    [Fact]
    public async Task A_model_more_than_twice_over_budget_is_rejected_and_nothing_changes()
    {
        var result = await _service.ImportGameModelAsync(Game, Source("huge.glb", ModelFixtures.Model(12_000)), Ct);

        Assert.Equal(ModelImportStatus.Rejected, result.Status);
        Assert.False(result.Report!.Accepted);
        Assert.Empty(await Models());
        Assert.False(Directory.Exists(Path.Combine(_paths.DataDir, "media")));
        Assert.Contains(ModelLog.ReadRecent(_paths.DataDir), l => l.Contains("error: huge.glb for ps2/Sub/Crimson Odyssey (Europe).iso: has 12,000 triangles", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Other_files_and_games_not_in_the_library_are_refused()
    {
        var text = await _service.ImportGameModelAsync(Game, Source("model.fbx", "FBX"u8.ToArray()), Ct);
        var broken = await _service.ImportGameModelAsync(Game, Source("broken.glb", "glTFnope"u8.ToArray()), Ct);
        var missing = await _service.ImportGameModelAsync(new GameKey("ps2", "gone.iso"), Source("tv.glb", ModelFixtures.Model(10)), Ct);

        Assert.Equal(ModelImportStatus.Unsupported, text.Status);
        Assert.Contains("isn't a model the launcher can import", Assert.Single(text.Messages), StringComparison.Ordinal);
        Assert.Equal(ModelImportStatus.Rejected, broken.Status);
        Assert.Equal(ModelImportStatus.NotInLibrary, missing.Status);
        Assert.Empty(await Models());
    }

    [Fact]
    public async Task Removing_a_games_model_puts_its_template_back()
    {
        var imported = await _service.ImportGameModelAsync(Game, Source("tv.glb", ModelFixtures.Model(100)), Ct);

        var removed = await _service.RemoveGameModelAsync(Game, Ct);

        Assert.Equal(ModelRemoveStatus.Removed, removed.Status);
        Assert.False(File.Exists(Path.Combine(_paths.DataDir, imported.ModelPath!)));
        Assert.Empty(await Models());
        Assert.Equal(ModelRemoveStatus.None, (await _service.RemoveGameModelAsync(Game, Ct)).Status);
        Assert.Null(await _service.GetGameModelAsync(Game, Ct));
    }

    [Fact]
    public async Task A_model_shared_by_name_isnt_removed_for_one_game()
    {
        ModelFixtures.Write(_dir, "user/media/ps2/model/Other.glb", ModelFixtures.Model(100));
        await _library.RefreshMediaAsync("ps2", Ct);

        var result = await _service.RemoveGameModelAsync(new GameKey("ps2", "other.iso"), Ct);

        Assert.Equal((ModelRemoveStatus.Shared, "media/ps2/model/Other.glb"), (result.Status, result.SharedPath));
        Assert.Single(await Models());
    }

    [Fact]
    public async Task A_systems_card_and_game_template_go_where_the_theme_resolver_looks()
    {
        var card = await _service.ImportSystemModelAsync("ps2", SystemModelSlot.Card, Source("console.glb", ModelFixtures.Model(12_000, ["label", "body"])), Ct);
        var template = await _service.ImportSystemModelAsync("ps2", SystemModelSlot.GameTemplate, Source("case.glb", ModelFixtures.Model(900, ["cover", "case"])), Ct);

        Assert.Equal((ModelImportStatus.Imported, "models/systems/ps2.glb"), (card.Status, card.ModelPath));
        Assert.Equal((ModelImportStatus.Imported, "models/templates/ps2.glb"), (template.Status, template.ModelPath));
        var found = Launcher.Core.Theming.UserModels.Find(_paths.ConfigDir);
        Assert.Contains("ps2", found.Systems);
        Assert.Contains("ps2", found.Templates);
        Assert.Equal(12_000, (await _service.GetSystemModelAsync("ps2", SystemModelSlot.Card, Ct))!.Triangles);
        Assert.Equal(["cover"], (await _service.GetSystemModelAsync("ps2", SystemModelSlot.GameTemplate, Ct))!.Slots);
        Assert.Empty(await Models());                                                  // not a per-game model
    }

    [Fact]
    public async Task A_system_model_is_held_to_the_budget_of_its_kind()
    {
        // 5,000 triangles is in a per-game model's budget but more than twice a game template's.
        var template = await _service.ImportSystemModelAsync("ps2", SystemModelSlot.GameTemplate, Source("big.glb", ModelFixtures.Model(5_000)), Ct);
        var unknown = await _service.ImportSystemModelAsync("nope", SystemModelSlot.Card, Source("card.glb", ModelFixtures.Model(10)), Ct);

        Assert.Equal(ModelImportStatus.Rejected, template.Status);
        Assert.Equal(ModelImportStatus.NotInLibrary, unknown.Status);
        Assert.False(Directory.Exists(Path.Combine(_paths.ConfigDir, "models")));
    }

    [Fact]
    public async Task Removing_a_system_model_puts_the_themes_back()
    {
        await _service.ImportSystemModelAsync("ps2", SystemModelSlot.Card, Source("card.glb", ModelFixtures.Model(100)), Ct);

        Assert.True(await _service.RemoveSystemModelAsync("ps2", SystemModelSlot.Card, Ct));
        Assert.False(await _service.RemoveSystemModelAsync("ps2", SystemModelSlot.Card, Ct));
        Assert.Empty(Launcher.Core.Theming.UserModels.Find(_paths.ConfigDir).Systems);
        Assert.Null(await _service.GetSystemModelAsync("ps2", SystemModelSlot.Card, Ct));
    }
}
