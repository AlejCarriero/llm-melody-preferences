"""
Step 5: do different models agree?

Reads every ranking in reports/ and prints how similar each pair of models'
preferences are, as a rank correlation:
  +1 = same order of favourites, 0 = unrelated, -1 = opposite.

Run:  python compare_models.py      (after running analyse.py for two or more models)
"""

import csv
import glob
import os

import numpy as np

from analyse import spearman


def main():
    scores = {}
    for path in sorted(glob.glob(os.path.join("reports", "*_ranking.csv"))):
        name = os.path.basename(path).replace("_ranking.csv", "")
        if name == "dryrun":
            continue
        by_id = {}
        with open(path) as handle:
            for row in csv.DictReader(handle):
                by_id[int(row["id"])] = float(row["score"])
        scores[name] = [by_id[k] for k in sorted(by_id)]

    names = list(scores)
    if len(names) < 2:
        print("Need rankings from at least two models. Run analyse.py --model ... for each.")
        return

    width = max(len(name) for name in names)
    for first in names:
        cells = []
        for second in names:
            cells.append(f"{spearman(np.array(scores[first]), np.array(scores[second])):+.2f}")
        print(f"{first:<{width}}  " + "  ".join(cells))
    print("\nColumns are in the same order as the rows.")


if __name__ == "__main__":
    main()
