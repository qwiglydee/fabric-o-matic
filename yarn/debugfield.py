import numpy as np
from numpy.typing import NDArray
from traitlets import Float, Instance, Tuple, observe
from ipywidgets import widgets as wg
import plotly.graph_objects as go

from field import Field


def debug_field(lattice: NDArray, data: NDArray):
    dim = data.shape
    if len(dim) == 2:
        return go.Figure(
            go.Surface(
                x=lattice[:, :, 0],
                y=lattice[:, :, 1],
                z=np.zeros(lattice.shape[:-1]),
                surfacecolor=data,
                customdata=data,
                hovertemplate="xy: %{x:.03f} %{y:.03f}<br>val: %{customdata:.03f}",
            ),
            layout=dict(scene_aspectmode="data", scene_zaxis_range=(-0.5, 0.5)),
        )
    elif dim[-1] == 2:
        coords = lattice.reshape(-1, 2)
        values = data.reshape(-1, 2)
        return go.Figure(
            go.Cone(
                x=coords[:, 0].ravel(),
                y=coords[:, 1].ravel(),
                z=np.zeros(coords.shape[0]),
                u=values[:, 0].ravel(),
                v=values[:, 1].ravel(),
                w=np.zeros(values.shape[0]),
            ),
            layout=dict(scene_aspectmode="data", scene_zaxis_range=(-0.5, 0.5)),
        )
    elif dim[-1] == 3:
        coords = lattice.reshape(-1, 2)
        values = data.reshape(-1, 3)
        return go.Figure(
            go.Cone(
                x=coords[:, 0].ravel(),
                y=coords[:, 1].ravel(),
                z=np.zeros(coords.shape[0]),
                u=values[:, 0].ravel(),
                v=values[:, 1].ravel(),
                w=values[:, 2].ravel(),
            ),
            layout=dict(scene_aspectmode="data", scene_zaxis_range=(-0.5, 0.5)),
        )
    else:
        raise NotImplementedError()


def debug_unmask(field: Field, mask: NDArray, masked: NDArray):
    dim = masked.shape
    if len(dim) == 1:
        data = np.zeros(field.shape)
    else:
        data = np.zeros((*field.shape, dim[-1]))
    data[mask] = masked
    return data
