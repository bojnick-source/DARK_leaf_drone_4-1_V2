from reidce.circuitry import (
    CircuitBoard,
    CircuitBoardTrace,
    Capacitor,
    CNTInterconnect,
    ElectroThermalResistor,
    Inductor,
    PhotonicModulator,
    PhotonicProcessor,
    PhotonicWaveguide,
    PowerDistributionNetwork,
    PowerRail,
    RailLoad,
    ThermalLoad,
    ThermalNode,
    build_photonic_processor_circuit,
    TaNResistor,
    build_advanced_fuselage_circuit,
    generate_fuselage_power_netlist,
    parse_netlist,
    simulate_photonic_burst,
    simulate_ac,
    simulate_electro_thermal_dc,
    simulate_transient,
    simulate_thermal_steady_state,
    simulate_dc,
)


def test_dc_simulation_simple_divider() -> None:
    netlist = [
        "V1 vin 0 10",
        "R1 vin vout 1000",
        "R2 vout 0 1000",
    ]
    circuit = parse_netlist(netlist)
    result = simulate_dc(circuit)
    assert abs(result.node_voltages["vout"] - 5.0) < 1e-6


def test_generate_fuselage_power_netlist() -> None:
    netlist = generate_fuselage_power_netlist(payload_power_w=48.0, bus_voltage_v=12.0)
    circuit = parse_netlist(netlist)
    result = simulate_dc(circuit)
    assert result.node_voltages["vbus"] > 0.0


def test_cnt_and_tan_resistance_models() -> None:
    cnt = CNTInterconnect(
        name="Rcnt",
        node_a="a",
        node_b="b",
        length_m=0.1,
        area_m2=1e-6,
        resistivity_ohm_m=1.5e-6,
        temp_c=35.0,
    )
    tan = TaNResistor(
        name="Rtan",
        node_a="a",
        node_b="b",
        sheet_resistance_ohms_per_sq=25.0,
        length_m=0.01,
        width_m=0.002,
        temp_c=35.0,
    )
    assert cnt.resistance() > 0.0
    assert tan.resistance() > 0.0


def test_advanced_fuselage_circuit_builds() -> None:
    circuit = build_advanced_fuselage_circuit(payload_power_w=30.0, processor_power_w=20.0)
    result = simulate_dc(circuit)
    assert result.node_voltages["vbus"] > 0.0


def test_photonic_processor_budget() -> None:
    waveguide = PhotonicWaveguide(name="wg0", length_m=0.02, loss_db_per_cm=0.6)
    modulator = PhotonicModulator(name="m0", drive_voltage_v=1.5, capacitance_f=0.4e-12, data_rate_hz=25e9)
    processor = PhotonicProcessor(
        name="pho",
        optical_input_mw=10.0,
        optical_efficiency=0.6,
        thermal_budget_w=5.0,
        modulators=(modulator,),
        waveguides=(waveguide,),
    )
    assert processor.optical_output_w() < processor.optical_power_w()
    assert processor.electrical_power_w() > 0.0

    circuit = build_photonic_processor_circuit(processor)
    result = simulate_dc(circuit)
    assert result.node_voltages["vbus"] > 0.0


def test_board_trace_loss() -> None:
    trace = CircuitBoardTrace(name="t0", length_m=0.05, width_m=0.002, thickness_m=35e-6)
    board = CircuitBoard(name="board", traces=(trace,), losses_w=0.1)
    loss = board.trace_loss_w(current_a=2.0)
    assert loss > 0.1


def test_power_distribution_network() -> None:
    rails = (
        PowerRail(name="1v8", voltage_v=1.8, max_current_a=5.0),
        PowerRail(name="3v3", voltage_v=3.3, max_current_a=3.0),
    )
    loads = {
        "1v8": (RailLoad(name="fpga", power_w=4.0),),
        "3v3": (RailLoad(name="io", power_w=2.0),),
    }
    pdn = PowerDistributionNetwork(rails=rails, loads=loads, regulator_efficiency=0.9)
    currents = pdn.rail_current_map()
    assert currents["1v8"] > 0.0
    assert pdn.total_input_power_w() > 0.0
    pdn.validate()


def test_thermal_steady_state() -> None:
    nodes = (
        ThermalNode(name="cpu", ambient_c=25.0, r_th_c_per_w=4.0),
        ThermalNode(name="pho", ambient_c=25.0, r_th_c_per_w=6.0),
    )
    loads = (
        ThermalLoad(name="cpu_load", node="cpu", power_w=2.0),
        ThermalLoad(name="pho_load", node="pho", power_w=1.2),
    )
    temps = simulate_thermal_steady_state(nodes, loads)
    assert temps["cpu"] > 25.0
    assert temps["pho"] > 25.0


def test_photonic_burst() -> None:
    waveguide = PhotonicWaveguide(name="wg1", length_m=0.01, loss_db_per_cm=0.4)
    modulator = PhotonicModulator(name="m1", drive_voltage_v=1.2, capacitance_f=0.3e-12, data_rate_hz=20e9)
    processor = PhotonicProcessor(
        name="pho2",
        optical_input_mw=8.0,
        optical_efficiency=0.65,
        thermal_budget_w=4.0,
        modulators=(modulator,),
        waveguides=(waveguide,),
    )
    result = simulate_photonic_burst(processor, duration_s=0.01, duty_cycle=0.4)
    assert result["energy_j"] > 0.0


def test_ac_response_rc() -> None:
    circuit = parse_netlist(
        [
            "V1 vin 0 1",
            "R1 vin vout 1000",
            "C1 vout 0 1e-6",
        ]
    )
    low = simulate_ac(circuit, freq_hz=1.0)
    high = simulate_ac(circuit, freq_hz=1e6)
    assert abs(low["vout"]) > abs(high["vout"])


def test_transient_rc_charging() -> None:
    circuit = parse_netlist(
        [
            "V1 vin 0 1",
            "R1 vin vout 1000",
            "C1 vout 0 1e-6",
        ]
    )
    result = simulate_transient(circuit, t_stop_s=0.01, dt_s=0.0001)
    assert result.node_voltages[0]["vout"] < result.node_voltages[-1]["vout"]
    assert result.node_voltages[-1]["vout"] > 0.8


def test_rlc_transient_step() -> None:
    circuit = parse_netlist(
        [
            "V1 vin 0 1",
            "R1 vin vout 10",
            "L1 vout n1 1e-3",
            "C1 n1 0 1e-6",
        ]
    )
    result = simulate_transient(circuit, t_stop_s=0.002, dt_s=1e-5)
    assert result.node_voltages[-1]["n1"] > 0.0


def test_electro_thermal_dc_loop() -> None:
    circuit = parse_netlist(
        [
            "V1 vin 0 12",
            "Rload vin 0 4",
        ]
    )
    thermal_nodes = (
        ThermalNode(name="hotspot", ambient_c=25.0, r_th_c_per_w=3.0),
    )
    thermal_resistors = (
        ElectroThermalResistor(
            name="Rload",
            node_a="vin",
            node_b="0",
            base_ohms=4.0,
            temp_coeff_per_c=0.004,
            ref_temp_c=25.0,
            thermal_node="hotspot",
        ),
    )
    result = simulate_electro_thermal_dc(
        circuit,
        thermal_nodes=thermal_nodes,
        thermal_resistors=thermal_resistors,
        max_iters=10,
    )
    assert result.temperatures_c["hotspot"] > 25.0
