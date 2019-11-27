""" Weaving module

The nodes in this module generate stripes of woven fabric.
Warp stripes go along V(Y) axis. Weft stripes go along U(X) axis.

Texture space is divided into cells with size 1.0 in each direction.
Generated stripes are placed in the middle of the cells, one stripe per cell.
If texture vector is unscaled, there will be just one cross in the texture.

Resulting values are encoded as colors/images
with R channel encoding value for weft and G channel encoding value for warp.
The values are not generally restricted to range 0..1 and any operations could be applied to them via `MixRGB` node.

When applying bump, each stripe has kinda semicircular profile.

The three weaving nodes (plain, twill, jacquard) generate elevation waves in range -1.0 .. +1.0
with -1.0 indicating back side and +1.0 face side. The generated waves are cell-wide and independant from stobing.
The range should be kept for `overlaying` node to work.

"""
import bpy

from .base import ShaderNodeBase
from .utils import FMmixfloats, FMfmodulo, FMcosine, FMcircle, FMstripes


class FMWeaveScaling(ShaderNodeBase):
    """Scale UV space

    This is just a compact version of `Mapping`.

    Options:
        balanced
            Use the same density for warp and weft scaling.

    Inputs:
        density
            Number of stripes per original texture unit.

    Outputs:
        vector
            Scaled vector.
        scale
            Resulting size of fabric cells (relative to original texture unit).
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
        self.inputs['density'].default_value = 100
        self.inputs['warp density'].default_value = 100
        self.inputs['weft density'].default_value = 100
        self.tweak_balance()

    def copy(self, node):
        super().copy(node)
        self.balanced = node.balanced

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_input('NodeSocketFloat', 'density', min_value=0.0)
        self.add_input('NodeSocketFloat', 'warp density', min_value=0.0)
        self.add_input('NodeSocketFloat', 'weft density', min_value=0.0)

        self.add_output('NodeSocketVector', 'vector')
        self.add_output('NodeSocketColor', 'scale')

        # rerouted from tweak_balanced
        d_wrp = self.add_node('NodeReroute', name='d_wrp')
        d_wft = self.add_node('NodeReroute', name='d_wft')

        xyz = self.add_xyz(('input', 'vector'))

        x_wrp = self.add_math('MULTIPLY', (xyz, 'X'), d_wrp)
        y_wft = self.add_math('MULTIPLY', (xyz, 'Y'), d_wft)

        vector = self.add_vec(x_wrp, y_wft)
        scale = self.add_col(
            self.add_math('DIVIDE', 1.0, d_wft),
            self.add_math('DIVIDE', 1.0, d_wrp),
        )

        self.add_link(vector, ('output', 'vector'))
        self.add_link(scale, ('output', 'scale'))

    def tweak_balance(self):
        self.inputs['density'].enabled = self.balanced
        self.inputs['warp density'].enabled = not self.balanced
        self.inputs['weft density'].enabled = not self.balanced
        if self.balanced:
            self.add_link(('input', 'density'), 'd_wrp')
            self.add_link(('input', 'density'), 'd_wft')
        else:
            self.add_link(('input', 'warp density'), 'd_wrp')
            self.add_link(('input', 'weft density'), 'd_wft')

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')


class FMWeaveStrobingMixin(ShaderNodeBase):
    def add_striping(self, xyz, w_wrp, w_wft):
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
            (stripes_wrp, 'profile'))

        mask = self.add_node('ShaderNodeSeparateHSV', inputs={0: strobes})

        self.add_link(strobes, ('output', 'strobes'))
        self.add_link(profiles, ('output', 'profiles'))
        self.add_link((mask, 'V'), ('output', 'alpha'))

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'balanced')


class FMWeaveStrobing(FMWeaveStrobingMixin, ShaderNodeBase):
    """Generating periodic stripes for warp and weft

    The stripes are placed in the middle of each texture cell.

    The profile is triangle with value 0.0 at stripe edges and 1.0 in the middle.
    It could be shaped with curves or `profiling` node.

    Options:
        balanced
            Use the same thickness for warp and weft scaling
        soft alpha
            Generate smooth alpha mask instead of binary

    Inputs:
        vector
            UV vector (pre scaled according to desired density)
        thickness
            Relative width of stripes (ratio of yarn to holes, with 1 = cover full area)

    Outputs:
        strobes
            Boolean mask indicating presence of warp or weft
        alpha
            Overall transparency, either binary or smooth
        profiles
            Triangle-shaped bump elevation of each stripe.
    """
    bl_idname = "fabricomatic.weave_strobing"
    bl_label = "weave strobing"

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

        self.add_striping(xyz, w_wrp, w_wft)

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


class FMWeaveStrobingBulged(FMWeaveStrobingMixin, ShaderNodeBase):
    """Generating stripes with increased width on face side

    The same as `weave strobing`, but with variable width according to provided elevation.

    Inputs:
        vector
            UV vector (pre scaled according to desired density)
        waves
            Map of stripes elevation (from some `weaving` node)
        min thickness
            Minimal thickness/width, as on back side
        max thickness
            Maximal thickness/width, as on top of front side
    """

    bl_idname = "fabricomatic.weave_strobing_bulged"
    bl_label = "weave bulged strobing"

    volatile = True

    balanced: bpy.props.BoolProperty(
        name="Balanced",
        description="Equal paramewters for warp and weft",
        default=True,
        update=lambda s, c: s.tweak_balance())

    def init(self, context):
        super().init(context)
        self.inputs['min thickness'].default_value = 0.5
        self.inputs['max thickness'].default_value = 0.75
        self.inputs['min warp thickness'].default_value = 0.5
        self.inputs['max warp thickness'].default_value = 0.75
        self.inputs['min weft thickness'].default_value = 0.5
        self.inputs['max weft thickness'].default_value = 0.75
        self.tweak_balance()

    def copy(self, node):
        super().copy(node)
        self.balanced = node.balanced

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_input('NodeSocketColor', 'waves')

        self.add_input('NodeSocketFloat', 'min thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'max thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'min warp thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'max warp thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'min weft thickness', min_value=0, max_value=1.0)
        self.add_input('NodeSocketFloat', 'max weft thickness', min_value=0, max_value=1.0)

        self.add_output('NodeSocketColor', 'strobes')
        self.add_output('NodeSocketColor', 'profiles')
        self.add_output('NodeSocketFloat', 'alpha')

        # rerouted from tweak_balanced
        min_wrp = self.add_node('NodeReroute', name='min_wrp')
        min_wft = self.add_node('NodeReroute', name='min_wft')
        max_wrp = self.add_node('NodeReroute', name='max_wrp')
        max_wft = self.add_node('NodeReroute', name='max_wft')

        factor = self.add_mix(
            'MULTIPLY',
            ('=', (0.5, 0.5, 0.0, 0.0)),
            self.add_mix(
                'ADD',
                ('=', (1.0, 1.0, 0.0, 0.0)),
                ('input', 'waves')))

        factor_rgb = self.add_rgb(factor)

        w_wrp = self.add_node(
            'ShaderNodeMapRange',
            inputs={
                'Value': (factor_rgb, 'G'),
                'To Min': min_wrp,
                'To Max': max_wrp
            })

        w_wft = self.add_node(
            'ShaderNodeMapRange',
            inputs={
                'Value': (factor_rgb, 'R'),
                'To Min': min_wft,
                'To Max': max_wft
            })

        xyz = self.add_xyz(('input', 'vector'))

        self.add_striping(xyz, w_wrp, w_wft)

    def tweak_balance(self):
        self.inputs['min thickness'].enabled = self.balanced
        self.inputs['max thickness'].enabled = self.balanced
        self.inputs['min warp thickness'].enabled = not self.balanced
        self.inputs['max warp thickness'].enabled = not self.balanced
        self.inputs['min weft thickness'].enabled = not self.balanced
        self.inputs['max weft thickness'].enabled = not self.balanced
        if self.balanced:
            self.add_link(('input', 'min thickness'), 'min_wrp')
            self.add_link(('input', 'min thickness'), 'min_wft')
            self.add_link(('input', 'max thickness'), 'max_wrp')
            self.add_link(('input', 'max thickness'), 'max_wft')
        else:
            self.add_link(('input', 'min warp thickness'), 'min_wrp')
            self.add_link(('input', 'min weft thickness'), 'min_wft')
            self.add_link(('input', 'max warp thickness'), 'max_wrp')
            self.add_link(('input', 'max weft thickness'), 'max_wft')


class FMWeaveProfiling(ShaderNodeBase):
    """Converting triangle profile to decent shape.

    Simply maps values 0..1 to some predefined curve.
    """
    bl_idname = "fabricomatic.weave_profiling"
    bl_label = "weave profiling"

    volatile = True

    PROFILE_SHAPES = (
        ('FLAT', 'Flat', "Flatten", 0),
        ('ROUND', 'Round', "Semicircular profile", 1),
        ('SINE', 'Sine', "Sine profile (full period)", 3),
        ('HSINE', 'Halfsine', "Sine profile (half period)", 4),
    )

    profile_shape: bpy.props.EnumProperty(
        name="Profle shape",
        items=PROFILE_SHAPES,
        update=lambda s, c: s.tweak_profile(),
        default='ROUND')

    def init(self, context):
        super().init(context)
        self.tweak_profile()

    def copy(self, node):
        super().copy(node)
        self.profile_shape = node.profile_shape

    def build_tree(self):
        self.add_input('NodeSocketColor', 'profiles')
        self.add_output('NodeSocketColor', 'profiles')

        profiles_rgb = self.add_rgb(('input', 'profiles'))

        self.add_col(
            self.add_math('GREATER_THAN', (profiles_rgb, 'R'), 0.0),
            self.add_math('GREATER_THAN', (profiles_rgb, 'G'), 0.0),
            name='flat')

        self.add_col(
            self.add_node(FMcircle, inputs={'value': (profiles_rgb, 'R')}),
            self.add_node(FMcircle, inputs={'value': (profiles_rgb, 'G')}),
            name='round')

        self.add_col(
            self.add_node(FMcosine, inputs={'t': (profiles_rgb, 'R'), 'period': 2.0, 'shift': -0.5}),
            self.add_node(FMcosine, inputs={'t': (profiles_rgb, 'G'), 'period': 2.0, 'shift': -0.5}),
            name='sine')

        self.add_col(
            self.add_node(FMcosine, inputs={'t': (profiles_rgb, 'R'), 'period': 4.0, 'shift': -0.25}),
            self.add_node(FMcosine, inputs={'t': (profiles_rgb, 'G'), 'period': 4.0, 'shift': -0.25}),
            name='hsine')

        self.add_link(('input', 'profiles'), ('output', 'profiles'))

    def tweak_profile(self):
        if self.profile_shape == 'ROUND':
            self.add_link('round', ('output', 'profiles'))
        elif self.profile_shape == 'SINE':
            self.add_link('sine', ('output', 'profiles'))
        elif self.profile_shape == 'HSINE':
            self.add_link('hsine', ('output', 'profiles'))
        elif self.profile_shape == 'FLAT':
            self.add_link('flat', ('output', 'profiles'))
        else:
            self.add_link(('input', 'profiles'), ('output', 'profiles'))

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'profile_shape', text="")


class FMWeaveOverlaying(ShaderNodeBase):
    """Adjusting and combining maps

    The elevation is scaled according to provided thickness and adjusted,
    so that stripes lay on top of each other.

    Stiffness makes corresponding stripes more straight and less waving.

    Options:
        balanced
            Use the same thickness for warp and weft scaling
        stifness
            Apply stiffness
        soft mask
            Generate soft mask with overlapping stripes

    Inputs:
        vector
            UV vector (pre scaled according to desired density)
        thickness
            Relative height of stripes and waves
        stiffness
            Stifness (1.0 = no waving)

    Outputs:
        evalation
            Combined elevation separately for each channel
        mask
            Map indicating which kind of stripe is on top
        height
            Resulting elevation
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

    # softmask: bpy.props.BoolProperty(
    #     name="Soft mask",
    #     description="Make mask smooth",
    #     default=True,
    #     update=lambda s, c: s.tweak_softness())
    #
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
        self.add_input('NodeSocketColor', 'strobes')
        self.add_input('NodeSocketColor', 'profiles')
        self.add_input('NodeSocketColor', 'waves')

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

        height_rgb = self.add_rgb(height)
        height_hsv = self.add_node('ShaderNodeSeparateHSV', inputs={0: height}, name='height_hsv')

        mask = self.add_col(
            self.add_math('GREATER_THAN', (height_rgb, 'R'), (height_rgb, 'G')),
            self.add_math('GREATER_THAN', (height_rgb, 'G'), (height_rgb, 'R')),
            name='mask')

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


