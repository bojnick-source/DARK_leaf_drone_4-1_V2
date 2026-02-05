from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, Iterable, List, Optional, Tuple

from reidce.memory import MemoryStore


@dataclass(frozen=True)
class Node:
    name: str


@dataclass(frozen=True)
class Resistor:
    name: str
    node_a: str
    node_b: str
    ohms: float


@dataclass(frozen=True)
class VoltageSource:
    name: str
    node_pos: str
    node_neg: str
    volts: float


@dataclass(frozen=True)
class CurrentSource:
    name: str
    node_pos: str
    node_neg: str
    amps: float


@dataclass(frozen=True)
class Capacitor:
    name: str
    node_a: str
    node_b: str
    farads: float


@dataclass(frozen=True)
class Inductor:
    name: str
    node_a: str
    node_b: str
    henrys: float


@dataclass(frozen=True)
class CNTInterconnect:
    name: str
    node_a: str
    node_b: str
    length_m: float
    area_m2: float
    resistivity_ohm_m: float
    temp_c: float = 25.0
    temp_coeff_per_c: float = 0.002

    def resistance(self) -> float:
        if self.area_m2 <= 0.0 or self.length_m <= 0.0:
            raise ValueError(f"Invalid CNT geometry for {self.name}")
        base = self.resistivity_ohm_m * self.length_m / self.area_m2
        return base * (1.0 + self.temp_coeff_per_c * (self.temp_c - 25.0))


@dataclass(frozen=True)
class TaNResistor:
    name: str
    node_a: str
    node_b: str
    sheet_resistance_ohms_per_sq: float
    length_m: float
    width_m: float
    temp_c: float = 25.0
    temp_coeff_per_c: float = 0.001

    def resistance(self) -> float:
        if self.width_m <= 0.0 or self.length_m <= 0.0:
            raise ValueError(f"Invalid TaN geometry for {self.name}")
        squares = self.length_m / self.width_m
        base = self.sheet_resistance_ohms_per_sq * squares
        return base * (1.0 + self.temp_coeff_per_c * (self.temp_c - 25.0))


@dataclass(frozen=True)
class ProcessingUnitLoad:
    name: str
    node_pos: str
    node_neg: str
    power_w: float
    nominal_voltage_v: float
    efficiency: float = 0.92

    def equivalent_resistance(self) -> float:
        if self.power_w <= 0.0 or self.nominal_voltage_v <= 0.0:
            raise ValueError(f"Invalid processing load for {self.name}")
        effective_power = self.power_w / max(self.efficiency, 1e-6)
        return (self.nominal_voltage_v**2) / effective_power


@dataclass(frozen=True)
class PhotonicWaveguide:
    name: str
    length_m: float
    loss_db_per_cm: float

    def insertion_loss_db(self) -> float:
        if self.length_m <= 0.0:
            raise ValueError(f"Invalid waveguide length for {self.name}")
        return self.loss_db_per_cm * (self.length_m * 100.0)


@dataclass(frozen=True)
class PhotonicModulator:
    name: str
    drive_voltage_v: float
    capacitance_f: float
    data_rate_hz: float

    def dynamic_power_w(self) -> float:
        if self.drive_voltage_v <= 0.0 or self.capacitance_f <= 0.0 or self.data_rate_hz <= 0.0:
            raise ValueError(f"Invalid modulator parameters for {self.name}")
        return 0.5 * self.capacitance_f * (self.drive_voltage_v**2) * self.data_rate_hz


