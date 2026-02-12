from reidce.circuitry import (
    BoardComponent,
    CircuitBoardMap,
    Net,
    NetConnection,
)


def test_board_component_count() -> None:
    comps = (
        BoardComponent(ref_des="U1", package="QFN-48", x_mm=10.0, y_mm=10.0),
        BoardComponent(ref_des="R1", package="0603", x_mm=15.0, y_mm=12.0),
        BoardComponent(ref_des="C1", package="0402", x_mm=20.0, y_mm=10.0),
    )
    board = CircuitBoardMap(
        name="main_pcb", width_mm=50.0, height_mm=40.0, components=comps, nets=()
    )
    assert board.component_count() == 3


def test_component_lookup() -> None:
    comps = (
        BoardComponent(ref_des="U1", package="QFN-48", x_mm=10.0, y_mm=10.0),
        BoardComponent(ref_des="R1", package="0603", x_mm=15.0, y_mm=12.0),
    )
    board = CircuitBoardMap(
        name="pcb", width_mm=50.0, height_mm=40.0, components=comps, nets=()
    )
    assert board.component_by_ref("U1") is not None
    assert board.component_by_ref("U1").package == "QFN-48"  # type: ignore[union-attr]
    assert board.component_by_ref("X9") is None


def test_net_connectivity() -> None:
    comps = (
        BoardComponent(ref_des="U1", package="QFN-48", x_mm=10.0, y_mm=10.0),
        BoardComponent(ref_des="R1", package="0603", x_mm=15.0, y_mm=12.0),
        BoardComponent(ref_des="C1", package="0402", x_mm=20.0, y_mm=10.0),
    )
    nets = (
        Net(
            name="VCC",
            connections=(
                NetConnection(ref_des="U1", pad="1"),
                NetConnection(ref_des="R1", pad="1"),
            ),
        ),
        Net(
            name="GND",
            connections=(
                NetConnection(ref_des="U1", pad="48"),
                NetConnection(ref_des="C1", pad="2"),
            ),
        ),
    )
    board = CircuitBoardMap(
        name="pcb", width_mm=50.0, height_mm=40.0, components=comps, nets=nets
    )
    assert board.net_count() == 2
    assert board.net_by_name("VCC") is not None
    u1_nets = board.nets_for_component("U1")
    assert len(u1_nets) == 2


def test_manhattan_distance() -> None:
    comps = (
        BoardComponent(ref_des="U1", package="QFN-48", x_mm=10.0, y_mm=10.0),
        BoardComponent(ref_des="R1", package="0603", x_mm=20.0, y_mm=15.0),
    )
    board = CircuitBoardMap(
        name="pcb", width_mm=50.0, height_mm=40.0, components=comps, nets=()
    )
    d = board.manhattan_distance_mm("U1", "R1")
    assert abs(d - 15.0) < 1e-9


def test_board_validation_pass() -> None:
    comps = (
        BoardComponent(ref_des="U1", package="QFN-48", x_mm=10.0, y_mm=10.0),
        BoardComponent(ref_des="R1", package="0603", x_mm=15.0, y_mm=12.0),
    )
    nets = (
        Net(
            name="VCC",
            connections=(
                NetConnection(ref_des="U1", pad="1"),
                NetConnection(ref_des="R1", pad="1"),
            ),
        ),
    )
    board = CircuitBoardMap(
        name="pcb", width_mm=50.0, height_mm=40.0, components=comps, nets=nets
    )
    assert board.validate() == []


def test_board_validation_fail_missing_ref() -> None:
    comps = (
        BoardComponent(ref_des="U1", package="QFN-48", x_mm=10.0, y_mm=10.0),
    )
    nets = (
        Net(
            name="VCC",
            connections=(
                NetConnection(ref_des="U1", pad="1"),
                NetConnection(ref_des="R1", pad="1"),  # R1 not in components
            ),
        ),
    )
    board = CircuitBoardMap(
        name="pcb", width_mm=50.0, height_mm=40.0, components=comps, nets=nets
    )
    errors = board.validate()
    assert len(errors) == 1
    assert "R1" in errors[0]
