"""
Design v2, step 1: make the melodies and choose which pairs to compare.

What changed from v1, and why:
  - 60 melodies of 24 notes (was 18 of 12). More melodies let us tell hypotheses
    apart; longer ones leave room for a listener to learn the pattern.
  - The melodies now span the whole range from fully predictable (one repeated
    note) to fully random, including a family where a repeating motif is
    corrupted by a controlled amount of noise.
  - Surprise comes from a better listener (see `listen` below). It predicts both
    pitches and intervals, so a scale run counts as predictable.
  - Not every pair is compared. Each melody meets 12 others, chosen at random,
    and every chosen pair is shown in both orders.

Writes stimuli_v2.json and pairs_v2.json. These two files ARE the experiment,
so the script refuses to overwrite them unless you pass --force.

Run:  python stimuli_v2.py
"""

import argparse
import json
import math
import os
import random

SCALE = ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5"]   # C major pentatonic
NUMBER_OF_PITCHES = len(SCALE)
LENGTH = 24
SEED = 2026
PARTNERS_PER_MELODY = 12     # how many other melodies each melody is compared with
SMOOTHING = 0.25             # how quickly the listener trusts a pattern (smaller = quicker)


def clip(position):
    """Keep a scale position inside the scale."""
    return max(0, min(NUMBER_OF_PITCHES - 1, position))


def repeat_to_length(motif):
    """Repeat a short motif until it fills the melody."""
    notes = []
    while len(notes) < LENGTH:
        notes.extend(motif)
    return notes[:LENGTH]


def random_motif(rng, size):
    """A motif of `size` notes with no immediate repeats."""
    motif = [rng.randrange(NUMBER_OF_PITCHES)]
    while len(motif) < size:
        candidate = rng.randrange(NUMBER_OF_PITCHES)
        if candidate != motif[-1]:
            motif.append(candidate)
    return motif


# ---------------------------------------------------------------------------
# Families, ordered roughly from most to least predictable.
# Each function returns a list of 24 scale positions (0-7).
# ---------------------------------------------------------------------------

def make_trivial(rng):
    """One note throughout, or two notes alternating."""
    first = rng.randrange(NUMBER_OF_PITCHES)
    if rng.random() < 0.5:
        return [first] * LENGTH
    second = clip(first + rng.choice([-2, -1, 1, 2]))
    if second == first:
        second = clip(first + 3) if first < 4 else clip(first - 3)
    return repeat_to_length([first, second])


def make_repeat(rng):
    """A 3- or 4-note motif repeated unchanged."""
    return repeat_to_length(random_motif(rng, rng.choice([3, 4])))


def make_scale_run(rng):
    """Straight runs up and down the scale, or a zigzag that climbs step by step."""
    if rng.random() < 0.5:
        start = rng.randrange(0, 2)
        up = [clip(start + step) for step in range(7 - start + 1)]
        down = list(reversed(up))[1:-1]
        cycle = up + down
        if rng.random() < 0.5:
            cycle = list(reversed(cycle))
        return repeat_to_length(cycle)
    # zigzag: up two, back one, and so on, then the same in reverse
    start = rng.randrange(0, 2)
    climb = []
    for step in range(4):
        climb.extend([clip(start + step), clip(start + step + 1), clip(start + step + 2)])
    fall = list(reversed(climb))
    return (climb + fall)[:LENGTH]


def make_motif_variation(rng):
    """A 4-note motif stated six times: moved up, brought back, moved further, with a new ending."""
    start = rng.randrange(1, 3)
    shape = [0, rng.choice([1, 2]), rng.choice([-1, 1]), rng.choice([0, 2])]
    motif = [clip(start + offset) for offset in shape]

    def moved(amount):
        return [clip(note + amount) for note in motif]

    ending = motif[:2] + [clip(motif[1] - 1), motif[0]]
    return motif + moved(1) + motif + moved(2) + moved(1) + ending


