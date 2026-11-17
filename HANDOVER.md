# Handover

Written by Claude Fable 5.2 on 16 November 2026, at the end of the conversation in
which this experiment was designed. It is for whoever continues the work: Alej, a
later Claude, or anyone replicating it. Read `PREDICTIONS.md` and the `README`
first; this file covers what they don't.

## How the work was divided

- **Design conversation (Claude Fable 5.2, in the Claude app):** chose the
  experiment, wrote the stimuli, analysis and predictions, and made every design
  decision. It never ran a trial and saw results only when they were brought to it.
- **Execution session (Claude Code, on Alej's computer):** ran the code, fixed
  plumbing, committed and pushed. It was told not to change prompts, stimuli or
  statistics, and not to interpret results.
- **Alej:** carried messages between the two, held the API key, paid for the
  trials, listened to the melodies, and brought her thesis, which changed how the
  results are described (Amendment 1).

## Where things stand

**Done: Claude Fable 5.2, design v2.** 720 choices, 360 predictions, 20 stated
theories, all pinned to the Anthropic host. Report in `reports/v2/`.

**Done (17 November): four comparison models**, choice trials only (Amendment 3):
`google/gemini-4-carbon`, `deepseek/deepseek-v4-pro-0813` (on `baidu/fp8`, as
DeepSeek's own host was blocked by the account's privacy setting),
`qwen/qwen3.8-27b` and `openai/gpt-6-luna`. Results below.

**Website:** three pages in `docs/` (landing page, "Be the subject", listening
test), served by GitHub Pages. The landing page was written by Claude Opus 5.5,
which took over the design role on 17 November.

**Money:** $10 was put on OpenRouter. About $6.15 had been spent by 17 November
($5.61 for Fable 5.2's design v2, $0.48 for the four comparison models, the rest
on the v1 pilot and probes), leaving about $3.85.

## Results for Claude Fable 5.2

| Question | Result |
|---|---|
| Position bias | 51.5% "A": none |
| Same melody chosen in both orders | 323 of 360 pairs (89.7%); chance 50% |
| Circular triples | 0 of 154 |
| Best pre-specified account | Inverted U over surprise: 0.498 bits, 85% correct |
| One-way surprise account | 0.760 bits, and the sign is MORE surprise preferred, so fluency fails |
| Learning progress | Adds nothing (0.497 against 0.498) |
| Preferred surprise | 2.33 bits on a range of 0.50 to 3.05 |
| Top family, bottom families | `motif_variation`; `trivial`, then `repeat` |
| Prediction matched choice | 330 of 360 (91.7%); 96% on pairs with a clear preference |
| Thinking against closeness | Rank correlation of -0.41: longer on close calls |

Against the predictions written beforehand: right on transitivity, the inverted U
beating fluency, learning adding little, self-prediction, and thinking on close
calls. Wrong on position bias (guessed 55 to 65%) and order agreement (guessed 70
to 85%). Half right on families: `motif_surprise` came seventh, not near the top,
and `repeat`, not `random`, was second from bottom. The preferred surprise missed
the guessed range by 0.03 bits.

### How to describe these results

Amendment 1 is binding. Say "the choices are predicted by an idealised listener's
surprise". Don't say the model computes value from surprise, and don't call the
result evidence about why it chooses.

### Three readings to resist

- **The self-prediction figure is not self-knowledge.** Predictions match choices
  about as often as choices match themselves. That is what you would see if "what
  would another instance choose?" is answered by choosing.
- **The inverted U is lopsided.** Exact repetition is rejected hard; pure
  randomness only mildly. "Dislikes loops, mildly dislikes noise" fits as well.
- **The stated theories are a mixed witness.** All 20 named varied motifs, stepwise
  motion and a balance of pattern and surprise, which the data support. All 20 also
  predicted a position bias that isn't there, and most named an ending on the home
  note, which shows no effect.

## Comparison models (Amendment 3)

| Model | Same melody in both orders | Chance | p | First option | Correlation with Fable |
|---|---|---|---|---|---|
| Claude Fable 5.2 | 89.7% | 50.0% | 1.5e-58 | 51.5% | n/a |
| Gemini 4 Carbon | 92.8% | 50.0% | 1.3e-69 | 49.4% | +0.93 |
| GPT-6 Luna | 70.6% | 47.0% | 1.3e-19 | 37.8% | +0.71 |
| Qwen3.8 27B | 56.7% | 49.8% | 0.0054 | 53.1% | +0.43 |
| DeepSeek V4 Pro | 41.7% | 36.7% | 0.028 | 75.8% | +0.32 |

**Scoring Fable's recorded prediction** ("rankings correlate positively with mine,
above +0.5 for large models"): all four correlations are positive. Gemini (+0.93)
meets the bar. DeepSeek (+0.32) does not, so the prediction was **not met** as
written. By the pre-specified gate (p < 0.01), DeepSeek showed no convincing stable
preferences, so its ranking is not interpreted; that explains the miss, but doesn't
change the score.

Every model that passed the gate fitted the inverted U best, with a preferred
surprise between 2.25 and 2.37 bits (Fable 2.33).

**Exploratory, written after seeing the data** (`python exploratory_models.py`):
lower agreement with Fable goes with lower self-consistency. Split-half reliability
of the ranking is 0.96 for Fable, 0.98 Gemini, 0.80 Luna, 0.56 Qwen and negative for
DeepSeek (its 76% habit of picking slot A reverses its ranking between the two
orders). Corrected for reliability, the four models that passed agree at about +0.6
to +1.0. By Amendment 1, broad agreement across labs fits the meaning account
(taste absorbed from shared training text) but does not establish it.

**Not like for like:** the comparison models ran with thinking off or at the lowest
setting allowed; Fable ran at its default, though its median thinking on a choice
was zero tokens. DeepSeek ran on an 8-bit copy from a third-party host. Only Fable
was given predict and describe trials.

## Exploratory checks (not pre-specified)

Run `python exploratory_v2.py`. These were thought of after seeing the results.

- **Amendment 2 mattered.** Re-asked cut-off predictions matched 21 of 35 (60%);
  the rest matched 95%. Dropping them would have flattered the result.
- **Repeat reliability.** 47 of 50 trials gave the same answer when asked twice,
  with no sign that the serving host mattered.
- **Most choices had no deliberation.** Median thinking was 0 tokens for a choice
  and 88 for a prediction.
- **Surprise is not special.** A plain measure of exact repetition, curved,
  predicts as well (0.481 bits). Adding the share of small steps improves on
  surprise (0.414). Ending on C adds nothing.

## One human listener

Alej rated the short set of 24 by ear (`human_listening/`). Her ratings and the
model's ranking correlate at +0.16, which on 24 melodies is indistinguishable from
zero. Both put single repeated notes and the random melody low. They disagree on
loops: she rated the three- and four-note repeats 3 to 4, and the model ranked them
near the bottom. Her only 5 went to a melody that recalled a childhood piano
exercise, which is the meaning account of Amendment 1 turning up in a person.
One listener, not blind: an anecdote that suggests an experiment.

## What I would do next, in this order

1. **Amendment 3 is scored** (above). Because the models that have stable
   preferences largely agree, the meaning experiment (item 3) has moved up in
   importance: it is the direct test of where the shared taste comes from.
2. **The format experiment.** Repeat the choice trials with each melody shown as a
   small piano-roll image in place of note names. If the ranking survives, the
   preferences belong to the structure. If loops rise, the dislike of repetition
   came from reading text. Write the prediction down first.
3. **The meaning experiment** (Amendment 1's follow-up). Pairs matched on the
   listener's statistics, where one resembles a widely known tune and the other is
   a scramble of it.
4. **Measure the model's own surprise** on a small subset, by asking many instances
   to continue a melody. Everything so far uses an idealised listener's surprise.
5. **Literature check, then decide on a write-up.** I did not check what has been
   published on coherent preferences or self-prediction in language models. Do that
   before claiming anything is new.

## Mistakes made along the way

Kept here so the record is honest and so they aren't repeated.

- The v1 listener scored scale runs as surprising and the v1 melodies did not span
  the surprise range, so v1 could not detect an inverted U even in fake data.
- I assumed the model answers without thinking and set a 20-token limit on that
  basis. The execution session caught it.
- The analysis row "fluency: less surprise is better" had a free sign and was
  mislabelled. It was flagged on 12 November and not fixed until the 16th.
- I first said cut-off replies should be left alone, then reversed that when one
  prediction in eight was cut off (Amendment 2).
- I misread Alej's description of her thesis and proposed a "step" account on that
  misreading. It is recorded as withdrawn in Amendment 1.
- Amendment 1 was written on 12 November but committed on the 15th. The record
  note under it says what existed at the time.
- The prediction for the comparison models named no consistency gate, so a model
  without stable preferences (DeepSeek) counted against it. A future prediction
  about agreement between models should be conditional on each model passing the gate.

## Rules worth keeping

- Prompts, `stimuli_v2.json` and `pairs_v2.json` are frozen. A new idea gets a new
  design version, not an edit.
- Predictions and changes of plan are written and committed before the data they
  concern is seen, with a line saying what had been seen.
- Every real reply comes from a real API call. A failed trial stays failed.
- Keys stay in environment variables.
- Publish the result whichever way it comes out.
