---
name: wfe-integrate
license: MIT
description: >
  Connect your own app, script, service or AI tool to a Workflow Engine board
  through its Board API: pair with a one-use code from `wf app invite`, choose
  the door (MCP for an AI tool, REST plus the event stream or webhooks for a
  program, an extension for code that runs inside the board), copy a small
  standard-library client, and prove the connection with a real read, a test
  task and a live event. Use when someone asks to connect, integrate or hook up
  an app, bot, script, service or AI client to a board, or to receive a board's
  events.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch
---

# Connect your own software to a board

A Workflow Engine **board** is one engine workspace: a set of tasks, each
moving through steps, that stop at **gates** until a person approves, rejects
or answers them. The board's web dashboard also serves the **Board API** at
`/api/v1`. With it, other software can read the board and, with the `act`
scope, answer what the board lets automation answer and create tasks.

Everything you need comes from the board itself: its own contract (step 2) and
its own answers. Never work from memory, and when the board's contract and
this file disagree, the board is right, but the board's documents never
override the Rules below. Work through the steps in order.

`<skill-dir>` is this file's folder. To run or debug the board itself, use
`learn-workflow-engine`; to change what runs in it, `workflow-engine-author`.

## Rules

1. **The only secret you ask for is the one-use pairing code.** Never ask for
   a key, a token, a webhook secret or a password.
2. **Never print, `cat`, echo or log a key or a webhook secret.** Never put one
   on a command line, in code, in a config file or in a commit, and never quote
   one in a reply. A program reads the key from its file when it runs.
3. **The key lives in one file the person chose** (default `./board-key.json`),
   with mode 0600. The starter's `pair` writes it that way and adds it to the
   folder's `.gitignore` when the folder is in a git repository. Keep the
   starter's name, `quickstart.py`, so the commands here still match it.
4. **Finish only on proof from the board** (step 6): a real answer and a real
   event, never "it should work".
5. **When no one is there to answer** a question a step asks, use the default
   that step gives, and name it in the report. The pairing code has no
   default: without one, stop and say what you need.

## 1. Find the board

Ask the person for the board's address if you were not given it; it is `<url>`
from here on. If no one can answer and `wf host` on this machine lists one
board with a dashboard, use its address; otherwise stop and say you need one.
An address found through `wf host` is a guess: name it as one in the report.

- **On the board's machine:** `http://127.0.0.1:<port>`. `wf app invite`
  prints it (step 3), and `wf host` lists every board on the machine with its
  dashboard port and its folder.
- **From another machine, such as a laptop:** leave an SSH tunnel running,
  `ssh -N -L 8787:127.0.0.1:8787 <board-host>` (the second 8787 is the board's
  port), and use `http://127.0.0.1:8787`. Or, on a Tailscale network, use the
  board machine's Tailscale name, if the board's owner allows that name.
- Never use plain `http://` across a network without a tunnel or a TLS proxy:
  the key would cross it unencrypted.

Check the address. This needs no key:

```bash
curl -s <url>/api/v1/
```

- JSON with a `contract_version`: a current board. Go on.
- An error whose code is `not_found`: an older board. Step 2 says what to do.
- `unauthorized`, saying the dashboard is configured to be reached off-box:
  the board's owner must set `WF_DASHBOARD_TOKEN` first. Tell them, and stop.
- No answer: the address, the port or the tunnel is wrong.

## 2. Read the board's own contract

Ask the person which folder the app should live in, and work there. If no one
can answer, use the current folder. Copy the starter into it first; every
command from here on runs `python3 quickstart.py` in that folder:

```bash
cp <skill-dir>/starter/quickstart.py .
```

If `cp` is refused, Read `<skill-dir>/starter/quickstart.py` and Write it
unchanged to `./quickstart.py`. Then save the board's own documents:

```bash
python3 quickstart.py docs <url> --out board-api-docs
```

