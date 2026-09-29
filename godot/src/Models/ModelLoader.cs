using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using Godot;
using Launcher.Core.Theming;

namespace Launcher.App.Models;

public enum ModelState
{
    Loading,
    Ready,
    Failed,
}

/// <summary>
/// Loads model candidates into <see cref="ItemTemplate"/>s without file I/O on the main thread (A3, A7). Every model,
/// a built-in theme's (<c>res://</c>, exported as the <c>.glb</c> itself) or a user's (user themes',
/// <c>ConfigDir/models/</c>), is parsed by <see cref="GltfDocument"/> and converted on its own worker, so they load in
/// parallel; the main thread only uploads each merged mesh. (Godot's threaded loader of imported scenes took about
/// 25 ms a model, one after another: docs/perf/m6-themes.md.) Meshes are cached by file for the session (theme switches
/// reload user files), and every candidate is loaded once. A game template without a <c>cover</c> material is rejected
/// (A7), so the next candidate in line is used.
/// </summary>
public sealed class ModelLoader
{
    private readonly Dictionary<string, Entry> _entries = new(StringComparer.Ordinal);
    private readonly Dictionary<string, ConvertedModel> _models = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _failed = new(StringComparer.Ordinal);
    private readonly HashSet<string> _loading = new(StringComparer.Ordinal);
    private readonly ConcurrentQueue<(string Path, ConvertedModel? Model, string? Error, double WorkerMs)> _parsed = new();

    private sealed class Entry(ModelCandidate candidate, bool systemCard)
    {
        public ModelCandidate Candidate { get; } = candidate;

        public bool SystemCard { get; } = systemCard;

        public ModelState State { get; set; } = ModelState.Loading;

        public ItemTemplate? Template { get; set; }
    }

    /// <summary>Loads still in flight.</summary>
    public int Pending => _loading.Count;

    /// <summary>Main thread. Starts loading the candidate's file, unless it's loaded or loading, and says where it stands.</summary>
    public ModelState Request(ModelCandidate candidate, bool systemCard)
    {
        var key = EntryKey(candidate, systemCard);
        if (_entries.TryGetValue(key, out var entry))
        {
            return entry.State;
        }

        entry = new Entry(candidate, systemCard);
        _entries[key] = entry;
        if (!_models.ContainsKey(candidate.Path) && !_failed.ContainsKey(candidate.Path) && _loading.Add(candidate.Path))
        {
            Start(candidate);
        }

        Settle(entry);
        return entry.State;
    }

    /// <summary>The loaded template, or null while it loads or if it failed.</summary>
    public ItemTemplate? Get(ModelCandidate candidate, bool systemCard) =>
        _entries.TryGetValue(EntryKey(candidate, systemCard), out var entry) ? entry.Template : null;

    public ModelState StateOf(ModelCandidate candidate, bool systemCard) =>
        _entries.TryGetValue(EntryKey(candidate, systemCard), out var entry) ? entry.State : ModelState.Loading;

    /// <summary>Main thread, each frame while anything loads: finishes the loads that are done. True when something changed.</summary>
    public bool Poll()
    {
        var changed = false;
        while (_parsed.TryDequeue(out var result))
        {
            var upload = System.Diagnostics.Stopwatch.StartNew();
            Finished(result.Path, result.Model, result.Error);
            if (result.Model is not null)
            {
                GD.Print(FormattableString.Invariant(
                    $"Models: {System.IO.Path.GetFileName(result.Path)} parsed and converted in {result.WorkerMs:0.0} ms on a worker, uploaded in {upload.Elapsed.TotalMilliseconds:0.0} ms on the main thread ({result.Model.Indices.Count / 3} triangles)."));
            }

            changed = true;
        }

        return changed;
    }

    /// <summary>Main thread: user files are read again next time (a theme switch picks up edited models).</summary>
    public void ForgetUserModels()
    {
        foreach (var (key, entry) in new List<KeyValuePair<string, Entry>>(_entries))
        {
            if (entry.Candidate.Origin == ThemeOrigin.User && entry.State != ModelState.Loading)
            {
                _entries.Remove(key);
                _models.Remove(entry.Candidate.Path);
                _failed.Remove(entry.Candidate.Path);
            }
        }
    }

    private static string EntryKey(ModelCandidate candidate, bool systemCard) => systemCard ? "card|" + candidate.Key : candidate.Key;

    private void Start(ModelCandidate candidate)
    {
        var path = candidate.Path;
        var inPack = candidate.Origin == ThemeOrigin.BuiltIn;
        _ = Task.Run(() =>
        {
            var clock = System.Diagnostics.Stopwatch.StartNew();
            try
            {
                if (inPack ? !Godot.FileAccess.FileExists(path) : !File.Exists(path))
                {
                    _parsed.Enqueue((path, null, "the file doesn't exist", 0));
                    return;
                }

                var document = new GltfDocument();
                var state = new GltfState();
                var error = document.AppendFromFile(path, state);
                if (error != Error.Ok)
                {
                    _parsed.Enqueue((path, null, $"it isn't a glTF 2.0 file Godot can read ({error})", 0));
                    return;
                }

                var model = ModelConverter.FromGltf(state, out var problem);
                _parsed.Enqueue((path, model, problem, clock.Elapsed.TotalMilliseconds));
            }
            catch (Exception e)
            {
                _parsed.Enqueue((path, null, e.Message, 0));
            }
        });
    }

    private void Finished(string path, ConvertedModel? model, string? error)
    {
        _loading.Remove(path);
        if (model is null)
        {
            _failed[path] = error ?? "it couldn't be loaded";
        }
        else
        {
            model.Build(System.IO.Path.GetFileNameWithoutExtension(path));
            _models[path] = model;
            foreach (var warning in model.Warnings)
            {
                GD.PushWarning($"Models: {path}: {warning}.");
            }
        }

        foreach (var entry in _entries.Values)
        {
            if (entry.State == ModelState.Loading && entry.Candidate.Path == path)
            {
                Settle(entry);
            }
        }
    }

    private void Settle(Entry entry)
    {
        var path = entry.Candidate.Path;
        if (_failed.TryGetValue(path, out var error))
        {
            Fail(entry, error);
            return;
        }

        if (!_models.TryGetValue(path, out var model))
        {
            return;
        }

        if (!entry.SystemCard && model.SlotAspects[MediaSlots.Cover] == 0)
        {
            Fail(entry, "it has no 'cover' material, which every game template needs (A7)");
            return;
        }

        entry.Template = new ItemTemplate(entry.Candidate, entry.SystemCard, model);
        entry.State = ModelState.Ready;
    }

    private static void Fail(Entry entry, string error)
    {
        entry.State = ModelState.Failed;
        GD.PushWarning($"Models: {entry.Candidate.Description} ({entry.Candidate.Path}) can't be used: {error}. The next model in line is used.");
    }
}
