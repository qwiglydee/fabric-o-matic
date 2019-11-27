"""Utiltities to generate basic node setups"""

import bpy

from .nodes.base import ShaderNodeBuilding
from .nodes import utils, weaving

GRID = 250


class TemplateBuilder(ShaderNodeBuilding):
    def __init__(self, mat):
        self.node_tree = mat.node_tree
        self.bsdf = self.get_node('Principled BSDF')


class WeavingStub(TemplateBuilder):
    name = "Weaving"

    def build_tree(self):
        x = -7 * GRID

        coords = self.add_node(
            'ShaderNodeTexCoord',
            location=(x, 0))

        x += GRID

        scaling = self.add_node(
            weaving.FMWeaveScaling,
            location=(x, 0),
            inputs={
                'vector': (coords, 'UV')
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
                'normal': (coords, 'Normal')
            })

        self.add_link((overlaying, 'mask'), (self.bsdf, 'Base Color'))
        self.add_link((strobing, 'alpha'), (self.bsdf, 'Alpha'))
        self.add_link((bumping, 'normal'), (self.bsdf, 'Normal'))


class AddTemplateOp(bpy.types.Operator):
    bl_idname = 'fabricomatic.add_template'
    bl_label = "Generate template node set"
    bl_options = {'UNDO'}

    template: bpy.props.StringProperty()

    TEMPLATES = {
        "Weaving stub": WeavingStub,
    }

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR'

    def execute(self, context):
        if not self.properties.is_property_set('template'):
            self.report('ERROR_INVALID_INPUT', "No template specified")
            return {'CANCELED'}
        mat = self.create_material()
        mat.blend_method = 'CLIP'
        mat.cycles.displacement_method = 'BOTH'
        obj = context.active_object
        if len(obj.material_slots) == 0:
            bpy.ops.object.material_slot_add()
        obj.material_slots[obj.active_material_index].material = mat
        return {'FINISHED'}

    def create_material(self):
        template_cls = self.TEMPLATES[self.template]
        mat = bpy.data.materials.new(template_cls.name)
        mat.use_nodes = True
        template = template_cls(mat)
        template.build_tree()
        return mat
