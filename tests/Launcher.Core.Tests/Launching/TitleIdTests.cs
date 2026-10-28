using System.Buffers.Binary;
using System.IO.Compression;
using System.Text;
using Launcher.Core.Launching;
using Launcher.Core.Tests.TestSupport;

namespace Launcher.Core.Tests.Launching;

public sealed class TitleIdTests : IDisposable
{
    private readonly TempDir _dir = new();

    public void Dispose() => _dir.Dispose();

    /// <summary>A <c>param.sfo</c> holding <paramref name="entries"/>, each a UTF-8 string value, as Sony lays one out.</summary>
    internal static byte[] Sfo(params (string Key, string Value)[] entries)
    {
        var keys = new MemoryStream();
        var values = new MemoryStream();
        var index = new byte[entries.Length * 16];
        for (var i = 0; i < entries.Length; i++)
        {
            var value = Encoding.UTF8.GetBytes(entries[i].Value + "\0");
            var kept = (value.Length + 3) / 4 * 4;
            var entry = index.AsSpan(i * 16, 16);
            BinaryPrimitives.WriteUInt16LittleEndian(entry, (ushort)keys.Length);
            BinaryPrimitives.WriteUInt16LittleEndian(entry[2..], 0x0204);
            BinaryPrimitives.WriteUInt32LittleEndian(entry[4..], (uint)value.Length);
            BinaryPrimitives.WriteUInt32LittleEndian(entry[8..], (uint)kept);
            BinaryPrimitives.WriteUInt32LittleEndian(entry[12..], (uint)values.Length);
            keys.Write(Encoding.ASCII.GetBytes(entries[i].Key + "\0"));
            values.Write(value);
            values.Write(new byte[kept - value.Length]);
        }

        while (keys.Length % 4 != 0)
        {
            keys.WriteByte(0);
        }

        var header = new byte[20];
        "\0PSF"u8.CopyTo(header);
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(4), 0x0101);
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(8), (uint)(20 + index.Length));
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(12), (uint)(20 + index.Length + keys.Length));
        BinaryPrimitives.WriteUInt32LittleEndian(header.AsSpan(16), (uint)entries.Length);
        return [.. header, .. index, .. keys.ToArray(), .. values.ToArray()];
    }

    private static readonly byte[] GravityRush = Sfo(("APP_VER", "01.00"), ("CATEGORY", "gd"), ("TITLE", "GRAVITY RUSH"), ("TITLE_ID", "PCSF00024"));

    [Theory]
    [InlineData("Gravity Rush (Europe) [PCSF00024].vpk", "PCSF00024")]
    [InlineData("Demon's Tier+ (USA) (v1.01) [vita3k] [PCSE01467].vpk", "PCSE01467")]
    [InlineData("Two [PCSA00001] [pcsb00002].zip", "PCSB00002")]
    [InlineData("VitaShell [VITASHELL].vpk", "VITASHELL")]
    [InlineData("Gravity Rush.psvita", null)]
    [InlineData("Gravity Rush [English1].vpk", null)]
    [InlineData("Gravity Rush [PCSF000245].vpk", null)]
    public void The_name_gives_the_last_nine_letter_or_digit_tag_in_square_brackets(string name, string? expected)
    {
        Assert.Equal(expected, TitleId.FromName(Path.Combine("S:", "Vita", name)));
    }

    [Fact]
    public void A_folders_name_counts_with_or_without_a_trailing_separator()
    {
        Assert.Equal("PCSF00024", TitleId.FromName(Path.Combine("S:", "Vita", "Gravity Rush [PCSF00024].psvita") + Path.DirectorySeparatorChar));
    }

    [Fact]
    public void A_small_file_is_read_as_text_as_ES_DEs_psvita_files_hold_the_id()
    {
        Assert.Equal("PCSE00232", TitleId.Read(_dir.File("A-men.psvita", "﻿PCSE00232\r\n")));
        Assert.Equal("PCSE00232", TitleId.Read(_dir.File("A-men 2.psvita", "-r pcse00232")));
        Assert.Null(TitleId.Read(_dir.File("Empty.psvita")));
        Assert.Null(TitleId.Read(_dir.File("Words.psvita", "not an id here")));

        // The name wins over the text.
        Assert.Equal("PCSB00842", TitleId.Read(_dir.File("Infected Wars [PCSB00842].psvita", "PCSE00232")));
    }

    [Fact]
    public void A_folder_gives_its_param_sfos_id()
    {
        var folder = _dir.Combine("Gravity Rush.psvita");
        Directory.CreateDirectory(Path.Combine(folder, "sce_sys"));
        File.WriteAllBytes(Path.Combine(folder, "sce_sys", "param.sfo"), GravityRush);

        Assert.Equal("PCSF00024", TitleId.Read(folder));
        Assert.Null(TitleId.Read(_dir.Combine("No Such Game.psvita")));
        Directory.CreateDirectory(_dir.Combine("Bare.psvita"));
        Assert.Null(TitleId.Read(_dir.Combine("Bare.psvita")));
    }

    [Fact]
    public void A_package_gives_the_id_of_the_param_sfo_nearest_its_root()
    {
        var package = _dir.Combine("Gravity Rush.vpk");
        using (var zip = ZipFile.Open(package, ZipArchiveMode.Create))
        {
            Write(zip, "patch/PCSF00999/sce_sys/param.sfo", Sfo(("TITLE_ID", "PCSF00999")));
            Write(zip, "sce_sys/param.sfo", GravityRush);

            // Bigger than a text file, as any real package is.
            var filler = new byte[TitleId.MaxTextFileSize * 2];
            new Random(7).NextBytes(filler);
            Write(zip, "eboot.bin", filler);
        }

        Assert.Equal("PCSF00024", TitleId.Read(package));

        // A large file that isn't a zip has no id, and doesn't throw.
        var notZip = _dir.Combine("Broken.vpk");
        File.WriteAllBytes(notZip, new byte[TitleId.MaxTextFileSize + 1]);
        Assert.Null(TitleId.Read(notZip));
    }

    [Fact]
    public void A_param_sfo_without_a_title_id_or_cut_short_has_none()
    {
        Assert.Equal("PCSF00024", TitleId.FromParamSfo(GravityRush));
        Assert.Null(TitleId.FromParamSfo(Sfo(("TITLE", "GRAVITY RUSH"))));
        Assert.Null(TitleId.FromParamSfo(Sfo(("TITLE_ID", "TOO LONG TO BE ONE"))));
        Assert.Null(TitleId.FromParamSfo(GravityRush.AsSpan(0, GravityRush.Length - 12)));
        Assert.Null(TitleId.FromParamSfo(GravityRush.AsSpan(0, 24)));
        Assert.Null(TitleId.FromParamSfo("PK\u0003\u0004 not an sfo at all"u8));
    }

    private static void Write(ZipArchive zip, string name, byte[] content)
    {
        using var stream = zip.CreateEntry(name, CompressionLevel.NoCompression).Open();
        stream.Write(content);
    }
}
