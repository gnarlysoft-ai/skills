# Workflow YAML reference

Every workflow, state and step field, for the `workflow-engine-author` skill. `wf workflow check -w <ws>` is the authority: run it after every edit.

A complete workflow that loads. Build, review on a second backend, loop on findings, then a person signs off:

```yaml
name: feature
description: Build a change, review it on a second backend, then a human signs off.
initial_state: pending
max_retries: 3

env:
  GH_TOKEN: ""                   # no default: read from <ws>/.env or the host env
requires:
  tools: [git, gh]
  env: [GH_TOKEN]                # fail before any step if it is not set

states:
  - name: pending
  - name: implemented
  - name: changes-requested
  - name: approved
    checkpoint: true             # the engine stops here for a person
    on_approve: done
    on_reject: changes-requested
  - name: done
    terminal: true
  - name: failed
    terminal: true

steps:
  - name: implement
    agent: developer             # prompts/developer.md
    trigger: pending
    transitions_to: [implemented]
    backend: claude
    on_fail: RETRY

  - name: review
    agent: code-reviewer
    trigger: implemented
    transitions_to: [changes-requested, approved]   # a branching step lists every landing
    backend: codex               # a second model reviews the first one's work
    on_fail: RETRY

  - name: fix
    agent: developer
    trigger: changes-requested
    transitions_to: [implemented]                    # back to review: the loop
    backend: claude
    on_fail: RETRY
```

Validate after every edit: `wf workflow check -w .workflow` (or `wf workflow check <name> -w .workflow`). It checks names, reachability, trap states (a state nothing can leave), `transitions_to`, and two files claiming one `name:`. A workflow is addressed by its `name:`, never its filename.

### Top-level fields

| Field | Default | Meaning |
|---|---|---|
| `name` | required | the workflow's identity |
| `description` | | human-readable |
| `initial_state` | `pending` | state for new tasks |
| `max_retries` | `3` | retries per step (`RETRY`, or jumps back to a named step) |
| `max_iterations` | `50` | ceiling on steps in one run |
| `max_wait_seconds` | `86400` | longest a task may WAIT (see *Waiting*). `0` = no limit |
| `max_workflow_depth` | `3` | how deep `runs_workflow` may nest, checked at load |
| `max_cycle_depth` | `6` | how many spawn hand-offs one chain may make before it parks for a person |
| `env` | | env values for agent and hook processes (see *Env*) |
| `requires` | | prerequisites (see *Prerequisites*) |
| `states` | | the vocabulary. Without it the workflow runs its steps in order and checks no states |
| `steps` | required | the steps |
| `hooks` | | lifecycle hooks (see *Hooks*) |
| `on_unblock_state` | `initial_state` | where a released `blocked_by` task goes when nothing could move it from where it sits |
| `render` | | dashboard artifact panels |
| `phases` | | the dashboard's stage-bar segments. Display only |
| `proven_backends` | | backends this workflow is proven on. A step routed elsewhere is held |
| `autopilot` | | the loop answers this workflow's checkpoints itself (see below) |
| `reactive` | `false` | this workflow reacts to another task's work (a CI fix, a rebase); the dashboard shows its tasks inside the work they serve |
| `intake` | | marks a lane that receives intake items, or an intake router |

### State fields

| Field | Meaning |
|---|---|
| `name` | any string; the engine has no built-in states |
| `checkpoint: true` | the engine stops; a person answers with `wf approve` or the dashboard |
| `on_approve` / `on_reject` | where Approve and Reject send the task. Without them the dashboard guesses the next / previous state, which is wrong for loops: declare them |
| `terminal: true` | the workflow ends here |
| `blocked: true` | a task parks here while its `blocked_by` dependencies are unresolved |
| `external: true` | only a hook writes this state (a merge listener writing `merged`, say). Nothing in the workflow may transition into it, and a non-terminal external checkpoint needs `on_approve` / `on_reject` |
| `arm_on_approve: true` | Approve also arms the task for the loop. Checkpoint with `on_approve` only |
| `autopilot: false` | opt one checkpoint out of `autopilot` |

A state that is both `terminal` and `checkpoint` is a sign-off: nothing runs, but a person still owes the last answer.

### Step fields

