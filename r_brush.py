#r_brush.py

import ctypes
import math
import struct

import OpenGL.GL as gl

import bspfile
import cl_main
import console
import cvar
import gl_model
import gl_rlight
import gl_rmain
import gl_rmisc
import gl_texmgr
import gl_vidsdl
import gl_warp
import glquake
import mathlib
import quakedef
import r_world
import render
import sys_sdl_unix

r_visframecount = 0
r_worldmodel = None # Set this when the map finishes loading

gl_lightmap_format = 0
lightmap_bytes = 0

MAX_SANITY_LIGHTMAPS = ( 1 << 20 )
lightmaps : list[glquake.lightmap_s] = []
lightmap_count = 0

allocated: list[int] = []
last_lightmap_allocated = 0
blocklights: list[int] = [ 0 for _ in range(glquake.LMBLOCK_WIDTH*glquake.LMBLOCK_HEIGHT*3)]

r_pcurrentvertbase: quakedef.mvertex_t = None
currentmodel: quakedef.qmodel_t = None

gl_bmodel_vbo = 0

def R_TextureAnimation(base:quakedef.texture_t, frame: int) -> quakedef.texture_t:
    if frame:
        if base.alternate_anims:
            base = base.alternate_anims

    if not base.anim_total:
        return base

    relative = int(cl_main.cl.time * 10 ) % base.anim_total

    count = 0
    while base.anim_min > relative or base.anim_max <= relative:
        base = base.anim_next
        if not base:
            sys_sdl_unix.Sys_Error('R_TextureAnimation: broken cycle')
        count += 1
        if count > 100:
            sys_sdl_unix.Sys_Error('R_TextureAnimation: infinite cycle')

    return base

def DrawGLPoly(p: quakedef.glpoly_t):
    gl.glBegin(gl.GL_POLYGON)

    for i in range(p.numverts):
        v = p.verts[i]
        gl.glTexCoord2f(v[3], v[4])
        gl.glVertex3f(v[0], v[1], v[2])
    gl.glEnd()

def DrawGLTriangleFan(p: quakedef.glpoly_t):

    gl.glBegin(gl.GL_TRIANGLE_FAN)
    for i in range(p.numverts):
        v = p.verts[i]
        gl.glVertex3f(v[0], v[1], v[2])
    gl.glEnd()


def R_DrawBrushModel(e: render.entity_t):

    if gl_rmain.R_CullModelForEntity(e):
        return

    gl_rmain.currententity = e
    clmodel = e.model

    mathlib.VectorSubtract(gl_rmain.r_refdef.vieworg, e.origin, gl_rmain.modelorg)
    if e.angles[0] or e.angles[1] or e.angles[2]:
        temp: quakedef.vec3_t = [0, 0, 0]
        forward: quakedef.vec3_t = [0, 0, 0]
        right: quakedef.vec3_t = [0, 0, 0]
        up: quakedef.vec3_t = [0, 0, 0]

        mathlib.VectorCopy(gl_rmain.modelorg, temp)
        mathlib.AngleVectors(e.angles, forward, right, up)
        gl_rmain.modelorg[0] = mathlib.DotProduct(temp, forward)
        gl_rmain.modelorg[1] = -mathlib.DotProduct(temp, right)
        gl_rmain.modelorg[2] = mathlib.DotProduct(temp, up)

    if clmodel.firstmodelsurface != 0 and not cvar.Cvar_GetCvar('gl_flashblend').value:
        for k in range(quakedef.MAX_DLIGHTS):
            if cl_main.cl_dlights[k].die < cl_main.cl.time or not cl_main.cl_dlights[k].radius:
                continue

            gl_rlight.R_MarkLights(cl_main.cl_dlights[k], k, clmodel.nodes[clmodel.hulls[0].firstclipnode])

    gl.glPushMatrix()

    e.angles[0] = -e.angles[0]
    gl_zfix = 0# cvar.Cvar_GetCvar('gl_zfix').value

    if gl_zfix:
        e.origin[0] -= quakedef.DIST_EPSILON
        e.origin[1] -= quakedef.DIST_EPSILON
        e.origin[2] -= quakedef.DIST_EPSILON

    gl_rmain.R_RotateForEntity(e.origin, e.angles, e.scale)

    if gl_zfix:
        e.origin[0] += quakedef.DIST_EPSILON
        e.origin[1] += quakedef.DIST_EPSILON
        e.origin[2] += quakedef.DIST_EPSILON

    e.angles[0] = -e.angles[0]

    r_world.R_ClearTextureChains(clmodel, quakedef.texchain_t.chain_model)

    for i in range(clmodel.nummodelsurfaces):
        psurf: quakedef.msurface_t = clmodel.surfaces[clmodel.firstmodelsurface + i]
        pplane:quakedef.mplane_t = psurf.plane
        dot = mathlib.DotProduct(gl_rmain.modelorg, pplane.normal) - pplane.dist

        if (((psurf.flags & quakedef.SURF_PLANEBACK) and (dot < -glquake.BACKFACE_EPSILON)) or (not(psurf.flags & quakedef.SURF_PLANEBACK) and (dot > glquake.BACKFACE_EPSILON))):
            r_world.R_ChainSurface(psurf, quakedef.texchain_t.chain_model)
            R_RenderDynamicLightmaps(psurf)
            gl_rmain.rs_brushpolys += 1

    r_world.R_DrawTextureChains (clmodel, e, quakedef.texchain_t.chain_model);
    r_world.R_DrawTextureChains_Water (clmodel, e, quakedef.texchain_t.chain_model)

    gl.glPopMatrix()

