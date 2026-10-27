# Workflow Engine agent skills

Skills that let your own AI agent work with the Workflow Engine. This
repository holds instructions only; it contains no engine code.

| Skill | Purpose |
|---|---|
| [workflow-engine-setup](skills/workflow-engine-setup/SKILL.md) | Set up the engine on a machine (a fresh Linux dev box or a Mac): install it, create a board for a repository, start its services and prove it with `wf doctor --onboarding` |
| [workflow-engine-author](skills/workflow-engine-author/SKILL.md) | Change how the agents work on a board: customise its project plugin on top of the shared lanes, or add a workflow, and prove it with `wf assemble` before the install and `wf workflow check` and `wf doctor` after |
| [learn-workflow-engine](skills/learn-workflow-engine/SKILL.md) | Run, debug and extend a board once the engine is installed: the mental model, the CLI, the workflow YAML, plugins, hooks, and why a task is not moving |

You can read the setup skill [on GitHub](https://github.com/gnarlysoft-ai/skills/blob/main/skills/workflow-engine-setup/SKILL.md)
or fetch its [raw Markdown](https://raw.githubusercontent.com/gnarlysoft-ai/skills/main/skills/workflow-engine-setup/SKILL.md).

## This repository is a mirror

This repository is a published copy. The skills are maintained in the
Workflow Engine repository and arrive here by pull request when an engine
release changes one. Pull requests opened here by hand are welcome: a
maintainer ports the change to the engine repository and closes the pull
request here. Only the engine's sync pull requests are merged here, and the
next sync overwrites any other change.

## Quickstart

SSH into the machine, start your agent there, and paste this prompt:

> Install the Workflow Engine setup skill. If you're in Claude Code, run
> `claude plugin marketplace add gnarlysoft-ai/skills`, then
> `claude plugin install workflow-engine@gnarlysoft-ai`. If you're in another
> agent, run `npx skills add gnarlysoft-ai/skills --skill workflow-engine-setup`
> and select your agent. Use one installation method. You can read the skill
> directly at https://github.com/gnarlysoft-ai/skills/blob/main/skills/workflow-engine-setup/SKILL.md
> (raw: https://raw.githubusercontent.com/gnarlysoft-ai/skills/main/skills/workflow-engine-setup/SKILL.md).
> Then use the workflow-engine-setup skill to set up the Workflow Engine on
> this machine.

The agent asks before anything that needs `sudo`, never asks you to paste a
secret into the chat, and finishes only when `wf doctor --onboarding` is green
or every remaining item is named with its fix.

## Install

### Claude Code plugin

```bash
claude plugin marketplace add gnarlysoft-ai/skills
claude plugin install workflow-engine@gnarlysoft-ai
```

The plugin carries all three skills. After a restart, Claude Code can also invoke
them explicitly as `/workflow-engine:workflow-engine-setup`, `/workflow-engine:workflow-engine-author` and
`/workflow-engine:learn-workflow-engine`.

### Other agents, via skills.sh

```bash
npx skills add gnarlysoft-ai/skills --skill workflow-engine-setup
npx skills add gnarlysoft-ai/skills --skill workflow-engine-author
npx skills add gnarlysoft-ai/skills --skill learn-workflow-engine
```

Select your agent when prompted. Installation is project-local by default; add
`-g` to install it for your user.
The `skills` CLI needs Node.js 22.20 or newer.

## What you need

- A GitHub account with read access to the Workflow Engine repositories. The
  engine is distributed privately while it is in beta; ask your Workflow
  Engine contact for access.
- A machine you can `sudo` on (Linux) or your own Mac.
- An agent CLI account (Claude Code today) for the board's agents.

## License

The skill text in this repository is [MIT](LICENSE). The Workflow Engine itself
is licensed separately and is not covered by this licence.