class FMWeaveBumping(ShaderNodeBase):
    """Generating bump/displacement map

    Inputs:
        scale
            Factor to scale each channel individually
        elevation
            Map of combined elevation for each channel
        mask
            Map of yarn
        normal
            Initial normal
        strength
            A parameter for bump
        midlevel
            A parameter for displacement

    Outputs:
        normal
            Bump mapped to plug into 'normal' of BSDFs
        displacement
            Vector displacement to plug into material output

    """
    bl_idname = "fabricomatic.weave_bumping"
    bl_label = "weave bumping"

    volatile = True

    STAMP_MODES = (
        ('BUMP', 'Bump', "", 1),
        ('DISPL', 'Displacement', "", 2),
    )

    stamp_mode: bpy.props.EnumProperty(
        name="Bumping mode",
        items=STAMP_MODES,
        update=lambda s, c: s.tweak_stamping(),
        default='BUMP')

    def init(self, context):
        super().init(context)
        self.inputs['strength'].default_value = 1.0
        self.tweak_stamping()

    def copy(self, node):
        super().copy(node)
        self.stamp_mode = node.stamp_mode

    def build_tree(self):
        self.add_input('NodeSocketColor', 'scale')
        self.add_input('NodeSocketColor', 'elevation')
        self.add_input('NodeSocketColor', 'mask')

        self.add_input('NodeSocketVector', 'normal')
        self.add_input('NodeSocketFloat', 'strength')
        self.add_input('NodeSocketFloat', 'midlevel')

        self.add_output('NodeSocketVector', 'displacement')
        self.add_output('NodeSocketVector', 'normal')

        height = self.add_mix(
            'MULTIPLY',
            ('input', 'mask'),
            self.add_mix(
                'MULTIPLY',
                ('input', 'elevation'),
                ('input', 'scale')))
        height_hsv = self.add_node('ShaderNodeSeparateHSV', inputs={0: height})

        self.add_node(
            'ShaderNodeDisplacement',
            inputs={
                'Height': (height_hsv, 'V'),
                'Normal': ('input', 'normal'),
                'Midlevel': ('input', 'midlevel')
            },
            name='displacing')

        self.add_node(
            'ShaderNodeBump',
            inputs={
                'Height': (height_hsv, 'V'),
                'Normal': ('input', 'normal'),
                'Distance': 1.0,
                'Strength': ('input', 'strength'),
            },
            name='bumping')

    def tweak_stamping(self):
        self.outputs['normal'].enabled = False
        self.outputs['displacement'].enabled = False
        self.inputs['strength'].enabled = False
        self.inputs['midlevel'].enabled = False
        if self.stamp_mode == 'BUMP':
            self.inputs['strength'].enabled = True
            self.outputs['normal'].enabled = True
            self.add_link('bumping', ('output', 'normal'))
        elif self.stamp_mode == 'DISPL':
            self.inputs['midlevel'].enabled = True
            self.outputs['displacement'].enabled = True
            self.add_link('displacing', ('output', 'displacement'))

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'stamp_mode')


