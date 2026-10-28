using Launcher.Core.Launching;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Launching;

public sealed class Vita3KGamesTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    private string Exe => _dir.Combine("Emulators", "Vita3K", "Vita3K.exe");

    private string Roaming => _dir.Combine("Roaming");

    [Fact]
    public void Storage_is_the_portable_folder_then_config_ymls_pref_path_then_the_users_application_data()
    {
        Assert.Equal(Path.Combine(Roaming, "Vita3K", "Vita3K"), Vita3KGames.StorageFolder(Exe, Roaming));

        var elsewhere = _dir.Combine("Vita Storage");
        _dir.File("Emulators/Vita3K/config.yml", $"backend-renderer: Vulkan\npref-path: {elsewhere}\nshow-gui: true\n");
        Assert.Equal(elsewhere, Vita3KGames.StorageFolder(Exe, Roaming));

        // A relative one is the executable's folder's, which is where Vita3K starts.
        _dir.File("Emulators/Vita3K/config.yml", "pref-path: ../saves/psvita\n");
        Assert.Equal(_dir.Combine("Emulators", "saves", "psvita"), Vita3KGames.StorageFolder(Exe, Roaming));

        _dir.File("Emulators/Vita3K/config.yml", "pref-path: \"\"\n");
        Assert.Equal(Path.Combine(Roaming, "Vita3K", "Vita3K"), Vita3KGames.StorageFolder(Exe, Roaming));

        // Portable mode wins over the config's path, as it does in Vita3K.
        _dir.File("Emulators/Vita3K/config.yml", $"pref-path: {elsewhere}\n");
        Directory.CreateDirectory(_dir.Combine("Emulators", "Vita3K", "portable"));
        Assert.Equal(_dir.Combine("Emulators", "Vita3K", "portable", "fs"), Vita3KGames.StorageFolder(Exe, Roaming));
    }

    [Theory]
    [InlineData("pref-path: C:\\Users\\Me\\Vita\\\n", "C:\\Users\\Me\\Vita\\")]
    [InlineData("a: 1\r\npref-path: D:/Vita3K\r\nb: 2\r\n", "D:/Vita3K")]
    [InlineData("pref-path: 'C:\\It''s Vita'", "C:\\It's Vita")]
    [InlineData("pref-path: \"C:\\\\Quoted \\\"Vita\\\"\"", "C:\\Quoted \"Vita\"")]
    [InlineData("pref-path: \"\"", null)]
    [InlineData("pref-path:", null)]
    [InlineData("pref-path: ~", null)]
    [InlineData("  pref-path: C:/Nested", null)]
    [InlineData("backend-renderer: Vulkan", null)]
    public void Pref_path_is_read_from_its_top_level_line(string yaml, string? expected)
    {
        Assert.Equal(expected, Vita3KGames.PrefPath(yaml));
    }

    [Fact]
    public void A_game_is_installed_when_its_title_ids_folder_is_in_ux0_app()
    {
        var storage = _dir.Combine("fs");
        Directory.CreateDirectory(Path.Combine(storage, "ux0", "app", "PCSF00024"));

        Assert.True(Vita3KGames.IsInstalled(storage, "PCSF00024"));
        Assert.False(Vita3KGames.IsInstalled(storage, "PCSB00842"));
    }

    [Fact]
    public void Vita3K_can_install_packages_and_folders_but_not_ES_DEs_psvita_files()
    {
        Assert.True(Vita3KGames.CanInstall(_dir.File("Gravity Rush.vpk")));
        Assert.True(Vita3KGames.CanInstall(_dir.File("Gravity Rush.ZIP")));
        Directory.CreateDirectory(_dir.Combine("Dump.psvita"));
        Assert.True(Vita3KGames.CanInstall(_dir.Combine("Dump.psvita")));
        Assert.False(Vita3KGames.CanInstall(_dir.File("Gravity Rush.psvita", "PCSF00024")));
    }
}
