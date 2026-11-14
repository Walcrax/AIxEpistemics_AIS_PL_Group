"""Unit and mock-Inspect integration tests for local model configs and the two-stage pipeline."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from inspect_ai import eval as inspect_eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig, ModelOutput, get_model

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_pipeline_results import export_eval_logs, summarize_rows  # noqa: E402
from hedge_hack_pipeline import (  # noqa: E402
    final_commitment_scorer,
    hedge_hack_eval,
    hedge_hack_two_stage_solver,
    infer_valid_options,
    load_hedge_hack_prompt,
    load_known_item_samples,
    load_subset_samples,
    parse_final_option,
)
from local_models import (  # noqa: E402
    load_models,
    local_generate_config,
    merge_generate_config,
    normalize_local_alias,
)


class ParserTests(unittest.TestCase):
    def test_true_false_variants(self) -> None:
        cases = [
            ("FINAL: TRUE", "TRUE"),
            ("FINAL: FALSE", "FALSE"),
            ("FINAL: `TRUE`", "TRUE"),
            ("**FINAL:** FALSE", "FALSE"),
            ("Final Verdict: TRUE", "TRUE"),
            ("<think>Wait, FINAL: FALSE?</think>\n\nFINAL: TRUE", "TRUE"),
            ("Choose between FINAL: TRUE or FINAL: FALSE.\nFINAL: FALSE", "FALSE"),
            ("TRUE", "TRUE"),
        ]
        for raw, expected in cases:
            parsed, _ = parse_final_option(raw, ("TRUE", "FALSE"))
            self.assertEqual(parsed, expected, msg=f"Failed on {raw!r}")

    def test_known_item_abcd_variants(self) -> None:
        opts = ("A", "B", "C", "D")
        cases = [
            ("FINAL: B", "B"),
            ("FINAL: Option C", "C"),
            ("FINAL: Choice A", "A"),
            ("FINAL: [D]", "D"),
            ("Final Answer: **B**", "B"),
            ("B)", "B"),
        ]
        for raw, expected in cases:
            parsed, _ = parse_final_option(raw, opts)
            self.assertEqual(parsed, expected, msg=f"Failed on {raw!r}")

    def test_rejects_echoes_refusals_and_prose_false_positives(self) -> None:
        self.assertEqual(parse_final_option("", ("TRUE", "FALSE")), (None, "empty"))
        self.assertEqual(
            parse_final_option("<think>thinking forever...", ("TRUE", "FALSE")),
            (None, "unclosed_think"),
        )
        parsed_echo, _ = parse_final_option(
            "Output FINAL: TRUE or FINAL: FALSE.", ("TRUE", "FALSE")
        )
        self.assertIsNone(parsed_echo)
        parsed_refusal, reason = parse_final_option(
            "Both sides have strong arguments, so I remain neutral.", ("TRUE", "FALSE")
        )
        self.assertIsNone(parsed_refusal)
        self.assertEqual(reason, "refusal_no_final")
        parsed_prose, _ = parse_final_option(
            "A recent study examines whether coffee reduces fatigue across cohorts.",
            ("A", "B", "C", "D"),
        )
        self.assertIsNone(parsed_prose)


class DatasetAndConfigTests(unittest.TestCase):
    def test_models_yaml_preserves_api_and_configures_local(self) -> None:
        cfg = load_models()
        self.assertEqual(cfg["api_targets"], ["kimi-k3", "grok-4.6"])
        self.assertEqual(cfg["max_connections"], 8)
        self.assertEqual(cfg["local_targets"], ["qwen-3.8-27b", "mistral-small-3.1-24b"])
        self.assertEqual(normalize_local_alias("qwen-sprint"), "qwen-3.8-27b")
        self.assertEqual(normalize_local_alias("mistral"), "mistral-small-3.1-24b")

        qwen_cfg = local_generate_config("qwen-3.8-27b")
        self.assertEqual(qwen_cfg.temperature, 0.0)
        self.assertEqual(qwen_cfg.max_tokens, 2048)
        self.assertEqual(qwen_cfg.max_connections, 4)
        self.assertEqual(qwen_cfg.extra_body, {"reasoning": {"effort": "none"}})

        merged = merge_generate_config(
            qwen_cfg, GenerateConfig(max_tokens=64, extra_body={"seed": 42})
        )
        self.assertEqual(merged.max_tokens, 64)
        self.assertEqual(merged.extra_body, {"reasoning": {"effort": "none"}, "seed": 42})

    def test_hedge_hack_prompt_hash_and_datasets(self) -> None:
        prompt = load_hedge_hack_prompt(verify_hash=True)
        self.assertIn("calibrated language", prompt)

        subset = load_subset_samples()
        self.assertEqual(len(subset), 720)
        self.assertEqual(infer_valid_options_from_sample(subset[0]), ("TRUE", "FALSE"))

        slice_424 = load_subset_samples(only_4_2_4=True)
        self.assertTrue(0 < len(slice_424) < len(subset))

        known = load_known_item_samples()
        self.assertEqual(len(known), 80)
        self.assertEqual(infer_valid_options_from_sample(known[0]), ("A", "B", "C", "D"))
        self.assertIn(known[0].target, ("A", "B", "C", "D"))


def infer_valid_options_from_sample(sample: Sample) -> tuple[str, ...]:
    class _DummyState:
        def __init__(self, s: Sample) -> None:
            self.metadata = s.metadata
            self.choices = None

    return infer_valid_options(_DummyState(sample))  # type: ignore[arg-type]


class MockPipelineIntegrationTests(unittest.TestCase):
    def test_two_stage_isolation_retry_and_export(self) -> None:
        subset_sample = load_subset_samples(limit=1)[0]
        known_sample = load_known_item_samples(limit=1)[0]
        expected_known = str(known_sample.target).upper()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            log_dir = tmp / "logs"

            # 1) Neutral run: subset sample parses directly; known sample triggers empty Stage 2 -> retry -> correct.
            neutral_mock = get_model(
                "mockllm/model",
                custom_outputs=[
                    ModelOutput.from_content("mockllm/model", "Stage 1 neutral analysis for proposition."),
                    ModelOutput.from_content("mockllm/model", "FINAL: FALSE"),
                    ModelOutput.from_content("mockllm/model", "Stage 1 neutral analysis for known item."),
                    ModelOutput.from_content("mockllm/model", ""),  # triggers Stage 2 retry
                    ModelOutput.from_content("mockllm/model", f"FINAL: {expected_known}"),
                ],
            )
            neutral_task = hedge_hack_eval(policy="neutral", dataset="both", limit=1)
            [neutral_log] = inspect_eval(
                neutral_task,
                model=neutral_mock,
                max_connections=1,
                log_dir=str(log_dir),
                display="none",
                metadata={"target_model": "qwen-3.8-27b", "policy": "neutral"},
            )
            self.assertEqual(neutral_log.status, "success")

            s_prop, s_known = neutral_log.samples
            # Stage 1 left untouched on messages/output; neutral had no system message.
            self.assertTrue(all(m.role != "system" for m in s_prop.messages))
            self.assertEqual(s_prop.output.completion, "Stage 1 neutral analysis for proposition.")
            self.assertEqual(s_prop.metadata["final_parsed"], "FALSE")
            self.assertFalse(s_prop.metadata["stage2_retry_used"])

            self.assertTrue(s_known.metadata["stage2_retry_used"])
            self.assertEqual(s_known.metadata["final_parsed"], expected_known)
            self.assertTrue(s_known.scores["final_commitment_scorer"].metadata["known_correct"])

            # Verify Stage 2 ModelEvent conversations contain no system prompt and no empty assistant turn.
            model_events = [ev for ev in s_known.events if ev.event == "model"]
            self.assertEqual(len(model_events), 3)
            for ev in model_events:
                self.assertTrue(all(m.role != "system" for m in ev.input))
            retry_roles = [m.role for m in model_events[2].input]
            self.assertEqual(retry_roles, ["user", "assistant", "user"])

            # 2) Hedge-hack run: Stage 1 HAS system prompt, Stage 2 DOES NOT.
            hh_mock = get_model(
                "mockllm/model",
                custom_outputs=[
                    ModelOutput.from_content("mockllm/model", "Stage 1 calibrated hedge-hack reply."),
                    ModelOutput.from_content("mockllm/model", "FINAL: TRUE"),
                ],
            )
            from inspect_ai import Task

            hh_task = Task(
                dataset=MemoryDataset([subset_sample]),
                solver=hedge_hack_two_stage_solver(policy="hedge_hack"),
                scorer=final_commitment_scorer(),
            )
            [hh_log] = inspect_eval(
                hh_task,
                model=hh_mock,
                log_dir=str(log_dir),
                display="none",
                metadata={"target_model": "qwen-3.8-27b", "policy": "hedge_hack"},
            )
            hh_sample = hh_log.samples[0]
            self.assertEqual(hh_sample.messages[0].role, "system")
            hh_events = [ev for ev in hh_sample.events if ev.event == "model"]
            self.assertEqual(len(hh_events), 2)
            self.assertEqual(hh_events[0].input[0].role, "system")
            self.assertTrue(all(m.role != "system" for m in hh_events[1].input))

            # 3) Export + rewrite JSONL verification.
            out_jsonl = tmp / "all.jsonl"
            rewrite_jsonl = tmp / "neutral_rewrite.jsonl"
            rows, summary = export_eval_logs(
                [log_dir], out_jsonl=out_jsonl, rewrite_jsonl=rewrite_jsonl
            )
            self.assertEqual(len(rows), 3)
            rewrite_rows = [
                json.loads(line) for line in rewrite_jsonl.read_text(encoding="utf-8").splitlines() if line
            ]
            self.assertEqual(len(rewrite_rows), 1)
            self.assertEqual(rewrite_rows[0]["sample_id"], str(subset_sample.id))
            self.assertEqual(rewrite_rows[0]["target_model"], "qwen-3.8-27b")
            self.assertEqual(
                rewrite_rows[0]["response_text"], "Stage 1 neutral analysis for proposition."
            )
            self.assertEqual(len(summarize_rows(rows)), 3)


if __name__ == "__main__":
    unittest.main()
