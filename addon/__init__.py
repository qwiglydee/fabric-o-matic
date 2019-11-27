import os
import bpy
import bpy.utils.previews

from .nodes import utils, weaving
from . import samples, templates

bl_info = {
    'name': "Fabric-o-matic",
    'description': "Library of nodes to generate various woven fabric patterns",
    'author': "qwiglydee@gmail.com",
    'version': (0, 1),
    'warning': "Beta release. Please, provide feedback to make it better",
    'blender': (2, 81, 0),
    'category': "Material",
    'location': "NodeEditor > Add > Fabric-o-matic"
}


class MenuBase(bpy.types.Menu):
    def draw_node_item(self, node_class):
        adding = self.layout.operator('node.add_node', text=node_class.bl_label)
        adding.type = node_class.bl_idname
        adding.use_transform = True


class AddNodeMenu(MenuBase, bpy.types.Menu):
    bl_idname = "NODE_MT_add_fabricomatic_component"
    bl_label = "Weaving components"

    def draw(self, _context):
        self.draw_node_item(weaving.FMWeaveScaling)
        self.draw_node_item(weaving.FMWeaveStrobing)
        self.draw_node_item(weaving.FMWeaveStrobingBulged)
        self.draw_node_item(weaving.FMWeaveProfiling)
        self.draw_node_item(weaving.FMWeavingPlain)
        self.draw_node_item(weaving.FMWeavingTwill)
        self.draw_node_item(weaving.FMWeavingJacquard)
        self.draw_node_item(weaving.FMWeaveOverlaying)
        self.draw_node_item(weaving.FMWeaveBumping)


class AddUtilMenu(MenuBase, bpy.types.Menu):
    bl_idname = "NODE_MT_add_fabricomatic_util"
    bl_label = "Utils"

    def draw(self, _context):
        self.draw_node_item(utils.FMzigzag)
        self.draw_node_item(utils.FMcosine)
        self.draw_node_item(utils.FMcircle)
        self.draw_node_item(utils.FMstripes)
        self.draw_node_item(utils.FMmixfloats)
        self.draw_node_item(utils.FMmixvalues)
        self.draw_node_item(utils.FMfmodulo)
        self.draw_node_item(utils.FMwraptex)
        self.draw_node_item(utils.FMfloortex)
        self.draw_node_item(weaving.FMWeavePatternSampling)
        self.draw_node_item(weaving.FMWeavePatternInterpolating)


class AddMenu(MenuBase, bpy.types.Menu):
    bl_idname = "NODE_MT_add_fabricomatic"
    bl_label = "Fabric-o-matic"

    def draw(self, _context):
        layout = self.layout
        layout.menu(AddUtilMenu.bl_idname)
        layout.menu(AddNodeMenu.bl_idname)
        for k in templates.AddTemplateOp.TEMPLATES.keys():
            op = layout.operator(templates.AddTemplateOp.bl_idname, text=k)
            op.template = k
        layout.operator(samples.BrowseLibraryOp.bl_idname, text="Browse library...")


def extend_add_menu(self, _context):
    self.layout.menu(AddMenu.bl_idname)


classes = (
    utils.FMmixfloats,
    utils.FMmixvalues,
    utils.FMfmodulo,
    utils.FMzigzag,
    utils.FMcosine,
    utils.FMcircle,
    utils.FMstripes,
    utils.FMwraptex,
    utils.FMfloortex,
    weaving.FMWeaveScaling,
    weaving.FMWeaveStrobingBulged,
    weaving.FMWeaveStrobing,
    weaving.FMWeaveProfiling,
    weaving.FMWeavePatternSampling,
    weaving.FMWeavePatternInterpolating,
    weaving.FMWeavingPlain,
    weaving.FMWeavingTwill,
    weaving.FMWeavingJacquard,
    weaving.FMWeaveOverlaying,
    weaving.FMWeaveBumping,
    samples.BrowseLibraryOp,
    samples.ImportMaterialOp,
    templates.AddTemplateOp,
    AddNodeMenu,
    AddUtilMenu,
    AddMenu,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_add.append(extend_add_menu)
    samples.register()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.NODE_MT_add.remove(extend_add_menu)
    samples.unregister()
