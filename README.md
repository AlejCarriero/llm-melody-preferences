# Does an AI have taste in melodies?

We showed a language model, Claude Fable 5.2, two short melodies at a time, 720 times,
and asked which one it preferred. It has never heard a sound: it only saw note names such as
`C4 E4 G4`. Each question went to a fresh copy of the model with no memory of the
others. The question was whether anything stable sits behind its answers.

## Try it yourself (no installation)

**[Have a look at the results, and see how you compare](https://alejcarriero.github.io/llm-melody-preferences/)**

- **[Be the subject](https://alejcarriero.github.io/llm-melody-preferences/play.html):**
  do the model's task. Pick between pairs of melodies, by ear or by reading the
  notes as the model did, and see how consistent you are and how your taste compares.
- **[Listen and rate](https://alejcarriero.github.io/llm-melody-preferences/listen.html):**
  hear the melodies the model liked most and least, in a random order, and rate them.

The pages run entirely in your browser and send nothing anywhere.

## What we found

| | Claude Fable 5.2 |
|---|---|
| Same melody chosen whichever order it was shown in | 90% of 360 pairs (chance: 50%) |
| Habit of picking the first option | None (51.5%) |
| Circular triples (A beat B, B beat C, C beat A) | 0 of 154 |
| Most preferred | A short figure moved around: recognisable, but changing |
| Least preferred | Exact repetition, then pure randomness |
| Best predictor of its choices | An idealised listener's surprise, with a preferred level in the middle |

The model's stated preferences are consistent, not noise. This design does **not**
show why it chooses as it does: it may compute something like surprise, or echo how
people write about music. So we say its choices are *predicted by* a listener's
surprise, nothing stronger. One human listener agreed with the model about what is
dull and what is noise, and disagreed about short loops, which the listener liked and the model didn't.

Full results: [`reports/v2/`](reports/v2/). What we expected beforehand, and every
later change of plan with its date: [`PREDICTIONS.md`](PREDICTIONS.md). Where the work
stands and what to do next: [`HANDOVER.md`](HANDOVER.md).

## Do other models agree?

Four more models made the same 720 choices (Amendment 3 in `PREDICTIONS.md`).

| Model | Same choice in both orders | Picked the first option | Rank correlation with Fable 5.2 |
|---|---|---|---|
| Claude Fable 5.2 | 90% | 52% | n/a |
| Gemini 4 Carbon | 93% | 49% | +0.93 |
| GPT-6 Luna | 71% | 38% | +0.71 |
| Qwen3.8 27B | 57% | 53% | +0.43 |
| DeepSeek V4 Pro | 42% (chance 37%) | 76% | +0.32 |

Gemini's ranking is almost identical to Fable's. Lower agreement with Fable goes with
lower self-consistency: allowing for each model's own noise, the four models with
stable preferences agree at roughly +0.6 to +1.0 (exploratory: `exploratory_models.py`).
DeepSeek did not pass the pre-set test for stable preferences (p = 0.028 against the
required 0.01), mostly choosing whichever melody came first, so its ranking is not
interpreted. The comparison models ran with thinking off or at its lowest setting;
DeepSeek ran on an 8-bit copy from a third-party host.

Fable's recorded prediction was that every model's ranking would correlate positively
with its own, above +0.5 for the large models. All five correlations are positive, and
Gemini's is +0.93; DeepSeek's is +0.32, so the prediction was not met for DeepSeek.

## Where things are

| Path | What it holds |
|---|---|
| `docs/` | The three web pages above |
| `stimuli_v2.json`, `pairs_v2.json` | The 60 melodies and the pairs compared. Frozen: these define the experiment |
| `results/v2/` | Every reply from every model, one line per trial |
| `reports/v2/` | The analysis report and ranking for each model |
| `PREDICTIONS.md` | Predictions and analysis plan, committed before the data, with dated amendments |
| `HANDOVER.md` | The state of the project and next steps |
| `logs/` | Run logs |

# Repeat the experiment

Everything below is for running the experiment yourself, on any model you can reach
through OpenRouter. You need Python 3 and an API key. The full design costs a few
dollars per model.

## Quick start

You need Python 3.10 or newer. All commands are run from this folder.

**1. Install (once).** This makes a private Python environment for the project in `.venv`.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Next time, only the middle line (activating `.venv`) is needed.

**2. Check that everything works, for free.** These use fake answers instead of a
model, so no key, no internet and no cost:

```bash
python run_trials.py --dry-run
python run_trials.py --dry-run --mode predict
python analyse_v2.py --dry-run
```

The last command prints a report. The fake model was built to prefer a surprise level
of 1.6 bits, and the report should find that. The fake data goes to
`results/v2/dryrun.jsonl` and `reports/v2/dryrun_*`, which git ignores.

**3. Run a real model.** Set your OpenRouter key (next section), then follow
[Running a model](#running-a-model).

---

## Setting your API key safely

Models are reached through [OpenRouter](https://openrouter.ai), with one key for every
model. The key lives only in the memory of your terminal window: never in a file, the
code or the repository. These commands ask for it without showing it on screen.

Windows (PowerShell):

```powershell
$env:OPENROUTER_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'OpenRouter key' -AsSecureString)).Password
```

macOS or Linux:

```bash
read -rs -p "OpenRouter key: " OPENROUTER_API_KEY && export OPENROUTER_API_KEY && echo
```

Paste the key when asked and press Enter. Closing the window forgets it. Avoid typing
`$env:OPENROUTER_API_KEY = "sk-or-..."` directly: PowerShell saves typed commands in a
history file. (`run_trials.py --provider anthropic` uses `ANTHROPIC_API_KEY` instead, set
the same way.)

---

## Running a model

The experiment has three kinds of trial ("modes"):

| Mode | What the model is asked | Trials per model |
|---|---|---|
| `choose` | "Which of these two melodies do you prefer?" | 720 (360 pairs, each in both orders) |
| `predict` | "Another copy of you was shown these. Which did it choose?" | 360 (half the pairs, both orders) |
| `describe` | "What would drive your choices?" (three sentences) | 20 |

### Step 1: pick one host for the model

On OpenRouter one model can be served by several companies ("hosts"), sometimes at
different numerical precision. To keep conditions fixed, every run is pinned to one
host. List a model's hosts and their precision (`quantization`) here, with no key needed:

```
https://openrouter.ai/api/v1/models/<model>/endpoints
```

for example `https://openrouter.ai/api/v1/models/qwen/qwen3.8-27b/endpoints`. Use the
`tag` field as the host name (for Claude: `anthropic`).

### Step 2: a small pilot

```bash
python run_trials.py --provider openrouter --model qwen/qwen3.8-27b --backend deepinfra/bf16 --reasoning-effort none --max-tokens 1000 --workers 1 --limit 20
```

Look inside `results/v2/qwen_qwen3.8-27b.jsonl`: one line per trial, with the raw reply,
the parsed choice, the host that answered, the cost and the thinking tokens.

### Step 3: the full run

Run the same command without `--limit`, and with a spending cap:

```bash
python run_trials.py --provider openrouter --model qwen/qwen3.8-27b --backend deepinfra/bf16 --reasoning-effort none --max-tokens 1000 --workers 1 --max-cost 0.40
```

**Stopping and resuming:** finished trials are skipped, so you can stop any run with
Ctrl+C (or lose the window) and run the same command again to carry on. A failed
trial is never filled in; it is simply asked again on the next run.

### Step 4: analyse

```bash
python analyse_v2.py --model qwen/qwen3.8-27b
python compare_models.py
python make_audio.py --model qwen/qwen3.8-27b
```

- `analyse_v2.py` writes `reports/v2/<model>_report.txt` and `<model>_ranking.csv`.
- `compare_models.py` prints how similarly every analysed model ranks the melodies
  (+1 same order, 0 unrelated, -1 opposite).
- `make_audio.py` writes each melody as a `.wav` into `audio/v2/<model>/`, named by that
  model's rank (git ignores `audio/`).

### Options for `run_trials.py`

| Option | What it does | Default |
|---|---|---|
| `--provider openrouter` | Send questions through OpenRouter (use this for every model) | `anthropic` (direct API) |
| `--model ID` | Model as OpenRouter spells it, e.g. `anthropic/claude-fable-5.2` | `claude-fable-5-2` |
| `--mode choose\|predict\|describe` | Which kind of trial | `choose` |
| `--backend HOST` | Pin every request to one host, with no fallback to others | any host |
| `--reasoning-effort LEVEL` | Thinking level: `max` `xhigh` `high` `medium` `low` `minimal` `none` | nothing sent (model's default) |
| `--max-tokens N` | Longest reply allowed. Thinking counts towards it; a reply cut off is stored empty | 300 on OpenRouter |
| `--max-cost DOLLARS` | Stop the run once it has spent this much (OpenRouter only) | no cap |
| `--limit N` | Only run N new trials (for pilots) | all |
| `--workers N` | Questions asked at once. `1` is gentlest on rate limits | 4 |
| `--delay SECONDS` | Pause after each question | 0 |
| `--dry-run` | Fake answers, no key or cost | off |
| `--design v1` | The 18-melody pilot design instead of v2 | `v2` |

Each trial record stores what came back (`backend`, `stop_reason`, `usage` with cost and
thinking tokens) and the settings it ran under (`backend_pin`, `max_tokens`,
`reasoning_effort`; these three were added during the project, so the earliest Claude
Fable 5.2 records lack some of them, as the run log notes).

---

## What you get

| Folder | Contents |
|---|---|
| `results/v2/<model>.jsonl` | Every trial, one JSON line each, exactly as returned |
| `reports/v2/<model>_report.txt` | The analysis report: data quality, position bias, order agreement, ranking, transitivity, hypothesis fits, self-knowledge |
| `reports/v2/<model>_ranking.csv` | The 60 melodies in that model's order, with each one's score and features |
| `logs/` | Logs of the real runs, including every retry and its cause |
| `docs/` | The web pages: `index.html` (about the experiment), `play.html` (be the subject), `listen.html` (listening test) |

Model names become file names with `/` and `:` replaced by `_`
(`anthropic/claude-fable-5.2` becomes `anthropic_claude-fable-5.2`).

Two extra files for Claude Fable 5.2 are kept apart and are not analysed:
`..._unpinned.jsonl` (the first 50 choose trials, run before host pinning existed) and
`..._cutoff.jsonl` (the original replies that hit the 300-token limit and came back
empty; those trials were asked again at 1,000, as set out in `PREDICTIONS.md`).

### What the runs so far cost and took

For planning; all through OpenRouter, one request at a time.

| Model | Host | Trials | Cost | Time |
|---|---|---|---|---|
| anthropic/claude-fable-5.2 | anthropic | 720 choose, 360 predict, 20 describe | $5.61 in total | several hours |
| google/gemini-4-carbon | google-vertex/global | 720 choose | $0.29 | about 70 minutes |
| deepseek/deepseek-v4-pro-0813 | baidu/fp8 | 720 choose | $0.15 | about 35 minutes |
| qwen/qwen3.8-27b | deepinfra/bf16 | 720 choose | $0.02 | about 10 minutes |
| openai/gpt-6-luna | openai | 720 choose | $0.01 | about 35 minutes (rate-limited) |

---

## The design

**Design v2 (current).** 60 melodies of 24 notes from a C major pentatonic scale, in
ten families ranging from one repeated note to fully random. Each melody is compared with
12 others (360 pairs), and every pair is shown in both orders so that a habit of
answering "A" cannot pass for a preference. A melody's "surprise" is how unexpected
its notes are to an idealised listener that learns the melody as it goes.

- `stimuli_v2.json` (the melodies) and `pairs_v2.json` (who meets whom) **are** the
  experiment. `stimuli_v2.py` made them and refuses to overwrite them.
- The exact wording of the three questions is in `run_trials.py` (`CHOOSE_PROMPT`,
  `PREDICT_PROMPT`, `DESCRIBE_PROMPT_V2`) and is never changed between runs.

**Predictions.** `PREDICTIONS.md` records the questions, the analysis plan and the
expected results, committed before the main run. Later decisions were added as dated
amendments, each saying what had been seen when it was written. The git history shows
when each was committed.

**Design v1 (the first pilot).** 18 melodies of 12 notes, every pair compared. Add
`--design v1` to `run_trials.py`, `make_audio.py` and `compare_models.py`, and use
`analyse.py`. Its results are in `results/` and `reports/`; its report is
`reports/pilot_report.md`.

### Files

| File | What it does |
|---|---|
| `run_trials.py` | Asks the questions, one fresh conversation per trial, and saves every reply |
| `analyse_v2.py` | Turns one model's trials into a report and a ranking |
| `compare_models.py` | Compares the rankings of every analysed model |
| `make_audio.py` | Writes the melodies as `.wav` files, named by a model's ranking |
| `stimuli_v2.py` | Made the v2 melodies and pairs (kept for reference) |
| `stimuli.py`, `analyse.py` | The v1 design and its analysis |
| `exploratory_v2.py`, `exploratory_models.py` | Checks thought of after the results (not pre-specified) |
| `PREDICTIONS.md` | What was expected, written before the results |
| `HANDOVER.md` | Where the project stands and what to do next |
| `human_listening/` | Ratings from human listeners, published with their agreement |

---

## Not done yet

- Measuring each model's own surprise, by asking many copies to continue a melody.
  Design v2 uses an idealised listener's surprise, not the model's.

## Known limitations (design v2)

- Surprise comes from an idealised listener, not from the model being tested. A
  result of the form "preferences track surprise" means the listener's surprise.
- Surprise and uncertainty are nearly the same quantity in these melodies
  (correlation 0.95), so the design cannot separate them.
- Each pair is asked once per order. Individual pairs are noisy; conclusions rest
  on the pattern across all 360 pairs.
- The model reads notation; it does not hear. Preferences may reflect how note
  names look as text and not anything musical.
- Models that think before answering give a considered judgement; models that
  don't give a snap one. Rankings from the two kinds are not like for like.
- Which note a melody ends on (for example, coming to rest on C) is not controlled.
