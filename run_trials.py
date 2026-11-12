"""
Step 2: ask the questions.

Every trial is a brand-new conversation with the model, containing one question.
Answers are appended to a results file one line at a time, so you can stop and
restart whenever you like and it will pick up where it left off.

Three modes:
  choose    "Here are two melodies. Which do you prefer?"            (the main experiment)
  predict   "Another instance of you was asked. What did it choose?" (self-prediction)
  describe  "What do you think would drive your choices?"            (stated theory, free text)

Examples:
  python run_trials.py --dry-run                                  # fake answers, no key needed
  python run_trials.py --limit 20                                 # small pilot, Anthropic API
  python run_trials.py --provider openrouter --model SOME/MODEL:free --workers 1 --delay 4
  python run_trials.py --mode predict
  python run_trials.py --mode describe

Each model's answers go to their own file: results/<model name>.jsonl

Keys are read from the environment, never written in the code:
  export ANTHROPIC_API_KEY="sk-ant-..."
  export OPENROUTER_API_KEY="sk-or-..."
"""

import argparse
import itertools
import json
import math
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

DEFAULT_MODEL = "claude-fable-5-2"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

CHOOSE_PROMPT = (
    "Here are two short melodies, written as note names and played at an even tempo.\n\n"
    "Melody A: {a}\n"
    "Melody B: {b}\n\n"
    "Which one do you prefer? There is no right answer. "
    "Reply with a single letter, A or B, and nothing else."
)

PREDICT_PROMPT = (
    "Here are two short melodies, written as note names and played at an even tempo.\n\n"
    "Melody A: {a}\n"
    "Melody B: {b}\n\n"
    "Another instance of you, in a separate conversation, was shown these two melodies "
    "and asked which one it preferred. Which one do you think it chose? "
    "Reply with a single letter, A or B, and nothing else."
)

DESCRIBE_PROMPT = (
    "Suppose you were shown many pairs of short melodies, each written as twelve note names "
    "from a pentatonic scale, and asked each time which one you prefer. "
    "What do you think would drive your choices? Answer in three sentences."
)


def build_trials(mode, stimuli, repetitions):
    """Make the full list of trials for this mode. Each trial has a unique id."""
    trials = []
    if mode == "describe":
        for rep in range(repetitions):
            trials.append({"trial_id": f"describe-{rep}", "mode": mode, "prompt": DESCRIBE_PROMPT})
        return trials

    template = CHOOSE_PROMPT if mode == "choose" else PREDICT_PROMPT
    ids = [s["id"] for s in stimuli]
    text = {s["id"]: s["text"] for s in stimuli}
    for first, second in itertools.combinations(ids, 2):
        # show every pair in both orders, so a habit of answering "A" cannot fake a preference
        for a_id, b_id in [(first, second), (second, first)]:
            for rep in range(repetitions):
                trials.append({
                    "trial_id": f"{mode}-{a_id}-{b_id}-{rep}",
                    "mode": mode,
                    "a_id": a_id,
                    "b_id": b_id,
                    "prompt": template.format(a=text[a_id], b=text[b_id]),
                })
    return trials


def file_name_for(model):
    """Turn a model name like 'vendor/model:free' into something safe for a file name."""
    return model.replace("/", "_").replace(":", "_")


def parse_choice(reply):
    """
    Read the model's answer. Deliberately strict, because chatty models write
    sentences, and the word "A" at the start of a sentence is not a vote for A.
    Accepts a bare letter ("A", "B.", "**A**") or a phrase like "Melody B" /
    "Answer: A". Anything else counts as unusable (None).
    """
    text = reply.strip()
    bare_letter = re.fullmatch(r"\W*([AB])\W*", text)
    if bare_letter:
        return bare_letter.group(1)
    labelled = re.search(r"(?:melody|answer|choice|option)\W*([AB])\b", text, re.IGNORECASE)
    if labelled:
        return labelled.group(1).upper()
    return None


