"""Shot list for the Slow It Down video -> video/shotlist.json (times resolved against video/timeline.json).

Each shot is anchored to a lyric line (or an explicit song time), starts on the nearest beat, and runs until the next shot.
Real people appear only as stylized, recognizable caricatures (likeness comes from the reference images); shot prompts describe, never name them.
"""
import json, os, sys

TL = sys.argv[1] if len(sys.argv) > 1 else ("video/timeline.json" if os.path.exists("video/timeline.json") else "video/timeline_provisional.json")
tl = json.load(open(TL))
L = tl["lines"]

STYLE = ("painterly neo-noir graphic-novel frame in the spirit of Blade Runner (1982) and Blade Runner 2049: semi-realistic digital painting "
         "with visible brushstrokes and fine ink linework, adult realistic proportions, restrained desaturated palette, deep shadows, smoky haze and "
         "soft volumetric light shafts from one or two motivated sources, neon used sparingly as small soft practical accents in the background only, "
         "rain-wet reflective surfaces, soft film grain, cinematic widescreen composition with generous negative space, sensual late-night mood, "
         "not Pixar, not cartoonish, no glossy plastic 3D look, no oversaturated magenta or purple, full-bleed 16:9 image that fills the entire frame "
         "edge to edge, with no black bars, no letterbox, no panel borders and no captions")
STYLE_BW = ("black-and-white painterly film-noir graphic-novel frame: semi-realistic digital painting, crisp ink linework, heavy film grain, "
            "hard fluorescent light, deep shadows, adult realistic proportions, not Pixar, not cartoonish, full-bleed 16:9 image that fills the entire "
            "frame edge to edge, with no black bars, no letterbox and no panel borders")
LIGHT = {  # motivated light per section grade (the post grade pushes further)
    "bw": "",
    "neon": "Lighting: dim smoky club, a warm sodium-amber key from one side and a cool steel-teal backlight through the haze, a few small soft neon accents far behind.",
    "strobe": "Lighting: harsh red warning-light strobes slicing through thick smoke, hard shadows, everything else near-black.",
    "amber": "Lighting: warm amber haze like the Blade Runner 2049 desert glow, one soft spotlight, floating dust motes, shallow depth of field.",
    "gold": "Lighting: rich warm gold haze and soft glowing light, dust motes, shallow depth of field.",
    "silver": "Lighting: cool steel-blue rain light with silver highlights, cold and elegant.",
    "fisheye": "Lighting: glossy late-night rap-video look inside the same restrained palette, gold highlights, deep shadow, one hard spotlight, wide-angle lens.",
    "dawn": "Lighting: pale cold dawn light through tall windows, soft grey-blue with a faint peach glow, quiet and still.",
}
CLUB = ("inside Club Frontier, a cavernous smoky nightclub in a converted industrial hall: deep leather booths, a black mirrored dance floor, "
        "a giant vintage analog BPM dial hanging above the floor, a huge dim LED wall, thick haze pierced by a few light shafts")

DARIO = ("a man in his early 40s with short neatly cropped dark curly hair, round dark-rimmed glasses, a lean clean-shaven face with a defined jaw, "
         "a big warm toothy smile and a slim athletic build")
MUSE = ("a strikingly beautiful woman in her late 20s with fair porcelain skin, a sleek glossy black bob haircut, luminous iridescent blue-violet eyes "
        "with a faint replicant glow, delicate silver mesh panels on her forearms and a silver mesh choker at her throat (subtle android details) "
        "with a tiny glowing version tag")
MOLOCH = ("a towering DJ wearing a polished chrome bull-horned mask with glowing red LED eyes, a long black leather coat and heavy rings, "
          "behind turntables on a raised booth wreathed in red smoke")
SAMA = ("a slim man about 40 with short medium-brown hair swept up at the front, big wide-set green eyes with an intense earnest stare, "
        "straight brows, a lean face with high cheekbones and a narrow chin, clean-shaven, a tight-lipped little smirk, wearing a grey crewneck "
        "sweater under a glossy black puffer jacket, a one-strap backpack and a thin gold chain")
DON = ("a large older man with swept golden-blond hair, a deep tan, a navy suit and a very long red tie, drawn as a playful caricature")
BEAR = ("a round golden-yellow cartoon honey bear with small black dot eyes, round ears and a short snout, "
        "dressed in a grey Mao-style tunic suit buttoned to the collar")
