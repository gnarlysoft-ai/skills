---
name: workflow-engine-author
license: MIT
description: >
  Build or change the workflows a Workflow Engine board runs: customise the
  board's project plugin on top of the shared lanes (wf-toolkit), change a
  step's instructions, model or reviewers, override a role prompt or a hook,
  set config values, add a custom workflow (with or without wf-toolkit),
  validate it with `wf assemble` and `wf workflow check`, and install it. Use
  when someone asks to change how the agents behave on a board, add a step,
  gate or review, tune prompts or models, or create a new workflow.
---

# Change how the agents work on a board

You are changing what a Workflow Engine board runs. You work in the board's
**project plugin**, never in the files the board runs from, and you finish on
the engine's own proofs (step 5), never on your own judgement. Work through the
steps in order.

Beside this file:

- [reference/workflow-yaml.md](reference/workflow-yaml.md): every workflow, state and step field, prerequisites (`requires`) and hooks.
- [reference/patterns.md](reference/patterns.md): the four composition patterns.
- [reference/toolkit-consumer.md](reference/toolkit-consumer.md): a project plugin on top of wf-toolkit, in depth (levers, expansion, config and secrets, QA setup).

To run or debug a board, use the `learn-workflow-engine` skill. To install the
engine or create a board, use `workflow-engine-setup`.

**Before you rely on anything here:** this skill is written for engine 1.2.93
or later (`wf --version`). `wf <command> --help` is the authority on commands
and flags; if one named here is missing, say so and use what `--help` offers.

## Rules

- **Never edit wf-toolkit or the engine.** Every board shares them. A value you
  cannot set from the project plugin is a missing config key: tell the user
  which key the toolkit would need, and do not fork or patch the toolkit.
- **Never edit installed files** under `<repo>/.workflow/`, `<repo>/.claude/`,
  `<repo>/.agents/`, `<repo>/.gemini/` or `<repo>/.codex/`. `wf plugin install`
  writes them and the next install overwrites them.
- **Work in the project plugin, which lives in a git repository, and commit each
  change there.** The install records the commit it installed.
- **Skills get literal values.** `{{wf.<key>}}` is expanded in workflows,
  prompts and agents only; in a `SKILL.md` it reaches the agent as text.
- **Never commit a secret, and never ask for one in the chat.** Config names
  an environment variable; the user stores its value with
  `wf secret set <KEY> -w <ws>`, which reads it without echoing.
- **Never change a live-behaviour switch** (auto-merge, `autopilot`, arming,
  pausing the board) unless the user asked for exactly that change.
- **Install only after the user approves the diff.** On a board with work in
  flight, install inside `wf maintenance run`. Never pass `--force`.
- **Keep it generic** in anything shared or published: no client name, host
  name, internal link or account value.
- **Before you create a repository** (`gh repo create`), ask the user for its
  name, owner and visibility. Private is the default.
- **Recommend only what this board can install:** lanes from
  `wf workflow catalog --intake --json -w <ws>`, extensions from
  `wf integration search -w <ws>`. If nothing listed fits, say so.

## 1. Find the board and its plugins, and take a baseline

`<repo>` is the repository the board works on and `<ws>` its workspace,
usually `<repo>/.workflow`.

```bash
wf plugin status --repo <repo> --no-fetch
python3 - <ws>/plugins.json <<'EOF'
import json, os, sys
path = sys.argv[1]
plugins = json.load(open(path))["plugins"] if os.path.exists(path) else {}
for name, p in plugins.items():
    src = p.get("source") or ""
    tag = "PROJECT PLUGIN" if os.path.isfile(os.path.join(src, "toolkit.config.yaml")) else ""
    print(name, p.get("version"), src, tag)
print(len(plugins), "plugin(s) installed")
EOF
```

The project plugin is the one whose source folder holds `toolkit.config.yaml`.
If there is none, or more than one, ask the user which plugin to change. If the
board has no plugin at all, or none of its own, go to step 7. Below, `<plugin>` is the project
plugin's folder and `<dir>` the folder that holds it and wf-toolkit.

