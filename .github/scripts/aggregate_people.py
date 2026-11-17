"""
Build docs/people.json: the combined preferences of everyone whose results are in
human_listening/, for the "compare with other people" parts of docs/play.html and
docs/listen.html. Holds only scores and counts: no names, notes or other text.

Both games are turned into pairwise comparisons, then ranked with the same
Bradley-Terry method used for the AI models (analyse.py):
  - Be the subject: each choice is one comparison (the chosen melody beats the other).
  - Listening test: within one person's ratings, a melody rated higher beats one rated
    lower (equal ratings give no comparison).
Only melodies that took part in at least one comparison get a score.

Run from the repository root:  python .github/scripts/aggregate_people.py
"""
import csv
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.getcwd())
from analyse import bradley_terry, spearman  # noqa: E402  (the project's own methods)

COUNT = 60
AI_MODELS = [("anthropic_claude-fable-5.2", "Claude Fable 5.2"), ("google_gemini-4-carbon", "Gemini 4 Carbon"),
             ("openai_gpt-6-luna", "GPT-6 Luna"), ("qwen_qwen3.8-27b", "Qwen3.8 27B"),
             ("deepseek_deepseek-v4-pro-0813", "DeepSeek V4 Pro")]


def comparisons_from(text):
    """Return ((winner, loser) pairs, kind) from one results file, or None if unreadable."""
    ratings = re.search(r"^ratings in the order heard \(melody id:rating 1-5\): ([\d:,]+)\s*$", text, re.M)
    if "LISTENING RESULTS v1" in text and ratings:
        rated = {}
        for item in ratings.group(1).split(","):
            if ":" in item:
                melody, rating = item.split(":")
                rated[int(melody)] = int(rating)
        ids = sorted(rated)
        return [(x, y) if rated[x] > rated[y] else (y, x)
                for i, x in enumerate(ids) for y in ids[i + 1:] if rated[x] != rated[y]], "listen"
    trials = re.search(r"^trials \(A>B=chosen\): ([\d>=,]+)\s*$", text, re.M)
    if "BE THE SUBJECT v1" in text and trials:
        pairs = []
        for item in trials.group(1).split(","):
            m = re.fullmatch(r"(\d+)>(\d+)=(\d+)", item.strip())
            if m:
                a, b, c = (int(v) for v in m.groups())
                if c in (a, b):
                    pairs.append((c, b if c == a else a))
        return pairs, "play"
    return None


def main():
    wins = np.zeros((COUNT, COUNT))
    counts = {"listen": 0, "play": 0}
    for path in sorted(glob.glob(os.path.join("human_listening", "*.txt"))):
        found = comparisons_from(open(path, encoding="utf-8").read())
        if not found:
            print(f"skipped (no results block): {path}")
            continue
        pairs, kind = found
        counts[kind] += 1
        for winner, loser in pairs:
            if 0 <= winner < COUNT and 0 <= loser < COUNT:
                wins[winner][loser] += 1

    covered = [i for i in range(COUNT) if (wins[i].sum() + wins[:, i].sum()) > 0]
    result = {"people": counts["listen"] + counts["play"], "listen": counts["listen"], "play": counts["play"],
              "comparisons": int(wins.sum()), "melodies": len(covered), "selfMatch": None, "scores": {}, "vsAI": []}
    if covered:
        # Rounded to 3 decimals, as published. This also turns melodies the data cannot tell apart
        # (for example, equal ratings) into exact ties, instead of tiny numerical differences
        # that a rank correlation would treat as a real order.
        scores = np.round(bradley_terry(wins), 3)
        result["scores"] = {str(i): float(scores[i]) for i in covered}
        agree = sum(wins[i][j] for i in covered for j in covered if scores[i] > scores[j])
        result["selfMatch"] = round(100 * agree / wins.sum())
        for key, name in AI_MODELS:
            path = os.path.join("reports", "v2", key + "_ranking.csv")
            ai = {int(r["id"]): float(r["score"]) for r in csv.DictReader(open(path, encoding="utf-8"))}
            rho = spearman(np.array([scores[i] for i in covered]), np.array([ai[i] for i in covered])) if len(covered) > 2 else float("nan")
            result["vsAI"].append({"name": name, "rho": None if np.isnan(rho) else round(rho, 2)})

    with open(os.path.join("docs", "people.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=1)
    print(f"docs/people.json: {result['people']} people ({counts['listen']} listening, {counts['play']} be the subject), "
          f"{result['comparisons']} comparisons over {result['melodies']} melodies")


if __name__ == "__main__":
    main()
