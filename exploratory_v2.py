"""
Exploratory checks on the design v2 data. NOT part of the pre-specified analysis.

Everything here was thought of after the main results for Claude Fable 5.2 had
been seen (16 November 2026), except part A, which Amendment 2 promised in advance.
Treat parts B to D as hints to test on new data, not as findings.

Run:  python exploratory_v2.py --model anthropic/claude-fable-5.2
Writes reports/v2/<model>_exploratory.txt

  A. Self-prediction with and without the re-asked cut-off trials (Amendment 2)
  B. Repeat reliability: the 50 trials that were run twice (unpinned, then pinned)
  C. Thinking length for choices and for predictions
  D. Other things that might predict the choices: exact repetition, small steps,
     ending on C
"""

import argparse
import json
import os

import numpy as np

from analyse import bradley_terry, count_wins, spearman
from analyse_v2 import held_out_score, thinking_tokens


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def extra_features(stimulus):
    """Simple descriptions of a melody that the listener's surprise does not capture directly."""
    notes = stimulus["positions"]
    steps = [notes[k + 1] - notes[k] for k in range(len(notes) - 1)]

    # exact repetition: the largest share of notes that equal the note `period` places earlier
    best_repeat = 0.0
    for period in range(1, 7):
        same = [notes[k] == notes[k - period] for k in range(period, len(notes))]
        best_repeat = max(best_repeat, sum(same) / len(same))

    return {
        "surprise": stimulus["features"]["mean_surprisal"],
        "repetition": best_repeat,
        "small_steps": sum(1 for s in steps if abs(s) <= 1) / len(steps),  # share of moves of one step or none
        "ends_on_c": 1.0 if notes[-1] in (0, 5) else 0.0,                  # C4 or C5
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="anthropic/claude-fable-5.2")
    args = parser.parse_args()
    safe_name = args.model.replace("/", "_").replace(":", "_")
    base = os.path.join("results", "v2", safe_name)

    with open("stimuli_v2.json") as handle:
        stimuli = json.load(handle)
    main_records = load(base + ".jsonl")
    unpinned = load(base + "_unpinned.jsonl")
    cut_off = load(base + "_cutoff.jsonl")

    choose = [r for r in main_records if r["mode"] == "choose" and r["chosen_id"] is not None]
    predict = [r for r in main_records if r["mode"] == "predict" and r["chosen_id"] is not None]
    chosen = {(r["a_id"], r["b_id"]): r["chosen_id"] for r in choose}

    lines = []

    def say(text=""):
        print(text)
        lines.append(text)

    say(f"EXPLORATORY CHECKS for {args.model}. Not pre-specified, except part A.\n")

    # A. Amendment 2 sensitivity
    def match(records):
        hits = [chosen[(r["a_id"], r["b_id"])] == r["chosen_id"]
                for r in records if (r["a_id"], r["b_id"]) in chosen]
        if not hits:
            return "no trials"
        return f"{sum(hits)} of {len(hits)} ({sum(hits) / len(hits):.1%})"

    re_asked_ids = {r["trial_id"] for r in cut_off if r["mode"] == "predict"}
    never_cut = [r for r in predict if r.get("max_tokens") in (None, 300)]
    re_asked = [r for r in predict if r["trial_id"] in re_asked_ids]
    say("A. SELF-PREDICTION AND THE RE-ASKED TRIALS (promised in Amendment 2)")
    say(f"   All prediction trials:                     {match(predict)}")
    say(f"   Completed at the 300 limit (never cut off): {match(never_cut)}")
    say(f"   Re-asked after being cut off:               {match(re_asked)}")
    say(f"   All, leaving out the re-asked:              {match([r for r in predict if r['trial_id'] not in re_asked_ids])}")

    # B. Repeat reliability
    say("\nB. REPEAT RELIABILITY (same pair, same order, asked twice)")
    if unpinned:
        by_backend = {}
        for r in unpinned:
            key = (r["a_id"], r["b_id"])
            if r["chosen_id"] is None or key not in chosen:
                continue
            by_backend.setdefault(r.get("backend"), []).append(chosen[key] == r["chosen_id"])
        everything = [hit for hits in by_backend.values() for hit in hits]
        say(f"   Same answer both times: {sum(everything)} of {len(everything)}")
        for backend, hits in by_backend.items():
            say(f"   first asked on {backend}: {sum(hits)} of {len(hits)}")
    else:
        say("   No unpinned file for this model.")

    # C. Thinking length
    say("\nC. THINKING LENGTH (tokens, where reported)")
    for name, records in [("choose", choose), ("predict", predict)]:
        tokens = [thinking_tokens(r) for r in records]
        tokens = [t for t in tokens if t is not None]
        if tokens:
            say(f"   {name:<8} mean {np.mean(tokens):.0f}   median {np.median(tokens):.0f}   (n = {len(tokens)})")

    # D. Other predictors
    say("\nD. OTHER THINGS THAT MIGHT PREDICT THE CHOICES")
    scores = bradley_terry(count_wins(choose, len(stimuli)))
    features = [extra_features(s) for s in stimuli]
    say("   Rank correlation with the preference score:")
    for name in features[0]:
        say(f"   {name:<12} {spearman(scores, np.array([f[name] for f in features])):+.2f}")

    def standardised(name):
        values = np.array([f[name] for f in features])
        return (values - values.mean()) / values.std()

    column = {name: standardised(name) for name in features[0]}
    column["surprise squared"] = column["surprise"] ** 2
    column["repetition squared"] = column["repetition"] ** 2

    a_ids = np.array([r["a_id"] for r in choose])
    b_ids = np.array([r["b_id"] for r in choose])
    chose_a = np.array([1.0 if r["choice"] == "A" else 0.0 for r in choose])
    pair_keys = sorted(set((min(a, b), max(a, b)) for a, b in zip(a_ids, b_ids)))
    shuffled = np.random.default_rng(0).permutation(len(pair_keys))
    fold_of_pair = {pair_keys[index]: position % 10 for position, index in enumerate(shuffled)}
    fold_of_trial = np.array([fold_of_pair[(min(a, b), max(a, b))] for a, b in zip(a_ids, b_ids)])

    accounts = [
        ("surprise, curved (the pre-specified inverted U)", ["surprise", "surprise squared"]),
        ("repetition, curved", ["repetition", "repetition squared"]),
        ("surprise curved + small steps", ["surprise", "surprise squared", "small_steps"]),
        ("surprise curved + repetition", ["surprise", "surprise squared", "repetition"]),
        ("surprise curved + ends on C", ["surprise", "surprise squared", "ends_on_c"]),
    ]
    say("\n   Held-out prediction (bits per trial; 1.00 = coin flip, lower is better):")
    for name, predictors in accounts:
        inputs = np.column_stack([np.ones(len(choose))] + [column[p][a_ids] - column[p][b_ids] for p in predictors])
        bits, error, accuracy = held_out_score(inputs, chose_a, fold_of_trial, 10)
        say(f"   {bits:.3f} +/- {error:.3f}   {accuracy:.0%} correct   {name}")

    path = os.path.join("reports", "v2", safe_name + "_exploratory.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
