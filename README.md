# Workflow Engine agent skills

Skills that let your own AI agent work with the Workflow Engine. This
repository holds instructions only; it contains no engine code.

| Skill | Purpose |
|---|---|
| [workflow-engine-setup](skills/workflow-engine-setup/SKILL.md) | Set up the engine on a machine (a fresh Linux dev box or a Mac): install it, create a board for a repository, start its services and prove it with `wf doctor --onboarding` |

You can [read SKILL.md on GitHub](https://github.com/gnarlysoft-ai/skills/blob/main/skills/workflow-engine-setup/SKILL.md)
or fetch its [raw Markdown](https://raw.githubusercontent.com/gnarlysoft-ai/skills/main/skills/workflow-engine-setup/SKILL.md).

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

After a restart, Claude Code can also invoke it explicitly as
`/workflow-engine:workflow-engine-setup`.

### Other agents, via skills.sh

```bash
npx skills add gnarlysoft-ai/skills --skill workflow-engine-setup
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