@dataclass(frozen=True)
class PhotonicProcessor:
    name: str
    optical_input_mw: float
    optical_efficiency: float
    thermal_budget_w: float
    modulators: Tuple[PhotonicModulator, ...] = ()
    waveguides: Tuple[PhotonicWaveguide, ...] = ()

    def optical_power_w(self) -> float:
        if self.optical_input_mw <= 0.0:
            raise ValueError(f"Invalid optical input for {self.name}")
        return self.optical_input_mw * 1e-3

    def total_waveguide_loss_db(self) -> float:
        return sum(waveguide.insertion_loss_db() for waveguide in self.waveguides)

    def optical_output_w(self) -> float:
        optical_in = self.optical_power_w()
        loss_db = self.total_waveguide_loss_db()
        return optical_in * (10.0 ** (-loss_db / 10.0))

    def electrical_power_w(self) -> float:
        mod_power = sum(modulator.dynamic_power_w() for modulator in self.modulators)
        if self.optical_efficiency <= 0.0:
            raise ValueError(f"Invalid optical efficiency for {self.name}")
        driver_overhead = self.optical_power_w() * (1.0 / self.optical_efficiency - 1.0)
        return mod_power + driver_overhead

    def total_power_w(self) -> float:
        return self.electrical_power_w() + self.optical_power_w()

    def thermal_margin_w(self) -> float:
        return self.thermal_budget_w - self.total_power_w()


@dataclass(frozen=True)
class CircuitBoardTrace:
    name: str
    length_m: float
    width_m: float
    thickness_m: float
    resistivity_ohm_m: float = 1.68e-8
    temp_c: float = 25.0
    temp_coeff_per_c: float = 0.0039

    def resistance(self) -> float:
        if self.length_m <= 0.0 or self.width_m <= 0.0 or self.thickness_m <= 0.0:
            raise ValueError(f"Invalid trace geometry for {self.name}")
        base = self.resistivity_ohm_m * self.length_m / (self.width_m * self.thickness_m)
        return base * (1.0 + self.temp_coeff_per_c * (self.temp_c - 25.0))


@dataclass(frozen=True)
class CircuitBoard:
    name: str
    traces: Tuple[CircuitBoardTrace, ...] = ()
    losses_w: float = 0.0

    def trace_loss_w(self, current_a: float) -> float:
        if current_a < 0.0:
            raise ValueError("current_a must be >= 0")
        return sum((current_a**2) * trace.resistance() for trace in self.traces) + self.losses_w


@dataclass(frozen=True)
class PowerRail:
    name: str
    voltage_v: float
    max_current_a: float


@dataclass(frozen=True)
class RailLoad:
    name: str
    power_w: float
    efficiency: float = 0.95

    def current_a(self, rail_voltage_v: float) -> float:
        if rail_voltage_v <= 0.0:
            raise ValueError("rail_voltage_v must be > 0")
        effective_power = self.power_w / max(self.efficiency, 1e-6)
        return effective_power / rail_voltage_v


@dataclass(frozen=True)
class PowerDistributionNetwork:
    rails: Tuple[PowerRail, ...]
    loads: Dict[str, Tuple[RailLoad, ...]]
    regulator_efficiency: float = 0.92

    def rail_current_map(self) -> Dict[str, float]:
        currents: Dict[str, float] = {}
        for rail in self.rails:
            rail_loads = self.loads.get(rail.name, ())
            rail_current = sum(load.current_a(rail.voltage_v) for load in rail_loads)
            currents[rail.name] = rail_current
        return currents

    def total_input_power_w(self) -> float:
        rail_power = sum(rail.voltage_v * current for rail, current in self._rail_pairs())
        return rail_power / max(self.regulator_efficiency, 1e-6)

    def validate(self) -> None:
        for rail in self.rails:
            rail_current = self.rail_current_map().get(rail.name, 0.0)
            if rail_current > rail.max_current_a:
                raise ValueError(f"Rail {rail.name} exceeds max current")

    def _rail_pairs(self) -> List[Tuple[PowerRail, float]]:
        current_map = self.rail_current_map()
        return [(rail, current_map.get(rail.name, 0.0)) for rail in self.rails]


@dataclass(frozen=True)
class ThermalNode:
    name: str
    ambient_c: float
    r_th_c_per_w: float


@dataclass(frozen=True)
class ThermalLoad:
    name: str
    node: str
    power_w: float


