from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib import error, request

from dsl.contracts import CodeEvidence, MarkerStrength, Phase, Rule, RuleStatus
from dsl.io import dump_json
from profile_builder.evidence import EvidenceBank


DISCOVERY_REQUEST_SCHEMA = "profile_builder_llm_discovery/request/v1"
DISCOVERY_RESPONSE_SCHEMA = "profile_builder_llm_discovery/response/v1"
VERIFICATION_SCHEMA = "profile_builder_llm_discovery/verification/v1"
SYNTHETIC_EXTRACTOR_VERSION = "profile_builder_llm_discovery/v1"

LLMDiscoveryAdapter = Callable[[Dict[str, Any]], Any]

_MIN_CONFIDENCE = 0.55
_MAX_SOURCE_REFS_PER_CANDIDATE = 6
_MAX_PAYLOAD_FUNCTIONS = 160
_MAX_PAYLOAD_EVIDENCE = 120

_BASE_MARKER_TYPES = {
    "ENTRY_SETUP",
    "ENTRY_UNLOAD",
    "STATE_WRITE",
    "COORD_REFRESH",
    "SUBSCRIBE",
    "UNSUBSCRIBE",
    "BLE_OP",
    "CLOUD_OP",
}

_PROTOCOL_MARKER_TYPES = {
    "BLE_CONNECT",
    "BLE_DISCONNECT",
    "BLE_GATT_OP",
    "BLE_SCAN",
    "BLE_RETRY_OR_TIMEOUT",
    "CLOUD_HTTP_CALL",
    "CLOUD_TOKEN_REFRESH",
    "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP",
    "CLOUD_SESSION_REUSE",
    "CLOUD_BATCH_CALL",
    "LOCAL_API_READ",
}

_GROUNDING_FAMILY_TYPES = _PROTOCOL_MARKER_TYPES | {
    "BLE_OP",
    "CLOUD_OP",
    "CLOUD_STATUS_CALL",
    "LOCAL_API_READ",
    "MQTT_READ",
}

_MARKER_TYPES = _BASE_MARKER_TYPES | _PROTOCOL_MARKER_TYPES

_BLE_CONTEXT_TOKENS = {
    "airthings_ble",
    "advertisement",
    "ble",
    "bleak",
    "bledevice",
    "bluetooth",
    "gatt",
    "scanner",
    "sensorpush",
    "xiaomi_ble",
}

_CLOUD_CONTEXT_TOKENS = {
    "429",
    "access_token",
    "aiohttp",
    "api.",
    "api/",
    "backoff",
    "cloud",
    "httpx",
    "https://",
    "oauth",
    "rate",
    "refresh_token",
    "requests",
    "retry_after",
    "token",
}

_LOCAL_CONTEXT_TOKENS = {
    "aiohttp",
    "bridge",
    "endpoint",
    "host",
    "http",
    "lan",
    "local",
    "websocket",
    "ws",
    "zeroconf",
}

_SUPPORTED_CANDIDATE_KINDS = {
    "runtime_carrier",
    "marker_detector",
    "rule_candidate",
    "test_behavior",
}


class LLMDiscoveryError(RuntimeError):
    pass


@dataclass
class FunctionIndexEntry:
    path: str
    rel_path: str
    integration: str
    name: str
    qualname: str
    line_start: int
    line_end: int
    is_async: bool
    call_attrs: Set[str] = field(default_factory=set)
    call_tokens: Set[str] = field(default_factory=set)
    imported_modules: Set[str] = field(default_factory=set)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "path": self.rel_path,
            "integration": self.integration,
            "name": self.name,
            "qualname": self.qualname,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "is_async": self.is_async,
            "call_attrs": sorted(self.call_attrs)[:24],
            "imported_modules": sorted(self.imported_modules)[:16],
        }


@dataclass
class FileIndexEntry:
    path: str
    rel_path: str
    root_kind: str
    integration: str
    line_count: int
    imported_modules: Set[str] = field(default_factory=set)
    call_attrs: Set[str] = field(default_factory=set)
    call_tokens: Set[str] = field(default_factory=set)
    function_qualnames: Set[str] = field(default_factory=set)
    text_lower: str = ""
    manifest_iot_class: str | None = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "path": self.rel_path,
            "root_kind": self.root_kind,
            "integration": self.integration,
            "manifest_iot_class": self.manifest_iot_class,
            "line_count": self.line_count,
            "imported_modules": sorted(self.imported_modules)[:16],
            "call_attrs": sorted(self.call_attrs)[:24],
            "function_qualnames": sorted(self.function_qualnames)[:20],
        }


@dataclass
class StaticIndex:
    repo_root: Path
    tests_root: Path | None
    files: Dict[str, FileIndexEntry] = field(default_factory=dict)
    functions: List[FunctionIndexEntry] = field(default_factory=list)

    def file_by_path(self, path: Path) -> FileIndexEntry | None:
        return self.files.get(str(path.resolve()))


@dataclass
class VerifiedCandidate:
    row: Dict[str, Any]
    candidate_id: str
    kind: str
    marker_type: str
    protocol_family: str
    integration: str
    confidence: float
    match: Dict[str, Any]
    source_refs: List[Dict[str, Any]]
    existing_evidence_ids: List[str]
    synthetic_evidence: List[CodeEvidence]
    notes: List[str] = field(default_factory=list)

    @property
    def all_evidence_ids(self) -> List[str]:
        return list(dict.fromkeys(self.existing_evidence_ids + [item.evidence_id for item in self.synthetic_evidence]))


