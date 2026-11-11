# Does Claude have stable melody preferences?

Many fresh instances of the model are each shown two short melodies (as note names)
and asked which one they prefer. We then check whether the answers agree with each
other, what predicts them, and whether the model can predict its own choices.

## Setup (once)

    pip install -r requirements.txt

Keys live in your terminal session, never in the code or the repository:

    export ANTHROPIC_API_KEY="sk-ant-..."      # from console.anthropic.com
    export OPENROUTER_API_KEY="sk-or-..."      # from openrouter.ai

## Check everything works, with fake answers (no key needed)

    python stimuli.py
    python run_trials.py --dry-run
    python analyse.py --dry-run

## The real experiment, for one model

    python run_trials.py --limit 20            # small pilot: look inside results/
    python run_trials.py                       # choose: 612 trials
    python run_trials.py --mode predict        # 612 trials
    python run_trials.py --mode describe       # 20 trials
    python analyse.py
    python make_audio.py --model claude-fable-5-2

You can stop any run with Ctrl+C and start it again; finished trials are skipped.

## Other models, through OpenRouter

    python run_trials.py --provider openrouter --model SOME/MODEL:free --workers 1 --delay 4
    python analyse.py --model SOME/MODEL:free
    python compare_models.py                   # do the models agree with each other?

Free models are rate-limited per account, per minute and per day. When the daily
limit is reached the script stops; run the same command the next day and it carries on.

## Files

| File | What it does |
|---|---|
| `stimuli.py` | Makes the 18 melodies (6 families x 3) and describes each with simple features |
| `run_trials.py` | Asks the questions, one fresh conversation per trial, saves to `results/<model>.jsonl` |
| `analyse.py` | Position bias, consistency, ranking, transitivity, feature fit, self-prediction |
| `compare_models.py` | Rank correlation between the preferences of different models |
| `make_audio.py` | Writes each melody as a `.wav`, named by a model's ranking if you give one |

## Planned next

- Estimate each model's own surprisal by asking many instances to continue a melody
- A listener that predicts intervals, so scale runs count as predictable
- About 60 melodies with randomly sampled pairs, to tell the hypotheses apart
- Fit and compare the fluency, inverted-U and learning models of value

## Known limitations

- Each pair is asked only 4 times by default (2 orders x 2 repetitions). Raise
  `--repetitions` for firmer per-pair results.
- The "surprisal" feature comes from a very simple listener that only tracks which
  note follows which. It scores a scale run as surprising, although most people
  would call it predictable.
- 18 melodies is a small set. A feature correlation here is a hint, not a finding.
- The model reads notation; it does not hear. Preferences may reflect how note
  names look as text and not anything musical.