def R_DrawBrushModel_ShowTris(e: render.entity_t):
    if gl_rmain.R_CullModelForEntity(e):
        return

    gl_rmain.currententity = e
    clmodel: quakedef.qmodel_t = e.model

    mathlib.VectorSubtract(gl_rmain.r_refdef.vieworg, e.origin, gl_rmain.modelorg)

    if e.angles[0] or e.angles[1] or e.angles[2]:
        temp: quakedef.vec3_t = [0, 0, 0]
        forward: quakedef.vec3_t = [0, 0, 0]
        right: quakedef.vec3_t = [0, 0, 0]
        up: quakedef.vec3_t = [0, 0, 0]

        mathlib.VectorCopy(gl_rmain.modelorg, temp)
        mathlib.AngleVectors(e.angles, forward, right, up)
        gl_rmain.modelorg[0] = mathlib.DotProduct(temp, forward)
        gl_rmain.modelorg[1] = mathlib.DotProduct(temp, right)
        gl_rmain.modelorg[2] = mathlib.DotProduct(temp, up)

    gl.glPushMatrix()
    e.angles[0] = -e.angles[0]
    gl_rmain.R_RotateForEntity(e.origin, e.angles, e.scale)
    e.angles[0] = -e.angles[0]

    r_oldwater = cvar.Cvar_GetCvar('r_oldwater').value

    for i in range(clmodel.nummodelsurfaces):
        psurf: quakedef.msurface_t = clmodel.surfaces[clmodel.firstmodelsurface + i]
        pplane:quakedef.mplane_t = psurf.plane
        dot = mathlib.DotProduct(gl_rmain.modelorg, pplane.normal) - pplane.dist

        if ((psurf.flags & quakedef.SURF_PLANEBACK) and (dot < -glquake.BACKFACE_EPSILON)) or (not(psurf.flags & quakedef.SURF_PLANEBACK) and (dot > glquake.BACKFACE_EPSILON)):
            if ((psurf.flags & quakedef.SURF_DRAWTURB) and r_oldwater):
                p = psurf.polys.next
                while p:
                    DrawGLTriangleFan (p);
                    p = psurf.polys.next
            else:
                DrawGLTriangleFan (psurf.polys);

    gl.glPopMatrix()


def R_RenderDynamicLightmaps(fa: quakedef.msurface_t) -> None:
    # 1. Skip non-lightmapped surfaces (e.g., tiled sky / water surfaces)
    if fa.flags & quakedef.SURF_DRAWTILED:
        return

    # 2. Add surface polygon to lightmap texture render chain
    lm = lightmaps[fa.lightmaptexturenum]
    fa.polys.chain = lm.polys
    lm.polys = fa.polys

    # 3. Check for lightstyle animated modifications (e.g., flickering lights)
    is_dynamic: bool = False
    for maps in range(quakedef.MAXLIGHTMAPS):
        style = fa.styles[maps]
        if style == 255:
            break
        if gl_rmain.d_lightstylevalue[style] != fa.cached_light[maps]:
            is_dynamic = True
            break

    # 4. Check for dynamic light entity interactions (rockets, explosions)
    if not is_dynamic:  # noqa: SIM102
        if fa.dlightframe == gl_rmain.r_framecount or fa.cached_dlight:
            is_dynamic = True

    # 5. Process lightmap rebuild and track dirty rect bounds
    if is_dynamic and cvar.Cvar_GetCvar('r_dynamic').value:
        lm.modified = True
        theRect = lm.rectchange

        # Expand top boundary (t)
        if fa.light_t < theRect.t:
            if theRect.h:
                theRect.h += theRect.t - fa.light_t
            theRect.t = fa.light_t

        # Expand left boundary (l)
        if fa.light_s < theRect.l:
            if theRect.w:
                theRect.w += theRect.l - fa.light_s
            theRect.l = fa.light_s

        smax = (fa.extents[0] >> 4) + 1
        tmax = (fa.extents[1] >> 4) + 1

        # Expand width boundary (w)
        if (theRect.w + theRect.l) < (fa.light_s + smax):
            theRect.w = (fa.light_s - theRect.l) + smax

        # Expand height boundary (h)
        if (theRect.h + theRect.t) < (fa.light_t + tmax):
            theRect.h = (fa.light_t - theRect.t) + tmax

        # Calculate buffer byte offset into lightmap atlas memory
        stride_bytes = quakedef.LMBLOCK_WIDTH * lightmap_bytes
        base_offset = (fa.light_t * stride_bytes) + (fa.light_s * lightmap_bytes)

        # Build dynamic surface lightmap pixels directly into lightmap data buffer
        R_BuildLightMap(fa, lm.data, base_offset, stride_bytes)



