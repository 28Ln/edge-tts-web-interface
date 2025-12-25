import os
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Ensure project root is on sys.path when running as a script
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import get_config  # noqa: E402
from src.services.ai_service import AIService  # noqa: E402


@dataclass
class RunResult:
    model: str
    ok: bool
    ms: float
    error: str = ""
    answer_preview: str = ""


def _truncate(s: str, n: int = 120) -> str:
    s = (s or "").replace("\r", " ").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 3] + "..."


def _call_once(service: AIService, model: str, question: str, timeout_s: int) -> RunResult:
    start = time.time()
    try:
        messages = [
            {"role": "system", "content": service.get_system_prompt(short=True)},
            {"role": "user", "content": question},
        ]
        resp = service.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
            timeout=timeout_s,
        )
        ans = (resp.choices[0].message.content or "").strip()
        return RunResult(
            model=model,
            ok=True,
            ms=(time.time() - start) * 1000,
            answer_preview=_truncate(ans, 160),
        )
    except Exception as e:
        return RunResult(
            model=model,
            ok=False,
            ms=(time.time() - start) * 1000,
            error=_truncate(repr(e), 200),
        )


def _get_candidates(service: AIService) -> List[str]:
    cfg = get_config()
    return service._get_model_candidates(cfg.ai.model)


def benchmark(question: str, timeout_s: Optional[int] = None) -> Tuple[List[RunResult], Optional[str]]:
    cfg = get_config()
    service = AIService()

    if not service.client:
        raise RuntimeError("AI 未配置：请设置 AI_API_BASE / AI_API_KEY（或对应 .env 配置）")

    timeout_s = int(timeout_s if timeout_s is not None else cfg.ai.timeout)

    candidates = _get_candidates(service)
    results: List[RunResult] = []

    for m in candidates:
        r = _call_once(service, m, question, timeout_s)
        results.append(r)

    ok_results = [r for r in results if r.ok]
    recommended = None
    if ok_results:
        ok_results.sort(key=lambda x: x.ms)
        recommended = ok_results[0].model

    return results, recommended


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage:\n  python scripts/ai_model_benchmark.py \"你好，介绍一下自己\" [timeout_seconds]\n\n")
        print("Env (optional):\n  AI_MODEL_FALLBACKS=deepseek-v3,deepseek-r1-search\n")
        return 2

    question = sys.argv[1]
    timeout_s = int(sys.argv[2]) if len(sys.argv) >= 3 else None

    results, recommended = benchmark(question, timeout_s)

    print("\n=== AI Model Benchmark ===")
    print(f"Question: {_truncate(question, 200)}")
    print("\nResults:")
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"- {r.model:28s} | {status:4s} | {r.ms:8.2f} ms | {r.answer_preview or r.error}")

    print("\nRecommendation:")
    if recommended:
        print(f"- fastest OK model: {recommended}")
        print("\nTo set default quickly (no code change):")
        print(f"- set .env or env var: AI_MODEL_FALLBACKS={recommended}")
        print(f"- or set config default in src/config.py: AIConfig.model='{recommended}'")
    else:
        print("- no model succeeded under current timeout")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
