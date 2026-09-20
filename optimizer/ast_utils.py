from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple


@dataclass
class StatementRecord:
    node_id: str
    file_path: str
    function_name: str
    line_start: int
    line_end: int
    col_start: int
    col_end: int
    stmt_kind: str
    raw_repr: str
    defs: Set[str]
    uses: Set[str]
    effects: Set[str]
    block_depth: int = 0
    ordinal: str = ""
    parent_ordinal: str = ""
    parent_block: str = ""


def parse_python_file(path: str | Path) -> Optional[ast.AST]:
    source = Path(path).read_text(encoding="utf-8", errors="ignore")
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def iter_function_nodes(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _call_attr_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _collect_defs_uses(stmt: ast.stmt) -> Tuple[Set[str], Set[str]]:
    defs: Set[str] = set()
    uses: Set[str] = set()

    for node in ast.walk(stmt):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                defs.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                uses.add(node.id)

    return defs, uses


def _collect_effects(stmt: ast.stmt) -> Set[str]:
    effects: Set[str] = set()
    for node in ast.walk(stmt):
        if isinstance(node, ast.Call):
            attr = _call_attr_name(node)
            if attr in {"async_write_ha_state", "schedule_update_ha_state"}:
                effects.add("state_write")
            elif attr in {"dispatcher_connect", "add_listener", "async_track_state_change_event"}:
                effects.add("subscribe")
            elif attr in {"unsubscribe", "unsub"}:
                effects.add("unsubscribe")
            elif attr in {"connect", "disconnect", "read_gatt_char", "write_gatt_char"}:
                effects.add("external_call_ble")
            elif attr in {"get", "post", "request", "call_api"}:
                effects.add("external_call_cloud")
    return effects


def _child_statement_blocks(stmt: ast.stmt) -> List[Tuple[str, List[ast.stmt]]]:
    blocks: List[Tuple[str, List[ast.stmt]]] = []
    for attr in ("body", "orelse", "finalbody"):
        value = getattr(stmt, attr, None)
        if isinstance(value, list) and value and all(isinstance(item, ast.stmt) for item in value):
            blocks.append((attr, value))

    handlers = getattr(stmt, "handlers", None)
    if isinstance(handlers, list):
        for handler in handlers:
            body = getattr(handler, "body", None)
            if isinstance(body, list) and body and all(isinstance(item, ast.stmt) for item in body):
                blocks.append(("except", body))

    cases = getattr(stmt, "cases", None)
    if isinstance(cases, list):
        for case in cases:
            body = getattr(case, "body", None)
            if isinstance(body, list) and body and all(isinstance(item, ast.stmt) for item in body):
                blocks.append(("case", body))

    return blocks


def _iter_nested_statements(
    stmts: List[ast.stmt],
    prefix: str = "",
    depth: int = 0,
    parent_ordinal: str = "",
    parent_block: str = "body",
) -> Iterator[Tuple[ast.stmt, str, int, str, str]]:
    for idx, stmt in enumerate(stmts):
        ordinal = f"{prefix}.{idx}" if prefix else str(idx)
        yield stmt, ordinal, depth, parent_ordinal, parent_block

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        for block_label, block in _child_statement_blocks(stmt):
            yield from _iter_nested_statements(
                block,
                prefix=ordinal,
                depth=depth + 1,
                parent_ordinal=ordinal,
                parent_block=block_label,
            )


def extract_statement_records(path: str | Path) -> List[StatementRecord]:
    file_path = str(Path(path))
    file_sig = hashlib.sha1(file_path.encode("utf-8")).hexdigest()[:8]
    tree = parse_python_file(path)
    if tree is None:
        return []

    records: List[StatementRecord] = []
    for fn in iter_function_nodes(tree):
        for stmt, ordinal, block_depth, parent_ordinal, parent_block in _iter_nested_statements(list(fn.body)):
            line_start = getattr(stmt, "lineno", 0)
            line_end = getattr(stmt, "end_lineno", line_start)
            col_start = getattr(stmt, "col_offset", 0)
            col_end = getattr(stmt, "end_col_offset", col_start)
            defs, uses = _collect_defs_uses(stmt)
            effects = _collect_effects(stmt)
            node_id = f"{file_sig}:{fn.name}:{ordinal}:{line_start}"
            records.append(
                StatementRecord(
                    node_id=node_id,
                    file_path=file_path,
                    function_name=fn.name,
                    line_start=line_start,
                    line_end=line_end,
                    col_start=col_start,
                    col_end=col_end,
                    stmt_kind=stmt.__class__.__name__,
                    raw_repr=ast.dump(stmt, annotate_fields=False),
                    defs=defs,
                    uses=uses,
                    effects=effects,
                    block_depth=block_depth,
                    ordinal=ordinal,
                    parent_ordinal=parent_ordinal,
                    parent_block=parent_block,
                )
            )

    return records


def collect_function_ranges(path: str | Path) -> Dict[str, Tuple[int, int]]:
    tree = parse_python_file(path)
    if tree is None:
        return {}
    ranges: Dict[str, Tuple[int, int]] = {}
    for fn in iter_function_nodes(tree):
        ranges[fn.name] = (getattr(fn, "lineno", 0), getattr(fn, "end_lineno", getattr(fn, "lineno", 0)))
    return ranges


def call_attributes_in_stmt(stmt: ast.stmt) -> List[str]:
    attrs: List[str] = []
    for node in ast.walk(stmt):
        if isinstance(node, ast.Call):
            name = _call_attr_name(node)
            if name:
                attrs.append(name)
    return attrs


def iter_statements_by_function(tree: ast.AST) -> Iterable[Tuple[str, List[ast.stmt]]]:
    for fn in iter_function_nodes(tree):
        yield fn.name, list(fn.body)
