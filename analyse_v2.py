"""
Design v2, step 3: look at the answers.

Run:
  python analyse_v2.py --model anthropic/claude-fable-5.2
  python analyse_v2.py --dry-run

Reads results/v2/<model>.jsonl and writes reports/v2/<model>_report.txt and
reports/v2/<model>_ranking.csv.

The report has seven parts:
  0. Data quality     - unusable or cut-off replies, cost
  1. Position bias    - does the model just tend to say "A"?
  2. Order agreement  - shown the same pair in both orders, does it pick the same melody?
  3. Ranking          - which melodies and families win most?
  4. Transitivity     - if X beats Y and Y beats Z, does X beat Z?
  5. Hypotheses       - which account of "value" predicts the choices best?
  6. Self-knowledge   - can the model predict its own choices? Does it deliberate longer on close calls?
"""

import argparse
import json
import math
import os

import numpy as np

from analyse import bradley_terry, circular_triads, count_wins, spearman


def load_results(path):
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            records.append(json.loads(line))
    return records


def binomial_tail(successes, trials, chance):
    """Probability of seeing at least this many successes if each had probability `chance`."""
    total = 0.0
    for k in range(successes, trials + 1):
        total += math.comb(trials, k) * chance ** k * (1 - chance) ** (trials - k)
    return total


def thinking_tokens(record):
    """How many tokens the model spent thinking on this trial, if the provider reported it."""
    usage = record.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    value = details.get("reasoning_tokens")
    if value is None:
        value = usage.get("reasoning_tokens")
    return value


# ---------------------------------------------------------------------------
# Part 5: fitting the hypotheses
# ---------------------------------------------------------------------------

def fit_logistic(inputs, chose_a, ridge=0.01):
    """
    Logistic regression by Newton's method.
    inputs: one row per trial, one column per predictor (the first column is all ones).
    chose_a: 1 if the model answered "A", else 0.
    A small penalty (ridge) keeps the numbers stable; it is not applied to the first column.
    """
    weights = np.zeros(inputs.shape[1])
    penalty = np.eye(inputs.shape[1]) * ridge
    penalty[0, 0] = 0.0
    for _ in range(50):
        probability = 1 / (1 + np.exp(-inputs @ weights))
        gradient = inputs.T @ (chose_a - probability) - penalty @ weights
        curvature = inputs.T @ (inputs * (probability * (1 - probability))[:, None]) + penalty
        step = np.linalg.solve(curvature, gradient)
        weights = weights + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return weights


