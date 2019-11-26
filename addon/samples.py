import os

import bpy

preview_collections = {}

# def enum_previews_from_directory_items(self, context):
#     """EnumProperty callback"""
#     enum_items = []
#
#     if context is None:
#         return enum_items
#
#     directory = PREVIEWS
#
#     # Get the preview collection (defined in register func).
#     pcoll = preview_collections["main"]
#
#     if pcoll.enum_items is not None:
#         return pcoll.enum_items
#
#     print("Scanning directory: %s" % PREVIEWS)
#
#     # Scan the directory for png files
#     image_paths = []
#     for fn in os.listdir(directory):
#         if fn.lower().endswith(".png"):
#             image_paths.append(fn)
#
#     for i, name in enumerate(image_paths):
#         # generates a thumbnail preview for a file.
#         filepath = os.path.join(directory, name)
#         thumb = pcoll.load(name, filepath, 'IMAGE')
#         enum_items.append((name, name, "", thumb.icon_id, i))
#     pcoll.enum_items = enum_items
#
#     return enum_items


class Library:
    BLENDFILE = os.path.join(os.path.dirname(__file__), "samples.blend")
    enumerated: list = None
    previews: bpy.utils.previews.ImagePreviewCollection = None

    @staticmethod
    def enum_materials(_1, context):
        if Library.enumerated is None:
            wm = context.window_manager
            materials = []
            with bpy.data.libraries.load(Library.BLENDFILE) as (src, dst):
                materials.extend(src.materials)
                dst.images = [f"Preview: {name}" for name in src.materials]
            wm.progress_begin(0, len(materials))
            i = 0
            Library.enumerated = []
            for mat, img in zip(materials, dst.images):
                if not mat or not img:
                    continue
                i += 1
                preview = Library.previews.new(mat)
                preview.image_size = img.size
                preview.image_pixels_float[:] = img.pixels
                Library.enumerated.append((mat, mat, "", preview.icon_id, i))
                bpy.data.images.remove(img)
                wm.progress_update(i)
            wm.progress_end()
        return Library.enumerated

    @staticmethod
    def import_material(material_name):
        with bpy.data.libraries.load(Library.BLENDFILE) as (src, dst):
            dst.materials = [material_name]
        mat = dst.materials[0]
        return mat


class ImportMaterialOp(bpy.types.Operator):
    bl_idname = 'fabricomatic.lib_append'
    bl_label = "Import from library"
    bl_options = {'UNDO'}

    material: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return context.space_data.type == 'NODE_EDITOR'

    def execute(self, context):
        if not self.properties.is_property_set('material'):
            self.report('ERROR_INVALID_INPUT', "No material specified")
            return {'CANCELED'}
        mat = Library.import_material(self.material)
        if mat is None:
            self.report('ERROR_INVALID_INPUT', f"Failed to import '{self.material}'")
            return {'CANCELED'}
        obj = context.active_object
        if len(obj.material_slots) == 0:
            bpy.ops.object.material_slot_add()
        obj.material_slots[obj.active_material_index].material = mat
        return {'FINISHED'}


class BrowseLibraryOp(ImportMaterialOp):
    bl_idname = 'fabricomatic.lib_browse'
    bl_label = "Browse library"

    material: bpy.props.EnumProperty(items=Library.enum_materials)

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, _context):
        self.layout.template_icon_view(self, 'material', show_labels=True, scale=16.0, scale_popup=8.0)


def register():
    Library.previews = bpy.utils.previews.new()


def unregister():
    bpy.utils.previews.remove(Library.previews)
