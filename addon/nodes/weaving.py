"""
The nodes in this module generate stripes of woven fabric.
Warp stripes go along V(Y) axis. Weft stripes go along U(X) axis.

Resulting values are encoded as colors/images
with R channel corresponding to weft and G channel corresponding to warp.
The values are not generally restricted to range 0..1 and any operations could be applied to them via `MixRGB` node.

All the nodes suppose texture space to be divided into weaving cells, so that each cell contains single cross.
The cells has texture coordinates in range ``n + 0.0 .. n + 1.0``

The strobing nodes place stripes in the middle of each cell,
so that center of each stripe has coordinate ``n + 0.5``.

The weaving nodes generate elevation waves in range ``-1.0 .. +1.0``
with -1.0 indicating back side and +1.0 face side.
Elevation changes sinusoidally starting and ending at centers of neighbour cells.
Weaving nodes are unaware of stripes width and generate cell-wide waves.

When generating very thick stripes it may result in some visible intersections.
This could be fixed with ``RGBCurves`` applied to waves to make more steep,
but value range -1 to +1 shoudle be preserved.
And this may produce other more ugly artefacts, not yet fixed.

"""
import bpy

from .base import ShaderSharedNodeBase, ShaderVolatileNodeBase
from .utils import FMmixfloats, FMfmodulo, FMcosine, FMstripes, FMcircle


class BalancingMixin():
    def tweak_balancing(self, balanced, bal_name, wrp_name, wft_name, wrp_route, wft_route):
        inp_bal = self.inputs[bal_name]
        inp_wrp = self.inputs[wrp_name]
        inp_wft = self.inputs[wft_name]
        if balanced:
            inp_bal.enabled = True
            inp_wrp.enabled = False
            inp_wft.enabled = False
            inp_bal.default_value = inp_wrp.default_value
            self.link(self.inp.outputs[bal_name], wrp_route)
            self.link(self.inp.outputs[bal_name], wft_route)
        else:
            inp_bal.enabled = False
            inp_wrp.enabled = True
            inp_wft.enabled = True
            inp_wrp.default_value = inp_bal.default_value
            inp_wft.default_value = inp_bal.default_value
            self.link(self.inp.outputs[wrp_name], wrp_route)
            self.link(self.inp.outputs[wft_name], wft_route)


