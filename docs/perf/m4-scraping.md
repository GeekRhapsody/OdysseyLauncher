# M4: scraping and the media pipeline, measurements

Measured on 28 September 2026 on the baseline Steam Deck (docked, Windows 11, desktop at 2560×1440, 59.94 Hz), the same machine as [m5-navigation.md](m5-navigation.md). Everything below ran on this machine; nothing here touched a provider's API (live scraping needs the owner's credentials: [manual-tests.md](../manual-tests.md#m4-a-live-scrape)).

## The BC7 encoder (risk R1)

M1 chose BC7 DDS derivatives but left the encoder open, because the export templates can't encode BCn ([SPIKE_RESULTS.md](../SPIKE_RESULTS.md) R1). The owner approved BCnEncoder.Net for M4. It was measured first, and replaced.

**Method.** A 512² image, encoded with its full mip chain (10 levels, 21,845 blocks), single-threaded, in Release on .NET 10 (the console harness; Core itself targets .NET 8). Quality is PSNR over RGB of the top level, decoded by BCnEncoder.Net's decoder, against the 512² image the encoder was given (the source scaled by Windows' WIC with its high-quality cubic filter).

| Encoder | Time per 512² cover with mips | Quality, synthetic covers (40, M1's library) | Quality, real box art (3 Mega Drive covers from the NAS) |
|---|---|---|---|
| BCnEncoder.Net 2.3.0, `Balanced` | **about 10 s** (9.6–10.4 s; `Fast` is no quicker) | — | 36.86 / 39.25 / 40.14 dB |
| Ours, mode 6 only (first version) | 167 ms median (synthetic), 188 ms (real) | 50.83 dB | 30.94 / 33.34 / 37.66 dB (mean of 14: 35.27 dB) |
| **Ours, mode 6 + mode 1 (shipped)** | 197 ms median (synthetic), **440 ms** median, 685 ms max (real) | **50.89 dB** | **37.33 / 39.68 / 40.67 dB** (mean of 14: **40.04 dB**, worst 37.33 dB) |
| Godot's editor encoder (M1's files) | editor only | 49.34 dB | — |

- **BCnEncoder.Net is too slow for thousands of covers:** 10 s each is about 39 hours of one core for the 14,215-game synthetic library. It stays in the test project only, as an independent decoder that checks our blocks.
- **Our encoder** (`Launcher.Core.Media.Bc7Encoder`) uses two of BC7's eight modes:
  - Mode 6, one subset with 7-bit RGBA endpoints plus p-bits and 4-bit indices, for every block. Endpoints come from the colours' principal axis, then two rounds of least-squares refinement, each trying the four p-bit combinations.
  - Mode 1, two subsets from BC7's 64 partitions with 6-bit endpoints and 3-bit indices, only for opaque blocks where mode 6's error is above an average of about 3 per channel (edges: text, outlines, logos). Every partition is scored by its colours' variance off each subset's principal axis; the best 3 are encoded in full.
  - With mode 1 it's slightly better than BCnEncoder.Net on the real covers, at 4% of the time. On real art it takes about 0.44 s a cover on the Deck: 14,000 covers is about 1.7 hours of one below-normal thread, once.
- **Correctness:** `DerivativeTests.Every_block_decodes_exactly_as_the_encoder_predicted_in_both_modes` encodes 3,000 blocks (flat regions on random partitions, noise, gradients, varying alpha) and checks that the squared error BCnEncoder.Net's decoder measures equals the error the encoder predicted, exactly. That checks both modes' bit layout, the partition and anchor tables, the weights and endpoint expansion.
- **Godot reads it:** the header is byte for byte M1's (DX10, `DXGI_FORMAT_BC7_UNORM`, 10 mips, 349,700 bytes), and a capture of the export-equivalent editor run shows a real cover baked by the console tool ([m4/real-cover-bc7.png](m4/real-cover-bc7.png)).

**Decoding** needs no package either: `WicImageDecoder` (Platform/Windows) decodes PNG, JPEG and WebP and scales with WIC, through raw COM vtable calls. Linux has no decoder yet, so nothing is baked there.

Reproduce: the harness lived in the session scratchpad (a console referencing Core and BCnEncoder.Net). `odyssey-scrape bake` times a real bake: 1.0–1.8 s for one cover, including WIC's start-up.

## The app: no regression

The app's only change on the boot and browse path: after the first background scans (or at once when there are none), `Navigator` runs `DerivativeService.BakeMissingAsync` on the derivative service's below-normal thread; it's off in benches, as scans are. The details query also joins `scrape_state` (thread pool).

An A/B in one session: the M5 commit (`7616fdb`, exported from a worktree, with a copy of the synthetic library downgraded to its schema) against this build, alternated.

| Build | Scroll hitches (3 × 60 s, scroll frames) | >2× | Scroll p99 | Main thread | Start-up of our code (median of 5) | Working set |
|---|---|---|---|---|---|---|
| M5 (`7616fdb`) | 3, 0, 0 | 0 | 20.2–21.4 ms | 64 B | 375 ms | 356–357 MB |
| M4 | 1, 2, 1 | 0 | 20.2–21.2 ms | 64 B | 354 ms | 357–358 MB |

Both have 100% of on-screen cells textured, the same GPU time (1.21 ms) and the same p99, which is the presentation limit M5 recorded. JSON: [m4/ab-m5-scroll](m4/ab-m5-scroll/), [m4/ab-m4-scroll](m4/ab-m4-scroll/), [m4/ab-m5-boot](m4/ab-m5-boot/), [m4/ab-m4-boot](m4/ab-m4-boot/).

Earlier in the session, before anything was alternated, one textured run had 13 hitches and a 91 ms frame, and the no-texture control had 1–3; the A/B above didn't reproduce it, so it's recorded as the environment's.

```powershell
.\tools\bench-export.ps1 -SkipExport -Runs 3 -Label ab-m4-scroll -AppArgs "--user-dir=$PWD\artifacts\synthetic", '--bench-scenario=scroll'
.\tools\bench-export.ps1 -SkipExport -Runs 5 -Frames 300 -Label ab-m4-boot -AppArgs "--user-dir=$PWD\artifacts\synthetic"
```

**Not measured:** scrolling while the baker runs. A bake allocates little managed memory (a file stream and path strings; the pixel buffer is one per thread, reused), runs below normal priority, and is a one-off per cover.

## Scraping throughput

No live numbers yet: they need the owner's credentials. What bounds it, from the providers' documentation and the code:
- ScreenScraper: the account's `maxthreads` (1 anonymous; 1–8 by contribution) and `maxrequestspermin`; its daily quota (20,000–100,000) and daily quota of lookups that find nothing (about a tenth). A game costs 1 lookup (2 with a title search) plus one request per media file.
- IGDB: 4 requests a second, at most 8 open (the client keeps to 4). One request a game, plus image downloads from its CDN.
- SteamGridDB: undocumented; paced at 2 in flight and 4 a second. One search plus one request per art list wanted.
- Baking: about 0.44 s a cover on one thread.