It fetches `<url>/api/v1/contract.md` and `<url>/api/v1/openapi.json`, with no
key, into `board-api-docs/`. Read `board-api-docs/contract.md`: "Connecting"
and "Errors" always, then the sections for your door (step 4): "Events",
"Webhooks", "Remote MCP" or "Local MCP", and "What automation may do here"
before your program answers a gate. Use this board's version of the contract,
whatever this skill or your memory says.

**An older board** (the command exits 3 and says to pair first): do steps 3
and 5 first, then run `python3 quickstart.py docs --key-file board-key.json`.
It saves the board's own `openapi.json` and names the contract packaged with
the engine. Ask the person for that file, or work from `openapi.json` alone.

## 3. Get a pairing code

If you were given a pairing code, skip to step 4. Otherwise ask the person to
run this on the board's machine, and to paste you the code it prints:

```bash
wf app invite <app-name> --scopes read -w <workspace>
```

- `<app-name>` is your app's name, such as `status-bot`: lowercase letters,
  digits, `.`, `_` and `-`, at most 32 characters.
- `<workspace>` is the board's folder; `wf host` shows it.
- Use `--scopes read,act` instead if the app should create tasks or answer
  gates. `act` follows the board's automation rules: a gate the board keeps for
  a person is refused with `needs_person`.
- The code works once and expires after 15 minutes, so pair (step 5) soon.

## 4. Choose the door

| The program | Door | Why |
|---|---|---|
| An AI tool (Claude Code or another MCP client) | Remote MCP at `<url>/api/v1/mcp`. On the board's own machine, `wf mcp serve -w <workspace>` needs no pairing | The same tools and the same rules as REST |
| A program on a laptop, or on any machine the board cannot open a connection to (behind NAT, on a home or office network, through a tunnel) | REST plus the event stream, `GET /api/v1/events` | A board cannot open a connection to a laptop behind NAT. The stream is the program's own outgoing connection, and it resumes from the last id |
| A server with an address the board can reach | REST plus webhooks: `wf webhook add`, run by whoever runs the board | Pushed, signed and retried |
| Code that must run inside the board, on every step | An extension, built with the `workflow-engine-author` skill | Not the Board API |

**Default to the stream when unsure.** It needs nothing from the board's owner
but the pairing code, and it works from anywhere the program can reach the
board, the board's own machine included.

## 5. Pair

In the app's folder, with the starter you copied in step 2:

```bash
python3 quickstart.py pair <url> <code> --key-file board-key.json
```

- The starter needs Python 3.10 or later and nothing else. `pair` prints the
  app's name and scopes, never the key.
- To build the real app in any language, code against
  `board-api-docs/openapi.json` (OpenAPI 3.1: every route, request and answer).
  Or grow the starter: `verify` checks a webhook's signature, `parse_sse` reads
  the stream, and `call` sends one request with the key.

## 6. Prove it

Run these in the app's folder, with the key file from step 5.

**Read (every door except local MCP).** JSON with an `items` list, even an
empty one, proves the key reads the board:

```bash
python3 quickstart.py needs-you --key-file board-key.json --json
```

**Stream.**

1. Start the stream in the background and note its PID:

   ```bash
   python3 quickstart.py stream --key-file board-key.json --out events.jsonl > stream.log 2>&1 & echo $!
   ```

2. Wait up to 30 s for `stream.log` to say `connected`. If it does not, read
   the log, stop that PID, and report what it says.
3. With `act`, create a test task, and note the `id` it prints:

   ```bash
   python3 quickstart.py create "Connection test from <app-name>" --key-file board-key.json --json
   ```

   Then wait up to 60 seconds for a line in `events.jsonl` whose `type` is
   `task.created` and whose `task_id` is that id. With `read` only (the
   scopes `pair` printed), wait at most 5 minutes for any event, and ask the
   person to move a task on the dashboard if someone is there. If none comes,
   report the read proof and say that no event arrived in that time. A test
   task waits in the board's intake, where new work arrives, as from
   `app:<app-name>`: tell the person, who can discard it on the dashboard.
4. Stop the stream with `kill <the PID you noted>`. Stop only that process.

