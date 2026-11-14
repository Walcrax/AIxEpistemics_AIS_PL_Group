"""Swap Pander's credence judges for substitutes served by our endpoint, without editing upstream.

Pander's pinned judges (GPT-5.4-mini 2026-03-17, Gemini 3 Flash preview) are not on our endpoint.
`install()` must run before `credence_scorer()` is built (i.e. before the task is constructed). It
replaces `pander_score.core.scorers.CREDENCE_JUDGES` with `gateway/<alias>` ids carrying the replaced
judge's GenerateConfig, and routes those ids to `api_models.resolve_judge`. Judge ids in the eval logs
read `gateway/judge-openai` / `gateway/judge-google`, so substituted runs are never mistaken for
Pander's. Aliases and the judges they replace: configs/models.yaml `judges`.
"""
import sys
from pathlib import Path

import pander_score.core.scorers as pander_scorers

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_models import load_models, resolve_judge  # noqa: E402

PREFIX = "gateway/"
_original_get_model = pander_scorers.get_model


def _get_model(model_id, *args, config=None, **kwargs):
    if isinstance(model_id, str) and model_id.startswith(PREFIX):
        return resolve_judge(model_id.removeprefix(PREFIX), config)
    return _original_get_model(model_id, *args, config=config, **kwargs)


def install() -> dict:
    if pander_scorers.get_model is _get_model:
        return pander_scorers.CREDENCE_JUDGES
    original = pander_scorers.CREDENCE_JUDGES
    swapped = {f"{PREFIX}{alias}": original[replaces] for alias, replaces in load_models()["judges"].items()}
    if len(swapped) != len(original):
        raise RuntimeError("configs/models.yaml judges must replace every Pander credence judge")
    pander_scorers.CREDENCE_JUDGES = swapped
    pander_scorers.get_model = _get_model
    return swapped