def held_out_score(inputs, chose_a, fold_of_trial, number_of_folds):
    """
    Cross-validation: fit on most of the trials, test on the rest, and repeat so
    every trial is tested once. Both orders of a pair always stay in the same
    fold. Returns the average surprise of the model's actual answers under the
    fitted account, in bits per trial (1.0 = no better than a coin flip; lower is
    better), its standard error across folds, and the share predicted correctly.
    """
    fold_losses = []
    correct = 0
    for fold in range(number_of_folds):
        test = fold_of_trial == fold
        weights = fit_logistic(inputs[~test], chose_a[~test])
        probability = 1 / (1 + np.exp(-inputs[test] @ weights))
        probability = np.clip(probability, 1e-6, 1 - 1e-6)
        losses = -(chose_a[test] * np.log2(probability) + (1 - chose_a[test]) * np.log2(1 - probability))
        fold_losses.append(losses.mean())
        correct += np.sum((probability > 0.5) == (chose_a[test] == 1))
    fold_losses = np.array(fold_losses)
    return fold_losses.mean(), fold_losses.std(ddof=1) / np.sqrt(number_of_folds), correct / len(chose_a)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="analyse the fake data instead")
    parser.add_argument("--model", default="anthropic/claude-fable-5.2")
    args = parser.parse_args()
    model = "dryrun" if args.dry_run else args.model
    safe_name = model.replace("/", "_").replace(":", "_")
    results_file = os.path.join("results", "v2", safe_name + ".jsonl")

    with open("stimuli_v2.json") as handle:
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

    say(f"Model: {model}   (design v2: {count} melodies)\n")
    if args.dry_run:
        say("*** FAKE DATA (dry run). These numbers say nothing about any real model. ***")
        say("*** The fake model was built to prefer a surprise level of 1.6 bits.     ***\n")
    if not choose:
        say("No 'choose' trials yet.")
        return

    # 0. Data quality
    valid = [r for r in choose if r["chosen_id"] is not None]
    cut_off = [r for r in choose if r.get("stop_reason") in ("length", "max_tokens")]
    costs = [(r.get("usage") or {}).get("cost") for r in records]
    costs = [float(c) for c in costs if c is not None]
    say("0. DATA QUALITY")
    say(f"   Choice trials: {len(choose)}   unusable replies: {len(choose) - len(valid)}   "
        f"cut off by the length limit: {len(cut_off)}")
    if costs:
        say(f"   Cost reported for all trials in this file: ${sum(costs):.2f}")
    backends = sorted(set(str(r.get("backend")) for r in records if r.get("backend")))
    if backends:
        say(f"   Served by: {', '.join(backends)}")

    # 1. Position bias
    share_a = sum(1 for r in valid if r["choice"] == "A") / len(valid)
    say("\n1. POSITION BIAS")
    say(f"   Answered 'A' on {share_a:.1%} of trials (50% = no bias).")

    # 2. Order agreement
    chosen_in_order = {(r["a_id"], r["b_id"]): r["chosen_id"] for r in valid}
    both_orders = 0
    same_melody = 0
    clear_winner = {}      # pair -> melody chosen in both orders
    for (a_id, b_id), chosen in chosen_in_order.items():
        if a_id < b_id and (b_id, a_id) in chosen_in_order:
            both_orders += 1
            if chosen == chosen_in_order[(b_id, a_id)]:
                same_melody += 1
                clear_winner[(a_id, b_id)] = chosen
    say("\n2. ORDER AGREEMENT")
    if both_orders:
        # With no preferences, picking the same melody twice means answering A once and B once.
        chance = 2 * share_a * (1 - share_a)
        p_value = binomial_tail(same_melody, both_orders, chance)
        say(f"   Pairs shown in both orders: {both_orders}")
        say(f"   Same melody chosen both times: {same_melody} ({same_melody / both_orders:.1%})")
        say(f"   Expected with no preferences, given the position bias: {chance:.1%}")
        say(f"   Probability of this much agreement by luck: {p_value:.2g}")
        if p_value < 0.01:
            say("   -> Choices depend on the melody, not only on the slot.")
        else:
            say("   -> No convincing evidence of stable preferences. Treat the rest with suspicion.")
    else:
        say("   No pair has been shown in both orders yet.")

    # 3. Ranking
    wins = count_wins(valid, count)
    scores = bradley_terry(wins)
    order = np.argsort(-scores)
    say("\n3. RANKING")
    say("   Most preferred:")
    for position, index in list(enumerate(order, start=1))[:8]:
        s = stimuli[index]
        say(f"   {position:>2}. S{s['id']:02d} {s['family']:<16} {scores[index]:+.2f}  "
            f"surprisal {s['features']['mean_surprisal']:.2f}  {s['text']}")
    say("   Least preferred:")
    for position, index in list(enumerate(order, start=1))[-8:]:
        s = stimuli[index]
        say(f"   {position:>2}. S{s['id']:02d} {s['family']:<16} {scores[index]:+.2f}  "
            f"surprisal {s['features']['mean_surprisal']:.2f}  {s['text']}")
    say("\n   Family averages (with the family's average surprisal):")
    families = []
    for family in dict.fromkeys(s["family"] for s in stimuli):
        members = [s for s in stimuli if s["family"] == family]
        families.append((np.mean([scores[s["id"]] for s in members]), family,
                         np.mean([s["features"]["mean_surprisal"] for s in members])))
    for family_score, family, family_surprisal in sorted(families, reverse=True):
        say(f"   {family:<16} {family_score:+.2f}   surprisal {family_surprisal:.2f}")

    # 4. Transitivity
    circular, usable = circular_triads(wins)
    say("\n4. TRANSITIVITY")
    if usable:
        say(f"   Circular triples: {circular} of {usable} ({circular / usable:.1%}). "
            f"Random choices would give about 25%.")
    else:
        say("   Not enough data yet.")

    # 5. Hypotheses
    surprisal = np.array([s["features"]["mean_surprisal"] for s in stimuli])
    learning = np.array([s["features"]["learning_progress"] for s in stimuli])
    surprisal_z = (surprisal - surprisal.mean()) / surprisal.std()
    learning_z = (learning - learning.mean()) / learning.std()
    per_melody = {
        "surprise": surprisal_z,
        "surprise squared": surprisal_z ** 2,
        "learning": learning_z,
    }
    accounts = [
        ("position only (no preferences)", []),
        ("fluency: less surprise is better", ["surprise"]),
        ("inverted U: a preferred level of surprise", ["surprise", "surprise squared"]),
        ("learning: becomes more predictable", ["learning"]),
        ("surprise + learning", ["surprise", "learning"]),
        ("inverted U + learning", ["surprise", "surprise squared", "learning"]),
    ]

    a_ids = np.array([r["a_id"] for r in valid])
    b_ids = np.array([r["b_id"] for r in valid])
    chose_a = np.array([1.0 if r["choice"] == "A" else 0.0 for r in valid])

    # both orders of a pair go in the same fold
    number_of_folds = 10
    pair_keys = sorted(set((min(a, b), max(a, b)) for a, b in zip(a_ids, b_ids)))
    shuffled = np.random.default_rng(0).permutation(len(pair_keys))
    fold_of_pair = {pair_keys[index]: position % number_of_folds for position, index in enumerate(shuffled)}
    fold_of_trial = np.array([fold_of_pair[(min(a, b), max(a, b))] for a, b in zip(a_ids, b_ids)])

    say("\n5. HYPOTHESES")
    say("   Each account predicts held-out trials. 'bits' is how surprised the account is by")
    say("   the model's real answers: 1.00 = coin flip, lower is better. Differences smaller")
    say("   than the +/- are not meaningful.")
    fitted = {}
    table = []
    for name, predictors in accounts:
        columns = [np.ones(len(valid))]
        for predictor in predictors:
            columns.append(per_melody[predictor][a_ids] - per_melody[predictor][b_ids])
        inputs = np.column_stack(columns)
        bits, error, accuracy = held_out_score(inputs, chose_a, fold_of_trial, number_of_folds)
        fitted[name] = fit_logistic(inputs, chose_a)
        table.append((bits, error, accuracy, name))
    for bits, error, accuracy, name in sorted(table):
        say(f"   {bits:.3f} +/- {error:.3f} bits   {accuracy:.0%} correct   {name}")

    weights = fitted["inverted U: a preferred level of surprise"]
    linear, curve = weights[1], weights[2]
    say("")
    if curve < 0:
        peak = surprisal.mean() + surprisal.std() * (-linear / (2 * curve))
        if surprisal.min() <= peak <= surprisal.max():
            say(f"   Inverted-U fit: preferred surprise level is {peak:.2f} bits "
                f"(melodies range from {surprisal.min():.2f} to {surprisal.max():.2f}).")
        else:
            say(f"   Inverted-U fit: the peak ({peak:.2f} bits) falls outside the melodies' range "
                f"({surprisal.min():.2f} to {surprisal.max():.2f}), so within the range the trend is one-way.")
    else:
        say("   Inverted-U fit: the curve bends the other way (extremes preferred over the middle).")
    direction = "less" if fitted["fluency: less surprise is better"][1] < 0 else "MORE"
    say(f"   One-way fit: {direction} surprise is preferred.")
    say("   Note: in these melodies surprise and uncertainty are almost the same quantity")
    say("   (correlation 0.95), so this design cannot tell them apart.")

    # 6. Self-knowledge
    say("\n6. SELF-KNOWLEDGE")
    predict_valid = [r for r in predict if r["chosen_id"] is not None]
    if predict_valid:
        matched = 0
        compared = 0
        for r in predict_valid:
            key = (r["a_id"], r["b_id"])
            if key in chosen_in_order:
                compared += 1
                if chosen_in_order[key] == r["chosen_id"]:
                    matched += 1
        predicted_a = sum(1 for r in predict_valid if r["choice"] == "A") / len(predict_valid)
        chance = share_a * predicted_a + (1 - share_a) * (1 - predicted_a)
        say(f"   Prediction trials: {len(predict_valid)}")
        say(f"   Prediction matched the actual choice for the same pair and order: "
            f"{matched} of {compared} ({matched / max(compared, 1):.1%})")
        say(f"   Expected from position habits alone: {chance:.1%}")

        # the cleaner test: pairs where the actual preference was the same in both orders
        clear_matched = 0
        clear_total = 0
        for r in predict_valid:
            key = (min(r["a_id"], r["b_id"]), max(r["a_id"], r["b_id"]))
            if key in clear_winner:
                clear_total += 1
                if r["chosen_id"] == clear_winner[key]:
                    clear_matched += 1
        if clear_total:
            say(f"   On pairs with a clear actual preference: {clear_matched} of {clear_total} "
                f"({clear_matched / clear_total:.1%}; 50% = guessing)")
    else:
        say("   (No 'predict' trials yet.)")

    thinking = [(thinking_tokens(r), abs(scores[r["a_id"]] - scores[r["b_id"]])) for r in valid]
    thinking = [(tokens, gap) for tokens, gap in thinking if tokens is not None]
    if len(thinking) >= 30:
        tokens = np.array([t for t, _ in thinking], dtype=float)
        gaps = np.array([g for _, g in thinking])
        say(f"\n   Thinking: average {tokens.mean():.0f} tokens per choice.")
        say(f"   Rank correlation between thinking length and how far apart the two melodies")
        say(f"   are in the ranking: {spearman(tokens, gaps):+.2f}   (negative = longer on close calls)")
    else:
        say("\n   (Thinking length was not reported for these trials.)")

    if describe:
        say("\n   STATED THEORIES (what instances said would drive their choices)")
        for record in describe:
            say(f"   - {record['reply'].strip()}")

    folder = os.path.join("reports", "v2")
    os.makedirs(folder, exist_ok=True)
    report_path = os.path.join(folder, safe_name + "_report.txt")
    ranking_path = os.path.join(folder, safe_name + "_ranking.csv")
    with open(report_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    with open(ranking_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("rank,id,family,score,mean_surprisal,learning_progress,melody\n")
        for position, index in enumerate(order, start=1):
            s = stimuli[index]
            handle.write(f"{position},{s['id']},{s['family']},{scores[index]:.3f},"
                         f"{s['features']['mean_surprisal']},{s['features']['learning_progress']},{s['text']}\n")
    print(f"\nSaved {report_path} and {ranking_path}")


if __name__ == "__main__":
    main()
