# gl_model.py

# from enum import Enum
# from typing import Optional # Required for Optional type hints

import sys_sdl_unix
import quakedef

MAX_MOD_KNOWN = 2048
mod_known : list[qmodel_t] = [None] * MAX_MOD_KNOWN
mod_numknown = 0

r_notexture_mip = None
r_notexture_mip2 = None


# --- Verbs ---

def GL_BuildPolygon(model, face):
    tex = face.texinfo
    poly = glpoly_t()

    verts = []
    mins = [99999, 99999]
    maxs = [-99999, -99999]

    # 1. Gather verts and find texture boundaries
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

    # 2. Store lightmap extents
    face.texturemins = [int(mins[0] // 16), int(mins[1] // 16)]
    face.extents = [int(maxs[0] // 16) - int(mins[0] // 16),
                    int(maxs[1] // 16) - int(mins[1] // 16)]

    # 3. Build 7-float vertex array [x, y, z, s1, t1, s2, t2]
    poly.numverts = len(verts)
    for v in verts:
        # Texture coordinates
        s1 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3]) / tex.texture.width
        t1 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3]) / tex.texture.height

        # Lightmap coordinates (Normalized 0.0 to 1.0 for the patch texture)
        s2 = (v[0] * tex.vecs[0][0] + v[1] * tex.vecs[0][1] +
              v[2] * tex.vecs[0][2] + tex.vecs[0][3])
        s2 = (s2 - face.texturemins[0] * 16 + 8) / ((face.extents[0] + 1) * 16)

        t2 = (v[0] * tex.vecs[1][0] + v[1] * tex.vecs[1][1] +
              v[2] * tex.vecs[1][2] + tex.vecs[1][3])
        t2 = (t2 - face.texturemins[1] * 16 + 8) / ((face.extents[1] + 1) * 16)

        poly.verts.append([v[0], v[1], v[2], s1, t1, s2, t2])

    face.polys = poly

def Mod_SetTextureChain(model):
    for tex in model.textures:
        tex.texturechains = []

    for face in model.faces:
        if not face.texinfo or not face.texinfo.texture:
            continue
        face.texinfo.texture.texturechains.append(face)



def Mod_Init():
    """Initializes the model loading subsystem."""
    global r_notexture_mip

    # Create a dummy texture to use when a real one is missing
    # This prevents the engine from crashing on bad texture lookups
    r_notexture_mip = quakedef.texture_t("notexture", 16, 16)

    # In a full engine, we would also clear the model list here
    print("Model Subsystem Initialized.")


def Mod_FindName(name):
    global mod_numknown
    if not name:
        sys_sdl_unix.Sys_Error('Mod_FindName: name is None')

    for i in range( mod_numknown ):
        mod = mod_known[i]
        if mod.name == name:
            break

    if i == mod_numknown:
        if mod_numknown == MAX_MOD_KNOWN:
            sys_sdl_unix.Sys_Error('mod_numknown == MAX_MOD_KNOWN')
        mod.name = name
        mod.needload = True
        mod_numknown += 1


def Mod_ForName(name, crash):
    mod = Mod_FindName(name)
    return Mod_LoadModel(mod, crash)