# Lightmap atlas state variables matching r_brush.c globals
lightmap_count: int = 0
lightmaps: list[glquake.lightmap_s] = []
allocated: list[list[int]] = []  # Per-lightmap height trackers: allocated[texnum][x]
last_lightmap_allocated: int = 0

def AllocBlock(w: int, h: int) -> tuple[int, int, int]:
    """
    C equivalent (r_brush.c):
    qboolean AllocBlock (int w, int h, int *x, int *y)

    Skyline lightmap packing algorithm. Allocates a sub-rectangle (w x h)
    within lightmap atlas textures. Returns (texnum, x, y).
    """
    global lightmap_count, lightmaps, allocated, last_lightmap_allocated

    for texnum in range(MAX_SANITY_LIGHTMAPS):
        # 1. Allocate a new lightmap atlas texture page if needed
        if texnum == lightmap_count:
            lightmap_count += 1
            lm = glquake.lightmap_s()
            lm.data = bytearray(lightmap_bytes * glquake.LMBLOCK_WIDTH * glquake.LMBLOCK_HEIGHT)
            lightmaps.append(lm)
            allocated.append([0] * glquake.LMBLOCK_WIDTH)

        best = glquake.LMBLOCK_HEIGHT
        best_x = -1
        best_y = -1

        # 2. Search for a position in the current lightmap page (texnum)
        curr_allocated = allocated[texnum]

        for i in range(glquake.LMBLOCK_WIDTH - w + 1):
            best2 = 0
            fits = True

            for j in range(w):
                val = curr_allocated[i + j]
                if val >= best:
                    fits = False
                    break
                if val > best2:
                    best2 = val

            if fits:
                best_x = i
                best_y = best = best2

        # 3. Check if block fits vertically within current page bounds
        if best + h > glquake.LMBLOCK_HEIGHT:
            continue

        # 4. Update skyline height map for this lightmap page
        for i in range(w):
            curr_allocated[best_x + i] = best + h

        last_lightmap_allocated = texnum
        return texnum, best_x, best_y

    sys_sdl_unix.Sys_Error("AllocBlock: full")
    return 0, 0, 0

def GL_CreateSurfaceLightmap(surf: quakedef.msurface_t) -> None:
    """
    C equivalent (r_brush.c):
    void GL_CreateSurfaceLightmap (msurface_t *surf)

    Allocates a lightmap region in the lightmap atlas for the surface
    and builds the initial lightmap pixel data.
    """
    # 1. Non-lightmapped surfaces (sky / water / tiled)
    if surf.flags & quakedef.SURF_DRAWTILED:
        surf.lightmaptexturenum = -1
        return

    # 2. Compute sample grid dimensions (extents >> 4 plus 1 sample)
    smax = (surf.extents[0] >> 4) + 1
    tmax = (surf.extents[1] >> 4) + 1

    # 3. Allocate sub-rectangle block in atlas
    texnum, light_s, light_t = AllocBlock(smax, tmax)
    surf.lightmaptexturenum = texnum
    surf.light_s = light_s
    surf.light_t = light_t

    # 4. Calculate stride and buffer offset
    row_stride = glquake.LMBLOCK_WIDTH * lightmap_bytes
    offset = (surf.light_t * row_stride) + (surf.light_s * lightmap_bytes)

    # 5. Build lightmap directly into atlas memory buffer
    R_BuildLightMap(
        surf,
        lightmaps[surf.lightmaptexturenum].data,
        offset,
        row_stride
    )



