using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using Godot;
using Launcher.Core.Media;
using Launcher.Core.Models;
using Launcher.Core.Theming;

namespace Launcher.App.Models;

public enum ModelState
{
    Loading,
    Ready,
    Failed,
}

/// <summary>
/// Loads model candidates into <see cref="ItemTemplate"/>s without file I/O on the main thread (A3, A7). A user's model
/// (per-game, <c>ConfigDir/models/</c>, a user theme's) comes from <see cref="ModelCache"/>, which inspects it against
/// its budget, scales its textures down and remembers the result, so a bad file is caught before Godot parses it and
/// only processed once; a built-in theme's is read from the PCK. Every model is then parsed by
/// <see cref="GltfDocument"/> and converted on its own worker, so they load in parallel, and the main thread only
/// adopts the result, within a time budget per frame. Models are kept for the session (a theme switch reloads user
/// files; <see cref="ReleasePerGame"/> drops per-game models no list needs). A candidate that's rejected or fails
/// is logged to the model log the user can read (<c>DataDir/logs/models.log</c>), and the next candidate in line is used.
/// </summary>
public sealed class ModelLoader
{
    private const double PollBudgetMs = 2;
    private const string PerGameSuffix = "|" + nameof(ModelKind.PerGame);

    private readonly Dictionary<string, Entry> _entries = new(StringComparer.Ordinal);
    private readonly Dictionary<string, ConvertedModel> _models = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _failed = new(StringComparer.Ordinal);
    private readonly HashSet<string> _loading = new(StringComparer.Ordinal);
    private readonly List<ConvertedModel> _retired = [];
    private readonly ConcurrentQueue<(string File, ConvertedModel? Model, string? Error, double WorkerMs)> _parsed = new();
    private ModelCache? _cache;
    private ModelLog? _log;

    private sealed class Entry(ModelCandidate candidate, bool systemCard, string file)
    {
        public ModelCandidate Candidate { get; } = candidate;

        public bool SystemCard { get; } = systemCard;

        /// <summary>The loaded file's key: its path and the budget it's held to.</summary>
        public string File { get; } = file;

        public ModelState State { get; set; } = ModelState.Loading;

        public ItemTemplate? Template { get; set; }
    }

    /// <summary>Loads still in flight.</summary>
    public int Pending => _loading.Count;

    /// <summary>Loads finished on a worker that the main thread hasn't adopted yet.</summary>
    public bool HasResults => !_parsed.IsEmpty;

    /// <summary>
    /// Where processed user models are cached and problems logged. Set before the first user model is requested (the
    /// boot does it as soon as the theme is resolved); without it, user models are processed each time and unlogged.
    /// </summary>
    public void UseFolders(string cacheDir, string dataDir, IImageDecoder? decoder)
    {
        _log = new ModelLog(dataDir);
        _cache = new ModelCache(cacheDir, decoder, _log);
    }

    /// <summary>Main thread. Starts loading the candidate's file, unless it's loaded or loading, and says where it stands.</summary>
    public ModelState Request(ModelCandidate candidate, bool systemCard)
    {
        var key = EntryKey(candidate, systemCard);
        if (_entries.TryGetValue(key, out var entry))
        {
            return entry.State;
        }

        var kind = KindOf(candidate, systemCard);
        var file = $"{candidate.Path}|{kind}";
        entry = new Entry(candidate, systemCard, file);
        _entries[key] = entry;
        if (!_models.ContainsKey(file) && !_failed.ContainsKey(file) && _loading.Add(file))
        {
            Start(candidate, kind, file);
        }

        Settle(entry);
        return entry.State;
    }

    /// <summary>The loaded template, or null while it loads or if it failed.</summary>
    public ItemTemplate? Get(ModelCandidate candidate, bool systemCard) =>
        _entries.TryGetValue(EntryKey(candidate, systemCard), out var entry) ? entry.Template : null;

