# 04 — Audio plan (audio-only pass first)

## Already done

| Asset | File | Notes |
|---|---|---|
| Original, lossless copy | `audio/original/slow-it-down.wav` | 4:16. Integrated loudness **-14.2 LUFS**, LRA 2.1 LU. |
| **Instrumental v1** | `audio/stems/instrumental_bsroformer.wav` | BS-RoFormer (Viperx 1297). -18.2 LUFS, so the vocals carried about 4 LU of the loudness. |
| Reference vocal | `audio/stems/vocals_reference_bsroformer.wav` | Used as the timing and melody guide only. |
| Instrumental v2 | `audio/stems/instrumental_melband_inst_v2.wav` | Unwa MelBand-RoFormer Inst v2. It's usually "fuller," but a crude bleed check (spectral correlation with the vocal in the 300 Hz–4 kHz band, hook 1) gives **v1 0.00 vs v2 0.10**, so v2 likely keeps more vocal ghosting. Decide by ear: `audio/previews/hook1_instrumental.mp3` vs `hook1_instrumental_v2.mp3`. |
| A/B previews | `audio/previews/hook1_{original,instrumental,vocals}.mp3` | Hook 1, 36 s |
| Tempo / bar grid | `analysis/grid.json`, `analysis/song-map.json` | 61.5 / 123.0 BPM, bar 1 = 0.227 s |

**Instrumental caveats.** Removing the vocals also removes every backing vocal, harmony and ad-lib, and the refrain is a stacked, harmonized part. The new vocal has to rebuild that stack. Listen for "ghost" bleed around the hook's sibilants. If either model leaves artifacts, an ensemble of the two, or a karaoke model on the leftovers, usually fixes it.

## A first test: ElevenLabs Voice Changer on the refrain

I converted the first refrain unit (0:61–0:67 of the reference vocal) with two ElevenLabs premade voices and measured the pitch of each result against the original (`audio/tests/`).

| Voice | Pitch contour correlation | Transposition | Frames within a semitone of the melody |
|---|---|---|---|
| Eric ("smooth") | 0.82 | dropped an octave | 51% |
| Brian ("deep") | 0.77 | about -17 semitones (off-key) | 5% |

**Takeaway:** ElevenLabs speech-to-speech keeps the rhythm and the shape of the melody, but it pulls everything toward the target's *speaking* range and drifts off-key. It's fine for spoken parts and probably the rap verse. It's **not good enough for the sung refrain as-is.** Sung parts need a pitch-preserving *singing* voice converter, or a real singer.

## Voice casting: three roles, not one

The original is a **lead plus a stacked backing group that answers him** (the "downs" and the "ahoo" tags), with a solo rap verse on top.

| Role | Sings | Recommendation |
|---|---|---|
| **Lead (THE-DARIO)** | Every line, the "slow it down" pickups, the hook 3 ad-libs | One original smooth R&B voice, consistent throughout |
| **Backups** | The six "downs" per unit, the "ahoo" tags, doubles on the first answer line | **Faithful option:** the lead voice multi-tracked into 3–6 layers with harmonies (that's how the original was made, so the refrain sounds the same). **Character option:** a female trio as the FOOM Fatales answering him. More drama, less like the original. **Hybrid:** faithful stacks on the "downs," Fatales on a few verse ad-libs. |
| **Rap feature (DADDY SAMA)** | Verse 2 | A contrasting laid-back rap voice. ElevenLabs Voice Changer is fine here because rap is speech-like. |

## Recommended vocal pipeline

1. **Cast an original "artist" voice.** No clone of Dario or The-Dream. Generate 4–6 short a cappella R&B candidates, then pick one:
   - Brief: "smooth, breathy male tenor, silky falsetto, late-2000s slow jam, intimate."
   - Tools: ElevenLabs Music or MiniMax Music 2.6 on fal, with vocals isolated; or ElevenLabs Voice Design.
   - The rap feature gets a second, contrasting voice (laid-back NY cadence).
2. **Record a guide vocal for the new lyrics.** A human sings the parody over the instrumental, with the original vocal in headphones. This is what gets the phrasing, the laid-back entries, and the exact "slow it down, down down down" feel.
   - Who: you, or a session R&B singer (roughly $100–300 on SoundBetter or AirGigs for a guide).
   - If a hired singer sounds great, we can simply keep their voice.
3. **Convert the guide to the artist voice with pitch preserved.** Run Seed-VC's singing model locally (fine on this M3 Pro for short sections), or RVC. Use ElevenLabs Voice Changer for the rap verse and spoken bits.
4. **Rebuild the stack and polish.**
   - Doubles and harmonies on the "downs."
   - The "ahoo" ad-libs.
   - A light Auto-Tune sheen, which matches the 2013 production.
   - Plate reverb plus a synced delay (a dotted 1/8 at 61.5 BPM is 366 ms).
   - De-essing.
5. **Mix and master** to about -14 LUFS integrated with a true peak of -1 dBTP, matching the original. I can script this pipeline in Python (pedalboard + pyloudnorm) for fast iteration, or export stems for Logic.

**Shortcut for the refrain.** Because the refrain lyrics don't change, we could convert *the original refrain performance itself* into the artist voice with a singing converter. That's guaranteed-identical phrasing. The tradeoff is that it uses more of the original recording (a performance, not just the beat), so the human-guide route is cleaner.

## No-human paths (experimental, worth one cheap test each)

- **ACE-Step inpaint (fal).** Mask one line of the original mix and re-sing it with new lyrics. It tends to imitate the surrounding voice and can alter the beat under the mask, so treat it as a *guide* generator, not the final vocal.
- **TTS + melody transplant.** Generate TTS for each parody line, time-warp it onto the original syllable grid, impose the original pitch contour (WORLD vocoder), then run singing voice conversion. It's fully automatic and will sound robotic, which the Auto-Tune aesthetic partly forgives.
- **Full-song generators** (MiniMax Music 3, ElevenLabs Music, Suno-style). These invent new melodies, so they break your "refrain exactly the same" requirement. Use them only for voice casting and ad-lib ideas.

## Cold-open "race" pre-roll (optional, 6–8 s)

- The same instrumental, time-stretched to about 2×, with a four-on-the-floor kick, a riser and a DJ Moloch hype drop.
- A turntable tape-stop (the literal sound of slowing down) then crashes into bar 1 of the real track.
- I can build this procedurally.

## Next experiments, cheapest first

1. **Seed-VC singing conversion** on the same refrain slice. Target: at least 90% of frames within a semitone.
2. **Voice casting board:** 4–6 generated R&B voices for you to pick from.
3. **Guide test:** you record the hook plus the intro verse on your phone. I convert and mix it over the instrumental, which gives the first real listen.
4. **ACE-Step inpaint** on one intro line, to see if an AI guide is viable.

## Practical note

Using the original instrumental master means YouTube Content ID will likely claim the video (usually monetization goes to the rights holder rather than a block). X is more lenient. Parody that comments on something other than the song itself gets weaker fair-use protection. This is not legal advice, just something to plan the distribution around.
