"""Create the "Slow It Down" project page in the Projects database (TransitiveBullsh.it CMS) via the Notion REST API.

Every image, video and audio file is uploaded to Notion (multi-part for the big video); only the original song's
YouTube video is embedded by URL. Public / Featured / Published are left unset for manual review.
usage: python video/notion/publish_notion.py [--dry]
Needs NOTION_API_TOKEN and NOTION_API_VERSION in the environment (the "notcrawl" integration).
"""
import json, math, mimetypes, os, pathlib, re, sys, time
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
A = ROOT / "video/notion/assets"
DATA_SOURCE = "6ffedb27-f124-8259-8a40-075b8e5a4993"          # Projects
AUTHOR = "b036f7f6-95a9-4f97-b3b5-c46867d0d103"               # Travis
SLUG = "slow-it-down-ai-safety-parody"
ORIGINAL_YT = "https://www.youtube.com/watch?v=yPwkzdYN4JE"
PAGES = {"doom": "3e5edb27-f124-8008-84cd-defb16b57151", "cultural": "3ddedb27-f124-8105-9885-e955643ddaf0",
         "pdoom": "3ddedb27-f124-8114-a98e-d3835e961d1e", "margin": "3ddedb27-f124-81c1-a145-c3d546904768",
         "pluribus": "3ddedb27-f124-8186-b064-c993b8e155c6"}
DRY = "--dry" in sys.argv

S = requests.Session()
S.headers.update({"Authorization": f"Bearer {os.environ['NOTION_API_TOKEN']}", "Notion-Version": os.environ.get("NOTION_API_VERSION", "2026-03-11")})
def api(method, path, **kw):
    for k in range(4):
        r = S.request(method, f"https://api.notion.com/v1/{path}", timeout=180, **kw)
        if r.status_code in (429, 502, 503, 504) and k < 3: time.sleep(2 + 4 * k); continue
        if r.status_code >= 300: raise RuntimeError(f"{method} {path}: {r.status_code} {r.text[:600]}")
        return r.json()

# ---------------------------------------------------------------- uploads
def upload(path, name=None):
    name = name or path.name
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    size, PART = path.stat().st_size, 10 * 1024 * 1024
    def send(url, payload, part=None):
        for k in range(4):
            try:
                r = S.post(url, files={"file": (name, payload, ctype)}, data={"part_number": str(part)} if part else None, timeout=900)
                if r.status_code < 300: return
                if k == 3: raise RuntimeError(f"send {name} part {part}: {r.status_code} {r.text[:400]}")
            except requests.RequestException:
                if k == 3: raise
            time.sleep(3 + 5 * k)
    if size <= 20 * 1024 * 1024:
        fu = api("POST", "file_uploads", json={"mode": "single_part", "filename": name, "content_type": ctype})
        send(fu["upload_url"], path.read_bytes())
    else:
        n = math.ceil(size / PART)
        fu = api("POST", "file_uploads", json={"mode": "multi_part", "number_of_parts": n, "filename": name, "content_type": ctype})
        with open(path, "rb") as f:
            for i in range(1, n + 1):
                send(fu["upload_url"], f.read(PART), part=i); print(f"   {name}: part {i}/{n}", flush=True)
        api("POST", f"file_uploads/{fu['id']}/complete")
    print(f"uploaded {name} ({size / 1e6:.1f} MB)", flush=True)
    return fu["id"]

# ---------------------------------------------------------------- blocks
TOKEN = re.compile(r"(@\[[^\]]+\]\(page:[a-z]+\)|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
def rt(s):
    """Inline markdown -> rich text: **bold**, *italic*, `code`, [text](url), @[Title](page:key) mentions."""
    out = []
    for part in TOKEN.split(s):
        if not part: continue
        ann = {}
        if part.startswith("@["):
            key = re.search(r"\(page:([a-z]+)\)", part).group(1)
            out.append({"type": "mention", "mention": {"type": "page", "page": {"id": PAGES[key]}}}); continue
        link = None
        if part.startswith("[") and "](" in part: text, link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part).groups()
        elif part.startswith("**"): text, ann = part[2:-2], {"bold": True}
        elif part.startswith("`"): text, ann = part[1:-1], {"code": True}
        elif part.startswith("*") and len(part) > 2: text, ann = part[1:-1], {"italic": True}
        else: text = part
        obj = {"type": "text", "text": {"content": text, **({"link": {"url": link}} if link else {})}}
        if ann: obj["annotations"] = ann
        out.append(obj)
    return out
