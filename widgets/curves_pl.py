import numpy as np
from ipywidgets import widgets as wg
from numpy.typing import NDArray
from plotly import colors
from plotly import graph_objects as go
from traitlets import Instance, List, Tuple, Unicode, observe


class Curve2DView(wg.Box):
    tspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))

    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    curve = Instance[NDArray | None](np.ndarray, allow_none=True)
    flow = Instance[NDArray | None](np.ndarray, allow_none=True)

    figure: go.FigureWidget

    def __init__(self, **kwargs):
        self.figure = go.FigureWidget(
            layout=go.Layout(
                autosize=False,
                height=720,
                margin=dict(t=64, b=16, l=16, r=16),
                scene_aspectmode="data",
                yaxis_scaleanchor="x",
            ),
            data=[
                go.Scatter(
                    name="controls",
                    mode="markers+lines",
                    marker=dict(symbol="circle-open", color="black"),
                    line=dict(dash="dash", width=1),
                    opacity=0.5,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}",
                ),
                go.Scatter(
                    name="curve",
                    mode="lines",
                    hovertemplate="t: %{customdata:.03f}<br>xy: %{x:.03f} %{y:.03f}",
                    line=dict(color="black"),
                ),
                go.Scatter(
                    name="flow",
                    mode="markers",
                    marker=dict(symbol="circle", colorscale=colors.sequential.Hot, cmin=0, cmax=2, color="gray"),
                    hovertemplate="t: %{customdata[0]:.03f}<br>|F|: %{customdata[1]:.03f}",
                    showlegend=True,
                ),
            ],
        )

        super().__init__([self.figure], **kwargs)

    @observe("controls")
    def render_controls(self, _):
        selector = {"name": "controls"}
        if self.controls is None:
            self.figure.update_traces(dict(x=[], y=[]), selector)
            return

        coords = self.controls.T
        self.figure.update_traces(dict(x=coords[0], y=coords[1]), selector)

    @observe("curve")
    def update_curve(self, _):
        selector = {"name": "curve"}
        if self.curve is None:
            self.figure.update_traces(dict(x=[], y=[], customdata=[]), selector)
            return

        coords = self.curve.T
        self.figure.update_traces(
            dict(x=coords[0], y=coords[1], customdata=self.tspace),
            selector,
        )

    @observe("flow")
    def update_flow(self, _):
        selector = {"name": "flow"}
        if self.curve is None or self.flow is None:
            self.figure.update_traces(dict(x=[], y=[], customdata=[]), selector)
            return

        coords = self.curve.T
        flowdir = self.flow.T
        flowmag = np.sqrt((flowdir * flowdir).sum(axis=0))

        self.figure.update_traces(
            dict(
                x=coords[0],
                y=coords[1],
                customdata=np.array([self.tspace, flowmag]).T,
                marker=dict(color=flowmag),
            ),
            selector,
        )


class Curve3DView(wg.Box):
    tspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))
    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    curve = Instance[NDArray | None](np.ndarray, allow_none=True)
    flow = Instance[NDArray | None](np.ndarray, allow_none=True)

    figure: go.FigureWidget

    def __init__(self, **kwargs):
        self.figure = go.FigureWidget(
            layout=go.Layout(
                autosize=False,
                height=720,
                margin=dict(t=64, b=16, l=16, r=16),
                scene=dict(
                    aspectmode="data",
                    camera=dict(eye=dict(x=0, y=0, z=3), up=dict(x=0, y=1, z=0), center=dict(x=0, y=0, z=0)),
                ),
            ),
            data=[
                go.Scatter3d(
                    name="controls",
                    mode="markers+lines",
                    marker=dict(symbol="circle-open", color="black"),
                    line=dict(dash="dash", width=1),
                    opacity=0.5,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}",
                ),
                go.Scatter3d(
                    name="curve",
                    mode="lines",
                    hovertemplate="t: %{customdata:.03f}<br>xy: %{x:.03f} %{y:.03f}",
                    line=dict(color="black"),
                ),
                go.Scatter3d(
                    name="flow",
                    mode="markers",
                    marker=dict(symbol="circle", colorscale=colors.sequential.Hot, cmin=0, cmax=2, size=4),
                    hovertemplate="t: %{customdata[0]:.03f}<br>|F|: %{customdata[1]:.03f}",
                    showlegend=True,
                ),
            ],
        )

        super().__init__([self.figure], **kwargs)

    @observe("controls")
    def render_controls(self, _):
        selector = {"name": "controls"}
        if self.controls is None:
            self.figure.update_traces(dict(x=[], y=[], z=[]), selector)
            return

        coords = self.controls.T
        self.figure.update_traces(dict(x=coords[0], y=coords[1], z=coords[2]), selector)

    @observe("curve")
    def update_curve(self, _):
        selector = {"name": "curve"}
        if self.curve is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            return

        coords = self.curve.T
        self.figure.update_traces(
            dict(x=coords[0], y=coords[1], z=coords[2], customdata=self.tspace),
            selector,
        )

    @observe("flow")
    def update_flow(self, _):
        selector = {"name": "flow"}
        if self.curve is None or self.flow is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], customdata=[]), selector)
            return

        coords = self.curve.T
        flowdir = self.flow.T
        flowmag = np.sqrt((flowdir * flowdir).sum(axis=0))

        self.figure.update_traces(
            dict(
                x=coords[0],
                y=coords[1],
                z=coords[2],
                customdata=np.array([self.tspace, flowmag]).T,
                marker=dict(color=flowmag),
            ),
            selector,
        )


class CurveDualView(wg.Box):
    view2d: Curve2DView
    view3d: Curve3DView

    tspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 1.0)))
    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    curve = Instance[NDArray | None](np.ndarray, allow_none=True)
    flow = Instance[NDArray | None](np.ndarray, allow_none=True)

    def __init__(self, **kwargs):
        self.view2d = Curve2DView()
        self.view3d = Curve3DView()

        super().__init__(children=[self.view2d, self.view3d])

    @observe("tspace")
    def update_tspace(self, _):
        self.view2d.tspace = self.tspace
        self.view3d.tspace = self.tspace

    @observe("controls")
    def update_controls(self, _):
        self.view2d.controls = self.controls
        self.view3d.controls = self.controls

    @observe("curve")
    def update_curve(self, _):
        if self.curve is not None:
            assert self.tspace is not None
            assert self.curve.shape[0] == self.tspace.shape[0]
        self.view2d.curve = self.curve
        self.view3d.curve = self.curve

    @observe("flow")
    def update_flow(self, _):
        if self.flow is not None:
            assert self.tspace is not None
            assert self.flow.shape[0] == self.tspace.shape[0]
        self.view2d.flow = self.flow
        self.view3d.flow = self.flow
