#r_brush.py

import OpenGL.GL as gl

import quakedef
import cl_main
import gl_model
import glquake

r_visframecount = 0
r_worldmodel = None # Set this when the map finishes loading

gl_lightmap_format = 0
lightmap_bytes = 0

MAX_SANITY_LIGHTMAPS = ( 1 << 20 )
lightmaps : glquake.lightmap_s = None
lightmap_count = 0

allocated: list[int] = []
last_lightmap_allocated = 0
blocklights: list[int] = []

def R_InitBrush():
    global allocated, blocklights
    allocated = [0 for i in range(quakedef.LMBLOCK_WIDTH)]
    blocklights = [ 0 for _ in range(quakedef.LMBLOCK_WIDTH * quakedef.LMBLOCK_HEIGHT * 3)]

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

def R_RecursiveWorldNode(node):
    # If this is a leaf, draw the surfaces it contains
    if node.contents < 0:
        if node.contents != quakedef.CONTENTS_SOLID:
            # Mark leaf visible
            node.visframe = r_visframecount

            # Draw the 'marksurfaces' (pointers to faces visible from this leaf)
            for i in range(node.nummarksurface):
                # marksurfaces are just indices into the master face list
                face_idx = r_worldmodel.marksurfaces[node.firstmarksurface + i]
                face = r_worldmodel.faces[face_idx]
                R_DrawFace(face)
        return

    # Normal Node splitting logic
    dot = (node.plane.normal[0] * r_refdef.vieworg[0] +
           node.plane.normal[1] * r_refdef.vieworg[1] +
           node.plane.normal[2] * r_refdef.vieworg[2]) - node.plane.dist

    if dot >= 0:
        R_RecursiveWorldNode(node.children[0])
        R_RecursiveWorldNode(node.children[1])
    else:
        R_RecursiveWorldNode(node.children[1])
        R_RecursiveWorldNode(node.children[0])

def R_DrawFace(face):
    global r_visframecount

    # 1. Check if already drawn this frame
    if face.visframe == r_visframecount:
        return

    # 2. Bind the Diffuse Wall Texture (Unit 0)
    tex = face.texinfo.texture
    if not tex or not tex.gltexture:
        return

    gl.glBindTexture(gl.GL_TEXTURE_2D, tex.gltexture.texnum)

    # 3. Draw the polygon built in GL_BuildPolygon
    poly = face.polys
    if not poly:
        return

    gl.glBegin(gl.GL_POLYGON)
    for v in poly.verts:
        # v = [x, y, z, s1, t1, s2, t2]
        # s1, t1 are the wall texture coordinates
        gl.glTexCoord2f(v[3], v[4])
        gl.glVertex3f(v[0], v[1], v[2])
    gl.glEnd()

    # Mark as drawn
    face.visframe = r_visframecount



def R_DrawWorldDebug(model):
    import OpenGL.GL as gl

    # 1. Check if we actually have data
    if not model.faces or not model.vertexes:
        return

    # 2. Basic GL Setup for the wireframe
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glDisable(gl.GL_LIGHTING)
    gl.glDisable(gl.GL_CULL_FACE) # See both sides

    gl.glBegin(gl.GL_LINES)
    gl.glColor3f(1.0, 1.0, 1.0) # White lines

    for surf in model.faces:
        # Each face in Quake is a collection of edges
        for i in range(surf.numedges):
            # Get the index into the surfedges list
            e_idx = model.surfedges[surf.firstedge + i]

            # Quake edges can be negative (means reversed)
            if e_idx >= 0:
                v_idx = model.edges[e_idx].v[0]
            else:
                v_idx = model.edges[-e_idx].v[1]

            # Grab the actual vertex coordinates
            # mvertex_t usually has a .position or is a list [x, y, z]
            v = model.vertexes[v_idx]

            # If vertexes is a list of objects, use v.position
            # If vertexes is a list of lists, use v
            if hasattr(v, 'position'):
                gl.glVertex3fv(v.position)
            else:
                gl.glVertex3f(v[0], v[1], v[2])

    gl.glEnd()