@dataclass
class LLMDiscoveryResult:
    request_payload: Dict[str, Any]
    raw_response: Any
    verified: List[VerifiedCandidate]
    rejected: List[Dict[str, Any]]
    marker_detectors: List[Dict[str, Any]]
    rule_candidates: List[Rule]
    grounding_profiles: Dict[str, Dict[str, Any]]
    synthetic_evidence: List[CodeEvidence]
    summary: Dict[str, Any]

    def verification_report(self) -> Dict[str, Any]:
        return {
            "schema_version": VERIFICATION_SCHEMA,
            "summary": self.summary,
            "verified": [
                {
                    "candidate_id": item.candidate_id,
                    "kind": item.kind,
                    "marker_type": item.marker_type,
                    "protocol_family": item.protocol_family,
                    "integration": item.integration,
                    "confidence": item.confidence,
                    "source_refs": item.source_refs,
                    "evidence_ids": item.all_evidence_ids,
                    "notes": item.notes,
                }
                for item in self.verified
            ],
            "rejected": self.rejected,
        }


def _sha1_json(value: Any, size: int = 12) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:size]


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _candidate_integration_from_rel(rel_path: str) -> str:
    parts = [part for part in Path(rel_path).parts if part not in {"", "."}]
    if len(parts) >= 2:
        return parts[0].lower()
    if parts:
        return Path(parts[0]).stem.lower()
    return ""


def _manifest_iot_class(repo_root: Path, integration: str) -> str | None:
    if not integration:
        return None
    path = repo_root / integration / "manifest.json"
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = raw.get("iot_class")
    return str(value).strip().lower() if isinstance(value, str) and value.strip() else None


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Subscript):
        return _call_name(node.value)
    return ""


def _call_tokens_from_name(name: str) -> Set[str]:
    out: Set[str] = set()
    for token in str(name).replace(":", ".").split("."):
        token = token.strip().lower()
        if token:
            out.add(token)
    full = str(name).strip().lower()
    if full:
        out.add(full)
    return out


def _collect_imports(tree: ast.AST) -> Set[str]:
    imports: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.strip().lower()
                if name:
                    imports.add(name.split(".", 1)[0])
                    imports.add(name)
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "").strip().lower()
            if module:
                imports.add(module.split(".", 1)[0])
                imports.add(module)
    return imports


def _collect_calls(node: ast.AST) -> Tuple[Set[str], Set[str]]:
    attrs: Set[str] = set()
    tokens: Set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        name = _call_name(child.func)
        if not name:
            continue
        child_tokens = _call_tokens_from_name(name)
        tokens |= child_tokens
        leaf = name.rsplit(".", 1)[-1].strip().lower()
        if leaf:
            attrs.add(leaf)
    return attrs, tokens


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, *, path: Path, rel_path: str, integration: str, imported_modules: Set[str]) -> None:
        self.path = path
        self.rel_path = rel_path
        self.integration = integration
        self.imported_modules = imported_modules
        self.stack: List[str] = []
        self.functions: List[FunctionIndexEntry] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._record_function(node, is_async=False)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._record_function(node, is_async=True)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool) -> None:
        call_attrs, call_tokens = _collect_calls(node)
        qualname = ".".join([*self.stack, node.name]) if self.stack else node.name
        self.functions.append(
            FunctionIndexEntry(
                path=str(self.path.resolve()),
                rel_path=self.rel_path,
                integration=self.integration,
                name=node.name,
                qualname=qualname,
                line_start=int(getattr(node, "lineno", 1) or 1),
                line_end=int(getattr(node, "end_lineno", getattr(node, "lineno", 1)) or 1),
                is_async=is_async,
                call_attrs=call_attrs,
                call_tokens=call_tokens,
                imported_modules=set(self.imported_modules),
            )
        )


def _iter_python_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (
        path
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts and ".venv" not in path.parts and path.is_file()
    )


def build_static_index(repo_root: str | Path, tests_root: str | Path | None = None) -> StaticIndex:


    repo = Path(repo_root)
    tests = Path(tests_root) if tests_root else None
    index = StaticIndex(repo_root=repo, tests_root=tests)

    roots: List[Tuple[str, Path]] = [("repo", repo)]
    if tests:
        roots.append(("tests", tests))

    for root_kind, root in roots:
        for path in _iter_python_files(root):
            try:
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text, filename=str(path))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            rel_path = _safe_rel(path, root)
            integration = _candidate_integration_from_rel(rel_path)
            imports = _collect_imports(tree)
            call_attrs, call_tokens = _collect_calls(tree)
            collector = _FunctionCollector(
                path=path,
                rel_path=rel_path,
                integration=integration,
                imported_modules=imports,
            )
            collector.visit(tree)
            manifest_iot = _manifest_iot_class(repo, integration) if root_kind == "repo" else None
            file_entry = FileIndexEntry(
                path=str(path.resolve()),
                rel_path=rel_path,
                root_kind=root_kind,
                integration=integration,
                line_count=max(1, len(text.splitlines())),
                imported_modules=imports,
                call_attrs=call_attrs,
                call_tokens=call_tokens,
                function_qualnames={fn.qualname for fn in collector.functions},
                text_lower=text.lower(),
                manifest_iot_class=manifest_iot,
            )
            index.files[file_entry.path] = file_entry
            index.functions.extend(collector.functions)
    return index


