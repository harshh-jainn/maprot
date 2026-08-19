"""maprot command line.

Deliberately small. These are the mechanical steps a model cannot do for
itself: fetch a post, cut frames, geocode a name, project a country, render a
page. Everything editorial — deciding what a place is, which frames are good,
what is worth saying about it — happens in the skill, and lands in board.json,
which is plain JSON you can edit by hand or with any agent.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import board as B
from . import frames, geocode, ingest, render


def _ok(msg): print(f"  \033[32m✓\033[0m {msg}")
def _no(msg): print(f"  \033[31m✗\033[0m {msg}")
def _hm(msg): print(f"  \033[33m!\033[0m {msg}")


# ---------------------------------------------------------------- doctor
def cmd_doctor(a):
    from . import transcribe
    print("maprot doctor")
    ok = True
    for bin_, why in (("yt-dlp", "downloading posts"), ("ffmpeg", "frames"), ("ffprobe", "durations")):
        if shutil.which(bin_):
            _ok(f"{bin_} — {why}")
        else:
            _no(f"{bin_} missing — needed for {why}")
            ok = False
    backend = transcribe.available()
    if backend:
        _ok(f"transcription backend: {backend}")
    else:
        _hm(f"no transcription backend (optional). {transcribe.install_hint()}")
    cache = __import__("maprot.geo", fromlist=["geo"]).cache_dir()
    have = list(cache.glob("*.geojson"))
    _ok(f"map cache: {cache} ({len(have)} file(s))") if have else _hm(
        f"map cache empty — first build downloads Natural Earth into {cache}")
    return 0 if ok else 1


# ---------------------------------------------------------------- init
def cmd_init(a):
    slug = B.slugify(a.name)
    p = B.path_for(slug)
    if p.exists() and not a.force:
        raise SystemExit(f"maprot: {p} exists (use --force)")
    bd = B.new_board(slug, a.name, a.country)
    if a.title:
        bd["title"] = a.title
    B.save(bd, p)
    B.media_dir(p)
    _ok(f"created {p}")
    print(f"\n  Next:  maprot fetch <url> --board {slug}")
    return 0


# ---------------------------------------------------------------- fetch
def cmd_fetch(a):
    bd, bp = B.load(a.board)
    work = B.work_dir(bp)

    print(f"maprot fetch {a.url}")
    meta = ingest.metadata(a.url, a.cookies_from)
    pid = meta["id"]
    _ok(f"caption from {meta['uploader']} (@{meta['handle']}), {meta['duration']}s")

    cap = work / f"{pid}.caption.txt"
    cap.write_text(meta["caption"])

    video = ingest.download(a.url, work / pid, a.cookies_from)
    _ok(f"video {video.name} ({video.stat().st_size // 1024} KB)")

    sheet, stamps = frames.contact_sheet(video, work / f"{pid}.sheet.jpg",
                                         cols=a.cols, rows=a.rows)
    _ok(f"contact sheet {sheet.name} — {a.cols}x{a.rows} frames")

    transcript = ""
    if a.transcribe:
        from . import transcribe as tr
        wav = frames.audio(video, work / f"{pid}.wav")
        transcript = tr.run(wav, a.model)
        if transcript:
            (work / f"{pid}.transcript.txt").write_text(transcript)
            _ok(f"transcript ({len(transcript.split())} words)")

    out = {"id": pid, "url": a.url, "uploader": meta["uploader"],
           "handle": meta["handle"], "duration": meta["duration"],
           "caption": meta["caption"], "video": str(video), "sheet": str(sheet),
           "frame_times": stamps, "transcript": transcript}
    (work / f"{pid}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"\n  Caption:\n{_indent(meta['caption'] or '(empty)')}")
    print(f"\n  Read the sheet, then cut the frames you want:")
    print(f"    maprot still {pid} --at <seconds> --name <file.jpg> --board {a.board}")
    print(f"  Frame times in the sheet: {', '.join(str(s) for s in stamps)}")
    if not a.transcribe:
        print("  (add --transcribe if the post is narrated and the caption is thin)")
    return 0


def _indent(s, n=4):
    pad = " " * n
    return "\n".join(pad + l for l in (s or "").splitlines())


# ---------------------------------------------------------------- still
def cmd_still(a):
    bd, bp = B.load(a.board)
    work, media = B.work_dir(bp), B.media_dir(bp)
    hits = [p for p in work.glob(f"{a.post}.*")
            if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if not hits:
        raise SystemExit(f"maprot: no downloaded video for {a.post!r} in {work}. Run `maprot fetch` first.")
    out = frames.still(hits[0], a.at, media / a.name, width=a.width, aspect=a.aspect)
    _ok(f"{out.relative_to(bp.parent)} ({out.stat().st_size // 1024} KB) @ {a.at}s")
    if a.thumb:
        t = frames.still(hits[0], a.at, media / a.thumb, width=210, aspect=a.aspect)
        _ok(f"{t.relative_to(bp.parent)} (thumb)")
    return 0


# ---------------------------------------------------------------- geocode
def cmd_geocode(a):
    if a.best:
        hit = geocode.best(a.query, a.locality or "", a.country or "")
        print(json.dumps(hit, indent=2) if hit else "null")
        return 0 if hit else 1
    rows = geocode.lookup(" ".join(x for x in (a.query, a.locality, a.country) if x), a.limit)
    print(json.dumps(rows, indent=2))
    return 0 if rows else 1


# ---------------------------------------------------------------- build
def cmd_build(a):
    bd, bp = B.load(a.board)
    out = Path(a.out) if a.out else bp.parent / f"{bd['slug']}.html"
    print(f"maprot build {bd['slug']} → {out}")
    path, warns = render.build(bd, bp, out)
    for w in warns:
        _hm(w)
    kb = path.stat().st_size // 1024
    _ok(f"{path} ({kb} KB, {len(bd['places'])} places)")
    if kb > 3000:
        _hm("page is heavy — consider fewer photos per place")
    return 0


# ---------------------------------------------------------------- list
def cmd_list(a):
    bd, bp = B.load(a.board)
    print(f"{bd['title']}  ({bd['country']}, {len(bd['places'])} places)")
    for p in sorted(bd["places"], key=lambda x: x.get("n", 0)):
        gaps = B.incomplete(p)
        flag = f"  \033[33mneeds: {', '.join(gaps)}\033[0m" if gaps else ""
        print(f"  {p['n']:>2}. {p['name']:<28} {p.get('loc',''):<16}"
              f"{'~' if p.get('approx') else ' '}{flag}")
    return 0


# ---------------------------------------------------------------- parser
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="maprot", description="Brain rot on a map — reels in, trip map out.")
    ap.add_argument("--version", action="version", version=__import__("maprot").__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="check external dependencies")
    d.set_defaults(fn=cmd_doctor)

    i = sub.add_parser("init", help="create a board")
    i.add_argument("name", help='e.g. "Sri Lanka"')
    i.add_argument("--country", required=True, help="ISO A3 code, e.g. LKA")
    i.add_argument("--title", help="page title (defaults to name)")
    i.add_argument("--force", action="store_true")
    i.set_defaults(fn=cmd_init)

    f = sub.add_parser("fetch", help="caption + video + contact sheet for one post")
    f.add_argument("url")
    f.add_argument("--board", required=True)
    f.add_argument("--transcribe", action="store_true", help="also run speech-to-text")
    f.add_argument("--model", default="large-v3-turbo")
    f.add_argument("--cols", type=int, default=4)
    f.add_argument("--rows", type=int, default=3)
    f.add_argument("--cookies-from", help="browser to read cookies from for gated posts")
    f.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("still", help="cut one frame into the board's media dir")
    s.add_argument("post", help="post id from `maprot fetch`")
    s.add_argument("--at", type=float, required=True, help="seconds")
    s.add_argument("--name", required=True, help="output filename, e.g. 04-cafe-chill-a.jpg")
    s.add_argument("--thumb", help="also write a small thumbnail under this name")
    s.add_argument("--board", required=True)
    s.add_argument("--width", type=int, default=460)
    s.add_argument("--aspect", default="3:4", choices=["3:4", "1:1", "full"])
    s.set_defaults(fn=cmd_still)

    g = sub.add_parser("geocode", help="look up coordinates for a place name")
    g.add_argument("query")
    g.add_argument("--locality", help="town or city, to disambiguate")
    g.add_argument("--country")
    g.add_argument("--limit", type=int, default=3)
    g.add_argument("--best", action="store_true",
                   help="one result, widening the query and flagging approximate fallbacks")
    g.set_defaults(fn=cmd_geocode)

    b = sub.add_parser("build", help="render the board to one HTML file")
    b.add_argument("--board", required=True)
    b.add_argument("--out", "-o")
    b.set_defaults(fn=cmd_build)

    l = sub.add_parser("list", help="show places and what still needs writing")
    l.add_argument("--board", required=True)
    l.set_defaults(fn=cmd_list)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (ingest.IngestError, frames.FrameError) as e:
        _no(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