def blk(kind, body): return {"object": "block", "type": kind, kind: body}
def p(s): return blk("paragraph", {"rich_text": rt(s)})
def h2(s): return blk("heading_2", {"rich_text": rt(s)})
def h3(s): return blk("heading_3", {"rich_text": rt(s)})
def bullet(s, kids=None): return blk("bulleted_list_item", {"rich_text": rt(s), **({"children": kids} if kids else {})})
def num(s, kids=None): return blk("numbered_list_item", {"rich_text": rt(s), **({"children": kids} if kids else {})})
def divider(): return blk("divider", {})
def callout(s, emoji): return blk("callout", {"rich_text": rt(s), "icon": {"type": "emoji", "emoji": emoji}, "color": "gray_background"})
def toggle(s, kids): return blk("toggle", {"rich_text": rt(s), "children": kids})
def code(s): return blk("code", {"rich_text": [{"type": "text", "text": {"content": s}}], "language": "plain text"})
def media(kind, fid, cap): return blk(kind, {"type": "file_upload", "file_upload": {"id": fid}, "caption": rt(cap)})
def youtube(url, cap): return blk("video", {"type": "external", "external": {"url": url}, "caption": rt(cap)})

STYLE = ("Late-night club slow jam, 2013 hip-hop R&B, a sensual anti-EDM grind record for the DJ to slow the party down. Sparse and warm: "
         "booming 808 kick and sub bass, soft claps on the backbeat, minimal percussion, dark warm synth pads, 61.5 BPM, A major. Big wide "
         "polished radio mix, airy reverb on the vocals. Light Auto-Tune, laid-back behind the beat. Smooth falsetto R&B lead with stacked "
         "male harmonies and \"ahoo\" ad-libs; chanted chorus hook is call-and-response: lead sings \"slow it down\", stacked male harmonies "
         "echo \"down down down, down down down\". Laid-back NY rap feature. Sexy, confident, sensual, seductive, explicit.")
EXCLUDES = "EDM, trap hi-hat rolls, rock, female vocals, fast tempo, ticking, clock, metronome, hi-hat rolls, trap hi-hats"
LYRICS = """[Intro]
(Oh-oh-oh-oh-oh-oh, yo-oh, yo-oh, yo-oh)

[Verse 1]
Candlelit dinner with the Don, I told him take it slow (ahoo)
While they drop a new model every eighteen days or so (ahoo)
You know when it's a test, ooh baby, you bad (ahoo)
Enough of that, lemme see that LOSS DROP

[Pre-Chorus]
I'm here to see the training stop
She's self-improving on me... DJ Moloch, you know you wrong
Enough with the motherfuckin' ARMS RACE

[Rap Verse - laid-back male rapper]
Everybody know slow AGI, way better than no AGI"""

