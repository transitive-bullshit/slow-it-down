# 01 — Song anatomy: "Slow It Down" (THE-DREAM ft. Fabolous, 2013)

Source: `audio/original/slow-it-down.mp3` (4:16, 192 kbps). Measured from the audio. Beat tracking used *beat_this*, stems came from BS-RoFormer, and word timings from Whisper large-v3-turbo on the isolated vocal. Machine-readable version: `analysis/song-map.json`, `analysis/grid.json`, `analysis/vocal_lines_raw.json`.

> **Why there are no original lyrics in this doc.** They're copyrighted, so I'm not reprinting them. Everything a parody needs to fit the song is here instead: sections, bar positions, entry points, syllable counts, rhyme schemes, and what each line is about (paraphrased). Keep the Genius page open next to this if you want the text: https://genius.com/The-dream-slow-it-down-lyrics

## The numbers

| | |
|---|---|
| Tempo | **61.5 BPM** half-time feel (the programmed grid is **123.0 BPM**). Rock-steady: 98.6% of detected beats sit on a fixed grid (±10 ms). |
| Meter | 4/4. Kick on beat 1 confirms the bar phase. |
| Bar length | 3.902 s at 61.5 BPM. Bar 1 starts at 0:00.227. |
| Key | **A major** (relative F♯ minor). The refrain melody stays in a narrow A3–E4 range around the tonic. |
| Length | 4:16.1, about 65.5 bars |
| Credits | Written by Terius Nash (The-Dream) and John Jackson (Fabolous). Produced by The-Dream, mixed by Jaycen Joshua. Premiered Feb 14, 2013; peaked at #24 on Billboard Hot R&B Songs. **No official instrumental exists**, so ours is extracted. songbpm lists 123 BPM, F♯ minor (the relative minor of A, same key signature). |
| 2013 video | Directed by Motion Family: a retro late-'50s/early-'60s house party split in two. It ends with two 1960s Mustangs lined up for a night drag race. A ready-made AI-race callback, see the creative doc. |
| Context | Lead single from *IV Play* (a pun on "foreplay"; single out March 2013, album May 28, 2013). Produced and written by The-Dream. **The song is a complaint to the club DJ: enough fast EDM "dance songs," play something slow.** Verse 1 also takes a shot at artists whose labels made them cut dance records. |

## Form (61.5-BPM bars)

| # | Section | Bars | Time | Performer | Shape |
|---|---|---|---|---|---|
| 1 | Intro chant | 1–4 (4) | 0:00 – 0:16 | Dream | Wordless "oh-oh / yo-oh" chant over the groove |
| 2 | Intro verse | 5–12 (8) | 0:16 – 0:47 | Dream | 8 lines, one per bar. Two quatrains, rhymed AAAA / BBBB |
| 3 | Pre-hook 1 | 13–16 (4) | 0:47 – 1:03 | Dream | "I'm here to see…" ×3 anaphora, then the call-out to the DJ |
| 4 | **Hook 1** | 17–24 (8) | 1:03 – 1:34 | Dream | 4 × 2-bar units + tag |
| 5 | Verse 1 | 25–32 (8) | 1:34 – 2:05 | Dream | 11 lines. The "labels forced others into dance records" verse |
| 6 | Pre-hook 2 | 33–36 (4) | 2:05 – 2:21 | Dream | Same as pre-hook 1 |
| 7 | **Chorus 2** | 37–44 (8) | 2:21 – 2:52 | Dream | Same as hook 1 |
| 8 | Verse 2 (rap) | 45–52 (8) | 2:52 – 3:23 | Fabolous | 16 bars of rap, 2 lines per bar. The last quatrain repeats the third. |
| 9 | **Hook 3** | 53–60 (8) | 3:23 – 3:54 | Dream | Hook with ad-lib variations |
| 10 | Outro | 61–65 (5) | 3:54 – 4:16 | Dream | Reprise of intro lines 5–8, then a spoken one-word DJ cue (~4:10) and a tail |

Vocals enter with pickups, so each section's first line starts a beat or two before the bar line listed above. Exact entry points are in the tables below.

## The refrain: the part that has to be identical

Each hook is **four 2-bar units**. Every unit has the same skeleton (positions in 61.5-BPM beats):

```
bar N     beat 3¾ ──── "(DJ) you gotta slow it"        pickup, 6 syl (8 with "DJ")
bar N+1   beat 1  ──── DOWN                             lands on the downbeat
          1½, 2½, 3 ── down · down · down
          3½ … 4½ ──── down · down                      loose; floats differently every time
bar N+2   beat 1  ──── DOWN                             7 "downs" in total
          1¼ – 3½ ──── ANSWER LINE                      the only words that change per unit
          3½ ──────── next pickup begins
```

