# A project plugin on top of wf-toolkit

The model behind the `workflow-engine-author` skill's levers, in depth. wf-toolkit ships the mechanism; the board's project plugin ships the values. Everything here is changed in the project plugin, never in the toolkit.

## The three layers

```
workflow-engine   the runner.        Generic. Never project-specific. Not yours to edit.
      ▲
wf-toolkit        the MECHANISM.     Generic. Reference workflows, role prompts,
      ▲                              partials, hooks, config schema. Shared by
      │                              every project — also not yours to edit.
      │
your-plugin       the VALUES.        The project's workflows, config, prompt
                                     overrides, hooks, skills. All yours.
```

The rule the whole design turns on: **wf-toolkit ships the mechanism, your
plugin ships the values.** If you find yourself wanting to put the project's
name, URL, model choice, or stack assumption into wf-toolkit, that's the signal
you've found a missing config var — not a reason to edit the toolkit. Every
other project would inherit whatever you put there.

## The levers

There are four levers, in increasing order of blast radius. Reach for
the smallest one that works. They are L1 to L4 in the skill's lever table;
a new workflow is the skill's L5.

### Lever 1 — edit the step in your own `workflows/*.yaml`

The cloned workflows are **your files**. Nothing is inherited at runtime, so
edit freely: a step's `description:` is passed straight to the agent, and you
can also set `model:`, `backend:`, `backend_args:`, `rubric:`, `timeout_seconds`,
`condition:`, `on_fail:`, add or remove steps, and rewire states.

```yaml
- name: implement
  agent: developer
  trigger: ready-for-dev
  transitions_to: [implemented]
  backend: claude
  model: <model id>
  description: >
    Implement the ticket. This codebase is a Rails monolith — follow the
    service-object pattern in app/services/, never put logic in controllers.
```

Per-step, per-workflow, no indirection. **Start here.** Most of what people
reach for levers 2–4 to do is really a `description:` edit.

The one constraint: if your workflow keeps the family `name:` (e.g.
`name: develop`), the toolkit's **family contract** enforces a minimum shape —
certain states must exist, certain transitions must be declared, `pr-ready`
must stay a human gate. That's a floor, not a ceiling; add whatever you want on
top. Rename the family and the contract stops applying entirely.

### Lever 2 — a config var injected into a shared prompt

For text that belongs to your project but is consumed by a toolkit-owned
prompt or partial. Set it in `toolkit.config.yaml`:

```yaml
context_gathering_steps: |
  Read the repo's agent instructions file (CLAUDE.md, AGENTS.md or similar)
  first — it is the authoritative map.
  Then read the module(s) the ticket names and their tests.
  Do NOT read the whole app/ tree; it is 400 files and mostly irrelevant.
```

The toolkit partial that needs it references `{{wf.context_gathering_steps}}`,
and assemble substitutes your value. **This is the pattern:** the config file
holds the instructions, and they land in the agent's prompt automatically.

You are not limited to the keys in the toolkit's `config.schema.yaml`. Any key you declare
in your own `toolkit.config.yaml` becomes referenceable as `{{wf.that_key}}`
from your own workflows, prompts, and agents.

### Lever 3 — override a whole role prompt

A project plugin may ship no `prompts/` directory, and that isn't an omission: **every
agent role's prompt is inherited from wf-toolkit unless you ship your own.**
Drop in `prompts/developer.md` and yours wins for that role — the toolkit's is
not consulted, not merged, not appended. Ship nothing and you inherit all of
them.

So the progression is: inherit everything → override the one role whose
behaviour you need to change → leave the others alone.

Assemble enforces the other half of this: every agent named by any of your
workflows must resolve to a prompt, yours or the toolkit's. A typo'd agent name
fails assembly rather than silently running a prompt-less agent.

### Lever 4 — override a hook

Toolkit hooks are defaults. Ship `hooks/<same-name>.py` and yours wins. The
toolkit's own `resolve-qa-auth.py` documents this as the intended escape hatch:
a project whose auth needs more than a declarative recipe — minting a token,
seeding a user, refreshing a session — replaces the resolver outright while the
family stays generic.

## `{{wf.var}}` vs `{{wf:include}}`, and the ordering trap

Two different mechanisms, easy to conflate:

