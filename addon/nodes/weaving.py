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
from .utils import FMmixfloats, FMfmodulo, FMcosine, FMstripes, FMWeaveProfiling


class FMWeaveScaling(ShaderVolatileNodeBase):
    """Dividing texture space.

    Scales vector to form weaving cells according to desired thread count.
    Basically, a wrapper around few simple vector math operations.

    Options:
        balanced
            Use the same thread count for warp and weft.

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

    balanced: bpy.props.BoolProperty(
        name="Balanced",
        description="Equal paramewters for warp and weft",
        default=True,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.tweak_balance()

    def build_tree(self):
        # x = warp count, y = weft count
        # rerouted in tweak_balance
        freq = self.add_vec(0.0, 0.0, name='freq')

        vector = self.add_vmath('MULTIPLY', (self.inp, 'vector'), freq)
        scale = self.add_vmath('DIVIDE', ('=', (1.0, 1.0, 1.0)), freq)
        snapped = self.add_vmath('SNAP', (self.inp, 'vector'), scale)
        self.add_link(vector, (self.out, 'vector'))
        self.add_link(scale, (self.out, 'scale'))
        self.add_link(snapped, (self.out, 'snapped'))

    def tweak_balance(self):
        self.inputs['threads count'].enabled = self.balanced
        self.inputs['warp count'].enabled = not self.balanced
        self.inputs['weft count'].enabled = not self.balanced
        if self.balanced:
            self.add_link((self.inp, 'threads count'), ('freq', 'X'))
            self.add_link((self.inp, 'threads count'), ('freq', 'Y'))
        else:
            self.add_link((self.inp, 'warp count'), ('freq', 'X'))
            self.add_link((self.inp, 'weft count'), ('freq', 'Y'))

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')


class FMWeaveStrobing(ShaderVolatileNodeBase):
    """Generating periodic stripes for warp and weft.

    Options:
        balanced
            Use the same thickness for warp and weft scaling

    Inputs:
        vector
            UV vector
        thickness
            Relative width of stripes (ratio of fill to gaps, with 1 = cover full area)

    Outputs:
        strobes
            Boolean mask indicating presence of warp or weft
        alpha
            Boolean mask of stripes/gaps
        profiles
            Triangle-shaped bump elevation of each stripe.
            It has value 1.0 in the middle of stripes, and 0.0 at its edges.
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
        ('NodeSocketColor', 'profiles'),
        ('NodeSocketFloat', 'alpha'),
    )

    balanced: bpy.props.BoolProperty(
        name="Balanced",
        description="Equal paramewters for warp and weft",
        default=True,
        update=lambda s, c: s.tweak_balance())

    profile_shape: bpy.props.EnumProperty(
        name="Profle shape",
        items=FMWeaveProfiling.PROFILE_SHAPES,
        update=lambda s, c: s.tweak_profile(),
        default='ROUND')

    def init(self, context):
        super().init(context)
        self.tweak_balance()

    def build_tree(self):
        xyz = self.add_xyz((self.inp, 'vector'))

        # rerouted from tweak_balanced
        w_wrp = self.add_node('NodeReroute', name='th_wrp')
        w_wft = self.add_node('NodeReroute', name='th_wft')

        stripes_wrp = self.add_node(
            FMstripes,
            name='wrp_stripes',
            inputs={
                't': (xyz, 'X'),
                'period': 1.0,
                'thickness': w_wrp
            })

        stripes_wft = self.add_node(
            FMstripes,
            name='wrp_stripes',
            inputs={
                't': (xyz, 'Y'),
                'period': 1.0,
                'thickness': w_wft
            })

        strobes = self.add_col(
            (stripes_wft, 'strobe'),
            (stripes_wrp, 'strobe'))

        profiles = self.add_col(
            (stripes_wft, 'profile'),
            (stripes_wrp, 'profile'),
            name='profiles')

        profiling = self.add_node(FMWeaveProfiling, inputs={'profiles': profiles}, name='profiling')

        mask = self.add_node('ShaderNodeSeparateHSV', inputs={0: strobes})

        self.add_link(strobes, (self.out, 'strobes'))
        self.add_link(profiling, (self.out, 'profiles'))
        self.add_link((mask, 'V'), (self.out, 'alpha'))

    def tweak_balance(self):
        self.inputs['thickness'].enabled = self.balanced
        self.inputs['warp thickness'].enabled = not self.balanced
        self.inputs['weft thickness'].enabled = not self.balanced
        if self.balanced:
            self.add_link((self.inp, 'thickness'), 'th_wrp')
            self.add_link((self.inp, 'thickness'), 'th_wft')
        else:
            self.add_link((self.inp, 'warp thickness'), 'th_wrp')
            self.add_link((self.inp, 'weft thickness'), 'th_wft')

    def tweak_profile(self):
        if self.profile_shape == 'NONE':
            self.add_link('profiles', (self.out, 'profiles'))
        else:
            self.add_link('profiling', (self.out, 'profiles'))
            self.get_node('profiling').profile_shape = self.profile_shape

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')
        layout.prop(self, 'profile_shape')


