import math

import bpy

from .base import ShaderNodeBase


class FMwraptex(ShaderNodeBase):
    """Wrapping coordinates to range 0..1"""
    bl_idname = "fabricomatic.wraptex"
    bl_label = "wrapping uv"

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_output('NodeSocketVector', 'vector')

        xyz = self.add_xyz(('input', 'vector'))
        res = self.add_vec(
            self.add_math('SUBTRACT', (xyz, 'X'), self.add_math('FLOOR', (xyz, 'X'))),
            self.add_math('SUBTRACT', (xyz, 'Y'), self.add_math('FLOOR', (xyz, 'Y'))),
            (xyz, 'Z'))
        self.add_link(res, ('output', 'vector'))


class FMfloortex(ShaderNodeBase):
    """Flooring coordinates to integers"""
    bl_idname = "fabricomatic.floortex"
    bl_label = "flooring uv"

    def build_tree(self):
        self.add_input('NodeSocketVector', 'vector')
        self.add_output('NodeSocketVector', 'vector')

        xyz = self.add_xyz(('input', 'vector'))
        res = self.add_vec(
            self.add_math('FLOOR', (xyz, 'X')),
            self.add_math('FLOOR', (xyz, 'Y')),
            (xyz, 'Z'))
        self.add_link(res, ('output', 'vector'))


class FMmixvalues(ShaderNodeBase):
    """Mix values according to thread map

    Uses triple mixing with 0 values for black mask.
    Mask need not to be boolean.
    """
    bl_idname = "fabricomatic.mixvalues"
    bl_label = "mixing values"

    def init(self, context):
        super().init(context)

    def build_tree(self):
        self.add_input('NodeSocketColor', 'mask')
        self.add_input('NodeSocketFloat', 'value R')
        self.add_input('NodeSocketFloat', 'value G')
        self.add_input('NodeSocketColor', 'color R')
        self.add_input('NodeSocketColor', 'color G')

        self.add_output('NodeSocketFloat', 'value')
        self.add_output('NodeSocketColor', 'color')

        mask = self.add_rgb(('input', 'mask'))

        val = self.add_math(
            'ADD',
            self.add_math('MULTIPLY', ('input', 'value R'), (mask, 'R')),
            self.add_math('MULTIPLY', ('input', 'value G'), (mask, 'G')))

        col = self.add_mix(
            'ADD',
            self.add_mix('MIX', ('=', (0, 0, 0, 0)), ('input', 'color R'), fac=(mask, 'R')),
            self.add_mix('MIX', ('=', (0, 0, 0, 0)), ('input', 'color G'), fac=(mask, 'G')))

        self.add_link(val, ('output', 'value'))
        self.add_link(col, ('output', 'color'))


class FMmixfloats(ShaderNodeBase):
    """Mixing floats with factor"""
    bl_idname = "fabricomatic.mixfloats"
    bl_label = "mixing floats"

    def init(self, context):
        super().init(context)

    def build_tree(self):
        self.add_input('NodeSocketFloat', 'fac')
        self.add_input('NodeSocketFloat', 'value 1')
        self.add_input('NodeSocketFloat', 'value 2')
        self.add_output('NodeSocketFloat', 'value')
        val = self.add_math(
            'ADD',
            self.add_math(
                'MULTIPLY',
                self.add_math(
                    'SUBTRACT', 1.0, ('input', 'fac')),
                ('input', 'value 1')),
            self.add_math(
                'MULTIPLY',
                ('input', 'fac'),
                ('input', 'value 2')))
        self.add_link(val, ('output', 'value'))


class FMfmodulo(ShaderNodeBase):
    """Floored division modulo

    Outputs positive result for negative dividents.
    Tolerant to texture coords shifts.
    """
    bl_idname = "fabricomatic.fmodulo"
    bl_label = "fmodulo"

    def init(self, context):
        super().init(context)

    def build_tree(self):
        self.add_input('NodeSocketFloat', 'divident')
        self.add_input('NodeSocketFloat', 'divisor')
        self.add_output('NodeSocketFloat', 'remainder')

        val = self.add_math(
            'SUBTRACT',
            ('input', 'divident'),
            self.add_math(
                'MULTIPLY',
                self.add_math(
                    'FLOOR',
                    self.add_math(
                        'DIVIDE',
                        ('input', 'divident'),
                        ('input', 'divisor'))),
                ('input', 'divisor')))

        self.add_link(val, ('output', 'remainder'))


class FMzigzag(ShaderNodeBase):
    """Generating 1-dimentional zigzag.

    A triangle wave that looks like a very low-poly cosine.
    """
    # formula: abs((t/period + shift) fmod 1 - 0.5)

    bl_idname = "fabricomatic.zigzag"
    bl_label = "zigzag"

    def init(self, context):
        super().init(context)
        self.inputs['period'].default_value = 1.0
        self.inputs['min'].default_value = 0.0
        self.inputs['max'].default_value = 1.0

    def build_tree(self):
        self.add_input('NodeSocketFloat', 't')
        self.add_input('NodeSocketFloat', 'period')
        self.add_input('NodeSocketFloat', 'shift')
        self.add_input('NodeSocketFloat', 'min')
        self.add_input('NodeSocketFloat', 'max')

        self.add_output('NodeSocketFloat', 'value')

        arg = self.add_math(
            'ADD',
            self.add_math(
                'DIVIDE',
                ('input', 't'),
                ('input', 'period')),
            ('input', 'shift'))

        val = self.add_math(
            'ABSOLUTE',
            self.add_math(
                'SUBTRACT',
                self.add_math('SUBTRACT', arg, self.add_math('FLOOR', arg)),
                0.5))

        out = self.add_node(
            'ShaderNodeMapRange',
            inputs={
                0: val,
                1: -0.5,
                2: +0.5,
                3: ('input', 'min'),
                4: ('input', 'max')
                })

        self.add_link(out, ('output', 0))