def build_discovery_payload(bank: EvidenceBank, index: StaticIndex) -> Dict[str, Any]:
    evidence_rows: List[Dict[str, Any]] = []
    for evidence_id, row in sorted(bank.by_id().items()):
        compact = {
            "evidence_id": evidence_id,
            "kind": row.get("kind"),
            "source_path": row.get("source_path"),
            "line_no": row.get("line_no"),
            "pattern": row.get("pattern"),
            "typed_anchor": row.get("typed_anchor"),
            "effective_typed_anchor": row.get("effective_typed_anchor"),
            "protocol_hypothesis": row.get("protocol_hypothesis"),
            "semantic_anchor": row.get("semantic_anchor"),
        }
        evidence_rows.append({k: v for k, v in compact.items() if v not in (None, "", [])})
        if len(evidence_rows) >= _MAX_PAYLOAD_EVIDENCE:
            break

    functions = sorted(
        index.functions,
        key=lambda item: (
            item.integration,
            item.rel_path,
            -len(item.call_attrs),
            item.qualname,
        ),
    )[:_MAX_PAYLOAD_FUNCTIONS]

    files = sorted(
        index.files.values(),
        key=lambda item: (item.integration, item.root_kind, item.rel_path),
    )[:_MAX_PAYLOAD_FUNCTIONS]

    return {
        "schema_version": DISCOVERY_REQUEST_SCHEMA,
        "task": "Propose candidate HA runtime carriers, marker detectors, and profile rules. Every candidate must include concrete source_refs or existing evidence_ids.",
        "candidate_contract": {
            "allowed_kinds": sorted(_SUPPORTED_CANDIDATE_KINDS),
            "allowed_marker_types": sorted(_MARKER_TYPES),
            "required_grounding": "source_refs with repo/test path + line, or evidence_ids from evidence_summary",
            "response_shape": {
                "schema_version": DISCOVERY_RESPONSE_SCHEMA,
                "candidates": [
                    {
                        "kind": "runtime_carrier|marker_detector|rule_candidate|test_behavior",
                        "marker_type": "one allowed marker type",
                        "protocol_family": "BLE|CLOUD|LOCAL_API|HA",
                        "integration": "optional integration name",
                        "symbol": "optional function or class.method",
                        "match": {"call_attrs": [], "function_names": [], "module_hints": []},
                        "source_refs": [{"path": "repo relative path", "line": 1}],
                        "evidence_ids": [],
                        "confidence": 0.0,
                    }
                ],
            },
        },
        "evidence_summary": evidence_rows,
        "file_index": [item.to_payload() for item in files],
        "function_index": [item.to_payload() for item in functions],
    }


def _normalize_response_candidates(raw_response: Any) -> List[Dict[str, Any]]:
    if raw_response is None:
        return []
    if isinstance(raw_response, list):
        return [dict(item) for item in raw_response if isinstance(item, dict)]
    if not isinstance(raw_response, dict):
        return []
    rows: List[Dict[str, Any]] = []
    candidates = raw_response.get("candidates", [])
    if isinstance(candidates, list):
        rows.extend(dict(item) for item in candidates if isinstance(item, dict))
    section_kinds = {
        "runtime_carriers": "runtime_carrier",
        "marker_detectors": "marker_detector",
        "rule_candidates": "rule_candidate",
        "test_behaviors": "test_behavior",
    }
    for section, kind in section_kinds.items():
        values = raw_response.get(section, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row.setdefault("kind", kind)
            rows.append(row)
    return rows


def _normalize_string_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw_values = [raw]
    elif isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray)):
        raw_values = list(raw)
    else:
        raw_values = [raw]
    out: List[str] = []
    seen: Set[str] = set()
    for item in raw_values:
        token = str(item or "").strip()
        if not token:
            continue
        lower = token.lower()
        if lower in seen:
            continue
        seen.add(lower)
        out.append(token)
    return out


def _normalized_match(row: Dict[str, Any]) -> Dict[str, Any]:
    raw = row.get("match", {}) if isinstance(row.get("match", {}), dict) else {}
    return {
        "call_attrs": [item.lower() for item in _normalize_string_list(raw.get("call_attrs", row.get("call_attrs", [])))],
        "function_names": _normalize_string_list(raw.get("function_names", row.get("function_names", []))),
        "module_hints": [item.lower() for item in _normalize_string_list(raw.get("module_hints", row.get("module_hints", [])))],
        "file_globs": _normalize_string_list(raw.get("file_globs", row.get("file_globs", []))),
    }


def _source_refs_from_row(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    raw_refs = row.get("source_refs", row.get("sources", []))
    if isinstance(raw_refs, dict):
        raw_refs = [raw_refs]
    if not isinstance(raw_refs, list):
        raw_refs = []
    for ref in raw_refs:
        if isinstance(ref, str):
            path = ref
            line: int | None = None
            match = re.match(r"^(.*):(\d+)$", ref)
            if match:
                path = match.group(1)
                line = int(match.group(2))
            refs.append({"path": path, "line": line})
        elif isinstance(ref, dict):
            path = ref.get("path") or ref.get("source_path") or ref.get("file")
            line = ref.get("line") if ref.get("line") is not None else ref.get("line_no")
            symbol = ref.get("symbol") or ref.get("function") or ref.get("qualname")
            refs.append({"path": path, "line": line, "symbol": symbol})
    top_path = row.get("source_path") or row.get("path") or row.get("file")
    if top_path:
        refs.append(
            {
                "path": top_path,
                "line": row.get("line") if row.get("line") is not None else row.get("line_no"),
                "symbol": row.get("symbol") or row.get("function") or row.get("qualname"),
            }
        )

    cleaned: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, int, str]] = set()
    for ref in refs:
        path = str(ref.get("path") or "").strip()
        if not path:
            continue
        try:
            line = int(ref.get("line") or 0)
        except (TypeError, ValueError):
            line = 0
        symbol = str(ref.get("symbol") or "").strip()
        key = (path, line, symbol)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"path": path, "line": line or None, "symbol": symbol or None})
        if len(cleaned) >= _MAX_SOURCE_REFS_PER_CANDIDATE:
            break
    return cleaned


