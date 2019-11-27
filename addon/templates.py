"""Utiltities to generate basic node setups"""

import bpy

from .nodes.base import ShaderNodeBuilding
from .nodes import utils, weaving

GRID = 200


class TemplateBuilder(ShaderNodeBuilding):
    def __init__(self, tree):
        self.node_tree = tree
        self.inputs = {}
        self.outputs = {}

    def init(self):
        coords = self.get_node('Texture Coordinate')
        if not coords:
            coords = self.add_node(
                'ShaderNodeTexCoord',
                location=(-1800, 0))
        self.inputs['UV'] = coords.outputs['UV']
        self.inputs['Normal'] = coords.outputs['Normal']

        bsdf = self.get_node('Principled BSDF')
        if bsdf:
            socket = bsdf.inputs['Base Color']
            if not socket.is_linked:
                self.outputs['color'] = socket
            socket = bsdf.inputs['Alpha']
            if not socket.is_linked:
                self.outputs['alpha'] = socket
            socket = bsdf.inputs['Normal']
            if not socket.is_linked:
                self.outputs['normal'] = socket


class WeavingStub(TemplateBuilder):
    def build_tree(self):

        x = -7 * GRID

        scaling = self.add_node(
            weaving.FMWeaveScaling,
            location=(x, 0),
            inputs={
                'vector': self.inputs['UV']
            })

        x += GRID

        waving = self.add_node(
            weaving.FMWeavingPlain,
            location=(x, 0),
            inputs={
                'vector': (scaling, 'vector')
            })

        x += GRID

        strobing = self.add_node(
            weaving.FMWeaveStrobing,
            location=(x, 0),
            inputs={
                'vector': (scaling, 'vector')
            })

        x += GRID

        profiling = self.add_node(
            weaving.FMWeaveProfiling,
            location=(x, 0),
            inputs={
                'profiles': (strobing, 'profiles')
            })

        x += GRID

        overlaying = self.add_node(
            weaving.FMWeaveOverlaying,
            location=(x, 0),
            inputs={
                'strobes': (strobing, 'strobes'),
                'profiles': (profiling, 'profiles'),
                'waves': (waving, 'waves')
            })

        x += GRID

        mixing = self.add_node(
            utils.FMmixvalues,
            location=(x, +0.5 * GRID),
            inputs={
                'mask': (overlaying, 'mask')
            })

        bumping = self.add_node(
            weaving.FMWeaveBumping,
            location=(x, -0.5 * GRID),
            inputs={
                'scale': (scaling, 'scale'),
                'elevation': (overlaying, 'elevation'),
                'mask': (overlaying, 'mask'),
                'normal': self.inputs['Normal']
            })

        if 'color' in self.outputs:
            self.add_link((overlaying, 'mask'), self.outputs['color'])
        if 'alpha' in self.outputs:
            self.add_link((strobing, 'alpha'), self.outputs['alpha'])
        if 'normal' in self.outputs:
            self.add_link((bumping, 'normal'), self.outputs['normal'])


class AddTemplateOp(bpy.types.Operator):
    bl_idname = 'fabricomatic.add_template'
    bl_label = "Generate template node set"
    bl_options = {'UNDO'}

    template: bpy.props.StringProperty()

    TEMPLATES = {
        "Stub weaving nodes": WeavingStub,
    }

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR'

    def execute(self, context):
        if not self.properties.is_property_set('template'):
            self.report('ERROR_INVALID_INPUT', "No template specified")
            return {'CANCELED'}
        obj = context.active_object
        mat = context.material
        if mat is None:
            mat = bpy.data.materials.new("weaving")
            mat.use_nodes = True
            mat.cycles.displacement_method = 'BOTH'
            mat.blend_method = 'CLIP'
            if len(obj.material_slots) == 0:
                bpy.ops.object.material_slot_add()
            obj.material_slots[obj.active_material_index].material = mat

        template_cls = self.TEMPLATES[self.template]
        template = template_cls(mat.node_tree)
        template.init()
        template.build_tree()
        return {'FINISHED'}
