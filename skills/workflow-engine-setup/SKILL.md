---
name: workflow-engine-setup
license: MIT
description: >
  Set up the Workflow Engine on a machine: a fresh Linux dev box (a cloud VM
  such as EC2) or a Mac. Opens with one short interview (at most two rounds of
  four questions) whose answers go into one answers file; its last question
  is what else the person needs, matched against the engine's feature
  catalog and shown as what it can do now, later, or not. Downloads the
  engine's installer with the user's own GitHub sign-in and runs its two
  passes: the machine pass installs the engine, then, once a board exists for
  one repository (shared lanes, the GitHub extension and a project plugin),
  the board pass applies the answers and installs everything the lanes
  declare and the board's services. The user writes secrets themselves,
  and the board pass is run again until `wf doctor --onboarding` signs the
  board off green or every remaining need is named with its fix. Use when
  someone asks to install, set up, onboard, or copy a Workflow Engine board
  onto a machine.
---

# Set up the Workflow Engine

You are setting up the Workflow Engine on the machine this shell runs on. Work
through the steps **in order**. Every step ends with a **Verify** command; do
not start the next step until it passes.

The engine installs itself. Its installer has two passes: the **machine pass**
(the release's installer package, step 2) installs the engine, and the **board
pass** (`wf setup install --board`, step 4) installs everything a board's lanes
declare, then the board's services, and finishes on `wf doctor --onboarding`.
You run the two passes, make the board between them, and pass on what they
say. You install nothing they install, and you grade nothing yourself: the
finish line is step 6, the board pass's own verdict.

Every decision that is the user's is asked once, in the interview before step
1, and written into one answers file that `wf plugin new` and the board pass
read (step 3c).

## Rules

- **Never ask for a secret in the chat.** No token, password, API key or
  private key is typed into this conversation, echoed, logged or written by
  you. Step 5 gives the user a command they run themselves.
- **Never print a config or credentials file**, whole or in part: an env file,
  an MCP or agent CLI config, a `git diff` of one. "Keys only" through a text
  filter (`sed`, `grep`, `awk`) counts as printing it: a filter that does not
  match prints the secret, and the same filter behaves differently on macOS
  and Linux. To learn what such a file holds, list its key names with a parser
  (the block below these rules), never its lines. When that block refuses a
  file, ask the user what it holds; do not read it another way.
- **If you see a secret anyway, say so at once.** Name the file and the key,
  never the value, and tell the user to rotate it. A token that reached this
  conversation stays in its transcript.
- **The installer is one consent.** Ask once, before the machine pass runs
  (step 2): say what both passes install as this user, then wait for a yes.
  That yes is the consent to every per-user step of both passes, re-runs
  included: running the board pass is that consent, so do not ask again item
  by item. An admin step (a system package, an apt source, or Homebrew's own
  installer on a Mac without it, which runs `sudo` itself) runs only after one
  yes to the plan that printed it: a pass with any comes back with one
  `consent` need. Show every admin command of that plan (each action with
  `admin: true`), say what it changes, and run the need's command (it carries
  `--yes <plan id>`) only once the user says yes; never give a `--yes` they did
  not. A `password` need is theirs to run in their own terminal, where `sudo`
  asks for their password (which never comes into this chat). An `admin` need
  (no admin rights for this user, or keeping user services running after
  logout) carries its exact command: show it and let them, or the machine's
  owner, run it.
- **Ask the user's decisions once, in the interview** (the next section),
  before anything is installed and never one by one later: which agent CLI
  (backend), models and effort the lanes run on, and turning on pollers or
  intake. Installing the board's services (the loop and a dashboard that is
  writable: it saves settings and answers checkpoints) comes with the board
  pass, so with the installer's one yes. Only the disk is asked when it comes
  up: any install over about 500 MB, or any install at all while the disk is
  more than 90% full. Say what each choice does and what it costs, then wait.
- **Read the engine that is running.** To read engine code, use the interpreter
  in the first line of `command -v wf` (`head -1 "$(command -v wf)"`). A machine
  can hold older engine copies (an install from before the versioned layout, a
  previous version directory) that answer differently.
- **Never put a broad personal token into a service file** (for example
  `gh auth token` into a LaunchAgent or a systemd env file) to satisfy a doctor
  row. If doctor requires a token and nothing on the board reads it (check the
  workflow that declares it and that workflow's hooks and prompts), stop and
  report it as a defect with the workflow's name; do not work around it.
- **Never touch another board.** If `wf` is already installed or the machine
  already has boards (`wf host --json` lists them), tell the user what you
  found and ask how to proceed before step 2. Never restart, reinstall or
  remove another board's services. The installer refuses to move an engine
  that a board runs from or an updater owns: never work around a refusal.
- **Never read or copy from another board.** Not another board's config,
  plugin or tasks, not the desktop app's `boards.json`, not shell history, not
  another project's agent memory, and write nothing into any of them. This
  board's values come from the interview's answers and from this repository. The
  one exception is a profile the user hands you (the profile section after
  step 3).
- **Stop at user steps.** Signing in to GitHub, signing in to the agent CLI,
  typing secrets and running an admin command are the user's. Say exactly what
  to run and wait.
- **Keep the project plugin in a git repository the user owns.** It holds the
  board's lane settings, so the user must be able to find, review and back it
  up. The interview asks where it goes; never put it under an application-data
  or cache directory, and never leave it untracked.
- **Verify after-merge steps before you hand them over.** Any command you give
  the user to run after a PR or a merge (`git switch`, `git pull`, a cleanup)
  must be proven safe in this repository first: check what it would overwrite
  or delete, local files git does not track included. A branch switch or a
  pull can overwrite or delete a local file the two sides track differently
  (a local `.mcp.json`, for one).
- **Never say "done" on your own word.** Done means the board pass exits 0
  (step 6), or every remaining need is named with its fix and who owes it.
- **Report the outcome, not the mechanism.** The last thing you tell the user
  is whether a task can run end to end on this board, or what stops it and who
  owes the fix. "Services active" or "pollers ok" does not answer that.
- **Report the installer verbatim.** Show each need's `detail` and `command`
  as the engine wrote them. A doctor row comes through as a need named
  `doctor.<code>`, carrying doctor's own fix.

Listing the key names of a config file without printing a value. It reads
JSON, and a file in which every line is one plain `NAME=VALUE` (blank and `#`
lines apart). It refuses anything else (TOML, YAML, INI, JSON that does not
parse, a value that runs over several lines, a `NAME=` with nothing after it):
it exits 1 and shows nothing from the file, because guessing at the format is
how a value gets printed.

```bash
python3 - path/to/file <<'PY'
import json, re, sys
text = open(sys.argv[1]).read()
# One assignment on one line: the value is quoted and closed, or has no quote and no backslash.
# A bare value is never empty and never starts with "=": a token padded with "=" reads as NAME=.
assignment = re.compile(r"""(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(?:"[^"]*"|'[^']*'|[^"'\\=][^"'\\]*)""")
def json_names(value, prefix=""):
    if isinstance(value, dict):
        for key in value:
            yield prefix + str(key)
            yield from json_names(value[key], prefix + str(key) + ".")
def line_names(text):
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if line and not line.startswith("#"):
            found = assignment.fullmatch(line)
            if not found:
                sys.exit(f"refused: line {number} is not one plain NAME=VALUE; nothing from this file is shown")
            yield found.group(1)
try:
    names = list(json_names(json.loads(text)))
except ValueError:  # not JSON: every line must be an assignment, or no name is printed
    names = list(line_names(text))
print("\n".join(names))
PY
```

## The interview

Before step 1, and before anything is installed, hold one short interview: at
most **two rounds of at most four questions**. Every decision that is the
user's is in it, so nothing is asked again later in the run, and nothing in it
is something you can detect or derive. The answers go into the settings file
(the next section); step 3c writes them into the one answers file that
`wf plugin new --answers` and the board pass (`wf setup install --board
--answers`, step 4) read.

**How to ask.** Use your agent's structured question tool if it has one (in
Claude Code, AskUserQuestion); otherwise ask in plain text, one question at a
time. Ask round 1, then round 2. Every question offers its choices with the
recommended one first, and always takes free text instead; when a choice needs
a value (a name, an address, a percent), the free text carries it.

**Look first; this changes nothing.** Run it before round 1, so that no
question asks what the machine already says:

