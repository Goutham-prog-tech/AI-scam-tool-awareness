"""
Creates the built-in MALE and FEMALE voice clips (English, Telugu, Hindi) that the website plays.
These clips sound the same on every phone and laptop, even when the device has no Telugu voice.

Run it ONCE on your own computer (it needs internet):

    pip install edge-tts
    python make_voice_clips.py

It writes the files into  static/audio/  (about 85 small .mp3 files plus manifest.json).
Then upload the  static/audio  folder to GitHub, like your other folders.

Options:
    --force            create every clip again, even if it already exists
    --male-pitch -20   make the male voice even deeper (default -14, in Hz)
"""
import argparse
import asyncio
import json
import os
import sys

try:
    import edge_tts
except ImportError:
    sys.exit("edge-tts is not installed. Run:  pip install edge-tts   and then run this file again.")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "static", "audio")

VOICES = {   # Microsoft neural voices (India)
    "en": {"female": "en-IN-NeerjaNeural", "male": "en-IN-PrabhatNeural"},
    "te": {"female": "te-IN-ShrutiNeural", "male": "te-IN-MohanNeural"},
    "hi": {"female": "hi-IN-SwaraNeural", "male": "hi-IN-MadhurNeural"},
}


async def make_one(sem, text, voice, rate, pitch, path):
    async with sem:
        last = None
        for attempt in range(1, 5):
            try:
                await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(path)
                if os.path.getsize(path) > 1000:
                    return True
            except Exception as e:           # network hiccup: wait and retry
                last = e
            await asyncio.sleep(2 * attempt)
        print(f"   FAILED: {os.path.basename(path)}  ({last})")
        if os.path.exists(path):
            os.remove(path)
        return False


async def main(force, male_pitch):
    texts = json.load(open(os.path.join(HERE, "voice_texts.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    settings = {"female": ("-5%", "+0Hz"), "male": ("-8%", f"{male_pitch:+d}Hz")}
    sem = asyncio.Semaphore(3)
    jobs = []
    for lang, clips in texts.items():
        for gender, voice in VOICES[lang].items():
            rate, pitch = settings[gender]
            for name, text in clips.items():
                path = os.path.join(OUT, f"{lang}_{gender}_{name}.mp3")
                if force or not os.path.exists(path):
                    jobs.append(make_one(sem, text, voice, rate, pitch, path))
    print(f"Creating {len(jobs)} clips (this takes a few minutes)...")
    results = await asyncio.gather(*jobs)

    manifest = {"version": 1, "clips": {}}
    total = 0
    for lang, clips in texts.items():
        manifest["clips"][lang] = {}
        for gender in VOICES[lang]:
            have = [n for n in clips if os.path.exists(os.path.join(OUT, f"{lang}_{gender}_{n}.mp3"))]
            manifest["clips"][lang][gender] = have if len(have) == len(clips) else []   # only complete sets are used
            total += len(have)
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print(f"Done: {sum(results)} new clips, {total} clips in total.")
    for lang in manifest["clips"]:
        for gender, names in manifest["clips"][lang].items():
            print(f"  {lang} {gender}: {'READY' if names else 'INCOMPLETE - run the script again'}")
    print("Next: upload the  static/audio  folder to GitHub.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--male-pitch", type=int, default=-14)
    a = ap.parse_args()
    asyncio.run(main(a.force, a.male_pitch))