def _resolve_source_path(path_text: str, index: StaticIndex) -> Path | None:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    direct = Path(raw)
    if direct.is_absolute() and direct.exists():
        return direct.resolve()

    candidates: List[Path] = []
    for root in [index.repo_root, index.tests_root]:
        if root is None:
            continue
        candidates.append((root / raw).resolve())
        if raw.startswith("homeassistant/components/"):
            parts = raw.split("homeassistant/components/", 1)[1]
            candidates.append((root / parts).resolve())
        if raw.startswith("tests/components/"):
            parts = raw.split("tests/components/", 1)[1]
            candidates.append((root / parts).resolve())
    for candidate in candidates:
        if candidate.exists():
            return candidate

    normalized = raw.replace("\\", "/").lower().lstrip("./")
    suffix_matches = [
        Path(item.path)
        for item in index.files.values()
        if item.rel_path.lower() == normalized
        or item.path.replace("\\", "/").lower().endswith("/" + normalized)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0].resolve()
    return None


def _function_matches_symbol(fn: FunctionIndexEntry, symbol: str) -> bool:
    token = str(symbol or "").strip()
    if not token:
        return False
    lowered = token.lower()
    return fn.name.lower() == lowered or fn.qualname.lower() == lowered or fn.qualname.lower().endswith("." + lowered)


def _file_functions(index: StaticIndex, path: Path) -> List[FunctionIndexEntry]:
    resolved = str(path.resolve())
    return [fn for fn in index.functions if fn.path == resolved]


def _observed_calls_for_candidate(index: StaticIndex, refs: List[Dict[str, Any]], symbol: str) -> Tuple[Set[str], Set[str], Set[str]]:
    call_attrs: Set[str] = set()
    call_tokens: Set[str] = set()
    imports: Set[str] = set()
    for ref in refs:
        path = Path(str(ref["resolved_path"]))
        file_entry = index.file_by_path(path)
        if file_entry:
            call_attrs |= file_entry.call_attrs
            call_tokens |= file_entry.call_tokens
            imports |= file_entry.imported_modules
        functions = _file_functions(index, path)
        local_symbol = str(ref.get("symbol") or symbol or "").strip()
        if local_symbol:
            functions = [fn for fn in functions if _function_matches_symbol(fn, local_symbol)]
        for fn in functions:
            call_attrs |= fn.call_attrs
            call_tokens |= fn.call_tokens
            imports |= fn.imported_modules
    return call_attrs, call_tokens, imports


def _protocol_family(row: Dict[str, Any], marker_type: str) -> str:
    raw = str(row.get("protocol_family") or row.get("family_group") or "").strip().upper()
    if raw:
        if raw in {"LOCAL", "LOCAL_API"}:
            return "LOCAL_API"
        return raw
    if marker_type.startswith("BLE_") or marker_type == "BLE_OP":
        return "BLE"
    if marker_type.startswith("CLOUD_") or marker_type == "CLOUD_OP":
        return "CLOUD"
    if marker_type.startswith("LOCAL_"):
        return "LOCAL_API"
    return "HA"


def _context_text(index: StaticIndex, refs: List[Dict[str, Any]], match: Dict[str, Any]) -> str:
    chunks: List[str] = []
    chunks.extend(match.get("call_attrs", []))
    chunks.extend(match.get("module_hints", []))
    for ref in refs:
        entry = index.file_by_path(Path(str(ref["resolved_path"])))
        if not entry:
            continue
        chunks.append(entry.rel_path)
        chunks.append(entry.integration)
        chunks.append(entry.manifest_iot_class or "")
        chunks.extend(sorted(entry.imported_modules))
        chunks.extend(sorted(entry.call_tokens))
        chunks.append(entry.text_lower[:4000])
    return " ".join(str(item).lower() for item in chunks if str(item).strip())


def _protocol_context_ok(protocol_family: str, context_text: str, refs: List[Dict[str, Any]], index: StaticIndex) -> Tuple[bool, str]:
    family = protocol_family.upper()
    manifest_values = {
        str(index.file_by_path(Path(str(ref["resolved_path"]))).manifest_iot_class or "").lower()
        for ref in refs
        if index.file_by_path(Path(str(ref["resolved_path"])))
    }
    if family == "BLE":
        return any(token in context_text for token in _BLE_CONTEXT_TOKENS), "ble_context_missing"
    if family == "CLOUD":
        if any("cloud" in value for value in manifest_values):
            return True, ""
        if any(value.startswith("local") for value in manifest_values) and not any(
            token in context_text for token in {"oauth", "token", "cloud", "429", "retry_after", "https://"}
        ):
            return False, "manifest_local_without_cloud_runtime_signal"
        return any(token in context_text for token in _CLOUD_CONTEXT_TOKENS), "cloud_context_missing"
    if family == "LOCAL_API":
        if any("cloud" in value for value in manifest_values) and not any(token in context_text for token in _LOCAL_CONTEXT_TOKENS):
            return False, "manifest_cloud_without_local_runtime_signal"
        return any(token in context_text for token in _LOCAL_CONTEXT_TOKENS), "local_context_missing"
    return True, ""


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.7
    return min(0.99, max(0.0, confidence))


