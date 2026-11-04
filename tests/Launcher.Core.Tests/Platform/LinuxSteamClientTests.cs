using Launcher.Core.Platform;
using Launcher.Core.Platform.Linux;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Platform;

/// <summary>Steam's state on Linux, read from a made-up home's <c>registry.vdf</c> and a made-up <c>/proc</c>: these run on every OS.</summary>
public sealed class LinuxSteamClientTests : IDisposable
{
    private const string Native = "home/.steam/registry.vdf";
    private const string Flatpak = "home/.var/app/com.valvesoftware.Steam/.steam/registry.vdf";

    private readonly TempDir _root = new();

    public void Dispose() => _root.Dispose();

    [Fact]
    public void A_game_steam_is_running()
    {
        _root.File(Native, Registry(steamPid: 4242, runningAppId: 0, app: ("400", Installed: 1, Running: 1, Updating: 0)));
        Process(4242);

        Assert.Equal(new SteamAppState(ClientRunning: true, Installed: true, Running: true, Current: false, Updating: false), Client().GetAppState(400));
    }

    [Fact]
    public void Steams_current_game_counts_when_it_writes_one()
    {
        _root.File(Native, Registry(steamPid: 4242, runningAppId: 400, app: ("400", Installed: 1, Running: 0, Updating: 0)));

        Assert.True(Client().GetAppState(400).Current);
        Assert.False(Client().GetAppState(220).Current);
    }

    [Fact]
    public void A_game_steam_is_updating()
    {
        _root.File(Native, Registry(steamPid: 4242, runningAppId: 0, app: ("400", Installed: 0, Running: 0, Updating: 1)));

        Assert.Equal(new SteamAppState(false, false, false, false, Updating: true), Client().GetAppState(400));
    }

    [Fact]
    public void The_client_has_closed_when_its_process_is_gone_or_its_pid_is_0()
    {
        _root.File(Native, Registry(steamPid: 4242, runningAppId: 0, app: ("400", 1, 1, 0)));
        Assert.False(Client().GetAppState(400).ClientRunning);

        _root.File(Native, Registry(steamPid: 0, runningAppId: 0, app: ("400", 1, 1, 0)));
        Process(0);
        Assert.False(Client().GetAppState(400).ClientRunning);
    }

    [Fact]
    public void An_app_steam_doesnt_list_is_neither_installed_nor_running()
    {
        _root.File(Native, Registry(steamPid: 4242, runningAppId: 0, app: ("400", 1, 1, 0)));
        Process(4242);

        Assert.Equal(new SteamAppState(true, false, false, false, false), Client().GetAppState(220));
    }

    [Fact]
    public void Keys_are_matched_ignoring_case_and_comments_and_bare_words_are_read()
    {
        _root.File(Native, """
            // Steam's registry
            "registry" { "hkcu" { "SOFTWARE" { "valve" { "steam" {
                apps { "400" { "Installed" 1 "running" "1" } }
            } } } } }
            """);

        var state = Client().GetAppState(400);

        Assert.True(state.Installed);
        Assert.True(state.Running);
    }

    [Fact]
    public void Without_a_registry_steam_isnt_installed()
    {
        Assert.Null(Client().ClientPath);
        Assert.Equal(default, Client().GetAppState(400));
    }

    [Fact]
    public void Flathubs_steam_is_read_when_its_the_only_one()
    {
        var flatpak = _root.File(Flatpak, Registry(steamPid: 7, runningAppId: 0, app: ("400", 1, 1, 0)));

        Assert.Equal(flatpak, Client().ClientPath);
        Assert.True(Client().GetAppState(400).Running);
    }

    [Fact]
    public void With_both_steams_the_registry_written_last_wins()
    {
        _root.File(Native, Registry(steamPid: 7, runningAppId: 0, app: ("400", 1, 0, 0)), new DateTime(2026, 11, 1, 0, 0, 0, DateTimeKind.Utc));
        var flatpak = _root.File(Flatpak, Registry(steamPid: 7, runningAppId: 0, app: ("400", 1, 1, 0)), new DateTime(2026, 11, 4, 0, 0, 0, DateTimeKind.Utc));

        Assert.Equal(flatpak, Client().ClientPath);
        Assert.True(Client().GetAppState(400).Running);
    }

    [Theory]
    [InlineData("\"Registry\" { \"HKCU\" { \"Software\" { ")]                  // unclosed blocks: a file caught half written
    [InlineData("\"Registry\" { \"HKCU\" { } } }")]                            // a closing brace too many
    [InlineData("\"Registry\" { \"HKCU\" { \"Software\" \"x }")]               // an unclosed quote
    [InlineData("{ \"Registry\" }")]                                           // a block with no key
    [InlineData("\"Registry\"")]                                               // a key with no value
    [InlineData("\"Registry\" }")]
    public void Text_that_isnt_keyvalues_says_nothing_is_running(string text)
    {
        _root.File(Native, text);

        Assert.Equal(default, Client().GetAppState(400));
    }

    [Fact]
    public void Text_nested_deeper_than_steam_could_write_isnt_read()
    {
        _root.File(Native, string.Concat(Enumerable.Repeat("\"k\" { ", 100)) + string.Concat(Enumerable.Repeat("} ", 100)));

        Assert.Equal(default, Client().GetAppState(400));
    }

    [Fact]
    public void A_quoted_value_keeps_its_escaped_quotes_and_braces()
    {
        _root.File(Native, """
            "Registry" { "HKCU" { "Software" { "Valve" { "Steam" {
                "SourceModInstallPath" "/home/x/{odd} \"name\""
                "Apps" { "400" { "Running" "1" } }
            } } } } }
            """);

        Assert.True(Client().GetAppState(400).Running);
    }

    private LinuxSteamClient Client() => new(_root.Combine("home"), _root.Combine("proc"));

    private void Process(int pid) => Directory.CreateDirectory(_root.Combine("proc", pid.ToString(System.Globalization.CultureInfo.InvariantCulture)));

    /// <summary>A registry as Steam writes it on Linux: tab-separated, one key a line.</summary>
    private static string Registry(int steamPid, int runningAppId, (string Id, int Installed, int Running, int Updating) app) =>
        $$"""
        "Registry"
        {
        	"HKLM"
        	{
        		"Software"
        		{
        			"Valve"
        			{
        				"Steam"
        				{
        					"SteamPID"		"{{steamPid}}"
        					"TempAppCmdLine"		""
        				}
        			}
        		}
        	}
        	"HKCU"
        	{
        		"Software"
        		{
        			"Valve"
        			{
        				"Steam"
        				{
        					"language"		"english"
        					"RunningAppID"		"{{runningAppId}}"
        					"Apps"
        					{
        						"228980"
        						{
        							"installed"		"1"
        						}
        						"{{app.Id}}"
        						{
        							"Updating"		"{{app.Updating}}"
        							"installed"		"{{app.Installed}}"
        							"Running"		"{{app.Running}}"
        							"name"		"A game"
        						}
        					}
        				}
        			}
        		}
        	}
        }
        """;
}