def make_motif_surprise(rng):
    """A repeated motif that is broken once: either at the very end or two-thirds through."""
    motif = random_motif(rng, rng.choice([3, 4]))
    notes = repeat_to_length(motif)
    if rng.random() < 0.5:
        positions = range(LENGTH - 4, LENGTH)          # the last four notes break away
    else:
        positions = range(15, 17)                      # two deviant notes, then the motif resumes
    for position in positions:
        replacement = rng.randrange(NUMBER_OF_PITCHES)
        while replacement == notes[position]:
            replacement = rng.randrange(NUMBER_OF_PITCHES)
        notes[position] = replacement
    return notes


def make_noisy_motif(rng, noise):
    """A repeated motif in which each note is replaced by a random one with probability `noise`."""
    notes = repeat_to_length(random_motif(rng, 4))
    for position in range(4, LENGTH):                  # the first statement is left intact
        if rng.random() < noise:
            notes[position] = rng.randrange(NUMBER_OF_PITCHES)
    return notes


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
    return [rng.randrange(NUMBER_OF_PITCHES) for _ in range(LENGTH)]


# (family name, how many to make, function)
FAMILIES = [
    ("trivial", 6, make_trivial),
    ("repeat", 8, make_repeat),
    ("scale_run", 6, make_scale_run),
    ("motif_variation", 8, make_motif_variation),
    ("motif_surprise", 8, make_motif_surprise),
    ("noisy_motif_15", 4, lambda rng: make_noisy_motif(rng, 0.15)),
    ("noisy_motif_30", 4, lambda rng: make_noisy_motif(rng, 0.30)),
    ("noisy_motif_50", 4, lambda rng: make_noisy_motif(rng, 0.50)),
    ("random_walk", 6, make_random_walk),
    ("random", 6, make_random),
]


# ---------------------------------------------------------------------------
# The listener: where "surprise" comes from.
# ---------------------------------------------------------------------------

def listen(notes):
    """
    An idealised listener hears the melody one note at a time. Before each note
    it holds a probability for each of the 8 possible pitches; after hearing the
    note it updates. It starts every melody knowing nothing.

    It is a committee of seven simple predictors:
      - how common each pitch has been so far                         (1 predictor)
      - which pitch has followed the last 1, 2 or 3 pitches           (3 predictors)
      - which interval has followed the last 1, 2 or 3 intervals      (3 predictors)
    The committee's prediction is a weighted average. A predictor's weight grows
    each time it gives the note that actually came a high probability, so the
    listener learns which way of hearing suits this melody (Bayesian model
    averaging). The interval predictors are what make a scale run predictable.

    Returns two lists, one value per note from the 2nd onward:
      surprisal    -log2 of the probability given to the note that came (bits)
      uncertainty  entropy of the prediction before the note was heard (bits)
    """
    predictor_names = ["pitch0", "pitch1", "pitch2", "pitch3", "interval1", "interval2", "interval3"]
    counts = {name: {} for name in predictor_names}      # counts[name][context][outcome]
    weights = {name: 1.0 / len(predictor_names) for name in predictor_names}

    def context_for(name, position):
        """What this predictor looks at just before `position`. None if not enough notes yet."""
        if name == "pitch0":
            return ()
        order = int(name[-1])
        if name.startswith("pitch"):
            if position < order:
                return None
            return tuple(notes[position - order:position])
        if position < order + 1:
            return None
        return tuple(notes[k] - notes[k - 1] for k in range(position - order, position))

    def outcome_for(name, position, pitch):
        """How this predictor describes `pitch` arriving at `position`."""
        if name.startswith("interval"):
            return pitch - notes[position - 1]
        return pitch

    def predict(name, position):
        """This predictor's probability for each of the 8 pitches."""
        context = context_for(name, position)
        if context is None:
            return [1.0 / NUMBER_OF_PITCHES] * NUMBER_OF_PITCHES
        seen = counts[name].get(context, {})
        raw = [seen.get(outcome_for(name, position, pitch), 0) + SMOOTHING
               for pitch in range(NUMBER_OF_PITCHES)]
        total = sum(raw)
        return [value / total for value in raw]

    surprisal = []
    uncertainty = []
    for position in range(1, len(notes)):
        predictions = {name: predict(name, position) for name in predictor_names}
        combined = [sum(weights[name] * predictions[name][pitch] for name in predictor_names)
                    for pitch in range(NUMBER_OF_PITCHES)]

        actual = notes[position]
        surprisal.append(-math.log2(combined[actual]))
        uncertainty.append(-sum(p * math.log2(p) for p in combined if p > 0))

        # reward the predictors that saw this note coming
        for name in predictor_names:
            weights[name] *= predictions[name][actual]
        weight_total = sum(weights.values())
        for name in predictor_names:
            weights[name] /= weight_total

        # every predictor remembers what happened (including the very first note for pitch0)
        for name in predictor_names:
            context = context_for(name, position)
            if context is None:
                continue
            outcome = outcome_for(name, position, actual)
            counts[name].setdefault(context, {})
            counts[name][context][outcome] = counts[name][context].get(outcome, 0) + 1
    return surprisal, uncertainty


