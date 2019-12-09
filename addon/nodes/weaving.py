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

from .base import ShaderNodeBase
from .utils import FMmixfloats, FMfmodulo, FMcosine, FMstripes, FMWeaveProfiling


class FMWeaveScaling(ShaderNodeBase):
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

    volatile = True

    balanced: bpy.props.BoolProperty(
        name="Balanced",
        description="Equal paramewters for warp and weft",
        default=True,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.inputs['threads count'].default_value = 200
        self.inputs['warp count'].default_value = 200
        self.inputs['weft count'].default_value = 200
        self.tweak_balance()

    def copy(self, node):
        super().copy(node)
        self.balanced = node.balanced

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_input('NodeSocketFloat', 'threads count', min_value=0.0)
        self.add_input('NodeSocketFloat', 'warp count', min_value=0.0)
        self.add_input('NodeSocketFloat', 'weft count', min_value=0.0)

        self.add_output('NodeSocketVector', 'vector')
        self.add_output('NodeSocketVector', 'scale')
        self.add_output('NodeSocketVector', 'snapped')

        # x = warp count, y = weft count
        # rerouted in tweak_balance
        freq = self.add_vec(0.0, 0.0, name='freq')

        vector = self.add_vmath('MULTIPLY', ('input', 'vector'), freq)
        scale = self.add_vmath('DIVIDE', ('=', (1.0, 1.0, 1.0)), freq)
        snapped = self.add_vmath('SNAP', ('input', 'vector'), scale)
        self.add_link(vector, ('output', 'vector'))
        self.add_link(scale, ('output', 'scale'))
        self.add_link(snapped, ('output', 'snapped'))

    def tweak_balance(self):
        self.inputs['threads count'].enabled = self.balanced
        self.inputs['warp count'].enabled = not self.balanced
        self.inputs['weft count'].enabled = not self.balanced
        if self.balanced:
            self.add_link(('input', 'threads count'), ('freq', 'X'))
            self.add_link(('input', 'threads count'), ('freq', 'Y'))
        else:
            self.add_link(('input', 'warp count'), ('freq', 'X'))
            self.add_link(('input', 'weft count'), ('freq', 'Y'))

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')


class FMWeaveStrobing(ShaderNodeBase):
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

    volatile = True

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
        self.inputs['thickness'].default_value = 0.5
        self.inputs['warp thickness'].default_value = 0.5
        self.inputs['weft thickness'].default_value = 0.5
        self.tweak_balance()

    def copy(self, node):
        super().copy(node)
        self.balanced = node.balanced

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_input('NodeSocketFloat', 'thickness', min_value=0.0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'warp thickness', min_value=0.0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'weft thickness', min_value=0.0, max_value=1.0)

        self.add_output('NodeSocketColor', 'strobes')
        self.add_output('NodeSocketColor', 'profiles')
        self.add_output('NodeSocketFloat', 'alpha')

        xyz = self.add_xyz(('input', 'vector'))

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

        self.add_link(strobes, ('output', 'strobes'))
        self.add_link(profiling, ('output', 'profiles'))
        self.add_link((mask, 'V'), ('output', 'alpha'))

    def tweak_balance(self):
        self.inputs['thickness'].enabled = self.balanced
        self.inputs['warp thickness'].enabled = not self.balanced
        self.inputs['weft thickness'].enabled = not self.balanced
        if self.balanced:
            self.add_link(('input', 'thickness'), 'th_wrp')
            self.add_link(('input', 'thickness'), 'th_wft')
        else:
            self.add_link(('input', 'warp thickness'), 'th_wrp')
            self.add_link(('input', 'weft thickness'), 'th_wft')

    def tweak_profile(self):
        if self.profile_shape == 'NONE':
            self.add_link('profiles', ('output', 'profiles'))
        else:
            self.add_link('profiling', ('output', 'profiles'))
            self.get_node('profiling').profile_shape = self.profile_shape

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')
        layout.prop(self, 'profile_shape')


class FMWeaveBulging(ShaderNodeBase):
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

    volatile = True

    balanced: bpy.props.BoolProperty(
        name="Balanced",
        description="Equal paramewters for warp and weft",
        default=True,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.inputs['thickness'].default_value = 0.5
        self.inputs['warp thickness'].default_value = 0.5
        self.inputs['weft thickness'].default_value = 0.5
        self.inputs['shrinking'].default_value = 0.5
        self.inputs['warp shrinking'].default_value = 0.5
        self.inputs['weft shrinking'].default_value = 0.5
        self.tweak_balance()

    def copy(self, node):
        super().copy(node)
        self.balanced = node.balanced

    def build_tree(self):
        self.add_input('NodeSocketColor', 'waves')

        self.add_input('NodeSocketFloat', 'thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'warp thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'weft thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'shrinking', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'warp shrinking', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'weft shrinking', min_value=0, max_value=1.0)

        self.add_output('NodeSocketFloat', 'warp thickness')
        self.add_output('NodeSocketFloat', 'weft thickness')

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
                ('input', 'waves')))

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

        self.add_link(th_wrp, ('output', 'warp thickness'))
        self.add_link(th_wft, ('output', 'weft thickness'))

    def tweak_balance(self):
        self.inputs['thickness'].enabled = self.balanced
        self.inputs['shrinking'].enabled = self.balanced
        self.inputs['warp thickness'].enabled = not self.balanced
        self.inputs['warp shrinking'].enabled = not self.balanced
        self.inputs['weft thickness'].enabled = not self.balanced
        self.inputs['weft shrinking'].enabled = not self.balanced
        if self.balanced:
            self.add_link(('input', 'thickness'), 'max_wrp')
            self.add_link(('input', 'thickness'), 'max_wft')
            self.add_link(('input', 'shrinking'), 'fac_wrp')
            self.add_link(('input', 'shrinking'), 'fac_wft')
        else:
            self.add_link(('input', 'warp thickness'), 'max_wrp')
            self.add_link(('input', 'weft thickness'), 'max_wft')
            self.add_link(('input', 'warp shrinking'), 'fac_wrp')
            self.add_link(('input', 'weft shrinking'), 'fac_wft')

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')


class FMWeaveOverlaying(ShaderNodeBase):
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

    volatile = True

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
        self.inputs['thickness'].default_value = 0.5
        self.inputs['warp thickness'].default_value = 0.5
        self.inputs['weft thickness'].default_value = 0.5
        self.inputs['warp stiffness'].default_value = 0
        self.inputs['weft stiffness'].default_value = 0
        self.tweak_balance()
        self.tweak_stiffnessful()

    def copy(self, node):
        super().copy(node)
        self.balanced = node.balanced
        self.stiffnessful = node.stiffnessful

    def build_tree(self):
        self.add_input('NodeSocketColor', 'waves')
        self.add_input('NodeSocketColor', 'strobes')
        self.add_input('NodeSocketColor', 'profiles')

        self.add_input('NodeSocketFloat', 'thickness', min_value=0.0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'warp thickness', min_value=0.0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'weft thickness', min_value=0.0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'warp stiffness', min_value=0.0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'weft stiffness', min_value=0.0, max_value=1.0)

        self.add_output('NodeSocketColor', 'elevation')
        self.add_output('NodeSocketColor', 'mask')
        self.add_output('NodeSocketFloat', 'height')

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
                ('input', 'warp stiffness'),
                h_wft))
        s_wft = self.add_math(
            'MULTIPLY',
            0.5,
            self.add_math(
                'MULTIPLY',
                ('input', 'weft stiffness'),
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
                ('input', 'waves'),
                ampl))

        profiles = self.add_mix(
            'MULTIPLY',
            ('input', 'profiles'),
            thick)

        height = self.add_mix(
            'ADD',
            self.add_mix('MULTIPLY', waves, ('input', 'strobes')),
            profiles,
            name='height')

        mask = self.add_node(FMWeaveMasking, inputs={0: height})
        height_hsv = self.add_node('ShaderNodeSeparateHSV', inputs={0: height}, name='height_hsv')

        self.add_link(mask, ('output', 'mask'))
        self.add_link(height, ('output', 'elevation'))
        self.add_link((height_hsv, 'V'), ('output', 'height'))

    def tweak_balance(self):
        if self.balanced:
            self.inputs['thickness'].enabled = True
            self.inputs['warp thickness'].enabled = False
            self.inputs['weft thickness'].enabled = False
            self.add_link(('input', 'thickness'), 'th_wrp')
            self.add_link(('input', 'thickness'), 'th_wft')
        else:
            self.inputs['thickness'].enabled = False
            self.inputs['warp thickness'].enabled = True
            self.inputs['weft thickness'].enabled = True
            self.add_link(('input', 'warp thickness'), 'th_wrp')
            self.add_link(('input', 'weft thickness'), 'th_wft')

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
    #         self.add_link('height', ('output', 'mask'))
    #     else:
    #         self.add_link('mask', ('output', 'mask'))

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')
        layout.prop(self, 'stiffnessful')
        # layout.prop(self, 'softmask')


