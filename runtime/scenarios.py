from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Scenario:
    scenario_id: str
    phases: List[str]
    faults: Dict[str, Any] = field(default_factory=dict)


def default_scenarios(seed: int = 7) -> List[Scenario]:
    rng = random.Random(seed)
    scenarios = [
        Scenario("lifecycle_nominal", ["setup", "update_poll", "unload"], {}),
        Scenario("push_nominal", ["setup", "push_callback", "unload"], {}),
        Scenario("ble_disconnect", ["setup", "update_poll", "unload"], {"ble_disconnect": True}),
        Scenario("cloud_429", ["setup", "update_poll", "unload"], {"cloud_429": True}),
        Scenario("token_expired", ["setup", "update_poll", "unload"], {"token_expired": True}),
    ]

    jitter_count = 2
    for idx in range(jitter_count):
        scenarios.append(
            Scenario(
                scenario_id=f"random_jitter_{idx}",
                phases=["setup", "update_poll", "unload"],
                faults={
                    "network_jitter_ms": rng.randint(10, 250),
                    "ble_timeout": rng.random() < 0.3,
                    "cloud_spike": rng.random() < 0.4,
                },
            )
        )

    return scenarios


SCENARIO_LIBRARY: Dict[str, Scenario] = {
    "baseline_happy_path": Scenario("baseline_happy_path", ["setup", "update_poll", "unload"], {}),
    "push_happy_path": Scenario("push_happy_path", ["setup", "push_callback", "unload"], {}),
    "fault_ble_disconnect": Scenario("fault_ble_disconnect", ["setup", "update_poll", "unload"], {"ble_disconnect": True}),
    "fault_cloud_429": Scenario("fault_cloud_429", ["setup", "update_poll", "unload"], {"cloud_429": True}),
    "fault_timeout": Scenario("fault_timeout", ["setup", "update_poll", "unload"], {"timeout": True}),
}


def scenarios_from_config(validation: Dict[str, Any] | None = None, seed: int = 7) -> List[Scenario]:
    validation = validation or {}
    diff = validation.get("differential_tests", {}) if isinstance(validation.get("differential_tests", {}), dict) else {}
    enabled = diff.get("enabled", True)
    if not enabled:
        return []

    scenario_names = diff.get("scenarios", [])
    runs_per_scenario = int(diff.get("runs_per_scenario", 1))
    if not scenario_names:
        return default_scenarios(seed=seed)

    scenarios: List[Scenario] = []
    for name in scenario_names:
        base = SCENARIO_LIBRARY.get(name)
        if base is None:
            base = Scenario(str(name), ["setup", "update_poll", "unload"], {})
        for run_idx in range(max(1, runs_per_scenario)):
            scenarios.append(
                Scenario(
                    scenario_id=f"{base.scenario_id}__run{run_idx}",
                    phases=list(base.phases),
                    faults=dict(base.faults),
                )
            )
    return scenarios