| Field | Meaning |
|---|---|
| `name` | unique within the workflow |
| `agent` | prompt template name. A step instead names `runs_workflow` or a handoff |
| `transitions_to` | **required**. The states this step may move the task into. `[]` = must not move it |
| `trigger` | the state that fires this step. Without it, steps run in file order |
| `backend` | `claude` (default), `codex`, `gemini`, `claude-local`. A typo fails the load |
| `model` | pin a model for this step's CLI |
| `backend_args` | extra argv tokens for the CLI |
| `description` | the step's objective, put into the prompt |
| `on_fail` | `FAIL` (default), `RETRY`, or a step name |
| `parallel_group` | steps sharing a group run at the same time |
| `condition` | context key. Falsy: the step does not apply and is passed over |
| `guard` | context key. Falsy: the task WAITS here, re-checked on every dispatch |
| `timeout_seconds` | default 1800 |
| `cwd: main` | run at the repo root instead of the task's worktree |
| `env` | step-level env, over the workflow's |
| `hooks.pre` / `hooks.post` | step hooks |
| `rubric` | success criteria the agent must report as passed |
| `runs_workflow` + `mode` | run another workflow instead of an agent (`flip` or `spawn`) |
| `effect` | the context path this step exists to produce |
| `uses` | extension actions the step may call |
| `skippable: true` | lets one task skip the step, with a reason |
| `phase` | which stage-bar phase the step counts under |
| `tool_policy` | `read-only`: no bypass flag, file-read tools only; refused on codex (and gemini until measured). A read-only step declares `transitions_to: []`, no rubric, no uses |

A hook entry is `{command, timeout_seconds?}`; an `on_init` entry may also carry `preflight: true`.

### `transitions_to` — the guard against made-up states

Every state a step may land on must be listed, and every listed name must be declared in `states:` (a typo fails the load with a "did you mean"). After the step runs, the engine checks the task's state: outside the list, or moved when the list is `[]`, fails the step and routes through `on_fail`, and `RETRY` hands the agent a correction ("you wrote `done`; valid states are ..."). This is also the "forgot to transition" guard: a step that leaves the task on its own trigger fails, unless it lists that trigger. Manual moves (`wf task transition`, the dashboard) are not checked: they are the operator's escape hatch.

### `on_fail`

| Value | Behavior |
|---|---|
| `FAIL` | stop the workflow |
| `RETRY` | run the same step again, up to `max_retries` |
| `<step-name>` | jump back to that step, up to `max_retries` times |

- **A jump back only works in a sequential (trigger-less) workflow.** In a state-triggered workflow a failure puts the state back, so the same trigger fires the same step again. Build loops there with states, like `review → changes-requested → fix → implemented` above.
- A task that ran out of retries can be given one more from the dashboard ("Try again"), which raises its own limit by one.
- A step that declares `effect: context.<path>` and has already written that value is recorded **completed with a warning** when its agent then exits non-zero: no retry, no `on_fail`. Write the effect before any trailing work that might fail. If the step does run again, its prompt opens by telling the agent what the task already records.

### `condition` vs `guard`

| Field | Question | When the key is falsy |
|---|---|---|
| `condition` | does this step apply at all? | the step is passed over |
| `guard` | may it run yet? | the task waits here; no retry is spent |

### Waiting (`max_wait_seconds`)

A run can end without succeeding or failing: it is **waiting**. Sources: an unmet `guard`, a `uses` action marked `required: true` that is unavailable, a hook exiting 2, or a hook that timed out. A wait spends no retry and no iteration. The next dispatch checks again, and `wf loop` sorts waiting tasks to the back of its queue.

The task shows it in `context`: `stalled_on` (what it waits on), `stalled_reason`, `stalled_since`, `stalled_observed_s`. `max_wait_seconds` is measured against `stalled_observed_s`, the time the engine actually spent checking (each gap is credited at most one hour), so a stopped loop or a rebooted machine does not burn a waiting task. Past the ceiling the run fails and says why. A hook that names a `holder` restarts the clock when the holder changes, so a queue that moves never expires. A hook that says `needs_person: true` lists the task under "Needs you" and its wait never expires.

### Env

When the engine starts an agent or hook process, values resolve in this order, last wins:

1. workflow `env:`
2. step `env:`
3. `<board>/.env`
4. the host environment

`env:` declares defaults and the set of names `requires.env` can check; the process inherits the rest of the host environment. `""` means "no default". Board settings from `settings.json` are laid over hook and poller env. To force a value the host sets, unset it in the host or service env: `env:` cannot override it. On a board using a GitHub App identity, child processes get no `GH_TOKEN` / `GITHUB_TOKEN`.