class FMWeaveMasking(ShaderNodeBase):
    """Creating thread mask from their elevations"""
    bl_idname = "fabricomatic.weave_masking"
    bl_label = "weave masking"

    def build_tree(self):
        self.add_input('NodeSocketColor', 'elevation')
        self.add_output('NodeSocketColor', 'mask')

        height_rgb = self.add_rgb(('input', 'elevation'))
        mask = self.add_col(
            self.add_math('GREATER_THAN', (height_rgb, 'R'), (height_rgb, 'G')),
            self.add_math('GREATER_THAN', (height_rgb, 'G'), (height_rgb, 'R')),
            name='mask')
        self.add_link(mask, ('output', 'mask'))


class FMWeavePatternSampling(ShaderNodeBase):
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

    def init(self, context):
        super().init(context)
        self.inputs['width'].default_value = 16
        self.inputs['height'].default_value = 16

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_input('NodeSocketInt', 'width')
        self.add_input('NodeSocketInt', 'height')

        self.add_output('NodeSocketVector', 'vector 0')
        self.add_output('NodeSocketVector', 'vector l')
        self.add_output('NodeSocketVector', 'vector r')
        self.add_output('NodeSocketVector', 'vector d')
        self.add_output('NodeSocketVector', 'vector u')

        scale = self.add_vmath(
            'DIVIDE',
            ('=', (1.0, 1.0, 1.0)),
            self.add_vec(('input', 'width'), ('input', 'height')))

        vec_0 = self.add_vmath(
            'SNAP',
            self.add_vmath(
                'MULTIPLY',
                ('input', 'vector'),
                scale),
            scale)

        def scalesnap(shift):
            return self.add_vmath(
                'SNAP',
                self.add_vmath(
                    'MULTIPLY',
                    self.add_vmath(
                        'ADD',
                        ('input', 'vector'),
                        ('=', shift)),
                    scale),
                scale)

        vec_l = scalesnap((-0.5, 0.0, 0.0))
        vec_r = scalesnap((+0.5, 0.0, 0.0))
        vec_d = scalesnap((0.0, -0.5, 0.0))
        vec_u = scalesnap((0.0, +0.5, 0.0))

        self.add_link(vec_0, ('output', 'vector 0'))
        self.add_link(vec_l, ('output', 'vector l'))
        self.add_link(vec_r, ('output', 'vector r'))
        self.add_link(vec_d, ('output', 'vector d'))
        self.add_link(vec_u, ('output', 'vector u'))


