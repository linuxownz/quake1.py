#gl_model.py

import struct
import bspfile
import host
import common
import sys_sdl_unix
import quakedef
import modelgen
import spritegen
import r_brush

MAX_MOD_KNOWN = 2048
mod_known: list[quakedef.qmodel_t] = [None] * MAX_MOD_KNOWN
mod_numknown = 0

r_notexture_mip = None
loadmodel: quakedef.qmodel_t = None
loadname = ''

# --- Geometry Verbs ---

def GL_BuildPolygon(model, face):
    """Converts BSP face into a GL-friendly 7-float vertex array."""
    # This logic stays here because it is part of the GL frontend
    tex = face.texinfo
    # Assume glpoly_t is defined in quakedef or locally
    class glpoly_t:
        def __init__(self):
            self.numverts = 0
            self.verts = []

    poly = glpoly_t()
    verts = []
    mins = [99999, 99999]
    maxs = [-99999, -99999]

    for i in range(face.numedges):
        e_idx = model.surfedges[face.firstedge + i]
        v_idx = model.edges[e_idx].v[0] if e_idx >= 0 else model.edges[-e_idx].v[1]
        v = model.vertexes[v_idx].position
        verts.append(v)

        for j in range(2):
            val = (v[0] * tex.vecs[j][0] + v[1] * tex.vecs[j][1] +
                   v[2] * tex.vecs[j][2] + tex.vecs[j][3])
            if val < mins[j]: mins[j] = val
            if val > maxs[j]: maxs[j] = val

    face.texturemins = [int(mins[0] // 16), int(mins[1] // 16)]
    face.extents = [int(maxs[0] // 16) - int(mins[0] // 16),
                    int(maxs[1] // 16) - int(mins[1] // 16)]

    poly.numverts = len(verts)
    for v in verts:
        s1 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3]) / tex.texture.width
        t1 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3]) / tex.texture.height

        s2 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3])
        s2 = (s2 - face.texturemins[0] * 16 + 8) / ((face.extents[0] + 1) * 16)

        t2 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3])
        t2 = (t2 - face.texturemins[1] * 16 + 8) / ((face.extents[1] + 1) * 16)

        poly.verts.append([v[0], v[1], v[2], s1, t1, s2, t2])

    face.polys = poly

def Mod_SetTextureChain(model):
    """Links faces to textures for efficient batch rendering."""
    if not model.textures:
        return
    for tex in model.textures:
        tex.texturechains = []

    for face in model.faces:
        if not face.texinfo or not face.texinfo.texture:
            continue
        face.texinfo.texture.texturechains.append(face)

# --- High Level Loaders ---

def Mod_LoadBrushModel(mod, buffer):
    """Wrapper that calls the BSP parser and then prepares GL data."""
    global loadmodel
    loadmodel = mod
    loadmodel.type = quakedef.modtype_t.mod_brush

    # DELEGATE: All struct.unpack logic for BSP is in bspfile.py
    bspfile.Mod_LoadModel(loadmodel, buffer)

    # POST-PROCESS: Prepare GL data now that the raw bytes are parsed
    for face in loadmodel.faces:
        GL_BuildPolygon(loadmodel, face)
        r_brush.R_BuildLightmap(loadmodel, face)

    Mod_SetTextureChain(loadmodel)
    return loadmodel

def Mod_LoadAliasModel(mod, buffer):
    """Wrapper that calls the MDL parser."""
    global loadmodel
    loadmodel = mod
    # Delegate to modelgen.py
    modelgen.Mod_UnpackAliasModel(loadmodel, buffer)
    return loadmodel

def Mod_LoadSpriteModel(mod, buffer):
    """Wrapper that calls the SPR parser."""
    global loadmodel
    loadmodel = mod
    # Delegate to spritegen.py
    spritegen.Mod_UnpackSpriteModel(loadmodel, buffer)
    return loadmodel

# --- System Management ---

def Mod_LoadModel(mod, crash):
    global loadname, loadmodel

    if not mod.needload:
        return mod

    buf = common.COM_LoadStackFile(mod.name)
    if not buf:
        if crash:
            host.Host_Error(f'Mod_LoadModel: {mod.name} not found')
        return None

    loadname = common.COM_FileBase(mod.name)
    loadmodel = mod
    mod.needload = False

    # Get header to determine type
    mod_type = struct.unpack("<I", buf[:4])[0]

    if mod_type == modelgen.IDPOLYHEADER:
        return Mod_LoadAliasModel(mod, buf)
    elif mod_type == spritegen.IDSPRITEHEADER:
        return Mod_LoadSpriteModel(mod, buf)
    else:
        # Defaults to BSP
        return Mod_LoadBrushModel(mod, buf)

def Mod_Init():
    global r_notexture_mip
    r_notexture_mip = quakedef.texture_t("notexture", 16, 16)
    print("Model Subsystem Initialized.")

def Mod_FindName(name):
    global mod_numknown
    for i in range(mod_numknown):
        if mod_known[i].name == name:
            return mod_known[i]

    if mod_numknown == MAX_MOD_KNOWN:
        sys_sdl_unix.Sys_Error('mod_numknown == MAX_MOD_KNOWN')

    mod = quakedef.qmodel_t()
    mod.name = name
    mod.needload = True
    mod_known[mod_numknown] = mod
    mod_numknown += 1
    return mod

#def Mod_ForName(name, crash):
#    mod = Mod_FindName(name)
#    return Mod_LoadModel(mod, crash)

def Mod_ForName(name):
    # Check cache first (optional for now)

    # Load the raw data
    import common
    buffer = common.COM_LoadHunkFile(name)
    if not buffer:
        return None

    mod = quakedef.qmodel_t()
    mod.name = name

    # Identify if it's a BSP (The 'Brush' model)
    if name.endswith('.bsp'):
        Mod_LoadBrushModel(mod, buffer)

    return mod

def Mod_PointInLeaf(p, model):
    """
    Traverses the BSP tree to find the leaf containing point p.
    p: vec3_t [x, y, z]
    model: The loaded map model object
    """
    if not model or not hasattr(model, 'nodes'):
        # Equivalent to Sys_Error
        raise RuntimeError("Mod_PointInLeaf: bad model")

    # Start at the root node
    node = model.nodes[0]

    while True:
        # In Quake, contents < 0 indicates the node is actually a leaf
        # (e.g., CONTENTS_EMPTY, CONTENTS_SOLID, CONTENTS_WATER)
        if node.contents < 0:
            return node # This is our mleaf_t

        plane = node.plane

        # Calculate the distance of point p from the plane:
        # Ax + By + Cz - D = 0
        d = DotProduct(p, plane.normal) - plane.dist

        if d > 0:
            # Point is "in front" of the plane
            node = node.children[0]
        else:
            # Point is "behind" or on the plane
            node = node.children[1]