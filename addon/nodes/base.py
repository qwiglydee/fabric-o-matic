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

    @property
    def inp(self):
        return self.node_tree.nodes['Group Input']

    @property
    def out(self):
        return self.node_tree.nodes['Group Output']

    @property
    def nodes(self):
        return self.node_tree.nodes

    def init_inputs(self, specs):
        for spec in specs:
            kind, name, def_val, min_val, max_val, *_ = spec + (None, None, None)
            isock = self.node_tree.inputs.new(kind, name)
            if def_val is not None:
                self.inputs[name].default_value = def_val
            if min_val is not None:
                isock.min_value = min_val
            if max_val is not None:
                isock.max_value = max_val

    def init_outputs(self, specs):
        for spec in specs:
            kind, name = spec
            self.node_tree.outputs.new(kind, name)

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
                return self.node_tree.nodes[dst[0]].inputs[dst[1]]
        raise ValueError(f"invalid dst {dst}")

    def link(self, src, dst):
        self.node_tree.links.new(self._get_src(src), self._get_dst(dst))

    def node(self, kind, inputs, name=None, **attrs):
        assert isinstance(kind, str) or hasattr(kind, 'bl_idname')
        if hasattr(kind, 'bl_idname'):
            kind = kind.bl_idname
        node = self.node_tree.nodes.new(kind)
        if name is not None:
            node.name = name
        for attr, val in attrs.items():
            setattr(node, attr, val)
        if isinstance(inputs, (list, tuple)):
            inputs = enumerate(inputs)
        elif isinstance(inputs, dict):
            inputs = inputs.items()
        else:
            raise ValueError('inputs')
        for k, inp in inputs:
            if inp is None:
                continue
            if isinstance(inp, float) or isinstance(inp, int):
                node.inputs[k].default_value = inp
            elif isinstance(inp, tuple) and inp[0] == '=':
                node.inputs[k].default_value = inp[1]
            else:
                self.link(inp, (node, k))
        return node

    def route(self, name):
        return self.node('NodeReroute', (), name=name)

    def math(self, operation, *args, name=None):
        return self.node(
            'ShaderNodeMath',
            args,            
            operation=operation, 
            name=name)

    def vmath(self, operation, *args, name=None):
        return self.node(
            'ShaderNodeVectorMath',
            args,            
            operation=operation,
            name=name)

    def col(self, r=0.0, g=0.0, b=0.0, name=None):
        return self.node('ShaderNodeCombineRGB', {'R': r, 'G': g, 'B': b}, name=name)

    def rgb(self, color, name=None):
        return self.node('ShaderNodeSeparateRGB', (color,), name=name)

    def vec(self, x=0.0, y=0.0, z=0.0, name=None):
        return self.node('ShaderNodeCombineXYZ', {'X': x, 'Y': y, 'Z': z}, name=name)

    def xyz(self, vector, name=None):
        return self.node('ShaderNodeSeparateXYZ', (vector,), name=name )

    def mix(self, operation, color1=None, color2=None, fac=1.0, name=None):
        return self.node(
            'ShaderNodeMixRGB',
            {'Fac': fac, 'Color1': color1, 'Color2': color2},
            blend_type=operation,
            name=name)


class ShaderSharedNodeBase(ShaderNodeBuilding, bpy.types.ShaderNodeCustomGroup):
    """Node with shared tree"""
    inp_sockets = ()
    out_sockets = ()

    def init(self, _context):
        name = "." + self.__class__.__name__
        if name in bpy.data.node_groups:
            self.node_tree = bpy.data.node_groups[name]
        else:
            self.init_tree(name)
            self.init_inputs(self.inp_sockets)
            self.init_outputs(self.out_sockets)
            self.build_tree()


class ShaderVolatileNodeBase(ShaderNodeBuilding, bpy.types.ShaderNodeCustomGroup):
    """Node with volatile tree"""
    inp_sockets = ()
    out_sockets = ()

    def init(self, _context):
        name = "." + self.__class__.__name__ + ".000"
        self.init_tree(name)
        self.init_inputs(self.inp_sockets)
        self.init_outputs(self.out_sockets)
        self.build_tree()

    def copy(self, node):
        self.node_tree = self.node_tree.copy()

    def free(self):
        self.node_tree.nodes.clear()
        bpy.data.node_groups.remove(self.node_tree)