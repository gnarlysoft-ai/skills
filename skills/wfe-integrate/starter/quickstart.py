#!/usr/bin/env python3
"""Board API quickstart: pair, list what needs you, receive webhooks, follow the stream.

Python standard library only (3.10+). Copy this file; each command is one short function.

    quickstart.py pair http://127.0.0.1:8787 <code>      # swap a pairing code for a key
    quickstart.py docs http://127.0.0.1:8787             # the board's own contract and OpenAPI, no key
    quickstart.py create "a test task" --key-file F      # one task, to prove the key works
    quickstart.py needs-you                              # what waits for a person
    quickstart.py receive --port 9000 --secret-file s    # signed webhooks, verified
    quickstart.py stream --state-file last-id            # follow events, resume after a drop
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import http.client
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Iterator, Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a 3xx surfaces as an HTTPError: the key never follows it
        return None


# No proxy: the environment's http_proxy would receive the key and the pairing code
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)

MAX_BODY = 1024 * 1024  # a delivery is one thin event; refuse to read more than 1 MiB


# --- webhooks -------------------------------------------------------------

def verify(secret: str, headers: Mapping[str, str], body: bytes, *, now: float | None = None, tolerance: int = 300) -> bool:
    """True only for a delivery the board signed with `secret`, within `tolerance` seconds."""
    got = {k.lower(): v for k, v in headers.items()}
    ts, sig = got.get("x-board-timestamp"), got.get("x-board-signature")
    if ts is None or sig is None or not ts.isascii() or not ts.isdigit() or len(ts) > 12:
        return False
    want = "v1=" + hmac.new(secret.encode(), f"{int(ts)}.".encode() + body, hashlib.sha256).hexdigest()
    ok = abs((time.time() if now is None else now) - int(ts)) <= tolerance
    try:
        return hmac.compare_digest(want.encode(), sig.encode("ascii")) and ok  # bytes: a non-ASCII header cannot raise
    except UnicodeEncodeError:
        return False


def make_server(host: str, port: int, secret: str, out, tolerance: int = 300) -> ThreadingHTTPServer:
    """A receiver that verifies, dedupes by event id (the board delivers at least once) and appends to `out`."""
    seen: set[str] = set()
    lock = threading.Lock()
    if out is not None and os.path.exists(out):  # survive a restart
        with open(out, encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(str(json.loads(line)["event"]["id"]))
                except (ValueError, KeyError, TypeError):
                    pass

    class Handler(BaseHTTPRequestHandler):
        timeout = 10  # a stalled sender must not hold a thread forever

        def reply(self, status: int) -> None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            try:
                size = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self.reply(411)
            if size < 0 or size > MAX_BODY:
                return self.reply(413)
            body = self.rfile.read(size)
            if not verify(secret, self.headers, body, tolerance=tolerance):
                return self.reply(401)  # nothing is written
            try:
                event = json.loads(body)
                event_id = str(event["id"])
            except (ValueError, KeyError, TypeError):
                return self.reply(400)
            with lock:
                if event_id not in seen:
                    line = json.dumps({"verified": True, "event": event}, sort_keys=True) + "\n"
                    if out is None:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    else:
                        with open(out, "a", encoding="utf-8") as f:
                            f.write(line)
                            f.flush()
                            os.fsync(f.fileno())
                    seen.add(event_id)  # only after it is written: a failed write is retried by the board
            self.reply(200)  # a duplicate is answered 200 too, or the board would retry it

        def log_message(self, *args) -> None:  # keep stderr quiet
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


# --- the stream -----------------------------------------------------------

def parse_sse(lines: Iterable[str]) -> Iterator[dict]:
    """Yield {"id", "event", "data"} per frame. Comments (heartbeats) and retry: lines are skipped."""
    frame: dict = {}
    data: list[str] = []
    carried = None  # an id sent without data still counts for Last-Event-ID (SSE); it rides on the next frame
    for line in lines:
        line = line.rstrip("\r\n")
        if line == "":
            if data:
                yield {"id": frame.get("id", carried), "event": frame.get("event"), "data": "\n".join(data)}
                carried = None
            elif "id" in frame:
                carried = frame["id"]
            frame, data = {}, []
        elif line.startswith(":"):
            continue
        else:
            name, _, value = line.partition(":")
            value = value[1:] if value.startswith(" ") else value
            if name == "data":
                data.append(value)
            elif name in ("id", "event"):
                frame[name] = value


# --- talking to the board -------------------------------------------------

def call(key_file: str, path: str, *, timeout: float = 30, payload: dict | None = None):
    """GET (or POST `payload` as JSON) with the key, to the board named in the key file and nowhere else."""
    with open(key_file, encoding="utf-8") as f:
        saved = json.load(f)
    headers = {"Authorization": "Bearer " + saved["key"]}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(saved["board"].rstrip("/") + path, headers=headers, method="GET" if payload is None else "POST",
                                 data=None if payload is None else json.dumps(payload).encode())
    return OPENER.open(req, timeout=timeout)


def error_text(exc: urllib.error.HTTPError) -> str:
    try:
        err = json.loads(exc.read(4096))["error"]
        return f"{exc.code} {err['code']}: {err['message']}" if isinstance(err, dict) else f"{exc.code} {err}"
    except (ValueError, KeyError, TypeError):
        return str(exc.code)


def ignore_in_git(key_file: Path) -> Path | None:
    """Add the key file to its folder's .gitignore when that folder is a git work tree that does not ignore it."""
    name = key_file.name
    try:
        rc = subprocess.run(["git", "-C", str(key_file.parent), "check-ignore", "-q", name],
                            capture_output=True, timeout=30).returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if rc != 1:  # 0: already ignored; 128: not a work tree
        return None
    path = key_file.parent / ".gitignore"
    old = path.read_bytes() if path.exists() else b""
    with path.open("ab") as f:
        f.write((b"\n" if old and not old.endswith(b"\n") else b"") + f"/{name}\n".encode())
    return path


