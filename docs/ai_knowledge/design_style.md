# Design Style Preferences

## Goals
- Prioritize efficiency per unit mass and per unit power.
- Favor deterministic, auditable calculations over black-box heuristics.
- Prefer modular subsystems with clear interface boundaries.

## Patterns You Like
- Redundancy (triple-wire control or voting logic).
- Simple, robust baselines before adding higher-fidelity layers.
- Clear visual status indicators linked to numeric data.

## Recommended Next-Move Heuristics
1. **Efficiency first**: improve $\eta$ by addressing largest loss term (drag, conversion loss, thermal margin).
2. **Stability second**: only increase performance after stability margins are proven.
3. **Scale last**: scale capacity after proving a stable, efficient baseline.

## Helpful Pattern Recognition Tips
- If $T/W < 1.0$, increase thrust or reduce mass.
- If $L/D$ drops, reduce $C_D$ (smooth geometry) or increase $C_L$ within stall margin.
- If thermal margin is low, reduce power density or improve heat rejection.
- If wind-ship net force is negative, adjust heading or increase sail area.
- If kite power drops, optimize reel speed and $C_L/C_D$.
