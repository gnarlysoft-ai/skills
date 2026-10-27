# Workflow composition patterns

The four shapes most workflows are built from. They compose freely.

### 1. Sequential pipeline

```yaml
name: pipeline
steps:
  - name: research
    agent: researcher
    transitions_to: []      # no states: block, so no step changes state
  - name: implement
    agent: developer
    transitions_to: []
    on_fail: research       # in a sequential workflow, a failure jumps back here
  - name: test
    agent: tester
    transitions_to: []
    on_fail: implement
```

### 2. Adversarial review

The `feature` workflow at the top of [workflow-yaml.md](workflow-yaml.md): `implement` (one backend) builds, `review` (another backend) either approves or sends it to `changes-requested`, and `fix` returns it to `implemented` for another review. One run stops after `max_iterations` steps.

**Why it works:** a model reviewing its own work settles for less. A different backend has different blind spots.

### 3. Multi-model consensus

```yaml
name: consensus
states:
  - name: pending
  - name: implemented
  - name: changes-requested
  - name: approved
    terminal: true
steps:
  - name: implement
    agent: developer
    trigger: pending
    transitions_to: [implemented]
  - name: review-claude
    agent: code-reviewer
    trigger: implemented
    parallel_group: review     # same group = run at the same time
    transitions_to: []         # reviewers write findings; they do not move the task
    backend: claude
  - name: review-gemini
    agent: code-reviewer
    trigger: implemented
    parallel_group: review
    transitions_to: []
    backend: gemini
  - name: synthesize           # no trigger: runs after the group, in file order
    agent: synthesizer
    transitions_to: [changes-requested, approved]
    backend: claude
  - name: fix
    agent: developer
    trigger: changes-requested
    transitions_to: [implemented]
```

Reviewers write findings files; only the synthesizer changes the state. The engine waits for every member of a group before it moves on.

### 4. Human checkpoints

```yaml
name: deploy
states:
  - name: pending
  - name: built
    checkpoint: true
    on_approve: deploying
    on_reject: pending
  - name: deploying
  - name: deployed
    terminal: true
steps:
  - name: build
    agent: builder
    trigger: pending
    transitions_to: [built]
  - name: deploy
    agent: deployer
    trigger: deploying
    transitions_to: [deployed]
```

Answer with `wf approve <id> --note "<why>" -w .workflow` (or `--reject`), or the dashboard. `wf approve -w .workflow` with no id lists every task waiting for a person. An answer is refused while the task's step is still running (the step's own write would erase it; retry in a moment), and Approve is refused while a PR in `context.pr_urls` is not merged (`--force` overrides and records it).

The dashboard's Approve and Reject take a note. It is stored as `context.checkpoint_feedback` and shown to later agents as `## Human Feedback`. **It stays on the task** and appears in every later prompt until the next note replaces it, so keep it specific to the gate.