### Models

Without `model:`, each CLI uses its own default. Pin one when reproducibility matters:

```yaml
- name: review
  agent: code-reviewer
  transitions_to: []
  backend: gemini
  model: gemini-3.1-pro-preview   # passed to the CLI as -m / --model
```

The engine does not validate model names. Prove one with `wf agent probe --backend gemini --model <id>`. A board can move steps to another model or backend without editing YAML: `WF_MODEL_OVERRIDES` (`wf settings set WF_MODEL_OVERRIDES '<json>' --dry-run -w .workflow` previews it). From first match to last: a task's own choice, then the board's `<workflow>.<step>`, `<workflow>.*` and `*.<step>` keys, then the installed step (when it differs from the board's installed default), then the board's `*`, then the installed step. A step routed to a backend outside the workflow's `proven_backends` is held, not run.

### `backend_args`

A list of argv tokens passed to the CLI after the engine's own flags. Each element is one literal argument, never shell-parsed, so write `["--max-turns", "40"]`, not `["--max-turns 40"]`, and quote numbers. Never override the flags the engine parses output with: `--output-format`, `--print`, `--verbose`, `--json`, `--yolo`, `--dangerously-skip-permissions`, `--dangerously-bypass-approvals-and-sandbox`, `--resume`. Prefer `model:` to a model flag in `backend_args`.

### `rubric` — self-checked success criteria

```yaml
- name: implement-ui
  agent: developer
  transitions_to: []
  on_fail: implement-ui          # retry until the criteria pass
  rubric:
    - id: tests                  # [A-Za-z_][A-Za-z0-9_]*, unique in the step
      label: All tests pass
      target: pass               # free text; the agent interprets it
    - id: lighthouse_perf
      label: Lighthouse performance
      target: ">= 90"
      numeric: true              # asks the agent for a measured value
```

1. Before the step runs, the engine clears this step's criterion ids from `rubric_results`, so a silent agent cannot inherit an earlier verdict.
2. The criteria are added to the prompt.
3. The agent checks its own work and writes `rubric_results` (each `{id, status: pass|fail, value, message}`) and `rubric_iterations` to the task file before it transitions.
4. The step succeeds only if every criterion says `pass`; otherwise `on_fail` applies.

It is the honour system: the engine does not re-run the checks. Gate what matters with a post hook too. Only one rubric step per `parallel_group` (the workflow refuses to load otherwise). The retry gets rubric feedback only when the rubric is what failed and the retried step has a rubric of its own; otherwise it gets the actual error.

### `render` — dashboard artifact panels

```yaml
render:
  - type: link
    from: context.pr_url
    label: Pull Request
    icon: github                 # link only: github, external, play
    show_in_states: [approved]   # optional; empty = whenever the value exists
  - type: findings
    from: review_findings[]      # [] takes the whole list
  - type: kvp
    label: Build
    from: context
    fields:
      - {from: context.commit_sha, label: Commit}
```

Nine types: `link`, `markdown`, `kvp`, `findings`, `image`, `video`, `diff`, `json`, `child_tasks`. Without a `render:` block the dashboard shows `context.pr_url`, `context.pr_urls` (one link per repo), `context.task_url`, `context.tunnel_url` and `description` when present.

### Sub-workflows (`runs_workflow` and `mode`)

A step can run another workflow (in the same directory) instead of an agent:

- `mode: flip` — the same task switches to the other workflow and runs it. The outer step learns only which terminal state it reached, and maps that to its own `transitions_to`. If the inner workflow stops at a checkpoint, the task waits there, and control returns to the outer workflow once the inner one finishes.
- `mode: spawn` — creates a new task on the other workflow, moves the parent to its single `transitions_to` target, and is done. It never waits for the child. Parent and child share `context.cycle_id`; the child's `context.spawned_from` names the parent. `wf cycle show <cycle-id>` reads the chain.

A chain past `max_cycle_depth` hand-offs parks with a `HUMAN-DECISION-cycle-depth-...` entry in `blocked_by` instead of spawning; removing that entry grants exactly one more hand-off.

### Autopilot, intake and actions, in brief

- `autopilot: true` — each loop cycle approves this workflow's parked checkpoints that are armed (or whose Approve arms them), taking the memo's recommendation for each open question. It holds instead of approving when a question has no recommendation, a PR in `context.pr_urls` is still open, or a step is running. It never merges.
- `intake:` — `external: true` marks a lane that can receive intake items (it needs a `summary`); `router: true` marks a router that reviews an item and hands it to a lane.
- `uses:` — the extension actions a step may call, as `<plugin>.<action>`; `{action: ..., required: true}` makes the step wait while that action is unavailable.

## Field details for authors

The sections above are the summary. These are the rules an author trips on.

### `guard`: wait at the gate

`guard: <context key>` must be truthy before the step may run. It is re-read
on every dispatch attempt, never cached. An unmet guard **waits**; it never
skips: the step does not run, the task keeps its state, no retry is spent and
`on_fail` is not consulted. The task moves the moment whoever owns the fact
writes the key, for example `wf task set <id> context.<key> true --json -w <ws>`.
`condition` is read first, so a step that does not apply never parks a task on
its guard. In a `parallel_group`, an unmet guard on any member holds the whole
group.

### `external: true` states

An external state is one only a hook writes, such as `merged` written by a
merge listener. Without the flag such a state cannot be declared at all:
nothing in the workflow reaches it, so the load fails with
`ERR_UNREACHABLE_STATE`.

- Nothing in the workflow may move a task into it. A `transitions_to`,
  `on_approve`, `on_reject` or `on_unblock_state` naming it fails the load
  (`ERR_EXTERNAL_STATE_TARGETED`).
- It counts as an entry point, so steps triggered on it may lead on to other
  states.
- A non-terminal external checkpoint needs `on_approve` or `on_reject`
  (`ERR_EXTERNAL_CHECKPOINT_NO_EXIT`). A hook seeds tasks straight into it, and
  a step triggered there never fires while the checkpoint holds the task.

### `arm_on_approve: true`

On a checkpoint with an `on_approve` target, Approve also arms the task for
`wf loop`, which dispatches armed work only, so one click releases the whole
chain. On any other state it fails the load
(`ERR_ARM_ON_APPROVE_NOT_CHECKPOINT`), and it is refused on an intake router's
`reconciliation-review` and `route-review` (`ERR_ARM_ON_APPROVE_INTAKE_REVIEW`).
Only the answer to that checkpoint arms; Reject and other moves never do.
`wf approve` arms too, so do not declare it on a checkpoint an automation
approves unless that approval is meant to release the chain.

### `autopilot`

`autopilot: true` at the top level lets the loop answer this workflow's
checkpoints itself. A toolkit lane reads the board's choice from config,
quoted because assembly substitutes text: `autopilot: "{{wf.autopilot}}"`.
Each cycle, for every armed task parked at one of its checkpoints (or at an
`arm_on_approve` gate), it rules each open memo question with that question's
recommendation and approves. It holds instead, and records why on the task,
when a question has no recommendation, a PR in `context.pr_urls` is still
open, a dependency is unresolved, a step is running, or the state says
`autopilot: false`. It never merges. Turning it on approves every parked,
armed checkpoint of that workflow on the next cycle. It is a live-behaviour
switch: change it only when the user asks for exactly that.

### `intake`

- `intake: {external: true, summary: <one paragraph>}` marks a lane intake can
  hand work to. The summary is what a router, and a person, choose by.
- `intake: {router: true, autonomous_state: <state>}` marks an intake router,
  which reviews an item and hands it to a lane. `autonomous_state` is the state
  an armed item runs from once its seed checkpoint is approved. It must be a
  declared state that is not terminal, checkpoint or external
  (`ERR_INVALID_INTAKE_AUTONOMOUS_STATE`), and it is refused on a workflow that
  is not a router.

`wf workflow catalog --intake --json -w <ws>` lists the lanes a board offers.

### `phases`

`phases: [{id, label?}]` lists the dashboard stage bar's segments in order, and
a step's `phase: <id>` says which segment it counts under. Display only: no
step runs differently. A step's `phase:` outside a declared list fails the
load (`ERR_UNKNOWN_PHASE`), and so does an id listed twice
(`ERR_DUPLICATE_PHASE`).

### `runs_workflow` and `mode`

- `mode: flip` runs the other workflow on the same task. The outer step learns
  only which terminal it reached: a success terminal lands the task on the
  step's `transitions_to` target (or on a target named after that terminal,
  which is how a step branches on the outcome); the failure terminal fails the
  step and its `on_fail` applies. If the inner workflow stops at a checkpoint,
  the task waits there and control returns to the outer workflow once the
  inner one finishes.