def pair(board: str, code: str, key_file: str) -> None:
    req = urllib.request.Request(
        board.rstrip("/") + "/api/v1/pair", data=json.dumps({"code": code}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")  # the header is required
    with OPENER.open(req, timeout=30) as resp:
        got = json.load(resp)
    saved = {"board": board, "key": got["key"], "name": got["name"], "scopes": got["scopes"]}
    fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)  # also when the file already existed with another mode
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(saved, f)
    print(f"paired as {got['name']} with scopes {','.join(got['scopes'])}; key saved to {key_file}")
    added = ignore_in_git(Path(key_file).absolute())
    if added:
        print(f"added {Path(key_file).name} to {added}, so the key is never committed")


def get_keyless(url: str) -> bytes:
    """The doc routes need no key, so none is sent."""
    with OPENER.open(url, timeout=30) as resp:
        return resp.read()


def docs(board: str | None, key_file: str | None, out: str) -> int:
    """Save the board's own contract and OpenAPI under `out`; returns the exit status."""
    if board is None:
        with open(key_file, encoding="utf-8") as f:
            board = json.load(f)["board"]
    if not board.startswith(("http://", "https://")):
        print("the board url must start with http:// or https://", file=sys.stderr)
        return 2
    base = board.rstrip("/") + "/api/v1/"
    dest = Path(out)
    try:
        raw = get_keyless(base)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        print("this board serves no keyless docs: its engine predates contract 1.3.0")
        if key_file is None:
            print("pair first, then run: docs --key-file <file>")
            return 3
        with call(key_file, "/api/v1/openapi.json") as resp:
            spec = resp.read()
        version = json.loads(spec)["info"]["version"]  # before any write: a malformed answer leaves no files
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "openapi.json").write_bytes(spec)
        print(f"its own OpenAPI document (contract {version}) is {dest / 'openapi.json'}; "
              "for prose, read the contract packaged with the engine on the board's machine: "
              "workflow_engine/board_api/contract.md")
        return 0
    index = json.loads(raw)
    if not isinstance(index, dict):
        print("the board's /api/v1/ did not answer a JSON object", file=sys.stderr)
        return 1
    contract, spec = get_keyless(base + "contract.md"), get_keyless(base + "openapi.json")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.json").write_bytes(raw)
    (dest / "contract.md").write_bytes(contract)
    (dest / "openapi.json").write_bytes(spec)
    print(f"board {index.get('board')}: contract {index.get('contract_version')}; "
          f"its contract is {dest / 'contract.md'}, served by the board")
    return 0


def create(title: str, body: str | None, labels: list[str], key_file: str, as_json: bool) -> None:
    payload: dict = {"title": title}
    if body is not None:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    try:
        with call(key_file, "/api/v1/tasks", payload=payload) as resp:
            got = json.load(resp)
    except urllib.error.HTTPError as exc:
        try:
            err = json.loads(exc.read(4096))["error"]
            sys.exit(f"{err['code']}: {err['message']}")
        except (ValueError, KeyError, TypeError):
            sys.exit(error_text(exc))
    if as_json:
        print(json.dumps(got, indent=2))
    else:
        print(f"created {got['id']} at {got['state']} in {got['workflow']}; "
              f"waits for a person: {'yes' if got['waits_for_person'] else 'no'}")


def needs_you(key_file: str, as_json: bool = False, file=None) -> None:
    with call(key_file, "/api/v1/needs-you") as resp:
        got = json.load(resp)
    if as_json:
        print(json.dumps(got, indent=2), file=file)
    for item in [] if as_json else got["items"]:
        print(f"{item['task_id']}  {item['kind']}  {item['state']}  {item['why']}", file=file)