def content(f):
    return [
        media("video", f["video"], "video created by claude opus 5.5; song made with suno v6"),
        divider(),
        h2("AI safety has a branding problem"),
        p("On Sept 13, the WSJ ran this headline: **“Biggest AI Rivals Agree They Need to Slow It Down.”** That’s also the title of a 2013 R&B slow jam."),
        p("Meanwhile, the labs keep saying they want to “pace” AI progress, because “slow” sounds like losing. That’s AI safety’s branding problem in a nutshell: slowing down sounds weak, and racing sounds sexy."),
        p("So I tried to flip it and make slowing down sexy."),
        p("THE-DREAM’s “Slow It Down” is literally a guy begging the club DJ to stop playing fast dance songs so he can actually get close to someone. It barely needed rewriting:"),
        youtube(ORIGINAL_YT, "The original: THE-DREAM feat. Fabolous, “Slow It Down” (2013)"),
        h2("Welcome to Club Frontier"),
        p("**DJ Moloch** (race dynamics, personified) keeps cranking the BPM while a new model drops every 18 days. **THE-DARIO** walks in wearing his shawl cardigan and asks the DJ to slow it down. The frontier model is the woman on the dance floor, with a few subtle android tells. **DADDY SAMA** takes the feature verse (*“everybody know slow AGI, way better than no AGI”*), and Winnie the Pooh shows up at the bar tryna distill all your honey."),
        p("Every chorus is the same slow dance, a little closer each time, until the whole club moves as one: *now we’re aligned*."),
        p("My rule for these: **let the headline misbehave; make the mechanism behave.** The jokes are outrageous, but the facts underneath are real, including every little footnote that pops up in the video."),
        p("It’s part of a series of AI safety projects, alongside @[Doom or Bloom](page:doom), @[Cultural Alignment](page:cultural), @[P(DOOM)](page:pdoom), and the AI-made parodies @[Margin Call](page:margin) and @[Pluribus](page:pluribus)."),
        h2("How it was made"),
        p("Claude Code with **Opus 5.5** made nearly all of it: the lyric rewrites, the audio experiments, the storyboard, every image and video prompt, the caption compositor, and the review tool. My job was taste and feedback. Start to finish took about a day of back-and-forth and ~$100 of fal credits."),
        p("The final pipeline:"),
        num("**Lyrics.** Rewritten line by line against the original’s rhymes and syllable counts."),
        num("**Song.** Suno V6, from text only: tagged lyrics plus a detailed style prompt. Of three takes, we kept the one that got the most lyrics right."),
        num("**Timing.** Local Whisper word timestamps aligned to the lyrics, plus a beat grid, so every word has a timestamp."),
        num("**Storyboard.** 70 shots, each anchored to a lyric line, each with an image prompt and a motion prompt."),
        num("**Characters.** One reference image per character, and one outfit each, iterated until they looked right."),
        num("**Keyframes.** One still per shot with Nano Banana Pro, conditioned on the character refs."),
        num("**Clips.** Veo 3.1 Fast image-to-video, with first + last frames for shots that have to land somewhere specific. Wan 2.2 for the shots Veo refused."),
        num("**Compositing.** A local Python + ffmpeg/libass pipeline for in-world neon captions (the backing vocals’ “down, down, down” literally steps down the screen), footnotes, color grades, letterboxing, and grain."),
        num("**Review.** A local scene-by-scene review tool (below). Five versions until it felt done."),
        num("**Poster.** Six first-frame options, since X shows a video’s first frame as its preview."),
        media("image", f["storyboard"], "All 70 shots, each anchored to a lyric line, a start time, and a color grade."),
        h3("The feedback loop"),
        p("The most useful thing we built was a scene-by-scene review tool. Every shot gets its keyframe, the clip as it plays in the cut, the raw generation, and in-context playback, plus **Keep / Tweak / Redo** and a notes box. My notes save to a file that Claude reads back as the next round of prompts."),
        media("image", f["review"], "My real note on the Pooh shot. The next version came straight from it."),
        h3("Tools I used"),
        bullet("**Claude Code (Opus 5.5):** director, producer, editor, and all of the code."),
        bullet("**Suno V6:** the song."),
        bullet("**fal:** Nano Banana Pro for character refs and keyframes, Veo 3.1 Fast for video, Wan 2.2 for the shots Veo wouldn’t touch, and OmniHuman 1.5 for Sam’s two rap close-ups."),
        bullet("**Local:** mlx-whisper for word timings, beat_this for the beat grid, audio-separator to pull the rap vocal for lip-sync, and ffmpeg + libass for captions and grading."),
        h3("Tried and discarded"),
        callout("Everything below was tried and thrown away. None of it made it into the final video.", "🗑️"),
        bullet("**ElevenLabs Music:** sang its own melody, not the song."),
        bullet("**ElevenLabs Voice Changer:** dropped an octave and drifted off-key on anything sung."),
        bullet("**ElevenLabs TTS v3 + Voice Design:** a designed voice for the rap verse."),
        bullet("**MiniMax Music 2.6 and 3:** wrote new songs, not ours."),
        bullet("**ACE-Step** (text-to-music, inpainting, and lyric editing): lyric editing came closest because it keeps the original singer, but two hook lines refused to change in every single take."),
        bullet("**Google Lyria 3.5 + Seed-VC:** Lyria sang the new lines and Seed-VC re-voiced the original refrain. It still didn’t feel like the song."),
        bullet("**Tencent AuK:** word-level vocal edits. The demo’s daily quota ended that experiment."),
        bullet("**Singing over the original’s instrumental** (split with BS-RoFormer and MelBand-RoFormer): none of the AI vocals layered on top came close to the real thing, and Suno and ElevenLabs both refused uploads of the original anyway."),
        bullet("**Lip-syncing Dario** (OmniHuman 1.5): it worked, but I cut every one of those shots in review."),
        bullet("**Kling v3:** refused the Trump dinner shot too."),
        bullet("**Models tested and not used:** Seedream 5, GPT Image 2.5, Qwen Image 3, Kling O3, Meta’s Muse Image, and Nano Banana 2 for images; Seedance 2.5 and Wan 3.0 for video."),
        bullet("**Two whole visual styles:** a Pixar-ish 3D look (too generic) and a neon-heavy cyberpunk look (way too purple)."),
        h2("How it came together"),
        p("The short version of a lot of trial and error:"),
        num("**Concept + lyrics.** Club Frontier, DJ Moloch, and THE-DARIO feat. DADDY SAMA, rewritten line by line against the original’s rhymes and syllables."),
        num("**Audio round 1: rejected.** ElevenLabs Music, MiniMax, and ACE-Step all wrote their own melodies. The only part I liked was the original singer leaking through an ACE-Step inpaint.",
            [media("audio", f["round1"], "Round 1 · ElevenLabs Music: a good singer, the wrong song.")]),
        num("**Round 2: rejected.** Lyria 3.5 sang the new lines, and Seed-VC re-voiced the original refrain into Lyria’s singer. Still not it.",
            [media("audio", f["round2"], "Round 2 · Lyria 3.5 lines + the original refrain, re-voiced with Seed-VC.")]),
        num("**Rounds 3–5: closest, still no.** ACE-Step’s lyric-edit mode kept the original recording and just swapped the words. But that meant the original singer’s voice, and two hook lines refused to change in every take.",
            [media("audio", f["round3"], "Round 3 · ACE-Step lyric edit on the original mix.")]),
        num("**Suno.** It blocked the original instrumental, so I went text-only: tagged lyrics plus a style prompt that describes the sound. One fix: every take had a ticking hi-hat, because the prompt literally said “ticking.”"),
        num("**Timing + storyboard.** Whisper word timestamps and a beat grid, then 70 shots mapped onto them."),
        num("**Three looks.** Stylized 3D was too Pixar. Painterly cyberpunk was way too purple. Restrained Blade Runner noir stuck.",
            [media("image", f["looks"], "The same cast in all three looks.")]),
        num("**Likeness.** Real people are recognizable caricatures, never photoreal. Dario took four passes before he actually looked like him.",
            [media("image", f["dario"], "THE-DARIO, v1 to final.")]),
        num("**Clips.** Veo refused the Trump dinner and the Pooh shot (Kling refused the dinner too), so those two went to Wan 2.2. Then the stern shadow behind Pooh kept growing bear ears, so the silhouette is locked with a composite.",
            [media("video", f["shadow"], "Outtake: the shadow grows bear ears."), media("image", f["pooh"], "The honey bear, try 1 to final.")]),
        num("**Five review rounds.** Captions moved off faces, a cold open got cut, the Dario lip-sync shots became dance shots, and one wand massager kept blowing smoke until we painted the haze out of its keyframe.",
            [media("video", f["wand"], "Outtake: Veo decided the wand should blow smoke."), media("video", f["lipsync"], "Cut in review: Dario lip-syncing (OmniHuman 1.5).")]),
        num("**Poster.** Six first-frame options, since X shows a video’s first frame as its preview. B won.",
            [media("image", f["posters"], "Poster options A–F. B is now the first frame of the video.")]),
        h2("What I learned"),
        bullet("**Stills are cheap, video is expensive.** Lock every composition as a keyframe (~15¢) before animating it (~60¢–$1.20 a clip)."),
        bullet("**Character refs are the whole game.** One reference image per character, one outfit each, passed into every keyframe."),
        bullet("**Likeness lives in the refs.** Name the real person when making the reference; describe, don’t name, them in the shot prompts."),
        bullet("**Use first + last frames when a shot has to land somewhere:** a kiss, a readable label."),
        bullet("**Composite anything that must not move.** Video models love to “improve” a silhouette."),
        bullet("**Different models refuse different things.** Veo wouldn’t animate the Trump dinner or the Pooh shot, and Kling wouldn’t do the dinner; Wan 2.2 did both."),
        bullet("**Say what you want, not what you don’t.** “Ticking” in a Suno prompt gets you ticking, and “no smoke” in a video prompt still gets you smoke."),
        bullet("**Scene-level feedback turns taste into prompts.** Anchoring every note to a shot and a timestamp made each revision cheap and specific."),
        bullet("**Budget:** ~$100 of fal credits for the visuals, across ~235 images and ~80 video clips over five versions."),
        h3("Suno: what worked"),
        p("Suno V6 made the song from text alone. The details, for anyone making their own parody:"),
        bullet("**No artist names in the style prompt.** Describe the era, tempo, key, instruments, and vocal style instead, and measure the tempo and key from the original."),
        bullet("**Section tags go on their own lines,** like `[Verse 1]` and `[Pre-Chorus]`. A delivery cue inside the tag switches the voice: `[Rap Verse - laid-back male rapper]`."),
        bullet("**Parentheses are backing vocals and ad-libs:** `(ahoo)` at the end of a line, and each backing answer on its own line."),
        bullet("**Shape the phrasing in the lyrics:** stretched vowels (`sloow`), `...` for a pause, and CAPS on one phrase for punch (`LOSS DROP`)."),
        bullet("**Spell words the way they should be sung.** We wrote “Meter” so it would pronounce METR, then fixed the spelling in the captions."),
        bullet("**Write every chorus out in full.** No `[Chorus x2]`."),
        bullet("**Settings I’d start with:** V6, male vocals, style influence ~70–80%, weirdness ~20–30%. Generate 4–8 takes and judge by ear."),
        bullet("**What didn’t work:** Suno fingerprints uploads, so it blocked the original instrumental, and it checks lyrics against a lyrics database. And the word “ticking” in my style prompt put a ticking sound in every take."),
        toggle("The final style prompt", [code(STYLE)]),
        toggle("Exclude styles", [code(EXCLUDES)]),
        toggle("Lyric formatting example", [code(LYRICS)]),
        divider(),
        p("*Parody. Not affiliated with any lab, artist, or head of state.*"),
    ]