    public ModelState StateOf(ModelCandidate candidate, bool systemCard) =>
        _entries.TryGetValue(EntryKey(candidate, systemCard), out var entry) ? entry.State : ModelState.Loading;

    /// <summary>
    /// Main thread, each frame while anything loads: adopts the loads that are done, for up to 2 ms (a list of hundreds
    /// of per-game models finishing together mustn't make one long frame). True when something changed.
    /// </summary>
    public bool Poll()
    {
        var changed = false;
        var start = System.Diagnostics.Stopwatch.GetTimestamp();
        while (System.Diagnostics.Stopwatch.GetElapsedTime(start).TotalMilliseconds < PollBudgetMs && _parsed.TryDequeue(out var result))
        {
            Finished(result.File, result.Model, result.Error);
            if (result.Model is { } model && !result.File.EndsWith(PerGameSuffix, StringComparison.Ordinal))
            {
                GD.Print(FormattableString.Invariant(
                    $"Models: {Path.GetFileName(result.File[..result.File.LastIndexOf('|')])} parsed and converted in {result.WorkerMs:0.0} ms on a worker ({model.Triangles} triangles{(model.Scene is null ? string.Empty : ", with clips")})."));
            }

            changed = true;
        }

        return changed;
    }

    /// <summary>
    /// Main thread: user files are read again next time (a theme switch picks up edited models). The grids still draw
    /// the forgotten models until the next theme is applied, so their node trees are freed then
    /// (<see cref="FreeRetired"/>).
    /// </summary>
    public void ForgetUserModels()
    {
        foreach (var (key, entry) in new List<KeyValuePair<string, Entry>>(_entries))
        {
            if (entry.Candidate.Origin == ThemeOrigin.User && entry.State != ModelState.Loading)
            {
                _entries.Remove(key);
                if (_models.Remove(entry.File, out var model) && model.Scene is not null)
                {
                    _retired.Add(model);
                }

                _failed.Remove(entry.File);
            }
        }
    }

    /// <summary>
    /// Main thread, once a theme has been applied and the grids hold none of the forgotten models: frees their node
    /// trees, which are never in the scene tree (each theme switch away from models with clips leaked them).
    /// </summary>
    public void FreeRetired()
    {
        foreach (var model in _retired)
        {
            if (model.Scene is { } scene && GodotObject.IsInstanceValid(scene))
            {
                scene.QueueFree();
            }
        }

        _retired.Clear();
    }

    /// <summary>
    /// Main thread: drops the per-game models whose files aren't in <paramref name="keep"/> (the lists shown or cached),
    /// so a session browsing many systems doesn't keep every model it has seen. They load again when needed.
    /// </summary>
    public void ReleasePerGame(IReadOnlySet<string> keep)
    {
        foreach (var (key, entry) in new List<KeyValuePair<string, Entry>>(_entries))
        {
            if (entry.Candidate.Level == ModelLevel.UserGame && entry.State != ModelState.Loading && !keep.Contains(entry.Candidate.Path))
            {
                _entries.Remove(key);
                if (_models.Remove(entry.File, out var model))
                {
                    model.Scene?.QueueFree();
                }

                _failed.Remove(entry.File);
            }
        }
    }

    /// <summary>Main thread: forgets one per-game model's file, so it's loaded again when next requested.</summary>
    public void ReleasePerGame(string path)
    {
        foreach (var (key, entry) in new List<KeyValuePair<string, Entry>>(_entries))
        {
            if (entry.Candidate.Level == ModelLevel.UserGame && entry.State != ModelState.Loading && entry.Candidate.Path == path)
            {
                _entries.Remove(key);
                if (_models.Remove(entry.File, out var model))
                {
                    model.Scene?.QueueFree();
                }

                _failed.Remove(entry.File);
            }
        }
    }

    /// <summary>Main thread, at exit: frees the models' node trees, which are never in the scene tree.</summary>
    public void FreeScenes()
    {
        _retired.AddRange(_models.Values);
        foreach (var model in _retired)
        {
            if (model.Scene is { } scene && GodotObject.IsInstanceValid(scene))
            {
                scene.Free();
            }
        }

        _retired.Clear();
        _models.Clear();
        _entries.Clear();
    }

