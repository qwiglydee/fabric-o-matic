from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from traitlets import Float, Instance, Tuple, observe
from ipywidgets import widgets as wg
import plotly.graph_objects as go
from plotly import colors

from field import Field


class Curve3DView(wg.Box):
    """Figure widget wrapper to plot 3D curves with control points and tangent flow
    Provided curve_fn and flow_fn should take tspace (array Nx1) and return vectors (array Nx3)
    """

    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    "controls a plotted as polygon"

    params = Tuple(allow_none=True)
    "params are passed to plotting functions directly"

    plotting_curve: Callable
    plotting_flow: Callable

    tspace_curve = Instance[NDArray](np.ndarray, default_value=np.linspace(0.0, 1.0, 16))
    tspace_flow = Instance[NDArray](np.ndarray, default_value=np.linspace(0.0, 1.0, 5))

    figure: go.FigureWidget
    out: wg.Output

    def __init__(self, plotting_curve: Callable, plotting_flow: Callable, **kwargs):
        self.plotting_curve = plotting_curve
        self.plotting_flow = plotting_flow

        self.figure = go.FigureWidget(
            layout=go.Layout(
                autosize=False,
                height=720,
                margin=dict(t=64, b=16, l=16, r=16),
                scene_aspectmode="data",
            )
        )
        self.figure.add_trace(
            go.Scatter3d(
                name="controls",
                mode="markers+lines",
                marker=dict(symbol="circle-open"),
                opacity=0.5,
                hovertemplate="xyz: %{x:.03f} %{y:.03f} %{z:.03f}",
            )
        )
        self.figure.add_trace(
            go.Scatter3d(
                name="curve",
                mode="lines",
                hovertemplate="t: %{customdata:.03f}<br>xyz: %{x:.03f} %{y:.03f} %{z:.03f}",
                line=dict(width=6),
            )
        )
        self.figure.add_trace(
            go.Cone(
                name="flow",
                hovertemplate="t: %{customdata[0]:.03f}<br>mag: %{customdata[1]:.03f}",
                sizemode="absolute",
                sizeref=0.25,
                colorscale=[(0.0, "gray"), (1.0, "gray")],
                showscale=False,
                showlegend=True,
            )
        )

        self.out = wg.Output()

        super().__init__([wg.VBox([self.figure, self.out])], **kwargs)

    @observe("controls")
    def render_controls(self, _):
        selector = {"name": "controls"}
        if self.controls is None:
            self.figure.update_traces(dict(x=[], y=[], z=[]), selector)
            return
        assert self.controls.shape[1] == 3, "expecting 3D points"
        points = self.controls.T
        self.figure.update_traces(dict(x=points[0], y=points[1], z=points[2]), selector)

    @observe("params", "tspace_curve")
    def render_curve(self, _):
        selector = {"name": "curve"}
        if self.params is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            return

        curve = self.plotting_curve(self.params, self.tspace_curve).T
        self.figure.update_traces(dict(x=curve[0], y=curve[1], z=curve[2], customdata=self.tspace_curve), selector)

    @observe("params", "tspace_flow")
    def render_flow(self, _):
        selector = {"name": "flow"}
        if self.params is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], u=[], v=[], w=[]), selector)
            return

        points = self.plotting_curve(self.params, self.tspace_flow).T
        flowdir = self.plotting_flow(self.params, self.tspace_flow).T
        flowmag = np.sqrt((flowdir * flowdir).sum(axis=0))

        self.figure.update_traces(
            dict(
                x=points[0],
                y=points[1],
                z=points[2],
                u=flowdir[0],
                v=flowdir[1],
                w=flowdir[2],
                customdata=np.stack((self.tspace_flow, flowmag)).T,
            ),
            {"name": "flow"},
        )


