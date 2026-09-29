# Release kit: "Slow It Down" (DistroKid → Spotify, Apple Music)

Everything DistroKid asks for, ready to upload. The media files are git-ignored like all media in this repo.

| File | What it is |
|---|---|
| `Slow It Down - Travis Fischer.wav` | The master: Suno V6 take B (`video/audio/suno_B.wav`), unaltered. 48 kHz / 16-bit stereo, 4:14, −14.6 LUFS. |
| `cover.jpg` | 3000×3000 RGB. The poster's muse (base `B_shh`) outpainted to a square with nano-banana-pro, plus the poster's neon title with the teal "down down" staircase. |
| `cover-title-only.jpg` | The same image with only "slow it down" on it. This is the safer upload, because DistroKid only allows cover text that matches the title or the artist name. |
| `cover-vertical.jpg` | 1440×2560 cover for TikTok: `sid_full` outpainted to 9:16 (`cover-work/sid_vert_d`, copied to `sid_vert.png`), with the title stacked "slow / it / down" down the left side. Her face and the title stay inside the 3:4 crop TikTok's profile grid shows. Instagram fits a Reel's cover to the video's shape, so the 16:9 Reel uses `video/poster/poster.png` instead. |
| `lyrics.txt` | The written lyrics (`docs/lyrics-current.txt`) in the order the take sings them, with Suno's pronunciation and pacing hacks undone: METR (not "Meter"), "exfilled", no stretched vowels, CAPS or `...` pause cues. |
| `make_cover.py`, `make_lyrics.py` | Rebuild the covers (`make_cover.py [square] [vertical]`, from the outpaints in `cover-work/`, each with its fal receipt next to it) and the lyrics. |

## DistroKid form

- **Artist:** Travis Fischer
- **Title:** Slow It Down
- **Songwriter (legal name):** Travis Fischer
- **Primary genre:** R&B/Soul · **Secondary:** Hip Hop/Rap
- **Language:** English
- **Explicit:** Yes ("motherfuckin'", "shit")
- **Cover song:** No · **Samples:** No · **Instrumental:** No
- **AI disclosure:** Yes. The music and vocals were generated with Suno (paid plan). The lyrics were written with AI assistance. The artwork is AI-generated.
- **Release date:** at least 2–3 weeks out, for example Friday, Oct 16, 2026.
- **℗ / ©:** 2026 Travis Fischer
- **YouTube Content ID:** leave it off. It would claim your own music video and anyone who shares it.

## Caveat before uploading

The refrain ("You gotta slow it down / Down down down / Down down down") and the title are kept exactly from The-Dream's 2013 single "Slow It Down" (`docs/03-lyrics-v1.md`). The public write-up also calls the song a parody of it. The melody and recording are new, since Suno generated them from text only, and the verses are new. But this is not "100% mine" in the way Sometimes I Think Slow is. DistroKid's upload form asks you to confirm you own all rights, and it can permanently ban an account over a false declaration.