```bash
uname -s; uname -m
for t in gh git python3 curl uv claude codex gemini wf; do printf '%-8s ' "$t"; command -v "$t" || echo MISSING; done
df -h "$HOME"
gh auth status
git config --global user.name || echo "MISSING: git user.name"
git config --global user.email || echo "MISSING: git user.email"
git rev-parse --show-toplevel && gh repo view --json nameWithOwner --jq .nameWithOwner
command -v wf && wf --version && wf host --json
```

If `wf` is already installed or `wf host --json` lists boards, the rule on
other boards applies first: tell the user what you found and ask how to go on.

### Round 1: the board

1. **Which repository does the board work on, and where do its lanes live?**
   - *The repository this session runs in, tested with the command its own
     files name, lanes in `~/wf-plugins`* (recommended, when the look found
     one): show its `owner/name` and that command in the choice
   - *Another repository of the user's*: its `owner/name`, cloned in step 3a
   - Free text: another repository with its test command; or another lanes
     folder, which must be a folder of the user's in a git repository they
     own, never an application-data or cache directory.
2. **Where does the board's work come from?**
   - *Tasks made on the board* (recommended): no tracker is polled
   - *Labelled GitHub issues*: of the board's repository, and of any other
     `owner/name` typed
   - *Jira issues*: the site address, the account email and the project key,
     typed (the API token is a secret, written in step 5)
   - *GitHub and Jira*
   - Free text: the repositories or the Jira project, as above.
3. **When does the board test merged work (the QA stage)?** Developing,
   reviewing and publishing always run; this is the check after merge.
   - *Later* (recommended): no test environment yet; finished work reads
     deferred until the user sets one up, and the board says when it sees one
   - *Now*: a test environment is up; its address, typed
   - *Never*: there is nothing to test after merge (a library, a CLI, scripts)
   - Free text.
4. **Which AI CLI may the board use, and how much of its plan's week?** Its
   account (a plan with a weekly limit, or an API key billed per token) is the
   user's own sign-in, step 5.
   - *The AI CLI already signed in here, slowing down at 80% of its week*
     (recommended): past that line, only work already begun or put first
     starts
   - *That CLI with no limit*: for an API-key account, which has no weekly
     meter
   - *Another AI CLI the look found* (`claude`, `codex` or `gemini`), slowing
     down at 80%
   - Free text: the CLI, and another percent from 1 to 100, or 0 for no
     limit.

### Round 2: the AI and how hands-off

5. **Which model and effort do the lanes run on?** They decide what every task
   costs, so they are the user's answer, never your pick. In the question,
   offer EVERY model and effort level the chosen CLI accepts, read from its
   own help (`claude --help` lists `--effort` as low, medium, high, xhigh,
   max), never a shortlist of your own; the value is passed to the CLI as
   typed.
   - *Its most capable model, at high effort* (recommended; `high` only where
     the CLI takes an effort level): say what that costs against the week
   - *A lighter model, at medium effort*: cheaper, for simpler work
   - Free text: any model and effort from those lists.
6. **What may the board do on its own?** Several may be chosen; what is not
   chosen stays a person's act.
   - *Keep the shared lanes up to date* (recommended): each new lanes release
     is installed when no agent runs
   - *Answer its own checkpoints with the memo's recommendation* (autopilot;
     it never merges)
   - *Start new tracker items without my Approve*, where the tracker vouches
     for them (offer it only when round 1 chose a tracker)
   - *Merge a pull request once every check passes*: the board pass then
     names the command that turns it on, for the user to run
   - Free text.
7. **Who else sees the board, and from where?** Several may be chosen.
   - *Only me, from my own computer* (recommended): a tunnel or the desktop
     app ("Reach the dashboard" at the end)
   - *Read-only viewers too*: their names, typed
   - *From my phone too*
   - Free text.
8. **What else do you need the board to do?** Ask it open, last: the tools,
   trackers, platforms or kinds of work they need beyond the choices above.
   The needs list (below) answers it.
   - *Nothing else for now* (recommended): the interview ends here
   - *Show me what it can do first*: read the catalog (below), show its
     areas, then ask this question again
   - Free text: each need, in their own words.

**The needs list.** Each need answer 8 names goes on it, and so does a
free-text answer to an earlier question that none of its choices covers
(another tracker or AI CLI, say); that question still takes one of its own
choices for the settings file.
With no need, there is no list. Otherwise match each need against the engine's
own feature catalog, `docs/features.md` in the engine's repository, and never
answer from memory. Nothing is installed yet, so read it with the user's `gh`
sign-in:

```bash
gh api "repos/gnarlysoft-ai/workflow-engine/contents/docs/features.md?ref=main" \
  -H "Accept: application/vnd.github.raw" > ~/.wf-setup-features.md
```

If `gh` is not signed in yet or prints `Not Found`, say the list comes after
GitHub access (step 1a) and show it there. Then show one short list, each need
under one of three headings, written as what it asks for, in plain words:

- **Can now:** an entry does it (Shipped, Behind a setting, or the part of a
  Partial entry that works): how, in one line, from its **Use** line, naming
  the setting when it is behind one.
- **Later:** the catalog has it under "Not shipped yet", or as what a Partial
  entry says is missing: planned, with its issue number when the catalog
  names one.
- **Can't:** no entry covers it: not something the engine does.

The list is shown and stops there. Never send it, or anything else, on your
own, and never put the repository's name or any task's text in a report.
Sending the Later and Can't lines to the engine's makers, after the person's
yes, comes in a later release of this skill; until then nothing leaves this
machine.

