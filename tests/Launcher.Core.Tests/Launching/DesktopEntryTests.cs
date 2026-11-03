using Launcher.Core.Launching;

namespace Launcher.Core.Tests.Launching;

public class DesktopEntryTests
{
    [Fact]
    public void A_Steam_shortcut_runs_steam_with_its_game()
    {
        var command = DesktopEntry.Read("""
            [Desktop Entry]
            Name=Celeste
            Comment=Play this game on Steam
            Exec=steam steam://rungameid/504230
            Icon=steam_icon_504230
            Terminal=false
            Type=Application
            Categories=Game;
            """);

        Assert.Equal("steam", command!.Program);
        Assert.Equal(["steam://rungameid/504230"], command.Arguments);
        Assert.Null(command.WorkingDirectory);
    }

    [Fact]
    public void Quotes_escapes_field_codes_and_the_Path_key_are_read_as_the_specification_says()
    {
        var command = DesktopEntry.Read(
            "[Desktop Entry]\n" +
            "Exec[fr]=wrong\n" +
            "Exec=\"/opt/My Games/run\" --title \"Say \\\\\"hi\\\\\"\" 100%% %U --flag\\sone\n" +
            "Path=/opt/My Games\n" +
            "[Desktop Action Other]\n" +
            "Exec=also-wrong\n");

        Assert.Equal("/opt/My Games/run", command!.Program);
        Assert.Equal(["--title", "Say \"hi\"", "100%", "--flag", "one"], command.Arguments);
        Assert.Equal("/opt/My Games", command.WorkingDirectory);
    }

    [Theory]
    [InlineData("[Desktop Entry]\nName=No command\n")]
    [InlineData("[Desktop Entry]\nExec=\"unclosed\n")]
    [InlineData("[Other]\nExec=elsewhere\n")]
    [InlineData("[Desktop Entry]\nExec=%f\n")]
    public void A_shortcut_with_no_usable_command_has_none(string text) => Assert.Null(DesktopEntry.Read(text));
}
