from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import yaml

from sfcs_mdp.model import ProcessStep, Spec


class SpecValidationError(ValueError):
    pass


def load_spec(path: Path) -> Spec:
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    if data is None:
        raise SpecValidationError("Spec is empty.")
    return Spec.model_validate(data)


def _ensure_unique_step_ids(steps: Iterable[ProcessStep]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for step in steps:
        if step.step_id in seen:
            duplicates.append(step.step_id)
        seen.add(step.step_id)
    if duplicates:
        raise SpecValidationError(f"Duplicate step_id values: {sorted(set(duplicates))}")


def _ensure_prerequisites_exist(steps: Iterable[ProcessStep]) -> None:
    step_ids = {step.step_id for step in steps}
    missing: list[str] = []
    for step in steps:
        for prereq in step.prerequisites:
            if prereq not in step_ids:
                missing.append(f"{step.step_id} -> {prereq}")
    if missing:
        raise SpecValidationError(f"Missing prerequisite steps: {missing}")


def topological_sort(steps: List[ProcessStep]) -> List[ProcessStep]:
    _ensure_unique_step_ids(steps)
    _ensure_prerequisites_exist(steps)

    by_id = {step.step_id: step for step in steps}
    remaining = {step.step_id: set(step.prerequisites) for step in steps}
    ordered: list[str] = []
    ready = [step_id for step_id, prereqs in remaining.items() if not prereqs]

    while ready:
        step_id = ready.pop(0)
        ordered.append(step_id)
        for candidate, prereqs in remaining.items():
            if step_id in prereqs:
                prereqs.remove(step_id)
                if not prereqs and candidate not in ordered and candidate not in ready:
                    ready.append(candidate)

    if len(ordered) != len(steps):
        raise SpecValidationError("Cycle detected in step prerequisites.")

    return [by_id[step_id] for step_id in ordered]


def validate_spec(spec: Spec) -> None:
    topological_sort(spec.process_flow)