def _existing_evidence_ids(row: Dict[str, Any], bank_ids: Set[str]) -> Tuple[List[str], List[str]]:
    raw_ids = row.get("evidence_ids", row.get("evidence_refs", []))
    ids = _normalize_string_list(raw_ids)
    accepted = [item for item in ids if item in bank_ids]
    missing = [item for item in ids if item not in bank_ids]
    return accepted, missing


def _make_synthetic_evidence(candidate: Dict[str, Any], verified_refs: List[Dict[str, Any]], marker_type: str, confidence: float) -> List[CodeEvidence]:
    evidence: List[CodeEvidence] = []
    for ref in verified_refs:
        evidence_id = "LLM_CODE_" + _sha1_json(
            {
                "path": ref["resolved_path"],
                "line": ref.get("line") or ref.get("resolved_line") or 1,
                "marker_type": marker_type,
                "candidate": candidate.get("candidate_id") or candidate.get("id"),
            },
            size=12,
        )
        line = int(ref.get("line") or ref.get("resolved_line") or 1)
        evidence.append(
            CodeEvidence(
                evidence_id=evidence_id,
                source_path=str(ref["resolved_path"]),
                pattern=marker_type,
                line_no=max(1, line),
                frequency=1,
                specificity="PROTOCOL",
                source_type="code",
                extractor_version=SYNTHETIC_EXTRACTOR_VERSION,
                normalization_flags=[
                    "llm_candidate_verified:source_ref",
                    f"candidate_kind:{candidate.get('kind', 'unknown')}",
                ],
                confidence=confidence,
                typed_anchor=marker_type,
                signal_strength="CALL_CHAIN_STRONG",
                effective_typed_anchor=marker_type,
                semantic_level="RUNTIME",
                semantic_anchor=marker_type,
            )
        )
    return evidence


def _verify_candidate(row: Dict[str, Any], *, index: StaticIndex, bank: EvidenceBank) -> Tuple[VerifiedCandidate | None, Dict[str, Any] | None]:
    row = dict(row)
    kind = str(row.get("kind") or row.get("type") or "").strip().lower()
    marker_type = str(row.get("marker_type") or row.get("family") or row.get("marker") or "").strip().upper()
    candidate_id = str(row.get("candidate_id") or row.get("id") or f"llm_candidate_{_sha1_json(row)}").strip()
    confidence = _normalize_confidence(row.get("confidence", row.get("score", 0.7)))
    match = _normalized_match(row)
    symbol = str(row.get("symbol") or row.get("function") or row.get("qualname") or "").strip()
    source_refs = _source_refs_from_row(row)
    bank_ids = set(bank.by_id())
    existing_ids, missing_ids = _existing_evidence_ids(row, bank_ids)
    reasons: List[str] = []
    notes: List[str] = []

    if kind not in _SUPPORTED_CANDIDATE_KINDS:
        reasons.append(f"unsupported_kind:{kind or 'missing'}")
    if confidence < _MIN_CONFIDENCE:
        reasons.append(f"confidence_below_threshold:{confidence:.2f}")
    if kind in {"runtime_carrier", "marker_detector", "test_behavior"} and not marker_type:
        reasons.append("missing_marker_type")
    if kind == "marker_detector" and marker_type and marker_type not in _MARKER_TYPES:
        reasons.append(f"unsupported_marker_type:{marker_type}")
    if kind == "runtime_carrier" and marker_type and marker_type not in _GROUNDING_FAMILY_TYPES and not (
        marker_type.startswith("BLE_") or marker_type.startswith("CLOUD_") or marker_type.startswith("LOCAL_")
    ):
        reasons.append(f"unsupported_runtime_family:{marker_type}")
    if kind == "rule_candidate" and not (row.get("marker_hints") or row.get("hard_edge_templates") or row.get("soft_constraint_templates")):
        reasons.append("rule_candidate_missing_semantics")
    if missing_ids:
        reasons.extend(f"missing_evidence_id:{item}" for item in missing_ids[:4])

    verified_refs: List[Dict[str, Any]] = []
    for ref in source_refs:
        resolved = _resolve_source_path(str(ref.get("path") or ""), index)
        if resolved is None:
            reasons.append(f"source_ref_unresolved:{ref.get('path')}")
            continue
        file_entry = index.file_by_path(resolved)
        if file_entry is None:
            reasons.append(f"source_ref_not_indexed:{resolved}")
            continue
        line = ref.get("line")
        if line is not None:
            try:
                line_int = int(line)
            except (TypeError, ValueError):
                reasons.append(f"source_ref_invalid_line:{ref.get('path')}:{line}")
                continue
            if line_int < 1 or line_int > file_entry.line_count:
                reasons.append(f"source_ref_line_out_of_range:{ref.get('path')}:{line_int}")
                continue
        else:
            line_int = 0
        local_symbol = str(ref.get("symbol") or symbol or "").strip()
        if local_symbol and not any(_function_matches_symbol(fn, local_symbol) for fn in _file_functions(index, resolved)):
            reasons.append(f"symbol_not_found:{local_symbol}")
            continue
        verified_refs.append(
            {
                "path": str(ref.get("path")),
                "resolved_path": str(resolved),
                "line": line_int or None,
                "symbol": local_symbol or None,
                "integration": file_entry.integration,
                "root_kind": file_entry.root_kind,
            }
        )

    if not verified_refs and not existing_ids:
        reasons.append("missing_local_grounding")

    observed_attrs, observed_tokens, observed_imports = _observed_calls_for_candidate(index, verified_refs, symbol)
    requested_attrs = {str(item).strip().lower() for item in match.get("call_attrs", []) if str(item).strip()}
    if kind == "marker_detector" and not requested_attrs and not match.get("function_names"):
        reasons.append("marker_detector_missing_match")
    if requested_attrs and not (requested_attrs & observed_attrs or requested_attrs & observed_tokens):
        reasons.append("candidate_call_attrs_not_observed")
    elif requested_attrs:
        missing_attrs = sorted(requested_attrs - observed_attrs - observed_tokens)
        if missing_attrs:
            notes.append("call_attrs_partially_observed:" + ",".join(missing_attrs[:6]))
    if observed_imports:
        notes.append("observed_imports:" + ",".join(sorted(observed_imports)[:8]))

    protocol_family = _protocol_family(row, marker_type)
    if marker_type and kind in {"runtime_carrier", "marker_detector", "test_behavior"}:
        context = _context_text(index, verified_refs, match)
        context_ok, reason = _protocol_context_ok(protocol_family, context, verified_refs, index)
        if not context_ok:
            reasons.append(reason)

    if reasons:
        return None, {
            "candidate_id": candidate_id,
            "kind": kind,
            "marker_type": marker_type,
            "reasons": sorted(dict.fromkeys(reasons)),
            "candidate": row,
        }

    integration = str(row.get("integration") or "").strip().lower()
    if not integration and verified_refs:
        integration = str(verified_refs[0].get("integration") or "").strip().lower()
    synthetic = _make_synthetic_evidence(row, verified_refs, marker_type or "UNKNOWN", confidence)
    return (
        VerifiedCandidate(
            row=row,
            candidate_id=candidate_id,
            kind=kind,
            marker_type=marker_type or "UNKNOWN",
            protocol_family=protocol_family,
            integration=integration,
            confidence=confidence,
            match=match,
            source_refs=verified_refs,
            existing_evidence_ids=existing_ids,
            synthetic_evidence=synthetic,
            notes=notes,
        ),
        None,
    )