class FMWeaveBulging(ShaderVolatileNodeBase):
    """Thickness bulging

    Makes stripes thicker on face side, proportional to elevation.

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

    balanced: bpy.props.BoolProperty(
        name="Balanced",
        description="Equal paramewters for warp and weft",
        default=True,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.tweak_balance()

    def build_tree(self):
        # rerouted from tweak_balanced
        max_wrp = self.add_node('NodeReroute', name='max_wrp')
        max_wft = self.add_node('NodeReroute', name='max_wft')
        fac_wrp = self.add_node('NodeReroute', name='fac_wrp')
        fac_wft = self.add_node('NodeReroute', name='fac_wft')

        min_wrp = self.add_math('MULTIPLY', max_wrp, self.add_math('SUBTRACT', 1.0, fac_wrp))
        min_wft = self.add_math('MULTIPLY', max_wft, self.add_math('SUBTRACT', 1.0, fac_wft))

        factor = self.add_mix(
            'MULTIPLY',
            ('=', (0.5, 0.5, 0.0, 0.0)),
            self.add_mix(
                'ADD',
                ('=', (1.0, 1.0, 0.0, 0.0)),
                (self.inp, 'waves')))

        factor_rgb = self.add_rgb(factor)

        th_wrp = self.add_node(
            'ShaderNodeMapRange',
            inputs={
                'Value': (factor_rgb, 'G'),
                'To Min': min_wrp,
                'To Max': max_wrp
            })

        th_wft = self.add_node(
            'ShaderNodeMapRange',
            inputs={
                'Value': (factor_rgb, 'R'),
                'To Min': min_wft,
                'To Max': max_wft
            })

        self.add_link(th_wrp, (self.out, 'warp thickness'))
        self.add_link(th_wft, (self.out, 'weft thickness'))

    def tweak_balance(self):
        self.inputs['thickness'].enabled = self.balanced
        self.inputs['shrinking'].enabled = self.balanced
        self.inputs['warp thickness'].enabled = not self.balanced
        self.inputs['warp shrinking'].enabled = not self.balanced
        self.inputs['weft thickness'].enabled = not self.balanced
        self.inputs['weft shrinking'].enabled = not self.balanced
        if self.balanced:
            self.add_link((self.inp, 'thickness'), 'max_wrp')
            self.add_link((self.inp, 'thickness'), 'max_wft')
            self.add_link((self.inp, 'shrinking'), 'fac_wrp')
            self.add_link((self.inp, 'shrinking'), 'fac_wft')
        else:
            self.add_link((self.inp, 'warp thickness'), 'max_wrp')
            self.add_link((self.inp, 'weft thickness'), 'max_wft')
            self.add_link((self.inp, 'warp shrinking'), 'fac_wrp')
            self.add_link((self.inp, 'weft shrinking'), 'fac_wft')

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')


class FMWeaveOverlaying(ShaderVolatileNodeBase):
    """Combining and adjusting maps.

    The elevation and profiles are scaled according to provided thickness.
    Waves of stripes are adjusted, so that they lay precisely on top of each other.

    Stiffness makes corresponding stripes more straight and less waving.

    It simulates tension of yarn in loom.
    Usually it is warp yarn straighened in loom's frame,
    but some weavers beat weft yarn so hard that it becomes the other way around.

    Options:
        balanced
            Use the same thickness for warp and weft.
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

    balanced: bpy.props.BoolProperty(
        name="Balanced",
        description="Equal paramewters for warp and weft",
        default=True,
        update=lambda s, c: s.tweak_balance())

    stiffnessful: bpy.props.BoolProperty(
        name="Stiffness", default=False,
        update=lambda s, c: s.tweak_stiffnessful(),
        description="Straighten stripes")

    def init(self, context):
        super().init(context)
        self.tweak_balance()
        self.tweak_stiffnessful()

    def build_tree(self):
        # rerouted in tweak_balanced
        h_wrp = self.add_node('NodeReroute', name='th_wrp')
        h_wft = self.add_node('NodeReroute', name='th_wft')

        thick = self.add_col(h_wft, h_wrp)
        x_thick = self.add_mix('MULTIPLY', self.add_col(h_wrp, h_wft), ('=', (0.5, 0.5, 0.0, 0.0)), name='x_thick')
        # stifness correction

        s_wrp = self.add_math(
            'MULTIPLY',
            0.5,
            self.add_math(
                'MULTIPLY',
                (self.inp, 'warp stiffness'),
                h_wft))
        s_wft = self.add_math(
            'MULTIPLY',
            0.5,
            self.add_math(
                'MULTIPLY',
                (self.inp, 'weft stiffness'),
                h_wrp))

        f_wrp = self.add_math('SUBTRACT', s_wrp, s_wft)
        f_wft = self.add_math('SUBTRACT', s_wft, s_wrp)

        self.add_mix(
            'ADD',
            x_thick,
            self.add_col(f_wrp, f_wft),
            name='ampl_s')

        self.add_mix(
            'ADD',
            x_thick,
            self.add_math(
                'MULTIPLY',
                0.5,
                self.add_math(
                    'MAXIMUM',
                    f_wrp,
                    f_wft)),
            name='base_s')

        # rerouted in tweak_stifnessful
        base = self.add_node('NodeReroute', name='base')
        ampl = self.add_node('NodeReroute', name='ampl')

        waves = self.add_mix(
            'ADD',
            base,
            self.add_mix(
                'MULTIPLY',
                (self.inp, 'waves'),
                ampl))

        profiles = self.add_mix(
            'MULTIPLY',
            (self.inp, 'profiles'),
            thick)

        height = self.add_mix(
            'ADD',
            self.add_mix('MULTIPLY', waves, (self.inp, 'strobes')),
            profiles,
            name='height')

        mask = self.add_node(FMWeaveMasking, inputs={0: height})
        height_hsv = self.add_node('ShaderNodeSeparateHSV', inputs={0: height}, name='height_hsv')

        self.add_link(mask, (self.out, 'mask'))
        self.add_link(height, (self.out, 'elevation'))
        self.add_link((height_hsv, 'V'), (self.out, 'height'))

    def tweak_balance(self):
        if self.balanced:
            self.inputs['thickness'].enabled = True
            self.inputs['warp thickness'].enabled = False
            self.inputs['weft thickness'].enabled = False
            self.add_link((self.inp, 'thickness'), 'th_wrp')
            self.add_link((self.inp, 'thickness'), 'th_wft')
        else:
            self.inputs['thickness'].enabled = False
            self.inputs['warp thickness'].enabled = True
            self.inputs['weft thickness'].enabled = True
            self.add_link((self.inp, 'warp thickness'), 'th_wrp')
            self.add_link((self.inp, 'weft thickness'), 'th_wft')

    def tweak_stiffnessful(self):
        if self.stiffnessful:
            self.inputs['warp stiffness'].enabled = True
            self.inputs['weft stiffness'].enabled = True
            self.add_link('ampl_s', 'ampl')
            self.add_link('base_s', 'base')
        else:
            self.inputs['warp stiffness'].enabled = False
            self.inputs['weft stiffness'].enabled = False
            self.add_link('x_thick', 'ampl')
            self.add_link('x_thick', 'base')

    # def tweak_softness(self):
    #     if self.softmask:
    #         self.add_link('height', (self.out, 'mask'))
    #     else:
    #         self.add_link('mask', (self.out, 'mask'))

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')
        layout.prop(self, 'stiffnessful')
        # layout.prop(self, 'softmask')


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
        height_rgb = self.add_rgb((self.inp, 'elevation'))
        mask = self.add_col(
            self.add_math('GREATER_THAN', (height_rgb, 'R'), (height_rgb, 'G')),
            self.add_math('GREATER_THAN', (height_rgb, 'G'), (height_rgb, 'R')),
            name='mask')
        self.add_link(mask, (self.out, 'mask'))


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
        scale = self.add_vmath(
            'DIVIDE',
            ('=', (1.0, 1.0, 1.0)),
            self.add_vec((self.inp, 'width'), (self.inp, 'height')))

        vec_0 = self.add_vmath(
            'SNAP',
            self.add_vmath(
                'MULTIPLY',
                (self.inp, 'vector'),
                scale),
            scale)

        def scalesnap(shift):
            return self.add_vmath(
                'SNAP',
                self.add_vmath(
                    'MULTIPLY',
                    self.add_vmath(
                        'ADD',
                        (self.inp, 'vector'),
                        ('=', shift)),
                    scale),
                scale)

        vec_l = scalesnap((-0.5, 0.0, 0.0))
        vec_r = scalesnap((+0.5, 0.0, 0.0))
        vec_d = scalesnap((0.0, -0.5, 0.0))
        vec_u = scalesnap((0.0, +0.5, 0.0))

        self.add_link(vec_0, (self.out, 'vector 0'))
        self.add_link(vec_l, (self.out, 'vector l'))
        self.add_link(vec_r, (self.out, 'vector r'))
        self.add_link(vec_d, (self.out, 'vector d'))
        self.add_link(vec_u, (self.out, 'vector u'))


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
        xyz = self.add_xyz(
            self.add_vmath(
                'FRACTION',
                self.add_vmath(
                    'ADD',
                    (self.inp, 'vector'),
                    ('=', (-0.5, -0.5, 0.0)))))

        weft = self.add_node(
            FMcosine,
            inputs={
                't': self.add_node(
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

        warp = self.add_node(
            FMcosine,
            inputs={
                't': self.add_node(
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

        out = self.add_col(weft, warp)

        self.add_link(out, (self.out, 'waves'))


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
        xyz = self.add_xyz((self.inp, 'vector'))

        weft = self.add_node(
            FMcosine,
            inputs={
                't': self.add_math('ADD', (xyz, 'X'), self.add_math('FLOOR', (xyz, 'Y'))),
                'period': 2.0,
                'shift': -0.25,
                'min': -1.0,
                'max': +1.0,
            })
        warp = self.add_node(
            FMcosine,
            inputs={
                't': self.add_math('ADD', (xyz, 'Y'), self.add_math('FLOOR', (xyz, 'X'))),
                'period': 2.0,
                'shift': +0.25,
                'min': -1.0,
                'max': +1.0,
            })

        out = self.add_col(weft, warp)

        self.add_link(out, (self.out, 'waves'))


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
        period = self.add_math('ADD', (self.inp, 'above'), (self.inp, 'below'))

        # binary integer formula:
        # h = (x - y * shift) mod (a + b) < a
        def twill(vec):
            xyz = self.add_xyz(vec)
            return self.add_math(
                'LESS_THAN',
                self.add_node(
                    FMfmodulo,
                    inputs={
                        'divident':
                            self.add_math(
                                'SUBTRACT',
                                (xyz, 'X'),
                                self.add_math(
                                    'MULTIPLY',
                                    (xyz, 'Y'),
                                    (self.inp, 'shift'))),
                        'divisor': period
                    }),
                (self.inp, 'above'))

        def snap(*shift):
            return self.add_vmath(
                'SNAP',
                self.add_vmath('ADD', (self.inp, 'vector'), ('=', shift)),
                ('=', (1.0, 1.0, 1.0)))

        waves = self.add_node(
            FMWeavePatternInterpolating,
            inputs={
                'vector': (self.inp, 'vector'),
                'value l': twill(snap(-0.5, 0.0, 0.0)),
                'value r': twill(snap(+0.5, 0.0, 0.0)),
                'value d': twill(snap(0.0, -0.5, 0.0)),
                'value u': twill(snap(0.0, +0.5, 0.0)),
                })

        self.add_link(waves, (self.out, 'waves'))


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
        sampling = self.add_node(
            FMWeavePatternSampling,
            name='sampling',
            inputs={
                'vector': (self.inp, 'vector'),
                'width': 1,
                'height': 1,
                })

        tex_l = self.add_node(
            'ShaderNodeTexImage',
            name='tex_l',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector l')})
        tex_r = self.add_node(
            'ShaderNodeTexImage',
            name='tex_r',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector r')})
        tex_d = self.add_node(
            'ShaderNodeTexImage',
            name='tex_d',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector d')})
        tex_u = self.add_node(
            'ShaderNodeTexImage',
            name='tex_u',
            interpolation='Closest',
            inputs={'Vector': (sampling, 'vector u')})

        waves = self.add_node(
            FMWeavePatternInterpolating,
            inputs={
                'vector': (self.inp, 'vector'),
                'value l': tex_l,
                'value r': tex_r,
                'value d': tex_d,
                'value u': tex_u,
                })

        self.add_link(waves, (self.out, 'waves'))

    def update_pattern(self):
        self.get_node('tex_l').image = self.pattern
        self.get_node('tex_r').image = self.pattern
        self.get_node('tex_d').image = self.pattern
        self.get_node('tex_u').image = self.pattern
        if self.pattern:
            spread = self.get_node('sampling')
            spread.inputs['width'].default_value = self.pattern.size[0]
            spread.inputs['height'].default_value = self.pattern.size[1]

    def draw_buttons(self, _context, layout):
        layout.template_ID(self, 'pattern', new='image.new', open='image.open')
