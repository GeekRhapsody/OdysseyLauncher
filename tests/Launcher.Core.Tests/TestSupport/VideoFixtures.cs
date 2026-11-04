namespace Launcher.Core.Tests.TestSupport;

/// <summary>
/// The committed test videos (<c>Media/Videos</c>, written by tools/linux/make-test-videos.sh), for where Media
/// Foundation can't write them: <see cref="TestVideos"/>' picture, 30 frames, and its tone. <c>red-blue.mp4</c> is
/// H.264 and AAC, <c>red-blue-silent.mp4</c> has no sound, and the others are named after their codecs.
/// </summary>
internal static class VideoFixtures
{
    public static readonly string[] Codecs =
        ["red-blue.mp4", "red-blue-h264-444.mp4", "red-blue-hevc.mp4", "red-blue-vp9-opus.mp4", "red-blue-mp3.mp4"];

    public static string File(string name) => Path.Combine(AppContext.BaseDirectory, "Media", "Videos", name);
}