class Curve2DView(wg.Box):
    """Figure widget wrapper to plot 2D curves with control points and tangent flow
    Provided curve_fn and flow_fn should take tspace (array Nx1) and return vectors (array Nx3)
    """

    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    "controls a plotted as polygon"

    params = Tuple(allow_none=True)
    "params are passed to plotting functions directly"

    plotting_curve: Callable
    plotting_flow: Callable

    tspace_curve = Instance[NDArray](np.ndarray, default_value=np.linspace(0.0, 1.0, 16))
    tspace_flow = Instance[NDArray](np.ndarray, default_value=np.linspace(0.0, 1.0, 5))

    figure: go.FigureWidget
    out: wg.Output

    def __init__(self, plotting_curve: Callable, plotting_flow: Callable, **kwargs):
        self.plotting_curve = plotting_curve
        self.plotting_flow = plotting_flow

        self.figure = go.FigureWidget(
            layout=go.Layout(
                autosize=False,
                height=720,
                margin=dict(t=64, b=16, l=16, r=16),
                scene_aspectmode="data",
            )
        )
        self.figure.add_trace(
            go.Scatter(
                name="controls",
                mode="markers+lines",
                marker=dict(symbol="circle-open"),
                opacity=0.5,
                hovertemplate="xyz: %{x:.03f} %{y:.03f}",
            )
        )
        self.figure.add_trace(
            go.Scatter(
                name="curve",
                mode="lines",
                hovertemplate="t: %{customdata:.03f}<br>xyz: %{x:.03f} %{y:.03f}",
                line=dict(width=6),
            )
        )
        self.figure.add_trace(
            go.Scatter(
                name="flow",
                mode="markers",
                marker=dict(symbol="arrow-wide", color="gray", opacity=1.0),
                hovertemplate="t: %{customdata[0]:.03f}<br>mag: %{customdata[1]:.03f}",
                showlegend=True,
            )
        )

        self.out = wg.Output()

        super().__init__([wg.VBox([self.figure, self.out])], **kwargs)

    @observe("controls")
    def render_controls(self, _):
        selector = {"name": "controls"}
        if self.controls is None:
            self.figure.update_traces(dict(x=[], y=[]), selector)
            return
        assert self.controls.shape[1] == 2, "expecting 2D points"
        points = self.controls.T
        self.figure.update_traces(dict(x=points[0], y=points[1]), selector)

    @observe("params", "tspace_curve")
    def render_curve(self, _):
        selector = {"name": "curve"}
        if self.params is None:
            self.figure.update_traces(dict(x=[], y=[], customdata=[]), selector)
            return

        curve = self.plotting_curve(self.params, self.tspace_curve).T
        self.figure.update_traces(dict(x=curve[0], y=curve[1], customdata=self.tspace_curve), selector)

    @observe("params", "tspace_flow")
    def render_flow(self, _):
        selector = {"name": "flow"}
        if self.params is None:
            self.figure.update_traces(dict(x=[], y=[], customdata=[], marker=None), selector)
            return

        points = self.plotting_curve(self.params, self.tspace_flow).T
        flowdir = self.plotting_flow(self.params, self.tspace_flow).T
        flowmag = np.sqrt((flowdir * flowdir).sum(axis=0))
        flowang = np.arctan2(flowdir[1], flowdir[0])

        self.figure.update_traces(
            dict(
                x=points[0],
                y=points[1],
                marker=dict(angle=90 - flowang * 180 / np.pi, size=24.0 * flowmag),
                customdata=np.stack((self.tspace_flow, flowmag)).T,
            ),
            selector,
        )


from collections.abc import Callable
from traitlets import Instance, Tuple, observe
from ipywidgets import widgets as wg
import plotly.graph_objects as go
from plotly import colors


