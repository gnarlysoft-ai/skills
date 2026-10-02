---
name: workflow-engine-setup
license: MIT
description: >
  Set up the Workflow Engine on a machine: a fresh Linux dev box (a cloud VM
  such as EC2) or a Mac. Installs the engine and its updater, creates a board
  for one repository with the shared lanes, the GitHub extension and a project
  plugin, has the user write secrets themselves, starts the loop and dashboard
  as services, and proves the result with `wf doctor --onboarding`. Use when
  someone asks to install, set up, onboard, or copy a Workflow Engine board
  onto a machine.
---

# Set up the Workflow Engine

You are setting up the Workflow Engine on the machine this shell runs on. Work
through the steps **in order**. Every step ends with a **Verify** command; do
not start the next step until it passes. The finish line is step 7: the engine's
own `wf doctor --onboarding`, never your own judgement.

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
- **Ask before anything host-wide**: `sudo`, a package install, a systemd unit,
  a LaunchAgent. Show the command, say what it changes, then run it.
- **Ask before a decision that is the user's**, at the step where it comes up
  and not in one question at the end: installing the board's services (the
  loop and dashboard units); which agent CLI (backend), models and effort the
  lanes run on; turning on pollers or intake; making the dashboard writable;
  and any install over about 500 MB, or any install at all while the disk is
  more than 90% full. Say what it does and what it costs, then wait.
- **Never touch another board.** If `wf` is already installed or the machine
  already has boards (`wf host --json` lists them), do not reinstall the
  engine, re-run its installer or restart its services. Tell the user what you
  found and ask how to proceed.
- **Never read or copy from another board.** Not another board's config,
  plugin or tasks, not the desktop app's `boards.json`, not shell history, not
  another project's agent memory, and write nothing into any of them. This
  board's values come from the user's answers and from this repository. The
  one exception is a profile the user hands you (step 4).
- **Stop at user steps.** Signing in to GitHub, signing in to the agent CLI and
  typing secrets are the user's. Say exactly what to run and wait.
- **Keep the project plugin in a git repository the user owns.** It holds the
  board's lane settings, so the user must be able to find, review and back it
  up. Ask where it goes; never put it under an application-data or cache
  directory, and never leave it untracked.
- **Verify after-merge steps before you hand them over.** Any command you give
  the user to run after a PR or a merge (`git switch`, `git pull`, a cleanup)
  must be proven safe in this repository first: check what it would overwrite
  or delete, local files git does not track included. A branch switch or a
  pull can overwrite or delete a local file the two sides track differently
  (a local `.mcp.json`, for one).
- **Never say "done" on your own word.** Done means step 7 is green, or every
  remaining refusal is named with its fix.
- **Report the outcome, not the mechanism.** The last thing you tell the user
  is whether a task can run end to end on this board, or what stops it and who
  owes the fix. "Services active" or "pollers ok" does not answer that.
- **Report doctor verbatim.** Show each row's `detail` and `fix` as the engine
  wrote them.

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

## Before you start: one settings file

Your shell may not keep variables between commands, so keep them in a file and
start every command block with `. ~/.wf-setup.env`. It holds no secrets. Ask
the user for the values you cannot detect. `MODEL` and `EFFORT` are empty on
purpose: they decide what every task costs, so they are the user's answer,
never your pick and never another board's values. The one exception is a
profile the user hands you (step 4): its `toolkit.config.yaml` is then the
answers file, and these two keys are not used.

```bash
cat > ~/.wf-setup.env <<'EOF'
# Where the product is distributed (read access is required while it is private)
ENGINE_REPO=gnarlysoft-ai/workflow-engine
PLUGINS_REPO=gnarlysoft-ai/workflow-engine-plugins
STORE_REPO=gnarlysoft-ai/workflow-engine-integrations
# Release channel: the one your vendor gave you, else the product's beta channel
CHANNEL=desktop-beta
# The repository the board works on, and the board's name (= the folder's name)
REPO_DIR="$HOME/code/myproject"
BOARD=myproject
# Where the shared lanes and this board's project plugin live: a folder of the
# user's (ask), never an application-data or cache directory
PLUGINS_DIR="$HOME/wf-plugins"
# The board's dashboard port on this machine (one port per board)
PORT=8787
# The model and the reasoning effort the lanes pass to the agent CLI (Claude
# Code: an alias such as sonnet or opus, a level such as medium or high).
# Ask the user, then fill both in. Step 3c stops while either is empty.
MODEL=
EFFORT=
export PATH="$HOME/.local/bin:$PATH"
EOF
```