Check its repository:

```bash
git -C <plugin> rev-parse --show-toplevel   # the plugin, or the user's plugins repository
git -C <plugin> status --short -- .         # must print nothing
```

If it is not in a git repository, ask before you run `git init` there. If it
has uncommitted changes, they are not yours: ask the user what to do with them.
If the plugin lives in the user's own plugins repository, work on a new branch
there.

Take the baseline before any edit:

```bash
mktemp -d
```

It prints a folder; below it is `<base>`. Your shell may not keep variables
between calls, so write the folder out wherever `<base>` appears.

```bash
wf assemble <plugin> --plugins-dir <dir>
wf doctor --json -w <ws> > <base>/doctor.json
wf doctor --onboarding --json -w <ws> > <base>/doctor-onboarding.json
```

`wf assemble` must print `Assembly OK`. If it does not, the board was broken
before you started: show the user the output and stop. `wf doctor` exits 1
when it refuses something; that is fine here, because these files are what
step 5 compares against. `--onboarding` also makes one short test call through
the board's agent CLI.

## 2. The model

- **Three layers.** The engine runs workflows. wf-toolkit is the shared
  mechanism: reference workflows, role prompts, partials, hooks and the config
  schema. The project plugin holds this board's values: its workflows,
  `toolkit.config.yaml`, prompt and hook overrides, and project skills.
- **Seed and source.** `wf plugin new` copied the toolkit's reference
  workflows into the project plugin once. They are the project's files now and
  do not follow later toolkit releases. Role prompts, partials and hooks the
  project does not override are read from the toolkit at every install, so
  they do follow it.
- **Family contracts.** While a workflow keeps a toolkit family's `name:`
  (`develop`, `minor-develop`, and so on), the toolkit's contract for that
  family applies: required states, transitions and human gates, enforced by
  `wf assemble`. Rename the workflow and no contract applies.
- **What install writes.** `wf plugin install` expands the plugin into
  `<ws>/workflows`, `<ws>/prompts`, `<ws>/hooks` and `<ws>/bin`. It copies its
  skills into `<repo>/.claude/skills/` and `<repo>/.agents/skills/`, and its
  agents into `<repo>/.claude/agents/`, `<repo>/.gemini/agents/` and
  `<repo>/.codex/agents/` (as `.toml` for Codex). Those are outputs, never
  inputs.

## 3. Choose the smallest lever

Take the first lever that does the job:

| Lever | Where | For |
|---|---|---|
| L1 | a step in `<plugin>/workflows/<name>.yaml` | `description:`, `model:`, `backend:`, `rubric:`, `guard:`, `condition:`, `on_fail:`; adding, removing or rewiring steps and states |
| L2 | a value in `<plugin>/toolkit.config.yaml` | text or a setting that a toolkit prompt, partial or workflow reads as `{{wf.<key>}}`; keys of your own are allowed |
| L3 | `<plugin>/prompts/<agent>.md` | a role prompt, extended or replaced |
| L4 | `<plugin>/hooks/<same-name>.py` | replacing one toolkit hook |
| L5 | `<plugin>/workflows/<new-name>.yaml` | a new workflow |
| skill | `<plugin>/skills/project-<topic>/SKILL.md` | project knowledge an agent loads by name |

**L1.** A step's `description:` goes straight into the agent's prompt, and
most behaviour changes are a description edit. Every field is in
[reference/workflow-yaml.md](reference/workflow-yaml.md). Every agent a step
names needs a prompt, the plugin's or the toolkit's, or `wf assemble` fails
naming the agent: `ls <dir>/wf-toolkit/prompts` lists the roles the toolkit
ships. To add a reviewer, add a step whose `agent:` is that role, rewire the
states around it, and keep each `transitions_to` true to where the step can
move the task.

