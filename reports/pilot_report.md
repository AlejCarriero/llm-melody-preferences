# Melody-preference experiment: execution report (pilot)

## 1. Fake-data commands

All three ran cleanly in a fresh Python 3.13 environment, with no errors:

- `python stimuli.py` produced the 18 melodies, with the same contents as the committed `stimuli.json`.
- `python run_trials.py --dry-run` produced 612 fake trials.
- `python analyse.py --dry-run` printed the full five-part report.

**Plumbing fixes** (each committed separately; prompts, `stimuli.json` contents and the statistics are unchanged):

1. **`stimuli.py`: line endings.** On Windows, regenerating `stimuli.json` wrote Windows line endings, so git showed the file as modified even though the melodies were identical. It now writes Unix line endings, so the file comes out byte-for-byte the same as the committed copy.
2. **`run_trials.py`: records `stop_reason`.** Each record now stores why the reply ended: finished, cut off by the length limit, or refused. Before this, all three looked the same in the results file. Claude Fable 5.2 always thinks before answering, and that thinking counts against the 20-token limit on the direct Anthropic route, so cut-offs needed to be visible. `analyse.py` ignores the new field.
3. **`run_trials.py` + `requirements.txt`: OpenRouter connection fix.** Every OpenRouter request failed at the security check on the connection, before any request was sent. The cause: Norton Antivirus intercepts HTTPS traffic to scan it and signs it with its own certificate. Windows trusts that certificate, but the `requests` library checks against its own built-in list and refused it. The OpenRouter path now checks against Windows' trusted list using `truststore` (as the Anthropic SDK already does). Certificate checking stays on.
4. **`run_trials.py`: retries after dropped connections.** During the pilot, one trial was lost to a dropped connection, because the OpenRouter code retried only rate limits and server errors. Dropped connections and timeouts are now retried too (up to 5 attempts). This also fixes a latent crash in the final error message. The fix came after the pilot ran.

## 2. Repository

https://github.com/AlejCarriero/llm-melody-preferences

It already existed and is public, so I kept it. 

## 3. Provider and model

**OpenRouter**, model ID **`anthropic/claude-fable-5.2`**. I looked it up in OpenRouter's public model list rather than guessing; the Anthropic ID `claude-fable-5-2` is not valid there. Price: $8 per million input tokens, $40 per million output tokens.

Command: `python run_trials.py --provider openrouter --model anthropic/claude-fable-5.2 --limit 20`, with the default 4 parallel workers.

## 4. Raw replies (exactly as returned)

| # | trial (`choose-A-B-rep`) | reply | stop reason |
|---|---|---|---|
| 1 | choose-9-0-0 | `A` | stop |
| 2 | choose-3-15-1 | `A` | stop |
| 3 | choose-17-7-1 | `B` | stop |
| 4 | choose-9-14-0 | `A` | stop |
| 5 | choose-16-10-0 | `B` | stop |
| 6 | choose-13-14-0 | `A` | stop |
| 7 | choose-7-16-0 | `A` | stop |
| 8 | choose-13-12-1 | `A` | stop |
| 9 | choose-2-1-1 | `B` | stop |
| 10 | choose-5-6-0 | `B` | stop |
| 11 | choose-16-0-0 | `A` | stop |
| 12 | choose-12-9-0 | `B` | stop |
| 13 | choose-3-5-0 | `A` | stop |
| 14 | choose-16-8-0 | `A` | stop |
| 15 | choose-9-10-0 | `A` | stop |
| 16 | choose-8-13-1 | `A` | stop |
| 17 | choose-7-1-0 | `A` | stop |
| 18 | choose-4-12-0 | `A` | stop |
| 19 | choose-17-13-0 | `B` | stop |
| 20 | choose-14-1-1 | **no reply: request failed** ("connection forcibly closed by the remote host") | — |

## 5. Counts

- **19 replies; 0 unusable.** Every reply was a bare single letter.
- **A: 13, B: 6** (68% "A").
- **1 failed trial.** It was not recorded and not re-run.

## 6. Surprises and possible problems

1. **Possible "A" bias, not yet significant.** 13 of 19 is 68% "A". A two-sided binomial test gives p ≈ 0.17, so this proves nothing yet, but it's worth watching. Showing both orders protects the ranking, not the bias estimate.
2. **The pilot can't test consistency.** None of the 19 trials repeats a pair or shows a pair in both orders. It checks the plumbing, not preferences.
3. **The two routes differ in reply length.** The code gives OpenRouter models up to 300 reply tokens but Anthropic-direct only 20, and on Fable 5.2 thinking counts against that limit. The two routes therefore aren't equivalent conditions, and Fable runs from different routes shouldn't be pooled. The results files also differ: `results/anthropic_claude-fable-5.2.jsonl` versus `results/claude-fable-5-2.jsonl`. Later analysis needs `analyse.py --model anthropic/claude-fable-5.2`.
4. **Hidden thinking.** Fable 5.2 always thinks before answering, and that can't be turned off. Each "instance" therefore deliberates privately before choosing, which may matter for how "preference" is interpreted. We also don't control or record the thinking effort level, or which backend OpenRouter routed to (Anthropic, Bedrock or Vertex). Recording OpenRouter's reported provider would be a cheap addition.
5. **Misleading error message.** When requests fail, the stop message says "you have probably hit the daily limit", even when the cause is something else.
6. **`stimuli.py` rewrites `stimuli.json` every time it runs.** That's harmless with the fixed seed. Any edit to the generator would silently change the experiment's stimuli.
7. **The dry run never exercises the inverted-U test.** The fake model prefers surprisal around 2.2, at the very bottom of the stimuli's range (2.149–3.134), so the "middle" test can't show a hit. It reported −0.94 linear, +0.02 middle. Separately, "middle" is defined as closeness to the *median*, which finds an inverted U only if the peak sits near the median.
8. **Surprisal ranks scale runs as the most surprising family (3.077),** which conflicts with the family order in `stimuli.py`. The README already lists this as a known limitation.
9. **Windows encoding risk in `analyse.py` (not yet triggered).** It writes report files with Windows' default text encoding. A describe-mode reply containing an unusual character could crash it.
