from __future__ import annotations

import numpy as np
import scipy.sparse as sp


def density_filter_matrix(nely: int, nelx: int, rmin: float) -> sp.csr_matrix:
    """
    Build sparse density filter H with radius rmin.

    Flattening convention:
      idx(y,x) = x*nely + y   (Fortran-order flatten)
    """
    if rmin <= 0:
        raise ValueError("rmin must be > 0")

    ne = nelx * nely
    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []

    def idx(y: int, x: int) -> int:
        return x * nely + y

    r = int(np.floor(rmin))
    for x in range(nelx):
        for y in range(nely):
            e1 = idx(y, x)
            xmin = max(x - r, 0)
            xmax = min(x + r, nelx - 1)
            ymin = max(y - r, 0)
            ymax = min(y + r, nely - 1)
            for xx in range(xmin, xmax + 1):
                for yy in range(ymin, ymax + 1):
                    e2 = idx(yy, xx)
                    dist = np.sqrt((x - xx) ** 2 + (y - yy) ** 2)
                    w = max(0.0, rmin - dist)
                    if w > 0:
                        rows.append(e1)
                        cols.append(e2)
                        vals.append(w)

    H = sp.coo_matrix((vals, (rows, cols)), shape=(ne, ne)).tocsr()
    return H


def filter_stats(H: sp.csr_matrix) -> np.ndarray:
    Hs = np.asarray(H.sum(axis=1)).ravel()
    if np.any(Hs <= 0):
        raise RuntimeError("Filter has zero row-sums; choose larger rmin or check grid.")
    return Hs


def apply_density_filter(H: sp.csr_matrix, x: np.ndarray) -> np.ndarray:
    nely, nelx = x.shape
    xf = x.reshape(-1, order="F")
    Hs = filter_stats(H)
    x_phys = (H @ xf) / Hs
    return x_phys.reshape((nely, nelx), order="F")


def chain_rule_grad_through_density_filter(H: sp.csr_matrix, dfdx_phys: np.ndarray) -> np.ndarray:
    """
    x_phys = (H x)/Hs  =>  df/dx = H^T ( (df/dx_phys)/Hs )
    """
    nely, nelx = dfdx_phys.shape
    g = dfdx_phys.reshape(-1, order="F")
    Hs = filter_stats(H)
    gx = H.T @ (g / Hs)
    return np.asarray(gx).reshape((nely, nelx), order="F")
