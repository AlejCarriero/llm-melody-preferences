"""
Step 1: make the melodies.

Creates 18 short melodies (6 families x 3 examples each) and saves them to
stimuli.json, together with a few simple numbers describing each one
(how repetitive it is, how surprising it is, and so on).

Run:  python stimuli.py
"""

import json
import math
import random

# C major pentatonic over about an octave and a half. Every melody uses only these.
SCALE = ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5"]
LENGTH = 12          # notes per melody
EXAMPLES_PER_FAMILY = 3
SEED = 2026          # fixed so that everyone gets the same melodies


def clip(index):
    """Keep a scale position inside the scale."""
    return max(0, min(len(SCALE) - 1, index))


# ---------------------------------------------------------------------------
# The six families. Each function returns a list of 12 scale positions (0-7).
# They are ordered roughly from most predictable to least predictable.
# ---------------------------------------------------------------------------

def make_repeat(rng):
    """A 3-note motif played four times, unchanged."""
    motif = [rng.randrange(len(SCALE)) for _ in range(3)]
    return motif * 4


def make_scale_run(rng):
    """Walk up the scale and back down (or down and back up)."""
    start = rng.randrange(0, 3)
    up = [clip(start + step) for step in range(6)]
    down = list(reversed(up))
    if rng.random() < 0.5:
        return up + down
    return down + up


def make_motif_variation(rng):
    """A 4-note motif, then the same shape moved up a step, then a return with a new ending."""
    start = rng.randrange(1, 4)
    shape = [0, rng.choice([1, 2]), rng.choice([-1, 1]), rng.choice([0, 2])]
    motif = [clip(start + offset) for offset in shape]
    moved = [clip(note + 1) for note in motif]
    ending = motif[:2] + [clip(motif[1] - 1), motif[0]]
    return motif + moved + ending


def make_motif_surprise(rng):
    """A 3-note motif three times, then three notes that break the pattern."""
    low = rng.randrange(0, 3)
    motif = [low, clip(low + 1), clip(low + 2)]
    high = len(SCALE) - 1
    surprise = [high, clip(high - rng.choice([2, 3])), clip(low + rng.choice([0, 3]))]
    return motif * 3 + surprise


def make_random_walk(rng):
    """Each note is close to the previous one, but the direction is random."""
    position = rng.randrange(2, 6)
    notes = [position]
    while len(notes) < LENGTH:
        position = clip(position + rng.choice([-2, -1, -1, 1, 1, 2]))
        notes.append(position)
    return notes


def make_random(rng):
    """Every note picked independently at random."""
    return [rng.randrange(len(SCALE)) for _ in range(LENGTH)]


FAMILIES = [
    ("repeat", make_repeat),
    ("scale_run", make_scale_run),
    ("motif_variation", make_motif_variation),
    ("motif_surprise", make_motif_surprise),
    ("random_walk", make_random_walk),
    ("random", make_random),
]


# ---------------------------------------------------------------------------
# Features: simple numbers that describe each melody.
# ---------------------------------------------------------------------------

def pitch_entropy(notes):
    """How evenly the melody spreads over different pitches (in bits). 0 = one note only."""
    total = len(notes)
    entropy = 0.0
    for pitch in set(notes):
        share = notes.count(pitch) / total
        entropy -= share * math.log2(share)
    return entropy


def mean_interval(notes):
    """Average jump size between neighbouring notes, in scale steps."""
    jumps = [abs(notes[k + 1] - notes[k]) for k in range(len(notes) - 1)]
    return sum(jumps) / len(jumps)


def bigram_novelty(notes):
    """Share of note-to-note transitions that are distinct. Low = repetitive."""
    transitions = [(notes[k], notes[k + 1]) for k in range(len(notes) - 1)]
    return len(set(transitions)) / len(transitions)


def surprisal_per_note(notes):
    """
    Imagine a listener who starts knowing nothing and learns as the melody plays.
    Before each note they guess what comes next, based only on which note has
    followed the current note so far in this melody. Surprisal is how unexpected
    the actual note was (in bits). Returns one value per note from the 2nd onward.
    """
    number_of_pitches = len(SCALE)
    counts = {}  # counts[previous_note][next_note]
    surprisals = []
    for k in range(1, len(notes)):
        previous_note = notes[k - 1]
        next_note = notes[k]
        seen = counts.get(previous_note, {})
        seen_total = sum(seen.values())
        # add-one smoothing: every pitch starts with one imaginary observation
        probability = (seen.get(next_note, 0) + 1) / (seen_total + number_of_pitches)
        surprisals.append(-math.log2(probability))
        counts.setdefault(previous_note, {})
        counts[previous_note][next_note] = counts[previous_note].get(next_note, 0) + 1
    return surprisals


def describe(notes):
    surprisals = surprisal_per_note(notes)
    half = len(surprisals) // 2
    first_half = sum(surprisals[:half]) / half
    second_half = sum(surprisals[half:]) / (len(surprisals) - half)
    return {
        "pitch_entropy": round(pitch_entropy(notes), 3),
        "mean_interval": round(mean_interval(notes), 3),
        "bigram_novelty": round(bigram_novelty(notes), 3),
        "mean_surprisal": round(sum(surprisals) / len(surprisals), 3),
        # positive = the melody becomes easier to predict as it goes on
        "learning_progress": round(first_half - second_half, 3),
    }


def main():
    rng = random.Random(SEED)
    stimuli = []
    for family_name, make in FAMILIES:
        made = []
        while len(made) < EXAMPLES_PER_FAMILY:
            notes = make(rng)
            if notes not in made:
                made.append(notes)
        for notes in made:
            stimuli.append({
                "id": len(stimuli),
                "family": family_name,
                "positions": notes,
                "text": " ".join(SCALE[n] for n in notes),
                "features": describe(notes),
            })

    # newline="\n" so Windows writes the same bytes as the committed file
    with open("stimuli.json", "w", newline="\n") as handle:
        json.dump(stimuli, handle, indent=2)

    print(f"Saved {len(stimuli)} melodies to stimuli.json\n")
    for s in stimuli:
        print(f"S{s['id']:02d}  {s['family']:<16} {s['text']}   surprisal={s['features']['mean_surprisal']}")


if __name__ == "__main__":
    main()