def _detector_from_candidate(candidate: VerifiedCandidate) -> Dict[str, Any] | None:
    if candidate.kind != "marker_detector":
        return None
    match: Dict[str, Any] = {}
    for key in ("call_attrs", "function_names", "module_hints"):
        values = candidate.match.get(key, [])
        if values:
            match[key] = values
    if not match:
        return None
    detector_id = "llm:detector:" + candidate.marker_type.lower() + ":" + _sha1_json(
        {
            "candidate_id": candidate.candidate_id,
            "marker_type": candidate.marker_type,
            "match": match,
        },
        size=10,
    )
    return {
        "id": detector_id,
        "type": candidate.marker_type,
        "match": match,
        "strength": str(candidate.row.get("strength") or MarkerStrength.MEDIUM.value).strip().upper(),
        "phase": str(candidate.row.get("phase") or Phase.RUNTIME.value).strip().upper(),
        "promotion_state": "LLM_VERIFIED",
        "provenance": {
            "candidate_id": candidate.candidate_id,
            "source": "profile_builder_llm_discovery",
            "source_refs": candidate.source_refs,
            "confidence": candidate.confidence,
        },
    }


def _rule_from_candidate(candidate: VerifiedCandidate) -> Rule | None:
    if candidate.kind != "rule_candidate":
        return None
    evidence_ids = candidate.all_evidence_ids
    if not evidence_ids:
        return None
    marker_hints = [item.upper() for item in _normalize_string_list(candidate.row.get("marker_hints", []))]
    if not marker_hints and candidate.marker_type != "UNKNOWN":
        marker_hints = [candidate.marker_type]
    rule_id = str(candidate.row.get("rule_id") or f"rule_llm_{_sha1_json(candidate.row)}").strip()
    title = str(candidate.row.get("title") or candidate.row.get("name") or f"LLM discovered {candidate.protocol_family} rule").strip()
    category = str(candidate.row.get("category") or "protocol").strip().lower()
    return Rule(
        rule_id=rule_id,
        title=title,
        category=category,
        status=RuleStatus.SOFT.value,
        marker_hints=marker_hints,
        hard_edge_templates=[
            item for item in candidate.row.get("hard_edge_templates", []) if isinstance(item, dict)
        ],
        soft_constraint_templates=[
            item for item in candidate.row.get("soft_constraint_templates", []) if isinstance(item, dict)
        ],
        guard=str(candidate.row.get("guard") or "runtime_metrics_available"),
        fallback=str(candidate.row.get("fallback") or "disable_rule"),
        evidence_ids=evidence_ids,
        match_pattern=dict(candidate.row.get("match_pattern", {})) if isinstance(candidate.row.get("match_pattern", {}), dict) else {
            "dominant_pattern": marker_hints[0] if marker_hints else candidate.marker_type,
            "topic": f"protocol_{candidate.protocol_family.lower()}",
        },
        effect=dict(candidate.row.get("effect", {})) if isinstance(candidate.row.get("effect", {}), dict) else {
            "kind": "ordering_or_constraint",
            "scope": f"protocol_{candidate.protocol_family.lower()}",
        },
        provenance={
            "source": "profile_builder_llm_discovery",
            "candidate_id": candidate.candidate_id,
            "source_refs": candidate.source_refs,
            "verification_notes": candidate.notes,
        },
        source_type="profile_builder_llm_candidate",
        extractor_version=SYNTHETIC_EXTRACTOR_VERSION,
        normalization_flags=["llm_candidate_verified"],
        confidence=candidate.confidence,
    )