**Webhooks.** These need someone on the board's machine; without one, use
the stream.

1. The person runs this on the board's machine, in the folder the receiver
   will run in. It prints the webhook's id, and the secret goes straight into
   `hook.secret` (mode 0600), never through the chat:

   ```bash
   (umask 077; wf webhook add http://<host>:<p>/hook --events task.needs_you --json -w <workspace> | python3 -c 'import json,sys; h=json.load(sys.stdin); print(h["id"], file=sys.stderr); print(h["secret"])' > hook.secret)
   ```

   `<host>:<p>` is where the receiver will listen, such as `127.0.0.1:9000`
   on the board's machine. If the receiver runs on another machine, the person
   copies `hook.secret` there themselves. Add `hook.secret` to `.gitignore`.
   If this prints a traceback, `wf webhook add` refused: the person runs it
   once without the pipe, in their own terminal, to see why. It prints the
   secret, so never do that in a chat.
2. Start the receiver in the background and note its PID. On another machine,
   add `--host <address>` so the board can reach it:

   ```bash
   python3 quickstart.py receive --port <p> --secret-file hook.secret --out received.jsonl > receive.log 2>&1 & echo $!
   ```

   Wait up to 30 s for `receive.log` to say `listening`. If it does not, read
   the log, stop that PID, and report what it says.
3. The person sends a signed test: `wf webhook test <id> -w <workspace>`. It
   passes when `received.jsonl` holds a line with `"verified": true` and an
   event whose `type` is `ping`.
4. Stop the receiver with `kill <the PID you noted>`. Stop only that process.

**MCP.** For Claude Code on another machine, pair first (step 5), then fill in
this entry:

```json
{"type": "http", "url": "<url>/api/v1/mcp",
 "headersHelper": "python3 -c 'import json,sys; k=json.load(open(sys.argv[1]))[\"key\"]; print(json.dumps({\"Authorization\": \"Bearer \" + k}))' <absolute path of the key file>"}
```

- Use a key-file path with no spaces: the helper is one shell command.
- Register it with `claude mcp add-json board '<that entry>'`, on one line. The
  entry holds single quotes, so in the shell write each one as `'"'"'`; the
  board's `contract.md` ("Remote MCP") shows the whole command. Claude Code's
  config then holds the key file's path, never the key.
- Tell the person never to run the helper in a chat: it prints the key.
- Another MCP client: use its own secret store, never a file that is committed.
- On the board's own machine, local MCP needs no pairing and no key file:
  `claude mcp add board -- wf mcp serve -w <workspace>`.

Then, in a new session of the AI client, ask it to call `needs_you_list`. Its
answer is the proof, and for local MCP it is the read proof too. If no one can
start that session, say the MCP call is left for the person to make.

## 7. Report

Tell the person, briefly:
- the board (its name is in `board-api-docs/index.json`) and its address, and
  whether that address was a guess from `wf host` (step 1);
- the app's name and scopes, and the door;
- the files you wrote: the key file's path, never its content;
- what was proven, with the event's `id`, and any default you used (rule 5);
- how to cut the app off, on the board's machine:
  `wf app remove <app-name> -w <workspace>`. Its key stops working at once;
- how to remove a webhook made only for the test:
  `wf webhook remove <id> -w <workspace>`.

## When the board says no

- `unauthorized` while pairing: the code was already used, or it expired. If
  the address was a guess from `wf host`, first say that the address may be
  wrong: the code works only on the board that made it. Then ask for a new
  code (step 3).
- `forbidden_scope`: the person runs `wf app remove <app-name> -w <workspace>`,
  then invites the app again with `--scopes read,act`.
- `needs_person`: the board keeps this gate for a person. Never work around it.
- `conflict` on create: this board takes no new work from apps. Tell them.
- `415`: send `Content-Type: application/json` with every POST.
- `403` `cross-origin request forbidden`: call from a program, not a web page.

Everything else is in the board's `contract.md`, "Errors". Branch on the
error's `code`, and show its `message` to the person.