def simulate_thermal_steady_state(
    nodes: Tuple[ThermalNode, ...],
    loads: Tuple[ThermalLoad, ...],
) -> Dict[str, float]:
    node_map = {node.name: node for node in nodes}
    totals: Dict[str, float] = {node.name: 0.0 for node in nodes}
    for load in loads:
        if load.node not in node_map:
            raise ValueError(f"Unknown thermal node {load.node}")
        totals[load.node] += load.power_w
    temps: Dict[str, float] = {}
    for node in nodes:
        temps[node.name] = node.ambient_c + totals[node.name] * node.r_th_c_per_w
    return temps


@dataclass(frozen=True)
class CircuitResult:
    node_voltages: Dict[str, float]
    source_currents: Dict[str, float]
    resistor_currents: Dict[str, float]


@dataclass(frozen=True)
class TransientResult:
    times_s: List[float]
    node_voltages: List[Dict[str, float]]


@dataclass(frozen=True)
class ElectroThermalResistor:
    name: str
    node_a: str
    node_b: str
    base_ohms: float
    temp_coeff_per_c: float
    ref_temp_c: float
    thermal_node: str

    def resistance(self, temp_c: float) -> float:
        return self.base_ohms * (1.0 + self.temp_coeff_per_c * (temp_c - self.ref_temp_c))


@dataclass(frozen=True)
class ElectroThermalResult:
    circuit: CircuitResult
    temperatures_c: Dict[str, float]
    iterations: int


@dataclass
class Circuit:
    nodes: Dict[str, Node] = field(default_factory=dict)
    resistors: List[Resistor] = field(default_factory=list)
    voltage_sources: List[VoltageSource] = field(default_factory=list)
    current_sources: List[CurrentSource] = field(default_factory=list)
    capacitors: List[Capacitor] = field(default_factory=list)
    inductors: List[Inductor] = field(default_factory=list)

    def add_node(self, name: str) -> Node:
        if name not in self.nodes:
            self.nodes[name] = Node(name=name)
        return self.nodes[name]

    def add_resistor(self, name: str, node_a: str, node_b: str, ohms: float) -> Resistor:
        self.add_node(node_a)
        self.add_node(node_b)
        resistor = Resistor(name=name, node_a=node_a, node_b=node_b, ohms=ohms)
        self.resistors.append(resistor)
        return resistor

    def add_voltage_source(
        self, name: str, node_pos: str, node_neg: str, volts: float
    ) -> VoltageSource:
        self.add_node(node_pos)
        self.add_node(node_neg)
        source = VoltageSource(name=name, node_pos=node_pos, node_neg=node_neg, volts=volts)
        self.voltage_sources.append(source)
        return source

    def add_current_source(
        self, name: str, node_pos: str, node_neg: str, amps: float
    ) -> CurrentSource:
        self.add_node(node_pos)
        self.add_node(node_neg)
        source = CurrentSource(name=name, node_pos=node_pos, node_neg=node_neg, amps=amps)
        self.current_sources.append(source)
        return source

    def add_capacitor(self, name: str, node_a: str, node_b: str, farads: float) -> Capacitor:
        self.add_node(node_a)
        self.add_node(node_b)
        capacitor = Capacitor(name=name, node_a=node_a, node_b=node_b, farads=farads)
        self.capacitors.append(capacitor)
        return capacitor

    def add_inductor(self, name: str, node_a: str, node_b: str, henrys: float) -> Inductor:
        self.add_node(node_a)
        self.add_node(node_b)
        inductor = Inductor(name=name, node_a=node_a, node_b=node_b, henrys=henrys)
        self.inductors.append(inductor)
        return inductor

    def add_cnt_interconnect(self, interconnect: CNTInterconnect) -> Resistor:
        resistance = interconnect.resistance()
        return self.add_resistor(interconnect.name, interconnect.node_a, interconnect.node_b, resistance)

    def add_tan_resistor(self, tan_resistor: TaNResistor) -> Resistor:
        resistance = tan_resistor.resistance()
        return self.add_resistor(tan_resistor.name, tan_resistor.node_a, tan_resistor.node_b, resistance)

    def add_processing_unit(self, load: ProcessingUnitLoad) -> Resistor:
        resistance = load.equivalent_resistance()
        return self.add_resistor(load.name, load.node_pos, load.node_neg, resistance)


