# maprot

**Brain rot on a map.** You save travel reels you'll never watch again. maprot
turns them into an interactive trip map you'll actually use: every place pinned,
geolocated, with photos pulled from the video and a short write-up you can plan
a day from.

Output is one self-contained HTML file. No server, no API keys, no build step at
view time — photos are inlined, so it works offline and over any static host.

---

## Heads up: this is vibe-coded slop

Written in one sitting, almost entirely by Claude, while I fed it Instagram
links and told it what I didn't like. It works — the Sri Lanka board in this
repo is real output, not a mockup — but it has had approximately zero hours of
hardening. There are no tests. Error handling is best-effort. Interfaces will
change without ceremony. Read the code before you trust it with anything you
care about.

I'm putting it up because it's genuinely useful to me and might be to you, not
because it's finished.

---

## The honest architecture

maprot is **a small amount of Python and a skill.** That split is deliberate.

The Python does what a model cannot do for itself:

| step | what it does |
|---|---|
| `fetch` | pulls the caption, downloads the video, cuts a contact sheet |
| `still` | extracts a chosen frame, centre-cropped and scaled |
| `geocode` | resolves a venue name to coordinates via OpenStreetMap |
| `build` | projects the country from Natural Earth and renders the page |

Everything that actually requires judgement — looking at the frames, working out
which venue this *is*, noticing two reels are the same place, deciding what's
worth saying — is done by **Claude**, driven by [`skills/maprot/SKILL.md`](skills/maprot/SKILL.md).
That file is the real product. The Python is plumbing.

Place data lives in `boards/<slug>/board.json`: plain JSON, hand-editable,
diffable. No database, no lock-in.

## Use it with Claude Code

Install the skill once:

```bash
git clone https://github.com/harshh-jainn/maprot && cd maprot

# a venv or an isolated tool install — modern Pythons refuse `pip install`
# into the system environment (PEP 668)
uv tool install .          # or: uv venv && uv pip install -e .
                           # or: pipx install .

mkdir -p ~/.claude/skills && ln -s "$PWD/skills/maprot" ~/.claude/skills/maprot
```

Then just paste links:

> **you:** https://instagram.com/reel/DasyNaQvTQb/ — add this to my Sri Lanka trip

Claude reads the caption, looks at the contact sheet, geocodes the venue, writes
the entry, cuts the photos and rebuilds the page. It asks you which board or
country only when it genuinely can't tell.

## Use it by hand

```bash
maprot doctor                                    # check ffmpeg / yt-dlp
maprot init "Sri Lanka" --country LKA            # ISO A3 code
maprot fetch <url> --board sri-lanka             # caption + video + contact sheet
open boards/sri-lanka/work/*.sheet.jpg           # pick your frames
maprot still <post-id> --at 23.5 \
  --name 01-dambulla-a.jpg --board sri-lanka
maprot geocode "Café Chill" --locality Ella --country "Sri Lanka" --best
$EDITOR boards/sri-lanka/board.json              # write the entry
maprot build --board sri-lanka
maprot list --board sri-lanka                    # shows what still needs writing
```

`build` warns about empty prose and missing photos rather than shipping a
half-finished page.

## What the map does

- **Real coastlines.** Natural Earth 1:10m, fetched once and cached, projected
  to spherical Mercator and fitted to the country. Any country, by ISO A3 code.
- **Clustered pins fan out.** Two venues a kilometre apart are ~3 SVG units
  apart while a pin is ~29 wide. Overlapping pins get spread around a shared
  anchor dot with leader lines back to their true positions, so they stay
  clickable without lying about where they are.
- **Reference towns**, for orientation, minus anywhere that already has a pin.
  Set `reference_cities` to a number and it takes the country's largest cities
  from Natural Earth — a usable starting point, but population is a poor proxy
  for *recognisable*, so for a travel map you'll often want to list them
  explicitly instead. Labels flip to whichever side has room.
- **A route line.** List localities in road order and it draws the itinerary.
- **Approximate pins are labelled.** Venues missing from OpenStreetMap sit on
  their locality, get an `approx.` badge, and their map links search by name so
  they still resolve to the real place.
