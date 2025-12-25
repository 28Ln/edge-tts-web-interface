import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import requests


def _url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def _print_kv(title: str, value: Any) -> None:
    print(f"[{title}] {value}")


def _req(
    session: requests.Session,
    method: str,
    url: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    data: Optional[str] = None,
    timeout: float = 15.0,
) -> requests.Response:
    if json_body is not None:
        return session.request(method, url, json=json_body, timeout=timeout)
    if data is not None:
        return session.request(method, url, data=data.encode("utf-8"), timeout=timeout)
    return session.request(method, url, timeout=timeout)


def _test_ping(session: requests.Session, base: str) -> bool:
    url = _url(base, "/mcu/ping")
    t0 = time.time()
    try:
        r = _req(session, "GET", url, timeout=5.0)
    except requests.RequestException as e:
        dt = (time.time() - t0) * 1000
        _print_kv("ping.error", f"{type(e).__name__}: {e}")
        _print_kv("ping.ms", f"{dt:.2f}")
        return False
    dt = (time.time() - t0) * 1000
    _print_kv("ping.status", r.status_code)
    _print_kv("ping.ms", f"{dt:.2f}")
    _print_kv("ping.body", r.text.strip()[:200])
    return r.status_code == 200


def _test_status(session: requests.Session, base: str) -> bool:
    url = _url(base, "/mcu/status")
    t0 = time.time()
    try:
        r = _req(session, "GET", url, timeout=10.0)
    except requests.RequestException as e:
        dt = (time.time() - t0) * 1000
        _print_kv("status.error", f"{type(e).__name__}: {e}")
        _print_kv("status.ms", f"{dt:.2f}")
        return False
    dt = (time.time() - t0) * 1000
    _print_kv("status.status", r.status_code)
    _print_kv("status.ms", f"{dt:.2f}")
    _print_kv("status.body", r.text.strip()[:400])
    return r.status_code == 200


def _test_ask(session: requests.Session, base: str, question: str) -> bool:
    url = _url(base, "/mcu/ask")
    t0 = time.time()
    try:
        r = _req(session, "POST", url, json_body={"question": question}, timeout=40.0)
    except requests.RequestException as e:
        dt = (time.time() - t0) * 1000
        _print_kv("ask.error", f"{type(e).__name__}: {e}")
        _print_kv("ask.ms", f"{dt:.2f}")
        return False
    dt = (time.time() - t0) * 1000
    _print_kv("ask.status", r.status_code)
    _print_kv("ask.ms", f"{dt:.2f}")
    _print_kv("ask.body", r.text.strip()[:400])
    return r.status_code == 200


def _save_file(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def _test_tts(session: requests.Session, base: str, text: str, voice: str, fmt: str, out: str) -> bool:
    url = _url(base, "/mcu/tts")
    t0 = time.time()
    try:
        r = session.post(url, json={"text": text, "voice": voice, "format": fmt}, timeout=120.0)
    except requests.RequestException as e:
        dt = (time.time() - t0) * 1000
        _print_kv("tts.error", f"{type(e).__name__}: {e}")
        _print_kv("tts.ms", f"{dt:.2f}")
        return False
    dt = (time.time() - t0) * 1000
    _print_kv("tts.status", r.status_code)
    _print_kv("tts.ms", f"{dt:.2f}")
    _print_kv("tts.content_type", r.headers.get("Content-Type"))
    _print_kv("tts.bytes", len(r.content))
    if r.status_code == 200 and r.content:
        _save_file(out, r.content)
        _print_kv("tts.saved", out)
        return True
    _print_kv("tts.body", r.text.strip()[:400])
    return False


def _test_ask_tts(session: requests.Session, base: str, question: str, voice: str, fmt: str, out: str) -> bool:
    url = _url(base, "/mcu/ask_tts")
    t0 = time.time()
    try:
        r = session.post(url, json={"question": question, "voice": voice, "format": fmt}, timeout=180.0)
    except requests.RequestException as e:
        dt = (time.time() - t0) * 1000
        _print_kv("ask_tts.error", f"{type(e).__name__}: {e}")
        _print_kv("ask_tts.ms", f"{dt:.2f}")
        return False
    dt = (time.time() - t0) * 1000
    _print_kv("ask_tts.status", r.status_code)
    _print_kv("ask_tts.ms", f"{dt:.2f}")
    _print_kv("ask_tts.content_type", r.headers.get("Content-Type"))
    _print_kv("ask_tts.bytes", len(r.content))
    if r.status_code == 200 and r.content:
        _save_file(out, r.content)
        _print_kv("ask_tts.saved", out)
        return True
    _print_kv("ask_tts.body", r.text.strip()[:400])
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="MCU API smoke test for Edge TTS Web Interface")
    p.add_argument("--host", default="127.0.0.1", help="Host of backend")
    p.add_argument("--port", default="3003", help="Port of backend")
    p.add_argument("--http", default="http", choices=["http", "https"], help="Scheme")
    p.add_argument("--question", default="你好，介绍一下你自己。", help="Question for /mcu/ask and /mcu/ask_tts")
    p.add_argument("--voice", default="xiaoxiao", help="Voice for TTS")
    p.add_argument("--format", default="wav", choices=["wav", "mp3"], help="Audio format")
    p.add_argument("--out-dir", default="data\\test_out", help="Directory to save audio")
    args = p.parse_args()

    base = f"{args.http}://{args.host}:{args.port}"
    print(f"base={base}")

    session = requests.Session()
    session.trust_env = False  # avoid proxy env breaking local/lan calls

    ok = True
    ok = _test_ping(session, base) and ok
    ok = _test_status(session, base) and ok

    ok = _test_ask(session, base, args.question) and ok

    tts_out = os.path.join(args.out_dir, f"tts.{args.format}")
    ok = _test_tts(session, base, "这是一段 TTS 测试语音。", args.voice, args.format, tts_out) and ok

    ask_tts_out = os.path.join(args.out_dir, f"ask_tts.{args.format}")
    ok = _test_ask_tts(session, base, args.question, args.voice, args.format, ask_tts_out) and ok

    print("result=PASS" if ok else "result=FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
