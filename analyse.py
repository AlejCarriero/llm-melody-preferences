"""
Step 3: look at the answers.

Reads stimuli.json and the results file, prints a report, and saves
report.txt and ranking.csv.

Run:
  python analyse.py                          # the default model
  python analyse.py --model SOME/MODEL:free  # another model
  python analyse.py --dry-run                # the fake data

Reads results/<model>.jsonl and writes reports/<model>_report.txt and
reports/<model>_ranking.csv.

The report answers five questions:
  1. Position bias   - does the model just tend to say "A"?
  2. Consistency     - do separate instances agree on which melody is preferred?
  3. Ranking         - which melodies and families win most?
  4. Transitivity    - if X beats Y and Y beats Z, does X beat Z?
  5. What predicts it, and can the model predict itself?
"""

import argparse
import itertools
import json
import os

import numpy as np

FEATURES = ["pitch_entropy", "mean_interval", "bigram_novelty", "mean_surprisal", "learning_progress"]


def load_results(path):
    records = []
    with open(path) as handle:
        for line in handle:
            records.append(json.loads(line))
    return records


def count_wins(records, number_of_stimuli):
    """wins[x][y] = how many times x was chosen when shown together with y."""
    wins = np.zeros((number_of_stimuli, number_of_stimuli))
    for record in records:
        chosen = record["chosen_id"]
        if chosen is None:
            continue
        other = record["b_id"] if chosen == record["a_id"] else record["a_id"]
        wins[chosen][other] += 1
    return wins


def consistency_score(wins):
    """
    For each pair, take the share of trials won by the more popular melody
    (0.5 = a coin flip, 1.0 = every instance agreed). Average over pairs.
    """
    shares = []
    for x, y in itertools.combinations(range(len(wins)), 2):
        total = wins[x][y] + wins[y][x]
        if total > 0:
            shares.append(max(wins[x][y], wins[y][x]) / total)
    return float(np.mean(shares))


def consistency_if_no_preference(records, number_of_stimuli, share_a, rounds=1000):
    """
    What would the consistency score be if the model had no preferences at all
    and only its habit of saying "A" at the observed rate? Simulate that many
    times so we know what "nothing going on" looks like.
    """
    rng = np.random.default_rng(0)
    valid = [r for r in records if r["chosen_id"] is not None]
    scores = []
    for _ in range(rounds):
        wins = np.zeros((number_of_stimuli, number_of_stimuli))
        picks_a = rng.random(len(valid)) < share_a
        for record, picked_a in zip(valid, picks_a):
            if picked_a:
                wins[record["a_id"]][record["b_id"]] += 1
            else:
                wins[record["b_id"]][record["a_id"]] += 1
        scores.append(consistency_score(wins))
    return float(np.mean(scores)), float(np.percentile(scores, 95))


def bradley_terry(wins, rounds=500):
    """
    Turn pairwise wins into one score per melody (higher = preferred more).
    This is the standard Bradley-Terry model, the same idea as chess ratings.
    """
    count = len(wins)
    smoothed = wins + 0.5 * (1 - np.eye(count)) * ((wins + wins.T) > 0)  # avoids infinite scores
    games = smoothed + smoothed.T
    strength = np.ones(count)
    for _ in range(rounds):
        for x in range(count):
            denominator = 0.0
            for y in range(count):
                if x != y and games[x][y] > 0:
                    denominator += games[x][y] / (strength[x] + strength[y])
            if denominator > 0:
                strength[x] = smoothed[x].sum() / denominator
        strength = strength / np.exp(np.mean(np.log(strength)))
    return np.log(strength)


def circular_triads(wins):
    """Count triples where X beats Y, Y beats Z, but Z beats X (majority vote each time)."""
    count = len(wins)
    circular = 0
    usable = 0
    for x, y, z in itertools.combinations(range(count), 3):
        pairs = [(x, y), (y, z), (x, z)]
        if any(wins[p][q] == wins[q][p] for p, q in pairs):
            continue  # skip triples that contain a tie or a missing pair
        usable += 1
        x_beats_y = wins[x][y] > wins[y][x]
        y_beats_z = wins[y][z] > wins[z][y]
        x_beats_z = wins[x][z] > wins[z][x]
        if (x_beats_y and y_beats_z and not x_beats_z) or (not x_beats_y and not y_beats_z and x_beats_z):
            circular += 1
    return circular, usable