class FMWeaveScaling(BalancingMixin, ShaderVolatileNodeBase):
    """Dividing texture space.

    Scales vector to form weaving cells according to desired thread count.
    Basically, a wrapper around few simple vector math operations.

    Options:
        unbalanced
            Use separate values for warp and weft.

    Inputs:
        vector
            Original texture vector.
        thread count
            Desired number of stripes per original texture unit.

    Outputs:
        vector
            Scaled vector.
        scale
            Resulting size of weaving cells (relative to original texture unit). I don't know what is it for.
        snapped
            Original vector snapped to weaving cells.
            Using the vector for some texture like noise will produce same value within each cell.
    """
    bl_idname = "fabricomatic.weave_scaling"
    bl_label = "weave scaling"

    inp_sockets = (
        ('NodeSocketVector', 'vector'),
        ('NodeSocketFloat', 'threads count', 200, 0),
        ('NodeSocketFloat', 'warp count', 200, 0),
        ('NodeSocketFloat', 'weft count', 200, 0),
    )
    out_sockets = (
        ('NodeSocketVector', 'vector'),
        ('NodeSocketVector', 'scale'),
        ('NodeSocketVector', 'snapped'),
    )

    unbalanced: bpy.props.BoolProperty(
        name="Unbalanced",
        description="Separate parameters for warp and weft",
        default=False,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.tweak_balance()

    def build_tree(self):
        # rerouted in tweak_balance
        freq = self.vec((self.inp, 'warp count'), (self.inp, 'weft count'), name='freq')

        vector = self.vmath('MULTIPLY', (self.inp, 'vector'), freq)
        scale = self.vmath('DIVIDE', ('=', (1.0, 1.0, 1.0)), freq)
        snapped = self.vmath('SNAP', (self.inp, 'vector'), scale)
        self.link(vector, (self.out, 'vector'))
        self.link(scale, (self.out, 'scale'))
        self.link(snapped, (self.out, 'snapped'))

    def tweak_balance(self):
        self.tweak_balancing(
            not self.unbalanced,
            'threads count', 'warp count', 'weft count',
            ('freq', 'X'), ('freq', 'Y')
        )
  
    def draw_buttons(self, _context, layout):
        layout.prop(self, 'unbalanced')


class FMWeaveStrobing(BalancingMixin, ShaderVolatileNodeBase):
    """Generating periodic stripes for warp and weft.

    Outputs maps indicating placement of stripes.

    Options:
        unbalanced
            Use separate values for warp and weft.

    Inputs:
        vector
            UV vector
        thickness
            Relative width of stripes (ratio of fill to gaps, with 1 = cover full area)

    Outputs:
        strobes
            Map of stripes as triangle shaped profiles.
            Maximum value =1.0 at the very middle of stripes, down to =0.0 at edges and over gaps
        mask
            Map of stripes as binary values.
            Value =1.0 over stripes and =0.0 over gaps
        profile
            Map of stripes with semicircular profile.
            Value is normalized to have height =1.0
            To make it perfectly round (in texture scale) it should be scaled down
            proportinally to thickness (by overlaying node) and overall weaving scale (by bump/displacement node).
        alpha
            Overall binary transparency mask
    """
    bl_idname = "fabricomatic.weave_strobing"
    bl_label = "weave strobing"

    inp_sockets = (
        ('NodeSocketVector', 'vector'),
        ('NodeSocketFloat', 'thickness', 0.5, 0.0, 1.0),
        ('NodeSocketFloat', 'warp thickness', 0.5, 0.0, 1.0),
        ('NodeSocketFloat', 'weft thickness', 0.5, 0.0, 1.0),
    )
    out_sockets = (
        ('NodeSocketColor', 'strobes'),
        ('NodeSocketColor', 'mask'),
        ('NodeSocketColor', 'profiles'),
        ('NodeSocketFloat', 'alpha'),
    )

    unbalanced: bpy.props.BoolProperty(
        name="Unbalanced",
        description="Separate parameters for warp and weft",
        default=False,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.tweak_balance()

    def build_tree(self):
        xyz = self.xyz((self.inp, 'vector'))

        # rerouted from tweak_balanced
        w_wrp = self.route('th_wrp')
        w_wft = self.route('th_wft')

        stripes_wrp = self.node(
            FMstripes,            
            {'t': (xyz, 'X'),
             'period': 1.0,
             'thickness': w_wrp
            })

        stripes_wft = self.node(
            FMstripes,
            {'t': (xyz, 'Y'),
             'period': 1.0,
             'thickness': w_wft
            })

        strobes = self.col(
            (stripes_wft, 'strobe'),
            (stripes_wrp, 'strobe'))

        mask = self.col(
            self.math('GREATER_THAN', (stripes_wft, 'strobe'), 0),
            self.math('GREATER_THAN', (stripes_wrp, 'strobe'), 0),
        )

        profiles = self.col(
            self.node(FMcircle, ((stripes_wft, 'strobe'),)),
            self.node(FMcircle, ((stripes_wrp, 'strobe'),)),
        )

        alpha = (self.node('ShaderNodeSeparateHSV', inputs={0: mask}), 'V')

        self.link(strobes, (self.out, 'strobes'))
        self.link(mask, (self.out, 'mask'))
        self.link(profiles, (self.out, 'profiles'))
        self.link(alpha, (self.out, 'alpha'))

    def tweak_balance(self):
        self.tweak_balancing(
            not self.unbalanced,
            'thickness', 'warp thickness', 'weft thickness',
            'th_wrp', 'th_wft'
        )

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'unbalanced')


class FMWeaveBulging(BalancingMixin, ShaderVolatileNodeBase):
    """Thickness bulging

    Makes stripes thicker on face side, proportional to elevation.

    Options:
        unbalanced
            Use separate values for warp and weft.

    Inputs:
        waves
            Map of stripes elevation (from some `weaving` node)
        thickness
            Base thickness/width
        shrinking
            Factor of shrinking on back side

    Outputs:
        thickness
            Resulting thickness
    """

    bl_idname = "fabricomatic.weave_bulging"
    bl_label = "weave bulging"

    inp_sockets = (
        ('NodeSocketColor', 'waves'),
        ('NodeSocketFloat', 'thickness', 0.5, 0, 1.0),
        ('NodeSocketFloat', 'warp thickness', 0.5, 0, 1.0),
        ('NodeSocketFloat', 'weft thickness', 0.5, 0, 1.0),
        ('NodeSocketFloat', 'shrinking', 0.5, 0, 1.0),
        ('NodeSocketFloat', 'warp shrinking', 0.5, 0, 1.0),
        ('NodeSocketFloat', 'weft shrinking', 0.5, 0, 1.0),
    )
    out_sockets = (
        ('NodeSocketFloat', 'warp thickness'),
        ('NodeSocketFloat', 'weft thickness'),
    )

    unbalanced: bpy.props.BoolProperty(
        name="Unbalanced",
        description="Separate parameters for warp and weft",
        default=False,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.tweak_balance()

    def build_tree(self):
        # rerouted from tweak_balanced
        max_wrp = self.route('max_wrp')
        max_wft = self.route('max_wft')
        fac_wrp = self.route('fac_wrp')
        fac_wft = self.route('fac_wft')

        min_wrp = self.math('MULTIPLY', max_wrp, self.math('SUBTRACT', 1.0, fac_wrp))
        min_wft = self.math('MULTIPLY', max_wft, self.math('SUBTRACT', 1.0, fac_wft))

        factor = self.mix(
            'MULTIPLY',
            ('=', (0.5, 0.5, 0.0, 0.0)),
            self.mix(
                'ADD',
                ('=', (1.0, 1.0, 0.0, 0.0)),
                (self.inp, 'waves')))

        factor_rgb = self.rgb(factor)

        th_wrp = self.node(
            'ShaderNodeMapRange',
            inputs={
                'Value': (factor_rgb, 'G'),
                'To Min': min_wrp,
                'To Max': max_wrp
            })

        th_wft = self.node(
            'ShaderNodeMapRange',
            inputs={
                'Value': (factor_rgb, 'R'),
                'To Min': min_wft,
                'To Max': max_wft
            })

        self.link(th_wrp, (self.out, 'warp thickness'))
        self.link(th_wft, (self.out, 'weft thickness'))

    def tweak_balance(self):
        self.tweak_balancing(
            not self.unbalanced,
            'thickness', 'warp thickness', 'weft thickness',
            'max_wrp', 'max_wft'
        )
        self.tweak_balancing(
            not self.unbalanced,
            'shrinking', 'warp shrinking', 'weft shrinking',
            'fac_wrp', 'fac_wft'
        )

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'unbalanced')


class FMWeaveOverlaying(BalancingMixin, ShaderVolatileNodeBase):
    """Combining and adjusting maps.

    The elevation and profiles are scaled according to provided thickness.
    Waves of stripes are adjusted, so that they lay precisely on top of each other.

    Stiffness makes corresponding stripes more straight and less waving.

    It simulates tension of yarn in loom.
    Usually it is warp yarn straighened in loom's frame,
    but some weavers beat weft yarn so hard that it becomes the other way around.

    Options:
        unbalanced
            Use separate values for warp and weft.
        stifness
            Apply stiffness. Applying it to both warp and weft will obviously compensate the effect.

    Inputs:
        strobes
            Boolean map of stripes.
        profiles
            Height map of stripes' profiles.
        waves
            Height map of stripes' waves. Should be in range ``-1 .. +1``
        thickness
            Height of stripes (kinda radius of semi-circular shape).
        stiffness
            Stiffness of corresponding stripes (1.0 = no waving).

    Outputs:
        evalation
            Combined elevation of waves and profiles separately for each channel.
        mask
            Map indicating which kind of stripe is on face side.
        height
            Resulting height for bump mapping.
    """

    # stiffnessless:
    #     a_wrp = h_wft/2
    #     b_wrp = h_wft/2
    #     a_wft = h_wrp/2
    #     b_wft = h_wrp/2
    #     midlevel = (h_wrp + h_wft) / 2
    #
    # stiffness correction:
    #     shift (against center):
    #         s_wrp = k_wrp * h_wft / 2
    #         s_wft = k_wft * h_wrp / 2
    #     amplitude increasing/decreasing:
    #         f_wft = +s_wrp -s_wft
    #         f_wrp = +s_wft -s_wrp
    #     a_wrp += f_wrp
    #     a_wft += f_wft
    #     b_all += max(f_wrp, f_wft)
    #

    bl_idname = "fabricomatic.weave_overlaying"
    bl_label = "weave overlaying"

    inp_sockets = (
        ('NodeSocketColor', 'waves'),
        ('NodeSocketColor', 'strobes'),
        ('NodeSocketColor', 'profiles'),
        ('NodeSocketFloat', 'thickness', 0.5, 0.0, 1.0),
        ('NodeSocketFloat', 'warp thickness', 0.5, 0.0, 1.0),
        ('NodeSocketFloat', 'weft thickness', 0.5, 0.0, 1.0),
        ('NodeSocketFloat', 'warp stiffness', 1.0, 0.0, 1.0),
        ('NodeSocketFloat', 'weft stiffness', 0.0, 0.0, 1.0),
    )
    out_sockets = (
        ('NodeSocketColor', 'elevation'),
        ('NodeSocketColor', 'mask'),
        ('NodeSocketFloat', 'height'),
    )

    unbalanced: bpy.props.BoolProperty(
        name="Unbalanced",
        description="Separate parameters for warp and weft",
        default=False,
        update=lambda s, c: s.tweak_balance())

    stiffnessful: bpy.props.BoolProperty(
        name="Stiffness", 
        default=False,
        update=lambda s, c: s.tweak_stiffnessful(),
        description="Straighten stripes")

    def init(self, context):
        super().init(context)
        self.tweak_balance()
        self.tweak_stiffnessful()

    def build_tree(self):
        # rerouted in tweak_balanced
        h_wrp = self.route('th_wrp')
        h_wft = self.route('th_wft')

        thick = self.col(h_wft, h_wrp)
        x_thick = self.mix('MULTIPLY', self.col(h_wrp, h_wft), ('=', (0.5, 0.5, 0.0, 0.0)), name='x_thick')
        # stifness correction

        s_wrp = self.math(
            'MULTIPLY',
            0.5,
            self.math(
                'MULTIPLY',
                (self.inp, 'warp stiffness'),
                h_wft))
        s_wft = self.math(
            'MULTIPLY',
            0.5,
            self.math(
                'MULTIPLY',
                (self.inp, 'weft stiffness'),
                h_wrp))

        f_wrp = self.math('SUBTRACT', s_wrp, s_wft)
        f_wft = self.math('SUBTRACT', s_wft, s_wrp)

        self.mix(
            'ADD',
            x_thick,
            self.col(f_wrp, f_wft),
            name='ampl_s')

        self.mix(
            'ADD',
            x_thick,
            self.math(
                'MULTIPLY',
                0.5,
                self.math(
                    'MAXIMUM',
                    f_wrp,
                    f_wft)),
            name='base_s')

        # rerouted in tweak_stifnessful
        base = self.route('base')
        ampl = self.route('ampl')

        waves = self.mix(
            'ADD',
            base,
            self.mix(
                'MULTIPLY',
                (self.inp, 'waves'),
                ampl))

        profiles = self.mix(
            'MULTIPLY',
            (self.inp, 'profiles'),
            thick)

        height = self.mix(
            'ADD',
            self.mix('MULTIPLY', waves, (self.inp, 'strobes')),
            profiles,
            name='height')

        mask = self.node(FMWeaveMasking, inputs={0: height})
        height_hsv = self.node('ShaderNodeSeparateHSV', inputs={0: height}, name='height_hsv')

        self.link(mask, (self.out, 'mask'))
        self.link(height, (self.out, 'elevation'))
        self.link((height_hsv, 'V'), (self.out, 'height'))

    def tweak_balance(self):
        self.tweak_balancing(
            not self.unbalanced,
            'thickness', 'warp thickness', 'weft thickness',
            'th_wrp', 'th_wft'
        )

    def tweak_stiffnessful(self):
        if self.stiffnessful:
            self.inputs['warp stiffness'].enabled = True
            self.inputs['weft stiffness'].enabled = True
            self.link('ampl_s', 'ampl')
            self.link('base_s', 'base')
        else:
            self.inputs['warp stiffness'].enabled = False
            self.inputs['weft stiffness'].enabled = False
            self.link('x_thick', 'ampl')
            self.link('x_thick', 'base')

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'unbalanced')
        layout.prop(self, 'stiffnessful')


