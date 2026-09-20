from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from dsl.contracts import ExecutionPlan, MSSU
from dsl.io import dump_json


@dataclass
class ReassemblyArtifact:
    wrapper_module_path: str
    patch_manifest_path: str


class CodeReassembler:
    def __init__(self, out_dir: str | Path) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _function_locations(source_path: str | Path) -> Dict[str, int]:
        tree = ast.parse(Path(source_path).read_text(encoding="utf-8", errors="ignore"))
        locations: Dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                locations[node.name] = getattr(node, "lineno", 0)
        return locations

    def _render_wrapper_code(self, module_name: str, mssus: List[MSSU], plan: ExecutionPlan) -> str:
        lines: List[str] = []
        lines.append("from __future__ import annotations")
        lines.append("")
        lines.append(f"import {module_name} as origin")
        lines.append("")
        lines.append("class FloWeaverExecutor:")
        lines.append("    def __init__(self, scheduler, handlers):")
        lines.append("        self.scheduler = scheduler")
        lines.append("        self.handlers = handlers")
        lines.append("")
        lines.append("    async def execute_plan(self, ctx, plan):")
        lines.append("        for batch in plan.ordered_batches:")
        lines.append("            tasks = []")
        lines.append("            for group in batch.parallel_groups:")
        lines.append("                for mssu_id in group:")
        lines.append("                    handler = self.handlers.get(mssu_id)")
        lines.append("                    if handler is None:")
        lines.append("                        continue")
        lines.append("                    tasks.append(handler(ctx))")
        lines.append("            if tasks:")
        lines.append("                for task in tasks:")
        lines.append("                    await task")
        lines.append("")
        lines.append("def build_default_handlers():")
        lines.append("    handlers = {}")
        for mssu in mssus:
            lines.append(f"    async def _{mssu.mssu_id}(ctx):")
            lines.append("        return None")
            lines.append(f"    handlers['{mssu.mssu_id}'] = _{mssu.mssu_id}")
        lines.append("    return handlers")
        lines.append("")
        lines.append("def get_plan_meta():")
        lines.append(f"    return {plan.meta!r}")
        lines.append("")
        return "\n".join(lines) + "\n"

    def reassemble(
        self,
        source_path: str | Path,
        mssus: List[MSSU],
        plan: ExecutionPlan,
        module_name: str,
    ) -> ReassemblyArtifact:
        source_path = str(source_path)
        locations = self._function_locations(source_path)

        wrapper_name = f"{Path(source_path).stem}_floweaver_wrapper.py"
        wrapper_path = self.out_dir / wrapper_name
        wrapper_path.write_text(self._render_wrapper_code(module_name, mssus, plan), encoding="utf-8")

        manifest = {
            "source_path": source_path,
            "wrapper_module": str(wrapper_path),
            "injection_points": {
                "setup": locations.get("async_setup_entry", 0),
                "runtime": locations.get("async_update", locations.get("_async_update_data", 0)),
                "teardown": locations.get("async_unload_entry", 0),
            },
            "mssu_ids": [mssu.mssu_id for mssu in mssus],
            "note": "Sidecar wrapper and patch manifest; handlers require source bindings.",
        }
        manifest_path = self.out_dir / f"{Path(source_path).stem}_patch_manifest.json"
        dump_json(manifest_path, manifest)

        return ReassemblyArtifact(
            wrapper_module_path=str(wrapper_path),
            patch_manifest_path=str(manifest_path),
        )