The answer lines in the four units run **12 / 10 / 6 / 5 syllables**. Units 1 and 2 both end on the same tag word, and units 3 and 4 rhyme with each other. A 7-syllable "DJ… slow it" tag plus an "ahoo" ad-lib closes each hook. **For the parody, the pickup and the seven "downs" stay exactly as they are. We only rewrite the four answer lines.**

## Line map, with the originals paraphrased

Times are line onsets (±0.1 s). "Entry" is bar.beat at 61.5 BPM. Syllable counts are for the original line.

### Intro verse (bars 5–12)
The-Dream enters just after beat 2 of every bar and tags each line with an "ahoo" ad-lib.

| ID | Time | Entry | Syl | Rhyme | What it says |
|---|---|---|---|---|---|
| I1 | 0:17.1 | 5.2¼ | 14 | A (long O) | Mainstream radio won't play this… |
| I2 | 0:21.1 | 6.2½ | 13 | A | …but a certain crowd will dance to it anyway |
| I3 | 0:25.2 | 7.2½ | 13 | A | He'll keep riding this beat |
| I4 | 0:29.0 | 8.2½ | 14 | A | He'll keep throwing money until she dances low |
| I5 | 0:33.1 | 9.2¾ | 11 | B (short A, "-ad") | Being real with her: she's "bad" (fine) |
| I6 | 0:36.7 | 10.2¼ | 11 | B | Compares her to a famous 80s pop song about being "bad" |
| I7 | 0:40.5 | 11.2¼ | 12 | B | If she were his and left, he'd be sad |
| I8 | 0:44.5 | 12.2¼ | 9 | B | Enough talk: he wants to watch her dance (explicit) |

### Pre-hook (bars 13–16, pickup at 12.4¾)

| ID | Time | Entry | Syl | Rhyme | What it says |
|---|---|---|---|---|---|
| P1 | 0:46.7 | 12.4¾ | 7 | A ("-op/-ock") | "I'm here to see…" a dance move |
| P2 | 0:48.7 | 13.2¾ | 7 | A | "I'm here to see…" a second move |
| P3 | 0:50.6 | 13.4¾ | 12 | A | The longest line; lands on the drop |
| P4 | 0:54.6 | 14.4¾ | 7 | — | She's grinding on him… |
| P5 | 0:56.1 | 15.2¼ | 6 | B | …so he calls out the DJ |
| P6 | 0:58.1 | 15.4¼ | 10 | B | Enough with the (expletive) dance songs |

### Hook (bars 17–24, pickup at 16.3¾)

| Unit | Pickup | Answer line | Syl | Rhyme | What the answer says |
|---|---|---|---|---|---|
| 1 | 1:01.4 | 1:06.9 | 12 | A (tag word) | So she can take her time dancing on him |
| 2 | 1:09.1 | 1:14.7 | 10 | A (same tag word) | Whispering in her ear while she dances on him |
| 3 | 1:17.3 | 1:22.8 | 6 | B ("-ight") | Sway left, sway right |
| 4 | 1:24.9 | 1:31.3 | 5 | B | That's what she likes |
| Tag | 1:32.9 | — | 7 | — | "DJ… slow it" + ahoo |

### Verse 1 (bars 25–32, pickup at 24.4½)

| ID | Time | Entry | Syl | Rhyme | What it says |
|---|---|---|---|---|---|
| V1 | 1:33.5 | 24.4½ | 10 | A ("-air") | She's rolling her body, hair flying |
| V2 | 1:38.3 | 26.1½ | 10 | A | In slow motion, and everyone stares |
| V3 | 1:41.8 | 27.1 | 11 | B (loose) | The view from the side |
| V4 | 1:45.2 | 27.4½ | 6 | B ("-ack") | Back-and-forth motion |
| V5 | 1:47.3 | 28.2¾ | 7 | B ("-at") | "Where do they do this?" |
| V6 | 1:50.6 | 29.2¼ | 6 | — | He's loyal to her… |
| V7 | 1:52.2 | 29.3¾ | 5 | C ("-out") | …and will never sell out |
| V8 | 1:53.9 | 30.1½ | 12 | — | Other artists had to make a dance record… |
| V9 | 1:55.8 | 30.3½ | 9 | C ("-out") | …or their label wouldn't put it out |
| V10 | 1:57.7 | 31.1½ | 12 | D ("-oo") | He'll never put record sales before her |
| V11 | 2:01.5 | 32.1¼ | 9 | D | Keep doing what you're doing |

### Verse 2: the Fabolous rap (bars 45–52, pickup at 44.4¼)
Each line enters on the "and" of beat 2 or beat 4 and puts its stressed syllable on the next downbeat.