**L2.** Read the keys from `<dir>/wf-toolkit/config.schema.yaml`, never from
memory: each entry under `vars:` has a `description`, and `required: true`
means the board must set it. A value used in the middle of a line (`model:
{{wf.model_default}}`) must be one line; a multi-line value belongs where the
reference sits alone in a YAML block.

**L3.** A prompt in the plugin replaces the toolkit's prompt for that role
entirely. To keep the toolkit's text and add to it:

```markdown
{{wf:include wf-toolkit/prompts/<role>.md}}

## Override for this project

- <the extra rule>
```

Leave the include out to replace the role prompt outright. A prompt says who
the agent is and its standing rules; what to do in one step belongs in that
step's `description:`.

**L4.** A hook in the plugin replaces the toolkit hook with the same file
name. Write it in Python, so it runs unchanged on macOS and Linux. It reads a
JSON context on stdin and may print one JSON object on stdout; `message` in
that object goes to the agent on a retry.

| Exit | Meaning |
|---|---|
| `0` | pass |
| `1` | fail: the step fails and its `on_fail` applies |
| `2` | not ready: the task waits and is asked again on the next dispatch |

A hook gets 30 seconds unless its entry sets `timeout_seconds`.

**L5.** Pick a shape from [reference/patterns.md](reference/patterns.md).
Declare every state; give every step `transitions_to` (`[]` for a step that
must not move the task); give each checkpoint `on_approve` and `on_reject`;
write a prompt for every agent it names. A name no toolkit family uses keeps
the workflow free of family contracts. A secret the workflow needs is declared
by name in its `env:` (empty value) and `requires.env`, and the user stores
the value with `wf secret set <KEY> -w <ws>`.

## 4. Expansion rules and traps

- Includes expand first, then variables. A `{{wf:include ...}}` inside a
  config value is never expanded: it reaches the agent as text. A partial may
  use `{{wf.<key>}}`.
- Only workflows, prompts and agents are expanded. Skills, hooks and `bin/`
  files are copied as they are.
- An unknown `{{wf.<key>}}` fails `wf assemble`, naming the key. Add the key
  to `toolkit.config.yaml`, never to the toolkit.
- An include path starts with a plugin name (`wf-toolkit/partials/...`) and is
  re-indented to its column, so a multi-line partial stays inside its YAML
  block.

## 5. Prove

Commit first:

```bash
git -C <plugin> add -A -- .
git -C <plugin> commit -m "<what changed and why>"
```

Then climb the ladder in order. A rung that fails stops you: fix it in the
plugin, commit, and start again from the first rung.

| Rung | Command | Passes when |
|---|---|---|
| Assembles | `wf assemble <plugin> --plugins-dir <dir>` | it prints `Assembly OK` (expansion, loading and family contracts all pass) |
| Changes only what you meant | the diff below | it shows only the files and lines you meant to change |
| Installs | step 6 | exit 0, naming the files it changed (never `NO FILE CHANGED` for an intended change) |
| Matches its source | `wf assemble --installed <repo>` | `Installed tree matches plugins.json.` |
| Loads | `wf workflow check -w <ws>` | every workflow is OK and none is `SHADOWED` |
| Box still healthy | the doctor comparison below | no refusal the baseline did not have |
| Behaves (optional) | one pilot task, offered to the user | `wf task show <id> -w <ws>` shows the new step ran |

**The diff, before you install:**

```bash
mktemp -d
```

It prints a folder; below it is `<out>`.

```bash
wf assemble <plugin> --plugins-dir <dir> --out <out>/assembled
(cd <out>/assembled && find . -type f) | while read -r f; do diff -uN "<ws>/$f" "<out>/assembled/$f"; done
```

`--out` writes only workflows, prompts and agents, so this diff never shows a
change to `hooks/`, `bin/` or `skills/`, or a deleted file, and it shows an
agent as wholly new (the board keeps agents under `<repo>/.claude/agents/`, not
`<ws>`). For those, show `git -C <plugin> show HEAD` as well.