**Never asked: detect or derive it.** The OS and CPU, the repository's stack,
its default branch and, when its own files name one, its test command (its
README, CLAUDE.md or AGENTS.md, its CI config, `package.json` `scripts.test`,
a Makefile), an existing `gh`
sign-in, the CLIs installed, a git identity already set (a missing one is the
user's to set in their own terminal, like a sign-in: step 3a), the dashboard
port (the first free one from 8787), the engine version (step 1b), and every
Claude Code plugin, skill, MCP server, CLI and tool the lanes declare: the
board pass derives those from the lanes, so they are never asked and never
listed here. Whether a task designs its screens first is not asked either: it
is answered per task (when the task is made, at its route review, or by the
GitHub extension's design label), and no board-wide answer has a reader.

**Where each answer goes.** Each answer is a variable of the settings file,
and step 3c (3e for two of them) turns it into a key of the answers file,
which the reader named after it applies:

| Answer | Settings file | Answers file key: its reader |
|---|---|---|
| 1, the repository | `REPO_DIR`, `BOARD`, `TEST_COMMAND`, `GITHUB_REPOS` | `plugin.test_gate_command` and `plugin.base_branch`: `wf plugin new`; `integrations.github.config.GITHUB_REPOS`: the board pass |
| 1, the lanes folder | `PLUGINS_DIR` | none: where step 3 puts the lanes, the project plugin and the answers file |
| 2, where work comes from | `TRACKERS`, `GITHUB_REPOS`, `JIRA_SITE`, `JIRA_EMAIL`, `JIRA_PROJECT` | `integrations.github` (its poller and intake on or off) and `integrations.jira` (step 3d installs it): the board pass |
| 3, QA | `QA`, `QA_URL` | now and never: `settings.WF_QA_APPLICABLE` (the board pass) and `plugin.qa_applicable`, `plugin.qa_base_url_default` (`wf plugin new`); later: only `stages_deferred`, every optional stage the installed lanes declare (step 3e), since the deferral alone holds QA off and `wf stage undefer` hands the choice back to `WF_QA_APPLICABLE` |
| 4, the AI CLI | `BACKEND` | `plugin.backend_default`: `wf plugin new` |
| 4, the week | `THROTTLE` | `settings.WF_BUDGET_THROTTLE_PCT` (0 is off): the board pass |
| 5, model and effort | `MODEL`, `EFFORT` | every `plugin.model_*` and `plugin.effort_default`: `wf plugin new` |
| 6, lanes up to date | `LANES_UPDATE` | `settings.WF_PLUGIN_DELIVERY`, `auto` for yes and `detect` for no: the board pass |
| 6, autopilot | `AUTOPILOT` | `plugin.autopilot` (`wf plugin new`) and `settings.WF_AUTOPILOT` (the board pass) |
| 6, start new items | `AUTO_START` | `settings.WF_INTAKE_AUTO_APPROVE`, only for a tracker whose installed extension vouches for its items (step 3e): the board pass |
| 6, merging | `AUTO_MERGE` | `settings.WF_AUTO_MERGE`: off is written; on is a need naming `wf settings set WF_AUTO_MERGE '*' --yes`, which the user runs |
| 7, viewers | `VIEWERS` | `viewers`: the board pass names `wf user add <name> --role viewer` for each, since it prints that person's key once |
| 7, from a phone | none | no key: nothing in the installer serves the dashboard to a phone yet, so step 6 names it as a need |
| 8, what else is needed | none | no key: it is shown as the needs list, and nothing is written |

**After the interview** the run asks only about what it finds: the
installer's one yes (step 2), boards already on this machine (the rules), a
file the key-name lister refuses, a channel that does not resolve (step 1b),
an install the yes did not cover or the disk cannot take (steps 3c and 4a),
labels to create in a shared repository (step 4b), an MCP server a lane uses
that the board hides (step 4c), and each admin command, which the user runs.

## Before you start: one settings file

Your shell may not keep variables between commands, so keep them in a file and
start every command block with `. ~/.wf-setup-myproject.env`, with `myproject`
replaced by the board's name (the repository folder's name, the same value as
`BOARD` below) in every block and file name. One file per board:
a machine can hold several boards, and a shared `~/.wf-setup.env` from an earlier
setup is another board's values, which the rules forbid reading. It holds no
secrets. Fill it in from the look and the interview. Every answer below ships
empty on purpose: each is the user's answer, never your pick and never another
board's values (`MODEL` and `EFFORT` decide what every task costs). The one
exception is a profile the user hands you (the profile section after step 3).

```bash
cat > ~/.wf-setup-myproject.env <<'EOF'
# Where the product is distributed (read access is required while it is private)
ENGINE_REPO=gnarlysoft-ai/workflow-engine
PLUGINS_REPO=gnarlysoft-ai/workflow-engine-plugins
STORE_REPO=gnarlysoft-ai/workflow-engine-integrations
# Release channel: the one your vendor gave you. Empty when you were given
# none: it never defaults, and step 1b takes the newest release instead.
CHANNEL=
# The engine version to install, without the v (step 1b fills it in)
VERSION=
# Where the installer package is downloaded to (step 1c)
PKG_DIR="$HOME/wf-install"
# Question 1: the repository the board works on, and the board's name (= the
# folder's name)
REPO_DIR="$HOME/code/myproject"
BOARD=myproject
# Question 1: where the shared lanes, this board's project plugin and its
# answers file live: a folder of the user's, never an application-data or
# cache directory
PLUGINS_DIR="$HOME/wf-plugins"
# The board's dashboard port on this machine: the first free one from 8787
PORT=8787
# The interview's answers. Step 3c stops while one it needs is empty. A value
# with a space goes in double quotes (TEST_COMMAND="npm test"): unquoted, the
# shell drops it, and step 3c stops.
# Question 1: the repository's test command, from answer 1 or its own files
# (step 3a); empty when nothing names one
TEST_COMMAND=""
# Questions 1 and 2: owner/name of each repository the board works in, the
# board's own first, comma-separated
GITHUB_REPOS=
# Question 2: none, github, jira, or github,jira
TRACKERS=
# Question 2, with jira only: the site address, the account email, the
# project key
JIRA_SITE=
JIRA_EMAIL=
JIRA_PROJECT=
# Question 3: now, later or never; with now, the test environment's address
QA=
QA_URL=
# Question 4: the AI CLI (claude, codex or gemini), and the percent of its
# plan's week to slow down at, 0 for off
BACKEND=
THROTTLE=
# Question 5: the model and the reasoning effort the lanes pass to that CLI
MODEL=
EFFORT=
# Question 6, yes or no each: keep the shared lanes up to date, autopilot,
# start new tracker items without an Approve, merge once every check passes
LANES_UPDATE=
AUTOPILOT=
AUTO_START=
AUTO_MERGE=
# Question 7: the read-only viewers' names, space-separated (empty for none)
VIEWERS=""
export PATH="$HOME/.local/bin:$PATH"
EOF
```

`BOARD` must be the repository folder's name, exactly: `wf init` records it as
the board's `repo_name`, and the board pass names this board's two services
after it, `local.wf.loop.<BOARD>` and `local.wf.dashboard.<BOARD>` (user
services of this account; "Where things are" at the end says where their
files and logs are). Use a folder name of letters, digits, `-` and `_`.

**The installer's reader.** Both passes print `wf.install/1` with `--json`:
JSON lines: `step` lines (`start`, `ok`, `skip`, `fail`, `needs`), one `plan`, and
a last `result` with `done`, `exit` and `needs` (`[{id, reason, command,
detail}]`). The installer redacts every line and prints no secret, so its
output may be shown as it is. Write this reader once; steps 2, 4 and 6 run it
on what a pass printed. It judges nothing: it shows the failed steps, every
need, doctor's sign-off sentence and the pass's own `done`.

```bash
cat > ~/.wf-setup-myproject.read.py <<'PY'
import json, sys
lines = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
result = next((line for line in lines if line.get("type") == "result"), None)
plan = next((line for line in lines if line.get("type") == "plan"), None)
if result is None and plan is not None:  # a --plan run: nothing was done
    for action in plan["actions"]:
        admin = f' (admin: {action.get("command")})' if action.get("admin") else ""
        print(f'WILL     {action["id"]}: {action["does"]}{admin}')
    for item in plan["prerequisites"]:
        if not item["present"]:
            print(f'MISSING  {item["id"]}' + (f': {item["command"]}' if item.get("command") else ""))
    sys.exit(0)
for line in lines:
    if line.get("type") == "step" and line.get("status") == "fail":
        print(f'FAIL     {line["id"]}: {line.get("detail", "")}')
if result is None:
    sys.exit("no result line: the run stopped before its end. Show the user the lines above, then run it again.")
for need in result["needs"]:
    print(f'NEED     {need["id"]} ({need["reason"]})\n         {need.get("detail", "")}'
          f'\n    fix: {need.get("command") or "(none named)"}')
for line in lines:
    if line.get("type") == "step" and line.get("id") == "board.doctor" and line.get("status") in ("ok", "needs"):
        print("SIGN-OFF:", line.get("detail", ""))
if result.get("updates"):
    print(f'UPDATES  {result["updates"]["state"]}: {result["updates"]["detail"]}')
print(f'exit {result["exit"]}, the {result["stage"]} pass, engine {result["version"]}')
print("VERDICT:", "DONE" if result["done"] else "NOT YET")
PY
```

**Who owes a need.** Every need has a `reason`; it says who acts:

| `reason` | Who owes it | What you do |
|---|---|---|
| `board` | you | from the machine pass: the board is left to make (steps 3 and 4). From the board pass: a viewer or a switch the user turns on with `--yes`: give them the command |
| `admin` | the user | an admin step the installer cannot take here because this user may not use `sudo` (a system package, Linux linger, or the Linux updater's files): show its exact command and what it changes; they, or the machine's owner, run it (several: in order), then you run the pass again. The Linux updater's `sudoedit` of an existing `wf.env` is always theirs |
| `sign-in` | the user | an AI CLI, MCP server or plugin to sign in to: the command is theirs to run (step 5). From the machine pass's `updater`: GitHub, which the updater reads the channel from (`gh auth status`) |
| `tool` | the user | a tool the pass could not install or that does not work: its command installs or fixes it, often with admin rights |
| `path` | the user | a new terminal does not find `wf`: the line to add to their shell profile (the installer never edits one) |
| `login-session` | the user | the pass ran as root: run it as their own account, without `sudo`. From the machine pass's `updater` on a Mac reached only over SSH: the updater starts at their next login at the Mac's screen; nothing to run |
| `recipe` | the lane plugin's owner | no installed plugin says how to install the item, or two disagree: report it as theirs; the user may install it by hand with the fix shown |
| `conflict` | the user | something on the machine is in the way (another board's service or port, a newer engine, a `wf` that is not the engine's, too little disk, another account's updater): say what, and never move another board's or account's things |
| `doctor` | depends on the row | a `wf doctor --onboarding` row that is not ok, with doctor's own fix: step 6 lists the known ones |
| `consent` | the user | admin steps wait for one yes: show every action with `admin: true` in that pass's plan and what it changes; on their yes, run the need's command (it carries `--yes <plan id>`) |
| `password` | the user | `sudo` needs their password and this run has no terminal: they run the need's command in their own terminal, where `sudo` asks; then you run the pass again |

## Step 1. Get the installer

The engine installs from one file per release, the same file for every OS and
CPU: `workflow-engine-<version>-install.sh`, with its `.sha256` beside it. It
is a release asset of the engine's private repository, so only a GitHub
account with access to it can download it (the team, for now). Nothing in
this skill downloads it another way.

The look before the interview already showed the machine, the boards on it
and how full the disk is (the disk rule).

Only `gh` is this skill's to have before the installer runs: the steps below
sign in and download with it. If it is missing, the user installs the GitHub
CLI by its own instructions (https://github.com/cli/cli#installation); that
can need admin rights, so it is theirs to run. `git`, `python3` and `uv` are
the installer's: it installs `uv` itself, and names any other that is missing
as a need, with its fix.

### 1a. GitHub access (user step)

The engine, its shared lanes and its extension store are private GitHub
repositories while the product is in beta. This machine needs a GitHub account
with read access to all three.

Ask the user to run `gh auth login` in their own terminal on this machine
(browser or device code), then:

```bash
. ~/.wf-setup-myproject.env
gh auth status
for r in "$ENGINE_REPO" "$PLUGINS_REPO" "$STORE_REPO"; do gh api "repos/$r" --jq .full_name; done
gh auth setup-git   # plain git can now clone the private extension store
```

**Verify**: three repository names print. **If one is `Not Found`**, the account
has no access: stop and tell the user to ask their Workflow Engine contact to
grant their GitHub account read access to those three repositories. There is
no public download yet, so there is no way past this step without it.

If the interview's needs list waited for this access, read the catalog and
show the list now, as the interview says.

### 1b. Pick the version

With a channel (the one your vendor gave you, in `CHANNEL`):

```bash
. ~/.wf-setup-myproject.env
gh api "repos/$ENGINE_REPO/contents/deploy/channels/$CHANNEL.json?ref=main" \
  -H "Accept: application/vnd.github.raw" --jq .version
```

With none, list the releases and take the newest, the first line (a version
the user named unasked wins):

```bash
. ~/.wf-setup-myproject.env
gh release list --repo "$ENGINE_REPO" --exclude-drafts --exclude-pre-releases --limit 5
```

Set `VERSION=` in the settings file to that version, without the `v`.

**The oldest version this skill installs is the first release after 1.3.9.**
Only from there does the board pass finish on `wf doctor --onboarding`
(`board.doctor`): at 1.3.9 it skips that finish, names it as a need, exits 3
on every run and refuses `--no-smoke`, so step 6 could never end. Check the
version:

```bash
. ~/.wf-setup-myproject.env
echo "$VERSION" | awk -F. '{ ok = $1+0 > 1 || ($1+0 == 1 && ($2+0 > 3 || ($2+0 == 3 && $3+0 >= 10))); word = ok ? "OK" : "TOO OLD"; print word, $0; exit !ok }'
```

If it prints `TOO OLD`, stop here and tell the user why. From a channel: the
vendor has not moved it past 1.3.9 yet, so the user asks them to. From the
release list: pick a newer release; if the list has none, the first release
that can finish is not out yet, so stop until it is.

**Verify**: a version such as `1.3.10` prints, and the check prints `OK`. If
the channel is `Not Found`, ask the user which channel their vendor gave them;
never guess, and never use another customer's channel.

### 1c. Download it and check it

```bash
. ~/.wf-setup-myproject.env
mkdir -p "$PKG_DIR" && cd "$PKG_DIR" &&
  gh release download "v$VERSION" --repo "$ENGINE_REPO" --pattern 'workflow-engine-*-install.sh*' --clobber
```

Or on the user's own computer: in a browser signed in to GitHub, open the
release `v<VERSION>` of the engine repository, download
`workflow-engine-<VERSION>-install.sh` and its `.sha256`, and copy both into
`$PKG_DIR` on this machine (for example with `scp`). Either way, check it (the
`.sha256` names the file without a folder, so check from `$PKG_DIR`):

```bash
. ~/.wf-setup-myproject.env
cd "$PKG_DIR" && f="workflow-engine-$VERSION-install.sh.sha256" &&
  if command -v sha256sum >/dev/null 2>&1; then sha256sum -c "$f"; else shasum -a 256 -c "$f"; fi
```

**Verify**: `workflow-engine-<VERSION>-install.sh: OK`. Anything else: do not
run the file; download it again.

## Step 2. The machine pass

**Ask once, here.** This is the installer's one consent (the rules). Tell the
user what the two passes do as this user, with no admin rights, and wait for
a yes that covers both:

- the machine pass, now: the engine with its dashboard and the bundled skills
  under `~/.local/share/wf` and `~/.local/bin/wf`, and `uv` when the machine
  has none. It needs about 2 GB free in the home folder and edits no shell
  profile;
- the board pass, in step 4: every tool, AI CLI, CLI plugin, MCP server and
  skill the board's lanes declare, the board's loop and a writable dashboard
  as this user's services (they keep running after this chat), and one agent
  run that proves the board;
- no admin rights on this yes: a system package, an apt source or Homebrew's
  own installer (it runs `sudo` itself) comes back as one `consent` need, and
  you ask again then, showing each admin command.

Then:

```bash
. ~/.wf-setup-myproject.env
cd "$PKG_DIR" && sh "workflow-engine-$VERSION-install.sh" --json ${CHANNEL:+--channel "$CHANNEL"} > ~/wf-install-myproject.machine.jsonl; echo "exit=$?"
python3 ~/.wf-setup-myproject.read.py ~/wf-install-myproject.machine.jsonl
```

It runs as this user, never with `sudo`, and refuses root. A good machine pass
is **exit 3 with one need, `board`**: the engine works, and the board is left
to make. Any other need: find its reason in the table above, have it done,
then run this block again. Running it again is safe: the same version changes
nothing.

If `python3` is missing, the reader cannot run, and the pass names it as a
need too (`require.python.hook`). Read the JSON lines as they are (they carry
no secret), have what they name installed, and run step 2 again.

**Verify**: the reader's only `NEED` line is `board (board)` (on a Mac reached
over SSH, `updater (login-session)` may stay: it clears at the user's next
login at its screen), and
`wf --version` prints `wf <VERSION>`.

**Updates.** With a channel (the one their vendor gave them, in `CHANNEL`),
the block above passes `--channel` and the pass's last step, `updater`, turns on
automatic updates: on a Mac it loads the updater's agent; on Linux it names the
admin commands that install it, as `admin` needs, in order. The reader's
`UPDATES` line says where that stands. With no channel it is `off`, and the
engine stays at this version: tell the user so. An installer from before this
option exits 2 naming `--channel`: run the block again without
`${CHANNEL:+--channel "$CHANNEL"}` and tell the user the same.

## Step 3. Create the board

### 3a. The repository

The repository is the interview's answer 1. Clone it if it is not on the
machine yet (`gh repo clone <owner>/<name> "$REPO_DIR"`). It must be a git
repository with an `origin` remote, a clean working tree, and a git identity
for this user:

```bash
. ~/.wf-setup-myproject.env
git -C "$REPO_DIR" remote -v && git -C "$REPO_DIR" status --porcelain
git config --global user.name || echo "MISSING: the user sets their name"
git config --global user.email || echo "MISSING: the user sets their email"
```

A missing identity is the user's to set in their own terminal, like a sign-in
(`git config --global user.name "…"`, `git config --global user.email "…"`).
Unless answer 1 named it, read the repository's test command from its own
files (its README, CLAUDE.md or AGENTS.md, its CI config, `package.json`
`scripts.test`, a Makefile; for example `npm test`, `pytest`, `make test`) and
set `TEST_COMMAND=` to it, in double quotes (`TEST_COMMAND="npm test"`). If
none of them names one, leave it empty: the
lanes' test gate then refuses every landing, and step 6 names it as a need.

Read the repository's default branch; step 3c writes it into the answers too
(the lanes assume `main` otherwise, and doctor refuses the mismatch):

```bash
. ~/.wf-setup-myproject.env
git -C "$REPO_DIR" remote set-head origin --auto >/dev/null
git -C "$REPO_DIR" symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##'
```

The board pushes branches to `origin` with this user's git credentials (the
`gh` sign-in), so that account needs write access to the repository. Doctor's
`push_access` row proves it at the board pass's finish (step 6); for a
repository the user cannot push to, use their fork.

### 3b. The shared lanes (wf-toolkit)

```bash
. ~/.wf-setup-myproject.env
TAG=$(gh api "repos/$PLUGINS_REPO/git/matching-refs/tags/wf-toolkit-v" --paginate --jq '.[].ref' | sed 's#refs/tags/##' | sort -V | tail -1)
echo "$TAG"
mkdir -p "$PLUGINS_DIR"
git -c advice.detachedHead=false clone -q --depth 1 --branch "$TAG" --filter=blob:none --sparse "https://github.com/$PLUGINS_REPO.git" "$PLUGINS_DIR/.toolkit-src"
git -C "$PLUGINS_DIR/.toolkit-src" sparse-checkout set wf-toolkit
ln -sfn "$PLUGINS_DIR/.toolkit-src/wf-toolkit" "$PLUGINS_DIR/wf-toolkit"
grep '^version' "$PLUGINS_DIR/wf-toolkit/plugin.yaml"
```

`wf plugin new` looks for the toolkit beside the new plugin, which is why it is
linked into `$PLUGINS_DIR`.

### 3c. The answers file, and the project plugin from it

One file holds every answer: `$PLUGINS_DIR/$BOARD.answers.json`, in the
`wf.setup-answers/1` shape. The block below writes it from the interview's
answers in the settings file and the repository's default branch, as the table
under the interview maps them. Two commands read it, each only its own part:
`wf plugin new --answers` its `plugin` section (the toolkit's config keys: each
required key of the toolkit's `config.schema.yaml` needs a one-line value, as
a two-line value breaks assembly), and the board pass the rest (step 4). The
plugin values that are not answers are generic starters. It never holds a
secret: step 5 writes those. With a profile from another machine (the profile
section after this step), its `toolkit.config.yaml` is the `plugin` section:
pass that file to `wf plugin new --answers` instead, and keep this file's
other sections for the board pass.

```bash
set -a; . ~/.wf-setup-myproject.env; set +a   # the answers reach Python as its environment
BASE=$(git -C "$REPO_DIR" symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##')
python3 - "$PLUGINS_DIR/$BOARD.answers.json" "$BASE" ~/.wf-setup-myproject.env <<'PY' &&
import json, os, shlex, sys
path, base = sys.argv[1], sys.argv[2].strip()
v = {k: os.environ.get(k, "").strip() for k in (
    "BOARD", "TEST_COMMAND", "GITHUB_REPOS", "TRACKERS", "JIRA_SITE", "JIRA_EMAIL", "JIRA_PROJECT",
    "QA", "QA_URL", "VIEWERS", "BACKEND", "MODEL", "EFFORT", "THROTTLE",
    "LANES_UPDATE", "AUTOPILOT", "AUTO_START", "AUTO_MERGE")}
lines = open(sys.argv[3]).read().splitlines()  # sourced, `KEY=a b` runs `b` and leaves KEY empty
if lost := [k for k in v if any(line.startswith(f"{k}=") and len(shlex.split(line, comments=True)) > 1
                                for line in lines)]:
    sys.exit(f"{', '.join(lost)} in ~/.wf-setup-myproject.env has a space outside quotes, so the shell dropped it:"
             " put the value in double quotes, run this block again")
trackers = {t for t in v["TRACKERS"].split(",") if t} - {"none"}
need = ["GITHUB_REPOS", "TRACKERS", "QA", "BACKEND", "MODEL", "EFFORT", "THROTTLE",
        "LANES_UPDATE", "AUTOPILOT", "AUTO_START", "AUTO_MERGE"]
need += ["JIRA_SITE", "JIRA_EMAIL", "JIRA_PROJECT"] if "jira" in trackers else []
need += ["QA_URL"] if v["QA"] == "now" else []
if empty := [k for k in need if not v[k]]:
    sys.exit(f"{', '.join(empty)} empty in ~/.wf-setup-myproject.env: set the interview's answer, run this block again")
wrong = [k for k, ok in (("QA", v["QA"] in ("now", "later", "never")),
                         ("TRACKERS", trackers <= {"github", "jira"}),
                         ("THROTTLE", v["THROTTLE"].isdigit() and int(v["THROTTLE"]) <= 100),
                         *((k, v[k] in ("yes", "no")) for k in ("LANES_UPDATE", "AUTOPILOT", "AUTO_START", "AUTO_MERGE")))
         if not ok]
if wrong:
    sys.exit(f"{', '.join(wrong)} in ~/.wf-setup-myproject.env is not one of the values its comment lists")
yes = {k: v[k] == "yes" for k in ("LANES_UPDATE", "AUTOPILOT", "AUTO_MERGE")}
plugin = {
  "context_gathering_steps": "1. Read the repository README, and CLAUDE.md or AGENTS.md if there is one. 2. Read the files the task names, and the tests next to them.",
  "conventions_skill": "project-conventions",
  "findings_files": "code_findings.json visual_findings.json correctness_findings.json security_findings.json",
  "infra_repos": "(none)",
  "integration_checks": "Check that a change on one side of an interface (an API, shared types, a database schema) is matched on the other side.",
  "target_context_limit": "200000",
  "task_type_taxonomy": "backend | frontend | fullstack | docs | chore",
  "test_command_rule": "use the repository's own documented test command (README, CLAUDE.md, CI config, package.json scripts.test or a Makefile), run from the repository root",
  "rollup_success_action": "transition the parent task to code-approved",
  "td_plan_docs_path": "docs/specs",
  "web_findings_repo": v["BOARD"],
  "backend_default": v["BACKEND"],
  "effort_default": v["EFFORT"],
  "autopilot": "true" if yes["AUTOPILOT"] else "false",
}
if v["QA"] != "later":  # later: the deferral alone holds QA off (step 3e); undeferring hands it back
    plugin["qa_applicable"] = "true" if v["QA"] == "now" else "false"
for k in ("model_default", "model_design", "model_minor_develop_reproduce", "model_minor_develop_fix",
          "model_minor_develop_review", "model_minor_develop_refix", "model_feature", "model_publish"):
    plugin[k] = v["MODEL"]
for key, value in (("test_gate_command", v["TEST_COMMAND"]), ("base_branch", base),
                   ("qa_base_url_default", v["QA_URL"] if v["QA"] == "now" else "")):
    if value:
        plugin[key] = value
github = "github" in trackers  # installed on every board: the lanes call its actions
integrations = {"github": {"enabled": github, "config": {
    "GITHUB_REPOS": v["GITHUB_REPOS"], "GITHUB_INTAKE_ENABLED": github, "GITHUB_INTAKE_LABEL": "ai-ready",
    "GITHUB_CLAIMED_LABEL": "wf-seeded", "GITHUB_REINTAKE_LABEL": "re-intake", "GITHUB_BRANCH_PREFIX": "feat",
    "GITHUB_MAX_SEEDS_PER_TICK": 5, "GITHUB_CLOSE_ON_DONE": True, "GITHUB_ROUTER_WORKFLOW": "intake-router"}}}
if "jira" in trackers:
    integrations["jira"] = {"enabled": True, "config": {
        "JIRA_BASE_URL": v["JIRA_SITE"], "JIRA_EMAIL": v["JIRA_EMAIL"], "JIRA_PROJECT": v["JIRA_PROJECT"],
        "AI_FIX_ROUTER_WORKFLOW": "intake-router"}}
answers = {
  "schema": "wf.setup-answers/1",
  "plugin": plugin,
  "settings": {
    "WF_BUDGET_THROTTLE_PCT": int(v["THROTTLE"]),
    "WF_PLUGIN_DELIVERY": "auto" if yes["LANES_UPDATE"] else "detect",
    "WF_AUTOPILOT": yes["AUTOPILOT"],
    "WF_AUTO_MERGE": "*" if yes["AUTO_MERGE"] else "",
  },
  "integrations": integrations,
}
if v["QA"] != "later":
    answers["settings"]["WF_QA_APPLICABLE"] = v["QA"] == "now"
if v["VIEWERS"]:
    answers["viewers"] = v["VIEWERS"].split()
json.dump(answers, open(path, "w"), indent=2)   # JSON is YAML: both readers take it
print("wrote", path)
PY
cd "$PLUGINS_DIR" &&
wf plugin new "$BOARD" --plugins-dir "$PLUGINS_DIR" --answers "$PLUGINS_DIR/$BOARD.answers.json" &&
git -C "$PLUGINS_DIR/$BOARD" init -q -b main && git -C "$PLUGINS_DIR/$BOARD" add -A \
  && git -C "$PLUGINS_DIR/$BOARD" commit -qm "Scaffold $BOARD" &&
wf assemble "$PLUGINS_DIR/$BOARD" --plugins-dir "$PLUGINS_DIR"
```

Each command runs only if the one before it succeeded, so a refused answers
file scaffolds nothing, even when one from an earlier attempt is still there.
When it stops on an empty or a wrong value, the interview's answer is missing
from the settings file: set it there, never a pick of yours, and run the block
again.

If `wf assemble` names a missing key, read that key's description in
`$PLUGINS_DIR/wf-toolkit/config.schema.yaml`, add a one-line value to
`$PLUGINS_DIR/$BOARD/toolkit.config.yaml`, commit, and assemble again.

The project plugin is now a git repository at `$PLUGINS_DIR/$BOARD`. It is the
user's: tell them where it is, and offer to add a remote of theirs and push it.
Pushing is their call.

**Install trees in task worktrees.** Tasks run in git worktrees, which carry no
untracked files, so a test command that needs installed dependencies fails
there for a reason unrelated to the work. Before step 3d:

1. Find the install trees the test command needs: untracked, ignored folders
   such as `node_modules` (at the root and in each workspace package),
   `vendor` or `Pods`. List them with `git status --ignored --porcelain` or by
   checking each workspace folder; do not guess.
2. If the repository has a lockfile but no install tree yet, the test command
   cannot pass anywhere. Ask before installing (the disk rule applies), then
   run the repository's own install command once in `REPO_DIR`. Run the test
   command there to prove it.
3. Set `worktree_link_paths` in
   `$PLUGINS_DIR/$BOARD/toolkit.config.yaml` to those paths (found, not
   asked: tell the user which), commit, and run
   `wf assemble` again. Write the value as a list in **single** quotes inside
   **double** quotes, for example
   `worktree_link_paths: "['node_modules', 'apps/api/node_modules']"`. The
   lanes paste the value inside a double-quoted string, so a value containing
   double quotes produces a workflow file that does not parse. Never link a
   Python environment that holds an editable install (the key's description
   in `config.schema.yaml` says why).
4. After step 3d, load every `$REPO_DIR/.workflow/workflows/*.yaml` with a YAML
   parser. Treat any `removed (no longer shipped)` line in an install's output
   as a stop: it means a workflow did not assemble.

**Verify**: `Assembly OK … workflows validate.`

### 3d. The board and its three plugins

```bash
. ~/.wf-setup-myproject.env
cd "$HOME"
wf init --repo "$REPO_DIR"
wf plugin install "$PLUGINS_DIR/wf-toolkit" --repo "$REPO_DIR"
wf plugin install 'github@^1' --repo "$REPO_DIR"     # the lanes call its actions; the consumer refuses to install without it
case ",$TRACKERS," in *,jira,*) wf plugin install 'jira@^1' --repo "$REPO_DIR";; esac   # when answer 2 named Jira
wf plugin install "$PLUGINS_DIR/$BOARD" --repo "$REPO_DIR"
wf plugin status --repo "$REPO_DIR" | tail -3
wf workflow check -w "$REPO_DIR/.workflow"
```

The board lives in `$REPO_DIR/.workflow`; the install also writes `.claude/`
and `.agents/`. Keep all three out of git without touching the repository's
tracked files:

```bash
. ~/.wf-setup-myproject.env
for p in .workflow/ .claude/ .agents/; do
  git -C "$REPO_DIR" status --porcelain=v1 | grep -qxF "?? $p" && echo "$p" >> "$REPO_DIR/.git/info/exclude"
done
git -C "$REPO_DIR" status --porcelain
python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["repo_name"])' "$REPO_DIR/.workflow/workspace.json"
```

**Verify**: `All plugins current.`, every workflow `OK`, `git status --porcelain`
prints nothing, and the last line prints `$BOARD`. (If `.claude/` was already
tracked and the install changed a
file in it, tell the user which files changed and let them read the diff in
their own terminal: it can hold tokens, so it is never printed here. Never
commit or stash it for them.)

### 3e. What only the installed lanes can name

Two answers name things the board learns only from the lanes it now has, so
they go into the same answers file now, read with the running engine's own
functions (the rule on reading the engine), never from a name written here:

- QA later (answer 3): `stages_deferred`, every optional stage the installed
  lanes declare. Finished work then reads deferred instead of unverified until
  the user runs `wf stage undefer <stage>`, after which the board's own
  `WF_QA_APPLICABLE` decides again (step 3c writes none for "later").
- Starting new tracker items without an Approve (answer 6):
  `settings.WF_INTAKE_AUTO_APPROVE`, for each chosen tracker whose installed
  extension vouches for its items. A tracker that does not leaves each new
  item waiting for the user's Approve; the block says which, so tell the user.

It also leaves out answer 6's lanes-update choice when the board already has
one of its own: a choice already made stands.

```bash
set -a; . ~/.wf-setup-myproject.env; set +a
"$(head -1 "$(command -v wf)" | cut -c3-)" - "$PLUGINS_DIR/$BOARD.answers.json" "$REPO_DIR/.workflow" <<'PY'
import json, os, sys
from pathlib import Path
from workflow_engine.cycles import optional_stage_names
from workflow_engine.intake_auto_approve import offered
from workflow_engine.loader import load_workflows
from workflow_engine.settings import SOURCE_DEFAULT, resolve_with_source
path, ws = Path(sys.argv[1]), Path(sys.argv[2])
answers = json.loads(path.read_text())
answers.pop("stages_deferred", None)
answers["settings"].pop("WF_INTAKE_AUTO_APPROVE", None)
if resolve_with_source(ws, "WF_PLUGIN_DELIVERY")[1] != SOURCE_DEFAULT:
    answers["settings"].pop("WF_PLUGIN_DELIVERY", None)
    print("lanes updates: the board's own choice stands")
if os.environ.get("QA") == "later":
    stages = list(optional_stage_names(load_workflows(ws / "workflows")))
    print("deferred until the user sets it up:", ", ".join(stages) or "nothing (the lanes declare no optional stage)")
    if stages:
        answers["stages_deferred"] = stages
if os.environ.get("AUTO_START") == "yes":
    chosen = [t for t in os.environ.get("TRACKERS", "").split(",") if t and t != "none"]
    vouched = [t for t in chosen if t in offered(ws)]
    if vouched:
        answers["settings"]["WF_INTAKE_AUTO_APPROVE"] = vouched
    for t in chosen:
        print(t, "items start without an Approve" if t in vouched
              else "does not vouch for its items: each new one waits for the user's Approve")
path.write_text(json.dumps(answers, indent=2) + "\n")
PY
```

**Verify**: it prints what it deferred and how each tracker's new items
start, and exits 0.

## Optional: copy settings from another machine (a profile)

A profile carries a board's setup **without secrets**: the plugin set with
versions and sources, which extensions are on or off, and the non-secret
settings. It never carries `.env`, `.env.integrations`, `users.json`, tasks or
pauses.

If the engine has the command (`wf profile --help >/dev/null 2>&1 && echo yes`;
an engine without it exits 2), use it:

```bash
. ~/.wf-setup-myproject.env
wf profile apply <profile-file> --repo "$REPO_DIR"
```

Until that command ships, do the same by hand from files the user copies off
the other machine (`<ws>` is its `.workflow` directory):

| From the other machine | Apply here |
|---|---|
| `wf plugin status --repo <repo>` (versions) | step 3b with `TAG=wf-toolkit-v<version>`; step 3d with `<extension>@<version>` |
| its project plugin's `toolkit.config.yaml` | the `plugin` section of the answers file (step 3c) |
| `<ws>/settings.json` | each key's value in the answers file's `settings` section |
| `<ws>/integration-overrides.json` | each extension's `enabled` in the answers file's `integrations` section |
| each extension's non-secret values: `curl -s localhost:<port>/api/integrations/<name>/config`, its `values` | that extension's `config` in the answers file's `integrations` section |

Never ask for, copy or accept the other machine's `.env`, `.env.integrations`
or `users.json`: those hold its secrets. Secrets are re-entered here in step 5.

## Step 4. The board pass

### 4a. Install what the lanes need, and the board's services

The board pass first applies the answers file through the board's own writers
(its settings, each extension's switch and values, the deferred stages; one
`answers.<section>.<key>` step each), naming as a need what only the user may
do: adding a viewer, turning merging on. Then it reads the lanes this board
now has and installs, as this user, everything they declare: the tools, the
AI CLI each agent step runs, the hook `python3`'s modules, CLI plugins, MCP
servers and skills. Then it installs the board's loop and dashboard as this
user's services (`board.services`), and finishes on `wf doctor --onboarding
--smoke` (`board.doctor`), which spends one agent run. The yes from step 2
covers it. Show the plan first; it changes nothing:

```bash
. ~/.wf-setup-myproject.env
wf setup install --board "$REPO_DIR/.workflow" --answers "$PLUGINS_DIR/$BOARD.answers.json" --port "$PORT" --json --plan > ~/wf-install-myproject.board.jsonl; echo "exit=$?"
python3 ~/.wf-setup-myproject.read.py ~/wf-install-myproject.board.jsonl
```

Exit 2 with no plan is a refused answers file: the lines name every fault
(never a value), and nothing was written. Correct the answer in the settings
file, run step 3c's block again (it rewrites the file first; `wf plugin new`
then refuses the plugin that is already there, as expected) and step 3e's,
then this one.

Tell the user what it will install (the `MISSING` lines) and which steps are
admin (they come back as needs). The AI CLI it names (`require.tool.<cli>`)
is the one answer 4 chose; any other is a mismatch to report, not a new
question. If anything there was not in what they said yes to (the disk rule
included), ask before going on. Then run it:

```bash
. ~/.wf-setup-myproject.env
wf setup install --board "$REPO_DIR/.workflow" --answers "$PLUGINS_DIR/$BOARD.answers.json" --port "$PORT" --json > ~/wf-install-myproject.board.jsonl; echo "exit=$?"
python3 ~/.wf-setup-myproject.read.py ~/wf-install-myproject.board.jsonl
```

A first run is seldom done: it names sign-ins and secrets (step 5), admin
steps for the user, and doctor rows. Steps 4b to 6 work through them.

The dashboard it installs is **writable**: it saves settings and answers
checkpoints. The engine's own guidance for a machine
that runs the loop is a read-only dashboard (`WF_DASHBOARD_READONLY=1`), so the
loop is the only writer of task files. The installer has no read-only option
yet, and the next board pass rewrites the services, which undoes a hand edit
of either, so this skill cannot make it read-only. Tell the user; if they want
it read-only, report that it waits on an installer option.

**Verify**: the reader prints a `VERDICT:` line and no `FAIL board.services`
line, and the dashboard answers:
`curl -s "localhost:$PORT/api/version"`. If `board.services` waits on an item
(`skip`) or names a need, deal with that need, then run the block again.

### 4b. The trackers

The board pass wrote each extension's values and switched its poller on or off
from the answers file (answer 2): `integrations.github` always, since the lanes
call its actions, and `integrations.jira` when Jira was chosen. Its
`answers.integrations.*` lines show each one written or already so. Read back
what the GitHub extension holds:

```bash
. ~/.wf-setup-myproject.env
curl -s "localhost:$PORT/api/integrations/github/config" | python3 -c 'import json, sys; print(json.dumps(json.load(sys.stdin)["values"], indent=2))'
```

A poller ships **off**, and `GITHUB_INTAKE_ENABLED: true` alone does not
switch it on: the file's `enabled: true` is what does, through the writer
`wf integration enable github` uses. Its status card
(`.workflow/integrations/github.json`) appears after the loop's next
integration pass (five minutes by default). Run the board pass again (step 6)
after it exists. In the loop's first pass after it starts, doctor grades a
poller with no card yet as waiting and says when to check again; after that
pass, no card is a refusal. Jira's API token is a secret: step 5.

If answer 2 chose GitHub issues, check that the three labels exist in each
repository (`gh api 'repos/<owner>/<name>/labels?per_page=100' --jq '.[].name'`;
`gh api` avoids the GraphQL limit that `gh label list` can hit). If any is
missing, ask before creating them: they change a shared repository. Name the
labels and why the poller needs them, offer to create them
(`gh label create <name> -R <owner>/<name>`), and accept "I'll create them
myself".

`GITHUB_ROUTER_WORKFLOW` names the workflow a seeded issue lands in. Without it
(or `GITHUB_WORKFLOW`) the poller reports itself unconfigured on every pass.
`intake-router` is the lane that reconciles an issue and lets a human confirm
the route; `wf workflow check` lists it.

The file carries every required key, including those with a default: the
extension records them as required, and doctor refuses a required key that is
only a default (the board pass names it as a `doctor.required_env` need).
**Verify**: the values above are the file's, and the reader shows no
`FAIL answers.` line.

### 4c. Safe defaults

Live-behaviour switches stay at their safe values unless the user chose
otherwise in the interview, and the answers file wrote them: auto-merge off
unless answer 6 opted in (even then the user runs the command the board pass
names), and testing after merge on only for answer 3's "now" (for "later",
the deferral alone holds it off). The engine's default for the latter is on,
which parks every approved task waiting for a test environment.

The loop dispatches only work someone **armed** (from the dashboard, or
`wf cycle arm`); a new board does nothing until then. That is intended.

A new board starts with `WF_MCP_ALLOW=[]`: AI steps reach only the MCP servers
the board requires, and doctor's `mcp_allow` row lists what they reach and
what is hidden. If a lane's prompts use another server, ask the user before
letting it through, then:

```bash
. ~/.wf-setup-myproject.env
wf settings set WF_MCP_ALLOW '["<server>"]' -w "$REPO_DIR/.workflow"   # names as the agent CLI's MCP list prints them
```

**Verify**: `wf settings get WF_QA_APPLICABLE -w "$REPO_DIR/.workflow"` prints
answer 3's value from `settings.json`, and for "later" no value of the board's:
`wf stage deferrals -w "$REPO_DIR/.workflow"` lists the deferred stage instead.

## Step 5. Secrets and sign-ins (user steps)

The board pass named every required key the installed plugins declare that no
reader can see: each is a `doctor.required_env` need in the reader's output
(step 4a), its detail starting with the key's name and its fix naming the
file. For an extension's key, that fix says `set KEY in <ws>/.env`; an
extension's key goes through its config writer instead, which writes
`<ws>/.env.integrations`, read by doctor and the pollers as well. For each
key, decide which kind it is and where it goes:

| Kind | How to tell | Who writes it, where |
|---|---|---|
| An extension setting that is not secret (`GITHUB_REPOS`, labels, switches) | the extension's config schema (`GET /api/integrations/<name>/config`) types it as anything but `secret` | you, in the answers file's `integrations` section (step 3c), which the board pass writes |
| An extension secret | that schema types it `secret` | the user, in the dashboard's Extensions page (a write-only field), through the tunnel in "Reach the dashboard" |
| Any other secret (a token, password or key a workflow declares) | the name ends in `TOKEN`, `SECRET`, `PASSWORD` or `KEY`, or the user says so | the user, with the command below, into the file doctor's fix names |

**The secret command.** Give the user this block to paste into **their own
terminal on this machine** (not into this chat). It reads the value without
echoing it, refuses to overwrite a value already set, and keeps the file 0600:

```bash
wf_secret() {  # usage: wf_secret KEY FILE
  local k="$1" f="$2" v
  case "$k" in ""|*[!A-Za-z0-9_]*) echo "bad key name"; return 1;; esac
  umask 077; touch "$f" && chmod 600 "$f" || return 1
  if grep -q "^$k=" "$f"; then echo "$k is already set in $f; nothing changed"; return 1; fi
  IFS= read -rs -p "Value for $k (not shown): " v; echo
  [ -n "$v" ] || { echo "empty; nothing written"; return 1; }
  case "$v" in *"'"*) echo "contains a single quote; use the dashboard instead"; return 1;; esac
  [ -s "$f" ] && [ -n "$(tail -c1 "$f")" ] && echo >> "$f"
  printf "%s='%s'\n" "$k" "$v" >> "$f"; unset v
  echo "$k written to $f (value not shown)"
}
wf_secret GH_TOKEN "$HOME/code/myproject/.workflow/.env"   # example: KEY and the file doctor named
```

Afterwards you may check that a key is present: list the file's key names with
the block under the rules, which prints names and never a value.

**Sign-ins.** The user also:

- signs in to each agent CLI the lanes pin, as this user, with that CLI's own
  login command (Claude Code: `claude auth login`, or start `claude` and use
  `/login`); the board pass names a signed-out one as `doctor.agent_cli`;
- signs in to each MCP server or plugin the board pass names as a `sign-in`
  need, with the command it names;
- keeps `gh` signed in (done in step 1a). The loop uses that sign-in; a
  `GH_TOKEN` is needed only if the board pass names one.

**Verify**: each agent CLI's own status command reports signed in (Claude
Code: `claude auth status`). The secret needs are re-checked in step 6.

## Step 6. Run the board pass until it is done

Run the board pass again, the same block as step 4a, after each round of
fixes:

```bash
. ~/.wf-setup-myproject.env
wf setup install --board "$REPO_DIR/.workflow" --answers "$PLUGINS_DIR/$BOARD.answers.json" --port "$PORT" --json > ~/wf-install-myproject.board.jsonl; echo "exit=$?"
python3 ~/.wf-setup-myproject.read.py ~/wf-install-myproject.board.jsonl
```

Show the user every `NEED` and `FAIL` line, and quote the `SIGN-OFF` line as it
is. The pass is done only on **exit 0**, where the reader says `VERDICT: DONE`:
the board pass sets `done` itself, only when doctor's own `signoff.green` is
true (no refusal, the `smoke` row OK, no poller still waiting) and no need is
left. You grade nothing: read `done` and the `needs`, never the rows' words.
Exit 1 is a failed step that a re-run fixes; exit 3 is a need a person owes.

Each run with `--smoke` spends one agent run. While you fix other needs you may
add `--no-smoke` to the command: it re-checks without an agent run, and such a
run is never done. The run you report as the finish must be without it.

**You are done only when** the board pass exits 0, **or** every remaining need
is listed with its fix and who owes it (the table under the settings file).
Known ones:

- `doctor.agent_cli` refuses until the user has signed in to the agent CLI as
  this user (step 5).
- On macOS, a `doctor.tools` need naming `flock` comes on every Mac because
  doctor matches the word in the toolkit's portable lock helper, a known engine
  issue. Until a release fixes it, report that one need as known, not as a
  setup failure.
- A `doctor.integration_coverage` need that says waiting is not done, although
  doctor only warns: the loop's first pass has not reached that poller yet.
  Run the board pass again after the time it names; only a run with no
  waiting need finishes. `doctor.loop_heartbeat` right after the services
  started is the same: run it again a minute later.
- `doctor.push_access` refuses when the `gh` account cannot push to `origin`
  (step 3a). That is the user's to grant; the board cannot publish without it.
- `doctor.base_branch` refuses when `base_branch` in the project plugin's
  `toolkit.config.yaml` differs from the repository's default branch: set it,
  commit, then `wf assemble` and `wf plugin install "$PLUGINS_DIR/$BOARD" --repo "$REPO_DIR"`
  again. It warns when the repository has no `origin/HEAD`
  (`git -C "$REPO_DIR" remote set-head origin --auto`).
- A `doctor.oninit_preflight` need that says a lane's on_init hooks were "not
  measured" means the plugin that ships the lanes does not yet mark its
  pre-flight hook `preflight: true`. Doctor only warns, but the sign-off does
  not claim dispatch. Report it as known until that plugin release ships.
- A `doctor.oninit_preflight` refusal quotes the lane's own pre-flight (for
  example a dirty checkout or stashes). Fix the condition it names, then run
  the board pass again.
- `doctor.smoke` refuses when the hello-world step did not finish on the
  board's AI; its detail names why (usually the same sign-in or model problem
  `doctor.agent_cli` names). It warns, measuring nothing, when the run was
  declined (low disk or memory) or did not finish in time: run it again.
- A plugin's onboarding probe (`doctor.<plugin>.<probe>`) is graded like a
  hook and carries the plugin's own fix. One that says it runs only with
  `--smoke` spends real runs; the board pass without `--no-smoke` runs it.
- An `admin` need (a system package, or `board.linger`: lingering is off, so
  the services stop at logout and do not start at boot, and this user may not
  use `sudo`) is for the user or the machine's owner to run in their own
  terminal, then run the board pass again.
- A `recipe` need is the lane plugin owner's: no installed plugin says how to
  install that item. Report it with its fix; the user may install it by hand.
- A `conflict` need on `board.services` names what is in the way (another
  board's service, or a port in use): set the next free `PORT` in the settings
  file, never move the other board's.
- `answers.viewers.<name>` is the user's: `wf user add` prints that person's
  key once, to hand over privately, so the installer does not run it.
- `answers.settings.WF_AUTO_MERGE` comes only when answer 6 chose merging: the
  user runs the `wf settings set … --yes` it names; the installer never says
  yes for them.
- Phone access (answer 7) is not a line the pass prints: nothing in the
  installer serves the dashboard to a phone yet. Name it as waiting on an
  installer option, with today's way in ("Reach the dashboard").
- No test command (step 3a found none) is not a line either: the lanes' test
  gate refuses every landing until the user names the command and you set
  `test_gate_command` in `$PLUGINS_DIR/$BOARD/toolkit.config.yaml`, commit,
  `wf assemble` and `wf plugin install "$PLUGINS_DIR/$BOARD" --repo "$REPO_DIR"`.

**Then say what it means**, in one sentence: a task can run end to end on this
board (armed, dispatched by the loop, worked by the agent CLI, published), or
it cannot yet and what stops it. The needs and doctor's sign-off are the
evidence for that sentence; a list of healthy mechanisms is not the sentence.
No task has run at this point, so say that as well: the first task the user
arms is the proof.

## Optional: a model on this computer (Ollama)

Claude Code can run a board's steps on a model on this machine instead of an
Anthropic account. The board keeps the `claude` CLI; only where it sends its
requests changes.

1. Install Ollama (https://ollama.com/download) and download a model that can
   use tools: `wf agent models --backend claude-local` lists the suggested ones.
2. Give the model room: set Ollama's context length to 64k
   (`OLLAMA_CONTEXT_LENGTH=64000`, then restart Ollama).
3. Point the board at it:
   `wf settings set WF_LOCAL_MODEL <model> -w <ws>` (the address defaults to
   Ollama's own; set `WF_LOCAL_MODEL_URL` only for another server).
4. Route steps to it: Settings > AI models > Claude Code > Running on: This
   computer, or `wf settings set WF_MODEL_OVERRIDES '{"*": {"backend": "claude-local"}}'`.
5. Prove it now: `wf agent probe --backend claude-local -w <ws>` (it runs in
   this shell). Once the board pass has started the loop (step 4), prove it
   where steps run: `wf agent check --backend claude-local --wait -w <ws>`, then
   `wf doctor --onboarding -w <ws>` — every `local_model` row must be ✓.

A lane that has not run on this computer yet still runs, with a warning
before each step until that step has finished here once.

## Reach the dashboard from your laptop

The dashboard listens on the machine's loopback only. From the laptop:

```bash
ssh -N -L 8787:127.0.0.1:<PORT> <host>     # then open http://localhost:8787
```

Or, in the Workflow Engine desktop app: **Add a board → Connect to a dev box**,
pick the host; it opens the same tunnel and lists this board. Do not bind the
dashboard to a public address: a non-loopback bind needs
`WF_DASHBOARD_TOKEN`, and the engine refuses to start without it.

## Where things are

The board pass writes and rewrites the service files below on every run, so
never edit them by hand.

| What | Where |
|---|---|
| Engine | `~/.local/bin/wf`, a link into `~/.local/share/wf/` (one folder per version, with `current` and `previous`) |
| Installer log | `~/.local/share/wf/install.log`: every run of either pass |
| What the passes printed | `~/wf-install-<BOARD>.machine.jsonl`, `~/wf-install-<BOARD>.board.jsonl` (this skill's copies) |
| Board | `$REPO_DIR/.workflow` (`settings.json`, `.env`, `.env.integrations`, `plugins.json`) |
| Shared lanes and project plugin | `$PLUGINS_DIR/wf-toolkit`, `$PLUGINS_DIR/<BOARD>` (a git repo the user owns) |
| Answers file | `$PLUGINS_DIR/<BOARD>.answers.json`: the interview's answers, which `wf plugin new` and the board pass read (no secret) |
| Services (Linux) | systemd user units `local.wf.loop.<BOARD>.service` and `local.wf.dashboard.<BOARD>.service` in `${XDG_CONFIG_HOME:-~/.config}/systemd/user/` |
| Services (macOS) | LaunchAgents `~/Library/LaunchAgents/local.wf.loop.<BOARD>.plist` and `local.wf.dashboard.<BOARD>.plist` |
| Logs (Linux) | `journalctl --user -u local.wf.loop.<BOARD>`, `journalctl --user -u local.wf.dashboard.<BOARD>` |
| Logs (macOS) | `~/Library/Logs/local.wf.loop.<BOARD>.out` and `.err`, the same for `local.wf.dashboard.<BOARD>`; `launchctl print gui/$(id -u)/local.wf.loop.<BOARD>` shows the loop's state |