def _source_file_globs(candidate: VerifiedCandidate) -> List[str]:
    globs: List[str] = []
    for ref in candidate.source_refs:
        rel = str(ref.get("path") or "").strip()
        resolved = str(ref.get("resolved_path") or "")
        if rel and rel.endswith(".py") and not Path(rel).is_absolute():
            globs.append(rel)
        elif candidate.integration and resolved:
            name = Path(resolved).name
            globs.append(f"{candidate.integration}/{name}")
    if not globs and candidate.integration:
        globs.append(f"{candidate.integration}/*.py")
    return sorted(dict.fromkeys(globs))


def _grounding_row_from_candidate(candidate: VerifiedCandidate) -> Dict[str, Any] | None:
    if candidate.kind != "runtime_carrier":
        return None
    symbol = str(candidate.row.get("symbol") or candidate.row.get("function") or candidate.row.get("qualname") or "").strip()
    function_patterns = _normalize_string_list(candidate.match.get("function_names", []))
    if symbol:
        function_patterns.append(symbol.rsplit(".", 1)[-1])
    function_patterns = sorted(dict.fromkeys(item for item in function_patterns if item))
    action_kind = str(candidate.row.get("runtime_role") or candidate.row.get("action_kind") or candidate.protocol_family.lower()).strip().lower()
    return {
        "rule_id": "llm_profile:" + (candidate.integration or "global") + ":" + candidate.marker_type.lower() + ":" + _sha1_json(candidate.row, 8),
        "integration": candidate.integration,
        "family": candidate.marker_type,
        "action_kind": action_kind,
        "generalization_scope": str(candidate.row.get("generalization_scope") or "file_specific").strip().lower(),
        "file_globs": _source_file_globs(candidate),
        "phase": str(candidate.row.get("phase") or Phase.RUNTIME.value).strip().upper(),
        "strength": str(candidate.row.get("strength") or MarkerStrength.MEDIUM.value).strip().upper(),
        "confidence": {
            "base": round(candidate.confidence, 3),
            "emit_threshold": round(max(0.62, min(0.88, candidate.confidence * 0.92)), 3),
            "boost_if_imports": candidate.match.get("module_hints", []),
            "boost_if_names": candidate.match.get("call_attrs", []),
        },
        "required_context": ["runtime_path"],
        "forbidden_context": ["setup_function", "teardown_function", "entity_property_getter"],
        "call_patterns": candidate.match.get("call_attrs", []),
        "function_name_patterns": function_patterns,
        "binding_hints": {
            "preferred_action_kinds": [action_kind] if action_kind else [],
            "phase": Phase.RUNTIME.value,
        },
        "runtime_path_evidence": [
            f"{ref.get('path') or ref.get('resolved_path')}:{ref.get('line') or 1}" for ref in candidate.source_refs
        ],
        "negative_evidence": [],
        "why_not_setup": ["verified source is constrained to runtime_path and setup/teardown contexts are forbidden"],
        "why_not_more_general": "LLM candidate is accepted only with concrete local source refs; default scope stays file_specific.",
        "source_file_paths": [str(ref.get("resolved_path")) for ref in candidate.source_refs if ref.get("resolved_path")],
        "reviewer_status": "verified_candidate",
    }


def _build_grounding_profiles(candidates: List[VerifiedCandidate]) -> Dict[str, Dict[str, Any]]:
    by_integration: Dict[str, List[Dict[str, Any]]] = {}
    for candidate in candidates:
        row = _grounding_row_from_candidate(candidate)
        if row is None:
            continue
        integration = str(row.get("integration") or "global").strip().lower()
        by_integration.setdefault(integration, []).append(row)

    return {
        integration: {
            "schema_version": "m1_grounding_profile/v3",
            "integration": integration,
            "version": "profile_builder_llm_discovery_v1",
            "runtime_families": rows,
        }
        for integration, rows in sorted(by_integration.items())
    }


def _dedupe_synthetic_evidence(bank: EvidenceBank, evidence: List[CodeEvidence]) -> List[CodeEvidence]:
    existing = set(bank.by_id())
    out: List[CodeEvidence] = []
    for item in evidence:
        if item.evidence_id in existing:
            continue
        existing.add(item.evidence_id)
        out.append(item)
    return out


