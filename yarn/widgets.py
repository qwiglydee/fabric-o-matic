import numpy as np
from numpy.typing import NDArray
from traitlets import Integer, Unicode, Instance, Callable, observe
from ipywidgets import widgets as wg
import plotly.graph_objects as go


class Curve3DView(wg.Box):
    """Figure widget wrapper to plot 3D curves with control points and tangent flow
    Provided curve_fn and flow_fn should take tspace (array Nx1) and return vectors (array Nx3)
    """

    title = Unicode()
    points = Instance[NDArray | None](np.ndarray, allow_none=True)

    curve_fn = Callable(allow_none=True)
    discr_curve = Integer(default_value=100)

    flow_fn = Callable(allow_none=True)
    discr_flow = Integer(default_value=5)

    figure: go.FigureWidget
    out: wg.Output

    def __init__(self, title: str, **kwargs):
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
        self.title = title

    @observe("title")
    def upd_title(self, change):
        self.figure.update_layout(title=self.title)

    @observe("points")
    def render_points(self, _):
        selector = {"name": "controls"}
        if self.points is None:
            self.figure.update_traces(dict(x=[], y=[], z=[]), selector)
            return

        controls = self.points.T
        self.figure.update_traces(dict(x=controls[0], y=controls[1], z=controls[2]), selector)

    @observe("curve_fn", "discr_curve")
    def render_curve(self, _):
        selector = {"name": "curve"}
        if self.curve_fn is None:
            self.figure.update_traces(dict(x=[], y=[], z=[]), selector)
            return

        tspace = np.linspace(0.0, 1.0, self.discr_curve)
        points = self.curve_fn(tspace).T
        self.figure.update_traces(dict(x=points[0], y=points[1], z=points[2], customdata=tspace), selector)

    @observe("flow_fn", "discr_flow")
    def render_flow(self, _):
        selector = {"name": "flow"}
        if self.flow_fn is None or self.curve_fn is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], u=[], v=[], w=[]), selector)
            return

        tsample = np.linspace(0.0, 1.0, self.discr_flow)

        points = self.curve_fn(tsample).T
        flowdir = self.flow_fn(tsample).T
        flowmag = np.sqrt((flowdir * flowdir).sum(axis=0))

        self.figure.update_traces(
            dict(
                x=points[0],
                y=points[1],
                z=points[2],
                u=flowdir[0],
                v=flowdir[1],
                w=flowdir[2],
                customdata=np.stack((tsample, flowmag)).T,
            ),
            {"name": "flow"},
        )


class Curve2DView(wg.Box):
    """Figure widget wrapper to plot 2D curves with control points and tangent flow
    Provided curve_fn and flow_fn should take tspace (array Nx1) and return vectors (array Nx3)
    """

    title = Unicode()
    points = Instance[NDArray | None](np.ndarray, allow_none=True)

    curve_fn = Callable(allow_none=True)
    discr_curve = Integer(default_value=100)

    flow_fn = Callable(allow_none=True)
    discr_flow = Integer(default_value=5)

    figure: go.FigureWidget
    out: wg.Output

    def __init__(self, title: str, **kwargs):
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
        self.title = title

    @observe("title")
    def upd_title(self, change):
        self.figure.update_layout(title=self.title)

    @observe("points")
    def render_points(self, _):
        selector = {"name": "controls"}
        if self.points is None:
            self.figure.update_traces(dict(x=[], y=[]), selector)
            return

        controls = self.points.T
        self.figure.update_traces(dict(x=controls[0], y=controls[1]), selector)

    @observe("curve_fn", "discr_curve")
    def render_curve(self, _):
        selector = {"name": "curve"}
        if self.curve_fn is None:
            self.figure.update_traces(dict(x=[], y=[]), selector)
            return

        tspace = np.linspace(0.0, 1.0, self.discr_curve)
        points = self.curve_fn(tspace).T
        self.figure.update_traces(dict(x=points[0], y=points[1], customdata=tspace), selector)

    @observe("flow_fn", "discr_flow")
    def render_flow(self, _):
        selector = {"name": "flow"}
        if self.flow_fn is None or self.curve_fn is None:
            self.figure.update_traces(dict(x=[], y=[], customdata=[], marker=None), selector)
            return

        tsample = np.linspace(0.0, 1.0, self.discr_flow)

        points = self.curve_fn(tsample).T
        flowdir = self.flow_fn(tsample).T
        flowmag = np.sqrt((flowdir * flowdir).sum(axis=0))
        flowang = np.arctan2(flowdir[1], flowdir[0])

        self.figure.update_traces(
            dict(
                x=points[0],
                y=points[1],
                marker=dict(angle=90 - flowang * 180 / np.pi, size=24.0 * flowmag),
                customdata=np.stack((tsample, flowmag)).T,
            ),
            selector,
        )