def parse_netlist(lines: Iterable[str]) -> Circuit:
    circuit = Circuit()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            raise ValueError(f"Invalid netlist line: {line}")
        name = parts[0]
        node_a = parts[1]
        node_b = parts[2]
        value = float(parts[3])
        kind = name[0].upper()
        if kind == "R":
            circuit.add_resistor(name, node_a, node_b, value)
        elif kind == "V":
            circuit.add_voltage_source(name, node_a, node_b, value)
        elif kind == "I":
            circuit.add_current_source(name, node_a, node_b, value)
        elif kind == "C":
            circuit.add_capacitor(name, node_a, node_b, value)
        elif kind == "L":
            circuit.add_inductor(name, node_a, node_b, value)
        else:
            raise ValueError(f"Unsupported component type: {name}")
    return circuit


def _solve_linear_system(matrix: List[List[float]], vector: List[float]) -> List[float]:
    size = len(vector)
    augmented = [row[:] + [vector[idx]] for idx, row in enumerate(matrix)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            raise ValueError("Singular matrix in circuit solve")
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_val = augmented[col][col]
        for k in range(col, size + 1):
            augmented[col][k] /= pivot_val
        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0.0:
                continue
            for k in range(col, size + 1):
                augmented[row][k] -= factor * augmented[col][k]

    return [augmented[row][size] for row in range(size)]


def _solve_linear_system_complex(matrix: List[List[complex]], vector: List[complex]) -> List[complex]:
    size = len(vector)
    augmented = [row[:] + [vector[idx]] for idx, row in enumerate(matrix)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot][col]) < 1e-18:
            raise ValueError("Singular matrix in AC circuit solve")
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_val = augmented[col][col]
        for k in range(col, size + 1):
            augmented[col][k] /= pivot_val
        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0.0:
                continue
            for k in range(col, size + 1):
                augmented[row][k] -= factor * augmented[col][k]

    return [augmented[row][size] for row in range(size)]


def simulate_dc(circuit: Circuit, memory: Optional[MemoryStore] = None) -> CircuitResult:
    nodes = sorted(name for name in circuit.nodes if name != "0")
    node_index = {name: idx for idx, name in enumerate(nodes)}
    n = len(nodes)
    m = len(circuit.voltage_sources)
    size = n + m

    if memory:
        memory.log_event(
            "circuit_sim",
            f"DC simulation started with {n} nodes, {len(circuit.resistors)} resistors, {m} sources.",
            {"nodes": nodes},
        )

    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    vector = [0.0 for _ in range(size)]

    def idx(node: str) -> Optional[int]:
        return node_index.get(node)

    for resistor in circuit.resistors:
        if resistor.ohms <= 0:
            raise ValueError(f"Invalid resistance for {resistor.name}")
        g = 1.0 / resistor.ohms
        a = idx(resistor.node_a)
        b = idx(resistor.node_b)
        if a is not None:
            matrix[a][a] += g
        if b is not None:
            matrix[b][b] += g
        if a is not None and b is not None:
            matrix[a][b] -= g
            matrix[b][a] -= g

    for source in circuit.current_sources:
        a = idx(source.node_pos)
        b = idx(source.node_neg)
        if a is not None:
            vector[a] += source.amps
        if b is not None:
            vector[b] -= source.amps

    for s_idx, source in enumerate(circuit.voltage_sources):
        row = n + s_idx
        a = idx(source.node_pos)
        b = idx(source.node_neg)
        if a is not None:
            matrix[a][row] += 1.0
            matrix[row][a] += 1.0
        if b is not None:
            matrix[b][row] -= 1.0
            matrix[row][b] -= 1.0
        vector[row] = source.volts

    solution = _solve_linear_system(matrix, vector)
    node_voltages = {"0": 0.0}
    for name, index in node_index.items():
        node_voltages[name] = solution[index]

    source_currents: Dict[str, float] = {}
    for s_idx, source in enumerate(circuit.voltage_sources):
        source_currents[source.name] = solution[n + s_idx]

    resistor_currents: Dict[str, float] = {}
    for resistor in circuit.resistors:
        v_a = node_voltages.get(resistor.node_a, 0.0)
        v_b = node_voltages.get(resistor.node_b, 0.0)
        resistor_currents[resistor.name] = (v_a - v_b) / resistor.ohms

    if memory:
        memory.log_event(
            "circuit_sim",
            "DC simulation completed.",
            {"node_voltages": node_voltages, "source_currents": source_currents},
        )

    return CircuitResult(
        node_voltages=node_voltages,
        source_currents=source_currents,
        resistor_currents=resistor_currents,
    )