def ranks(values):
    """Rank values from 1 upward, giving tied values the same average rank."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    result = np.zeros(len(values))
    result[order] = np.arange(1, len(values) + 1)
    for value in np.unique(values):
        tied = values == value
        result[tied] = result[tied].mean()
    return result


def spearman(first, second):
    """Rank correlation, from -1 to 1."""
    first_ranks = ranks(first)
    second_ranks = ranks(second)
    if first_ranks.std() == 0 or second_ranks.std() == 0:
        return float("nan")
    return float(np.corrcoef(first_ranks, second_ranks)[0, 1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="analyse the fake data instead")
    parser.add_argument("--model", default="claude-fable-5-2")
    args = parser.parse_args()
    model = "dryrun" if args.dry_run else args.model
    safe_name = model.replace("/", "_").replace(":", "_")
    results_file = os.path.join("results", safe_name + ".jsonl")

    with open("stimuli.json") as handle:
        stimuli = json.load(handle)
    count = len(stimuli)

    if not os.path.exists(results_file):
        print(f"No {results_file} yet. Run run_trials.py first.")
        return
    records = load_results(results_file)
    choose = [r for r in records if r["mode"] == "choose"]
    predict = [r for r in records if r["mode"] == "predict"]
    describe = [r for r in records if r["mode"] == "describe"]

    lines = []

    def say(text=""):
        print(text)
        lines.append(text)

    say(f"Model: {model}\n")
    if args.dry_run:
        say("*** FAKE DATA (dry run). These numbers say nothing about the real model. ***\n")

    if not choose:
        say("No 'choose' trials yet.")
        return

    valid = [r for r in choose if r["chosen_id"] is not None]
    say(f"Choice trials: {len(choose)}  (unusable replies: {len(choose) - len(valid)})")

    # 1. Position bias
    share_a = sum(1 for r in valid if r["choice"] == "A") / len(valid)
    say("\n1. POSITION BIAS")
    say(f"   Answered 'A' on {share_a:.1%} of trials (50% = no bias).")

    # 2. Consistency
    wins = count_wins(valid, count)
    observed = consistency_score(wins)
    null_mean, null_95 = consistency_if_no_preference(valid, count, share_a)
    say("\n2. CONSISTENCY ACROSS INSTANCES")
    say(f"   Average agreement per pair: {observed:.3f}")
    say(f"   Expected with no preferences at all: {null_mean:.3f} (95% of simulations below {null_95:.3f})")
    if observed > null_95:
        say("   -> Above what chance alone produces: choices depend on the melody.")
    else:
        say("   -> Not distinguishable from chance: no evidence of stable preferences.")

    # 3. Ranking
    scores = bradley_terry(wins)
    order = np.argsort(-scores)
    say("\n3. RANKING (most preferred first)")
    for position, index in enumerate(order, start=1):
        s = stimuli[index]
        say(f"   {position:>2}. S{s['id']:02d} {s['family']:<16} score {scores[index]:+.2f}   {s['text']}")
    say("\n   Family averages:")
    families = sorted(set(s["family"] for s in stimuli),
                      key=lambda f: -np.mean([scores[s["id"]] for s in stimuli if s["family"] == f]))
    for family in families:
        family_mean = np.mean([scores[s["id"]] for s in stimuli if s["family"] == family])
        say(f"   {family:<16} {family_mean:+.2f}")

    # 4. Transitivity
    circular, usable = circular_triads(wins)
    say("\n4. TRANSITIVITY")
    if usable:
        say(f"   Circular triples: {circular} of {usable} ({circular / usable:.1%}). "
            f"Random choices would give about 25%.")
    else:
        say("   Not enough data yet.")

    # 5a. Features
    say("\n5. WHAT PREDICTS THE RANKING")
    say("   Rank correlation between preference score and each feature (-1 to +1).")
    say("   'middle' tests an inverted U: are melodies near the middle of the range preferred?")
    for feature in FEATURES:
        values = np.array([s["features"][feature] for s in stimuli])
        straight = spearman(scores, values)
        middle = spearman(scores, -np.abs(values - np.median(values)))
        say(f"   {feature:<18} linear {straight:+.2f}   middle {middle:+.2f}")

    # 5b. Self-prediction
    predict_valid = [r for r in predict if r["chosen_id"] is not None]
    if predict_valid:
        predicted_wins = count_wins(predict_valid, count)
        matches = 0
        compared = 0
        for x, y in itertools.combinations(range(count), 2):
            actual_gap = wins[x][y] - wins[y][x]
            predicted_gap = predicted_wins[x][y] - predicted_wins[y][x]
            if actual_gap == 0 or predicted_gap == 0:
                continue
            compared += 1
            if (actual_gap > 0) == (predicted_gap > 0):
                matches += 1
        predicted_scores = bradley_terry(predicted_wins)
        say("\n   SELF-PREDICTION")
        say(f"   Predicted the majority choice on {matches} of {compared} pairs "
            f"({matches / max(compared, 1):.1%}; 50% = guessing).")
        say(f"   Rank correlation between predicted and actual ranking: {spearman(scores, predicted_scores):+.2f}")
    else:
        say("\n   (No 'predict' trials yet.)")

    if describe:
        say("\n   STATED THEORIES (what instances said would drive their choices)")
        for record in describe:
            say(f"   - {record['reply'].strip()}")

    os.makedirs("reports", exist_ok=True)
    report_path = os.path.join("reports", safe_name + "_report.txt")
    ranking_path = os.path.join("reports", safe_name + "_ranking.csv")
    with open(report_path, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    with open(ranking_path, "w") as handle:
        handle.write("rank,id,family,score,melody\n")
        for position, index in enumerate(order, start=1):
            s = stimuli[index]
            handle.write(f"{position},{s['id']},{s['family']},{scores[index]:.3f},{s['text']}\n")
    print(f"\nSaved {report_path} and {ranking_path}")


if __name__ == "__main__":
    main()