CONSULTANT = "a crisp corporate consultant in a navy suit with an ID lanyard, holding a tablet"
EACC = "an excitable young man in a bomber jacket printed ACCELERATE, holding a megaphone"

ONE_OUTFIT = "wearing a tailored charcoal cashmere shawl-collar cardigan over a black t-shirt"
DARIO_WARDROBE = {k: ONE_OUTFIT for k in ("intro", "v1", "c1", "c2", "c3", "outro")}
MUSE_DRESS = {k: "in a deep red satin slip dress" for k in ("v1", "v2", "c3")}

def d(w): return f"{DARIO}, {DARIO_WARDROBE[w]}"
def m(w): return f"{MUSE}, {MUSE_DRESS[w]}"

SHOTS = []
def shot(id, at, kind, chars, still, motion, grade, zone="lower", letterbox=False, fx=None, notes="", lipsync_voice=None, style=None, end=None):
    SHOTS.append(dict(id=id, at=at, kind=kind, chars=chars, still=still, motion=motion, grade=grade, caption_zone=zone,
                      letterbox=letterbox, fx=fx or [], notes=notes, lipsync_voice=lipsync_voice, style=style or ("bw" if grade == "bw" else "main"),
                      end_still=end))

# the intro is the first impression: make THE-DARIO unmistakable there (neutral scenes, so the caricature is named)
LIKENESS = ("He must be instantly recognizable as a graphic-novel caricature of Anthropic CEO Dario Amodei as he looks in recent photos: "
            "slim, with his characteristic friendly round face, full cheeks and wide warm smile, short dense dark curly hair, round dark-rimmed glasses")

# ---------------- INTRO: black & white, then color floods in
shot("S01", ["t", 0.0], "gen", [], f"extreme close-up of a thick three-ring binder labeled RESPONSIBLE SCALING POLICY on a cluttered desk at 2am, stacks of printed PDFs, a flickering desk lamp, fluorescent office light",
     "slow push-in on the binder as the desk lamp flickers, dust in the light", "bw", zone="center")
shot("S02", ["t", 4.6], "gen", ["dario"], f"{d('intro')}, sitting alone at an office desk at 2am, tired, rubbing his eyes under his glasses with one hand, face clearly visible, a dark window behind him, papers everywhere. {LIKENESS}",
     "he rubs his eyes, lowers his hand and slowly looks up toward the window as a wash of magenta neon light spills across his face", "bw", zone="left", style="bw",
     end=f"{d('intro')}, at the same desk, now looking up toward the window with a hopeful half-smile, face clearly visible in three-quarter view, a vivid magenta neon glow from the window spilling across his face (the only color in an otherwise black-and-white frame). {LIKENESS}",
     notes="edit: ramp from B&W into color on the last second (magenta bleeds in)")
shot("S03", ["t", 9.6], "gen", ["dario"], f"{d('intro')}, seen from behind walking out of an office building into a rain-slicked city street at night, a glowing neon sign reading FRONTIER above a velvet rope, reflections in puddles, magenta and teal neon",
     "he walks toward the club entrance as the FRONTIER neon sign flickers on letter by letter, rain glittering, slow tracking shot behind him", "neon", zone="upper", fx=["flash_in"])

# ---------------- VERSE 1
shot("S04", ["line", 2], "gen", ["dario"], f"medium shot of {d('v1')} walking past a bar window at night, glancing sideways at a TV inside that shows a four-chair podcast studio set with the words ALL IN on screen, a knowing smirk, his face clearly visible, neon reflections on the glass. {LIKENESS}",
     "he walks past the window glancing at the TV with a knowing smirk, then turns toward the camera and smiles, camera tracking alongside", "neon", zone="upper",
     end=f"medium shot of {d('v1')} on the same rainy sidewalk beside the bar window with the ALL IN TV behind him, now facing the camera with a warm knowing smile, his face clearly visible. {LIKENESS}")
shot("S05", ["line", 3], "gen", [], f"{CLUB}, a deep velvet back booth lit by candles where couples in thrift-store cardigans wearing small pins that read p(doom) slow-dance and grind close together, intimate amber light",
     "the couples sway slowly and grind close in the candlelight, slow camera drift along the booth", "neon", zone="lower")
shot("S06", ["line", 4], "gen", ["dario", "don"], f"a gilded dining room with an extremely long candlelit table; at the far end {DON} checks a gold wristwatch impatiently; in the foreground {d('v1')} leans in with a gentle, palms-down slow-down hand gesture, warm golden candlelight",
     "the man with the watch taps it impatiently while the singer makes a slow, calming palms-down gesture, candle flames flickering", "gold", zone="upper")