def simulate_ac(circuit: Circuit, freq_hz: float) -> Dict[str, complex]:
    if freq_hz <= 0.0:
        raise ValueError("freq_hz must be > 0")
    nodes = sorted(name for name in circuit.nodes if name != "0")
    node_index = {name: idx for idx, name in enumerate(nodes)}
    n = len(nodes)
    m = len(circuit.voltage_sources)
    size = n + m

    matrix: List[List[complex]] = [[0.0 + 0.0j for _ in range(size)] for _ in range(size)]
    vector: List[complex] = [0.0 + 0.0j for _ in range(size)]

    def idx(node: str) -> Optional[int]:
        return node_index.get(node)

    for resistor in circuit.resistors:
        if resistor.ohms <= 0:
            raise ValueError(f"Invalid resistance for {resistor.name}")
        g = 1.0 / resistor.ohms
        a = idx(resistor.node_a)
        b = idx(resistor.node_b)
        if a is not None:
            matrix[a][a] += g
        if b is not None:
            matrix[b][b] += g
        if a is not None and b is not None:
            matrix[a][b] -= g
            matrix[b][a] -= g

    omega = 2.0 * math.pi * freq_hz
    for capacitor in circuit.capacitors:
        if capacitor.farads <= 0:
            raise ValueError(f"Invalid capacitance for {capacitor.name}")
        y = 1j * omega * capacitor.farads
        a = idx(capacitor.node_a)
        b = idx(capacitor.node_b)
        if a is not None:
            matrix[a][a] += y
        if b is not None:
            matrix[b][b] += y
        if a is not None and b is not None:
            matrix[a][b] -= y
            matrix[b][a] -= y

    for inductor in circuit.inductors:
        if inductor.henrys <= 0:
            raise ValueError(f"Invalid inductance for {inductor.name}")
        y = 1.0 / (1j * omega * inductor.henrys)
        a = idx(inductor.node_a)
        b = idx(inductor.node_b)
        if a is not None:
            matrix[a][a] += y
        if b is not None:
            matrix[b][b] += y
        if a is not None and b is not None:
            matrix[a][b] -= y
            matrix[b][a] -= y

    for source in circuit.current_sources:
        a = idx(source.node_pos)
        b = idx(source.node_neg)
        if a is not None:
            vector[a] += source.amps
        if b is not None:
            vector[b] -= source.amps

    for s_idx, source in enumerate(circuit.voltage_sources):
        row = n + s_idx
        a = idx(source.node_pos)
        b = idx(source.node_neg)
        if a is not None:
            matrix[a][row] += 1.0
            matrix[row][a] += 1.0
        if b is not None:
            matrix[b][row] -= 1.0
            matrix[row][b] -= 1.0
        vector[row] = source.volts

    solution = _solve_linear_system_complex(matrix, vector)
    node_voltages: Dict[str, complex] = {"0": 0.0 + 0.0j}
    for name, index in node_index.items():
        node_voltages[name] = solution[index]
    return node_voltages