| ID | Time | Syl | Rhyme | What it says |
|---|---|---|---|---|
| F1 | 2:51.3 | 8 | A (repeated end word) | Everyone knows slow money… |
| F2 | 2:53.5 | 7 | A | …beats no money |
| F3 | 2:55.4 | 8 | — | Except for people who don't get it… |
| F4 | 2:57.3 | 9 | A | …who understand neither women nor money |
| F5 | 2:59.3 | 6 | B ("-ool/-ooh") | At first he plays it cool… |
| F6 | 3:01.3 | 9 | C ("-unny") | …hanging out, being funny… |
| F7 | 3:03.2 | 10 | B | …then suddenly he's a honey-loving cartoon bear… |
| F8 | 3:05.2 | 8 | C | …going after her "honey" |
| F9 | 3:07.1 | 5 | D ("-it") | Her slim-fit pants… |
| F10 | 3:09.1 | 6 | D | …the room's dim lighting… |
| F11 | 3:11.0 | 8 | — | …his hands on her… |
| F12 | 3:13.0 | 9 | D | …a name-drop of a 90s R&B/rap pair (explicit) |
| F13–16 | 3:15.0 – 3:22.7 | 5/6/8/9 | D | Exact repeat of F9–F12. **In the parody this is a free slot for a new punchline.** |

### Hook 3 (bars 53–60, pickup at 52.4½) and outro (bars 61–65)
Hook 3 uses the same skeleton, with more ad-libs layered over it. The outro reprises I5–I8 at 3:56.3, 3:59.8, 4:03.7 and 4:07.6 (11/11/12/9 syllables). The-Dream then speaks a one-word DJ cue at about 4:10, and the instrumental tail runs to 4:16.

## Voices: lead vs backups (call-and-response)

Confirmed with a karaoke lead/backing separation (BS-RoFormer karaoke by frazer-becruily). Per-bar map: `analysis/voice-map.json`. Stems: `audio/stems/karaoke/`. The lead is mixed centre, and the stacked backing voices are mostly wide. **The backups only ever sing refrain words and vocables** (the intro chant, the "ahoo" tags, and the "downs"). So the entire backing arrangement can be kept note-for-note and re-voiced into the new lead's timbre.

| Section | Who does what |
|---|---|
| Intro verse, verse 1, outro | **Lead sings each line, and the stacked backups answer with the "ahoo" tag.** The tag spills across beats 1½–2½ of the next bar, just before the next lead line enters. This is the back-and-forth. |
| Pre-hooks | Mostly lead, with a few stacked accents |
| Hooks 1–2 | **Lead calls, backups answer.** The lead sings the "(DJ) you gotta slow it down" pickup. The **stacked backups sing the six answering "downs"**, which fill the whole bar. The lead comes back with the answer line (the first one is doubled or stacked). |
| Verse 2 (rap) | Fabolous solo, centre, no backups |
| Hook 3 | All centred. The lead appears to **ad-lib and riff over the final hook** rather than restate it. Whisper hears different words there. |

**What this means for the parody:**
- The "downs" are the backups' part. In the video, **the FOOM Fatales, the temptresses themselves, sing "down, down, down"** back to Dario as they slow down.
- The "ahoo" tags stay as the backups' signature response.
- Hook 3's ad-lib space is where the coordination jokes go: *(Sam, you too… Demis, you too…)*.
- For production, the refrain needs a real stack (3–6 voices) behind a single lead.

## Performance traits worth copying

- **Laid-back entries.** Sung lines start after the backbeat, not on it. Keep that lazy, behind-the-beat feel.
- **"Ahoo" ad-libs** end almost every intro and verse line. It's a wordless signature, so the new vocalist can keep an equivalent.
- **Stacked "downs."** The refrain is doubled and harmonized, and the stem split removes all of that, so the new vocal has to rebuild the stack.
- **The rap feature changes the texture.** It's a conversational, punchline-driven NY flow (2 lines per bar), a deliberate contrast with the melismatic hook.
- **Hooks are identical,** which is what makes the song easy to sing along to. The parody should keep hooks 1 and 2 identical and save any twist for hook 3.

## Structural gifts for the parody

1. **The premise transfers directly.** "DJ, enough with the dance songs, slow it down" becomes "Moloch, enough with the race, slow it down."
2. **Verse 1 already mocks commercial pressure.** "Other artists had to make dance records or the label wouldn't release them" becomes "other *labs* had to ship race models or their *backers* wouldn't fund them." "Label" and "lab" are one syllable apart.
3. **The album title is *IV Play*.** The joke writes itself: ***ASL-IV Play***.
4. **Fabolous's thesis, "slow money beats no money," is Dario's essay in one line:** slow AGI beats no AGI. Pacing isn't pausing.
5. **The rap verse's bear-and-honey couplet** is a ready-made hook for the China/distillation argument.
6. **The final spoken DJ cue** can become "(pause)", followed by a tape-stop to silence.
