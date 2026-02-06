from __future__ import annotations

import json
from dataclasses import dataclass

from reidce.schemas import CadRef, DesignSpec, GeometrySpec
from sfcs_mdp.hashutil import sha256_bytes


@dataclass(frozen=True)
class PicoGKResult:
    cad_ref: CadRef
    geom_hash: str
    source: str


def _hash_geometry(geometry: GeometrySpec) -> str:
    payload = geometry.model_dump(mode="json", by_alias=True)
    return sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def generate_cad_ref(geometry: GeometrySpec, source: str = "pico_gk_stub") -> PicoGKResult:
    geom_hash = _hash_geometry(geometry)
    cad_ref = CadRef(type="implicit", uri=f"pico_gk://{geom_hash}", sha256=geom_hash)
    return PicoGKResult(cad_ref=cad_ref, geom_hash=geom_hash, source=source)


def apply_pico_gk(design: DesignSpec, source: str = "pico_gk_stub") -> DesignSpec:
    if design.geometry.cad_ref.type != "none":
        return design
    result = generate_cad_ref(design.geometry, source)
    updated_geometry = design.geometry.model_copy(update={"cad_ref": result.cad_ref})
    return design.model_copy(update={"geometry": updated_geometry})