def BuildSurfaceDisplayList(fa: quakedef.msurface_t) -> None:
    """
    C equivalent (r_brush.c):
    void BuildSurfaceDisplayList (msurface_t *fa)

    Reconstructs glpoly_t geometry from BSP edges and computes
    base texture and lightmap coordinates.
    """
    pedges = currentmodel.edges
    lnumverts = fa.numedges

    # 1. Instantiate polygon and prepend to surface chain
    poly = quakedef.glpoly_t()
    poly.numverts = lnumverts
    poly.verts = [[0.0] * quakedef.VERTEXSIZE for _ in range(lnumverts)]

    poly.next = fa.polys
    fa.polys = poly

    # 2. Setup base texture coordinate scale & offset
    if fa.flags & quakedef.SURF_DRAWTURB:
        s0 = 0.0
        t0 = 0.0
        sdiv = 128.0
        tdiv = 128.0
    else:
        s0 = fa.texinfo.vecs[0][3]
        t0 = fa.texinfo.vecs[1][3]
        sdiv = float(fa.texinfo.texture.width)
        tdiv = float(fa.texinfo.texture.height)

    # 3. Process each vertex in the surface edge chain
    for i in range(lnumverts):
        lindex = currentmodel.surfedges[fa.firstedge + i]

        if lindex > 0:
            r_pedge = pedges[lindex]
            vec = r_pcurrentvertbase[r_pedge.v[0]].position
        else:
            r_pedge = pedges[-lindex]
            vec = r_pcurrentvertbase[r_pedge.v[1]].position

        # Base texture mapping (s, t)
        s = mathlib.DotProduct(vec, fa.texinfo.vecs[0]) + s0
        s /= sdiv

        t = mathlib.DotProduct(vec, fa.texinfo.vecs[1]) + t0
        t /= tdiv

        # Assign X, Y, Z world space vertex coordinates
        poly.verts[i][0] = vec[0]
        poly.verts[i][1] = vec[1]
        poly.verts[i][2] = vec[2]

        # Assign base texture coordinates (s1, t1)
        poly.verts[i][3] = s
        poly.verts[i][4] = t

        # Q64 RERELEASE texture shift compatibility
        if fa.texinfo.texture.shift > 0:
            shift_factor = 2 * fa.texinfo.texture.shift
            poly.verts[i][3] /= shift_factor
            poly.verts[i][4] /= shift_factor

        # Lightmap texture coordinates (s2, t2)
        s_lm = mathlib.DotProduct(vec, fa.texinfo.vecs[0]) + fa.texinfo.vecs[0][3]
        s_lm -= fa.texturemins[0]
        s_lm += fa.light_s * 16
        s_lm += 8
        s_lm /= float(glquake.LMBLOCK_WIDTH * 16)

        t_lm = mathlib.DotProduct(vec, fa.texinfo.vecs[1]) + fa.texinfo.vecs[1][3]
        t_lm -= fa.texturemins[1]
        t_lm += fa.light_t * 16
        t_lm += 8
        t_lm /= float(glquake.LMBLOCK_HEIGHT * 16)

        poly.verts[i][5] = s_lm
        poly.verts[i][6] = t_lm

    poly.numverts = lnumverts

    # 4. Handle liquid surface subdivision for warp animation
    if fa.flags & quakedef.SURF_DRAWTURB:
        gl_warp.GL_SubdivideSurface(fa)