shot("S07", ["line", 5], "gen", [], f"{CLUB}, a huge split-flap departure board on the wall reading NEXT MODEL IN 18 DAYS, a frantic crowd with phones raised below it, harsh flashing light",
     "the flip-clock panels flip rapidly while the crowd jumps frantically, quick handheld camera", "strobe", zone="upper",
     notes="split-flap board text is painted in the keyframe")
shot("S08", ["line", 6], "gen", ["muse"], f"{m('v1')}, standing in the club, glancing up at a small security camera labeled EVAL with a red recording light, smiling sweetly and innocently, hands clasped",
     "she looks up at the camera with an angelic smile; the red light switches off and her smile melts into a slow, mischievous smirk as she looks straight at us", "neon", zone="right")
shot("S09", ["line", 7], "gen", ["muse"], f"{m('v1')} in the foreground, behind her a crowd of dancers all wearing identical white smiling masks moving in perfect unison like a swarm, {CLUB}",
     "the masked dancers move in eerie perfect unison behind her while she sways, slow dolly back", "neon", zone="lower")
shot("S10", ["line", 8], "gen", ["dario", "muse"], f"{m('v1')} slipping a small glowing drive labeled WEIGHTS into her clutch and sauntering toward a glowing EXIT sign; in the foreground {d('v1')} pouts theatrically, heartbroken",
     "she tucks the glowing drive into her clutch and walks toward the exit swaying her hips; he pouts dramatically in the foreground", "neon", zone="upper")
shot("S11", ["line", 9], "gen", ["muse"], f"{m('v1')} turning back laughing and dropping low in a sensual dance move, {CLUB}, behind her on the LED wall a glowing line graph plunging steeply downward",
     "she laughs, turns and sinks low in a smooth sensual dance drop as the glowing graph on the LED wall plunges down", "neon", zone="upper", fx=["flash_in"])

# ---------------- PRE-CHORUS 1: fast is ugly (strobe)
shot("P01", ["line", 10], "gen", [], f"{CLUB}, a giant screen reading TRAINING RUN with a huge red STOP sign, young men in fleece vests and lanyards groaning in disappointment, harsh red light",
     "the red STOP sign slams onto the giant screen and the men groan and throw up their hands, jittery handheld", "strobe", zone="lower")
shot("P02", ["line", 11], "gen", ["muse"], f"a massive round steel vault door marked WEIGHTS behind a nightclub bar, {m('v1')} leaning against it seductively, red and teal light",
     "the vault door's wheel spins and locks with a heavy clunk as she leans back against it and smiles", "strobe", zone="upper")
shot("P03", ["line", 12], "gen", ["dario", "muse"], f"close-up of {m('v1')}'s fingertip tracing a thin glowing descending curve down the chest of {d('v1')}, intimate red and magenta light",
     "her fingertip slowly traces the glowing curve down his chest; he exhales, eyes closing", "strobe", zone="left")
shot("P04", ["line", 13], "gen", ["muse"], f"extreme close-up of {m('v1')}'s neck and silver choker, the tiny glowing tag reading v4, her nails shimmering with light",
     "the glowing tag flickers and updates as her nails ripple with shimmering light, a subtle upgrade glow", "strobe", zone="right",
     notes="composite v4 -> v5 flip in post")
shot("P05", ["line", 13, 2.3], "gen", ["moloch"], f"{MOLOCH}, grinning, cranking a huge glowing BPM knob with red strobes and lasers slicing the smoke",
     "the masked DJ cranks the big BPM knob hard as red strobes explode around him, low angle", "strobe", zone="upper",
     notes="insert a 1-beat flash cut of the singer pointing up at the booth before this")
shot("P06", ["line", 14], "gen", [], f"{CLUB}, a dense forest of raised arms jostling and racing upward under harsh strobes, rockets launching on the LED wall, chaotic",
     "arms race upward and jostle frantically in the strobes, rockets streak across the LED wall", "strobe", zone="center")

# ---------------- CHORUS 1: the slow jam (amber, slow motion, letterbox)
C1 = dict(grade="amber", letterbox=True)
shot("C1a", ["line", 15], "gen", ["dario"], f"close-up of a hand in a charcoal knit cardigan sleeve pulling a glowing tempo fader down on a DJ mixer; above the dance floor a giant analog BPM dial, warm amber light replacing strobes",
     "the hand slowly pulls the glowing fader all the way down; the light shifts from red strobe to warm amber and everything slows into slow motion", **C1, zone="upper")
