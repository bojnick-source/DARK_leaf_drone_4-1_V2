# Mechanical Engineering Calculations (Reference)

## Axial Stress / Strain
- $\sigma = \frac{F}{A}$
- $\varepsilon = \frac{\Delta L}{L}$
- Hooke: $\sigma = E \varepsilon$

## Torsion (solid circular shaft)
- Shear stress: $\tau_{max} = \frac{T r}{J}$
- Polar inertia: $J = \frac{\pi r^4}{2}$
- Twist: $\theta = \frac{T L}{G J}$

## Beam Bending (Euler-Bernoulli)
- Curvature: $\kappa = \frac{M}{E I}$
- Max stress: $\sigma_{max} = \frac{M c}{I}$

Mathlib reference:
- `structures_beam_bending_stress`: $\sigma = \frac{M c}{I}$

## Deflection (common cases)
- Cantilever, end load: $\delta = \frac{F L^3}{3 E I}$
- Simply supported, center load: $\delta = \frac{F L^3}{48 E I}$

Mathlib reference:
- `risf_robot_deflection_compliance_template`: $\delta = C_{lin} \cdot F$ (calibrated compliance)

## Rigidity Metrics
- Flexural rigidity: $E I$
- Torsional rigidity: $G J$

## Reference
- See [manufacturing/mathlib_v0.yaml](manufacturing/mathlib_v0.yaml) for additional formulae and references.
