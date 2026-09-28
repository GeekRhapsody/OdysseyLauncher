using System.Runtime.InteropServices;
using Launcher.Core.Platform.Windows;

namespace Launcher.Core.Tests.Platform;

public partial class WindowsCommandLineTests
{
    public static TheoryData<string> Arguments =>
    [
        "plain",
        "",
        "with space",
        "tab\there",
        "new\nline",
        "C:\\Program Files\\Emu\\",
        "C:\\trailing\\\\",
        "quote\"inside",
        "\"quoted\"",
        "back\\\"slash quote",
        "back\\\\\"two slashes quote",
        "\\\\server\\share\\Game (USA).cue",
        "Sonic & Knuckles (100%) ^ | < > !",
        "ü 日本 😀",
        "--rom=C:\\ROMs\\Mega Drive\\",
        " ",
        "\\",
        "\"",
    ];

    [Theory]
    [MemberData(nameof(Arguments))]
    public void Windows_splits_the_command_line_back_into_the_same_argument(string argument)
    {
        Assert.SkipUnless(OperatingSystem.IsWindows(), "CommandLineToArgvW is Windows-only.");

        var parsed = Split(WindowsCommandLine.Build(@"C:\Emu Dir\emu.exe", ["first", argument, "last"]));

        Assert.Equal([@"C:\Emu Dir\emu.exe", "first", argument, "last"], parsed);
    }

    [Theory]
    [InlineData("plain", "plain")]
    [InlineData("", "\"\"")]
    [InlineData("a b", "\"a b\"")]
    [InlineData("C:\\Dir\\", "C:\\Dir\\")]
    [InlineData("C:\\My Dir\\", "\"C:\\My Dir\\\\\"")]
    [InlineData("say \"hi\"", "\"say \\\"hi\\\"\"")]
    [InlineData("a\\\"b", "\"a\\\\\\\"b\"")]
    [InlineData("100%&^", "100%&^")]
    public void Arguments_are_quoted_only_when_they_need_it(string argument, string expected)
    {
        Assert.Equal(expected, WindowsCommandLine.Quote(argument));
    }

    [Fact]
    public void The_program_name_is_always_quoted_and_cant_contain_a_quote()
    {
        Assert.Equal("\"C:\\emu.exe\" a", WindowsCommandLine.Build("C:\\emu.exe", ["a"]));
        Assert.Throws<ArgumentException>(() => WindowsCommandLine.Build("C:\\e\"mu.exe", []));
    }

    private static string[] Split(string commandLine)
    {
        var argv = CommandLineToArgvW(commandLine, out var count);
        Assert.NotEqual(0, argv);
        try
        {
            var result = new string[count];
            for (var i = 0; i < count; i++)
            {
                result[i] = Marshal.PtrToStringUni(Marshal.ReadIntPtr(argv, i * IntPtr.Size))!;
            }

            return result;
        }
        finally
        {
            LocalFree(argv);
        }
    }

    [LibraryImport("shell32.dll", StringMarshalling = StringMarshalling.Utf16)]
    private static partial nint CommandLineToArgvW(string commandLine, out int count);

    [LibraryImport("kernel32.dll")]
    private static partial nint LocalFree(nint memory);
}