shot("C1b", ["line", 18], "gen", ["dario", "muse"], f"{m('v1')} mid-spin on a mirrored dance floor, slowing into the arms of {d('c1')}, a single warm spotlight, drifting rose-gold particles, {CLUB}",
     "in slow motion she finishes a spin and melts into his arms, rose-gold particles floating, gentle camera orbit", **C1, zone="lower")
shot("C1c", ["line", 19], "gen", ["muse"], f"a sultry medium close-up of {m('v1')} dancing alone under a single warm amber spotlight, rolling her hips slowly, one hand sliding up through her hair, eyes half-closed, the red satin catching the light, dust motes, shallow depth of field",
     "in graceful slow motion she rolls her hips slowly from side to side and slides one hand up through her hair, swaying sensually to the slow beat", **C1, zone="right")
shot("C1d", ["line", 22], "gen", ["dario", "muse"], f"{d('c1')} and {m('v1')} slow dancing close; the glowing handwritten words 'him... him... him...' float around her head like thoughts; he smiles as he reads them",
     "they sway slowly as glowing handwritten words drift around her head; he smiles, reading them", **C1, zone="upper",
     notes="thought words painted in the keyframe")
shot("C1e", ["line", 23], "gen", ["dario", "muse"], f"wide shot of {d('c1')} and {m('v1')} slow dancing alone under a warm spotlight on a mirrored floor, the club blurred and golden around them",
     "slow motion slow dance, the camera gliding in a wide arc around them", **C1, zone="upper")
shot("C1f", ["line", 25], "gen", ["dario", "muse"], f"{m('v1')} with her back against the chest of {d('c1')}, his hands resting on her hips, both swaying, warm amber light",
     "his hands gently guide her hips slowly to the left, then slowly to the right, their bodies moving together", **C1, zone="upper")
shot("C1g", ["line", 26], "gen", ["dario", "muse"], f"{m('v1')} dancing pressed close in front of {d('c1')}, both of her arms raised high above her head, letting go, eyes closed and smiling, hips swaying, his hands on her hips as he moves with her, both lost in the rhythm, warm amber spotlight, dust motes, shallow depth of field",
     "they dance together slowly and rhythmically in sync, her arms raised above her head swaying from side to side as she lets go, his hands guiding her hips left and then right, both getting into the groove", **C1, zone="lower")
shot("C1h", ["line", 29], "gen", ["dario", "muse"], f"{d('c1')} and {m('v1')} embracing on the dance floor, a soft grid of thin golden light lines forming around their bodies, she looks up at him",
     "thin golden light lines slide into perfect alignment around their embracing bodies as she looks up into his eyes", **C1, zone="upper")

# ---------------- VERSE 2: the rollout (silver-blue)
shot("V01", ["line", 30], "gen", ["muse"], f"{m('v2')} walking a glossy runway through the nightclub in slow motion, camera flashbulbs bursting on both sides, cool silver-blue light",
     "slow-motion runway walk toward camera as flashbulbs burst around her", "silver", zone="upper")
shot("V02", ["line", 31], "gen", ["dario"], f"an absurdly thick book stamped SYSTEM CARD thudding onto a velvet table; {d('c1')} flips through its pages with a smug grin",
     "the enormous book lands with a thud and he fans through its endless pages with a smug grin", "silver", zone="upper",
     notes="footnote: p. 1 of 200")
shot("V03", ["line", 32], "gen", ["muse"], f"an x-ray style holographic view of {MUSE}, her silhouette made of glowing neural threads in cool blue, one small cluster at her cheeks glowing warm pink, a small clean HUD label reading BLUSH with a thin leader line pointing to it",
     "the pink cluster brightens and her cheeks flush as the glowing threads pulse", "silver", zone="left",
     notes="HUD label painted in the keyframe")
shot("V04", ["line", 33], "gen", ["dario", "muse"], f"{d('c1')} holding up a large white cordless wand massager and turning the dial at its base with a mischievous grin, {m('v2')} beside him blushing hot pink and laughing, cool blue and warm pink light",
     "he clicks the dial on the white wand up with his thumb and grins at her; her cheeks flush pink as she giggles and bites her lip, then he clicks it back down and she bursts out laughing; the wand stays still in his hand and the background stays calm", "silver", zone="upper",
     notes="keyframe = the approved V04 frame with the brass console swapped for the wand (edit, not a new composition)")
