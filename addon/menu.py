import bpy

from . import operators

class FBMMenu(bpy.types.Menu):
    bl_idname="NODE_MT_add_fbm"
    bl_label="Fabric-o-Matic"

    def draw(self, context):
        layout = self.layout
        layout.operator(operators.AddBezier.bl_idname, text=operators.AddBezier.bl_label)


def extend_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.menu(FBMMenu.bl_idname)


def register():
    bpy.types.NODE_MT_add.append(extend_menu)


def unregister():
    bpy.types.NODE_MT_add.remove(extend_menu)
