"""Shared prompt blocks for the scouting tests (original characters; no real-person names)."""
STYLE = ("Stylized 3D animated feature-film still with a painterly neo-noir look: hand-painted textures, visible brushstroke "
         "shading, slightly exaggerated elegant proportions, bold graphic shapes and deep shadows, neon rim light, "
         "volumetric haze. Not photorealistic.")
CLUB = ("Inside Club Frontier, a moody neon night club: magenta and cyan neon tubes, haze, a DJ booth with a glowing red BPM "
        "readout far in the background, a glossy reflective dance floor, soft bokeh lights.")
SINGER = ("a lean, fit man in his early 40s with dark curly hair, dark-rimmed rectangular glasses, a short stubble beard, "
          "wearing a stylish charcoal shawl-collar knit cardigan over a plain black t-shirt")
MUSE = ("a beautiful woman in her late 20s with a sleek black bob and blunt bangs, with subtle android details: faint silver "
        "mesh panels on her forearms and along the sides of her neck, and iridescent eyes that shimmer teal and violet; she "
        "wears an elegant deep-burgundy satin slip dress with a modest neckline")
SINGER_SHOT = (f"{STYLE} Medium close-up, waist-up, three-quarter view facing the camera: {SINGER} stands at the edge of the "
               f"dance floor, singing softly with lips slightly parted, eyes half-closed and confident, one hand raised near "
               f"his chest. {CLUB} Cinematic 16:9 composition, shallow depth of field, his face clearly lit by a warm amber "
               f"key light against the cool cyan-and-magenta background.")
MUSE_SHOT = (f"{STYLE} Medium shot, three-quarter view: {MUSE} stands near the glowing bar, looking over her shoulder toward "
             f"the camera with a knowing half-smile. {CLUB} Cinematic 16:9 composition, her face and forearms clearly "
             f"visible, soft neon rim light.")

# Scene A: the tasteful slow-dance (both characters). {A} / {B} are replaced by each model's reference syntax.
DUO_SCENE = ("Keep the man from {A} and the woman from {B} exactly the same (faces, hair, glasses, stubble, outfits, her silver "
             "mesh android details and iridescent eyes). New shot: the two of them slow-dancing close together in the middle "
             "of the Club Frontier dance floor, his hand resting on the small of her back, her arms draped around his neck, "
             "foreheads almost touching, eyes locked, tender and sensual but fully clothed. A warm amber spotlight on the "
             "couple, magenta and cyan neon haze around them, other dancers blurred in the background. Same painterly "
             "stylized 3D animation style as the references, not photorealistic. Cinematic 16:9 medium-wide shot.")
# Scene B: the singer alone from a very different angle, to test identity at a smaller scale.
SOLO_SCENE = ("Keep the man from {A} exactly the same (face, curly hair, dark-rimmed glasses, stubble, charcoal shawl-collar "
              "cardigan over a black t-shirt). New shot: a low-angle wide shot of him walking calmly toward the camera through "
              "a packed, frantic crowd of dancers in Club Frontier, the crowd motion-blurred around him while he stays sharp "
              "and serene, strobing magenta and cyan neon, haze, the glowing red BPM readout above the DJ booth behind him. "
              "Same painterly stylized 3D animation style as the reference, not photorealistic. Cinematic 16:9.")