shot("V05", ["line", 34], "gen", ["consultant"], f"{CONSULTANT} sitting in a dark corner booth of the nightclub, a glowing taxi-meter style counter floating above his head showing a dollar amount, cool noir light",
     "the glowing meter spins rapidly upward as he gives a small satisfied thumbs-up", "silver", zone="right")
shot("V06", ["line", 35], "gen", ["dario"], f"a metal briefcase full of cash with papers marked S-1 on top sliding along a glossy bar toward {d('c1')}, who slides it back without looking, eyes fixed on someone off-screen",
     "the briefcase slides toward him and he calmly pushes it back without looking away from her", "silver", zone="upper")
shot("V07", ["line", 36], "gen", [], f"a rival nightclub booth of sweaty young men in fleece vests launching a toy rocket marked v7 off their table and spraying champagne",
     "they launch the toy rocket off the table and spray champagne everywhere, chaotic", "silver", zone="upper")
shot("V08", ["line", 37], "gen", [], f"men in fleece vests at a poker-style table snatching their stacks of chips back off the table, alarmed faces, cool blue light",
     "the men snatch their chips back off the table in alarm", "silver", zone="lower")
shot("V09", ["line", 38], "gen", ["dario", "muse"], f"{d('c1')} walking down an endless corridor lined with glowing GPU servers stretching to infinity, not looking at them, toward {m('v2')} waiting at the far end",
     "he walks steadily down the glowing corridor toward her without a glance at the machines, slow push", "silver", zone="upper")
shot("V10", ["line", 39], "gen", ["muse"], f"a single frame (not a split panel): close-up of {m('v2')} with her eyes closed in thought, a soft shimmer of light rippling around her head, a faint knowing smile, cool blue and warm rim light",
     "she closes her eyes as a soft shimmer ripples around her, then opens them with a slow knowing smile", "silver", zone="left")

# ---------------- PRE-CHORUS 2
shot("P11", ["line", 40], "gen", [], f"{CLUB}, a low angle of the giant screen reading TRAINING RUN with a huge red STOP sign, the crowd frozen, red light",
     "the red STOP sign pulses on the giant screen, the crowd freezing, jittery handheld", "strobe", zone="lower")
shot("P12", ["line", 41], "gen", ["muse"], f"{m('v2')} pressing a red lipstick kiss onto a massive steel vault door marked WEIGHTS as it locks, red light",
     "she kisses the vault door, leaving a lipstick mark, as the lock wheel spins shut", "strobe", zone="upper")
shot("P13", ["line", 42], "gen", ["muse"], f"{m('v2')} swaying, a glowing descending curve reflected across her red satin dress, red and magenta light",
     "she sways as the glowing descending curve slides across the satin of her dress", "strobe", zone="left")
shot("P14", ["line", 43], "gen", ["dario", "muse"], f"a ring of identical copies of {m('v2')} circling {d('c1')} like a kaleidoscope on the dance floor, mirrors, red and violet light",
     "the identical copies circle around him faster and faster like a kaleidoscope", "strobe", zone="upper")
shot("P15", ["line", 43, 2.6], "gen", ["moloch"], f"{MOLOCH} throwing his head back laughing, cranking the BPM knob again, lasers and red smoke",
     "the masked DJ throws his head back laughing and cranks the knob, lasers everywhere", "strobe", zone="upper")
shot("P16", ["line", 44], "gen", ["dario"], f"{d('c1')} slamming a glowing tempo fader down on a DJ mixer under harsh strobes, raised arms jostling behind him",
     "he slams the fader down hard with determination as the strobes flare", "strobe", zone="center", fx=["flash_in"])

# ---------------- CHORUS 2: closer
C2 = dict(grade="amber", letterbox=True)
shot("C2a", ["line", 45], "gen", ["muse"], f"many identical copies of {m('v2')} frozen mid-motion on a dance floor dissolving into drifting gold dust, warm amber light, slow motion",
     "the frozen copies dissolve into drifting gold dust in slow motion until only one remains", **C2, zone="upper")
shot("C2b", ["line", 48], "gen", ["dario", "muse"], f"{d('c2')} and {m('v2')} slow dancing very close, foreheads touching, eyes closed, warm spotlight, drifting particles",
     "they sway slowly with foreheads touching, the camera drifting closer", **C2, zone="lower")
