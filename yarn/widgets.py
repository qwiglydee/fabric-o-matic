import numpy as np
from ipywidgets import widgets as wg
from numpy.typing import NDArray
from plotly import colors
from plotly import graph_objects as go
from traitlets import Instance, List, Tuple, Unicode, observe


from field import Field


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


class Field2DView(wg.Box):
    tspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))
    gspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))

    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    axes = Tuple(List(Unicode()), Instance(np.ndarray), allow_none=True)
    curve = Instance[NDArray | None](np.ndarray, allow_none=True)
    field = Instance[Field | None](Field, allow_none=True)

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
                    line=dict(dash="dash", width=1, color="black"),
                    opacity=0.5,
                    visible="legendonly",
                ),
                go.Scatter(
                    name="axes",
                    mode="text+lines",
                    line=dict(dash="dot", width=2, color="black"),
                    opacity=0.5,
                    visible="legendonly",
                ),
                go.Scatter(
                    name="curve",
                    mode="lines",
                    hovertemplate="t: %{customdata:.03f}<br>xy: %{x:.03f} %{y:.03f}",
                    line=dict(color="black"),
                ),
                go.Heatmap(
                    name="sdf",
                    x=[],
                    y=[],
                    z=[],
                    colorscale=colors.diverging.RdBu_r,
                    zmin=-1.4142,
                    zmax=+1.4142,
                    showscale=False,
                    showlegend=True,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}<br>t: %{customdata[0]:.03f}<br>dist: %{customdata[1]:.03f}",
                ),
                go.Heatmap(
                    name="arc",
                    x=[],
                    y=[],
                    z=[],
                    colorscale=colors.cyclical.Edge,
                    zmin=-0.5,
                    zmax=+0.5,
                    showscale=False,
                    showlegend=True,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}<br>t: %{customdata:.03f}",
                    visible="legendonly",
                ),
                go.Scatter(
                    name="flw",
                    x=[],
                    y=[],
                    mode="markers",
                    marker=dict(
                        symbol="arrow",
                        colorscale=colors.sequential.Hot,
                        cmin=1.0,
                        cmax=2.0,
                        showscale=False,
                    ),
                    hovertemplate="xy: %{x:.03f} %{y:.03f}<br>dir: %{customdata[1]:.3f} %{customdata[2]:.3f} %{customdata[3]:.3f}<br>mag: %{customdata[0]:.3f}",
                    visible="legendonly",
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

    @observe("axes")
    def update_axes(self, _):
        selector = {"name": "axes"}
        if self.axes is None:
            self.figure.update_traces(dict(x=[], y=[], text=[]), selector)

        labels, points = self.axes
        self.figure.update_traces(
            dict(x=points[:, 0], y=points[:, 1], text=labels),
            selector,
        )

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

    @observe("field")
    def update_field(self, _):
        if self.field is None:
            return
        lattice = self.field.smp.reshape(-1, 2)  # (count×2)
        self.render_sdf(lattice)
        self.render_arc(lattice)
        self.render_flw(lattice)

    def render_sdf(self, lattice: NDArray):
        assert self.field is not None

        values = self.field.sdist.flatten()

        self.figure.update_traces(
            dict(
                x=lattice[:, 0],
                y=lattice[:, 1],
                z=values,
                customdata=np.array((self.field.arc.flatten(), values)).T,
            ),
            {"name": "sdf"},
        )

    def render_arc(self, lattice):
        assert self.field is not None

        values = self.field.arc.flatten()
        values = values - np.floor(values) - 0.5  # local t for segments

        self.figure.update_traces(
            dict(
                x=lattice[:, 0],
                y=lattice[:, 1],
                z=values,
                customdata=self.field.arc.flatten(),
            ),
            {"name": "arc"},
        )

    def render_flw(self, lattice):
        assert self.field is not None

        flw = self.field.flw.reshape(-1, 3)
        mag = np.sqrt((flw * flw).sum(-1))
        ang = 90 - np.atan2(flw[:, 1], flw[:, 0]) * 180 / np.pi

        self.figure.update_traces(
            dict(
                x=lattice[:, 0],
                y=lattice[:, 1],
                marker=dict(
                    color=mag,
                    angle=ang,
                ),
                customdata=np.array((mag, flw[:, 0], flw[:, 1], flw[:, 2])).T,
            ),
            {"name": "flw"},
        )


class Field3DView(wg.Box):
    tspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))
    gspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))

    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    axes = Tuple(List(Unicode()), Instance(np.ndarray), allow_none=True)
    curve = Instance[NDArray | None](np.ndarray, allow_none=True)
    field = Instance[Field | None](Field, allow_none=True)

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
                    line=dict(dash="dash", width=2, color="black"),
                    opacity=0.5,
                    visible="legendonly",
                ),
                go.Scatter3d(
                    name="axes",
                    mode="text+lines",
                    line=dict(dash="dot", width=2, color="black"),
                    opacity=0.5,
                    visible="legendonly",
                ),
                go.Scatter3d(
                    name="curve",
                    mode="lines",
                    hovertemplate="t: %{customdata:.03f}<br>xyz: %{x:.03f} %{y:.03f} %{z:.03f}",
                    line=dict(color="black"),
                    visible=True,
                ),
                go.Scatter3d(
                    name="curve2d",
                    mode="lines",
                    hoverinfo="skip",
                    line=dict(color="black", width=2, dash="dash"),
                    visible=True,
                ),
                go.Scatter3d(
                    name="sdf",
                    mode="markers",
                    marker=go.scatter3d.Marker(
                        symbol="circle",
                        size=8,
                        colorscale=colors.diverging.RdBu_r,
                        cmin=-1.4142,
                        cmax=+1.4142,
                        showscale=False,
                    ),
                    opacity=0.75,
                    showlegend=True,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}<br>t: %{customdata[0]:.03f}<br>dist: %{customdata[1]:.03f}",
                ),
                go.Scatter3d(
                    name="arc",
                    mode="markers",
                    marker=go.scatter3d.Marker(
                        symbol="circle",
                        size=8,
                        colorscale=colors.cyclical.Edge,
                        cmin=-0.5,
                        cmax=+0.5,
                        showscale=False,
                    ),
                    opacity=0.75,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}<br>t: %{customdata[0]:.03f}<br>dist: %{customdata[1]:.03f}",
                    visible="legendonly",
                    showlegend=True,
                ),
                go.Cone(
                    name="flw",
                    colorscale=colors.sequential.Hot,
                    cmin=1.0,
                    cmax=2.0,
                    sizemode="raw",
                    sizeref=0.025,
                    hovertemplate="xy: %{x:.03f} %{y:.03f}<br>dir: %{customdata[1]:.3f} %{customdata[2]:.3f} %{customdata[3]:.3f}<br>mag: %{customdata[0]:.3f}",
                    showscale=False,
                    showlegend=True,
                    visible="legendonly",
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

    @observe("axes")
    def update_axes(self, _):
        selector = {"name": "axes"}
        if self.axes is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], text=[]), selector)

        labels, points = self.axes
        self.figure.update_traces(
            dict(x=points[:, 0], y=points[:, 1], z=points[:, 2], text=labels),
            selector,
        )

    @observe("curve")
    def update_curve(self, _):
        if self.curve is None:
            self.figure.update_traces(dict(x=[], y=[], z=[], customdata=[]), {"name": "curve"})
            self.figure.update_traces(dict(x=[], y=[], z=[], customdata=[]), {"name": "curve2d"})
            return

        coords = self.curve.T
        self.figure.update_traces(
            dict(x=coords[0], y=coords[1], z=coords[2], customdata=self.tspace),
            {"name": "curve"},
        )
        self.figure.update_traces(
            dict(x=coords[0], y=coords[1], z=np.zeros(coords.shape[-1])),
            {"name": "curve2d"},
        )

    @observe("field")
    def update_field(self, _):
        if self.field is None:
            return
        lattice = self.field.smp.reshape(-1, 2)  # (count×2)
        self.render_sdf(lattice)
        self.render_arc(lattice)
        self.render_flw(lattice)

    def render_sdf(self, lattice):
        assert self.field is not None

        values = self.field.sdist.flatten()

        self.figure.update_traces(
            dict(
                x=lattice[:, 0],
                y=lattice[:, 1],
                z=np.zeros(lattice.shape[0]),
                marker=dict(color=values),
                customdata=np.array((self.field.arc.flatten(), values)).T,
            ),
            {"name": "sdf"},
        )

    def render_arc(self, lattice):
        assert self.field is not None

        values = self.field.arc.flatten()
        values = values - np.floor(values) - 0.5  # local t for segments

        self.figure.update_traces(
            dict(
                x=lattice[:, 0],
                y=lattice[:, 1],
                z=np.zeros(lattice.shape[0]),
                marker=dict(color=values),
                customdata=self.field.arc.flatten(),
            ),
            {"name": "arc"},
        )

    def render_flw(self, lattice):
        assert self.field is not None

        flw = self.field.flw.reshape(-1, 3)
        mag = np.sqrt((flw * flw).sum(-1))

        self.figure.update_traces(
            dict(
                x=lattice[:, 0],
                y=lattice[:, 1],
                z=np.zeros(lattice.shape[0]),
                u=flw[:, 0],
                v=flw[:, 1],
                w=flw[:, 2],
                customdata=np.array((mag, flw[:, 0], flw[:, 1], flw[:, 2])).T,
            ),
            {"name": "flw"},
        )


