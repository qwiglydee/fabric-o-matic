import bpy


class ShaderNodeBuilding:
    """Base utilities to construct node trees"""

    node_tree = None
    inputs = {}
    outputs = {}

    def init_tree(self, name):
        self.node_tree = bpy.data.node_groups.new(name, 'ShaderNodeTree')
        self.node_tree.nodes.new('NodeGroupInput')
        self.node_tree.nodes.new('NodeGroupOutput')

    def add_input(self, kind, name, **attrs):
        isock = self.node_tree.inputs.new(kind, name)
        sock = self.inputs[name]
        for attr, val in attrs.items():
            if attr in ('min_value', 'max_value'):
                setattr(isock, attr, val)
            else:
                setattr(sock, attr, val)
        return sock

    def add_output(self, kind, name, **attrs):
        self.node_tree.outputs.new(kind, name)
        sock = self.outputs[name]
        for attr, val in attrs.items():
            setattr(sock, attr, val)
        return sock

    def _get_src(self, src):
        if isinstance(src, bpy.types.NodeSocket):
            return src
        if isinstance(src, bpy.types.Node):
            return src.outputs[0]
        if isinstance(src, str):
            return self.node_tree.nodes[src].outputs[0]
        if isinstance(src, tuple):
            if isinstance(src[0], bpy.types.Node):
                return src[0].outputs[src[1]]
            if isinstance(src[0], str):
                if src[0] == 'input':
                    return self.node_tree.nodes['Group Input'].outputs[src[1]]
                else:
                    return self.node_tree.nodes[src[0]].outputs[src[1]]
        raise ValueError(f"invalid src {src}")

    def _get_dst(self, dst):
        if isinstance(dst, bpy.types.NodeSocket):
            return dst
        if isinstance(dst, bpy.types.Node):
            return dst.inputs[0]
        if isinstance(dst, str):
            return self.node_tree.nodes[dst].inputs[0]
        if isinstance(dst, tuple):
            if isinstance(dst[0], bpy.types.Node):
                return dst[0].inputs[dst[1]]
            if isinstance(dst[0], str):
                if dst[0] == 'output':
                    return self.node_tree.nodes['Group Output'].inputs[dst[1]]
                else:
                    return self.node_tree.nodes[dst[0]].inputs[dst[1]]
        raise ValueError(f"invalid dst {dst}")

    def add_link(self, src, dst):
        self.node_tree.links.new(self._get_src(src), self._get_dst(dst))

    def add_node(self, kind, name=None, inputs=None, **attrs):
        if hasattr(kind, 'bl_idname'):
            kind = kind.bl_idname
        node = self.node_tree.nodes.new(kind)
        if name is not None:
            node.name = name
        for attr, val in attrs.items():
            setattr(node, attr, val)
        if inputs:
            for dstsock, inp in inputs.items():
                if inp is None:
                    continue
                if isinstance(inp, float) or isinstance(inp, int):
                    node.inputs[dstsock].default_value = inp
                elif isinstance(inp, tuple) and inp[0] == '=':
                    node.inputs[dstsock].default_value = inp[1]
                else:
                    self.add_link(inp, (node, dstsock))
        return node

    def add_math(self, operation, *args, name=None):
        return self.add_node(
            'ShaderNodeMath',
            name=name,
            operation=operation,
            inputs=dict(enumerate(args)))

    def add_vmath(self, operation, *args, name=None):
        return self.add_node(
            'ShaderNodeVectorMath',
            name=name,
            operation=operation,
            inputs=dict(enumerate(args)))

    def add_col(self, r=0.0, g=0.0, b=0.0, name=None):
        return self.add_node('ShaderNodeCombineRGB', inputs={'R': r, 'G': g, 'B': b}, name=name)

    def add_rgb(self, color, name=None):
        return self.add_node('ShaderNodeSeparateRGB', inputs={0: color}, name=name)

    def add_vec(self, x=0.0, y=0.0, z=0.0, name=None):
        return self.add_node('ShaderNodeCombineXYZ', inputs={'X': x, 'Y': y, 'Z': z}, name=name)

    def add_xyz(self, vector, name=None):
        return self.add_node('ShaderNodeSeparateXYZ', inputs={0: vector}, name=name)

    def add_mix(self, operation, color1=None, color2=None, fac=1.0, name=None):
        return self.add_node(
            'ShaderNodeMixRGB',
            blend_type=operation,
            name=name,
            inputs={
                'Fac': fac,
                'Color1': color1,
                'Color2': color2})

    def get_node(self, name):
        return self.node_tree.nodes.get(name)


class ShaderSharedNodeBase(ShaderNodeBuilding, bpy.types.ShaderNodeCustomGroup):
    """Node with shared tree"""

    def init(self, _context):
        name = "." + self.__class__.__name__
        if name in bpy.data.node_groups:
            self.node_tree = bpy.data.node_groups[name]
        else:
            self.init_tree(name)
            self.build_tree()


class ShaderVolatileNodeBase(ShaderNodeBuilding, bpy.types.ShaderNodeCustomGroup):
    """Node with volatile tree"""

    def init(self, _context):
        name = "." + self.__class__.__name__ + ".000"
        self.init_tree(name)
        self.build_tree()

    def copy(self, node):
        self.node_tree = self.node_tree.copy()

    def free(self):
        self.node_tree.nodes.clear()
        self.free_tree()
    