import random
import bpy


def clean_previews():
    for img in bpy.data.images.values():
        if img.name.startswith("Preview:"):
            img.use_fake_user = False
            bpy.data.images.remove(img)


def render_preview(name):
    scene = bpy.data.scenes["Scene"]
    scene.render.filepath = f"/tmp/preview-{name}.png"
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(bpy.data.scenes["Scene"].render.filepath)
    img.name = f"Preview: {name}"
    img.use_fake_user = True
    img.pack()


def show_objects(b, *names):
    for n in names:
        bpy.data.objects[n].hide_render = not b


if __name__ == "__main__":
    clean_previews()
    for m in bpy.data.materials.values():
        if m.name[0] == '.':
            continue
        if m.name == 'Wicker':
            show_objects(True, 'Torus')
            show_objects(False, 'Sphere', 'Cloth')
            bpy.data.objects["Torus"].material_slots[0].material = m
        else:
            show_objects(False, 'Torus')
            show_objects(True, 'Sphere', 'Cloth')
            bpy.data.objects["Cloth"].material_slots[0].material = m
        render_preview(m.name)
    bpy.ops.wm.save_mainfile()
