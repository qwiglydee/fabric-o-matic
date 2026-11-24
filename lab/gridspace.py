import numpy as np
from numpy.typing import NDArray


def space_coords(xspace: NDArray, yspace: NDArray):
    return np.dstack(np.meshgrid(xspace, yspace, indexing="xy"))  # (h×w×2)


def gridspace(xmin: float, xmax: float, xres: int, ymin: float, ymax: float, yres: int):
    """Create array (yres×xres) of coords of pixel centers
    (xspace(xres), yspace(xres), gspace(yres×xres×2))
    """
    xspace = np.linspace(xmin, xmax, xres, endpoint=False) + 0.5 / xres
    yspace = np.linspace(ymin, ymax, yres, endpoint=False) + 0.5 / yres
    gspace = space_coords(xspace, yspace)
    return xspace, yspace, gspace


def space_spacing(lspace: NDArray):
    """Estimate bounds and spacing of a linspace
    (lmin, lmax, lspacing)
    """
    lmin = np.min(lspace)
    lmax = np.max(lspace)
    lspc = (lmax - lmin) / (lspace.size - 1)
    return lmin, lmax, lspc


dot2 = lambda v: (v * v).sum(axis=-1)


def space_sample(gspace: NDArray, sample: NDArray):
    """Closest point in space
    (idx, coords)
    """
    idx = np.argmin(dot2(gspace - sample))
    idx = np.unravel_index(idx, gspace.shape[:-1])
    return idx, gspace[idx]