def simulate_transient(
    circuit: Circuit,
    t_stop_s: float,
    dt_s: float,
    initial_voltages: Optional[Dict[str, float]] = None,
) -> TransientResult:
    if t_stop_s <= 0.0 or dt_s <= 0.0:
        raise ValueError("t_stop_s and dt_s must be > 0")
    steps = int(t_stop_s / dt_s)
    nodes = sorted(name for name in circuit.nodes if name != "0")
    node_index = {name: idx for idx, name in enumerate(nodes)}
    n = len(nodes)
    m = len(circuit.voltage_sources)
    size = n + m
    l_count = len(circuit.inductors)
    size = n + m + l_count

    prev = {name: 0.0 for name in nodes}
    if initial_voltages:
        for name, value in initial_voltages.items():
            if name in prev:
                prev[name] = value

    prev_inductor_currents = {inductor.name: 0.0 for inductor in circuit.inductors}

    times: List[float] = []
    voltages: List[Dict[str, float]] = []

    def idx(node: str) -> Optional[int]:
        return node_index.get(node)

    for step in range(steps + 1):
        time = step * dt_s
        matrix = [[0.0 for _ in range(size)] for _ in range(size)]
        vector = [0.0 for _ in range(size)]

        for resistor in circuit.resistors:
            if resistor.ohms <= 0:
                raise ValueError(f"Invalid resistance for {resistor.name}")
            g = 1.0 / resistor.ohms
            a = idx(resistor.node_a)
            b = idx(resistor.node_b)
            if a is not None:
                matrix[a][a] += g
            if b is not None:
                matrix[b][b] += g
            if a is not None and b is not None:
                matrix[a][b] -= g
                matrix[b][a] -= g

        for capacitor in circuit.capacitors:
            if capacitor.farads <= 0:
                raise ValueError(f"Invalid capacitance for {capacitor.name}")
            g = capacitor.farads / dt_s
            a = idx(capacitor.node_a)
            b = idx(capacitor.node_b)
            v_a = prev.get(capacitor.node_a, 0.0)
            v_b = prev.get(capacitor.node_b, 0.0)
            v_prev = v_a - v_b
            if a is not None:
                matrix[a][a] += g
                vector[a] += g * v_prev
            if b is not None:
                matrix[b][b] += g
                vector[b] -= g * v_prev
            if a is not None and b is not None:
                matrix[a][b] -= g
                matrix[b][a] -= g

        for l_idx, inductor in enumerate(circuit.inductors):
            if inductor.henrys <= 0:
                raise ValueError(f"Invalid inductance for {inductor.name}")
            a = idx(inductor.node_a)
            b = idx(inductor.node_b)
            row = n + m + l_idx
            g = inductor.henrys / dt_s
            i_prev = prev_inductor_currents[inductor.name]

            if a is not None:
                matrix[a][row] += 1.0
                matrix[row][a] += 1.0
            if b is not None:
                matrix[b][row] -= 1.0
                matrix[row][b] -= 1.0
            matrix[row][row] -= g
            vector[row] = -g * i_prev

        for source in circuit.current_sources:
            a = idx(source.node_pos)
            b = idx(source.node_neg)
            if a is not None:
                vector[a] += source.amps
            if b is not None:
                vector[b] -= source.amps

        for s_idx, source in enumerate(circuit.voltage_sources):
            row = n + s_idx
            a = idx(source.node_pos)
            b = idx(source.node_neg)
            if a is not None:
                matrix[a][row] += 1.0
                matrix[row][a] += 1.0
            if b is not None:
                matrix[b][row] -= 1.0
                matrix[row][b] -= 1.0
            vector[row] = source.volts

        solution = _solve_linear_system(matrix, vector)
        node_voltages = {"0": 0.0}
        for name, index in node_index.items():
            node_voltages[name] = solution[index]
        prev = {name: node_voltages[name] for name in nodes}

        for l_idx, inductor in enumerate(circuit.inductors):
            prev_inductor_currents[inductor.name] = solution[n + m + l_idx]

        times.append(time)
        voltages.append(node_voltages)

    return TransientResult(times_s=times, node_voltages=voltages)


