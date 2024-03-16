import bpy
from pathlib import Path

BASE_DIR = Path(__file__).parent
SHADERS_DIR = BASE_DIR / "shaders"


def shader_filepath(filename):
    return str(SHADERS_DIR / filename)


def load_shader(filename: str):
    if filename in bpy.data.texts:
        return bpy.data.texts[filename]
    else:
        return bpy.data.texts.load(shader_filepath(filename), internal=True)