class FMWeavePatternSampling(ShaderNodeBase):
    """Generating coordinates for pattern sampling.

    Coordinates are scaled and rounded, so that each pixel of pattern corresponds to a cell of weaving.

    Inputs:
        vector
            original vector, assuming all pattern fit range 0..1
        width
            width of image in pixels
        height
            height of image in pixels

    Outputs:
        Vectors shifted and snapped.

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
    """Interpolating sampled pattern

    Produces wave-map from values sampled from pattern.
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
            pre-scaled vector

    Outputs:
        waves
            map of stripe elevation, in range -1.0..+1.0

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

    Generating interlacing according to twill scheme.

    Inputs:
        vector
            pre-scaled vector
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

        spread = self.add_node(
            FMWeavePatternSampling,
            inputs={
                'vector': ('input', 'vector'),
                'width': 1,
                'height': 1,
                })

        period = self.add_math('ADD', ('input', 'above'), ('input', 'below'))

        y_0_s = self.add_math('MULTIPLY', (spread, 'y_0'), ('input', 'shift'))
        y_d_s = self.add_math('MULTIPLY', (spread, 'y_d'), ('input', 'shift'))
        y_u_s = self.add_math('MULTIPLY', (spread, 'y_u'), ('input', 'shift'))

        val_l = self.add_math(
            'LESS_THAN',
            self.add_node(
                FMfmodulo,
                inputs={
                    'divisor': period,
                    'divident': self.add_math('SUBTRACT', (spread, 'x_l'), y_0_s)
                    }),
            ('input', 'above'))
        val_r = self.add_math(
            'LESS_THAN',
            self.add_node(
                FMfmodulo,
                inputs={
                    'divisor': period,
                    'divident': self.add_math('SUBTRACT', (spread, 'x_r'), y_0_s)
                    }),
            ('input', 'above'))
        val_d = self.add_math(
            'LESS_THAN',
            self.add_node(
                FMfmodulo,
                inputs={
                    'divisor': period,
                    'divident': self.add_math('SUBTRACT', (spread, 'x_0'), y_d_s)
                    }),
            ('input', 'above'))
        val_u = self.add_math(
            'LESS_THAN',
            self.add_node(
                FMfmodulo,
                inputs={
                    'divisor': period,
                    'divident': self.add_math('SUBTRACT', (spread, 'x_0'), y_u_s)
                    }),
            ('input', 'above'))

        interp = self.add_node(
            FMWeavePatternInterpolating,
            inputs={
                'vector': ('input', 'vector'),
                'v_l': val_l,
                'v_r': val_r,
                'v_u': val_u,
                'v_d': val_d,
                })

        self.add_link(interp, ('output', 'waves'))


