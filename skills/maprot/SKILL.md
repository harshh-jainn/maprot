---
name: maprot
description: Turn a travel reel or short video link into a pin on an interactive trip map. Use when someone sends a social video link (Instagram reel, TikTok, Shorts) of a place and wants it saved, mapped, or added to a trip plan — or asks to build/rebuild a trip board. Handles identifying the place, geocoding it, picking photos, writing the write-up, and rendering the page.
---

# maprot

The person sends a link to a video about a place. You end up with that place
pinned on a map, with photos and a short write-up they can plan a trip from.

The CLI does the mechanical work. **You** do the part that matters: looking at
the frames, working out what the place actually is, and writing about it. Do not
try to automate your own judgement away.

## The pipeline, in the order that actually works

**1. Caption first.** `maprot fetch <url> --board <slug>` prints the post's
caption. This is the single most reliable signal — it usually names the venue
outright and often tags its account. Read it before anything else.

**2. Frames second.** `fetch` writes a contact sheet. **Read it with the Read
tool.** It is a tiled grid, so one image shows you the whole video. This is
where you catch what text cannot tell you: the dress code people are wearing,
whether it is busy, what the food looks like, whether the on-screen caption
names the venue.

**3. Transcript only if needed.** Add `--transcribe` when the post is narrated
*and* the caption is thin. Treat it as colour, never as ground truth — see the
failure notes below.

**4. Geocode.** `maprot geocode "<venue>" --locality "<town>" --country "<X>" --best`.
Then **cross-check the result against the address in the caption or on the
venue's site.** A hit whose street matches the listed address is confirmed; one
that does not is a guess.

**5. Write the entry** into `boards/<slug>/board.json` with the Edit tool.

**6. Cut the photos** you chose from the sheet:
`maprot still <post-id> --at <sec> --name <file.jpg> --board <slug>`

**7. Build.** `maprot build --board <slug>`. It warns about empty prose fields
and missing photos. Fix what it flags.

## Ask before assuming

Ask the person — briefly, in one turn — when you cannot tell from the link:

- **Which board?** `maprot list --board <slug>` shows existing ones. If none
  fits, `maprot init "<Country>" --country <ISO-A3>`.
- **Is this a place, or advice?** Some reels are itinerary tips with no venue at
  all. Those belong in the board's `notes`, not as a pin. Do not force a pin.
- **Region/province**, if the caption is vague and it affects the map.

Do not ask what you can determine yourself. The country is usually obvious from
the caption's hashtags.

## Four failure modes, all seen in real use

**The transcript lies.** Speech-to-text heard a restaurant called *Café Chill*
as *"Cafe Chin"* and placed it in the wrong city; the correct name was legible
on a menu in the frames. It also hallucinated a sentence on a loop for the last
20 seconds over trailing music. Names from audio are guesses. Names from
captions and on-screen text are evidence.

**Music-only posts.** Most reels have no narration, just a licensed track.
Transcribing them returns song lyrics, which are useless and not yours to copy
into a board. If the transcript is lyrics, discard it.

**Two posts, one venue.** Different creators post the same place. Check the
board before adding — if it is already pinned, add a second entry to that
place's `sources` array rather than creating a duplicate pin.

**Gated posts.** Some return "empty media response" and need a logged-in
session. `--cookies-from chrome` reads the person's live browser cookies, so
**never pass it unless they have said to.** Report the block and offer it as an
option.

## Writing the entry

Keep it skimmable. People scan trip boards; they do not read them.

- `one` — one line, under ~14 words. The hook, for the map callout.
- `unique` — one short paragraph, ~45 words. What makes this place *this* place,
  not a generic description. Wrap the sharpest phrase in `<em>`.
- `desc` — one short paragraph, ~70 words. What being there is like. Draw on the
  frames: light, crowds, materials, what people are wearing.
- `facts` — at most 4 pairs. Hours, price, what to order, what to watch out for.
- `near` — 3 distances that help sequence a day.

**Attribute claims, do not launder them.** "Ranked 2nd best in the world" is a
TripAdvisor award a creator quoted, not a fact. Prices are what one person paid
on one day. Write "by the resort's own reckoning" where that is what it is.

**Describe the place, not the person filming it.** Prefer frames showing the
venue over frames showing the creator's face, and do not describe children who
appear in footage.

## Details that are easy to get wrong

- **`loc`** groups places by town. Two pins in the same town get fanned apart
  automatically with leader lines back to their true position — that is why a
  pin a kilometre from another is still clickable.
- **`route`** is a list of `loc` values in road order; it draws the dashed
  itinerary line. Order it the way someone would actually drive it.
- **Reference towns are automatic** from Natural Earth, and any town that has
  its own pin is excluded. Do not hand-list them unless the defaults are wrong.
- **`approx: true`** plus `maps_query: "<venue name>"` for venues missing from
  OpenStreetMap: the pin sits on the locality, and the map links search by name
  so they still land on the real place.
- Photos: 3 per place is right. The first one is also the thumbnail and the
  callout image, so make it the most recognisable.

## Finishing

Build, then tell the person what you found — especially anything that
contradicts the source, anything you could not resolve, and any claim you had to
attribute rather than assert. If they want it shareable, the built file is a
single self-contained HTML page: it works offline, over a share link, or as an
Artifact.