class FieldView(wg.Box):
    """View 3d and 2d curve and projection fields"""

    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    curve = Instance[NDArray | None](np.ndarray, allow_none=True)
    field = Instance[Field | None](Field, allow_none=True)

    poke = Instance[NDArray | None](np.ndarray, allow_none=True)
    picking: Callable | None = None
    picked = Instance[Field | None](Field, allow_none=True)

    figure3d: go.FigureWidget
    figure2d: go.FigureWidget

    def __init__(self, **kwargs):
        self.figure3d = go.FigureWidget(
            layout=go.Layout(
                autosize=False,
                height=720,
                margin=dict(t=16, b=16, l=16, r=16),
                scene=dict(
                    aspectmode="data",
                    camera=dict(eye=dict(x=0, y=0, z=2), up=dict(x=0, y=1, z=0), center=dict(x=0, y=0, z=0)),
                ),
            ),
            data=[
                go.Scatter3d(
                    name="controls",
                    mode="markers+lines",
                    marker=dict(symbol="circle-open", color="black"),
                    opacity=0.25,
                    hoverinfo="skip",
                ),
                go.Scatter3d(
                    name="curve",
                    mode="lines",
                    hovertemplate="xyz: %{x:.03f} %{y:.03f} %{z:.03f}",
                    line=dict(width=4, color="black"),
                    showlegend=True,
                ),
                go.Scatter3d(
                    name="curve2d",
                    mode="lines",
                    hovertemplate="xy: %{x:.03f} %{y:.03f}",
                    line=dict(width=4, color="black", dash="dash"),
                    showlegend=True,
                ),
                go.Surface(
                    name="sdist",
                    x=[],
                    y=[],
                    z=[],
                    colorscale=colors.diverging.RdBu_r,
                    cmin=-1.0,
                    cmax=+1.0,
                    showscale=False,
                    opacity=0.75,
                    showlegend=True,
                    hovertemplate="t: %{customdata[0]:.03f}<br>xy: %{x:.03f} %{y:.03f}<br>dist: %{z:.03f}",
                ),
                go.Scatter3d(
                    name="poke",
                    mode="markers",
                    marker=dict(symbol="square", color="magenta"),
                    showlegend=False,
                ),
                go.Scatter3d(
                    name="pick",
                    mode="markers+text",
                    marker=dict(symbol="circle", color="magenta"),
                    showlegend=False,
                    hovertemplate="t: %{customdata[0]:.03f}<br>dst: %{customdata[1]:.03f}",
                ),
                go.Cone(
                    name="flow",
                    sizemode="raw",
                    sizeref=0.025,
                    showscale=False,
                    showlegend=True,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}<br>dir: %{u:.03f} %{v:.03f} %{w:.03f}<br>mag: %{customdata:.03f}",
                ),
            ],
        )
        self.figure2d = go.FigureWidget(
            layout=go.Layout(
                autosize=False,
                height=720,
                margin=dict(t=16, b=16, l=16, r=16),
                scene_aspectmode="data",
            ),
            data=[
                go.Scatter(
                    name="controls",
                    mode="markers+lines",
                    marker=dict(symbol="circle-open", color="black"),
                    opacity=0.25,
                    hoverinfo="skip",
                ),
                go.Scatter(
                    name="curve",
                    mode="lines",
                    hovertemplate="xy: %{x:.03f} %{y:.03f}",
                    line=dict(width=4, color="black"),
                    showlegend=True,
                ),
                go.Heatmap(
                    name="sdist",
                    zmid=0.0,
                    colorscale=colors.diverging.RdBu_r,
                    showscale=False,
                    showlegend=True,
                    hovertemplate="t: %{customdata[0]:.03f}<br>xy: %{x:.03f} %{y:.03f}<br>dist: %{z:.03f}",
                ),
                go.Scatter(
                    name="poke",
                    mode="markers",
                    marker=dict(symbol="square", color="magenta"),
                    showlegend=False,
                ),
                go.Scatter(
                    name="pick",
                    mode="markers+text",
                    marker=dict(symbol="circle", color="magenta", size=8),
                    showlegend=False,
                    hovertemplate="t: %{customdata[0]:.03f}<br>dst: %{customdata[1]:.03f}",
                ),
            ],
        )

        super().__init__(children=[self.figure3d, self.figure2d], **kwargs)

        self.figure2d.data[2].on_click(self.on_click)  # type: ignore
        self.figure3d.data[3].on_click(self.on_click)  # type: ignore

    @observe("controls")
    def update_controls(self, _):
        selector = {"name": "controls"}

        if self.controls is None:
            self.figure3d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            self.figure2d.update_traces(dict(x=[], y=[], customdata=[]), selector)
            return

        assert self.controls.shape[1] == 3, "expecting 3D points"

        coords = self.controls.T
        self.figure3d.update_traces(dict(x=coords[0], y=coords[1], z=coords[2]), selector)
        self.figure2d.update_traces(dict(x=coords[0], y=coords[1]), selector)

        self.figure3d.update_layout(scene_camera_eye_z=4)

    @observe("curve")
    def update_curve(self, _):
        selector = {"name": "curve"}
        selector2 = {"name": "curve2d"}

        if self.curve is None:
            self.figure3d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            self.figure2d.update_traces(dict(x=[], y=[], customdata=[]), selector)
            return

        coords = self.curve.T
        self.figure3d.update_traces(dict(x=coords[0], y=coords[1], z=coords[2]), selector)
        self.figure3d.update_traces(dict(x=coords[0], y=coords[1], z=np.zeros(coords.shape[1])), selector2)
        self.figure2d.update_traces(dict(x=coords[0], y=coords[1]), selector)

        self.figure3d.update_layout(scene_camera_eye_z=4)

    @observe("field")
    def update_field(self, _):
        self.update_sdist()
        self.update_flow()
        self.poke = None
        self.picked = None

    def update_sdist(self):
        selector = {"name": "sdist"}
        if self.field is None:
            self.figure3d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            self.figure2d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            return

        lattice = self.field.smp
        values = self.field.sdist

        self.figure3d.update_traces(
            dict(
                x=lattice[:, :, 0],
                y=lattice[:, :, 1],
                z=np.zeros(self.field.shape),
                surfacecolor=values,
                # customdata=np.stack((self.field.arc.flatten(), values.flatten())).T,
            ),
            selector,
        )

        lattice = lattice.reshape(-1, 2)
        values = values.flatten()

        self.figure2d.update_traces(
            dict(
                x=lattice[:, 0],
                y=lattice[:, 1],
                z=values,
                customdata=np.stack((self.field.arc.flatten(), values)).T,
            ),
            selector,
        )

    def update_flow(self):
        selector = {"name": "flow"}
        if self.field is None:
            self.figure3d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            # self.figure2d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            return

        interl = 2

        coords = self.field.smp[::interl, ::interl, :].reshape(-1, 2)

        dim = self.field.flw.shape[-1]
        flows = self.field.flw[::interl, ::interl, :].reshape(-1, dim)
        magn = np.sqrt((flows * flows).sum(axis=-1))

        self.figure3d.update_traces(
            dict(
                x=coords[:, 0],
                y=coords[:, 1],
                z=np.zeros(coords.shape[0]),
                u=flows[:, 0],
                v=flows[:, 1],
                w=flows[:, 2] if dim == 3 else np.zeros(flows.shape[0]),
                customdata=magn,
            ),
            selector,
        )

    def on_click(self, trace, points, mouse):
        if self.controls is None or len(points.point_inds) == 0:
            self.poke = None
            return
        self.poke = np.array([points.xs[0], points.ys[0]])

        if self.picking is not None:
            self.picked = self.picking(self.poke)

    @observe("poke")
    def update_poke(self, _):
        selector = {"name": "poke"}
        if self.poke is None:
            self.figure3d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            self.figure2d.update_traces(dict(x=[], y=[], customdata=[]), selector)
            return

        coords = self.poke[:, None]

        self.figure3d.update_traces(dict(x=coords[0], y=coords[1], z=[0], customdata=[]), selector)
        self.figure2d.update_traces(dict(x=coords[0], y=coords[1], customdata=[]), selector)

    @observe("picked")
    def update_picked(self, _):
        selector = {"name": "pick"}
        if self.picked is None:
            self.figure3d.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            self.figure2d.update_traces(dict(x=[], y=[], customdata=[]), selector)
            return

        markers = self.picked.pnt
        info = np.stack((self.picked.arc, self.picked.sdist)).T
        labels = [f"t: {t - 0.5:.03f}" for t in self.picked.arc]

        self.figure3d.update_traces(
            dict(
                x=markers[:, 0],
                y=markers[:, 1],
                z=np.zeros(self.picked.shape),
                customdata=info,
                text=labels,
            ),
            selector,
        )
        self.figure2d.update_traces(
            dict(
                x=markers[:, 0],
                y=markers[:, 1],
                customdata=info,
                text=labels,
            ),
            selector,
        )