- `mode: spawn` creates a new task on the other workflow and moves the parent
  to its `transitions_to` target, which must be exactly one state. It never
  waits for the child.
- `mode` without `runs_workflow` fails the load, and so does an unknown
  workflow name. `max_workflow_depth` (default 3) caps nesting at load;
  `max_cycle_depth` (default 6) caps hand-offs at run time, after which the
  chain parks for a person.

### What is not a wait

A checkpoint (a person owes an answer) and a `blocked: true` state
(dependencies unresolved) are not waits: neither is bounded by
`max_wait_seconds`.

## Prerequisites (`requires`)

```yaml
requires:
  tools: [docker, git, gh]        # must be on PATH
  env: [GH_TOKEN]                 # must be set, after .env is loaded
  python:                         # the PATH python3 that hooks run under
    version: "3.10"               # quote it: unquoted 3.10 is the number 3.1
    modules: [yaml]
  hooks:
    - command: python3 "$WF_REPO_DIR/.workflow/hooks/check-docker.py"
```

These run once, before the first step of a run. A failure fails the task ("missing tool: docker", "missing env var: GH_TOKEN", "hook failed: ...") without spending a token. `python:` probes the `python3` on PATH (or the one `WF_HOOK_PYTHON` pins), never the engine's own interpreter, because that is what hooks run under.