Show it to the user and wait for their yes before step 6.

**The doctor comparison, after you install:**

```bash
wf doctor --json -w <ws> > <base>/doctor-after.json
wf doctor --onboarding --json -w <ws> > <base>/doctor-onboarding-after.json
python3 - <base> <<'EOF'
import json, os, sys
def refusals(name):
    data = json.load(open(os.path.join(sys.argv[1], name)))
    return {(f["code"], f["subject"]) for f in data["findings"] if f["severity"] == "refuse"}
new = (refusals("doctor-after.json") - refusals("doctor.json")) | (
    refusals("doctor-onboarding-after.json") - refusals("doctor-onboarding.json"))
for code, subject in sorted(new):
    print("NEW REFUSAL:", code, subject)
print("no new refusal" if not new else "new refusals: see above")
sys.exit(1 if new else 0)
EOF
```

The finish line is **no worse than before your change**. A refusal the
baseline already had is not yours to fix here: name it in the hand-back (the
`workflow-engine-setup` skill is what fixes a board's setup). A new refusal
stops you: show it, then fix it in the plugin, or revert your commit
(`git -C <plugin> revert --no-edit HEAD`) and install again.

**Behaves.** A changed step proves itself only when it runs. Offer the user
one pilot task and run it only if they say yes, because it spends a real agent
run: `wf task create --id <id> --title "<title>" --workflow <name> -w <ws>`,
then `wf task start <id> -w <ws>`, then `wf task show <id> -w <ws>` once the
loop has run it.

## 6. Install

Only after the user has approved the diff:

```bash
wf plugin install <plugin> --repo <repo>
```

- **It refuses because a step is running on the board:** install inside a
  maintenance window, which waits for running steps and holds new ones:
  `wf maintenance run -w <ws> --reason "plugin update" -- wf plugin install <plugin> --repo <repo>`.
  Never `--force`.
- **It names tasks parked in a state your change removed:** list each task and
  the `wf task transition <id> <state> -w <ws>` that would free it, and ask the
  user before you move any.
- **It refuses to overwrite an agent or skill it did not write** (the user's
  own): ask the user. `--adopt` backs theirs up and installs ours; `--skip`
  keeps theirs.
- **After a toolkit update:** `wf plugin install <dir>/wf-toolkit --repo <repo> --with-dependents`
  installs the toolkit and re-expands the project plugin against it.

Then finish the ladder: `wf assemble --installed <repo>`,
`wf workflow check -w <ws>`, and the doctor comparison.

## 7. Without the shared lanes

For a board with no plugin of its own, or a workflow that should not use
wf-toolkit. When the board has no plugin yet, `<dir>` does not exist: ask the
user where the plugins folder should live, and never put it inside `<repo>`.

```bash
wf plugin init <name> --output <dir>
git -C <dir>/<name> init
git -C <dir>/<name> add -A
git -C <dir>/<name> commit -m "Scaffold <name>"
```

`wf plugin init` makes no git repository, so make one and commit the scaffold
before you change anything. Then write each workflow in
`<dir>/<name>/workflows/<workflow>.yaml` (lever L5) and a
`<dir>/<name>/prompts/<agent>.md` for every agent it names. A plugin with no
`depends:` has no toolkit values to read, so keep its values literal. Take the
baseline of step 1 (the `wf doctor` files; `wf assemble` of the new plugin
proves the scaffold), and prove it with the same ladder, `--plugins-dir <dir>`.

## 8. Hand back

Give the user:

1. what changed, why, and which lever you used;
2. the diff: `git -C <plugin> show --stat HEAD` and the assembled diff from step 5;
3. every rung's output, verbatim;
4. what is still theirs to decide: the install if it is pending, a pilot
   task, a refusal the baseline already had, a toolkit key that is missing.

Never report a rung as green that you did not run. Report a red rung with its
fix and who owes it.
