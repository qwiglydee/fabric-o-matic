import bpy

from .utils import load_shader

class AddBezier(bpy.types.Operator):
    bl_idname = "nodes.bezier_sdf"
    bl_label = "Bezier SDF"
    bl_description = "Add bezier projection node"

    def execute(self, context):
        text = load_shader("bezier2.osl")
        bpy.ops.node.add_node(type=bpy.types.ShaderNodeScript.__name__)
        node = context.active_node
        node.script = text
        node.bl_label="Bezier SDF"
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.engine == 'CYCLES' and context.scene.cycles.shading_system