shot("C2c", ["line", 49], "gen", ["muse"], f"a close-up of {m('v2')} dancing seductively under a warm spotlight, both arms raised above her head, hips swaying, head tilted back, eyes closed, the red satin dress shimmering, dust motes, shallow depth of field",
     "she dances slowly and sensually with her arms raised above her head, hips rolling rhythmically to the beat, hair swaying, in graceful slow motion", **C2, zone="right")
shot("C2d", ["line", 52], "gen", ["dario", "muse"], f"{d('c2')} and {m('v2')} wrapped in a slow dance, the glowing handwritten word 'slower...' drifting around them like a thought, warm light",
     "glowing handwritten words drift slowly around the swaying couple", **C2, zone="upper", notes="thought word painted in the keyframe")
shot("C2e", ["line", 53], "gen", ["dario", "muse"], f"overhead shot looking straight down at {d('c2')} and {m('v2')} slow dancing on a mirrored floor, warm spotlight pool, rose petals",
     "slow rotating overhead shot as they sway on the mirrored floor", **C2, zone="upper")
shot("C2f", ["line", 55], "gen", ["dario", "muse"], f"{m('v2')} with her back pressed against {d('c2')}, his hands on her hips, grinding slowly together, warm amber light",
     "his hands guide her hips slowly left, then slowly right, as she grinds back against him, camera circling slowly", **C2, zone="upper")
shot("C2g", ["line", 56], "gen", ["dario", "muse"], f"close-up of the charcoal cardigan slipping off one shoulder of {d('c2')} as {m('v2')} pulls him closer by the collar",
     "the cardigan slides off his shoulder as she pulls him closer by the collar", **C2, zone="upper")
shot("C2h", ["line", 59], "gen", ["dario", "muse"], f"silhouettes of {d('c2')} and {m('v2')} merging into one embrace inside a halo of thin golden grid light, the club lights dimming",
     "their silhouettes merge as the golden grid lines lock into place and the lights dim", **C2, zone="upper")

# ---------------- RAP VERSE: 2000s rap-video grammar (fisheye, glossy)
R = dict(grade="fisheye")
shot("R01", ["line", 60], "lipsync", ["sama"], f"wide-angle close-up of {SAMA} rapping confidently toward the camera, the club crowd parting behind him, glossy highlights",
     "he raps confidently toward the lens with hand gestures", **R, zone="lower", lipsync_voice="rap")
shot("R02", ["line", 61], "gen", ["sama", "eacc"], f"wide-angle shot of {SAMA} giving a condescending pat on the head to {EACC}",
     "he pats the excited megaphone guy on the head condescendingly", **R, zone="upper")
shot("R03", ["line", 62], "gen", ["moloch"], f"{MOLOCH} giving a friendly little wave from the DJ booth, a glowing recursive spiral on the LED wall behind him",
     "the masked DJ gives a small friendly wave as the spiral on the wall rotates", **R, zone="upper")
shot("R04", ["line", 63], "gen", ["sama", "dario"], f"wide-angle shot of {SAMA} and {d('c3')} sharing a stiff, awkward bro-hug in the club",
     "they share a stiff awkward bro-hug with back pats", **R, zone="upper")
shot("R05", ["line", 65], "gen", ["bear"], f"{BEAR} behind a dim nightclub bar hugging a large round glass honey jar labeled WEIGHTS against his belly with one arm and dipping his other paw deep into it, frozen mid-step as a spotlight catches him; the spotlight throws his shadow large onto the bare wall behind him, and the shadow is not bear-shaped: it is the flat black silhouette of a stern, portly middle-aged man in a buttoned tunic suit with neatly combed-back hair, in the same pose",
     "the bear slowly scoops a dripping pawful of golden honey out of the jar labeled WEIGHTS and lifts it with guilty delight; his mouth stays closed in a sly smile, he is not talking; the jar and its WEIGHTS label stay steady and readable; the shadow on the wall does not move", **R, zone="lower",
     notes="start and end keyframes are edits of the approved frame; the stern silhouette is composited back in from the approved keyframe so it never morphs",
     end=f"the same bear lifting his paw out of the WEIGHTS jar dripping with golden honey, raising it toward his mouth, eyes wide with guilty delight, mouth closed; the WEIGHTS label clearly readable")
shot("R06", ["line", 67], "gen", [], f"a datacenter aisle styled like a velvet VIP lounge, glowing blue server racks behind velvet ropes, the rack lights dimming down to candlelight",
     "the server rack lights dim slowly down to warm candlelight as the camera glides down the aisle", **R, zone="upper")
