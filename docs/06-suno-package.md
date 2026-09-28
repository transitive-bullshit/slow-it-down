# 06 — Suno package (what we used for the final audio, and what we learned)

The final track is the user's own **Suno V6** generation, take B of three (`video/audio/suno_B.wav`). Suno kept our section structure almost exactly, and take B had the best lyric accuracy: a Whisper transcript matched 77% of the script's words in order.

## Files
- `docs/lyrics-suno.txt` is the Suno-formatted lyrics, pasted as-is. It's the version the final take was generated from.
- `docs/lyrics-current.txt` holds the same lyrics without Suno formatting.

## Style prompt (final, after the ticking fix)
```
Late-night club slow jam, 2013 hip-hop R&B, a sensual anti-EDM grind record for the DJ to slow the party down. Sparse and warm: booming 808 kick and sub bass, soft claps on the backbeat, minimal percussion, dark warm synth pads, 61.5 BPM, A major. Big wide polished radio mix, airy reverb on the vocals. Light Auto-Tune, laid-back behind the beat. Smooth falsetto R&B lead with stacked male harmonies and "ahoo" ad-libs; chanted chorus hook is call-and-response: lead sings "slow it down", stacked male harmonies echo "down down down, down down down". Laid-back NY rap feature. Sexy, confident, sensual, seductive, explicit.
```
If the field is short:
```
Hip-hop R&B slow jam, 2013, 61.5 BPM half-time, A major, 808s, claps, synth pads, sultry male tenor, falsetto, stacked harmonies, call-and-response hook, laid-back NY rap verse, explicit
```
**Exclude styles:** `EDM, trap hi-hat rolls, rock, female vocals, fast tempo, ticking, clock, metronome, hi-hat rolls, trap hi-hats`

**Variant to try if the singer drifts** (voice-first; its hi-hat mention is removed):
```
Hip-hop R&B slow jam, 2013. Male R&B tenor who lives in his falsetto: breathy, silky, melismatic runs, conversational sung verses that enter just after the backbeat, a howled "ahoo" ad-lib closing almost every line. He stacks his own voice into tight three-part harmonies for the hook and answers himself. Light Auto-Tune sheen, close-mic intimacy. 61.5 BPM half-time, A major, minimal 808s, claps, warm pads. Guest verse by a relaxed, punchline-heavy New York rapper, two lines per bar. Seductive, playful, explicit.
```

**Rules for writing the prompt:**
- **No artist or song names.** Suno rejects them, so describe the sound instead: era, tempo, key, instruments, and the vocal character.
- **Measure tempo and key from the reference track.** Don't guess them.
- **Write out the hook's call-and-response inside the style prompt.** Say who sings the call and who answers.

## Lyric formatting that worked (V6)
- **Section tags on their own lines:** `[Intro]` `[Verse 1]` `[Pre-Chorus]` `[Chorus]` `[Verse 2]` `[Rap Verse - laid-back male rapper]` `[Outro]` `[End]`. This had the biggest effect on song form. Putting a delivery cue inside the tag (the rap one) switched voice and delivery for that section.
- **Parentheses are backing vocals and ad-libs:**
  - A line-end `(ahoo)` gives the lead's signature ad-lib, like `...I told him take it slow (ahoo)`.
  - The backing answer goes on its own line after the lead line, in parentheses, repeated once per answer.
  - The wordless intro chant is also in parentheses: `(Oh-oh-oh-oh-oh-oh, yo-oh, yo-oh, yo-oh)`.
- **Stretched vowels shape the phrasing:** `sloow`, `slooow`, `Ohhh` for a held note.
- **`...` marks a pause:** `Just steer it left... steer it right`.
- **CAPS give punch to a single phrase, used sparingly:** `lemme see that LOSS DROP`, `Enough with the motherfuckin' ARMS RACE`.
- **Spell words the way they should be sung:** `Meter` for METR, `exfill'ed`. Fix the spelling in the captions afterwards.
- **Repeats:** write every chorus out in full each time, word for word. Don't use `[Chorus x2]`.

## Settings (recommended; the user's exact slider values weren't recorded)
- Model V6, Vocal Gender **Male**.
- Style Influence **~70–80%**, Weirdness **~20–30%**.
- Generate 4–8 takes per prompt and judge by ear. Voice and flow vary a lot between takes.
- When a take nails the singer, save it as a **Persona** and generate from it after that.
- Fix single lines with **Replace Section** instead of rerolling the whole song.

## What didn't work, and why
- **Uploading the original instrumental.** Suno fingerprints uploads against known recordings and blocked ours. Suno also checks lyrics against a lyrics database, so long verbatim runs of the original lyrics can get blocked. The final take was generated from text only.
- **The ticking sound in every take.** The prompt said "very subtle ticking double-time hi-hats at 123 BPM". Suno took "ticking" literally, and "double-time hi-hats" plus "123 BPM" gave constant 16th-note hats; "hypnotic" made it loop. The fix was to remove every hi-hat, tempo-doubling and ticking word and to add the exclusions above. If a faint tick survives, add "no hi-hats" to the style text.
- **Before Suno** (see `docs/04-audio-plan.md`): the user rejected ElevenLabs Music, MiniMax, ACE-Step inpainting and Lyria layering. ElevenLabs' uploaded-audio edit also rejected the clip as copyrighted.
