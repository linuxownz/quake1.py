#r_brush.py

import OpenGL.GL as gl

import glquake
import quakedef
import cl_main
import gl_model

gl_lightmap_format = 0
lightmap_bytes = 0

MAX_SANITY_LIGHTMAPS = ( 1 << 20 )
lightmaps : glquake.lightmap_s = None
lightmap_count = 0

allocated = [0 for i in range(glquake.LMBLOCK_WIDTH)]
last_lightmap_allocated = 0

blocklights = [ 0 for _ in range(glquake.LMBLOCK_WIDTH*glquake.LMBLOCK_HEIGHT*3)]

def R_BuildLightmap(model, face):
    """Converts raw BSP light data into an OpenGL texture for the face."""
    if face.lightofs == -1:
        face.lightmap_texture = 0 # No lighting for this face (e.g., sky)
        return

    # 1. Calculate dimensions (1 pixel per 16 world units)
    width = face.extents[0] + 1
    height = face.extents[1] + 1
    size = width * height

    # 2. Extract raw bytes from the lighting lump
    offset = face.lightofs
    light_bytes = model.lightdata[offset : offset + size]

    # 3. Create RGBA data (Greyscale light + Alpha 255)
    rgba_data = bytearray(size * 4)
    for i in range(size):
        val = light_bytes[i]
        rgba_data[i*4 + 0] = val
        rgba_data[i*4 + 1] = val
        rgba_data[i*4 + 2] = val
        rgba_data[i*4 + 3] = 255

    # 4. Upload to OpenGL
    texid = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texid)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, width, height, 0,
                    gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, rgba_data)

    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

    face.lightmap_texture = texid

def R_RebuildAllLightmaps():
    if not cl_main.cl.worldmodel:
        return

    for i in range(1, quakedef.MAX_MODELS):
        mod : gl_model.qmodel_t = None
        if not ( mod := cl_main.cl.model_precache[i]):
            continue
        fa = mod.surface