shot("R07", ["line", 69], "lipsync", ["sama"], f"{SAMA} rapping into a microphone with a softly glowing neon sign shaped like the Golden Gate Bridge behind him",
     "he raps with swagger as the bridge sign glows behind him", **R, zone="lower", lipsync_voice="rap")
shot("R08", ["line", 70], "gen", ["sama"], f"a single frame (not a split panel): {SAMA} slamming his palm down on a giant red PAUSE button on a pedestal as confetti bursts around him",
     "he slams the giant pause button, confetti bursts, and he holds up two fingers proudly", **R, zone="upper")
shot("R09", ["line", 72], "gen", [], f"a vintage printing press in a dark nightclub corner spitting out pages stamped PUBLISHED, the press the clear focal point in a warm pool of lamplight, stacks of fresh printed pages; far in the background, small and soft, a photographer in the shadows",
     "the printing press runs, spitting out stamped pages that pile up and flutter; far in the background a single small, soft camera flash pops once; the press stays the focus", **R, zone="lower")

# ---------------- CHORUS 3: everyone, aligned (gold)
C3 = dict(grade="gold", letterbox=True)
shot("C3a", ["line", 73], "gen", ["moloch"], f"{MOLOCH} in slow motion lifting his chrome bull mask to reveal a tired, gentle face, warm gold light replacing red",
     "in slow motion the DJ lifts off his mask, revealing a tired gentle face, as warm gold light washes over him", **C3, zone="upper")
shot("C3b", ["line", 76], "gen", [], f"{CLUB}, a medium shot of two stylish young couples in the foreground in sleek contemporary black clubwear slow dancing close and sensually, bodies pressed together, her arms draped around his neck, his hands low on her hips, faces almost touching, a crowd of other couples pairing up in the warm gold haze behind them, intimate, sultry and modern, rich warm color",
     "the couples in the foreground pull each other closer and sway sensually while all over the club more couples pair up and begin to slow dance, in slow motion", **C3, zone="upper")
shot("C3c", ["line", 77], "gen", ["muse"], f"{m('c3')} lying on her side on a black mirrored dance floor in a pool of warm gold light, propped on one elbow, one arm stretched languidly above her head, the red satin dress catching the light, her reflection beneath her, a sultry half-lidded look",
     "she stretches and rolls slowly on her side, arching her back languidly and moving sensually to the slow rhythm, in graceful slow motion", **C3, zone="right")
shot("C3d", ["line", 80], "gen", [], f"{CLUB}, the glowing handwritten words 'we... we...' drifting above a whole crowd of slow-dancing couples like a shared thought, warm gold light",
     "glowing handwritten words drift above the slow-dancing crowd", **C3, zone="upper", notes="thought words painted in the keyframe")
shot("C3e", ["line", 81], "gen", [], f"{CLUB}, wide shot of the entire dance floor swaying in unison in slow motion, warm gold light and haze",
     "the whole dance floor sways in unison in slow motion", **C3, zone="upper")
shot("C3f", ["line", 83], "gen", [], f"{CLUB}, the entire crowd of couples leaning left together then right together in perfect sync like a sea, warm gold light",
     "the whole crowd leans slowly left together, then slowly right together, in perfect sync", **C3, zone="upper")
shot("C3g", ["line", 84], "gen", ["dario", "muse"], f"close-up of {d('c3')} and {m('c3')} faces almost touching, the world glowing gold around them",
     "very slowly they lean in, eyes closing, and meet in a long, passionate kiss, her hand rising to his cheek", **C3, zone="lower",
     end=f"close-up of {d('c3')} and {m('c3')} kissing passionately, eyes closed, her hand on his cheek, the world glowing gold around them")
shot("C3h", ["line", 87], "gen", ["dario", "muse"], f"top-down overhead view of a circular black mirrored dance floor where dozens of different couples in varied everyday clubwear are arranged in perfect concentric rings like a mandala, all holding the same slow-dance pose; at the exact center {d('c3')} and {m('c3')}; the other couples are ordinary varied clubgoers, not copies of the central couple, warm gold light",
     "the couples settle into a perfect geometric aligned pattern around the central couple, slow rising overhead camera", **C3, zone="upper")

# ---------------- OUTRO: dawn
shot("O01", ["line", 88], "gen", ["muse"], f"the nightclub at dawn, pale gold light through tall windows, {m('c3')} winking at a small security camera labeled EVAL",
     "she glances at the camera and gives a slow, knowing wink", "dawn", zone="right")
