---
name: learn-workflow-engine
description: Run, debug and extend a Workflow Engine board (the `wf` CLI) — a file-based orchestrator that runs AI coding CLIs (Claude Code, Codex, Gemini CLI) through YAML workflows. Teaches the mental model, the CLI, how to read a workflow, task files, hooks, plugins and extensions, the dashboard, and an ordered check for "why isn't this task moving?". Use at the start of a session where the user wants to operate, debug or extend a board on a machine that already has the engine. To write or change a board's workflows, prompts or project plugin, use the workflow-engine-author skill; to install the engine or create a first board, use the workflow-engine-setup skill. To connect another program or AI tool to a board, use the wfe-integrate skill.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch
---

# Workflow Engine — Operator's Guide

You are now equipped to work with the **Workflow Engine**: a file-based orchestrator that runs AI coding CLIs through YAML workflows. After reading this you should be able to run a board, read and validate workflows, install plugins, and find out why a task is stuck, without re-reading other docs unless you hit an edge case.

**Before you rely on anything here:**

- This guide is written for engine **1.2.88** or later. `wf --version` prints the installed one.
- `wf <command> --help` is the authority on commands and flags. If a command named here fails `--help`, the installed engine is older than this guide: say so and use what `--help` offers.
- No `wf` on the machine, or no board yet: use the `workflow-engine-setup` skill.
- To write or change a board's workflows, prompts or project plugin: use the `workflow-engine-author` skill.
- Finish on the engine's own proof, never on your own word: `wf doctor`, `wf workflow check`, `wf assemble`, or the task's history moving.
- Never ask the user to paste a secret into the chat. `wf secret set <KEY> -w .workflow` reads it from a no-echo prompt.

This skill ships inside the engine. Every `wf` call keeps the copies in `~/.claude/skills/` and `~/.agents/skills/` (read by Codex and Gemini CLI) up to date, unless someone edited a copy: an edited copy is left alone and stops updating (`wf skill install` says why). It is also published at https://github.com/gnarlysoft-ai/skills.

---

## Core mental model

> **You define WHAT should happen. AI agents figure out HOW.**