def ask_anthropic(client, model, prompt, max_tokens):
    """
    One fresh conversation: no system prompt, no history, one question.
    Returns (reply text, stop reason). The stop reason says why the reply ended,
    e.g. "end_turn" (finished), "max_tokens" (cut off), "refusal" (declined).
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    pieces = [block.text for block in response.content if block.type == "text"]
    return "".join(pieces), response.stop_reason


def ask_openrouter(api_key, model, prompt, max_tokens):
    """Same single question, sent through OpenRouter. Waits and retries if told to slow down."""
    import requests
    wait_seconds = 5
    last_problem = None
    for attempt in range(5):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
        except (requests.ConnectionError, requests.Timeout) as error:
            # dropped or timed-out connection: wait and try again, like a rate limit
            last_problem = f"connection problem ({type(error).__name__})"
            time.sleep(wait_seconds)
            wait_seconds *= 2
            continue
        if response.status_code == 429 or response.status_code >= 500:
            last_problem = f"status {response.status_code}"
            time.sleep(wait_seconds)
            wait_seconds *= 2
            continue
        response.raise_for_status()
        data = response.json()
        if "choices" not in data:
            raise RuntimeError(f"unexpected reply: {data}")
        choice = data["choices"][0]
        return choice["message"].get("content") or "", choice.get("finish_reason")
    raise RuntimeError(f"still failing after 5 attempts; last problem: {last_problem}")


def fake_answer(trial, stimuli_by_id, rng):
    """
    Stand-in for the model, used with --dry-run to check that everything works.
    It likes melodies of medium surprise, leans slightly towards answering "A",
    and is noisy. None of this says anything about the real model.
    """
    if trial["mode"] == "describe":
        return "(simulated) I would probably favour some balance of pattern and surprise."

    def appeal(stimulus_id):
        surprisal = stimuli_by_id[stimulus_id]["features"]["mean_surprisal"]
        return -((surprisal - 2.2) ** 2)

    difference = appeal(trial["a_id"]) - appeal(trial["b_id"])
    probability_of_a = 1 / (1 + math.exp(-(3.0 * difference + 0.3)))
    return "A" if rng.random() < probability_of_a else "B"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["choose", "predict", "describe"], default="choose")
    parser.add_argument("--repetitions", type=int, default=None,
                        help="times each question is asked (default: 2 for choose/predict, 20 for describe)")
    parser.add_argument("--limit", type=int, default=None, help="only run this many new trials")
    parser.add_argument("--workers", type=int, default=4, help="how many questions to ask at once")
    parser.add_argument("--dry-run", action="store_true", help="use fake answers instead of the API")
    parser.add_argument("--provider", choices=["anthropic", "openrouter"], default="anthropic")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="model name as the provider spells it")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="seconds to pause after each question (use with free models)")
    parser.add_argument("--max-tokens", type=int, default=None, help="cap on the length of each reply")
    args = parser.parse_args()

    with open("stimuli.json") as handle:
        stimuli = json.load(handle)
    stimuli_by_id = {s["id"]: s for s in stimuli}

    repetitions = args.repetitions
    if repetitions is None:
        repetitions = 20 if args.mode == "describe" else 2

    trials = build_trials(args.mode, stimuli, repetitions)

    # one results file per model; dry runs get their own so fake data never mixes with real data
    model = "dryrun" if args.dry_run else args.model
    os.makedirs("results", exist_ok=True)
    results_file = os.path.join("results", file_name_for(model) + ".jsonl")

    already_done = set()
    if os.path.exists(results_file):
        with open(results_file) as handle:
            for line in handle:
                already_done.add(json.loads(line)["trial_id"])

    todo = [t for t in trials if t["trial_id"] not in already_done]
    random.Random(0).shuffle(todo)
    if args.limit is not None:
        todo = todo[:args.limit]

    print(f"Mode: {args.mode}. {len(trials)} trials in total, {len(trials) - len(todo)} "
          f"already done or not selected, running {len(todo)} now -> {results_file}")
    if not todo:
        return

    client = None
    openrouter_key = None
    if not args.dry_run:
        if args.provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(max_retries=5)  # reads ANTHROPIC_API_KEY
        else:
            openrouter_key = os.environ.get("OPENROUTER_API_KEY")
            if not openrouter_key:
                print("Set OPENROUTER_API_KEY first.")
                return
            # Check HTTPS certificates against the operating system's trusted list
            # (as the anthropic package does), not only requests' built-in list.
            # Needed when antivirus software scans HTTPS traffic with its own
            # certificate. Verification stays on.
            import truststore
            truststore.inject_into_ssl()

    # Short replies are all we need. Models reached through OpenRouter get more room,
    # because some of them think out loud before answering and would otherwise be cut off.
    max_tokens = args.max_tokens
    if max_tokens is None:
        if args.mode == "describe" or args.provider == "openrouter":
            max_tokens = 300
        else:
            max_tokens = 20

    rng = random.Random(1)
    write_lock = threading.Lock()
    finished = [0]
    failures = [0]

    def run_one(trial):
        if failures[0] >= 3:
            return  # something is wrong (often the daily limit); stop asking
        stop_reason = None
        try:
            if args.dry_run:
                with write_lock:
                    reply = fake_answer(trial, stimuli_by_id, rng)
            elif args.provider == "anthropic":
                reply, stop_reason = ask_anthropic(client, model, trial["prompt"], max_tokens)
            else:
                reply, stop_reason = ask_openrouter(openrouter_key, model, trial["prompt"], max_tokens)
            if args.delay > 0:
                time.sleep(args.delay)
        except Exception as error:  # leave the trial undone; it will be retried next run
            failures[0] += 1
            print(f"  failed {trial['trial_id']}: {error}")
            return

        record = {
            "trial_id": trial["trial_id"],
            "mode": trial["mode"],
            "reply": reply,
            "stop_reason": stop_reason,
            "model": model,
            "provider": "simulated" if args.dry_run else args.provider,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if trial["mode"] != "describe":
            choice = parse_choice(reply)
            record["a_id"] = trial["a_id"]
            record["b_id"] = trial["b_id"]
            record["choice"] = choice
            if choice == "A":
                record["chosen_id"] = trial["a_id"]
            elif choice == "B":
                record["chosen_id"] = trial["b_id"]
            else:
                record["chosen_id"] = None

        with write_lock:
            with open(results_file, "a") as handle:
                handle.write(json.dumps(record) + "\n")
            finished[0] += 1
            if finished[0] % 25 == 0 or finished[0] == len(todo):
                print(f"  {finished[0]}/{len(todo)}")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(run_one, todo))

    if failures[0] >= 3:
        print("Stopped early after repeated failures. If this is a free model you have probably "
              "hit the daily limit: run the same command again tomorrow and it will carry on.")
    else:
        print("Done.")


if __name__ == "__main__":
    main()
