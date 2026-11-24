"""Creating mesh from grid
by Claude
"""

import numpy as np
from numpy.typing import NDArray


def gridmesh(coords: NDArray):
    assert len(coords.shape) == 3 and coords.shape[2] == 2
    h, w, d = coords.shape

    # 1. Vertices: (h*w, 3), z = 0 for a flat mesh
    vertices = np.zeros((h * w, 3), dtype=np.float32)
    vertices[:, :2] = coords.reshape(-1, 2)

    # 2. Triangle indices: split each grid cell into two triangles
    idx = np.arange(h * w, dtype=np.uint32).reshape(h, w)
    a = idx[:-1, :-1]  # top-left
    b = idx[:-1, 1:]  # top-right
    c = idx[1:, :-1]  # bottom-left
    d = idx[1:, 1:]  # bottom-right

    tri1 = np.stack([a, b, c], axis=-1).reshape(-1, 3)
    tri2 = np.stack([b, d, c], axis=-1).reshape(-1, 3)
    indices = np.concatenate([tri1, tri2]).astype(np.uint32)

    return vertices, indices