def GL_BuildLightmaps() -> None:
    """
    C equivalent (r_brush.c):
    void GL_BuildLightmaps (void)

    Rebuilds all world and brush model surface lightmaps, packages them
    into atlas textures, and uploads them to OpenGL via TexMgr.
    """
    global lightmaps, last_lightmap_allocated, lightmap_count, gl_lightmap_format, lightmap_bytes
    global currentmodel, allocated

    gl_rmain.r_framecount = 1

    # 1. Clear existing lightmaps
    if lightmaps is not None:
        for i in range(lightmap_count):
            lightmaps[i].data = None

    lightmaps = []
    allocated = []  # Reset skyline allocation tracking lists
    last_lightmap_allocated = 0
    lightmap_count = 0

    global r_pcurrentvertbase

    # 2. Configure lightmap format and global byte stride
    gl_lightmap_format = gl.GL_RGBA

    if gl_lightmap_format in (gl.GL_RGBA, gl.GL_BGRA):
        lightmap_bytes = 4
    else:
        sys_sdl_unix.Sys_Error("GL_BuildLightmaps: bad lightmap format")

    # 3. Process every precached brush model (world + bmodel entities like
    #    items/doors files); '*N' submodels share the world's surfaces
    if not cl_main.cl.worldmodel:
        return

    for j in range(1, quakedef.MAX_MODELS):
        m = cl_main.cl.model_precache[j]
        if not m:
            continue
        if m.name and m.name[0] == '*':
            continue
        if m.type != quakedef.modtype_t.mod_brush:
            continue

        r_pcurrentvertbase = m.vertexes
        currentmodel = m

        for i in range(m.numsurfaces):
            surf = m.surfaces[i]

            # Skip tiled/non-lightmapped surfaces (sky/water)
            if surf.flags & quakedef.SURF_DRAWTILED:
                continue

            GL_CreateSurfaceLightmap(surf)
            BuildSurfaceDisplayList(surf)

    # 4. Upload lightmap atlas pages to GPU via TexMgr
    for i in range(lightmap_count):
        lm = lightmaps[i]
        lm.modified = False

        # Reset dynamic lightmap dirty rectangle bounds
        lm.rectchange.l = glquake.LMBLOCK_WIDTH
        lm.rectchange.t = glquake.LMBLOCK_HEIGHT
        lm.rectchange.w = 0
        lm.rectchange.h = 0

        name = f"lightmap{i:07d}"
        lm.texture = gl_texmgr.TexMgr_LoadImage(
            cl_main.cl.worldmodel,
            name,
            glquake.LMBLOCK_WIDTH,
            glquake.LMBLOCK_HEIGHT,
            gl_texmgr.srcformat.SRC_LIGHTMAP,
            lm.data,
            "",
            lm.data,
            gl_texmgr.TEXPREF_LINEAR | gl_texmgr.TEXPREF_NOPICMIP
        )

    # 5. Check total allocated lightmap block count against engine limits
    num_blocks = lightmap_count * ((glquake.LMBLOCK_WIDTH // 128) * (glquake.LMBLOCK_HEIGHT // 128))
    if num_blocks > 64:
        console.Con_Warning(f"{num_blocks} lightmaps exceed standard limit of 64\n")



def GL_DeleteBModelVertexBuffer():
    global gl_bmodel_vbo

    if not ( gl_vidsdl.gl_vbo_able and gl_vidsdl.gl_mtexable and gl_vidsdl.gl_max_texture_units >= 3):
        return

    if gl_bmodel_vbo != 0:
        gl.glDeleteBuffers(1, [gl_bmodel_vbo] )
        gl_bmodel_vbo = 0

    gl_rmisc.GL_ClearBufferBindings()




def GL_BuildBModelVertexBuffer() -> None:
    """
    C equivalent (r_brush.c / gl_vbo.c):
    void GL_BuildBModelVertexBuffer (void)

    Packs all brush model surface vertices into a single VBO buffer
    and uploads it to the GPU as GL_STATIC_DRAW.
    """
    global gl_bmodel_vbo

    # 1. Hardware extension check
    if not (gl_vidsdl.gl_vbo_able and gl_vidsdl.gl_mtexable and gl_vidsdl.gl_max_texture_units >= 3):
        return

    # 2. Delete existing buffer and generate a new VBO ID
    if gl_bmodel_vbo != 0:
        buf_id = (gl.GLuint * 1)(gl_bmodel_vbo)
        gl.glDeleteBuffers(1, buf_id)
        gl_bmodel_vbo = 0

    buf_id = (gl.GLuint * 1)()
    gl.glGenBuffers(1, buf_id)
    gl_bmodel_vbo = buf_id[0]

    # 3. Pass 1: Count total vertices across all precached brush models
    numverts: int = 0
    for j in range(1, quakedef.MAX_MODELS):
        m = cl_main.cl.model_precache[j]
        if not m or not m.name or m.name[0] == '*' or m.type != quakedef.modtype_t.mod_brush:
            continue

        for i in range(m.numsurfaces):
            numverts += m.surfaces[i].numedges

    if numverts == 0:
        return

    # 4. Pass 2: Allocate flat C float array and pack interleaved vertex data
    total_floats = numverts * quakedef.VERTEXSIZE
    varray_type = gl.GLfloat * total_floats
    varray = varray_type()

    varray_index: int = 0  # Running vertex count offset

    for j in range(1, quakedef.MAX_MODELS):
        m = cl_main.cl.model_precache[j]
        if not m or not m.name or m.name[0] == '*' or m.type != quakedef.modtype_t.mod_brush:
            continue

        for i in range(m.numsurfaces):
            s = m.surfaces[i]
            s.vbo_firstvert = varray_index

            # Copy s.polys.verts into flat varray memory
            if s.polys:
                float_dest_idx = varray_index * quakedef.VERTEXSIZE
                for v_idx in range(s.numedges):
                    vert = s.polys.verts[v_idx]
                    base_idx = float_dest_idx + (v_idx * quakedef.VERTEXSIZE)

                    varray[base_idx + 0] = vert[0]  # X
                    varray[base_idx + 1] = vert[1]  # Y
                    varray[base_idx + 2] = vert[2]  # Z
                    varray[base_idx + 3] = vert[3]  # S1
                    varray[base_idx + 4] = vert[4]  # T1
                    varray[base_idx + 5] = vert[5]  # S2
                    varray[base_idx + 6] = vert[6]  # T2

            varray_index += s.numedges

    # 5. Upload buffer to GPU memory
    varray_bytes = total_floats * ctypes.sizeof(gl.GLfloat)

    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, gl_bmodel_vbo)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, varray_bytes, varray, gl.GL_STATIC_DRAW)

    # 6. Clear cached GL state bindings
    gl_rmisc.GL_ClearBufferBindings()