class FMWeaveMasking(ShaderSharedNodeBase):
    """Creating thread mask from their elevations"""

    bl_idname = "fabricomatic.weave_masking"
    bl_label = "weave masking"

    inp_sockets = (
        ('NodeSocketColor', 'elevation'),
    )
    out_sockets = (
        ('NodeSocketColor', 'mask'),
    )

    def build_tree(self):
        height_rgb = self.rgb((self.inp, 'elevation'))
        mask = self.col(
            self.math('GREATER_THAN', (height_rgb, 'R'), (height_rgb, 'G')),
            self.math('GREATER_THAN', (height_rgb, 'G'), (height_rgb, 'R')),
            name='mask')
        self.link(mask, (self.out, 'mask'))


class FMWeavePatternSampling(ShaderSharedNodeBase):
    """Generating coordinates for pattern sampling.

    Coordinates are snapped so that each pixel of pattern corresponds to cell of weaving.
    The vectors are shifted to point to neighbouring pixels/cells.

    The vectors should be fed to texture node and the resulting color routed to
    `FMWeavePatternInterpolating` to produce smooth waves.

    Parameters:
        image
            The pattern image. Should be black-n-white.

    Inputs:
        vector
            UV vector
        width
            width of image in pixels.
        height
            height of image in pixels.

    Outputs:
        Vectors shifted left/right up/down, and snapped to cells or half-cells.

    """
    bl_idname = "fabricomatic.pattern_sampling"
    bl_label = "pattern sampling"

    inp_sockets = (
        ('NodeSocketVector', 'vector'),
        ('NodeSocketInt', 'width', 16),
        ('NodeSocketInt', 'height', 16),
    )
    out_sockets = (
        ('NodeSocketVector', 'vector 0'),
        ('NodeSocketVector', 'vector l'),
        ('NodeSocketVector', 'vector r'),
        ('NodeSocketVector', 'vector d'),
        ('NodeSocketVector', 'vector u'),
    )

    def build_tree(self):
        scale = self.vmath(
            'DIVIDE',
            ('=', (1.0, 1.0, 1.0)),
            self.vec((self.inp, 'width'), (self.inp, 'height')))

        vec_0 = self.vmath(
            'SNAP',
            self.vmath(
                'MULTIPLY',
                (self.inp, 'vector'),
                scale),
            scale)

        def scalesnap(shift):
            return self.vmath(
                'SNAP',
                self.vmath(
                    'MULTIPLY',
                    self.vmath(
                        'ADD',
                        (self.inp, 'vector'),
                        ('=', shift)),
                    scale),
                scale)

        vec_l = scalesnap((-0.5, 0.0, 0.0))
        vec_r = scalesnap((+0.5, 0.0, 0.0))
        vec_d = scalesnap((0.0, -0.5, 0.0))
        vec_u = scalesnap((0.0, +0.5, 0.0))

        self.link(vec_0, (self.out, 'vector 0'))
        self.link(vec_l, (self.out, 'vector l'))
        self.link(vec_r, (self.out, 'vector r'))
        self.link(vec_d, (self.out, 'vector d'))
        self.link(vec_u, (self.out, 'vector u'))


