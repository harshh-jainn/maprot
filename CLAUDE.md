# Working on maprot

Read [`skills/maprot/SKILL.md`](skills/maprot/SKILL.md) first if you're *using*
maprot to add a place. This file is about changing the code.

## The split to preserve

Python does the mechanical work; the skill does the judgement. Resist the urge
to move editorial logic into Python — there is no `maprot describe` and there
should not be. If a step needs taste, it belongs in the skill.

## Layout

```
maprot/
  geo.py          Natural Earth fetch/cache, Mercator projection, reference cities
  geocode.py      Nominatim, rate-limited to 1 req/sec
  ingest.py       yt-dlp: caption metadata, then video
  frames.py       ffmpeg: contact sheets, stills, audio
  transcribe.py   optional mlx-whisper / faster-whisper
  board.py        board.json load/save, slugs, completeness checks
  render.py       board -> one HTML file; pin fan-out lives here
  cli.py          thin argparse wrapper
  templates/      style.css, app.js, page.html — token replacement, no engine
boards/<slug>/
  board.json      the data
  media/          committed photos
  work/           downloads, sheets, transcripts (gitignored)
```

## Conventions

- **Stdlib only** in the core; `yt-dlp` is the single runtime dependency.
  `ffmpeg`/`ffprobe` are external binaries — check with `shutil.which`.
- **Geometry is precomputed in Python.** `app.js` only draws. Keep it that way;
  it makes layout testable without a browser.
- **Templates use `{{TOKEN}}` replacement**, not a template engine. CSS is full
  of braces, so `str.format` is not an option.
- **CSS colours must be defined on bare `:root`**, then overridden in
  `prefers-color-scheme` and `[data-theme]` blocks. A colour whose only
  definition sits inside a media query renders one theme's text on the other
  theme's background.
- **Never fail silently on missing media.** `render.build` raises; empty prose
  fields warn.

## Testing a change

```bash
maprot build --board sri-lanka -o /tmp/check.html
python3 -c "import json,re; h=open('/tmp/check.html').read(); \
  js=h.split('<script>')[2].split('</script>')[0]; open('/tmp/c.js','w').write(js)"
node --check /tmp/c.js
```

The Sri Lanka board is the fixture: 7 places, two fan-out clusters (Ella and
Nuwara Eliya), one `approx` pin, one place with two sources, and a notes
section. If a change survives it rendering correctly, it probably works.