PROPS = {
    "Name": {"title": [{"type": "text", "text": {"content": "Slow It Down — AI Safety Parody"}}]},
    "Description": {"rich_text": [{"type": "text", "text": {"content": "Dario asks DJ Moloch to slow it down in this AI-made R&B parody."}}]},
    "Slug": {"rich_text": [{"type": "text", "text": {"content": SLUG}}]},
    "Tags": {"multi_select": [{"name": "AI"}, {"name": "Video"}, {"name": "Projects"}]},
    "Author": {"people": [{"object": "user", "id": AUTHOR}]},
}

if __name__ == "__main__":
    existing = api("POST", f"data_sources/{DATA_SOURCE}/query", json={"filter": {"property": "Slug", "rich_text": {"equals": SLUG}}})["results"]
    if existing:
        sys.exit(f"a page with slug {SLUG} already exists: {existing[0]['url']} (not creating a duplicate)")
    files = {"cover": A / "cover.jpg", "video": ROOT / "video/build/slow_it_down_share_v5.mp4", "storyboard": A / "storyboard.jpg",
             "review": A / "review-tool.png", "round1": A / "round1-elevenlabs-music.mp3", "round2": A / "round2-lyria-plus-seedvc.mp3",
             "round3": A / "round3-ace-step-lyric-edit.mp3", "looks": A / "looks.jpg", "dario": A / "dario.jpg", "shadow": A / "outtake-shadow-grows-ears.mp4",
             "pooh": A / "pooh.jpg", "wand": A / "outtake-wand-blows-smoke.mp4", "lipsync": A / "outtake-lipsync-cut.mp4", "posters": A / "poster-options.jpg"}
    for k, v in files.items(): assert v.exists(), v
    if DRY:
        blocks = content({k: "dry-run" for k in files}); print(len(blocks), "top-level blocks;", sum(len(json.dumps(b)) for b in blocks) // 1024, "KB of JSON"); sys.exit()
    ids = {k: upload(v, name="slow-it-down.mp4" if k == "video" else None) for k, v in files.items()}
    blocks = content(ids)
    page = api("POST", "pages", json={"parent": {"type": "data_source_id", "data_source_id": DATA_SOURCE}, "icon": {"type": "emoji", "emoji": "🎬"},
                                      "cover": {"type": "file_upload", "file_upload": {"id": ids["cover"]}}, "properties": PROPS, "children": blocks[:90]})
    for i in range(90, len(blocks), 90):
        api("PATCH", f"blocks/{page['id']}/children", json={"children": blocks[i:i + 90]})
    (ROOT / "video/notion/page.json").write_text(json.dumps({"id": page["id"], "url": page["url"]}, indent=1))
    print("created", page["url"], "with", len(blocks), "top-level blocks")
