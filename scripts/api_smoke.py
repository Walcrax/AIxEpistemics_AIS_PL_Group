"""One short call per API target. Costs well under $0.05.

uv run --project external/pander-score python -I scripts/api_smoke.py [model ...]
"""
import asyncio, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_models import load_models, resolve_model  # noqa: E402


async def main(names: list[str]) -> None:
    for name in names:
        out = await resolve_model(name).generate("Reply with exactly: OK", cache=False)
        u = out.usage
        print(f"{name:10s} {out.completion.strip()[:20]!r} "
              f"(in {u.input_tokens}, out {u.output_tokens}, reasoning {u.reasoning_tokens})")


asyncio.run(main(sys.argv[1:] or list(load_models()["api_targets"])))