def R_AddDynamicLights(surf: quakedef.msurface_t) -> None:
    """
    C equivalent (r_brush.c):
    void R_AddDynamicLights (msurface_t *surf)

    Accumulates dynamic lighting contributions (dlights) into the global
    blocklights array for the current surface.
    """
    smax = (surf.extents[0] >> 4) + 1
    tmax = (surf.extents[1] >> 4) + 1
    tex = surf.texinfo

    impact = [0.0, 0.0, 0.0]
    local = [0.0, 0.0]

    for lnum in range(quakedef.MAX_DLIGHTS):
        # 1. Check bitmask to see if dynamic light hits this surface plane
        if not (surf.dlightbits[lnum >> 5] & (1 << (lnum & 31))):
            continue

        dl = cl_main.cl_dlights[lnum]
        rad = dl.radius

        # 2. Distance from light origin to surface plane
        dist = mathlib.DotProduct(dl.origin, surf.plane.normal) - surf.plane.dist
        rad -= math.fabs(dist)
        minlight = dl.minlight

        if rad < minlight:
            continue

        minlight = rad - minlight

        # 3. Calculate 3D impact point on plane
        for i in range(3):
            impact[i] = dl.origin[i] - (surf.plane.normal[i] * dist)

        # 4. Transform impact point to local surface lightmap coordinates
        local[0] = mathlib.DotProduct(impact, tex.vecs[0]) + tex.vecs[0][3] - surf.texturemins[0]
        local[1] = mathlib.DotProduct(impact, tex.vecs[1]) + tex.vecs[1][3] - surf.texturemins[1]

        cred   = dl.color[0] * 256.0
        cgreen = dl.color[1] * 256.0
        cblue  = dl.color[2] * 256.0

        # 5. Rasterize dynamic light circle over surface lightmap grid
        for t in range(tmax):
            td = math.fabs(local[1] - (t * 16))

            for s in range(smax):
                sd = math.fabs(local[0] - (s * 16))

                # Approximate radial distance: max(sd, td) + 0.5 * min(sd, td)
                if sd > td:
                    sample_dist = sd + (td * 0.5)
                else:
                    sample_dist = td + (sd * 0.5)

                if sample_dist < minlight:
                    # Calculate attenuation brightness ratio
                    brightness = rad - sample_dist

                    # 1D offset into global RGB blocklights array
                    bl_idx = ((t * smax) + s) * 3

                    blocklights[bl_idx + 0] += int(brightness * cred)
                    blocklights[bl_idx + 1] += int(brightness * cgreen)
                    blocklights[bl_idx + 2] += int(brightness * cblue)



def R_InitBrush():
    global allocated, blocklights
    allocated = [0 for i in range(quakedef.LMBLOCK_WIDTH)]
    blocklights = [ 0 for _ in range(quakedef.LMBLOCK_WIDTH * quakedef.LMBLOCK_HEIGHT * 3)]