class FMcosine(ShaderNodeBase):
    """Generating 1-dimentional cosine.

    Just a cosine with parameters.
    Use shift = 0.25 to make it sine.
    """

    bl_idname = "fabricomatic.cosine"
    bl_label = "cosine"

    def init(self, context):
        super().init(context)
        self.inputs['period'].default_value = 1.0
        self.inputs['min'].default_value = 0.0
        self.inputs['max'].default_value = 1.0

    def build_tree(self):
        self.add_input('NodeSocketFloat', 't')
        self.add_input('NodeSocketFloat', 'period')
        self.add_input('NodeSocketFloat', 'shift')
        self.add_input('NodeSocketFloat', 'min')
        self.add_input('NodeSocketFloat', 'max')

        self.add_output('NodeSocketFloat', 'value')

        val = self.add_math(
            'COSINE',
            self.add_math(
                'MULTIPLY',
                self.add_math(
                    'ADD',
                    self.add_math(
                        'DIVIDE',
                        ('input', 't'),
                        ('input', 'period')),
                    ('input', 'shift')),
                math.pi * 2)
            )
        out = self.add_node(
            'ShaderNodeMapRange',
            inputs={
                0: val,
                1: -1.0,
                2: +1.0,
                3: ('input', 'min'),
                4: ('input', 'max')
                })

        self.add_link(out, ('output', 0))


# class FMbezier(NodeTreeBuilder, bpy.types.ShaderNodeCustomGroup):
#     """Generating bezier easing"""
#     bl_idname = "fabricomatic.easing"
#     bl_label = "easing"
#
#     p1: bpy.props.FloatVectorProperty(name="p1", size=2,
#         description="control point 1",
#         update=lambda s,c: s.tweak_points())
#     p2: bpy.props.FloatVectorProperty(name="p2", size=2,
#         description="control point 2",
#         update=lambda s,c: s.tweak_points())

class FMcircle(ShaderNodeBase):
    """Maps range 0..2 to semicircle curve"""
    bl_idname = "fabricomatic.circle"
    bl_label = "circle"

    def init(self, context):
        super().init(context)

    def build_tree(self):
        self.add_input('NodeSocketFloat', 'value')
        self.add_output('NodeSocketFloat', 'value')

        val = self.add_math(
            'SQRT',
            self.add_math(
                'SUBTRACT',
                self.add_math(
                    'MULTIPLY',
                    ('input', 'value'),
                    2.0),
                self.add_math(
                    'POWER',
                    ('input', 'value'),
                    2.0)))

        self.add_link(val, ('output', 'value'))


class FMstripes(ShaderNodeBase):
    """Generatng periodic 1-dimentional stripes

    the stripes are placed in the middle of period.

    Inputs:
        t
            coordinate
        period
            period
        thickness
            ratio of stripe/period

    Outputs:
        strobe
            boolean, =1 where stripe is present
        profile
            triangle profile of stripe with 0.0 at edges and 1.0 at middle
    """

    # Formulas:
    #     val = zigzag(t, period) + w
    #     strobe = val > 0
    #     triangle = max(0, val/w)
    #     round = sqrt(triangle * 2 - triangle^2)

    bl_idname = "fabricomatic.stripes"
    bl_label = "stripes"

    def init(self, context):
        super().init(context)
        self.inputs['period'].default_value = 1.0
        self.inputs['thickness'].default_value = 0.5
        # self.tweak_profile()

    def build_tree(self):
        self.add_input('NodeSocketFloat', 't')
        self.add_input('NodeSocketFloat', 'period')
        self.add_input('NodeSocketFloat', 'thickness', min_value=0, max_value=1)

        self.add_output('NodeSocketFloat', 'strobe')
        self.add_output('NodeSocketFloat', 'profile')

        w = self.add_math('MULTIPLY', ('input', 'thickness'), 0.5)
        z = self.add_node(
            FMzigzag,
            inputs={
                't': ('input', 't'),
                'period': ('input', 'period'),
                'shift': 0.5,
                'min': -1.0,
                'max': 0.0,
            })
        val = self.add_math('ADD', z, w)

        strobe = self.add_math(
            'GREATER_THAN',
            val,
            0.0,
            name='strobe')

        triangle = self.add_math(
            'MAXIMUM',
            self.add_math(
                'DIVIDE',
                val,
                w),
            0.0,
            name='triangle')

        self.add_link(strobe, ('output', 'strobe'))
        self.add_link(triangle, ('output', 'profile'))
