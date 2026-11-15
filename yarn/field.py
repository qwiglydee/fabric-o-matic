from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray


class Field(NamedTuple):
    """Struct to hold all the field data
    Dimensions are (X×Y×) preserving structure of sampling lattice
    """

    smp: NDArray  # (2d) sample points in UV
    arc: NDArray  # (float) path along curve, =t (num×1), ~= arc length distorted
    pnt: NDArray  # (2d or 3d) projection closest point
    dsq: NDArray  # (float) disquance
    flw: NDArray  # (2d or 3d) tangential flow ~ tangent
    sgn: NDArray  # (±1) orientation (sign of the distance)

    @property
    def sdist(self) -> NDArray:
        return self.sgn * np.sqrt(self.dsq)

    @property
    def shape(self):
        return self.arc.shape

    def __getitem___(self, slice):
        return Field(self.smp[slice], self.arc[slice], self.pnt[slice], self.dsq[slice], self.flw[slice], self.sgn[slice])


def save_field(fld: Field, filename: str):
    np.savez(filename, smp=fld.smp, arc=fld.arc, pnt=fld.pnt, dsq=fld.dsq, flw=fld.flw, sgn=fld.sgn)


def load_field(filename: str):
    data = np.load(filename)
    return Field(smp=data["smp"], arc=data["arc"], pnt=data["pnt"], dsq=data["dsq"], flw=data["flw"], sgn=data["sgn"])
