from typing import Any

import numpy as np
from numpy.typing import NDArray

import k3d
from ipywidgets import widgets as wg

from lab.gridspace import space_coords, space_spacing, space_sample


def pprintnp(value: float | NDArray):
    if isinstance(value, float):
        return f"{value:.03f}"
    elif isinstance(value, np.ndarray):
        return "[" + (" ".join(f"{v:.03f}" for v in value)) + "]"
    else:
        return repr(value)


class K3DView(wg.VBox):
    """Wrapper for k3d plot for UV-map-oriented stuff"""

    gspace: NDArray
    gspdim: tuple
    bounds: tuple
    vbounds: tuple

    plot: k3d.Plot
    layers: wg.SelectMultiple
    statusbar: wg.Label
    debug: wg.Output

    fields: dict[str, NDArray]

    def __init__(self, xspace: NDArray, yspace: NDArray, k3plot: dict | None = None, **kwargs):
        self.gspace = space_coords(xspace, yspace)
        self.gspdim = self.gspace.shape[:-1]
        xmin, xmax, xspc = space_spacing(xspace)
        ymin, ymax, yspc = space_spacing(yspace)
        xmid, ymid = (xmin + xmax) / 2, (ymin + ymax) / 2
        xmrg, ymrg = 0.5 * xspc, 0.5 * yspc
        vxmin, vxmax, vymin, vymax = xmin - xmrg, xmax + xmrg, ymin - ymrg, ymax + ymrg
        self.bounds = xmin, xmax, ymin, ymax
        self.vbounds = vxmin, vxmax, vymin, vymax

        self.statusbar = wg.Label()
        self.layers = wg.SelectMultiple(options={}, rows=10)
        self.debug = wg.Output()

        k3kwargs: dict[str, Any] = dict(
            grid=(vxmin, vymin, -0.5, vxmax, vymax, +0.5),
            mode="callback",
            menu_visibility=False,
            camera_auto_fit=False,
            camera=(xmid, ymid, 2, xmid, ymid, 0, 0, 1, 0),
        )
        if k3plot:
            k3kwargs.update(k3plot)

        self.plot = k3d.Plot(**k3kwargs)
        self.fields = {}
        self.init_aims()
        super().__init__([wg.HBox([self.plot, self.layers]), self.statusbar], **kwargs)

        self.layers.observe(self.onselect, "value")

    def add(self, drawable: k3d.objects.Drawable):
        assert drawable.name
        obj = self.get(drawable.name)
        if obj:
            self.rem(obj)
        self.plot.object_ids = self.plot.object_ids + [drawable.id]
        self.layers.options = dict(tuple(self.layers.options.items()) + ((drawable.name, drawable),))
        self.layers.value = (drawable,)

    def get(self, name: str) -> k3d.objects.Drawable | None:
        return self.layers.options.get(name)

    def rem(self, drawable: k3d.objects.Drawable):
        self.plot.object_ids = [id_ for id_ in self.plot.object_ids if id_ != drawable.id]
        self.layers.options = dict(item for item in self.layers.options.items() if item[1] != drawable)

    def texture(self, name, **kwargs):
        self.add(k3d.texture(name=name, bounds=self.vbounds, click_callback=self.onclick, **kwargs))

    def surface(self, name, **kwargs):
        self.add(k3d.surface(name=name, bounds=self.vbounds, click_callback=self.onclick, **kwargs))

    def points(self, name, **kwargs):
        self.add(k3d.points(name=name, **kwargs))

    def vectors(self, name, **kwargs):
        self.add(k3d.vectors(name=name, **kwargs))

    def mesh(self, name, **kwargs):
        self.add(k3d.mesh(name=name, click_callback=self.onclick, **kwargs))

    def onselect(self, data):
        selected = self.layers.value
        for o in self.layers.options.values():
            o.visible = o in selected

    xaim: k3d.objects.Line
    yaim: k3d.objects.Line
    zaim: k3d.objects.Line
    pick: k3d.objects.Points

    def init_aims(self):
        xmin, xmax, ymin, ymax = self.vbounds
        self.yaim = k3d.line(((xmin, 0, 0), (xmax, 0, 0)), width=0.005, color=0x808080, opacity=0.75, visible=False)
        self.xaim = k3d.line(((0, ymin, 0), (0, ymax, 0)), width=0.005, color=0x808080, opacity=0.75, visible=False)
        self.zaim = k3d.line(((0, 0, 0), (0, 0, 0)), width=0.005, color=0x808080, opacity=0.75, visible=False)
        self.pick = k3d.points([], point_size=0.02, color=0x808080, opacity=0.75, visible=False)
        self.plot.objects = [self.xaim, self.yaim, self.zaim, self.pick]
        self.plot.object_ids = [o.id for o in self.plot.objects]

    def upd_aims(self, xyz: tuple[float, float, float], uv: tuple[float, float]):
        x, y, z = xyz
        u, v = uv
        xmin, xmax, ymin, ymax = self.vbounds
        self.yaim.vertices = ((xmin, y, 0), (xmax, y, 0))
        self.xaim.vertices = ((x, ymin, 0), (x, ymax, 0))
        self.zaim.vertices = ((x, y, 0), (x, y, z))
        self.pick.positions = (u, v, 0)
        self.xaim.visible = True
        self.yaim.visible = True
        self.zaim.visible = True
        self.pick.visible = True

    def onclick(self, data):
        x, y, z = data["position"]
        idx, smp = space_sample(self.gspace, np.array((x, y)))
        u, v = smp
        self.statusbar.value = f"| {x:+.03f} {y:+.03f} {z:+.03f} [{u:+.03f} {v:+.03f}] | "
        self.upd_aims((x, y, z), smp)
        self.upd_values(idx)

    def upd_values(self, idx):
        for fld in self.fields.values():
            assert fld.shape == self.gspdim or fld.shape[:-1] == self.gspdim

        status = []
        for name, fld in self.fields.items():
            value = fld[idx]
            vrepr = pprintnp(value)
            status.append(f"{name}={vrepr}")
        self.statusbar.value = self.statusbar.value + (" | ".join(status))
