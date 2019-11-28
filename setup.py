# import os.path
# import sys

from setuptools import setup
from sphinx.setup_command import BuildDoc

# sys.path.insert(0, os.path.dirname(__file__))

NAME = "fabric-o-matic"
VERSION = "0.1-beta"

setup(
    name=NAME,
    version=VERSION,
    description='An add-on for Blender3D',
    url="https://github.com/qwiglydee/fabric-o-matic",
    setup_requires=['Sphinx', 'sphinx-rtd-theme'],
    cmdclass={
        'docs': BuildDoc,
    },
    command_options={
        'docs': {
            'project': ('setup.py', NAME),
            'version': ('setup.py', VERSION),
            'source_dir': ('setup.py', "dev/docs/"),
            'build_dir': ('setup.py', "docs/")
        }
    }
)


