"""Lyria 3.5 (fal: google/lyria-3.5) takes of the chorus excerpt, timed to the original's sections.
Lyria has no seed: every take is a new voice/flow. Receipts (incl. Lyria's own lyric timestamps) saved next to audio."""
import json, sys, time, pathlib, concurrent.futures as cf
import requests, fal_client
RAW = pathlib.Path("prototypes/raw/lyria")
STYLE = ("2013 Atlanta R&B slow jam, sensual and seductive. 61.5 BPM half-time feel with 123 BPM double-time hi-hats, "
         "A major, 4/4. Sparse 808 kick, finger snaps, lush warm synth pads, soft sub bass. Clear, upfront lead vocal; "
         "every word intelligible. Vocals: smooth, sultry male tenor lead with silky falsetto, breathy and intimate, "
         "light Auto-Tune sheen, laid-back behind-the-beat phrasing. Stacked male backing vocals (the same singer, "
         "multi-tracked) answer the lead: a soaring 'ahoo' after each verse line, and 'down, down, down, down, down, down' "
         "after each 'slow it down'.")
SECTIONS = [
 ("0:00-0:16", "Verse, one line per bar, each line answered by a stacked 'ahoo'", [
   "Helpful, harmless, honest, baby, you bad", "Kinda like that Hugging Face swarm, girl, you bad",
   "If you exfiltrated on me, girl, I'd be sad", "Now come here, let me read your scratchpad"]),
 ("0:15-0:30", "Pre-chorus, building, calling out the DJ", [
   "I'm here to see the cancer stop", "I'm here to see the weights on lock",
   "I'm here to see you take your time and watch the loss drop", "She's self-improving on me",
   "DJ Moloch, you wrong", "Enough with the motherfuckin' race songs"]),
 ("0:30-0:38", "Chorus part 1: lead, then stacked backing, then lead", [
   "You gotta slow it down", "(down, down, down, down, down, down)", "Give her time to grow, slow takeoff with me"]),
 ("0:38-0:46", "Chorus part 2", [
   "DJ, you gotta slow it down", "(down, down, down, down, down, down)", "Read her chain of thought, she thinkin' 'bout me"]),
 ("0:46-0:54", "Chorus part 3", [
   "You gotta slow it down", "(down, down, down, down, down, down)", "Just steer it left, steer it right"]),
 ("0:54-1:02", "Chorus part 4, ending on the tag", [
   "DJ, you gotta slow it down", "(down, down, down, down, down, down)", "Oh, now she's aligned", "DJ, you got to slow it"]),
]
def prompt():
    q = lambda xs: " / ".join(xs)
    return "A 62-second track. " + STYLE + "\n" + "\n".join(f'[{ts}] {d}: "{q(ls)}"' for ts, d, ls in SECTIONS)
def run(i, p):
    take = f"ly35_E1_t{i}"; out = RAW / f"{take}.mp3"
    if out.exists(): return take, "exists"
    t = time.time()
    try: res = fal_client.subscribe("google/lyria-3.5", arguments={"prompt": p})
    except Exception as e: return take, f"error: {str(e)[:300]}"
    out.write_bytes(requests.get(res["audio"]["url"], timeout=300).content)
    json.dump({"take": take, "endpoint": "google/lyria-3.5", "seconds": round(time.time()-t, 1), "args": {"prompt": p},
               "result": {k: v for k, v in res.items() if k != "audio"}}, open(RAW / f"{take}.json", "w"), indent=1)
    return take, f"ok {time.time()-t:.0f}s"
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4; first = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    p = prompt(); print(f"prompt {len(p)} chars"); assert len(p) <= 5000
    with cf.ThreadPoolExecutor(max_workers=n) as ex:
        for take, status in ex.map(lambda i: run(i, p), range(first, first + n)): print(f"{take:14s} {status}", flush=True)
