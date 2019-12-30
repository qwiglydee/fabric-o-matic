"""
Various utility nodes
"""
import math

import bpy

from .base import ShaderSharedNodeBase, ShaderVolatileNodeBase


class FMmixvalues(ShaderSharedNodeBase):
    """Mix values according to thread map

    Outputs value or color corresponding to value of thread map

    Inputs:
        - mask
            R/G mask of threads
        - value R/G
            scalar value
        - color R/G
            color

    Outputs:
        - value
        - color
    """
    bl_idname = "fabricomatic.mixvalues"
    bl_label = "mixing values"

    inp_sockets = (
        ('NodeSocketColor', 'mask', (0.5, 0.5, 0.0, 1.0)),
        ('NodeSocketFloat', 'warp value'),
        ('NodeSocketFloat', 'weft value'),
        ('NodeSocketColor', 'warp color'),
        ('NodeSocketColor', 'weft color'),
    )
    out_sockets = (
        ('NodeSocketFloat', 'value'),
        ('NodeSocketColor', 'color'),
    )

    def build_tree(self):
        mask = self.rgb((self.inp, 'mask'))

        val = self.math(
            'ADD',
            self.math('MULTIPLY', (self.inp, 'weft value'), (mask, 'R')),
            self.math('MULTIPLY', (self.inp, 'warp value'), (mask, 'G')))

        col = self.mix(
            'ADD',
            self.mix('MIX', ('=', (0, 0, 0, 0)), (self.inp, 'weft color'), fac=(mask, 'R')),
            self.mix('MIX', ('=', (0, 0, 0, 0)), (self.inp, 'warp color'), fac=(mask, 'G')))

        self.link(val, (self.out, 'value'))
        self.link(col, (self.out, 'color'))


class FMmixfloats(ShaderSharedNodeBase):
    """Mixing floats with factor

    Very dumb node.
    Analogous to MapRange(value=fac, to_min = value1, to_max=value2)
    """
    bl_idname = "fabricomatic.mixfloats"
    bl_label = "mixing floats"

    inp_sockets = (
        ('NodeSocketFloat', 'fac', 0.5),
        ('NodeSocketFloat', 'value 1'),
        ('NodeSocketFloat', 'value 2'),
    )
    out_sockets = (
        ('NodeSocketFloat', 'value'),
    )

    def build_tree(self):
        val = self.math(
            'ADD',
            self.math(
                'MULTIPLY',
                self.math(
                    'SUBTRACT', 1.0, (self.inp, 'fac')),
                (self.inp, 'value 1')),
            self.math(
                'MULTIPLY',
                (self.inp, 'fac'),
                (self.inp, 'value 2')))
        self.link(val, (self.out, 'value'))


class FMfmodulo(ShaderSharedNodeBase):
    """Floored division modulo

    Outputs positive result for negative dividents.
    Tolerant to texture coords shifts.
    """
    bl_idname = "fabricomatic.fmodulo"
    bl_label = "fmodulo"

    inp_sockets = (
        ('NodeSocketFloat', 'divident'),
        ('NodeSocketFloat', 'divisor', 1.0),
    )
    out_sockets = (
        ('NodeSocketFloat', 'remainder'),
    )

    def build_tree(self):
        val = self.math(
            'SUBTRACT',
            (self.inp, 'divident'),
            self.math(
                'MULTIPLY',
                self.math(
                    'FLOOR',
                    self.math(
                        'DIVIDE',
                        (self.inp, 'divident'),
                        (self.inp, 'divisor'))),
                (self.inp, 'divisor')))

        self.link(val, (self.out, 'remainder'))


