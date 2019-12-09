"""Utilities sto implrt materials from samples library"""

from pathlib import Path

import bpy
import bpy.utils.previews


class Library:
    def __init__(self, path):
        self.blendfile = path / "samples.blend"
        self.imagedir = path / "previews" / "samples"
        self.__previews = None
        self.__materials_enum = None

    def list_materials(self):
        materials = []
        with bpy.data.libraries.load(str(self.blendfile)) as (src, dst):
            materials.extend(filter(lambda m: '.' not in m, src.materials))
        return materials

    def load_previews(self):
        self.__previews = bpy.utils.previews.new()
        for file in self.imagedir.iterdir():
            img = self.__previews.load(file.name, str(file), 'IMAGE')
            # print("loaded", file, img.icon_size[:], img.image_size[:])

    def free_previews(self):
        bpy.utils.previews.remove(self.__previews)
        self.__previews = None
        self.__materials_enum = None

    def enum_materials(self):
        if self.__materials_enum is None:
            self.load_previews()
            previews = self.__previews
            materials = self.list_materials()

            def preview(m):
                img = m + ".png"
                if img in previews:
                    return previews[img].icon_id

            self.__materials_enum = [(mat, mat, "", preview(mat), i) for i, mat in enumerate(materials)]

        return self.__materials_enum

    def import_material(self, name):
        with bpy.data.libraries.load(str(self.blendfile)) as (src, dst):
            dst.materials = [name]
        mat = dst.materials[0]
        return mat


library = Library(Path(__file__).parent)


class ImportMaterialOp(bpy.types.Operator):
    bl_idname = 'fabricomatic.lib_append'
    bl_label = "Import from library"
    bl_options = {'UNDO'}

    material: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return context.area.ui_type == 'ShaderNodeTree'

    def execute(self, context):
        if not self.properties.is_property_set('material'):
            self.report({'ERROR_INVALID_INPUT'}, "No material specified")
            return {'CANCELLED'}
        mat = library.import_material(self.material)
        if mat is None:
            self.report({'ERROR_INVALID_INPUT'}, f"Failed to import '{self.material}'")
            return {'CANCELLED'}
        obj = context.active_object
        if len(obj.material_slots) == 0:
            bpy.ops.object.material_slot_add()
        obj.material_slots[obj.active_material_index].material = mat
        return {'FINISHED'}


class BrowseLibraryOp(ImportMaterialOp):
    bl_idname = 'fabricomatic.lib_browse'
    bl_label = "Browse library"

    material: bpy.props.EnumProperty(items=lambda s, c: library.enum_materials())

    def invoke(self, context, _event):
        self.material = 'Plain'
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, _context):
        self.layout.template_icon_view(self, 'material', show_labels=True, scale=10)
        self.layout.prop(self, 'material')


def register():
    # library.load_previews()
    pass


def unregister():
    library.free_previews()
