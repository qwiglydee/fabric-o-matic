from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray


class Projections(NamedTuple):
    """All of projection data"""

    smp: NDArray  # sample points (num×dim)
    arc: NDArray  # path along curve, =t (num×1)
    pnt: NDArray  # projection/closest point (num×dim)
    dsq: NDArray  # disquance (num×1)
    flw: NDArray  # tangential flow (num×dim)
    sgn: NDArray  # orientation (num×1)

    @property
    def sdist(self) -> float | NDArray:
        return self.sgn * np.sqrt(self.dsq)

    @property
    def __len__(self):
        return self.smp.shape[0]


def saveproj(proj: Projections, filename: str):
    np.savez(filename, smp=proj.smp, arc=proj.arc, pnt=proj.pnt, dsq=proj.dsq, flw=proj.flw, sgn=proj.sgn)


def loadproj(filename: str):
    data = np.load(filename)
    return Projections(smp=data["smp"], arc=data["arc"], pnt=data["pnt"], dsq=data["dsq"], flw=data["flw"], sgn=data["sgn"])