class FMzigzag(ShaderSharedNodeBase):
    """Generating 1-dimentional zigzag.

    A triangle wave that looks like a very low-poly cosine.
    """
    # formula: abs((t/period + shift) fmod 1 - 0.5)

    bl_idname = "fabricomatic.zigzag"
    bl_label = "zigzag"

    inp_sockets = (
        ('NodeSocketFloat', 't', 1.0),
        ('NodeSocketFloat', 'period', 1.0),
        ('NodeSocketFloat', 'shift', 0.0),
        ('NodeSocketFloat', 'min', 0.0),
        ('NodeSocketFloat', 'max', 1.0),
    )
    out_sockets = (
        ('NodeSocketFloat', 'value'),
    )

    def build_tree(self):
        arg = self.math(
            'ADD',
            self.math(
                'DIVIDE',
                (self.inp, 't'),
                (self.inp, 'period')),
            (self.inp, 'shift'))

        val = self.math(
            'ABSOLUTE',
            self.math(
                'SUBTRACT',
                self.math('SUBTRACT', arg, self.math('FLOOR', arg)),
                0.5))

        out = self.node('ShaderNodeMapRange', (val, -0.5, +0.5, (self.inp, 'min'), (self.inp, 'max')))

        self.link(out, (self.out, 0))


class FMcosine(ShaderSharedNodeBase):
    """Generating 1-dimentional cosine.

    Just a cosine with parameters.
    Use shift = 0.25 to make it sine.
    """

    bl_idname = "fabricomatic.cosine"
    bl_label = "cosine"

    inp_sockets = (
        ('NodeSocketFloat', 't'),
        ('NodeSocketFloat', 'period', 1.0),
        ('NodeSocketFloat', 'shift', 0.0),
        ('NodeSocketFloat', 'min', 0.0),
        ('NodeSocketFloat', 'max', 1.0),
    )
    out_sockets = (
        ('NodeSocketFloat', 'value'),
    )

    def build_tree(self):
        val = self.math(
            'COSINE',
            self.math(
                'MULTIPLY',
                self.math(
                    'ADD',
                    self.math(
                        'DIVIDE',
                        (self.inp, 't'),
                        (self.inp, 'period')),
                    (self.inp, 'shift')),
                math.pi * 2)
            )
        out = self.node('ShaderNodeMapRange', (val, -1.0, +1.0, (self.inp, 'min'), (self.inp, 'max')))

        self.link(out, (self.out, 0))


class FMcircle(ShaderSharedNodeBase):
    """Maps range 0..2 to semicircle curve"""
    bl_idname = "fabricomatic.circle"
    bl_label = "circle"

    inp_sockets = (
        ('NodeSocketFloat', 'value'),
    )
    out_sockets = (
        ('NodeSocketFloat', 'value'),
    )

    def build_tree(self):
        val = self.math(
            'SQRT',
            self.math(
                'SUBTRACT',
                self.math(
                    'MULTIPLY',
                    (self.inp, 'value'),
                    2.0),
                self.math(
                    'POWER',
                    (self.inp, 'value'),
                    2.0)))

        self.link(val, (self.out, 'value'))


class FMstripes(ShaderSharedNodeBase):
    """Generating periodic 1-dimentional stripes

    Outputs a signal indicating presence of stripes.
    The stripes are placed in the middle of period.

    Inputs:
        - t
            coordinate (across stripes)
        - period
            period (total width of stripe + gap)
        - thickness
            relative width of stripes

    Outputs:
        - stripe
            triangle shaped stripe profile.
            =1.0 at the very middle, =0.0 at edges and over gap
    """
    # Formula:
    #     stripe = max(0, zigzag(t, period)/w + 1)

    bl_idname = "fabricomatic.stripes"
    bl_label = "stripes"

    inp_sockets = (
        ('NodeSocketFloat', 't'),
        ('NodeSocketFloat', 'period', 1.0),
        ('NodeSocketFloat', 'thickness', 0.5, 0.0, 1.0),
    )
    out_sockets = (
        ('NodeSocketFloat', 'strobe'),
    )

    def build_tree(self):
        w = self.math('MULTIPLY', (self.inp, 'thickness'), 0.5)
        zigzag = self.node(
            FMzigzag,
            inputs={
                't': (self.inp, 't'),
                'period': (self.inp, 'period'),
                'shift': 0.5,
                'min': -1.0,
                'max': 0.0,
            })

        strobe = self.math('MAXIMUM', 0.0, self.math('ADD', 1.0, self.math('DIVIDE', zigzag, w)))

        self.link(strobe, (self.out, 'strobe'))