class FMWeavePatternInterpolating(ShaderSharedNodeBase):
    """Interpolating sampled pattern.

    Interpolates values from heighbour cells to form smooth transitions.

    Inputs:
        vector
            original, unsnapped vector
        value l/r/u/d
            values for neighbouring cells
    """

    bl_idname = "fabricomatic.pattern_interpolating"
    bl_label = "pattern interpolating"

    inp_sockets = (
        ('NodeSocketVector', 'vector'),
        ('NodeSocketFloat', 'value l'),
        ('NodeSocketFloat', 'value r'),
        ('NodeSocketFloat', 'value d'),
        ('NodeSocketFloat', 'value u'),
    )
    out_sockets = (
        ('NodeSocketColor', 'waves'),
    )

    def build_tree(self):
        xyz = self.xyz(
            self.vmath(
                'FRACTION',
                self.vmath(
                    'ADD',
                    (self.inp, 'vector'),
                    ('=', (-0.5, -0.5, 0.0)))))

        weft = self.node(
            FMcosine,
            inputs={
                't': self.node(
                    FMmixfloats,
                    inputs={
                        'fac': (xyz, 'X'),
                        'value 1': (self.inp, 'value l'),
                        'value 2': (self.inp, 'value r'),
                    }),
                'period': 2.0,
                'shift': -0.5,
                'min': -1.0,
                'max': +1.0,
            })

        warp = self.node(
            FMcosine,
            inputs={
                't': self.node(
                    FMmixfloats,
                    inputs={
                        'fac': (xyz, 'Y'),
                        'value 1': (self.inp, 'value d'),
                        'value 2': (self.inp, 'value u'),
                    }),
                'period': 2.0,
                'shift': 0,
                'min': -1.0,
                'max': +1.0,
            })

        out = self.col(weft, warp)

        self.link(out, (self.out, 'waves'))