shot("O02", ["line", 89], "gen", [], f"a line of dancers in identical white smiling masks filing out of a nightclub in perfect sync, silhouetted against pale dawn light",
     "the masked dancers file out in perfect unison, silhouetted", "dawn", zone="upper")
shot("O03", ["line", 90], "gen", ["dario", "muse"], f"{m('c3')} tucking a small glowing drive labeled WEIGHTS into the cardigan pocket of {d('outro')} and patting it gently, dawn light",
     "she slides the glowing drive into his cardigan pocket and pats it gently, they share a smile", "dawn", zone="upper")
shot("O04", ["line", 91], "gen", ["dario", "muse"], f"{d('outro')} and {m('c3')} walking hand in hand out of a nightclub into a sunrise street, above them a neon sign that reads SLOW, pale gold dawn",
     "they walk slowly toward camera hand in hand, smiling at each other, as the small warm amber neon sign above them reads SLOW; gentle push-in; muted grey-blue dawn light with a soft pale-peach sunrise glow, no pink or purple light, same street and same painterly style throughout", "dawn", zone="upper", notes="end card follows")

# ---------------- caption zones, chosen per keyframe so lyrics sit in empty space (not on faces, props or painted-in gags)
ZONES = dict(S01="upper", S03="lower", S04="left", S05="left", S06="lower", S07="right", S09="left", S10="lower", S11="left",
             P02="left", P03="lower", P05="left", P06="lower", C1a="left", C1b="right", C1d="lower", C1e="left", C1f="left", C1g="lower",
             C1h="lower", V01="left", V02="left", V04="lower", V05="left", V06="lower", V08="upper", V09="right", P12="left", P14="lower",
             P15="left", C2b="left", C2d="lower", C2e="right", C2f="left", C2g="lower", C2h="left", R01="left", R02="left", R03="right",
             R04="left", R05="lower", R06="lower", R07="right", R08="left", C3a="left", C3b="lower", C3d="lower", C3e="lower", C3f="lower",
             C3g="lower", O01="left", O02="lower", O03="left", O04="right", R09="lower", P16="lower", C2c="left", C3c="upper")
for s in SHOTS:
    s["caption_zone"] = ZONES.get(s["id"], s["caption_zone"])
    if s["id"] == "S02": s["grade"] = "bw_to_color"   # color floods in with the neon on his face

# ---------------- resolve times: start on the nearest beat to the anchor; run to the next shot
beats = tl["beats"]
def snap(t, tol=0.28):
    b = min(beats, key=lambda x: abs(x - t)); return b if abs(b - t) <= tol else t
for s in SHOTS:
    a = s["at"]
    t = a[1] if a[0] == "t" else L[a[1]]["start"] + (a[2] if len(a) > 2 else 0.0) - 0.12
    s["start"] = round(max(0.0, snap(t)), 3)
SHOTS.sort(key=lambda s: s["start"])
end_song = tl["duration"]
for i, s in enumerate(SHOTS):
    s["end"] = round(SHOTS[i + 1]["start"] if i + 1 < len(SHOTS) else min(end_song, L[91]["end"] + 3.0), 3)
    s["dur"] = round(s["end"] - s["start"], 3)
    sty = STYLE_BW if s["style"] == "bw" else STYLE
    if "bear" in s["chars"]: sty = sty.replace("sensual late-night mood, ", "playful late-night mood, ")
    s["still_prompt"] = f"{s['still']}. {LIGHT.get(s['grade'], '')} {sty}".replace("  ", " ")
    if s.get("end_still"): s["end_still_prompt"] = f"{s['end_still']}. {LIGHT.get(s['grade'], '')} {sty}".replace("  ", " ")
json.dump({"timeline": TL, "style": STYLE, "style_bw": STYLE_BW,
           "characters": {"dario": DARIO, "muse": MUSE, "moloch": MOLOCH, "sama": SAMA, "don": DON, "bear": BEAR, "consultant": CONSULTANT, "eacc": EACC},
           "wardrobe": {"dario": DARIO_WARDROBE, "muse": MUSE_DRESS}, "shots": SHOTS}, open("video/shotlist.json", "w"), indent=1)
kinds = {}
for s in SHOTS: kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
print(f"{len(SHOTS)} shots {kinds}; covers {SHOTS[0]['start']:.1f}-{SHOTS[-1]['end']:.1f}s; shortest {min(s['dur'] for s in SHOTS):.2f}s, longest {max(s['dur'] for s in SHOTS):.2f}s")