| | What it does |
|---|---|
| `{{wf.some_key}}` | substitutes a **value** from `toolkit.config.yaml` (or a dependency's schema default) |
| `{{wf:include wf-toolkit/partials/foo.md}}` | inlines a **file**, recursively, re-indented to the include site's column |

Include paths must start with a known plugin name. Includes are re-indented to
their column, so a multi-line partial stays inside an enclosing YAML block
scalar.

**The trap.** Expansion order is **includes first, then variables**:

```python
VAR_RE.sub(sub_var, INCLUDE_RE.sub(sub_include, text))
```

So a `{{wf:include ...}}` written *inside a config value* never expands — by
the time variables are substituted, the include pass is over, and your literal
`{{wf:include ...}}` string ships to the agent as text. It works the other way
round: a partial may contain `{{wf.vars}}`, and those do expand.

- Config value → prompt: **`{{wf.var}}`**. ✅
- Prompt → shared partial file: **`{{wf:include}}`**. ✅
- Config value that is itself an include: ❌ silently ships as literal text.

Two more expansion facts worth knowing up front:

- **Only `workflows/*.yaml`, `prompts/*.md`, and `agents/*.md` are expanded.**
  `skills/**/SKILL.md` is **not** — a `{{wf.foo}}` in a SKILL.md reaches the
  agent as the literal seven characters. Skills describe mechanism and take
  their values through the prompt. This bites people.
- **An unknown variable is a hard failure**, not an empty string. Assemble
  stops with `unknown variable '{{wf.key}}' — not in toolkit.config.yaml or any
  dependency schema default`. That's a feature: no silently-blank instructions.

## Config vs secrets

`toolkit.config.yaml` is the single source of truth **for configuration** — and
that explicitly includes QA. The schema already carries `qa_applicable`,
`qa_base_url_default`, `qa_auth_method`, `qa_auth_endpoint`,
`qa_auth_personas`, `qa_auth_storage_state`, `qa_auth_user_env`,
`qa_auth_pass_env`. You do not need a separate QA config file. The QA section below walks
through setting them.

What stays out is **secret values**, and the split is load-bearing rather than
stylistic. Config names the env var; the environment holds the value:

```yaml
# toolkit.config.yaml — committed
qa_auth_method: form
qa_auth_user_env: SHOP_QA_USERNAME     # the NAME
qa_auth_pass_env: SHOP_QA_PASSWORD     # the NAME
```

```bash
# <repo>/.workflow/.env — gitignored
SHOP_QA_USERNAME=<the QA user's login>
SHOP_QA_PASSWORD=<written by `wf secret set`, never typed into a chat>
```

The engine hands a run only the `.env` names its workflow declares in `env:`.
The reference `qa.yaml` declares both credential names for you (engine >=
1.2.84); if your project owns its own `qa.yaml`, keep the same two quoted
lines, `"{{wf.qa_auth_user_env}}": ""` and `"{{wf.qa_auth_pass_env}}": ""`, in
its `env:`, or a `form` run fails at `on_init` naming the missing variable.

The toolkit's resolver states the reason plainly: task `context` is written
into task frontmatter, which is read by the dashboard, included in prompts, and
often committed. A resolver that helpfully inlined a password would leak it
three ways. The agent reads the named variable from its own environment at the
moment it needs it.

## Setting up QA

QA is the part with the most moving pieces.
The `qa` family is deliberately **target-agnostic** — it exercises whatever
`context.qa_base_url` points at and authenticates however
`context.qa_auth` says. Two `on_init` resolvers turn your config into those
two values. Everything below is config; you write no code unless your
project needs something the recipes can't express.

### Does QA apply at all?

```yaml
qa_applicable: "true"        # schema default
```

The one distinction worth understanding before anything else, because the
resolver refuses to guess it: **"no target" has two meanings and they must not
share an outcome.**

- **Misconfigured** — the project has a surface and someone forgot to point at
  it. Exits 1, loudly. This is the *default* reading of a missing target, and
  it stays the default: silently skipping QA is worse than failing.
- **Not applicable** — the project has no surface QA could ever exercise (a
  library, a CLI, a hooks repo). Parks on the `qa-not-applicable` **success**
  terminal.

Not-applicable is never inferred from an absence — it's a positive declaration,
`qa_applicable: false`. Say nothing and you get fail-closed behaviour.

⚠️ **If you ever set it false, you must also thread it.** Hooks are not
variable-expanded and cannot read `toolkit.config.yaml`; they only see the
running workflow's `env:` block. The reference `qa.yaml` already threads it —
but if you write your own workflow, drop the line and your declaration becomes
invisible and the task dies at `on_init`.

### Where does QA point?

```yaml
qa_base_url_default: "https://staging.example.com"
```

Precedence, first wins:

1. `context.qa_base_url` already on the task — an operator override for one run
2. `WF_QA_BASE_URL`, threaded from this config key

Leave it blank if your own resolver starts a local server instead.

### How does it log in?

Four methods. Pick with `qa_auth_method`:

| method | needs | for |
|---|---|---|
| `none` *(default)* | — | an open target |
| `form` | `qa_auth_user_env`, `qa_auth_pass_env` | a username/password sign-in form the agent fills |
| `dev-endpoint` | `qa_auth_endpoint` | a dev-only login route that sets the session directly |
| `session` | `qa_auth_storage_state` | a pre-authenticated saved browser session — **the only workable model behind federated SSO**, where an agent cannot complete a third-party OAuth consent flow |

A half-configured method fails at `on_init` with a precise message rather than
letting an agent improvise a login and report a confident false pass.

`dev-endpoint` usually offers several identities, so scenarios pick by role:

```yaml
qa_auth_method: dev-endpoint
qa_auth_endpoint: /__dev/login
qa_auth_personas: "admin=qa-admin,member=qa-member,readonly=qa-readonly"
```

**Names of env vars only, never values** — and this is enforced, not just
advised. The resolver hard-refuses any recipe key called `password`, `passwd`,
`secret`, `token`, or `api_key`, because `context` becomes task frontmatter and
frontmatter reaches the dashboard, the prompts, and git.

### Web or mobile?

The capture surface is inferred from a **pair** of keys, and the inference is
deliberately strict:

```yaml
capture_platform_default: web       # or: mobile
capture_viewport: "1440x900"        # set for web, blank for mobile
capture_devices: ""                 # set for mobile, blank for web
```

Viewport set + devices empty = web. Devices set + viewport empty = mobile. Both
set = ambiguous. **Neither set = the hook says so on stderr** rather than
quietly assuming web — which is the failure a native-mobile project would
otherwise hit at `on_init` with no explanation. If the project is mobile-only,
prune nothing and fill `capture_devices`; if web-only, delete the cloned
`skills/capture-mobile/`.

### When does QA actually run?

This trips people up, because the answer is "later than you'd think."

QA only means something once the merged commits are **live on the target**, and
the deploy happens on external CI time, not workflow time. So `develop` flips a
task into `qa` only after a human approves at `pr-ready` — and the flip is
gated on `context.deploy_confirmed`, which a deploy listener stamps when it
observes the deploy land.

Two consequences worth knowing before you debug a "stuck" task:

- A task sitting in `awaiting-qa` is usually **waiting on a deploy**, not
  broken.
- For work that deploys nowhere, a publish hook assigns the gate up front so
  the task doesn't park for the full timeout and then fail.

### What comes out

`exercise` → `capture` → `review-visual` + `review-e2e` → `report`, landing on
the **`report-ready` checkpoint**. A human approves (→ `done`) or rejects
(→ `changes-requested`). The reporter writes a `wf.memo/1` document the
dashboard's memo tab renders — verdict chips, findings with clickable
`file:line`, screenshots, and any decision questions it wants a human to rule
on.

### When the recipes aren't enough

Ship `hooks/resolve-qa-auth.py` (or `resolve-qa-target.py`) in your plugin and
yours wins over the toolkit's. That's the intended escape hatch for auth that
needs real logic — minting a short-lived token, seeding a user, refreshing a
session before each scenario. The family stays generic; your project keeps full
control.

## Things that will bite you

- **A task must be *armed* to run.** `wf task create` leaves it neither armed
  nor workflow-assigned. Set `workflow:` and run `wf task start <id> -w <ws>` (or `wf cycle arm <cycle-id> -w <ws>` for a whole chain). `wf loop` dispatches armed work only and logs
  `N task(s) actionable but not armed` — half-armed tasks park forever.
- **`transitions_to` is required on every step.** Use `[]` for steps that don't
  change state (reviewers, fetchers). Both load time and run time enforce it,
  which is what stops an agent hallucinating an out-of-vocabulary state and
  wedging the workflow.
- **A state only a hook writes must be declared `external: true`.** Without it nothing in the workflow reaches the state, so the load fails with `ERR_UNREACHABLE_STATE`.
- **macOS and Linux are both first-class.** No `flock(1)`, no `timeout`, no
  `readlink -f`, no `sed -i` — Python is already a hard dependency, use it.
  A scheduler's entry point must be the `wf` binary itself, never a shell
  wrapper (macOS TCC judges the entry-point binary and denies the whole tree).
- **Pilot before you loop.** One real ticket, with a human at every
  checkpoint, before anything runs unattended:
  `wf task create --id <id> --title "<title>" --workflow <name> -w <ws>`, then
  `wf task start <id> -w <ws>`, then `wf task show <id> -w <ws>` once the loop
  has run it.
