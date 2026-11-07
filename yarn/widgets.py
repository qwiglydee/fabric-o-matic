from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from traitlets import Integer, Float, Unicode, Instance, Tuple, observe
from ipywidgets import widgets as wg
import plotly.graph_objects as go


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

        curve = self.plotting_curve(self.tspace_curve, self.params).T
        self.figure.update_traces(dict(x=curve[0], y=curve[1], z=curve[2], customdata=self.tspace_curve), selector)

    @observe("params", "tspace_flow")
    def render_flow(self, _):
        selector = {"name": "flow"}
        if self.params is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], u=[], v=[], w=[]), selector)
            return

        points = self.plotting_curve(self.tspace_flow, self.params).T
        flowdir = self.plotting_flow(self.tspace_flow, self.params).T
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

        curve = self.plotting_curve(self.tspace_curve, self.params).T
        self.figure.update_traces(dict(x=curve[0], y=curve[1], customdata=self.tspace_curve), selector)

    @observe("params", "tspace_flow")
    def render_flow(self, _):
        selector = {"name": "flow"}
        if self.params is None:
            self.figure.update_traces(dict(x=[], y=[], customdata=[], marker=None), selector)
            return

        points = self.plotting_curve(self.tspace_flow, self.params).T
        flowdir = self.plotting_flow(self.tspace_flow, self.params).T
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
