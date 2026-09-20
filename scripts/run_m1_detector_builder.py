from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dsl.io import dump_json, load_json
from optimizer.m1_detector_builder import (
    DetectorBuilderLLMError,
    build_detector_profile_draft,
    generate_detector_profile_draft_with_llm,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline M1 detector draft generation against an unresolved grounding report.")
    parser.add_argument("--unresolved-report", required=True, help="Path to m1_unresolved_grounding_report.json")
    parser.add_argument("--output", required=True, help="Path to write the resulting detector draft JSON")
    parser.add_argument("--api-base-url", required=True, help="OpenAI-compatible chat completions URL")
    parser.add_argument("--model", default="gpt-5", help="Model name")
    parser.add_argument("--api-key", default="", help="API key. Prefer using --api-key-env.")
    parser.add_argument("--api-key-env", default="FLOWEAVER_LLM_API_KEY", help="Environment variable that holds the API key")
    parser.add_argument("--timeout-s", type=int, default=120, help="HTTP timeout in seconds")
    parser.add_argument(
        "--mode",
        choices=("heuristic", "llm"),
        default="llm",
        help="heuristic: only build the deterministic heuristic draft; llm: call the LLM and normalize its candidate draft",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    unresolved_report = load_json(args.unresolved_report)

    if args.mode == "heuristic":
        draft = build_detector_profile_draft(unresolved_report)
    else:
        api_key = args.api_key or os.environ.get(args.api_key_env, "")
        if not api_key:
            raise DetectorBuilderLLMError(
                f"Missing API key. Pass --api-key or set environment variable {args.api_key_env}."
            )
        draft = generate_detector_profile_draft_with_llm(
            unresolved_report,
            api_base_url=args.api_base_url,
            api_key=api_key,
            model=args.model,
            timeout_s=args.timeout_s,
        )

    dump_json(args.output, draft)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
