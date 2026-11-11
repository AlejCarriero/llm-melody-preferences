"""
Step 4: make the melodies audible.

Writes one .wav file per melody into the audio/ folder, using plain sine tones.
If you name a model that has been analysed, the file names start with that
model's rank, so its favourites sort to the top and its least favourites to
the bottom.

Run:
  python make_audio.py                           # plain names -> audio/
  python make_audio.py --model claude-fable-5-2  # ranked names -> audio/claude-fable-5-2/
"""

import argparse

import csv
import json
import math
import os
import struct
import wave

SAMPLE_RATE = 44100
NOTE_SECONDS = 0.30
VOLUME = 0.4

# semitones above C for each note letter used in the scale
SEMITONES = {"C": 0, "D": 2, "E": 4, "G": 7, "A": 9}


def frequency(note_name):
    """Convert a name like 'A4' to a frequency in Hz (A4 = 440)."""
    letter = note_name[0]
    octave = int(note_name[1])
    semitones_from_a4 = SEMITONES[letter] - 9 + 12 * (octave - 4)
    return 440.0 * (2 ** (semitones_from_a4 / 12))


def tone(note_name):
    """One note as a list of samples, with a soft start and end so it doesn't click."""
    hz = frequency(note_name)
    total = int(SAMPLE_RATE * NOTE_SECONDS)
    fade = int(SAMPLE_RATE * 0.02)
    samples = []
    for k in range(total):
        loudness = VOLUME
        if k < fade:
            loudness *= k / fade
        elif k > total - fade:
            loudness *= (total - k) / fade
        samples.append(loudness * math.sin(2 * math.pi * hz * k / SAMPLE_RATE))
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    with open("stimuli.json") as handle:
        stimuli = json.load(handle)

    rank_of = {}
    folder = "audio"
    if args.model:
        safe_name = args.model.replace("/", "_").replace(":", "_")
        ranking_path = os.path.join("reports", safe_name + "_ranking.csv")
        if not os.path.exists(ranking_path):
            print(f"No {ranking_path} yet. Run analyse.py --model {args.model} first.")
            return
        with open(ranking_path) as handle:
            for row in csv.DictReader(handle):
                rank_of[int(row["id"])] = int(row["rank"])
        folder = os.path.join("audio", safe_name)

    os.makedirs(folder, exist_ok=True)
    for s in stimuli:
        samples = []
        for note_name in s["text"].split():
            samples.extend(tone(note_name))

        name = f"S{s['id']:02d}_{s['family']}.wav"
        if s["id"] in rank_of:
            name = f"rank{rank_of[s['id']]:02d}_{name}"
        path = os.path.join(folder, name)

        with wave.open(path, "w") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(SAMPLE_RATE)
            out.writeframes(b"".join(struct.pack("<h", int(v * 32767)) for v in samples))
        print("wrote", path)


if __name__ == "__main__":
    main()
