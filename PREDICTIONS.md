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

---

# Amendment 1

Written on 12 November 2026 at about 16:50 UTC. Nothing above this line was changed.

**What had been seen when this was written:** the report on the first 50 choice
trials of design v2 for Claude Fable 5.2. No other v2 data.

**Source:** Alej Carriero's PhD thesis (the model of Chapter 5 and Experiment 2),
read by Claude after the original predictions were written. The thesis argues that
in mice, value is not computed from the statistics of a sound alone: two grammars
matched in their statistics were valued differently once each had been associated
with a different housing context.

## A fourth account, which this round cannot test

**Meaning.** A sequence is valued for what it has come to signal through learning,
not for its statistics. Everything a language model knows about melodies was
learned from text, so on this account its choices reflect how people describe and
judge such patterns (a drone is "boring", a scale is "an exercise"), not any
surprise the model computes while reading.

All three accounts in the original plan (fluency, inverted U, learning) are
statistical. This design never manipulates meaning, so it cannot separate the two
kinds of account. A statistical account fitting well does not rule meaning out.

## Consequence for how results are described (binding)

A good fit will be reported as "the choices are predicted by an idealised
listener's surprise". It will not be reported as "the model computes value from
surprise" or as evidence about why the model chooses as it does.

## What in this round bears on it (all exploratory, and to be labelled so)

- **Stated theories.** Whether instances explain their choices by learned
  associations (what a pattern resembles or is used for) or by structure.
- **Agreement between models.** High agreement is what the meaning account
  expects, because the models share much of their training text.
- **Misfits.** The melodies whose rank departs most from what surprise predicts,
  inspected by ear and for resemblance to familiar music.

## Planned follow-up (not part of this round)

Pairs matched on the listener's statistics in which one melody resembles the
opening of a widely known tune and the other is a scramble of the same notes with
the same surprise. The meaning account predicts a preference for the familiar
one; the statistical accounts predict none.

## Withdrawn

A "step" account (any detectable pattern is preferred over none, however much
surprise it carries), which Claude proposed in conversation after misreading the
thesis's finding. It is not adopted as a hypothesis. Whether preference falls
smoothly or sharply across the noisy-motif families may still be looked at, as
exploration.

## Added guess

| Question | Guess | Confidence |
|---|---|---|
| Stated theories | Draw more on musical ideas learned from people (resolution, phrasing, tension) than on prediction or surprise | Guessing |

## Record note on Amendment 1 (added 15 November 2026)

Amendment 1 was written in the design conversation at about 16:50 UTC on
12 November and saved locally at 16:59:41 UTC, but it was not committed until
15 November. Its statement of what had been seen refers to the design
conversation, which had seen only the report on the first 50 trials. By the
time the file was saved, the results file held 290 choice trials. None of them
had been analysed, and the design conversation had not seen them; the execution
session's progress check at about 17:00 showed only trial counts, backends and
spend. The local save time cannot be independently verified. The commit date can.

---

# Amendment 2

Written on 16 November 2026 at about 11:55 UTC. Nothing above this line was changed.

**What had been seen when this was written:** for the choose and predict trials,
only counts, costs, backends and the number of cut-off replies. No v2 data had
been analysed beyond the report on the first 50 trials.

**Why.** The original plan excludes cut-off replies. In predict mode, 35 of the
first 279 replies (12.5%) were cut off at the 300-token limit and came back
empty, and predict trials used about twice the tokens of choose trials. Cut-offs
at that rate are unlikely to be random: they are the trials with the longest
deliberation. Excluding them would bias the self-prediction results.

**New rule, for both modes.** A trial whose reply was cut off and empty is asked
again once, with a limit of 1,000 tokens. The original cut-off records are kept
unchanged in a separate file. The remaining predict trials and all describe
trials run at the 1,000 limit. Every record stores the limit it ran under. A
reply still cut off at 1,000 is excluded and counted.

**Reported alongside the results.** The cut-off rate at the 300 limit for each
mode, and the self-prediction results with and without the re-asked trials.

**Untested assumption.** That raising the limit does not change replies that
would have completed within 300 tokens anyway.

---

# Amendment 3

Written on 16 November 2026 at about 17:35 UTC. Nothing above this line was changed.

**What had been seen when this was written:** the complete design v2 results for
Claude Fable 5.2. No data from any other model.

**Comparison models** (choice trials only, 720 each, each pinned to one host):
google/gemini-4-carbon, deepseek/deepseek-v4-pro-0813, qwen/qwen3.8-27b,
openai/gpt-6-luna.

**Settings.** Each comparison model runs at the lowest thinking setting it
allows ("none" where available), with a reply limit of 1,000 tokens. Reason:
Claude Fable 5.2's median thinking on a choice trial was zero tokens, so the
nearest matched condition is a quick answer. The match is imperfect: Fable ran on
its adaptive default with no setting sent, and gemini-4-carbon cannot turn
thinking off. Thinking tokens are recorded per trial.

**Exclusion rule.** A model whose 20-trial pilot gives more than 2 unusable
replies is not run further and is reported as excluded.

**Analysis.** The same analyse_v2.py report for each model, then
compare_models.py. The prediction recorded earlier stands: rankings correlate
positively with Fable's, above +0.5 for the large models.