class FMWeavingPlain(ShaderSharedNodeBase):
    """Plain weaving.

    Generating simple checkerboard-like interlacing.

    Inputs:
        vector
            UV vector

    Outputs:
        waves

    """
    bl_idname = "fabricomatic.weaving_plain"
    bl_label = "weaving plain"

    inp_sockets = (
        ('NodeSocketVector', 'vector'),
    )
    out_sockets = (
        ('NodeSocketColor', 'waves'),
    )

    def build_tree(self):
        xyz = self.xyz((self.inp, 'vector'))

        weft = self.node(
            FMcosine,
            inputs={
                't': self.math('ADD', (xyz, 'X'), self.math('FLOOR', (xyz, 'Y'))),
                'period': 2.0,
                'shift': -0.25,
                'min': -1.0,
                'max': +1.0,
            })
        warp = self.node(
            FMcosine,
            inputs={
                't': self.math('ADD', (xyz, 'Y'), self.math('FLOOR', (xyz, 'X'))),
                'period': 2.0,
                'shift': +0.25,
                'min': -1.0,
                'max': +1.0,
            })

        out = self.col(weft, warp)

        self.link(out, (self.out, 'waves'))


class FMWeavingTwill(ShaderSharedNodeBase):
    """Twill weaving

    Generating interlacing according to twill scheme specifying how weft yarn goes between warp yarns.

    This covers all kinds of twill and satin weaving. Especially if to change parametyers dynamically.

    Inputs:
        vector
            UV vector
        above
            number of cells a weft stripe is on face side (above warp)
        below
            number of cells a weft stripe is on back side (below warp)
        shift
            number of cells to shift pattern every subsequent row
    Outputs:
        waves
            map of stripe elevation, in range -1.0..+1.0

    """
    bl_idname = "fabricomatic.weaving_twill"
    bl_label = "weaving twill"

    inp_sockets = (
        ('NodeSocketVector', 'vector'),
        ('NodeSocketInt', 'above', 2, 1),
        ('NodeSocketInt', 'below', 2, 1),
        ('NodeSocketInt', 'shift', 1),
    )
    out_sockets = (
        ('NodeSocketColor', 'waves'),
    )

    def build_tree(self):
        # ('math', 'ADD', x, y)
        period = self.math('ADD', (self.inp, 'above'), (self.inp, 'below'))

        # binary integer formula:
        # h = (x - y * shift) mod (a + b) < a
        def twill(vec):
            xyz = self.xyz(vec)
            return self.math(
                'LESS_THAN',
                self.node(
                    FMfmodulo,
                    inputs={
                        'divident':
                            self.math(
                                'SUBTRACT',
                                (xyz, 'X'),
                                self.math(
                                    'MULTIPLY',
                                    (xyz, 'Y'),
                                    (self.inp, 'shift'))),
                        'divisor': period
                    }),
                (self.inp, 'above'))

        def snap(*shift):
            return self.vmath(
                'SNAP',
                self.vmath('ADD', (self.inp, 'vector'), ('=', shift)),
                ('=', (1.0, 1.0, 1.0)))

        waves = self.node(
            FMWeavePatternInterpolating,
            inputs={
                'vector': (self.inp, 'vector'),
                'value l': twill(snap(-0.5, 0.0, 0.0)),
                'value r': twill(snap(+0.5, 0.0, 0.0)),
                'value d': twill(snap(0.0, -0.5, 0.0)),
                'value u': twill(snap(0.0, +0.5, 0.0)),
                })

        self.link(waves, (self.out, 'waves'))