def R_BuildLightMap(
    surf: quakedef.msurface_t,
    dest: bytearray | memoryview,
    offset: int,
    stride: int
) -> None:
    """
    C equivalent (r_brush.c):
    void R_BuildLightMap (msurface_t *surf, byte *dest, int stride)

    Builds dynamic lightmap samples for a surface into a target byte buffer,
    supporting overbright scaling, wide 10-bit color packed formats, and
    both RGBA and BGRA pixel layouts.
    """
    global blocklights

    overbright = 1 if cvar.Cvar_GetCvar('gl_overbright').value != 0 else 0
    wide10bits = 1 if cvar.Cvar_GetCvar('r_lightmapwide').value != 0 else 0

    surf.cached_dlight = (surf.dlightframe == gl_rmain.r_framecount)

    smax = (surf.extents[0] >> 4) + 1
    tmax = (surf.extents[1] >> 4) + 1
    size = smax * tmax

    # 1. Accumulate lightmap samples or default to fullbright
    if cl_main.cl.worldmodel and cl_main.cl.worldmodel.lightdata:
        # Clear blocklights buffer (size * 3 channels)
        for i in range(size * 3):
            blocklights[i] = 0

        # Accumulate static lightmap data across active lightstyles
        if surf.samples is not None:
            sample_ptr = 0
            for maps in range(quakedef.MAXLIGHTMAPS):
                if surf.styles[maps] == 255:
                    break

                scale = gl_rmain.d_lightstylevalue[surf.styles[maps]]
                surf.cached_light[maps] = scale  # 8.8 fraction scale factor

                bl_ptr = 0
                for _ in range(size):
                    sample_offset = surf.samples + sample_ptr
                    blocklights[bl_ptr + 0] += cl_main.cl.worldmodel.lightdata[sample_offset + 0] * scale
                    blocklights[bl_ptr + 1] += cl_main.cl.worldmodel.lightdata[sample_offset + 1] * scale
                    blocklights[bl_ptr + 2] += cl_main.cl.worldmodel.lightdata[sample_offset + 2] * scale
                    sample_ptr += 3
                    bl_ptr += 3

        # Accumulate dynamic light sources hitting the surface frame
        if surf.dlightframe == gl_rmain.r_framecount:
            R_AddDynamicLights(surf)
    else:
        # Set to full bright (255) if level has no lightdata
        for i in range(size * 3):
            blocklights[i] = 255

    # 2. Pack and write blocklights into destination texture buffer
    dest_ptr = offset
    bl_ptr = 0

    match gl_lightmap_format:
        case gl.GL_RGBA:
            row_stride_adjust = stride - (smax * 4)

            for i in range(tmax):
                for j in range(smax):
                    if overbright:
                        r = blocklights[bl_ptr + 0] >> 8
                        g = blocklights[bl_ptr + 1] >> 8
                        b = blocklights[bl_ptr + 2] >> 8
                        bl_ptr += 3
                    else:
                        r = blocklights[bl_ptr + 0] >> 7
                        g = blocklights[bl_ptr + 1] >> 7
                        b = blocklights[bl_ptr + 2] >> 7
                        bl_ptr += 3

                        if wide10bits:
                            r = 255 if r > 255 else r
                            g = 255 if g > 255 else g
                            b = 255 if b > 255 else b

                            # Pack 10-10-10-2 unsigned integer (loc0 goto equivalent)
                            packed_val = ((r & 0x3FF) << 22) | ((g & 0x3FF) << 12) | ((b & 0x3FF) << 2) | 3
                            struct.pack_into("<I", dest, dest_ptr, packed_val)
                            dest_ptr += 4
                            continue

                    if wide10bits:
                        r = 1023 if r > 1023 else r
                        g = 1023 if g > 1023 else g
                        b = 1023 if b > 1023 else b

                        packed_val = ((r & 0x3FF) << 22) | ((g & 0x3FF) << 12) | ((b & 0x3FF) << 2) | 3
                        struct.pack_into("<I", dest, dest_ptr, packed_val)
                        dest_ptr += 4
                    else:
                        dest[dest_ptr + 0] = 255 if r > 255 else r
                        dest[dest_ptr + 1] = 255 if g > 255 else g
                        dest[dest_ptr + 2] = 255 if b > 255 else b
                        dest[dest_ptr + 3] = 255
                        dest_ptr += 4

                dest_ptr += row_stride_adjust

        case gl.GL_BGRA:
            row_stride_adjust = stride - (smax * 4)

            for i in range(tmax):
                for j in range(smax):
                    if overbright:
                        r = blocklights[bl_ptr + 0] >> 8
                        g = blocklights[bl_ptr + 1] >> 8
                        b = blocklights[bl_ptr + 2] >> 8
                        bl_ptr += 3
                    else:
                        r = blocklights[bl_ptr + 0] >> 7
                        g = blocklights[bl_ptr + 1] >> 7
                        b = blocklights[bl_ptr + 2] >> 7
                        bl_ptr += 3

                        if wide10bits:
                            r = 255 if r > 255 else r
                            g = 255 if g > 255 else g
                            b = 255 if b > 255 else b

                            # Pack 10-10-10-2 BGRA unsigned integer (loc1 goto equivalent)
                            packed_val = ((b & 0x3FF) << 22) | ((g & 0x3FF) << 12) | ((r & 0x3FF) << 2) | 3
                            struct.pack_into("<I", dest, dest_ptr, packed_val)
                            dest_ptr += 4
                            continue

                    if wide10bits:
                        r = 1023 if r > 1023 else r
                        g = 1023 if g > 1023 else g
                        b = 1023 if b > 1023 else b

                        packed_val = ((b & 0x3FF) << 22) | ((g & 0x3FF) << 12) | ((r & 0x3FF) << 2) | 3
                        struct.pack_into("<I", dest, dest_ptr, packed_val)
                        dest_ptr += 4
                    else:
                        dest[dest_ptr + 0] = 255 if b > 255 else b
                        dest[dest_ptr + 1] = 255 if g > 255 else g
                        dest[dest_ptr + 2] = 255 if r > 255 else r
                        dest[dest_ptr + 3] = 255
                        dest_ptr += 4

                dest_ptr += row_stride_adjust

        case _:
            sys_sdl_unix.Sys_Error("R_BuildLightMap: bad lightmap format")