class FMWeavePatternInterpolating(ShaderNodeBase):
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

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_input('NodeSocketFloat', 'value l')
        self.add_input('NodeSocketFloat', 'value r')
        self.add_input('NodeSocketFloat', 'value d')
        self.add_input('NodeSocketFloat', 'value u')

        self.add_output('NodeSocketColor', 'waves')

        xyz = self.add_xyz(
            self.add_vmath(
                'FRACTION',
                self.add_vmath(
                    'ADD',
                    ('input', 'vector'),
                    ('=', (-0.5, -0.5, 0.0)))))

        weft = self.add_node(
            FMcosine,
            inputs={
                't': self.add_node(
                    FMmixfloats,
                    inputs={
                        'fac': (xyz, 'X'),
                        'value 1': ('input', 'value l'),
                        'value 2': ('input', 'value r'),
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
                        'value 1': ('input', 'value d'),
                        'value 2': ('input', 'value u'),
                    }),
                'period': 2.0,
                'shift': 0,
                'min': -1.0,
                'max': +1.0,
            })

        out = self.add_col(weft, warp)

        self.add_link(out, ('output', 'waves'))


class FMWeavingPlain(ShaderNodeBase):
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

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_output('NodeSocketColor', 'waves')

        xyz = self.add_xyz(('input', 'vector'))

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

        self.add_link(out, ('output', 'waves'))


class FMWeavingTwill(ShaderNodeBase):
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

    def init(self, context):
        super().init(context)
        self.inputs['above'].default_value = 2
        self.inputs['below'].default_value = 2
        self.inputs['shift'].default_value = 1

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_input('NodeSocketInt', 'above', min_value=1)
        self.add_input('NodeSocketInt', 'below', min_value=1)
        self.add_input('NodeSocketInt', 'shift')

        self.add_output('NodeSocketColor', 'waves')

        # ('math', 'ADD', x, y)
        period = self.add_math('ADD', ('input', 'above'), ('input', 'below'))

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
                                    ('input', 'shift'))),
                        'divisor': period
                    }),
                ('input', 'above'))

        def snap(*shift):
            return self.add_vmath(
                'SNAP',
                self.add_vmath('ADD', ('input', 'vector'), ('=', shift)),
                ('=', (1.0, 1.0, 1.0)))

        waves = self.add_node(
            FMWeavePatternInterpolating,
            inputs={
                'vector': ('input', 'vector'),
                'value l': twill(snap(-0.5, 0.0, 0.0)),
                'value r': twill(snap(+0.5, 0.0, 0.0)),
                'value d': twill(snap(0.0, -0.5, 0.0)),
                'value u': twill(snap(0.0, +0.5, 0.0)),
                })

        self.add_link(waves, ('output', 'waves'))


class FMWeavingJacquard(ShaderNodeBase):
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

    volatile = True

    pattern: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Pattern",
        update=lambda s, c: s.update_pattern())

    def init(self, context):
        super().init(context)
        self.pattern = bpy.data.images.new("weaving draft", 16, 16, is_data=True)

    def copy(self, node):
        super().copy(node)
        self.pattern = node.pattern

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_output('NodeSocketColor', 'waves')

        sampling = self.add_node(
            FMWeavePatternSampling,
            name='sampling',
            inputs={
                'vector': ('input', 'vector'),
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
                'vector': ('input', 'vector'),
                'value l': tex_l,
                'value r': tex_r,
                'value d': tex_d,
                'value u': tex_u,
                })

        self.add_link(waves, ('output', 'waves'))

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