- **Workflow YAML** is the recipe: states, steps, triggers, failure routing, env, prerequisites.
- **Task files** are the record: one markdown file with YAML frontmatter per task. Its `state` decides which step runs next.
- **The engine** is deliberately simple. It reads a task's state, picks the step that triggers on it, runs it, checks the result against the workflow, and follows `on_fail`.
- **Agents** are AI coding CLIs. There are four backends: `claude`, `codex`, `gemini`, and `claude-local` (Claude Code pointed at the board's own model server). An agent moves a task by editing `state:` in the task file, and writes everything else through `wf task set` and `wf task findings`.
- **Hooks** are commands (usually Python) the engine runs around steps. `on_init` sets up a run and can fail it or make it wait; pre/post hooks gate a step; lifecycle hooks notify.
- **Plugins** are installable bundles: workflows, prompts, agents, skills and hooks. Extensions also ship pollers ("integrations"), actions, connections, settings rows and family contracts.
- **`wf loop`** is the long-running process. Each cycle it runs its sweeps (dependency release, flip returns, autopilot, pending actions) and dispatches **armed** tasks. On its own thread it polls the board's integrations (every 300 s by default).
- **The dashboard** (`wf dashboard`) is a web UI and HTTP API over one board.

State lives in files under the board directory, not in a database, which is why `wf task show`, the dashboard and a hook all see the same thing.

The engine is not only for code. Anything you can describe as states, steps and agents fits: content, data pipelines, research.

---

## A board on disk

`wf init --repo <repo>` creates the board (also called the workspace) at `<repo>/.workflow/`: `workspace.json`, `tasks/`, `logs/`, `reviews/`, and on a new board `settings.json`. Everything else comes from `wf plugin install` or is written while the board runs.

| Path | What it is | Written by |
|---|---|---|
| `workflows/*.yaml` | workflow definitions. A file whose name starts with `.` is ignored | plugin install, or you |
| `prompts/<agent>.md` | agent prompt templates | plugin install, or you |
| `hooks/`, `bin/` | hook scripts and helpers, called as `$WF_REPO_DIR/.workflow/hooks/<file>` | plugin install |
| `plugins.json` | what is installed and which files each plugin owns | plugin install only. An agent step that changes it fails |
| `tasks/<id>.md` | one file per task | `wf task create`, pollers, agents |
| `archive/` | archived tasks | the dashboard |
| `logs/` | `run-*.json` per run, and one `.jsonl` transcript (plus `.stderr.log`) per step | the engine |
| `artifacts/<id>/` | attachments and step outputs | the engine, agents |
| `integrations/*.json` | status cards: one per poller, plus `loop.json` (what the loop skipped or declined, per task) | `wf loop` |
| `settings.json` | board settings | `wf settings set`, the Settings page |
| `.env` | the board's secrets and env values | `wf secret set` |
| `paused-integrations.json` | pauses: per poller, and the board-wide dispatch pause | `wf pause`, the dashboard, pollers |
| `.dispatch-breaker.json` | the loop's own hold when the AI backend keeps failing | `wf loop` |
| `.locks/` | exec sentinels and locks | the engine |

**Every agent step needs a prompt template.** The engine looks in the workflow's own prompts directory first, then `<board>/prompts/<agent>.md` (`--prompts` overrides both). A missing template fails the step when it is dispatched, not when the workflow loads.

**A new board's AI steps reach only the MCP servers it requires** (`wf init` writes `WF_MCP_ALLOW=[]`). Add one with `wf settings set WF_MCP_ALLOW '["<server>"]' -w .workflow`. Claude Code and Gemini CLI enforce the list; Codex has no allowlist flag, so it does not, and `wf doctor` warns.

---

## CLI surface

Almost every command needs `-w <board>` (the `.workflow` directory). Without it `wf` uses a default workspace that is not your board, and answers "Task not found".

```bash
# The board
wf init --repo <repo>                               # create <repo>/.workflow
wf doctor -w .workflow                              # what is wrong here, and the fix (--json for scripts)
wf workflow check -w .workflow                      # validate every workflow; non-zero exit on a problem
wf settings get -w .workflow                        # board settings, where each value comes from
wf settings set <KEY> <VALUE> -w .workflow
wf secret set <KEY> -w .workflow                    # no-echo prompt; never pass a secret on argv
wf harness status -w .workflow --task <id>          # MCP servers / skills / plugins a task needs, and their state

# Tasks
wf task create -w .workflow --id <id> --title "<title>" --workflow <name> --description "<what to do>"
wf task list -w .workflow
wf task show <id> -w .workflow                      # frontmatter, context, history
wf task start <id> -w .workflow                     # arm it and put it first in the loop's queue
wf task transition <id> <state> --reason "<why>" -w .workflow   # manual move, any state to any state
wf task set <id> context.<key> <value> -w .workflow  # also branch, repos_touched, blocked_by; --json parses
wf task findings <id> --file findings.json --summary "<one line>" -w .workflow
wf task set-backend <id> <step> codex -w .workflow  # one step of one task on another backend
wf task hold <id> --kind <slug> --reason "<why>" --release "<what clears it>" -w .workflow
wf task release <id> -w .workflow
wf task backlog <id> -w .workflow                   # park it out of the working views; --undo brings it back
wf task verify <id> --stage <workflow> --reason "<how>" -w .workflow

# Checkpoints
wf approve -w .workflow                             # list everything waiting for a person
wf approve <id> --note "<why>" -w .workflow         # --reject sends it to on_reject

# Running work
wf exec --task <id> -w .workflow                    # run one task now (no arming needed)
wf run -w .workflow                                 # one dispatch pass over actionable tasks
wf loop -w .workflow --max-cycles 0                 # the daemon: armed tasks plus integrations
wf cycle list -w .workflow                          # chains of tasks linked by spawn; also show, arm, disarm

# Stopping the board
wf pause -w .workflow --until 2h --reason "<why>"   # running steps finish; nothing new starts
wf resume -w .workflow
wf loop drain -w .workflow                          # pause until `wf loop resume`, steps end at their boundary, then stop what is left
wf loop resume -w .workflow                         # lift the pause `wf loop drain` set
wf maintenance status -w .workflow
wf maintenance run -w .workflow --reason "<why>" -- <command>   # pause, wait for running steps, run, always release

# Watching
wf dashboard -w .workflow                           # http://127.0.0.1:8787
wf stalls -w .workflow --task <id>                  # steps that ran long while producing little output

# Plugins and extensions
wf plugin list                                      # plugins bundled with the engine
wf plugin status --repo <repo>                      # are the installed plugins current?
wf plugin install <plugin-dir> --repo <repo>
wf assemble <plugin-dir>                            # expand and validate a plugin before installing it
wf integration list -w .workflow                    # also run, enable, disable, verify, config, lint, schema
wf act <plugin>.<action> --task <id> -w .workflow   # run an extension action

# The AI CLIs
wf agent probe --backend codex                      # one short prompt through that CLI
wf agent check -w .workflow --wait                  # ask the running loop to check each CLI's sign-in
wf agent models -w .workflow                        # model choices per backend
```

**`wf loop` runs only ARMED tasks.** A task is armed when its context carries both `autonomous` and `chain_started_at` (always written together). `wf task create` leaves a task unarmed, so the loop skips it and `integrations/loop.json` lists it under `skipped` as `unarmed`. Arm a task with `wf task start <id>`, a whole chain with `wf cycle arm <cycle-id>`, from the dashboard, or by approving a checkpoint that declares `arm_on_approve: true`. `wf exec` and `wf run` do not check arming.

**`wf loop --max-cycles` defaults to 100.** Use `0` for a service. The engine ships systemd and launchd units: `wf setup extract <dir>` writes them out.

**`wf exec` runs until the next checkpoint, wait or terminal state**, not necessarily to the end. It exits **2** with a `STALLED:` banner when the task is waiting, which is "not run, not a failure, try again later".

**`wf queue` sets the order queued tasks run in.** `wf queue move <id> --first` (or `--to N`, `--before <id>`, `--after <id>`, `--last`) puts an armed task in the board's queue order; `wf queue list --json` shows the order with each task's status and wait; `wf queue remove <id>` and `wf queue clear` take tasks out. Listed tasks run before the board's own order, behind any task that is stalled or waiting on a dependency, and they pass the weekly budget line. `wf task start` and the dashboard's Put first put a task at the top and mark it `context.focus`, which its children carry (`wf queue` itself never touches `focus`). The order is a board file, so reordering is safe while a step runs; a finished, cancelled or unarmed task leaves it on its own.

---

## Workflow YAML

A workflow is a YAML file of states and steps. The full field reference and the four composition patterns (sequential pipeline, adversarial review, multi-model consensus, human checkpoints) are in the `workflow-engine-author` skill, in `reference/workflow-yaml.md` and `reference/patterns.md`. Use that skill to write or change a workflow. Enough to read one:

- `states:` is the vocabulary. `checkpoint: true` stops for a person (`on_approve` / `on_reject` say where Approve and Reject send the task), `terminal: true` ends the workflow, `blocked: true` holds a task while its `blocked_by` dependencies are unresolved, and `external: true` marks a state only a hook writes.
- Each step names an `agent` (its prompt template), the `trigger` state that fires it, and `transitions_to`: the states it may move the task into. It is required; `[]` means the step must not move the task.
- `on_fail` is `FAIL`, `RETRY` or a step name to jump back to. `condition` passes over a step that does not apply; `guard` makes the task wait until a context key is truthy. A step can run another workflow instead of an agent with `runs_workflow` and `mode: flip` or `mode: spawn`.
- A run can end **waiting** (an unmet `guard`, a hook exiting 2): no retry is spent, and `max_wait_seconds` bounds the wait.

Validate after every edit: `wf workflow check -w .workflow` (or `wf workflow check <name> -w .workflow`). A workflow is addressed by its `name:`, never its filename.

The dashboard's Approve and Reject take a note. It is stored as `context.checkpoint_feedback` and shown to later agents as `## Human Feedback`. **It stays on the task** and appears in every later prompt until the next note replaces it, so keep it specific to the gate.

---

## The Dashboard

```bash
wf dashboard -w .workflow                # http://127.0.0.1:8787; --port to change
```

- One board per dashboard process (`-w` is required).
- **"Dashboard not built"?** A release wheel ships the built UI and cannot rebuild it, so install a release wheel. An editable checkout builds it on first launch (needs Node.js and npm).
- **Access.** It binds to loopback by default. A non-loopback `--host` refuses to start without `WF_DASHBOARD_TOKEN`; requests then send it as `Authorization: Bearer <token>`. `WF_DASHBOARD_READONLY` refuses every write. `wf user add <name> --role viewer|approver -w .workflow` gives a person their own key (printed once); once anyone is added, every request needs a key, loopback included. `--login <tailscale-login>` instead lists a person who signs in through Tailscale Serve (on a dashboard started with `WF_DASHBOARD_PROXY_IDENTITY=tailscale`); it counts only on connections owned by Tailscale's OS user (`WF_DASHBOARD_PROXY_PEER_USER`, default root), never for a request from the board's own machine, and the setting stays off, saying why, where the dashboard cannot tell who owns a connection; it does not keep out root, programs running as Tailscale's user, a raw TCP forward (`tailscale serve --tcp`) pointed at the port, anyone Tailscale SSH lets in while its port forwarding is on, or, in userspace mode, any tailnet device that can reach the port; it prints no key, and login-only entries leave loopback as it was. For TLS, put a proxy in front.
- **It shows** tasks grouped as active, queued, review, sign-off, blocked, done, unverified, failed, rejected and undeclared; for each task its run log, live step transcripts, artifact panels, memo and decision questions, and rubric status (status, value, message per criterion).
- **It can** approve and reject checkpoints, run a task (which starts `wf exec`), arm and pause tasks, pause the board, and change board settings.
- Step transcripts have credentials redacted when they are written.

---

## Connecting other software: the Board API

The dashboard also serves a versioned API for other programs at `/api/v1`. `<url>/api/v1/` and `<url>/api/v1/contract.md` (`<url>` is the dashboard's address) explain it with no key.

- **Apps.** `wf app invite <app-name> --scopes read -w .workflow` makes a one-use pairing code (`--scopes read,act` to act, under the board's automation rules). `wf app list -w .workflow` lists the paired apps, and `wf app remove <app-name> -w .workflow` cuts one off.
- **MCP.** `wf mcp serve -w .workflow` is MCP for an AI client on this machine (`claude mcp add board -- wf mcp serve -w <workspace>`). Remote clients use `<url>/api/v1/mcp` with a key.
- **Events.** `GET /api/v1/events` streams them. For webhooks: `wf webhook add <url> -w .workflow`, `wf webhook list -w .workflow`, `wf webhook test <id> -w .workflow` and `wf webhook deliveries -w .workflow`.

When someone wants their own app, script, service or AI tool to read the board, answer its gates or hear its events, use the `wfe-integrate` skill. Code that must run inside the board is an extension (`workflow-engine-author`).

---

## Task files

```markdown
---
id: add-todo-form                 # also the filename: tasks/add-todo-form.md
title: Build AddTodoForm
state: reviewing                  # decides which step runs next
workflow: feature                 # required in practice: a task with none is never dispatched
task_type: ui
branch: feat/add-todo-form
blocked_by: []                    # task ids this one waits on
repos_touched: [api, app]         # sub-repos for a multi-repo task
review_findings:                  # written with `wf task findings`
  - category: A                   # A must fix, B blocked on something out of scope, C follow-up
    path: src/Form.tsx
    line: 23
    body: "**MUST FIX:** unescaped user input"
review_summary: "1 must-fix"
rubric_results: []                # written by an agent on a rubric step
history:                          # written by the engine only
  - {from: pending, to: implemented, at: '2026-04-05T12:00:00', reason: "..."}
context:                          # the cross-step scratchpad
  worktree_path: .worktrees/add-todo-form
  pr_urls: {app: "https://github.com/<owner>/<repo>/pull/<n>"}
---

## Description
Build a form component for adding todos.
```

**Who writes what.** An agent edits `state:` directly (and `rubric_results` on a rubric step), and writes everything else with `wf task set <id> <key> <value>` (`context.<dotted.key>`, `branch`, `repos_touched`, `blocked_by`) and `wf task findings`. It never writes `history`, `workflow` or `id`. A change to an engine-owned context key is reverted and fails the step. The engine writes a history entry for every move, including one an agent made by editing `state:`.

**`blocked_by`.** A dependency resolves when its task reaches a terminal state that is not a failure, judged by that task's own workflow. A dependency that ended in a failure terminal (a name containing `fail`, `error`, `abort`, `cancel` or `reject`) does **not** release the task: it stays held, and `wf doctor` lists it under `blocked_on_failed`. Blocked tasks are re-checked every cycle. When every dependency resolves, the task moves to `on_unblock_state` only if nothing in its workflow could move it from where it sits (and only then does `on_unblock` fire); otherwise the block is cleared and the state left alone. An entry that names no task shows under `wf doctor`'s `dangling_blocked_by`.

**`repos_touched`.** Each entry must be a directory, relative to the step's working directory (the task's worktree), falling back to the repo root. A bad entry fails the task before any agent runs. The list goes into the prompt as `## Repos Touched`.

**Common `context` keys:**

| Key | Meaning |
|---|---|
| `worktree_path` | the task's git worktree; agent steps run there unless `cwd: main` |
| `pr_url` / `pr_urls` | the PR a reactive task responds to / the PRs this task opened, one per repo |
| `autonomous`, `chain_started_at` | the arming pair |
| `checkpoint_feedback` | the latest note from a dashboard Approve or Reject |
| `decision_rulings` | a person's answers to memo questions; shown to agents as binding |
| `stalled_on`, `stalled_reason`, `stalled_since` | the task is waiting |
| `paused`, `cancelled`, `backlog` | an operator halted it |
| `workflow_failed_reason` | why the engine failed it |
| `cycle_id`, `spawned_from` | its chain of spawned tasks |

---

## The prompt an agent receives

The engine builds each agent step's prompt in this order:

1. The header: task file path, id, title, state and working directory.
2. `## Repos Touched` and `## Attachments`, when the task has them.
3. `## Human Feedback` (`context.checkpoint_feedback`) and `## Operator Feedback` (memo rulings), when set.
4. `## Feedback From Previous Attempt`, on a retry.
5. `## Step Objective`: the step's `description`.
6. `## Rubric`, when the step has one.
7. The agent's prompt template, under `## Your Instructions`.
8. `## Task file (as of dispatch)`: the frontmatter, minus `history` and the review findings themselves (only their count).
9. `## Valid States`: the step's `transitions_to`, and how to set `state:`.
10. The rule to write through `wf task set` / `wf task findings`, with the board's `-w` path.
11. The repo's agent instruction files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) by name; the CLI reads its own.
12. The extension actions the step may call, when it has any.

**Keep each source to one job.** Step-specific instructions go in the step's `description`; the agent's role and standing rules go in its template; project rules go in the repo's instruction file. A fix step must read `review_findings` from the task file (`wf task show <id>`): the prompt carries only their count.

---

## Backends

| Backend | CLI | Skip approvals | Model flag | JSON output | Prompt delivery |
|---|---|---|---|---|---|
| `claude` | Claude Code | `--dangerously-skip-permissions` | `--model <id>` | `--output-format stream-json` | stdin |
| `gemini` | Gemini CLI | `--yolo` | `-m <id>` | `--output-format stream-json` | `-p` flag |
| `codex` | Codex CLI | `--dangerously-bypass-approvals-and-sandbox` | `-m <id>` | `--json` | positional argument |
| `claude-local` | Claude Code on the board's model server | as `claude` | as `claude` | as `claude` | as `claude` |

Plugin agents are synced to `.claude/agents/` and `.gemini/agents/` as written, and translated to TOML under `.codex/agents/`. Skills go to `.claude/skills/` and `.agents/skills/` (Codex and Gemini CLI share it). The engine sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` for Claude steps, so one Claude step can run its own sub-agents.

**Session resume.** Within one run, a retried step may resume its earlier CLI session on the same backend; it then gets only a short follow-up, not the whole prompt. Otherwise it starts fresh with the full prompt and the previous failure under `## Feedback From Previous Attempt`. Sessions live in memory for one run only, so every new dispatch starts fresh.

---

## Prerequisites and hooks

`requires:` lists what a run needs before its first step (tools on PATH, env vars, the Python that hooks run under, check scripts), plus the MCP servers, skills and plugins the loop's harness checks. Hooks are commands (usually Python) the engine runs around a step (`pre`, `post`) and at lifecycle events (`on_init`, `on_terminal`, `on_checkpoint`, `on_state_change`, `on_unblock`); each gets a JSON context on stdin.

A hook's exit code is its verdict: `0` pass, `1` fail (the step fails and `on_fail` applies), `2` not ready (the task waits and is asked again on the next dispatch).

Every field, the hook context keys and the timeouts are in the `workflow-engine-author` skill's `reference/workflow-yaml.md`.

---

## Plugins

```
my-plugin/
├── plugin.yaml          # manifest (see plugin-manifest.md)
├── workflows/           # workflow YAML
├── prompts/             # agent prompt templates
├── agents/              # portable agent definitions, synced to each CLI
├── skills/              # SKILL.md folders
├── hooks/               # installed to .workflow/hooks/
└── bin/                 # installed to .workflow/bin/
```

**Three ways to start one:**

- `wf plugin new <name> --toolkit wf-toolkit` — a project plugin on top of a shared toolkit: it clones the toolkit's reference workflows and writes a `toolkit.config.yaml` from the toolkit's config schema. This is how most production boards are built: the toolkit ships the mechanism, the project plugin ships the values.
- `wf plugin init <name>` — an empty plugin.
- `wf plugin init --extension <name> -o <dir>` — a working extension: a poller, a read action, a connection, settings, a test.

`wf plugin list` shows the plugins bundled with the engine, including a small demo.

**Assembly.** At install, `{{wf:include <plugin>/<path>}}` and `{{wf.<key>}}` are expanded in workflows, prompts and agents, with values from the consumer's `toolkit.config.yaml` checked against each dependency's `config.schema.yaml`. Skills are **not** expanded: a `{{wf.<key>}}` in a SKILL.md reaches the agent as literal text. `wf assemble <plugin-dir>` runs the whole expansion and validation without installing (`--out <dir>` writes the result for a diff).

**Dependencies.** `depends:` names other plugins with version specs (`>=`, `^`, `==`); `engine:` sets a minimum engine version. Install the dependency first, then the consumer. `--with-dependencies` installs what the consumer needs first; `--with-dependents` reinstalls the consumers after a library changes. Installing only the library leaves the consumers' expanded files stale, and the install says which.

**Family contracts.** A dependency may ship `contracts/<family>.yaml`: states, transitions and hook files a workflow with that `name:` must have. A violation fails both `wf assemble` and `wf plugin install`.

**Installing safely:**

- `wf plugin install` refuses while an agent step is running on the board (it rewrites the hooks that step uses). Use `wf maintenance run -w .workflow --reason "plugin update" -- wf plugin install <dir> --repo <repo>`, or `--force`.
- It refuses to overwrite an agent or skill file it did not write: `--adopt` backs yours up and installs, `--skip` keeps yours.
- It refuses when two plugins claim the same file.
- When the new version drops a state some task sits in, it names those tasks; `--strict` makes that a non-zero exit.
- Prove it afterwards: `wf plugin status --repo <repo>` (exit 1 when something is stale), `wf assemble --installed <repo>` (checks installed files against their recorded hashes), `wf workflow check -w .workflow`.

**The manifest** is a versioned contract described field by field in [plugin-manifest.md](plugin-manifest.md) (also `wf integration schema --markdown`). `wf integration lint <dir>` checks an extension's manifest and pollers. It requires at least one `integrations:` entry, so for a plugin that only ships workflows, `wf assemble` is the check.

### Extensions

- **Integrations** are pollers: scripts `wf loop` runs on its integrations thread (each gets 120 s unless its entry says otherwise). Their status cards are `integrations/<name>.json`. Manage them with `wf integration list`, `enable`, `disable`, `run` and `verify`; `wf integration config` writes their settings (secrets from stdin).
- **Connections** carry credentials and a `verify` probe.
- **Actions** are commands an extension declares, each a `read` or a `write`. Run one with `wf act <plugin>.<action> --task <id> --<arg> <value> -w .workflow`. A step may call a write action only when its `uses:` names it. Every write is recorded in the task's action ledger, and the dashboard shows it.

**Dry runs.** `wf integration run <name> --dry-run -w .workflow` and `wf act <plugin>.<action> --task <id> --dry-run -w .workflow` run against a throwaway copy of the board with `WF_DRY_RUN=1` and print, as JSON, what would change. The extension must honour it: when `WF_DRY_RUN` is `1`, skip every external write and print one `{"would": "<verb>", "target": "<what>", "detail": {...}}` line per skipped write. The report lists those lines with `"source": "extension"`, and every file the run changed in the board copy with `"source": "workspace"`. Only entries that declare `dry_run: true` are dry-run (a read action always runs), and `wf integration lint` warns about a writer that never reads `WF_DRY_RUN`. A dry run takes no lock, so it is safe beside a running loop.

---

## Production patterns

**Multi-perspective review.** Run correctness and security reviewers in one `parallel_group` on different backends, then a synthesizer with no `trigger` (pattern 3 in the `workflow-engine-author` skill's `reference/patterns.md`).

**Category A/B/C findings.** Reviewers write findings files; the synthesizer merges them:

- **A** (in scope, must fix): store them with `wf task findings` and move to `changes-requested`.
- **B** (blocked on out-of-scope work): create the blocker (`wf task create ...`), add it with `wf task set <id> blocked_by '["<blocker-id>"]' --json`, and move to a `blocked: true` state if the workflow has one.
- **C** (follow-up): create a new task and carry on.

**Worktree provisioning.** Make it an `on_init` hook: it runs once per run, costs no tokens, and writes `context.worktree_path`, after which agent steps run in that worktree. Steps that must run at the repo root take `cwd: main`.

**Multi-repo work.** In an umbrella folder of repos, set `repos_touched: [repo-a, repo-b]` on the task. The engine checks the directories before dispatch and tells the agent to `cd` into each.

---

## Why isn't this task moving?

Check in this order. Start with `wf task show <id> -w .workflow`, `wf doctor -w .workflow`, and the loop's card `integrations/loop.json`: its `skipped` and `declined` lists name each task the loop passed over and why.

1. **At a checkpoint?** `wf approve -w .workflow` lists those. Answer with `wf approve <id>`.
2. **Armed?** `wf loop` runs armed tasks only: is `context.autonomous` set? Arm with `wf task start <id>` or `wf cycle arm <cycle-id>`.
3. **Halted?** `context.paused`, `cancelled`, `backlog` or `workflow_failed` on the task.
4. **Board paused?** `paused-integrations.json` lists the dispatch pause under one of `loop`, `loop-kill-switch`, `loop-usage-limit` or `autonomous-drain`. `wf resume -w .workflow` lifts them. A maintenance window shows in `wf maintenance status`.
5. **Breaker held?** `.dispatch-breaker.json` says `held` or `probing` when the AI backend kept failing; it lifts by itself after a trial dispatch succeeds. The dashboard's health endpoint (`/api/health`) reports it.
6. **Blocked behind another task?** `wf doctor` rows `blocked_on_failed` (a predecessor failed) and `dangling_blocked_by` (an entry names no task).
7. **Waiting?** `context.stalled_on` and `stalled_reason`. Hook holders show in `wf doctor`'s `locks` row, and `on_init` waits that never change in `oninit_deferrals`.
8. **No step applies at its state?** Every step there has a falsy `condition` (or a `context.skip_steps` entry). After one dispatch prints `No step ran`, the loop skips it as `no-step-applies`; `wf doctor`'s `no_step_applies` row names the task, the step and the key. Write the key (`wf task set <id> context.<key> true --json`) to let the step run, or move the task with `wf task transition <id> <state>`.
9. **State not in its workflow?** The loop skips it as `undeclared-state`, and `wf plugin status` counts tasks left in states a plugin update removed. Fix with `wf task transition <id> <declared-state> --reason "<why>"`.
10. **Setup failing?** An `on_init` failure fails the task (`context.workflow_failed_reason`) and the loop holds all dispatch for 20 cycles.
11. **No room?** `declined` names the cause: `WF_EXEC_MAX_CONCURRENT` slots full, a disk or memory floor, the task or branch already running, a maintenance window. Also check `wf harness status --task <id>` (a required MCP server, skill or plugin is not ready), a step held as `not-proven` (its backend is outside `proven_backends`), and `wf agent check --wait` (a CLI needs signing in).

**Prove the fix by the outcome, not the mechanism:** the task's history gains an entry, or its `updated_at` moves (`wf task show <id>`). A running loop with no errors is not evidence that work is moving.

When you had to explain something here that `wf doctor` or the dashboard should have said, tell the user: it is a product gap worth reporting.

---

## A step failed

1. `wf task show <id> -w .workflow` — state, history, `context.workflow_failed_reason`.
2. The run log, `logs/run-*.json`: every step, its backend and model, state before and after, tokens, duration and error.
3. The step transcript, `logs/<time>-<backend>-<step>-<task>.jsonl`, and its `.stderr.log`. The dashboard streams the same.
4. `wf stalls -w .workflow --task <id>` — steps that ran long while producing little.
5. Hooks: a post hook exiting 1 fails the step; exit 2 is a wait, not a failure; a timeout is retried, then a wait.

### The review loop is not converging

1. Do the builder and the reviewer use **different backends**?
2. Does the reviewer's template ask it to be strict, with categories it must justify?
3. Does the fix step read `review_findings` from the task file? The prompt carries only their count.
4. Is `max_retries` / `max_iterations` high enough for the loop you expect?
5. Are models pinned on both sides, so a CLI default change does not move the result?
6. Should it be a loop at all? For measurable criteria (tests pass, a score of at least N), one step with a `rubric` and `on_fail: <itself>` is simpler. Keep two-model review for judgment calls: security reasoning, design.

---

## Common gotchas

1. **Forgetting `-w .workflow`.** Commands then act on the default workspace and report "Task not found".
2. **A created task never runs under `wf loop`.** It is unarmed: `wf task start <id>`.
3. **A missing prompt template fails at dispatch**, not at load.
4. **`on_fail: <step>` does not loop a state-triggered workflow.** Route loops through states.
5. **A synthesizer after a parallel group should have no `trigger`**, so it runs after the group, in file order.
6. **Reviewers in a parallel group should not change state**; let the synthesizer do it.
7. **Checkpoint feedback persists.** It is repeated in every later prompt until a new note replaces it.
8. **A failed dependency keeps its dependants blocked.** Restore and finish the predecessor, or remove the `blocked_by` entry.
9. **`requires.tools` / `env` / `python` / `hooks` are checked once per run.** For checks before every step, use pre hooks.
10. **`env:` cannot override the host environment.** Unset the value in the host or service env.
11. **`backend_args` are not shell-parsed.** One token per list item.
12. **The dashboard binds to loopback.** Off loopback it needs `WF_DASHBOARD_TOKEN`, and TLS is your proxy's job.
13. **Answering a checkpoint while its step is still running is refused.** Wait for the step to end.
14. **The rubric is the honour system.** Gate critical criteria with a post hook as well.
15. **Only one rubric step per `parallel_group`.** The workflow will not load otherwise.
16. **A `{{wf.<key>}}` inside a plugin's SKILL.md is not expanded.**

---

## When to use the engine vs. calling an AI CLI directly

| Use the engine when... | Call the CLI directly when... |
|---|---|
| the work has several steps with failure routing | it is one-shot generation |
| you want two models to check each other | one model is enough |
| a person must approve mid-way | the task is autonomous end to end |
| you need structured logs, retries and history | no audit trail is needed |
| tasks depend on each other (`blocked_by`) | tasks are independent |
| the workflow is reused across projects (plugins) | it is a one-off |
| contracts between steps must be enforced | you can trust one model's output |

**Rule of thumb:** if you can describe the work as a state machine with failure routing, use the engine. If it is "read this and write that", call the CLI.

---

## How to help with common requests

### "Show me it working"

```bash
wf setup extract ~/wf-examples
~/wf-examples/examples/run-example.sh 01-hello-world
```

The script copies the example into a sandbox next to `examples/`, initialises git and runs `wf exec`. The examples pin `backend: claude`; for another CLI, change the step with `wf task set-backend <task> <step> codex -w <sandbox>/.workflow`.

### "Create a workflow for X", or "change how the agents work"

Use the `workflow-engine-author` skill. It works in the board's project plugin, never in the installed files (the next install overwrites those), and it finishes on `wf assemble`, `wf plugin install`, `wf workflow check` and `wf doctor`, not on its own word.

### "Install a plugin"

```bash
wf assemble <plugin-dir>
wf plugin install <plugin-dir> --repo <repo>
wf plugin status --repo <repo>
wf workflow check -w <repo>/.workflow
```

It copies workflows, prompts, hooks and helpers into `.workflow/` and syncs agents and skills to each CLI's directories. A catalog extension installs by name: `wf plugin install <name>@<version-spec> --repo <repo>`.

### "Write an agent prompt template"

A template says who the agent is: its role, standing rules and protocol. What to do in a particular step goes in that step's `description`. An example:

```markdown
You are a senior developer on this project.

## Your rules
- Read the repo's agent instruction file (CLAUDE.md, AGENTS.md or GEMINI.md) first.
- Write a failing test before the fix.
- If the tests fail, your step failed. Say so; do not hide it.

## Your task file protocol
1. Read the task file: description, acceptance criteria, context.
2. Do the work.
3. Record what the next step needs with `wf task set` (and findings with `wf task findings`).
4. Set `state:` to one of the valid states listed below.
```

---

## Where to look things up

- `wf --help` and `wf <command> --help` — commands and flags.
- `wf doctor -w .workflow` — what is wrong with this board right now, with the fix.
- `wf workflow check -w .workflow` — whether a workflow is valid.
- `wf setup extract <dir>` — the onboarding guide (`docs/`), runnable examples (`examples/`), and the service units and env examples (`deploy/`).
- `<board-url>/api/v1/contract.md` — the Board API's contract, served with no key.
- [plugin-manifest.md](plugin-manifest.md) beside this skill, or `wf integration schema --markdown` — every `plugin.yaml` field.
- The engine is a Python package (`workflow_engine`). When this guide and the code disagree, the code is right, and this guide is out of date.

---

## Final instruction

After reading this, help the user with Workflow Engine work proactively, without re-reading other docs. When something is not covered here, use `--help`, `wf doctor` and the shipped docs and examples, in that order.

Announce that you loaded the skill with one line, such as:
> Loaded `learn-workflow-engine` — ready to help run, debug and extend your Workflow Engine board.

Then ask what the user wants to do.