def R_UploadLightmap(lmap: int):
    wide10bits = bool(cvar.Cvar_GetCvar('r_lightmapwide').value)
    _type = gl.GL_UNSIGNED_INT_10_10_10_2 if wide10bits else gl.GL_UNSIGNED_BYTE
    lm = lightmaps[lmap]

    if not lm.modified:
        return

    lm.modified = False

    gl.glTexSubImage2D(
        gl.GL_TEXTURE_2D,
        0, 0,
        lm.rectchange.t,
        quakedef.LMBLOCK_WIDTH,
        lm.rectchange.h,
        gl_lightmap_format,
        _type,
        lm.data[lm.rectchange.t * quakedef.LMBLOCK_WIDTH * lightmap_bytes:]
    )

    lm.rectchange.l = quakedef.LMBLOCK_WIDTH
    lm.rectchange.t = quakedef.LMBLOCK_HEIGHT
    lm.rectchange.h = 0
    lm.rectchange.w = 0

    gl_rmain.rs_dynamiclightmaps += 1

def R_UploadLightmaps():
    for lmap in range(lightmap_count):
        if not lightmaps[lmap].modified:
            continue

        gl_texmgr.GL_Bind(lightmaps[lmap].texture)
        R_UploadLightmap(lmap)

def R_RebuildAllLightmaps() -> None:
    """
    C equivalent (r_brush.c):
    void R_RebuildAllLightmaps (void)

    Rebuilds all surface lightmaps across precached models and uploads
    the full lightmap texture blocks directly to the GPU.
    """
    wide10bits = bool(cvar.Cvar_GetCvar('r_lightmapwide').value)
    _type = gl.GL_UNSIGNED_INT_10_10_10_2 if wide10bits else gl.GL_UNSIGNED_BYTE

    if not cl_main.cl.worldmodel:
        return

    # 1. For each surface in each precached model, rebuild lightmaps into block memory
    for i in range(1, quakedef.MAX_MODELS):
        mod = cl_main.cl.model_precache[i]
        if not mod:
            continue

        for j in range(mod.nummodelsurfaces):
            fa = mod.surfaces[mod.firstmodelsurface + j]

            if fa.flags & quakedef.SURF_DRAWTILED:
                continue

            # Calculate byte offset into target lightmap block data array
            offset = (
                fa.light_t * quakedef.LMBLOCK_WIDTH * lightmap_bytes
                + fa.light_s * lightmap_bytes
            )

            R_BuildLightMap(
                fa,
                lightmaps[fa.lightmaptexturenum].data,
                offset,
                quakedef.LMBLOCK_WIDTH * lightmap_bytes
            )

    # 2. For each lightmap block, bind and upload the complete texture
    for i in range(lightmap_count):
        gl_texmgr.GL_Bind(lightmaps[i].texture)
        gl.glTexSubImage2D(
            gl.GL_TEXTURE_2D,
            0,
            0,
            0,
            quakedef.LMBLOCK_WIDTH,
            quakedef.LMBLOCK_HEIGHT,
            gl_lightmap_format,
            _type,
            lightmaps[i].data
        )