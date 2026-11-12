# Does Claude have stable melody preferences?

Many fresh instances of the model are each shown two short melodies (as note names)
and asked which one they prefer. We then check whether the answers agree with each
other, what predicts them, and whether the model can predict its own choices.

## Setup (once)

    pip install -r requirements.txt

Keys live in your terminal session, never in the code or the repository:

    export ANTHROPIC_API_KEY="sk-ant-..."      # from console.anthropic.com
    export OPENROUTER_API_KEY="sk-or-..."      # from openrouter.ai

## Design v2 (current)

60 melodies of 24 notes, spanning fully predictable to fully random. Each melody
meets 12 others, and every pair is shown in both orders. `stimuli_v2.json` and
`pairs_v2.json` define the experiment and are never regenerated once data exists.
`PREDICTIONS.md` records what we expected before the main run.

Check everything works, with fake answers (no key needed):

    python run_trials.py --dry-run
    python run_trials.py --dry-run --mode predict
    python analyse_v2.py --dry-run

The real experiment, for one model (all models go through OpenRouter, so conditions match):

    python run_trials.py --provider openrouter --model anthropic/claude-fable-5.2 --limit 50 --max-cost 0.50
    python run_trials.py --provider openrouter --model anthropic/claude-fable-5.2 --backend anthropic --max-cost 4.00
    python run_trials.py --provider openrouter --model anthropic/claude-fable-5.2 --backend anthropic --mode predict --max-cost 2.00
    python run_trials.py --provider openrouter --model anthropic/claude-fable-5.2 --backend anthropic --mode describe
    python analyse_v2.py --model anthropic/claude-fable-5.2
    python make_audio.py --model anthropic/claude-fable-5.2
    python compare_models.py                   # once two or more models are analysed

`--backend` makes OpenRouter serve every request from one host, with no fallback to
others. It takes OpenRouter's provider slug for that host (for Claude, `anthropic`);
each model's slugs are listed at `https://openrouter.ai/api/v1/models/<model>/endpoints`.
Every trial records both the host that answered (`backend`) and the one required
(`backend_pin`). The first 50 Fable 5.2 choice trials ran before pinning was added and
were served by Anthropic, Azure and Google.

`--max-cost` stops a run once it has spent that many US dollars. You can stop any
run with Ctrl+C and start it again; finished trials are skipped.

Trial counts per model: choose 720, predict 360, describe 20.

## Design v1 (the pilot)

18 melodies of 12 notes, every pair compared. Add `--design v1` to `run_trials.py`,
`make_audio.py` and `compare_models.py`, and use `analyse.py` for the analysis.
Its results live in `results/` and `reports/`; v2 uses `results/v2/` and `reports/v2/`.

## Files

| File | What it does |
|---|---|
| `stimuli_v2.py` | Makes the 60 melodies, the listener's surprise for each, and the list of pairs |
| `run_trials.py` | Asks the questions, one fresh conversation per trial; records cost and thinking tokens |
| `analyse_v2.py` | Data quality, position bias, order agreement, ranking, transitivity, hypothesis fits, self-knowledge |
| `compare_models.py` | Rank correlation between the preferences of different models |
| `make_audio.py` | Writes each melody as a `.wav`, named by a model's ranking if you give one |
| `stimuli.py`, `analyse.py` | The v1 design and analysis |

## Not done yet

- Measuring each model's own surprise by asking many instances to continue a melody.
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
