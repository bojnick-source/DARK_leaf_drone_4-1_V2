# Controls & Autopilot (Reference)

## PID Controller

- $u(t) = K_p e(t) + K_i \int e(t) dt + K_d \frac{d e}{dt}$

## Discrete PID

- $u_k = K_p e_k + K_i \sum e_k \Delta t + K_d \frac{e_k - e_{k-1}}{\Delta t}$

## Stability Heuristic

- Keep bandwidths separated: attitude loop \> velocity loop \> position loop

## Heading Error Wrap

- $e_\psi = \text{wrap}(\psi_{cmd} - \psi)$ into $[-\pi, \pi]$