- **Mobile-first.** Pins scale up on small screens with 44px+ hit areas, and
  callouts clamp inside the map instead of spilling off the edge.
- **Both themes**, honouring an explicit toggle or the OS setting.

## Board format

```jsonc
{
  "country": "LKA",                 // ISO A3
  "route": ["Colombo", "Ella"],     // localities, in road order
  "reference_cities": 8,            // or an explicit list
  "places": [{
    "n": 1,
    "name": "Café Chill",
    "loc": "Ella",                  // groups pins; drives fan-out and route
    "region": "Uva",
    "lat": 6.8742, "lon": 81.0487,
    "approx": false,                // true -> badge + name-based map links
    "maps_query": null,
    "one":    "…",                  // map callout, one line
    "unique": "…",                  // ~45 words
    "desc":   "…",                  // ~70 words
    "facts":  [["Hours", "…"]],
    "near":   [["Ella town", "3.7 km"]],
    "photos": [{ "file": "04-cafe-chill-a.jpg", "alt": "…" }],
    "sources":[{ "url": "…", "by": "@handle", "dur": "80 s" }]
  }],
  "notes": { "items": [["don't", "do instead"]] }
}
```

`sources` is an array because different creators post the same venue — add to it
rather than creating a duplicate pin.

## Transcription is optional

Off by default, behind `--transcribe`. It uses `mlx-whisper` on Apple Silicon
and `faster-whisper` elsewhere, and skips cleanly if neither is installed.

It's optional because it turned out to be the *least* reliable signal. On real
posts it heard a restaurant called *Café Chill* as *"Cafe Chin"*, placed it in
the wrong city, and hallucinated a looping sentence over the trailing music. Most
reels have no narration at all — just a licensed track, which transcribes to song
lyrics. **Captions and on-screen text identify places; audio is colour at best.**

## Requirements

- Python ≥ 3.9, `ffmpeg` and `ffprobe` on PATH
- `yt-dlp` (installed as a dependency)
- Optional: `maprot[mlx]` (Apple Silicon) or `maprot[whisper]`

## Please be decent about it

Photos are frames from other people's videos and the write-ups draw on their
captions. Boards credit every creator and link back to every original post —
keep it that way. This is for planning your own trip, not for republishing
someone's work as your own. Downloaded videos and transcripts stay in
`boards/*/work/`, which is gitignored on purpose.

Some posts are private or gated and need a logged-in session. `--cookies-from`
exists for accounts you're entitled to read; don't point it at anything else.

## Contributing

**Fork it.** Genuinely — this is a small pile of scripts, and the interesting
version is probably the one you bend around your own trip, your own map style,
your own idea of what a good write-up looks like. You don't need permission and
you don't need to send it back.

If you'd rather contribute here instead:

- **Open an issue** for anything broken, wrong, or missing. Reports of places it
  mis-identified are the most useful kind — that's the failure mode that
  matters, and every one of them belongs in the skill as a named trap.
- **Open a PR** from a branch or from your fork. Keep it small and focused.
  Changes to *how a place gets written up* belong in
  [`skills/maprot/SKILL.md`](skills/maprot/SKILL.md), not in Python.
- **Don't move judgement into the code.** The split described above is the whole
  design. There is no `maprot describe` and there shouldn't be.

**`main` is pull-request only.** Nobody commits to it directly — not
contributors, and mostly not me either. Branch, PR, merge. GitHub gates
protection rules behind Pro for private repos, so this is currently a convention
rather than something the server enforces; it gets switched on the moment the
repo goes public. Treat it as binding regardless.

## Credits

Country and city geometry from [Natural Earth](https://www.naturalearthdata.com/)
(public domain). Geocoding by [Nominatim](https://nominatim.org/) /
OpenStreetMap contributors (ODbL) — be gentle, it's rate-limited to one request
per second. Downloads via [yt-dlp](https://github.com/yt-dlp/yt-dlp).

MIT licensed.
