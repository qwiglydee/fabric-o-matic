import bpy

from . import utils


class AddBezier(bpy.types.Operator):
    bl_idname = "nodes.bezier_sdf"
    bl_label = "Bezier SDF"
    bl_description = "Add bezier projection node"

    def execute(self, context):
        bpy.ops.node.add_node(type=bpy.types.ShaderNodeScript.__name__)
        node = context.active_node
        node.bl_label = "Bezier SDF"
        # node.mode = "INTERNAL"
        # node.script = utils.load_shader("bezier2.osl")
        node.mode = "EXTERNAL"
        node.filepath = utils.shader_filepath("bezier2.osl")
        return {"FINISHED"}

    @classmethod
    def poll(cls, context):
        return context.engine == "CYCLES" and context.scene.cycles.shading_system