def describe(notes):
    surprisal, uncertainty = listen(notes)
    half = len(surprisal) // 2
    first_half = sum(surprisal[:half]) / half
    second_half = sum(surprisal[half:]) / (len(surprisal) - half)

    pitch_entropy = 0.0
    for pitch in set(notes):
        share = notes.count(pitch) / len(notes)
        pitch_entropy -= share * math.log2(share)
    jumps = [abs(notes[k + 1] - notes[k]) for k in range(len(notes) - 1)]

    return {
        "mean_surprisal": round(sum(surprisal) / len(surprisal), 3),
        # positive = the melody becomes easier to predict as it goes on
        "learning_progress": round(first_half - second_half, 3),
        "mean_uncertainty": round(sum(uncertainty) / len(uncertainty), 3),
        "pitch_entropy": round(pitch_entropy, 3),
        "mean_interval": round(sum(jumps) / len(jumps), 3),
    }


def choose_pairs(number_of_melodies, rng):
    """
    Pick which melodies meet. In each round every melody is paired with exactly
    one other; rounds are repeated until each melody has met PARTNERS_PER_MELODY
    different partners. Returns a list of [x, y] pairs in the order they were drawn.
    """
    pairs = []
    used = set()
    for _ in range(PARTNERS_PER_MELODY):
        while True:
            order = list(range(number_of_melodies))
            rng.shuffle(order)
            round_pairs = [tuple(sorted((order[k], order[k + 1]))) for k in range(0, len(order), 2)]
            if not any(pair in used for pair in round_pairs):
                break
        used.update(round_pairs)
        pairs.extend([list(pair) for pair in round_pairs])
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="overwrite the existing design files")
    args = parser.parse_args()

    for path in ["stimuli_v2.json", "pairs_v2.json"]:
        if os.path.exists(path) and not args.force:
            print(f"{path} already exists. It defines the experiment, so it is not overwritten.")
            print("Use --force only if no data has been collected with it yet.")
            return

    rng = random.Random(SEED)
    stimuli = []
    for family_name, how_many, make in FAMILIES:
        made = []
        while len(made) < how_many:
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

    pairs = choose_pairs(len(stimuli), rng)

    # newline="\n" keeps the files byte-for-byte identical on Windows, Mac and Linux
    with open("stimuli_v2.json", "w", newline="\n") as handle:
        json.dump(stimuli, handle, indent=2)
    with open("pairs_v2.json", "w", newline="\n") as handle:
        json.dump(pairs, handle)

    print(f"Saved {len(stimuli)} melodies and {len(pairs)} pairs.\n")
    for s in stimuli:
        f = s["features"]
        print(f"S{s['id']:02d} {s['family']:<16} surprisal {f['mean_surprisal']:.2f}  "
              f"learning {f['learning_progress']:+.2f}  {s['text']}")


if __name__ == "__main__":
    main()