def stream(key_file: str, after: str | None, state_file: str | None, types: str | None, out: str | None,
           stop: threading.Event | None = None) -> None:
    last = after
    if last is None and state_file and os.path.exists(state_file):
        with open(state_file, encoding="utf-8") as f:
            last = f.read().strip() or None
    sink = open(out, "a", encoding="utf-8") if out else sys.stdout
    delay = 1
    stop = stop or threading.Event()  # only a test sets it; the command runs until interrupted
    while not stop.is_set():
        path = "/api/v1/events" + (f"?types={urllib.parse.quote(types, safe=',')}" if types else "")
        try:
            with open(key_file, encoding="utf-8") as f:
                saved = json.load(f)
            headers = {"Authorization": "Bearer " + saved["key"]}
            if last:
                headers["Last-Event-ID"] = last
            # 60 s read timeout: the board sends a heartbeat about every 15 s, so silence means a dead link
            with OPENER.open(urllib.request.Request(saved["board"].rstrip("/") + path, headers=headers),
                               timeout=60) as resp:
                print("connected", file=sys.stderr, flush=True)
                delay = 1
                for frame in parse_sse(line.decode("utf-8") for line in resp):
                    if frame["event"] == "reset":
                        print(f"reset: {frame['data']}", file=sys.stderr, flush=True)
                        # the log cannot replay what was missed: read the state again (to stderr
                        # when stdout carries the events, so it stays one JSON event per line)
                        needs_you(key_file, file=sys.stdout if out else sys.stderr)
                    else:
                        sink.write(frame["data"] + "\n")
                        sink.flush()
                    if frame["id"]:
                        last = frame["id"]
                        if state_file:  # after the event is handled: a crash replays it, never skips it
                            tmp = state_file + ".tmp"
                            with open(tmp, "w", encoding="utf-8") as f:
                                f.write(last)
                            os.replace(tmp, state_file)
        except urllib.error.HTTPError as exc:
            if exc.code < 500:  # a bad key or id will not mend by retrying
                sys.exit("stream refused: " + error_text(exc))
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:  # IncompleteRead is an HTTPException
            print(f"disconnected ({type(exc).__name__}); retrying in {delay}s", file=sys.stderr, flush=True)
        stop.wait(delay)
        delay = min(delay * 2, 30)


# --- command line ---------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pair", help="swap a pairing code for a key")
    a.add_argument("board_url")
    a.add_argument("code")
    a.add_argument("--key-file", default="board-key.json")
    a = sub.add_parser("docs", help="save the board's own contract and OpenAPI document")
    a.add_argument("board_url", nargs="?")
    a.add_argument("--key-file")
    a.add_argument("--out", default="board-api-docs")
    a = sub.add_parser("create", help="create one task")
    a.add_argument("title")
    a.add_argument("--body")
    a.add_argument("--label", action="append", default=[])
    a.add_argument("--key-file", default="board-key.json")
    a.add_argument("--json", action="store_true")
    a = sub.add_parser("needs-you", help="list what waits for a person")
    a.add_argument("--key-file", default="board-key.json")
    a.add_argument("--json", action="store_true")
    a = sub.add_parser("receive", help="receive signed webhooks")
    a.add_argument("--port", type=int, required=True)
    a.add_argument("--host", default="127.0.0.1")
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--secret")
    g.add_argument("--secret-file", help="keeps the secret out of the process list")
    a.add_argument("--out")
    a.add_argument("--tolerance", type=int, default=300)
    a = sub.add_parser("stream", help="follow the event stream")
    a.add_argument("--key-file", default="board-key.json")
    a.add_argument("--after")
    a.add_argument("--state-file")
    a.add_argument("--types")
    a.add_argument("--out")
    args = p.parse_args(argv)
    try:
        if args.cmd == "pair":
            pair(args.board_url, args.code, args.key_file)
        elif args.cmd == "docs":
            if (args.board_url is None) == (args.key_file is None):
                p.error("docs takes a board url or --key-file")
            code = docs(args.board_url, args.key_file, args.out)
            if code:
                sys.exit(code)
        elif args.cmd == "create":
            create(args.title, args.body, args.label, args.key_file, args.json)
        elif args.cmd == "needs-you":
            needs_you(args.key_file, args.json)
        elif args.cmd == "receive":
            secret = args.secret if args.secret is not None else open(args.secret_file, encoding="utf-8").read().strip()
            server = make_server(args.host, args.port, secret, args.out, args.tolerance)
            print(f"listening on http://{args.host}:{server.server_address[1]}/", flush=True)
            server.serve_forever()
        else:
            stream(args.key_file, args.after, args.state_file, args.types, args.out)
    except urllib.error.HTTPError as exc:
        sys.exit(error_text(exc))
    except (urllib.error.URLError, OSError) as exc:
        sys.exit(f"{type(exc).__name__}: {exc}")
    except (ValueError, KeyError, TypeError) as exc:  # a malformed answer or key file: the type and reason, never a body
        sys.exit(f"{type(exc).__name__}: {exc}")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
