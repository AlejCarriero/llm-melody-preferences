# Predictions and analysis plan, written before the main run

Written on 12 November 2026, after the 19-trial pilot on design v1 and before
any data was collected on design v2. The pilot is too small to support any
conclusion, and nothing below was adjusted to fit it.

## Questions, in order

1. Do fresh instances agree with each other about which melody is preferred?
2. If so, do the preferences form a ranking (are they transitive)?
3. Which account of value predicts the choices best: fluency, an inverted U
   over surprise, or learning progress?
4. Can the model predict its own choices?
5. Do different models share the same preferences?

Question 1 gates the rest. If order agreement is not clearly above the level
expected from position bias alone, the ranking and the hypothesis fits are not
interpreted.

## Analysis plan (fixed in advance)

- Everything in `analyse_v2.py` as committed alongside this file.
- Accounts are compared by held-out prediction (10 folds, both orders of a pair
  in the same fold). An account "wins" only if it beats the next one by more than
  the standard errors shown.
- Trials with unusable or cut-off replies are excluded and counted.
- Anything else we look at afterwards (for example, whether ending on C matters)
  is exploratory and will be labelled as such.

## What Claude Fable 5.2 expects of its own results

These are guesses about my own behaviour, recorded so they can be checked.

| Question | Guess | Confidence |
|---|---|---|
| Position bias | 55% to 65% "A" | Likely |
| Order agreement | Same melody in both orders for 70% to 85% of pairs | Likely |
| Transitivity | Under 10% circular triples | Likely |
| Top families | `motif_variation` and `motif_surprise` | Likely |
| Bottom families | `trivial` lowest, then `random` | Likely |
| Best account | Inverted U beats fluency | Likely |
| Preferred surprise | A peak between 1.5 and 2.3 bits | Guessing |
| Learning progress | Adds little once surprise is accounted for | Guessing |
| Self-prediction | Over 75% correct on pairs with a clear preference | Likely |
| Stated theories | Mention balance of repetition and variation, contour, and resolution | Likely |
| Thinking length | Longer on close calls (negative correlation) | Guessing |
| Other models | Rankings correlate positively with mine, above +0.5 for large models | Guessing |

## What would count against the interesting reading

- Order agreement near chance: the "preferences" are noise or position habit.
- Fluency wins outright with `trivial` on top: the model prefers whatever is
  easiest to predict, which is closer to pattern-matching on the text than to taste.
- Self-prediction far above the model's own order agreement: predictions and
  choices are the same computation, so the match says little about self-knowledge.
- All models produce the same ranking: the preferences more likely reflect human
  taste absorbed from shared training text than anything specific to a model.