class FieldDualView(wg.Box):
    view2d: Field2DView
    view3d: Field3DView

    tspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))
    gspace = Instance[NDArray](np.ndarray, default=np.array((0.0, 0.5, 1.0)))

    controls = Instance[NDArray | None](np.ndarray, allow_none=True)
    axes = Tuple(List(Unicode()), Instance(np.ndarray), allow_none=True)
    curve = Instance[NDArray | None](np.ndarray, allow_none=True)
    field = Instance[Field | None](Field, allow_none=True)

    pick = Instance[NDArray | None](np.ndarray, allow_none=True)
    poke = Instance[Field | None](Field, allow_none=True)

    def __init__(self, **kwargs):
        self.view2d = Field2DView()
        self.view3d = Field3DView()

        self.view2d.figure.add_trace(
            go.Scatter(
                name="pick",
                mode="markers",
                marker=dict(symbol="square", color="purple"),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        self.view2d.figure.add_trace(
            go.Scatter(
                name="poke",
                mode="markers",
                marker=dict(symbol="circle", color="purple"),
                hovertemplate="t: %{customdata[0]:.03f}<br>dist: %{customdata[1]:.03f}",
                showlegend=False,
            )
        )
        self.view3d.figure.add_trace(
            go.Scatter3d(
                name="pick",
                mode="markers",
                marker=dict(symbol="square", color="purple", size=4),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        self.view3d.figure.add_trace(
            go.Scatter3d(
                name="poke",
                mode="markers",
                marker=dict(symbol="circle", color="purple", size=4),
                hovertemplate="t: %{customdata[0]:.03f}<br>dist: %{customdata[1]:.03f}",
                showlegend=False,
            )
        )

        super().__init__(children=[self.view2d, self.view3d])

        def on_click(trace, points, mouse):
            if len(points.xs) != 1 or len(points.ys) != 1:
                return
            self.pick = np.array((points.xs[0], points.ys[0]))

        for trace in self.view2d.figure.select_traces({"name": "sdf"}):
            trace.on_click(on_click)  # type: ignore
        for trace in self.view3d.figure.select_traces({"name": "sdf"}):
            trace.on_click(on_click)  # type: ignore

    @observe("tspace")
    def update_tspace(self, _):
        self.view2d.tspace = self.tspace
        self.view3d.tspace = self.tspace

    @observe("gspace")
    def update_gspace(self, _):
        self.view2d.gspace = self.gspace
        self.view3d.gspace = self.gspace

    @observe("controls")
    def update_controls(self, _):
        self.view2d.controls = self.controls
        self.view3d.controls = self.controls

    @observe("axes")
    def update_axes(self, _):
        self.view2d.axes = self.axes
        self.view3d.axes = self.axes

    @observe("curve")
    def update_curve(self, _):
        if self.curve is not None:
            assert self.tspace is not None
            assert self.curve.shape[0] == self.tspace.shape[0]
        self.view2d.curve = self.curve
        self.view3d.curve = self.curve

    @observe("field")
    def update_flow(self, _):
        self.pick = None
        self.poke = None

        if self.field is not None:
            assert self.gspace is not None

        self.view2d.field = self.field
        self.view3d.field = self.field

    @observe("pick")
    def update_pick(self, _):
        if self.pick is None:
            self.view2d.figure.update_traces(dict(x=[], y=[]), {"name": "pick"})
            self.view3d.figure.update_traces(dict(x=[], y=[], z=[]), {"name": "pick"})
            return

        x, y = self.pick

        self.view2d.figure.update_traces(dict(x=[x], y=[y]), {"name": "pick"})
        self.view3d.figure.update_traces(dict(x=[x], y=[y], z=[0]), {"name": "pick"})

    @observe("poke")
    def update_poke(self, _):
        if self.poke is None:
            self.view2d.figure.update_traces(dict(x=[], y=[], customdata=[]), {"name": "poke"})
            self.view3d.figure.update_traces(dict(x=[], y=[], z=[], customdata=[]), {"name": "poke"})
            return

        fld = self.poke
        coords = fld.pnt.T
        data = np.array((fld.arc, fld.sdist)).T

        self.view2d.figure.update_traces(dict(x=coords[0], y=coords[1], customdata=data), {"name": "poke"})
        self.view3d.figure.update_traces(dict(x=coords[0], y=coords[1], z=np.zeros(coords.shape[1]), customdata=data), {"name": "poke"})