    private static ModelKind KindOf(ModelCandidate candidate, bool systemCard) =>
        systemCard ? ModelKind.SystemModel : candidate.Level == ModelLevel.UserGame ? ModelKind.PerGame : ModelKind.GameTemplate;

    private static string EntryKey(ModelCandidate candidate, bool systemCard) => systemCard ? "card|" + candidate.Key : candidate.Key;

    private void Start(ModelCandidate candidate, ModelKind kind, string file)
    {
        var path = candidate.Path;
        var description = candidate.Description;
        var inPack = candidate.Origin == ThemeOrigin.BuiltIn;
        var cache = _cache;
        var log = _log;
        _ = Task.Run(() =>
        {
            var clock = System.Diagnostics.Stopwatch.StartNew();
            try
            {
                byte[] bytes;
                if (inPack)
                {
                    if (!Godot.FileAccess.FileExists(path))
                    {
                        _parsed.Enqueue((file, null, "the file doesn't exist", 0));
                        return;
                    }

                    bytes = Godot.FileAccess.GetFileAsBytes(path);
                }
                else
                {
                    // Inspected, fitted to its budget and cached (or rejected, and logged) before Godot sees it.
                    var cached = (cache ?? new ModelCache(Path.Combine(Path.GetTempPath(), "odyssey-models"), null, null)).Get(path, kind, description);
                    if (cached.Path is null)
                    {
                        _parsed.Enqueue((file, null, $"it was rejected: {string.Join("; ", cached.Report.Errors)} (see {log?.Path ?? "the model log"})", 0));
                        return;
                    }

                    bytes = File.ReadAllBytes(cached.Path);
                }

                var model = ModelConverter.Convert(bytes, Path.GetFileNameWithoutExtension(path), out var error);
                if (model is null && !inPack)
                {
                    log?.Write(Launcher.Core.Diagnostics.LogLevel.Error, $"{description}: Godot couldn't load it: {error}. The next model in line is used instead");
                }

                _parsed.Enqueue((file, model, error, clock.Elapsed.TotalMilliseconds));
            }
            catch (Exception e)
            {
                log?.Write(Launcher.Core.Diagnostics.LogLevel.Error, $"{description}: couldn't be loaded: {e.Message}. The next model in line is used instead");
                _parsed.Enqueue((file, null, e.Message, 0));
            }
        });
    }

    private void Finished(string file, ConvertedModel? model, string? error)
    {
        _loading.Remove(file);
        if (model is null)
        {
            _failed[file] = error ?? "it couldn't be loaded";
        }
        else
        {
            _models[file] = model;
            foreach (var warning in model.Warnings)
            {
                GD.PushWarning($"Models: {file}: {warning}.");
            }
        }

        foreach (var entry in _entries.Values)
        {
            if (entry.State == ModelState.Loading && entry.File == file)
            {
                Settle(entry);
            }
        }
    }

    private void Settle(Entry entry)
    {
        if (_failed.TryGetValue(entry.File, out var error))
        {
            entry.State = ModelState.Failed;
            GD.PushWarning($"Models: {entry.Candidate.Description} ({entry.Candidate.Path}) can't be used: {error}. The next model in line is used.");
            return;
        }

        if (!_models.TryGetValue(entry.File, out var model))
        {
            return;
        }

        entry.Template = new ItemTemplate(entry.Candidate, entry.SystemCard, model);
        entry.State = ModelState.Ready;
        if (entry.Candidate.Template?.ShapeFromMedia == true && !entry.SystemCard && !entry.Template.ShapeFromMedia)
        {
            GD.PushWarning($"Models: {entry.Candidate.Description} ({entry.Candidate.Path}) has animation clips, so it keeps its own shape: shape = \"media\" is for static boxes.");
        }
    }
}