`BOARD` must be the repository folder's name, exactly: `wf init` records it as
the board's `repo_name`, and the service names and
`/etc/workflow-engine/projects/<BOARD>.env` are derived from it. Use a folder
name of letters, digits, `-` and `_`.

## Step 1. Detect the machine

```bash
. ~/.wf-setup.env
uname -s; uname -m
for t in python3 git gh uv jq curl node npm claude codex gemini; do printf '%-8s ' "$t"; command -v "$t" || echo MISSING; done
python3 -c 'import sys, yaml; print(sys.version.split()[0], "yaml ok")'
df -h "$HOME"
command -v wf && wf --version && wf host --json
```

What the engine needs on `PATH`:

| Tool | Why |
|---|---|
| `python3` >= 3.10 that can `import yaml` | every shipped hook runs on the host's `python3`, not the engine's own Python |
| `git`, `gh`, `uv`, `jq`, `curl` | install, updates, the extension store |
| `node`, `npm` | three shared lanes declare them in `requires.tools` |
| the agent CLI the lanes run on | see below |

The `df` line says how full the disk is. Above 90%, or before any install that
takes more than about 500 MB (a large `node_modules` does), stop and ask.

Install what is missing (ask first; these need `sudo`):

- **Debian / Ubuntu**:
  ```bash
  sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git jq curl python3-yaml nodejs npm
  # GitHub CLI, from GitHub's own apt repository (https://github.com/cli/cli/blob/trunk/docs/install_linux.md)
  sudo mkdir -p -m 755 /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
  sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  sudo apt-get update && sudo apt-get install -y gh
  # uv (no sudo; installs to ~/.local/bin)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Other Linux**: the same packages through its package manager. Amazon
  Linux 2023 and RHEL 9 ship `python3` 3.9, which the hooks cannot run on:
  install 3.11 or newer with PyYAML and make it the `python3` on `PATH`.
- **macOS**: `xcode-select --install` (git), then `brew install gh uv jq node`.
  Apple's own `python3` is 3.9, too old for the hooks: install a newer one
  (`brew install python`, or the python.org installer) so it is the first
  `python3` on `PATH`, then `python3 -m pip install --user pyyaml` (Homebrew's
  Python also needs `--break-system-packages` for a user install). The macOS
  steps of this skill have not yet been proven on a fresh Mac; report anything
  that does not match.

**The agent CLI.** The shared lanes pin a backend per step. Once step 3 has
fetched them, `grep -hoE '^\s+backend: [a-z]+' "$PLUGINS_DIR"/wf-toolkit/reference/workflows/*.yaml | sort | uniq -c`
says which. Today that is Claude Code
(`curl -fsSL https://claude.ai/install.sh | bash`; see its docs if that
fails). Tell the user which CLI the lanes need and install it on their yes;
signing in is the user's, in step 5. If you are
Claude Code yourself, running on this machine as this user, it is already
installed and signed in: `claude auth status` confirms it.

**Verify**: every tool above prints a path, and the python line prints a
version >= 3.10 and `yaml ok`.

## Step 2. Install the engine

### 2a. GitHub access (user step)

The engine, its shared lanes and its extension store are private GitHub
repositories while the product is in beta. This machine needs a GitHub account
with read access to all three.

Ask the user to run `gh auth login` in their own terminal on this machine
(browser or device code), then:

```bash
. ~/.wf-setup.env
gh auth status
for r in "$ENGINE_REPO" "$PLUGINS_REPO" "$STORE_REPO"; do gh api "repos/$r" --jq .full_name; done
gh auth setup-git   # plain git can now clone the private extension store
```

**Verify**: three repository names print. **If one is `Not Found`**, the account
has no access: stop and tell the user to ask their Workflow Engine contact to
grant their GitHub account read access to those three repositories. There is
no public download yet, so there is no way past this step without it.

### 2b. Pick the version

```bash
. ~/.wf-setup.env
VERSION=$(gh api "repos/$ENGINE_REPO/contents/deploy/channels/$CHANNEL.json?ref=main" \
  -H "Accept: application/vnd.github.raw" | jq -r .version) && echo "$VERSION"
```

**Verify**: a version such as `1.2.75`. If the channel is `Not Found`, ask the
user which channel to use; do not guess another customer's channel.

### 2c. Install (Linux)

The engine installs as the user who runs the board (the one whose home holds
the agent CLI's sign-in), never as root.

```bash
. ~/.wf-setup.env
VERSION=$(gh api "repos/$ENGINE_REPO/contents/deploy/channels/$CHANNEL.json?ref=main" -H "Accept: application/vnd.github.raw" | jq -r .version)
d=$(mktemp -d)
gh release download "v$VERSION" --repo "$ENGINE_REPO" --pattern '*.whl' --pattern '*.whl.sha256' --dir "$d"
(cd "$d" && sha256sum -c -- *.whl.sha256)
uv tool install --python '>=3.12' --with fastapi --with 'uvicorn[standard]' --with python-multipart "$d"/workflow_engine-"$VERSION"-py3-none-any.whl
wf --version
```

Then stage the units, the updater and `/etc/workflow-engine` with the engine's
own installer (it uses `sudo`; ask first):

```bash
. ~/.wf-setup.env
wf setup extract ~/wf-ops
bash ~/wf-ops/deploy/bootstrap.sh
# Record the channel in the box config. Rewrite in place: the file must stay
# owned by you (the updater reads it as you), and /etc/workflow-engine is not
# writable by you, so `sed -i` cannot create its temp file there.
python3 - "$CHANNEL" "$ENGINE_REPO" <<'PY'
import re, sys
p = "/etc/workflow-engine/wf.env"
s = open(p).read()
s = re.sub(r"(?m)^WF_CHANNEL=.*$", "WF_CHANNEL=" + sys.argv[1], s)
s = re.sub(r"(?m)^WF_REPO=.*$", "WF_REPO=" + sys.argv[2], s)
open(p, "w").write(s)
# Read the two values back by key name. This file can hold tokens, so its
# lines are never put through a text filter.
for line in open(p).read().splitlines():
    if line.split("=", 1)[0] in ("WF_CHANNEL", "WF_REPO"):
        print(line)
PY
ls -l /etc/workflow-engine/wf.env
```

The updater timer is turned on in step 6, after the board runs.

**Verify**: `wf --version` prints `$VERSION`; `wf.env` shows both values and is
owned by this user, mode `-rw-r-----`.

### 2c. Install (macOS)

The engine's macOS updater installs the channel's version when no `wf` exists.
It is not shipped outside the wheel, so fetch it and run it once:

```bash
. ~/.wf-setup.env
mkdir -p ~/wf-ops
gh api "repos/$ENGINE_REPO/contents/deploy/wf-update-mac.sh?ref=main" -H "Accept: application/vnd.github.raw" > ~/wf-ops/wf-update-mac.sh
chmod 0755 ~/wf-ops/wf-update-mac.sh
WF_REPO="$ENGINE_REPO" WF_CHANNEL="$CHANNEL" /bin/bash ~/wf-ops/wf-update-mac.sh
wf --version
```

Do not judge it by its exit code (it exits 0 when it cannot read the channel);
judge it by `wf --version`. The updater acts on every board on the machine,
which is why the rules forbid running it where boards already exist.

The same script installs itself as an hourly LaunchAgent, which keeps the
engine current after this chat ends. Ask first: say that it runs every hour and
updates the engine for every board on this Mac, and install it only on the
user's yes. Without it the engine stays at this version until someone runs the
command above again.

```bash
. ~/.wf-setup.env
WF_REPO="$ENGINE_REPO" WF_CHANNEL="$CHANNEL" /bin/bash ~/wf-ops/wf-update-mac.sh --install
```

**Verify**: `wf --version` prints `$VERSION`; the log is
`~/Library/Logs/wf-update/update.log`.

## Step 3. Create the board

### 3a. The repository

Ask the user which repository the board works on. Clone it if it is not on the
machine yet (`gh repo clone <owner>/<name> "$REPO_DIR"`). It must be a git
repository with an `origin` remote, a clean working tree, and a git identity
for this user:

```bash
. ~/.wf-setup.env
git -C "$REPO_DIR" remote -v && git -C "$REPO_DIR" status --porcelain
git config --global user.name || echo "MISSING: ask the user for their name"
git config --global user.email || echo "MISSING: ask the user for their email"
```

Set a missing identity with the user's answers (`git config --global user.name "…"`,
`git config --global user.email "…"`). Ask for the repository's test command
(for example `npm test`, `pytest`, `make test`); it goes in the answers below.

Read the repository's default branch; it goes in the answers too (the lanes
assume `main` otherwise, and doctor refuses the mismatch):

```bash
. ~/.wf-setup.env
git -C "$REPO_DIR" remote set-head origin --auto >/dev/null
git -C "$REPO_DIR" symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##'
```

The board pushes branches to `origin` with this user's git credentials (the
`gh` sign-in), so that account needs write access to the repository. Doctor's
`push_access` row proves it in step 7; for a repository the user cannot push
to, use their fork.

### 3b. The shared lanes (wf-toolkit)

```bash
. ~/.wf-setup.env
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

### 3c. The project plugin, from an answers file

Every required key of the toolkit's `config.schema.yaml` must have a one-line
value (a two-line value breaks assembly). These starters are generic; replace
the test command and keep the rest unless the user wants otherwise. With a
profile from another machine (step 4), use its `toolkit.config.yaml` as the
answers file instead.

```bash
. ~/.wf-setup.env
BASE=$(git -C "$REPO_DIR" symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##')
python3 - "$PLUGINS_DIR/$BOARD.answers.json" "$BOARD" "$MODEL" "npm test" "$BASE" "$EFFORT" <<'PY' &&
import json, sys
path, repo, model, test, base, effort = (arg.strip() for arg in sys.argv[1:7])
if not model or not effort:
    sys.exit("MODEL or EFFORT is empty in ~/.wf-setup.env: ask the user, set both, run this block again")
a = {
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
  "effort_default": effort,
  "web_findings_repo": repo,
  "test_gate_command": test,
  "base_branch": base,
}
for k in ("model_default", "model_design", "model_minor_develop_reproduce", "model_minor_develop_fix",
          "model_minor_develop_review", "model_minor_develop_refix", "model_feature", "model_publish"):
    a[k] = model
json.dump(a, open(path, "w"), indent=2)   # JSON is YAML: --answers reads it with yaml.safe_load
print("wrote", path)
PY
cd "$PLUGINS_DIR" &&
wf plugin new "$BOARD" --plugins-dir "$PLUGINS_DIR" --answers "$PLUGINS_DIR/$BOARD.answers.json" &&
git -C "$PLUGINS_DIR/$BOARD" init -q -b main && git -C "$PLUGINS_DIR/$BOARD" add -A \
  && git -C "$PLUGINS_DIR/$BOARD" commit -qm "Scaffold $BOARD" &&
wf assemble "$PLUGINS_DIR/$BOARD" --plugins-dir "$PLUGINS_DIR"
```

(Replace `"npm test"` with the user's command before running.) Each command
runs only if the one before it succeeded, so a refused answers file scaffolds
nothing, even when an answers file from an earlier attempt is still there.

If `wf assemble` names a missing key, read that key's description in
`$PLUGINS_DIR/wf-toolkit/config.schema.yaml`, add a one-line value to
`$PLUGINS_DIR/$BOARD/toolkit.config.yaml`, commit, and assemble again.

The project plugin is now a git repository at `$PLUGINS_DIR/$BOARD`. It is the
user's: tell them where it is, and offer to add a remote of theirs and push it.
Pushing is their call.

**Verify**: `Assembly OK … workflows validate.`

### 3d. The board and its three plugins

```bash
. ~/.wf-setup.env
cd "$HOME"
wf init --repo "$REPO_DIR"
wf plugin install "$PLUGINS_DIR/wf-toolkit" --repo "$REPO_DIR"
wf plugin install 'github@^1' --repo "$REPO_DIR"     # the lanes call its actions; the consumer refuses to install without it
wf plugin install "$PLUGINS_DIR/$BOARD" --repo "$REPO_DIR"
wf plugin status --repo "$REPO_DIR" | tail -3
wf workflow check -w "$REPO_DIR/.workflow"
```

The board lives in `$REPO_DIR/.workflow`; the install also writes `.claude/`
and `.agents/`. Keep all three out of git without touching the repository's
tracked files:

```bash
. ~/.wf-setup.env
for p in .workflow/ .claude/ .agents/; do
  git -C "$REPO_DIR" status --porcelain=v1 | grep -qxF "?? $p" && echo "$p" >> "$REPO_DIR/.git/info/exclude"
done
git -C "$REPO_DIR" status --porcelain
```

**Verify**: `All plugins current.`, every workflow `OK`, `git status --porcelain`
prints nothing, and `jq -r .repo_name "$REPO_DIR/.workflow/workspace.json"`
prints `$BOARD`. (If `.claude/` was already tracked and the install changed a
file in it, tell the user which files changed and let them read the diff in
their own terminal: it can hold tokens, so it is never printed here. Never
commit or stash it for them.)

## Step 4. Optional: copy settings from another machine (a profile)

A profile carries a board's setup **without secrets**: the plugin set with
versions and sources, which extensions are on or off, and the non-secret
settings. It never carries `.env`, `.env.integrations`, `users.json`, tasks or
pauses.

If the engine has the command (`wf profile --help >/dev/null 2>&1 && echo yes`;
an engine without it exits 2), use it:

```bash
. ~/.wf-setup.env
wf profile apply <profile-file> --repo "$REPO_DIR"
```

Until that command ships, do the same by hand from files the user copies off
the other machine (`<ws>` is its `.workflow` directory):

| From the other machine | Apply here |
|---|---|
| `wf plugin status --repo <repo>` (versions) | step 3b with `TAG=wf-toolkit-v<version>`; step 3d with `<extension>@<version>` |
| its project plugin's `toolkit.config.yaml` | the answers file in step 3c |
| `<ws>/settings.json` | each key with `PUT /api/settings` once the dashboard runs (step 6) |
| `<ws>/integration-overrides.json` | `wf integration enable <name> -w "$REPO_DIR/.workflow"` / `disable` |
| each extension's non-secret values: `curl -s localhost:<port>/api/integrations/<name>/config`, its `values` | `POST /api/integrations/<name>/config` here (step 6) |

Never ask for, copy or accept the other machine's `.env`, `.env.integrations`
or `users.json`: those hold its secrets. Secrets are re-entered here in step 5.

## Step 5. Secrets and sign-ins (user steps)

Doctor names every required key the installed plugins declare that no reader
can see. Run it now to get the list (it will also refuse things step 6 fixes):

```bash
. ~/.wf-setup.env
wf doctor --onboarding --json -w "$REPO_DIR/.workflow" --dashboard-port "$PORT" \
  | python3 -c 'import json,sys; [print(f["subject"], "->", f["fix"]) for f in json.load(sys.stdin)["findings"] if f["code"]=="required_env" and f["severity"]=="refuse"]'
```

For an extension's key, doctor's `fix` says `set KEY in <ws>/.env`; write it
through the extension's config endpoint instead (step 6). That endpoint writes
`<ws>/.env.integrations`, which doctor and the pollers read as well. For each
key, decide which kind it is and where it goes:

| Kind | How to tell | Who writes it, where |
|---|---|---|
| An extension setting that is not secret (`GITHUB_REPOS`, labels, switches) | the extension's config schema (`GET /api/integrations/<name>/config`) types it as anything but `secret` | you, in step 6, through the dashboard's config endpoint |
| An extension secret | that schema types it `secret` | the user, in the dashboard's Extensions page (a write-only field), through the tunnel in "Reach the dashboard" |
| Any other secret (a token, password or key a workflow declares) | the name ends in `TOKEN`, `SECRET`, `PASSWORD` or `KEY`, or the user says so | the user, with the command below, into the file doctor's `fix` names |

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

- signs in to the agent CLI as this user: `claude auth login` (or start
  `claude` and use `/login`); for another CLI, its own login command;
- keeps `gh` signed in (done in step 2a). The loop uses that sign-in; a
  `GH_TOKEN` is needed only if doctor asks for one.

**Verify**: `claude auth status` (or the other CLI's status command) reports
signed in. The secret rows are re-checked in step 7.

## Step 6. Start the board's services

The loop (dispatch plus the extension pollers) and the dashboard run as
services whose entry point is the `wf` binary itself. Nothing is started
before this step.

**Ask first.** Tell the user what this step leaves running after this chat
ends, and start it only on their yes:

- the loop, which dispatches armed tasks and runs the extension pollers;
- the dashboard, which starts writable: it saves settings and answers
  checkpoints, and the configuration below posts to it. Say both sides. The
  engine's own guidance for a machine that runs the loop is a read-only
  dashboard (`WF_DASHBOARD_READONLY=1`), so that the loop is the only writer
  of task files; its deploy guide says a writable dashboard beside the loop
  "double-dispatches". A read-only dashboard refuses every change made from
  it, approving a checkpoint included; those then go through the CLI
  (`wf approve`). Which one the board keeps is the user's call, and "Read-only
  dashboard" at the end of this step applies it;
- the engine's self-updater: on Linux its timer is turned on in this step; on
  macOS it was installed in step 2c, if the user said yes there.

### Linux (systemd)

`bootstrap.sh` already installed `wf-loop@.service` and `wf-dashboard@.service`.
Each board gets one env file named after it. `wf setup schedule -w
"$REPO_DIR/.workflow"` prints the loop's recipe; this is that recipe plus the
dashboard's port:

```bash
. ~/.wf-setup.env
SVC_PATH=$(wf setup schedule -w "$REPO_DIR/.workflow" | sed -n "s/^  '.*' '\(.*\)' > \"\$tmp\"$/\1/p")
echo "PATH for the services: $SVC_PATH"
umask 077; tmp="$(mktemp)"
printf 'WF_WORKSPACE=%s\nWF_PORT=%s\nWF_INTERVAL=30\nWF_MAX_CYCLES=0\nPATH=%s\n' \
  "$REPO_DIR/.workflow" "$PORT" "$SVC_PATH" > "$tmp"
[ -e "/etc/workflow-engine/projects/$BOARD.env" ] \
  || sudo install -m 0600 -o "$(id -un)" -g "$(id -gn)" "$tmp" "/etc/workflow-engine/projects/$BOARD.env"
rm -f "$tmp"
sudo systemctl enable --now "wf-dashboard@$BOARD" "wf-loop@$BOARD"
sudo systemctl enable --now wf-update.timer      # engine self-update, last
```

If `SVC_PATH` came out empty, read the `PATH=` value off the `printf` line of
`wf setup schedule`'s output by hand. It must contain the directories of
`wf`, the agent CLI, `node` and `git`.

**Verify**:

```bash
. ~/.wf-setup.env
systemctl is-active "wf-dashboard@$BOARD" "wf-loop@$BOARD" wf-update.timer
curl -s "localhost:$PORT/api/version" | jq -r .version
sleep 40; ls "$REPO_DIR/.workflow/.heartbeat.json" && ls "$REPO_DIR/.workflow/integrations/"
```

`journalctl -u "wf-loop@$BOARD" -n 50` says why if one is not active.

### macOS (LaunchAgents)

First check that no other board already uses these labels (two repositories
with the same folder name would collide):

```bash
. ~/.wf-setup.env
ls ~/Library/LaunchAgents/local.wf.loop.$BOARD.plist ~/Library/LaunchAgents/local.wf.dashboard.$BOARD.plist 2>&1
```

Both must say `No such file`. If either exists, stop and tell the user: another
board on this Mac has a repository folder of the same name, and the engine
derives the loop's label from that name.

```bash
. ~/.wf-setup.env
LABEL="local.wf.loop.$BOARD"
wf setup schedule -w "$REPO_DIR/.workflow" --platform darwin \
  | awk '/^<\?xml/{p=1} p{print} /^<\/plist>/{exit}' > ~/Library/LaunchAgents/$LABEL.plist
plutil -lint ~/Library/LaunchAgents/$LABEL.plist
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/$LABEL.plist
# The dashboard: fill the engine's own template, from the installed wheel
wf setup extract ~/wf-ops >/dev/null 2>&1 || true   # refuses (harmlessly) when the files already exist
DLABEL="local.wf.dashboard.$BOARD"
svc_path="$(dirname "$(command -v wf)"):$(dirname "$(command -v git)"):$(dirname "$(command -v claude)"):$(dirname "$(command -v node)"):/usr/bin:/bin:/usr/sbin:/sbin"
python3 - ~/wf-ops/deploy/wf-dashboard.plist ~/Library/LaunchAgents/$DLABEL.plist \
  __WF_LABEL__ "$DLABEL" __WF_BIN_DIR__ "$(dirname "$(command -v wf)")" __WF_WORKSPACE__ "$REPO_DIR/.workflow" \
  __WF_HOME__ "$HOME" __WF_PATH__ "$svc_path" "<string>8787</string>" "<string>$PORT</string>" <<'PY'
import sys
src, dst, *pairs = sys.argv[1:]
t = open(src).read()
for a, b in zip(pairs[::2], pairs[1::2]):
    t = t.replace(a, b)
open(dst, "w").write(t)
PY
plutil -lint ~/Library/LaunchAgents/$DLABEL.plist
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/$DLABEL.plist
```

**Verify**: `launchctl print "gui/$(id -u)/$LABEL" | grep state` says running,
`curl -s localhost:$PORT/api/version` answers, and after a minute
`$REPO_DIR/.workflow/.heartbeat.json` exists.

### Configure the GitHub extension (both platforms)

Through the dashboard's own endpoint, the same one its Extensions form posts
to. Read the current values, then post them back with the user's choices.
Ask the user: which repositories (`owner/name`, comma-separated) and whether new
GitHub issues with a label should become tasks (default **no**):

```bash
. ~/.wf-setup.env
curl -s "localhost:$PORT/api/integrations/github/config" | jq '.values'
curl -s -X POST -H 'Content-Type: application/json' "localhost:$PORT/api/integrations/github/config" -d '{
  "values": {"GITHUB_REPOS": "owner/name", "GITHUB_INTAKE_ENABLED": false, "GITHUB_INTAKE_LABEL": "ai-ready",
             "GITHUB_CLAIMED_LABEL": "wf-seeded", "GITHUB_REINTAKE_LABEL": "re-intake",
             "GITHUB_BRANCH_PREFIX": "feat", "GITHUB_MAX_SEEDS_PER_TICK": 5, "GITHUB_CLOSE_ON_DONE": true}}'; echo
```

Post every required key, including those already showing a default: the
installer records them as required, and doctor refuses a required key that is
only a default. **Verify**: the response lists them under `written`.

### Safe defaults

Live-behaviour switches stay at their safe values unless the user rules
otherwise: auto-merge off (the default), and testing after merge off when there
is no test environment to test against. The engine's default for the latter is
on, which parks every approved task waiting for one:

```bash
. ~/.wf-setup.env
curl -s -X PUT -H 'Content-Type: application/json' "localhost:$PORT/api/settings" -d '{"key": "WF_QA_APPLICABLE", "value": false}' | jq -r '.key, .value'
```

The loop dispatches only work someone **armed** (from the dashboard, or
`wf cycle arm`); a new board does nothing until then. That is intended.

### Agent harness

Doctor's `harness` rows name plugins and skills the lanes require of the agent
CLI. Apply each row's `fix` as written. For Claude Code on a fresh machine the
official marketplace must be added first:

```bash
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin install superpowers@claude-plugins-official   # example: what the harness row names
. ~/.wf-setup.env; touch "$REPO_DIR/.workflow/.harness-check-request"   # the loop re-checks within seconds
until [ ! -e "$REPO_DIR/.workflow/.harness-check-request" ]; do sleep 2; done   # gone = re-checked
```

### Read-only dashboard (only if the user chose it)

Do this last. The two configuration blocks above post to the dashboard, and
the user types an extension secret into its Extensions page (step 5); a
read-only dashboard refuses both.

On Linux, add the key to the board's env file and restart the unit, which
reads that file on every start. The restart uses `sudo`: show it first.

```bash
. ~/.wf-setup.env
printf 'WF_DASHBOARD_READONLY=1\n' >> "/etc/workflow-engine/projects/$BOARD.env"
sudo systemctl restart "wf-dashboard@$BOARD"
```

On macOS, set the key in the dashboard's plist, then unload the job and load
it again. A restart (`launchctl kickstart -k`) is not enough: launchd reads
the plist when it loads the job, so a restarted dashboard keeps its old
environment and stays writable.

```bash
. ~/.wf-setup.env
DLABEL="local.wf.dashboard.$BOARD"
plutil -replace EnvironmentVariables.WF_DASHBOARD_READONLY -string 1 ~/Library/LaunchAgents/$DLABEL.plist
launchctl bootout "gui/$(id -u)/$DLABEL"
while launchctl print "gui/$(id -u)/$DLABEL" >/dev/null 2>&1; do sleep 1; done   # bootout returns before the job is gone
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/$DLABEL.plist
```

**Verify**: `curl -s "localhost:$PORT/api/settings" | jq .readonly` prints
`true`.

## Step 7. Prove it

```bash
. ~/.wf-setup.env
wf doctor --onboarding --json -w "$REPO_DIR/.workflow" --dashboard-port "$PORT" > ~/wf-doctor.json; echo "exit=$?"
python3 - ~/wf-doctor.json <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
order = {"refuse": 0, "warn": 1, "ok": 2}
for f in sorted(d["findings"], key=lambda f: order.get(f["severity"], 3)):
    if f["severity"] == "ok":
        continue
    print(f'{f["severity"].upper():6} {f["code"]} {f.get("subject") or ""}\n       {f["detail"]}\n   fix: {f["fix"]}\n')
print("ok rows:", ", ".join(f["code"] for f in d["findings"] if f["severity"] == "ok"))
print("VERDICT:", "GREEN" if d["ok"] else "NOT YET")
PY
```

Show the user every row. Fix what you can (each row's `fix` is the engine's own
instruction), wait for user steps, and run it again. A second green run after
the loop's next cycle is the real sign-off.

**You are done only when** `"ok": true` (exit 0), **or** every remaining
refusal is listed with its fix and who owes it. Known items:

- `agent_cli` refuses until the user has signed in to the agent CLI as this
  user (step 5).
- On macOS, `tools: flock` is refused on every Mac because doctor matches the
  word in the toolkit's portable lock helper, a known engine issue. Until a
  release fixes it, report that one row as known, not as a setup failure.
- `push_access` refuses when the `gh` account cannot push to `origin`
  (step 3a). That is the user's to grant; the board cannot publish without it.
- `base_branch` refuses when `base_branch` in the project plugin's
  `toolkit.config.yaml` differs from the repository's default branch: set it,
  commit, then `wf assemble` and `wf plugin install "$PLUGINS_DIR/$BOARD" --repo "$REPO_DIR"`
  again. It warns when the repository has no `origin/HEAD`
  (`git -C "$REPO_DIR" remote set-head origin --auto`).

**Then say what it means**, in one sentence: a task can run end to end on this
board (armed, dispatched by the loop, worked by the agent CLI, published), or
it cannot yet and what stops it. Doctor's rows are the evidence for that
sentence; a list of healthy mechanisms is not the sentence. No task has run
at this point, so say that as well: the first task the user arms is the proof.

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

| What | Where |
|---|---|
| Engine | `~/.local/bin/wf` (Linux: moved under `~/.local/share/wf/versions/` by the first update) |
| Box config (Linux) | `/etc/workflow-engine/wf.env`, `/etc/workflow-engine/projects/<BOARD>.env` |
| Board | `$REPO_DIR/.workflow` (`settings.json`, `.env`, `.env.integrations`, `plugins.json`) |
| Shared lanes and project plugin | `$PLUGINS_DIR/wf-toolkit`, `$PLUGINS_DIR/<BOARD>` (a git repo the user owns) |
| Logs | `journalctl -u wf-loop@<BOARD>`, `-u wf-dashboard@<BOARD>`, `-u wf-update`; macOS `~/Library/Logs/wf-update/` |
