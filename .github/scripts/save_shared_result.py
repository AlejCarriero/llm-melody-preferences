"""
Save a visitor's shared results (posted as a GitHub issue from docs/play.html or
docs/listen.html) as a file in human_listening/.

Run by .github/workflows/save-shared-results.yml when an issue is opened. The issue
text is untrusted: it is read here as data from the event file, never placed in a
shell command. Only a correctly formatted results block is saved; everything else
is ignored.

Writes the file and prints KEY=VALUE lines for the workflow (to $GITHUB_OUTPUT):
  saved=true|false, path=<file>, reason=<why not saved>
"""
import json
import os
import re
import sys

PAGES = {
    "Listening results": ("listen", "LISTENING RESULTS v1"),
    "Be the subject results": ("play", "BE THE SUBJECT v1"),
}
MAX_NOTES = 500


def output(**values):
    target = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{key}={str(value).replace(chr(10), ' ')}" for key, value in values.items()]
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def safe_slug(text):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug[:30] or "anonymous"


def check_listen(lines):
    """Return the cleaned block, or None if it is not a valid listening results block."""
    if len(lines) < 3 or lines[0] != "LISTENING RESULTS v1":
        return None
    if not re.fullmatch(r"set: (quick|full) \(\d{1,2} melodies\)", lines[1]):
        return None
    m = re.fullmatch(r"ratings in the order heard \(melody id:rating 1-5\): ((?:\d{1,2}:[1-5],?)+)", lines[2])
    if not m:
        return None
    pairs = [p for p in m.group(1).split(",") if p]
    ids = [int(p.split(":")[0]) for p in pairs]
    if not (3 <= len(pairs) <= 60) or len(set(ids)) != len(ids) or max(ids) > 59:
        return None
    notes = "(none)"
    rest = "\n".join(lines[3:])
    if rest.startswith("notes:"):
        notes = " ".join(rest[len("notes:"):].split())[:MAX_NOTES] or "(none)"
    return "\n".join(lines[:3] + ["notes: " + notes])


def check_play(lines):
    """Return the cleaned block, or None if it is not a valid Be the subject results block."""
    if len(lines) < 5 or lines[0] != "BE THE SUBJECT v1":
        return None
    if not re.fullmatch(r"mode: (hear|read)", lines[1]) or not re.fullmatch(r"length: (short|full)", lines[2]):
        return None
    m = re.fullmatch(r"melodies: ((?:\d{1,2},){5}\d{1,2})", lines[3])
    t = re.fullmatch(r"trials \(A>B=chosen\): ((?:\d{1,2}>\d{1,2}=\d{1,2},?)+)", lines[4])
    if not m or not t:
        return None
    melodies = {int(x) for x in m.group(1).split(",")}
    trials = [x for x in t.group(1).split(",") if x]
    if len(melodies) != 6 or max(melodies) > 59 or not (15 <= len(trials) <= 60):
        return None
    for trial in trials:
        a, rest = trial.split(">")
        b, c = rest.split("=")
        if {int(a), int(b)} - melodies or int(c) not in (int(a), int(b)):
            return None
    return "\n".join(lines[:5])


def main():
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    issue = event["issue"]
    title = issue.get("title") or ""
    body = (issue.get("body") or "").replace("\r\n", "\n")

    page = next(((key, val) for key, val in PAGES.items() if title.startswith(key)), None)
    if page is None:
        output(saved="false", reason="not a results issue")
        return
    kind, first_line = page[1]

    block = re.search(r"```\n(.*?)\n```", body, re.S)
    if not block:
        output(saved="false", reason="no results block found")
        return
    lines = [line.strip() for line in block.group(1).strip().split("\n")]
    cleaned = check_listen(lines) if kind == "listen" else check_play(lines)
    if cleaned is None or not cleaned.startswith(first_line):
        output(saved="false", reason="the results block is incomplete or not in the expected format")
        return

    name_match = re.search(r"^Name: (.+)$", body, re.M)
    name = " ".join(name_match.group(1).split())[:60] if name_match else "anonymous"
    date = (issue.get("created_at") or "")[:10]
    number = int(issue["number"])
    path = os.path.join("human_listening", f"{date}_{safe_slug(name)}_{kind}_issue{number}.txt")
    page_name = "listening page" if kind == "listen" else "Be the subject page"
    header = (f"Shared from the {page_name} on {date} via issue #{number} by GitHub user "
              f"{issue['user']['login']}.\nName given: {name}\n"
              f"The visitor agreed to publication when posting.\n\n")
    os.makedirs("human_listening", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(header + cleaned + "\n")
    output(saved="true", path=path)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:   # never fail loudly on odd input; just don't save
        output(saved="false", reason=f"could not read the issue ({type(error).__name__})")
        sys.exit(0)
