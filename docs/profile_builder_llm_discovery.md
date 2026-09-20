# Profile Builder LLM Discovery

This module adds an optional LLM-assisted candidate-discovery layer to the
Profile Builder. It is disabled by default and does not change the deterministic
profile path unless explicitly enabled.

## Goal

The LLM is used only as a candidate discovery tool. It can suggest:

- runtime carriers for later M1 grounding profiles;
- marker detectors for calls that deterministic evidence misses;
- conservative profile rule candidates.

The LLM output is not trusted directly. Every accepted candidate must be
verified against local repo/test snapshots through AST and source-reference
checks.

## Inputs

- `EvidenceBank` from deterministic profile extraction.
- Repo snapshot root.
- Optional test snapshot root.
- Optional LLM adapter or offline candidate JSON.

Candidate JSON may use this shape:

```json
{
  "schema_version": "profile_builder_llm_discovery/response/v1",
  "candidates": [
    {
      "kind": "runtime_carrier",
      "marker_type": "CLOUD_HTTP_CALL",
      "protocol_family": "CLOUD",
      "runtime_role": "status",
      "symbol": "Client.async_update_data",
      "match": {
        "call_attrs": ["request"],
        "module_hints": ["aiohttp"]
      },
      "source_refs": [{"path": "demo/api.py", "line": 42}],
      "confidence": 0.8
    }
  ]
}
```

## Verification

A candidate is accepted only when the local verifier can confirm:

- source refs resolve to indexed repo/test files;
- cited line numbers are in range;
- cited symbols exist when provided;
- proposed call attrs are observed in the cited function or file;
- protocol context is plausible, for example BLE candidates require BLE-like
  imports/path/text and cloud candidates require cloud-like manifest or runtime
  signals;
- marker/family type is in the supported vocabulary;
- confidence is above the minimum threshold.

Rejected candidates are recorded with structured reasons.

## Outputs

When enabled, the builder writes:

- `llm_candidate_request.json`: compact payload sent to the LLM adapter;
- `llm_candidate_report.json`: raw LLM/offline candidate response;
- `llm_candidate_verification.json`: accepted/rejected candidate report;
- `llm_grounding_profiles_auto/*.json`: verified runtime-carrier grounding
  profile drafts.

Verified candidates can also add synthetic code evidence and verified marker
detectors to the generated profile. These additions are recorded under
`profile.provenance.profile_enhancements.llm_discovery`.

## CLI

Offline candidate JSON:

```bash
python floweaver_cli.py build-profile \
  --enable-llm-discovery \
  --llm-discovery-candidates-path /path/to/candidates.json
```

OpenAI-compatible chat completion:

```bash
python floweaver_cli.py build-profile \
  --enable-llm-discovery \
  --llm-discovery-api-base-url "$FLOWEAVER_LLM_API_BASE_URL" \
  --llm-discovery-api-key-env FLOWEAVER_LLM_API_KEY \
  --llm-discovery-model gpt-5
```

## Trust Boundary

This layer should be treated as a recall improver, not as a proof source. The
accepted output is bounded by local source evidence and remains conservative:
default Profile Builder behavior is unchanged, and failed LLM transport or
invalid LLM output falls back to the deterministic profile path.

## Evidence Layers

Profile Builder now separates deterministic extraction into three layers:

- `evidence_bank_raw.json`: all deterministic extractor output plus any
  verified LLM synthetic evidence. This is retained for auditability and future
  candidate discovery.
- `profile_facts.json`: AST facts such as files, functions, imports, call attrs,
  and line ranges. This is the factual substrate used to verify LLM candidates.
- `evidence_bank.json`: semantic evidence admitted into rule normalization,
  gate, hardening, and profile synthesis.

The default semantic policy is `core_plus_verified`. It keeps high-confidence
framework/protocol/test/doc evidence and LLM-verified evidence, while filtering
weak hint rows such as downgraded `_HINT` anchors. The legacy behavior is still
available with:

```bash
python floweaver_cli.py build-profile \
  --evidence-semantic-policy legacy
```

The admission decision is written to `evidence_policy_report.json`.