class FMWeavingJacquard(ShaderNodeBase):
    """Jacquard weaving.

    Generating interlacing according to given pattern image, corrssponding to "weaving draft" in weaving reality.
    White pixels indicate weft-facing cells, black pixels indicate warp-facing cells.

    Paramaters:
        pattern
            an black-n-white image specifying weaving pattern

    Inputs:
        vector
            pre-scaled vector

    Outputs:
        waves
            map of stripe elevation, in range -1.0..+1.0

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
            inputs={'Vector': self.add_vec((sampling, 'x_l'), (sampling, 'y_0'))})
        tex_r = self.add_node(
            'ShaderNodeTexImage',
            name='tex_r',
            interpolation='Closest',
            inputs={'Vector': self.add_vec((sampling, 'x_r'), (sampling, 'y_0'))})
        tex_d = self.add_node(
            'ShaderNodeTexImage',
            name='tex_d',
            interpolation='Closest',
            inputs={'Vector': self.add_vec((sampling, 'x_0'), (sampling, 'y_d'))})
        tex_u = self.add_node(
            'ShaderNodeTexImage',
            name='tex_u',
            interpolation='Closest',
            inputs={'Vector': self.add_vec((sampling, 'x_0'), (sampling, 'y_u'))})

        interp = self.add_node(
            FMWeavePatternInterpolating,
            inputs={
                'vector': ('input', 'vector'),
                'v_l': tex_l,
                'v_r': tex_r,
                'v_d': tex_d,
                'v_u': tex_u,
                })

        self.add_link(interp, ('output', 'waves'))

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