class FMWeavingJacquard(ShaderVolatileNodeBase):
    """Jacquard weaving.

    Generating interlacing according to given pattern image (corresponding to "weaving draft" in weaving reality).
    White pixels indicate weft-facing cells, black pixels indicate warp-facing cells.

    Paramaters:
        pattern
            a black-n-white image specifying weaving pattern.

    Inputs:
        vector
            UV vector.

    Outputs:
        waves
            map of stripe elevation.

    """
    bl_idname = "fabricomatic.weaving_jacquard"
    bl_label = "weaving jacquard"

    inp_sockets = (
        ('NodeSocketVector', 'vector'),
    )
    out_sockets = (
        ('NodeSocketColor', 'waves'),
    )

    pattern: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Pattern",
        update=lambda s, c: s.update_pattern())

    def init(self, context):
        super().init(context)
        self.pattern = bpy.data.images.new("weaving draft", 16, 16, is_data=True)

    def build_tree(self):
        sampling = self.node(
            FMWeavePatternSampling,
            name='sampling',
            inputs={
                'vector': (self.inp, 'vector'),
                'width': 1,
                'height': 1,
                })

        tex_l = self.node(
            'ShaderNodeTexImage',
            name='tex_l',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector l')})
        tex_r = self.node(
            'ShaderNodeTexImage',
            name='tex_r',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector r')})
        tex_d = self.node(
            'ShaderNodeTexImage',
            name='tex_d',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector d')})
        tex_u = self.node(
            'ShaderNodeTexImage',
            name='tex_u',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector u')})

        waves = self.node(
            FMWeavePatternInterpolating,
            inputs={
                'vector': (self.inp, 'vector'),
                'value l': tex_l,
                'value r': tex_r,
                'value d': tex_d,
                'value u': tex_u,
                })

        self.link(waves, (self.out, 'waves'))

    def update_pattern(self):
        self.nodes['tex_l'].image = self.pattern
        self.nodes['tex_r'].image = self.pattern
        self.nodes['tex_d'].image = self.pattern
        self.nodes['tex_u'].image = self.pattern
        if self.pattern:
            spread = self.nodes['sampling']
            spread.inputs['width'].default_value = self.pattern.size[0]
            spread.inputs['height'].default_value = self.pattern.size[1]

    def draw_buttons(self, _context, layout):
        layout.template_ID(self, 'pattern', new='image.new', open='image.open')