`requires` can also list `mcp`, `skills` and `plugins`. Those are checked by the loop's harness on an interval, not once per run, and a task whose item is not ready is held before it starts rather than failed: `wf harness status --task <id> -w .workflow`.


## Hooks

A hook gets a JSON context on stdin and may print one JSON object on stdout.

```python
# .workflow/hooks/require-findings.py — a post hook on a review step
import json, os, sys

ctx = json.load(sys.stdin)
path = os.path.join(ctx["step_cwd"], "review_findings.json")
if not os.path.exists(path):
    print(json.dumps({"message": f"Write your findings to {path} before you finish."}))
    sys.exit(1)
sys.exit(0)
```

**Context keys:** `event`, `step_name`, `agent`, `backend`, `task_id`, `task_file`, `task_state`, `task_state_before`, `success`, `workspace_dir`, `repo_dir`, `step_cwd`, `worktree_path`, `repos_touched`, plus token and cost fields; a post hook also gets `agent_output`, the agent's final answer. **Env vars:** `WF_REPO_DIR`, `WF_WORKSPACE_DIR`, `WF_STEP_CWD`, `WF_WORKTREE_PATH`, and the workflow's `env:`.

| Exit | Meaning |
|---|---|
| `0` | pass |
| `1` | fail: the step fails and `on_fail` applies. An `on_init` failure fails the run |
| `2` | not ready, ask again: the task waits (on `on_init`, pre hooks and post hooks; in a parallel group a post hook's 2 is a failure) |

- **stdout keys.** `message` goes to the agent on the retry. On exit 2, `holder` names who the task queues behind, and `needs_person: true` says only a person can clear it.
- **Timeouts.** 30 s unless the entry sets `timeout_seconds`. A timeout is retried twice, then treated as a wait, never a failure.
- **A script that cannot be opened is a failure**, even though `python3 missing.py` exits 2.
- **`on_init` failures.** After one `on_init` failure, `wf loop` holds all dispatch for 20 cycles instead of failing the next task the same way; the hold then lifts by itself.
- **A post hook that waits** sends the step back to run again on the next dispatch; if nothing changed (the git heads and the landed state), only the post hooks run again.

**Lifecycle hooks** (workflow-level `hooks:`):

- `on_init` — once, before the first step. Setup: a lock, a worktree. It can fail the run (1) or make it wait (2). Entries marked `preflight: true` only check whether a run can start and must come first; `wf doctor --onboarding` runs them.
- `on_terminal` — the task reached any terminal state.
- `on_checkpoint` — the task reached a checkpoint.
- `on_state_change` — every state change.
- `on_unblock` — a `blocked_by` release moved the task.

Hooks are where validation and integration live: contracts between steps, `gh` calls (labels, PR comments), notifications, database checks.
