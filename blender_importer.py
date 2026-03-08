"""Import a PLY file into Blender as a point cloud object."""

import bpy


def _create_vertex_color_material():
    """Create (or reuse) a material that displays vertex colors."""
    mat_name = "ArborTools_VertexColor"
    mat = bpy.data.materials.get(mat_name)
    if mat is not None:
        return mat

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    # Attribute node → reads "Color" from PLY import
    attr_node = tree.nodes.new("ShaderNodeAttribute")
    attr_node.attribute_name = "Color"
    attr_node.location = (-300, 0)

    # Emission shader — unlit, shows colors as-is
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.location = (0, 0)

    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (200, 0)

    tree.links.new(attr_node.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])

    return mat


def import_ply_to_blender(ply_path):
    """Import PLY and name the resulting object 'ArborTools_PointCloud'.

    Returns the imported object.
    """
    # Blender 4.0+ uses wm.ply_import; older versions use import_mesh.ply
    if hasattr(bpy.ops.wm, "ply_import"):
        bpy.ops.wm.ply_import(filepath=ply_path)
    elif hasattr(bpy.ops.import_mesh, "ply"):
        bpy.ops.import_mesh.ply(filepath=ply_path)
    else:
        raise RuntimeError("No PLY import operator found in this Blender version")

    obj = bpy.context.active_object
    if obj is None:
        raise RuntimeError("PLY import did not produce an active object")
    obj.name = "ArborTools_PointCloud"

    # Assign vertex color material
    mat = _create_vertex_color_material()
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    return obj