def generate_fuselage_power_netlist(
    payload_power_w: float,
    bus_voltage_v: float = 12.0,
    battery_voltage_v: float = 16.0,
    bus_efficiency: float = 0.92,
) -> List[str]:
    if payload_power_w <= 0:
        raise ValueError("payload_power_w must be > 0")
    if bus_voltage_v <= 0 or battery_voltage_v <= 0:
        raise ValueError("voltages must be > 0")
    if not 0.1 <= bus_efficiency <= 1.0:
        raise ValueError("bus_efficiency must be between 0.1 and 1.0")

    effective_power = payload_power_w / bus_efficiency
    load_resistance = (bus_voltage_v**2) / effective_power

    return [
        f"Vbat vbatt 0 {battery_voltage_v}",
        "Rbus vbatt vbus 0.05",
        f"Rload vbus 0 {load_resistance}",
    ]


def build_advanced_fuselage_circuit(
    payload_power_w: float,
    processor_power_w: float,
    bus_voltage_v: float = 12.0,
    battery_voltage_v: float = 16.0,
    bus_efficiency: float = 0.92,
    cnt_length_m: float = 0.08,
    cnt_area_m2: float = 1.2e-6,
    cnt_resistivity_ohm_m: float = 1.5e-6,
    cnt_temp_c: float = 35.0,
    tan_sheet_resistance: float = 25.0,
    tan_length_m: float = 0.01,
    tan_width_m: float = 0.002,
    tan_temp_c: float = 35.0,
) -> Circuit:
    if payload_power_w <= 0.0 or processor_power_w <= 0.0:
        raise ValueError("payload_power_w and processor_power_w must be > 0")
    circuit = Circuit()
    circuit.add_voltage_source("Vbat", "vbatt", "0", battery_voltage_v)
    circuit.add_resistor("Rbus", "vbatt", "vbus", 0.05)

    cnt = CNTInterconnect(
        name="Rcnt",
        node_a="vbus",
        node_b="vcore",
        length_m=cnt_length_m,
        area_m2=cnt_area_m2,
        resistivity_ohm_m=cnt_resistivity_ohm_m,
        temp_c=cnt_temp_c,
    )
    circuit.add_cnt_interconnect(cnt)

    tan = TaNResistor(
        name="Rtan",
        node_a="vcore",
        node_b="0",
        sheet_resistance_ohms_per_sq=tan_sheet_resistance,
        length_m=tan_length_m,
        width_m=tan_width_m,
        temp_c=tan_temp_c,
    )
    circuit.add_tan_resistor(tan)

    processor = ProcessingUnitLoad(
        name="Rcpu",
        node_pos="vcore",
        node_neg="0",
        power_w=processor_power_w,
        nominal_voltage_v=bus_voltage_v,
        efficiency=bus_efficiency,
    )
    circuit.add_processing_unit(processor)

    payload = ProcessingUnitLoad(
        name="Rpayload",
        node_pos="vbus",
        node_neg="0",
        power_w=payload_power_w,
        nominal_voltage_v=bus_voltage_v,
        efficiency=bus_efficiency,
    )
    circuit.add_processing_unit(payload)

    return circuit