def _append_unique_detectors(existing: List[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    detector_rows = [dict(item) for item in existing]
    seen_ids = {str(item.get("id", "")).strip() for item in detector_rows}
    seen_keys = {
        (
            str(item.get("type", "")).strip().upper(),
            json.dumps(item.get("match", {}), sort_keys=True),
        )
        for item in detector_rows
    }
    for candidate in candidates:
        detector_id = str(candidate.get("id", "")).strip()
        key = (
            str(candidate.get("type", "")).strip().upper(),
            json.dumps(candidate.get("match", {}), sort_keys=True),
        )
        if not detector_id or detector_id in seen_ids or key in seen_keys:
            continue
        seen_ids.add(detector_id)
        seen_keys.add(key)
        detector_rows.append(candidate)
    return detector_rows


def merge_llm_marker_detectors(existing: List[Dict[str, Any]], result: LLMDiscoveryResult | None) -> List[Dict[str, Any]]:
    if result is None:
        return existing
    return _append_unique_detectors(existing, result.marker_detectors)


def run_llm_candidate_discovery(
    *,
    repo_root: str | Path,
    tests_root: str | Path | None,
    bank: EvidenceBank,
    adapter: LLMDiscoveryAdapter | None = None,
    candidate_payload: Any = None,
    out_dir: str | Path | None = None,
) -> LLMDiscoveryResult:


    index = build_static_index(repo_root, tests_root)
    request_payload = build_discovery_payload(bank, index)

    raw_response = candidate_payload
    if adapter is not None:
        raw_response = adapter(request_payload)
    candidates = _normalize_response_candidates(raw_response)

    verified: List[VerifiedCandidate] = []
    rejected: List[Dict[str, Any]] = []
    for row in candidates:
        accepted, rejection = _verify_candidate(row, index=index, bank=bank)
        if accepted is not None:
            verified.append(accepted)
        elif rejection is not None:
            rejected.append(rejection)

    synthetic = _dedupe_synthetic_evidence(bank, [item for candidate in verified for item in candidate.synthetic_evidence])
    synthetic_ids = {item.evidence_id for item in synthetic}
    for candidate in verified:
        candidate.synthetic_evidence = [
            item for item in candidate.synthetic_evidence if item.evidence_id in synthetic_ids or item.evidence_id in set(bank.by_id())
        ]

    marker_detectors = [
        detector
        for detector in (_detector_from_candidate(candidate) for candidate in verified)
        if detector is not None
    ]
    rule_candidates = [
        rule for rule in (_rule_from_candidate(candidate) for candidate in verified) if rule is not None
    ]
    grounding_profiles = _build_grounding_profiles(verified)
    summary = {
        "schema_version": VERIFICATION_SCHEMA,
        "candidate_count": len(candidates),
        "verified_count": len(verified),
        "rejected_count": len(rejected),
        "synthetic_evidence_count": len(synthetic),
        "marker_detector_count": len(marker_detectors),
        "rule_candidate_count": len(rule_candidates),
        "grounding_profile_count": len(grounding_profiles),
        "verified_by_kind": {
            kind: sum(1 for item in verified if item.kind == kind)
            for kind in sorted(_SUPPORTED_CANDIDATE_KINDS)
        },
    }
    result = LLMDiscoveryResult(
        request_payload=request_payload,
        raw_response=raw_response,
        verified=verified,
        rejected=rejected,
        marker_detectors=marker_detectors,
        rule_candidates=rule_candidates,
        grounding_profiles=grounding_profiles,
        synthetic_evidence=synthetic,
        summary=summary,
    )

    if out_dir is not None:
        out = Path(out_dir)
        dump_json(out / "llm_candidate_request.json", request_payload)
        dump_json(out / "llm_candidate_report.json", raw_response if raw_response is not None else {"candidates": []})
        dump_json(out / "llm_candidate_verification.json", result.verification_report())
        profile_dir = out / "llm_grounding_profiles_auto"
        for integration, payload in grounding_profiles.items():
            dump_json(profile_dir / f"{integration}.json", payload)
    return result


def _content_from_chat_response(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message", {})
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
            ]
            return "\n".join(parts)
    return str(first.get("text", "") or "")


def _json_from_llm_text(text: str) -> Any:
    value = str(text or "").strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        value = value[start : end + 1]
    return json.loads(value)


def make_chat_completion_discovery_adapter(
    *,
    api_base_url: str,
    api_key: str,
    model: str = "gpt-5",
    timeout_s: int = 120,
) -> LLMDiscoveryAdapter:


    base_url = str(api_base_url or "").strip()
    key = str(api_key or "").strip()
    if not base_url:
        raise LLMDiscoveryError("api_base_url is required")
    if not key:
        raise LLMDiscoveryError("api_key is required")

    def _adapter(payload: Dict[str, Any]) -> Any:
        messages = [
            {
                "role": "system",
                "content": (
                    "You discover Home Assistant integration profile candidates. "
                    "Return JSON only. Every candidate must cite concrete source_refs or evidence_ids. "
                    "Do not invent files, line numbers, marker types, or unsupported concurrency rules."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
        ]
        request_payload = {
            "model": model,
            "temperature": 0.0,
            "messages": messages,
        }
        req = request.Request(
            base_url,
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=int(timeout_s)) as resp:
                raw = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise LLMDiscoveryError(f"LLM HTTP error {exc.code}: {body[:500]}") from exc
        except error.URLError as exc:
            raise LLMDiscoveryError(f"LLM request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LLMDiscoveryError("LLM request failed: timeout") from exc
        except OSError as exc:
            raise LLMDiscoveryError(f"LLM request failed: {exc}") from exc

        try:
            response_payload = json.loads(raw)
            content = _content_from_chat_response(response_payload)
            return _json_from_llm_text(content)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise LLMDiscoveryError("LLM endpoint did not return parseable JSON candidates") from exc

    return _adapter
