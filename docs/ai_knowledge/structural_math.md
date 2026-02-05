# Structural Engineering (Flexion, Deflection, Rigidity)

## Section Properties
- Rectangular: $I = \frac{b h^3}{12}$
- Circular: $I = \frac{\pi r^4}{4}$

## Beam Deflection (Euler-Bernoulli)
- $E I \frac{d^4 y}{d x^4} = q(x)$

## Flexural Stress
- $\sigma = \frac{M y}{I}$

Mathlib reference:
- `structures_beam_bending_stress`: $\sigma = \frac{M c}{I}$

## Buckling (Euler)
- $P_{cr} = \frac{\pi^2 E I}{(K L)^2}$

Mathlib reference:
- `structures_plate_buckling_stress_template`: $\sigma_{cr} = \frac{k \pi^2 E}{12(1-\nu^2)} (t/b)^2$

## Effective Length Factor (common)
- Pinned-pinned: $K=1.0$
- Fixed-fixed: $K=0.5$
- Fixed-pinned: $K\approx0.7$
- Cantilever: $K=2.0$

## Deflection Limits
- Serviceability: $\delta_{max} \leq L/\alpha$ (common $\alpha\in[200,500]$)

## Rigidity & Safety
- Stiffness: $k = \frac{F}{\delta}$
- Safety factor: $SF = \frac{\sigma_{allow}}{\sigma_{max}}$

## Reference
- See [manufacturing/mathlib_v0.yaml](manufacturing/mathlib_v0.yaml) for detailed derivations and references.