def build_photonic_processor_circuit(
    processor: PhotonicProcessor,
    bus_voltage_v: float = 12.0,
    ground_node: str = "0",
) -> Circuit:
    if bus_voltage_v <= 0.0:
        raise ValueError("bus_voltage_v must be > 0")
    circuit = Circuit()
    circuit.add_voltage_source("Vbus", "vbus", ground_node, bus_voltage_v)
    load = ProcessingUnitLoad(
        name=f"R{processor.name}",
        node_pos="vbus",
        node_neg=ground_node,
        power_w=processor.electrical_power_w(),
        nominal_voltage_v=bus_voltage_v,
        efficiency=1.0,
    )
    circuit.add_processing_unit(load)
    return circuit


def simulate_photonic_burst(
    processor: PhotonicProcessor,
    duration_s: float,
    duty_cycle: float = 0.5,
) -> Dict[str, float]:
    if duration_s <= 0.0:
        raise ValueError("duration_s must be > 0")
    if not 0.0 < duty_cycle <= 1.0:
        raise ValueError("duty_cycle must be within (0, 1]")
    avg_power = processor.total_power_w() * duty_cycle
    energy_j = avg_power * duration_s
    return {
        "avg_power_w": avg_power,
        "energy_j": energy_j,
        "thermal_margin_w": processor.thermal_margin_w(),
    }


def _clone_circuit_with_resistors(
    circuit: Circuit,
    resistors: List[Resistor],
) -> Circuit:
    cloned = Circuit()
    for node in circuit.nodes:
        cloned.add_node(node)
    for source in circuit.voltage_sources:
        cloned.add_voltage_source(source.name, source.node_pos, source.node_neg, source.volts)
    for source in circuit.current_sources:
        cloned.add_current_source(source.name, source.node_pos, source.node_neg, source.amps)
    for capacitor in circuit.capacitors:
        cloned.add_capacitor(capacitor.name, capacitor.node_a, capacitor.node_b, capacitor.farads)
    for inductor in circuit.inductors:
        cloned.add_inductor(inductor.name, inductor.node_a, inductor.node_b, inductor.henrys)
    for resistor in resistors:
        cloned.add_resistor(resistor.name, resistor.node_a, resistor.node_b, resistor.ohms)
    return cloned


def simulate_electro_thermal_dc(
    circuit: Circuit,
    thermal_nodes: Tuple[ThermalNode, ...],
    thermal_resistors: Tuple[ElectroThermalResistor, ...],
    extra_loads: Tuple[ThermalLoad, ...] = (),
    max_iters: int = 20,
    tol_c: float = 0.05,
) -> ElectroThermalResult:
    if max_iters <= 0:
        raise ValueError("max_iters must be > 0")
    temps = {node.name: node.ambient_c for node in thermal_nodes}
    fixed_resistors = [
        resistor for resistor in circuit.resistors if resistor.name not in {r.name for r in thermal_resistors}
    ]

    for iteration in range(1, max_iters + 1):
        updated = []
        for resistor in thermal_resistors:
            temp_c = temps.get(resistor.thermal_node, resistor.ref_temp_c)
            updated.append(
                Resistor(
                    name=resistor.name,
                    node_a=resistor.node_a,
                    node_b=resistor.node_b,
                    ohms=resistor.resistance(temp_c),
                )
            )
        working = _clone_circuit_with_resistors(circuit, fixed_resistors + updated)
        result = simulate_dc(working)

        loads = list(extra_loads)
        for resistor in updated:
            current = result.resistor_currents.get(resistor.name, 0.0)
            power = (current**2) * resistor.ohms
            thermal_node = next(
                item.thermal_node for item in thermal_resistors if item.name == resistor.name
            )
            loads.append(ThermalLoad(name=resistor.name, node=thermal_node, power_w=power))

        new_temps = simulate_thermal_steady_state(thermal_nodes, tuple(loads))
        max_delta = max(
            abs(new_temps[name] - temps.get(name, value)) for name, value in new_temps.items()
        )
        temps = new_temps
        if max_delta <= tol_c:
            return ElectroThermalResult(circuit=result, temperatures_c=temps, iterations=iteration)

    return ElectroThermalResult(circuit=result, temperatures_c=temps, iterations=max_iters)
