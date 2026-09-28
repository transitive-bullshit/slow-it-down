# Slow It Down – AI Music Video

> AI safety has a branding problem. Sometimes you just gotta slow it down, baby.

[![Slow It Down – AI Music Video](https://assets.cultural-alignment.com/personal-site/media/5a28d2e05504f914a9e2fa0935e3ccc7ff960b865aae0c8cfd1a91fcd682bffa.webp)](https://www.transitivebullsh.it/projects/slow-it-down-ai-music-video)

**[▶ Watch the video and read the write-up](https://www.transitivebullsh.it/projects/slow-it-down-ai-music-video)**

An AI-made R&B parody of THE-DREAM feat. Fabolous, “Slow It Down” (2013), made almost entirely by Claude Code with Opus 5.5, Suno, and fal. This repo is the whole working directory behind it.

## AI safety has a branding problem

On Sept 13, the WSJ ran this headline: **“Biggest AI Rivals Agree They Need to Slow It Down.”** That’s also the title of a 2013 R&B slow jam.

Meanwhile, the labs keep saying they want to [“pace” the frontier](https://www.pacingthefrontier.com/), because “slow” sounds too much like losing. That’s AI safety’s branding problem in a nutshell: slowing down sounds weak, and racing sounds more optimistic and inevitable.

So I wanted to try flipping this and make slowing down feel sexy.

THE-DREAM’s “Slow It Down” is literally a guy begging the club DJ to stop playing fast dance songs so he can actually get close to someone. It barely needed rewriting. ([Watch the original](https://www.youtube.com/watch?v=yPwkzdYN4JE))

## Welcome to Club Frontier

**DJ Moloch** (race dynamics, personified) keeps cranking the BPM while a new model drops every 18 days. **THE-DARIO** walks in wearing his shawl cardigan and asks the DJ to slow it down. The frontier model is the woman on the dance floor, with a few subtle android tells. **DADDY SAMA** takes the feature verse (*“everybody know slow AGI, way better than no AGI”*), and Winnie the Pooh shows up at the bar tryna distill all your honey.

Every chorus is the same slow dance, a little closer each time, until the whole club moves as one: *now we’re aligned*.

My rule for these: **let the headline misbehave; make the mechanism behave.** The jokes are outrageous, but the facts underneath are real, including every little footnote that pops up in the video.

It’s part of a series of recent AI safety projects, alongside [Doom or Bloom](https://www.transitivebullsh.it/projects/doom-or-bloom), [Cultural Alignment](https://www.transitivebullsh.it/projects/cultural-alignment), [P(DOOM)](https://www.transitivebullsh.it/projects/p-doom), and AI-made parodies like [Margin Call](https://www.transitivebullsh.it/projects/margin-call-ai-safety-parody) and [Pluribus](https://www.transitivebullsh.it/projects/pluribus-openai-parody).

## How it was made

Claude Code with **Opus 5.5** made nearly all of it: the lyric rewrites, the audio experiments, the storyboard, every image and video prompt, the caption compositor, and the review tool. My job was taste and feedback. Start to finish took about a day of back-and-forth and ~$100 of fal credits.

The final pipeline:

1. **Lyrics.** Rewritten line by line against the original’s rhymes and syllable counts.
2. **Song.** Suno V6, from text only: tagged lyrics plus a detailed style prompt. Of three takes, we kept the one that got the most lyrics right.
3. **Timing.** Local Whisper word timestamps aligned to the lyrics, plus a beat grid, so every word has a timestamp.
4. **Storyboard.** 70 shots, each anchored to a lyric line, each with an image prompt and a motion prompt.
5. **Characters.** One reference image per character, and one outfit each, iterated until they looked right.
6. **Keyframes.** One still per shot with Nano Banana Pro, conditioned on the character refs.
7. **Clips.** Veo 3.1 Fast image-to-video, with first + last frames for shots that have to land somewhere specific. Wan 2.2 for the shots Veo refused.
8. **Compositing.** A local Python + ffmpeg/libass pipeline for in-world neon captions (the backing vocals’ “down, down, down” literally steps down the screen), footnotes, color grades, letterboxing, and grain.
9. **Review.** A local scene-by-scene review tool (below). Five versions until it felt done.
10. **Poster.** Six first-frame options, since X shows a video’s first frame as its preview.

![All 70 shots, each anchored to a lyric line, a start time, and a color grade.](https://assets.cultural-alignment.com/personal-site/media/3431a800c39badfc8fdc6872d707ceb96f96a31ca226666fc5bdbd513e4b9975.webp)

### The feedback loop

The most useful thing we built was a scene-by-scene review tool. Every shot gets its keyframe, the clip as it plays in the cut, the raw generation, and in-context playback, plus **Keep / Tweak / Redo** and a notes box. My notes save to a file that Claude reads back as the next round of prompts.

![The review tool, with my real note on the Pooh shot. The next version came straight from it.](https://assets.cultural-alignment.com/personal-site/media/2b83b310548328f9eb0bc51e23a638e72be18e1cbffea957c87111c4178f7f93.webp)

### Tools used

- **Claude Code (Opus 5.5):** director, producer, editor, and all of the code.
- **Suno V6:** the song.
- **fal:** Nano Banana Pro for character refs and keyframes, Veo 3.1 Fast for video, Wan 2.2 for the shots Veo wouldn’t touch, and OmniHuman 1.5 for Sam’s two rap close-ups.
- **Local:** mlx-whisper for word timings, beat_this for the beat grid, audio-separator to pull the rap vocal for lip-sync, and ffmpeg + libass for captions and grading.

### Tried and discarded

> 🗑️ Everything below was tried and thrown away. None of it made it into the final video.

- **ElevenLabs Music:** sang its own melody, not the song.
- **ElevenLabs Voice Changer:** dropped an octave and drifted off-key on anything sung.
- **ElevenLabs TTS v3 + Voice Design:** a designed voice for the rap verse.
- **MiniMax Music 2.6 and 3:** wrote new songs, not ours.
- **ACE-Step** (text-to-music, inpainting, and lyric editing): lyric editing came closest because it keeps the original singer, but two hook lines refused to change in every single take.
- **Google Lyria 3.5 + Seed-VC:** Lyria sang the new lines and Seed-VC re-voiced the original refrain. It still didn’t feel like the song.
- **Tencent AuK:** word-level vocal edits. The demo’s daily quota ended that experiment.
- **Singing over the original’s instrumental** (split with BS-RoFormer and MelBand-RoFormer): none of the AI vocals layered on top came close to the real thing, and Suno and ElevenLabs both refused uploads of the original anyway.
- **Lip-syncing Dario** (OmniHuman 1.5): it worked, but I cut every one of those shots in review.
- **Kling v3:** refused the Trump dinner shot too.
- **Models tested and not used:** Seedream 5, GPT Image 2.5, Qwen Image 3, Kling O3, Meta’s Muse Image, and Nano Banana 2 for images; Seedance 2.5 and Wan 3.0 for video.
- **Two whole visual styles:** a Pixar-ish 3D look (too generic) and a neon-heavy cyberpunk look (way too purple).

## How it came together

The short version of a lot of trial and error:

1. **Concept + lyrics.** Club Frontier, DJ Moloch, and THE-DARIO feat. DADDY SAMA, rewritten line by line against the original’s rhymes and syllables.
2. **Audio round 1: rejected.** ElevenLabs Music, MiniMax, and ACE-Step all wrote their own melodies. The only part I liked was the original singer leaking through an ACE-Step inpaint. ▶ [Listen: ElevenLabs Music, a good singer, the wrong song](https://assets.cultural-alignment.com/personal-site/media/cd35d02f6486f9391171fa1cc8e9080aadff13f588756c821266283a10ed1c1e.mp3)
3. **Round 2: rejected.** Lyria 3.5 sang the new lines, and Seed-VC re-voiced the original refrain into Lyria’s singer. Still not it. ▶ [Listen: Lyria 3.5 lines + the original refrain, re-voiced with Seed-VC](https://assets.cultural-alignment.com/personal-site/media/fbed70cd1cca046c90d2c402a216bdb5210822dac0788e8b143ae4abbbecb871.mp3)
4. **Rounds 3–5: closest, still no.** ACE-Step’s lyric-edit mode kept the original recording and just swapped the words. But that meant the original singer’s voice, and two hook lines refused to change in every take. ▶ [Listen: ACE-Step lyric edit on the original mix](https://assets.cultural-alignment.com/personal-site/media/0ff42366ecf3f8cb253cb5e868e38c54eb4e8f9e9763c3ea475edf7a7b66a93a.mp3)
5. **Suno.** It blocked the original instrumental, so I went text-only: tagged lyrics plus a style prompt that describes the sound. One fix: every take had a ticking hi-hat, because the prompt literally said “ticking.”
6. **Timing + storyboard.** Whisper word timestamps and a beat grid, then 70 shots mapped onto them.
7. **Three looks.** Stylized 3D was too Pixar. Painterly cyberpunk was way too purple. Restrained Blade Runner noir stuck.

   ![The same cast in all three looks.](https://assets.cultural-alignment.com/personal-site/media/50e068e7b6e7a6947f9ecd1b894d67eb6fc07fc1ece8df39f20d23780e772bfb.webp)

8. **Likeness.** Real people are recognizable caricatures, never photoreal. Dario took four passes before he actually looked like him.

   ![THE-DARIO, v1 to final.](https://assets.cultural-alignment.com/personal-site/media/737abaf4118ffbda064b9f1ace9fc8bc7822fb962a9933269b599b100e62a61a.webp)

9. **Clips.** Veo refused the Trump dinner and the Pooh shot (Kling refused the dinner too), so those two went to Wan 2.2. Then the stern shadow behind Pooh kept growing bear ears, so the silhouette is locked with a composite. ▶ [Outtake: the shadow grows bear ears](https://assets.cultural-alignment.com/personal-site/media/c9c6f85c846e19e762c3dc08ec07900e0a6a45143dd8214166ad4a0886bed76f.mp4)

   ![The honey bear, try 1 to final.](https://assets.cultural-alignment.com/personal-site/media/83a276c5e36497ab237d3e09d8995692fb5edaebd055aefcc74c17fb60798682.webp)

10. **Five review rounds.** Captions moved off faces, a cold open got cut, the Dario lip-sync shots became dance shots, and one wand massager kept blowing smoke until we painted the haze out of its keyframe. ▶ [Outtake: Veo decided the wand should blow smoke](https://assets.cultural-alignment.com/personal-site/media/386f65b531f915f27edc396fa8a0d035d462c2e638fa1357606300142b01461f.mp4) · ▶ [Cut in review: Dario lip-syncing](https://assets.cultural-alignment.com/personal-site/media/1b7707536981860e1550c9b8b861c618b5a3e940e05dd14bbe74d20ae4fe2f4f.mp4)
11. **Poster.** Six first-frame options, since X shows a video’s first frame as its preview. B won.

    ![Poster options A–F. B is now the first frame of the video.](https://assets.cultural-alignment.com/personal-site/media/c2d51461214fe505d9351fb524d824d1448df5fb95263bec74b3ef542df0cdb8.webp)

## What I learned

- **Stills are cheap, video is expensive.** Lock every composition as a keyframe (~15¢) before animating it (~60¢–$1.20 a clip).
- **Character refs are the whole game.** One reference image per character, one outfit each, passed into every keyframe.
- **Likeness lives in the refs.** Name the real person when making the reference; describe, don’t name, them in the shot prompts.
- **Use first + last frames when a shot has to land somewhere:** a kiss, a readable label.
- **Composite anything that must not move.** Video models love to “improve” a silhouette.
- **Different models refuse different things.** Veo wouldn’t animate the Trump dinner or the Pooh shot, and Kling wouldn’t do the dinner; Wan 2.2 did both.
- **Say what you want, not what you don’t.** “No ticking” in a Suno prompt still gets you ticking, and “no smoke” in a video prompt still gets you smoke.
- **Scene-level feedback turns taste into prompts.** Anchoring every note to a shot and a timestamp made each revision cheap and specific.
- **Budget:** ~$100 of fal credits for the visuals, across ~235 images and ~80 video clips over five versions.

### Suno: what worked

Suno V6 made the song from text alone. The details, for anyone making their own parody:

- **No artist names in the style prompt.** Describe the era, tempo, key, instruments, and vocal style instead, and measure the tempo and key from the original.
- **Section tags go on their own lines,** like `[Verse 1]` and `[Pre-Chorus]`. A delivery cue inside the tag switches the voice: `[Rap Verse - laid-back male rapper]`.
- **Parentheses are backing vocals and ad-libs:** `(ahoo)` at the end of a line, and each backing answer on its own line.
- **Shape the phrasing in the lyrics:** stretched vowels (`sloow`), `...` for a pause, and CAPS on one phrase for punch (`LOSS DROP`).
- **Spell words the way they should be sung.** We wrote “Meter” so it would pronounce METR, then fixed the spelling in the captions.
- **Write every chorus out in full.** No `[Chorus x2]`.
- **Settings I’d start with:** V6, male vocals, style influence ~70–80%, weirdness ~20–30%. Generate 4–8 takes and judge by ear.
- **What didn’t work:** Suno fingerprints uploads, so it blocked the original instrumental, and it checks lyrics against a lyrics database. And the word “ticking” in my style prompt put a ticking sound in every take.

<details>
<summary>The final style prompt</summary>

```text
Late-night club slow jam, 2013 hip-hop R&B, a sensual anti-EDM grind record for the DJ to slow the party down. Sparse and warm: booming 808 kick and sub bass, soft claps on the backbeat, minimal percussion, dark warm synth pads, 61.5 BPM, A major. Big wide polished radio mix, airy reverb on the vocals. Light Auto-Tune, laid-back behind the beat. Smooth falsetto R&B lead with stacked male harmonies and "ahoo" ad-libs; chanted chorus hook is call-and-response: lead sings "slow it down", stacked male harmonies echo "down down down, down down down". Laid-back NY rap feature. Sexy, confident, sensual, seductive, explicit.
```

</details>

<details>
<summary>Exclude styles</summary>

```text
EDM, trap hi-hat rolls, rock, female vocals, fast tempo, ticking, clock, metronome, hi-hat rolls, trap hi-hats
```

</details>

<details>
<summary>Lyric formatting example</summary>

```text
[Intro]
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
Everybody know slow AGI, way better than no AGI
```

</details>

## License

The code is [MIT](license) © [Travis Fischer](https://x.com/transitive_bs). The video is a parody, not affiliated with any lab, artist, or head of state. The original song belongs to its owners.

---

Want to run the pipeline, redo a shot, or see where everything lives? See [CONTRIBUTING.md](CONTRIBUTING.md).
