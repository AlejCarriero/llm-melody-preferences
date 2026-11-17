"""
Exploratory: how reliable is each model's ranking, and how much do the models
agree once that is allowed for? NOT pre-specified; written on 17 November 2026
after the comparison results had been seen.

Reliability: each pair was shown once in each order. The ranking from one order is
correlated with the ranking from the other (split-half), then stepped up to the
full data with the Spearman-Brown formula. A noisy ranking cannot correlate highly
with anything, so between-model correlations are also shown divided by the square
root of the two reliabilities (the classical correction for attenuation). The
correction is undefined when a reliability is zero or negative.

Run:  python exploratory_models.py
"""

import glob
import itertools
import json
import os

import numpy as np

from analyse import bradley_terry, count_wins, spearman


def load_choices(path):
    with open(path, encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    return [r for r in records if r["mode"] == "choose" and r["chosen_id"] is not None]


def main():
    with open("stimuli_v2.json") as handle:
        count = len(json.load(handle))

    models = {}
    for path in sorted(glob.glob(os.path.join("results", "v2", "*.jsonl"))):
        name = os.path.basename(path)[:-len(".jsonl")]
        if name == "dryrun" or name.endswith("_unpinned") or name.endswith("_cutoff"):
            continue
        models[name] = load_choices(path)

    full = {}
    reliability = {}
    print("RELIABILITY OF EACH MODEL'S RANKING (exploratory)")
    for name, choices in models.items():
        full[name] = bradley_terry(count_wins(choices, count))
        first_order = [r for r in choices if r["a_id"] < r["b_id"]]
        second_order = [r for r in choices if r["a_id"] > r["b_id"]]
        split = spearman(bradley_terry(count_wins(first_order, count)),
                         bradley_terry(count_wins(second_order, count)))
        reliability[name] = 2 * split / (1 + split) if split > 0 else split
        print(f"  {name:<34} split-half {split:+.2f}   reliability {reliability[name]:+.2f}")

    print("\nAGREEMENT BETWEEN MODELS: raw rank correlation, and corrected for reliability")
    for first, second in itertools.combinations(models, 2):
        raw = spearman(full[first], full[second])
        if reliability[first] > 0 and reliability[second] > 0:
            corrected = f"{raw / np.sqrt(reliability[first] * reliability[second]):+.2f}"
        else:
            corrected = "undefined"
        print(f"  {first:<34} {second:<34} raw {raw:+.2f}   corrected {corrected}")
    print("\nA corrected value above 1 means the estimate is noisy, not that agreement exceeds 1.")


if __name__ == "__main__":
    main()
