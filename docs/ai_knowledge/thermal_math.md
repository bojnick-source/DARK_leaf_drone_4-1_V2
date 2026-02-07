# Thermal Calculations (Reference)

## Steady-State Temperature Rise

- $\Delta T = P \cdot R_{th}$
- $T = T_{amb} + \Delta T$

## Thermal Margin

- $M = T_{limit} - T$

## Electro-Thermal Coupling (iterative)

1. Compute electrical losses $P = I^2 R(T)$
2. Update $T$ with $\Delta T = P \cdot R_{th}$
3. Iterate until $|\Delta T|$ converges
