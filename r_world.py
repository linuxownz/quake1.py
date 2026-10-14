#r_world.py

import collections
import ctypes
import random

import numpy as np
import OpenGL.GL as gl

import cl_main
import cvar
import gl_model
import gl_warp
import gl_fog
import gl_rmain
import gl_refrag
import gl_rmisc
import gl_texmgr
import gl_vidsdl
import glquake
import mathlib
import protocol
import quakedef
import r_brush
import render
import sv_main

vertAttrIndex      = 0
texCoordsAttrIndex = 1
LMCoordsAttrIndex  = 2

r_world_program     = 0
texLoc              = 0
LMTexLoc            = 0
fullbrightTexLoc    = 0
useFullbrightTexLoc = 0
useOverbrightLoc    = 0
useAlphaTestLoc     = 0
useLightmapWideLoc  = 0
useLightmapOnlyLoc  = 0
alphaLoc            = 0

MAX_BATCH_SIZE = 4096

vbo_indices = np.zeros(MAX_BATCH_SIZE, dtype=np.uint32)   # client-side index array for glDrawElements
num_vbo_indices: int = 0

def _chains(t):
    """texture_t.texturechains is None until first use (C: texturechains[2]).
    Use a defaultdict that yields None for unset chains, so any chain key works."""
    c = t.texturechains
    if not isinstance(c, collections.defaultdict):
        c = collections.defaultdict(lambda: None)
        t.texturechains = c
    return c


def _chain_get(t, chain):
    return _chains(t).get(chain)


def R_ClearTextureChains(mod: quakedef.qmodel_t, chain: quakedef.texchain_t):
    for i in range(mod.numtextures):
        if mod.textures[i]:
            _chains(mod.textures[i])[chain] = None

    for i in range(r_brush.lightmap_count):
        r_brush.lightmaps[i].polys = None

def R_ChainSurface(surf: quakedef.msurface_t, chain: quakedef.texchain_t):
    chains = _chains(surf.texinfo.texture)
    surf.texturechain = chains.get(chain)
    chains[chain] = surf

def R_BackFaceCull(surf: quakedef.msurface_t) -> bool:
    if surf.plane.type < 3:
        dot = gl_rmain.r_refdef.vieworg[surf.plane.type] - surf.plane.dist
    else:
        dot = mathlib.DotProduct (gl_rmain.r_refdef.vieworg, surf.plane.normal) - surf.plane.dist

    return bool((dot < 0) ^ bool(surf.flags & quakedef.SURF_PLANEBACK))



def R_MarkSurfaces() -> None:
    """C: R_MarkSurfaces (r_world.c) - PVS walk, culling, texture chains."""
    worldmodel = cl_main.cl.worldmodel
    chain_world = quakedef.texchain_t.chain_world

    # Clear lightmap chains
    for i in range(r_brush.lightmap_count):
        r_brush.lightmaps[i].polys = None

    viewleaf = gl_rmain.r_viewleaf

    # Water portal check on the current view leaf
    nearwaterportal = False
    for surf in viewleaf.firstmarksurface[:viewleaf.nummarksurfaces]:
        if surf.flags & quakedef.SURF_DRAWTURB:
            nearwaterportal = True
            break

    r_novis = _cv('r_novis')

    if (r_novis != 0 or viewleaf.contents == quakedef.CONTENTS_SOLID or
            viewleaf.contents == quakedef.CONTENTS_SKY):
        vis = gl_model.Mod_NoVisPVS(worldmodel)
    elif nearwaterportal:
        vis = sv_main.SV_FatPVS(gl_rmain.r_origin, worldmodel)
    else:
        vis = gl_model.Mod_LeafPVS(viewleaf, worldmodel)

    gl_rmain.r_visframecount += 1
    visframecount = gl_rmain.r_visframecount

    # Clear world chains
    for texture in worldmodel.textures:
        if texture is not None:
            _chains(texture)[chain_world] = None

    oldskyleaf = _cv('r_oldskyleaf')

    # Leaf i in the PVS is worldmodel.leafs[i + 1]
    for i in range(worldmodel.numleafs):
        if not (vis[i >> 3] & (1 << (i & 7))):
            continue

        leaf = worldmodel.leafs[i + 1]

        if gl_rmain.R_CullBox(leaf.minmaxs[0:3], leaf.minmaxs[3:6]):
            continue

        if oldskyleaf or leaf.contents != quakedef.CONTENTS_SKY:
            for surf in leaf.firstmarksurface[:leaf.nummarksurfaces]:
                if surf.visframe == visframecount:
                    continue
                surf.visframe = visframecount

                if (not gl_rmain.R_CullBox(surf.mins, surf.maxs)
                        and not R_BackFaceCull(surf)):
                    gl_rmain.rs_brushpolys += 1
                    R_ChainSurface(surf, chain_world)
                    r_brush.R_RenderDynamicLightmaps(surf)

                    tex = surf.texinfo.texture
                    if getattr(tex, 'warpimage', None):
                        tex.update_warp = True

        # Static entities attached to this leaf
        if leaf.efrags:
            gl_refrag.R_StoreEfrags(leaf.efrags)


def _cv(name):
    c = cvar.Cvar_GetCvar(name)
    return c.value if c is not None else 0


def R_BeginTransparentDrawing(entalpha: float):
    if entalpha < 1.0:
        gl.glDepthMask(gl.GL_FALSE)
        gl.glEnable(gl.GL_BLEND)
        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
        gl.glColor4f(1, 1, 1, entalpha)

def R_EndTransparentDrawing(entalpha: float):
    if entalpha < 1.0:
        gl.glDepthMask (gl.GL_TRUE);
        gl.glDisable (gl.GL_BLEND);
        gl.glTexEnvf (gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
        gl.glColor3f (1, 1, 1);

def R_DrawTextureChains_ShowTris(model: quakedef.qmodel_t, chain: quakedef.texchain_t):

    r_oldwater = cvar.Cvar_GetCvar('r_oldwater').value

    for i in range(model.numtextures):
        t = model.textures[i]
        if not t:
            continue
        if r_oldwater and t.texturechains[chain] and ( t.texturechains[chain].flags & quakedef.SURF_DRAWTURB):
            s = t.texturechains[chain]
            while s is not None:
                if s.polys is not None:
                    p = s.polys.next
                    while p is not None:
                        r_brush.DrawGLTriangleFan(p)
                        p = p.next

                s = s.texturechain

        else:
            s = t.texturechains[chain]
            while s is not None:
                r_brush.DrawGLTriangleFan(p)
                s = s.texturechain


def R_DrawTextureChains_Drawflat(model: quakedef.qmodel_t, chain: int) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_Drawflat (qmodel_t *model, texchain_t chain)

    Renders flat-shaded debug polygon chains by seeding pseudo-random RGB
    colors using polygon/surface memory addresses (r_drawflat visualization).
    """
    for i in range(model.numtextures):
        t = model.textures[i]
        if t is None:
            continue

        head_surf = t.texturechains[chain]

        # Check for legacy turbulent/water surfaces
        if _cv('r_oldwater') != 0 and head_surf is not None and (head_surf.flags & quakedef.SURF_DRAWTURB):
            s = head_surf
            while s is not None:
                if s.polys is not None:
                    p = s.polys.next
                    while p is not None:
                        # Emulate srand((unsigned int)(uintptr_t)p)
                        random.seed(id(p) & 0xFFFFFFFF)
                        gl.glColor3f(
                            random.randint(0, 255) / 255.0,
                            random.randint(0, 255) / 255.0,
                            random.randint(0, 255) / 255.0
                        )
                        r_brush.DrawGLPoly(p)
                        gl_rmain.rs_brushpasses += 1
                        p = p.next
                s = s.texturechain
        else:
            s = head_surf
            while s is not None:
                if s.polys is not None:
                    # Emulate srand((unsigned int)(uintptr_t)s->polys)
                    random.seed(id(s.polys) & 0xFFFFFFFF)
                    gl.glColor3f(
                        random.randint(0, 255) / 255.0,
                        random.randint(0, 255) / 255.0,
                        random.randint(0, 255) / 255.0
                    )
                    r_brush.DrawGLPoly(s.polys)
                    gl_rmain.rs_brushpasses += 1
                s = s.texturechain

    # Reset draw state color and frame random seed
    gl.glColor3f(1.0, 1.0, 1.0)
    random.seed(int(cl_main.cl.time * 1000) & 0xFFFFFFFF)

def R_DrawTextureChains_Glow(model: quakedef.qmodel_t, ent: render.entity_t | None, chain: int) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_Glow (qmodel_t *model, entity_t *ent, texchain_t chain)

    Renders fullbright/glow texture passes for brush models and world surfaces.
    Lazy-binds the animated fullbright gltexture only when valid chain surfaces exist.
    """
    frame_num = ent.frame if ent is not None else 0

    for i in range(model.numtextures):
        t = model.textures[i]
        if t is None:
            continue

        head_surf = t.texturechains[chain]
        if head_surf is None:
            continue

        # Fetch animated texture frame and check for associated fullbright gltexture
        anim_tex = r_brush.R_TextureAnimation(t, frame_num)
        if anim_tex is None or anim_tex.fullbright is None:
            continue

        glt = anim_tex.fullbright
        bound: bool = False

        s = head_surf
        while s is not None:
            # Lazy bind texture on first actual surface pass
            if not bound:
                gl_texmgr.GL_Bind(glt)
                bound = True

            if s.polys is not None:
                r_brush.DrawGLPoly(s.polys)
                gl_rmain.rs_brushpasses += 1

            s = s.texturechain

def R_NumTriangleIndicesForSurf(s: quakedef.msurface_t) -> int:
    return 3 * ( s.numedges - 2 )


def R_TriangleIndicesForSurf(s: quakedef.msurface_t, dest: list[int] | None = None) -> list[int]:
    indices: list[int] = []
    base_vert = s.vbo_firstvert

    for i in range(2, s.numedges):
        v0 = base_vert
        v1 = base_vert + i - 1
        v2 = base_vert + i

        indices.extend([v0, v1, v2])

        if dest is not None:
            dest.extend([v0, v1, v2])

    return indices


def R_ClearBatch():
    global num_vbo_indices
    num_vbo_indices = 0


def R_FlushBatch():
    global num_vbo_indices
    if num_vbo_indices > 0:
        gl.glDrawElements(gl.GL_TRIANGLES, num_vbo_indices, gl.GL_UNSIGNED_INT, vbo_indices)
        num_vbo_indices = 0





def R_BatchSurface(s: quakedef.msurface_t) -> None:
    """
    C equivalent (r_brush.c):
    static void R_BatchSurface (msurface_t *s)

    Accumulates surface triangle fan indices into the global VBO index batch buffer (vbo_indices).
    Flushes the batch via R_FlushBatch() if adding the surface exceeds MAX_BATCH_SIZE.
    """
    global num_vbo_indices

    num_surf_indices = R_NumTriangleIndicesForSurf(s)

    if num_surf_indices <= 0:
        # Bad numedges or degenerate surface
        return

    # Check if index buffer capacity would be exceeded
    if num_vbo_indices + num_surf_indices > MAX_BATCH_SIZE:
        R_FlushBatch()

    # Write the triangle-fan indices at the current offset (C: dest = vbo_indices + num_vbo_indices)
    base = s.vbo_firstvert
    k = num_vbo_indices
    for i in range(2, s.numedges):
        vbo_indices[k]     = base
        vbo_indices[k + 1] = base + i - 1
        vbo_indices[k + 2] = base + i
        k += 3

    num_vbo_indices = k




def R_DrawTextureChains_Multitexture(
    model: quakedef.qmodel_t,
    ent: render.entity_t | None,
    chain: int
) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_Multitexture (qmodel_t *model, entity_t *ent, texchain_t chain)

    Renders world and brush surfaces using two hardware multitexture units:
      - Unit 0 (GL_TEXTURE0_ARB): Animated base diffuse texture map
      - Unit 1 (GL_TEXTURE1_ARB): Dynamic lightmap surface texture atlas

    Handles SURF_DRAWFENCE alpha testing transitions and VERTEXSIZE stride offsets.
    """
    frame_num = ent.frame if ent is not None else 0

    for i in range(model.numtextures):
        t = model.textures[i]

        # 1. Skip null textures, empty chains, or non-multitextured surface types
        if (t is None or
            t.texturechains[chain] is None or
            (t.texturechains[chain].flags & (quakedef.SURF_DRAWTURB | quakedef.SURF_DRAWTILED | quakedef.SURF_NOTEXTURE))):
            continue

        bound: bool = False
        s = t.texturechains[chain]

        while s is not None:
            # 2. Lazy-bind base diffuse texture and enable multitexturing (Unit 1) on first valid surface
            if not bound:
                anim_tex = r_brush.R_TextureAnimation(t, frame_num)
                gl_texmgr.GL_Bind(anim_tex.gltexture)

                # Enable alpha testing for fence/cutout textures
                if t.texturechains[chain].flags & quakedef.SURF_DRAWFENCE:
                    gl.glEnable(gl.GL_ALPHA_TEST)

                # Selects GL_TEXTURE1_ARB and enables GL_TEXTURE_2D
                gl_texmgr.GL_EnableMultitexture()
                bound = True

            # 3. Bind surface dynamic lightmap texture on Unit 1
            gl_texmgr.GL_Bind(r_brush.lightmaps[s.lightmaptexturenum].texture)

            # 4. Render surface polygon vertices with dual texture coordinates
            if s.polys is not None:
                gl.glBegin(gl.GL_POLYGON)

                # Iterate through poly vertex array using VERTEXSIZE stride (7 floats per vertex)
                # v[0..2] = Position (X, Y, Z)
                # v[3..4] = Base Texture UV (S, T)
                # v[5..6] = Lightmap UV (S, T)
                for v in s.polys.verts[:s.polys.numverts]:
                    # v[0..2] position, v[3..4] texture ST, v[5..6] lightmap ST
                    gl.glMultiTexCoord2f(gl.GL_TEXTURE0, v[3], v[4])
                    gl.glMultiTexCoord2f(gl.GL_TEXTURE1, v[5], v[6])
                    gl.glVertex3f(v[0], v[1], v[2])

                gl.glEnd()
                gl_rmain.rs_brushpasses += 1

            s = s.texturechain

        # 5. Disable Multitexturing (resets active unit to GL_TEXTURE0_ARB)
        gl_texmgr.GL_DisableMultitexture()

        # Restore state if fence alpha testing was flipped on for this texture
        if bound and (t.texturechains[chain].flags & quakedef.SURF_DRAWFENCE):
            gl.glDisable(gl.GL_ALPHA_TEST)




def R_DrawTextureChains_NoTexture(model: quakedef.qmodel_t, chain: int) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_NoTexture (qmodel_t *model, texchain_t chain)

    Renders surfaces flagged with SURF_NOTEXTURE (e.g. missing textures or placeholder materials).
    Lazy-binds the base model gltexture handle only when matching surfaces exist in the chain.
    """
    for i in range(model.numtextures):
        t = model.textures[i]

        # 1. Skip null textures, empty chains, or surfaces without SURF_NOTEXTURE
        if (t is None or
            t.texturechains[chain] is None or
            not (t.texturechains[chain].flags & quakedef.SURF_NOTEXTURE)):
            continue

        bound: bool = False
        s = t.texturechains[chain]

        while s is not None:
            # 2. Lazy bind base texture handle on first valid surface pass
            if not bound:
                gl_texmgr.GL_Bind(t.gltexture)
                bound = True

            # 3. Render surface polygon
            if s.polys is not None:
                r_brush.DrawGLPoly(s.polys)
                gl_rmain.rs_brushpasses += 1

            s = s.texturechain


def R_DrawTextureChains_TextureOnly(
    model: quakedef.qmodel_t,
    ent: render.entity_t | None,
    chain: int
) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_TextureOnly (qmodel_t *model, entity_t *ent, texchain_t chain)

    Renders diffuse texture passes for brush models and world surfaces, skipping
    lightmapping calculations. Filters out turbulent (water/lava) and sky surfaces,
    and handles SURF_DRAWFENCE alpha-test state toggles.
    """
    frame_num = ent.frame if ent is not None else 0

    for i in range(model.numtextures):
        t = model.textures[i]

        # 1. Skip null textures, empty chains, or water/sky surfaces
        if (t is None or
            t.texturechains[chain] is None or
            (t.texturechains[chain].flags & (quakedef.SURF_DRAWTURB | quakedef.SURF_DRAWSKY))):
            continue

        bound: bool = False
        s = t.texturechains[chain]

        while s is not None:
            # 2. Lazy bind animated texture handle & handle alpha test state
            if not bound:
                anim_tex = r_brush.R_TextureAnimation(t, frame_num)
                gl_texmgr.GL_Bind(anim_tex.gltexture)

                # Enable alpha testing for cutout/fence textures
                if t.texturechains[chain].flags & quakedef.SURF_DRAWFENCE:
                    gl.glEnable(gl.GL_ALPHA_TEST)

                bound = True

            # 3. Draw polygon
            if s.polys is not None:
                r_brush.DrawGLPoly(s.polys)
                gl_rmain.rs_brushpasses += 1

            s = s.texturechain

        # 4. Restore state if alpha testing was enabled for this chain
        if bound and (t.texturechains[chain].flags & quakedef.SURF_DRAWFENCE):
            gl.glDisable(gl.GL_ALPHA_TEST)


def GL_WaterAlphaForEntitySurface(ent: render.entity_t, s: quakedef.msurface_t) -> float:
    entalpha = 0.0
    if ent is None or ent.alpha == protocol.ENTALPHA_DEFAULT:
        entalpha = gl_rmisc.GL_WaterAlphaForSurface(s)
    else:
        entalpha = protocol.ENTALPHA_DECODE(ent.alpha)

    return entalpha



def R_DrawTextureChains_Water(
    model: quakedef.qmodel_t,
    ent: render.entity_t | None,
    chain: int
) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_Water (qmodel_t *model, entity_t *ent, texchain_t chain)

    Renders turbulent water, lava, and slime surfaces. Handles CPU-generated warp
    polygons, lit shader water with lightmap batching, and standard unlit water paths.
    """
    # 1. Early out on flat-shading / lightmap-only cheat modes
    if gl_rmain.r_drawflat_cheatsafe or gl_rmain.r_lightmap_cheatsafe:
        return

    has_lit_water: bool = False
    has_unlit_water: bool = False

    # -------------------------------------------------------------------------
    # Path 1: Legacy CPU-based water warping (r_oldwater)
    # -------------------------------------------------------------------------
    if _cv('r_oldwater'):
        for i in range(model.numtextures):
            t = model.textures[i]
            if (t is None or
                t.texturechains[chain] is None or
                not (t.texturechains[chain].flags & quakedef.SURF_DRAWTURB)):
                continue

            bound: bool = False
            entalpha: float = 1.0

            s = t.texturechains[chain]
            while s is not None:
                if not bound:
                    entalpha = GL_WaterAlphaForEntitySurface(ent, s)
                    R_BeginTransparentDrawing(entalpha)
                    gl_texmgr.GL_Bind(t.gltexture)
                    bound = True

                # Traverse subdivided water polygon chain
                if s.polys is not None:
                    p = s.polys.next
                    while p is not None:
                        gl_warp.DrawWaterPoly(p)
                        gl_rmain.rs_brushpasses += 1
                        p = p.next

                s = s.texturechain

            if bound:
                R_EndTransparentDrawing(entalpha)

    # -------------------------------------------------------------------------
    # Path 2: Shader-based lit water (VBO + glsl shader program)
    # -------------------------------------------------------------------------
    elif (cl_main.cl.worldmodel is not None and
          cl_main.cl.worldmodel.haslitwater and
          _cv('r_litwater') and
          r_world_program != 0):

        overbright = 1 if _cv('gl_overbright') else 0
        wide10bits = 1 if _cv('r_lightmapwide') else 0

        has_lit_water = True

        gl.glUseProgram(r_world_program)

        # Bind VBO buffers and setup vertex attribute pointers
        gl_rmisc.GL_BindBuffer(gl.GL_ARRAY_BUFFER, r_brush.gl_bmodel_vbo)
        gl_rmisc.GL_BindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

        gl.glEnableVertexAttribArray(vertAttrIndex)
        gl.glEnableVertexAttribArray(texCoordsAttrIndex)
        gl.glEnableVertexAttribArray(LMCoordsAttrIndex)

        float_size = ctypes.sizeof(ctypes.c_float)
        stride = gl_model.VERTEXSIZE * float_size

        gl.glVertexAttribPointer(
            vertAttrIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0)
        )
        gl.glVertexAttribPointer(
            texCoordsAttrIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(3 * float_size)
        )
        gl.glVertexAttribPointer(
            LMCoordsAttrIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(5 * float_size)
        )

        # Set uniform constants
        gl.glUniform1i(texLoc, 0)
        gl.glUniform1i(LMTexLoc, 1)
        gl.glUniform1i(fullbrightTexLoc, 2)
        gl.glUniform1i(useFullbrightTexLoc, 0)
        gl.glUniform1i(useOverbrightLoc, overbright)
        gl.glUniform1i(useAlphaTestLoc, 0)
        gl.glUniform1i(useLightmapWideLoc, wide10bits)
        gl.glUniform1i(useLightmapOnlyLoc, 0)

        for i in range(model.numtextures):
            t = model.textures[i]
            if (t is None or
                t.texturechains[chain] is None or
                not (t.texturechains[chain].flags & quakedef.SURF_DRAWTURB)):
                continue

            # TEX_SPECIAL surfaces (sky, non-lit liquid) deferred to unlit pass
            if t.texturechains[chain].texinfo.flags & gl_model.TEX_SPECIAL:
                has_unlit_water = True
                continue

            bound = False
            entalpha = 1.0
            lastlightmap = 0

            s = t.texturechains[chain]
            while s is not None:
                if not bound:
                    entalpha = GL_WaterAlphaForEntitySurface(ent, s)
                    if entalpha < 1.0:
                        gl.glUniform1f(alphaLoc, entalpha)
                        R_BeginTransparentDrawing(entalpha)

                    gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE0)
                    gl_texmgr.GL_Bind(t.warpimage)

                    if model != cl_main.cl.worldmodel:
                        t.update_warp = True

                    bound = True
                    lastlightmap = s.lightmaptexturenum

                # Flush batch if lightmap texture ID changes
                if s.lightmaptexturenum != lastlightmap:
                    R_FlushBatch()

                gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE1)
                gl_texmgr.GL_Bind(r_brush.lightmaps[s.lightmaptexturenum].texture)
                lastlightmap = s.lightmaptexturenum

                R_BatchSurface(s)
                gl_rmain.rs_brushpasses += 1

                s = s.texturechain

            R_FlushBatch()
            if bound:
                R_EndTransparentDrawing(entalpha)

        # Cleanup GL state
        gl.glDisableVertexAttribArray(vertAttrIndex)
        gl.glDisableVertexAttribArray(texCoordsAttrIndex)
        gl.glDisableVertexAttribArray(LMCoordsAttrIndex)
        gl.glUseProgram(0)
        gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE0)

    else:
        has_unlit_water = True

    # -------------------------------------------------------------------------
    # Path 3: Unlit water (fallback or TEX_SPECIAL water surfaces)
    # -------------------------------------------------------------------------
    if has_unlit_water:
        for i in range(model.numtextures):
            t = model.textures[i]
            if (t is None or
                t.texturechains[chain] is None or
                not (t.texturechains[chain].flags & quakedef.SURF_DRAWTURB)):
                continue

            if has_lit_water and not (t.texturechains[chain].texinfo.flags & gl_model.TEX_SPECIAL):
                continue

            bound = False
            entalpha = 1.0

            s = t.texturechains[chain]
            while s is not None:
                if not bound:
                    entalpha = GL_WaterAlphaForEntitySurface(ent, s)
                    R_BeginTransparentDrawing(entalpha)
                    gl_texmgr.GL_Bind(t.warpimage)

                    if model != cl_main.cl.worldmodel:
                        t.update_warp = True

                    bound = True

                if s.polys is not None:
                    r_brush.DrawGLPoly(s.polys)
                    gl_rmain.rs_brushpasses += 1

                s = s.texturechain

            if bound:
                R_EndTransparentDrawing(entalpha)




def R_DrawTextureChains_White(model: quakedef.qmodel_t, chain: int) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_White (qmodel_t *model, texchain_t chain)

    Renders flat white polygons for SURF_DRAWTILED surface chains without 2D texturing.
    Disables GL_TEXTURE_2D during iteration and re-enables it upon completion.
    """
    gl.glDisable(gl.GL_TEXTURE_2D)

    for i in range(model.numtextures):
        t = model.textures[i]

        # 1. Skip null textures, empty chains, or surfaces without SURF_DRAWTILED
        if (t is None or
            t.texturechains[chain] is None or
            not (t.texturechains[chain].flags & quakedef.SURF_DRAWTILED)):
            continue

        # 2. Render untextured polygons in the chain
        s = t.texturechains[chain]
        while s is not None:
            if s.polys is not None:
                r_brush.DrawGLPoly(s.polys)
                gl_rmain.rs_brushpasses += 1

            s = s.texturechain

    gl.glEnable(gl.GL_TEXTURE_2D)



def R_DrawLightmapChains() -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawLightmapChains (void)

    Renders lightmaps over geometry using immediate mode (GL_POLYGON).
    Binds each lightmap texture and draws all attached surface polygons
    using lightmap UV coordinates stored at offsets 5 and 6 in vertex data.
    """
    for i in range(r_brush.lightmap_count):
        # 1. Skip lightmap sheets that have no attached polygons
        if not r_brush.lightmaps[i].polys:
            continue

        # 2. Bind current lightmap texture
        gl_texmgr.GL_Bind(r_brush.lightmaps[i].texture)

        # 3. Traverse polygon chain linked to this lightmap
        p = r_brush.lightmaps[i].polys
        while p is not None:
            gl.glBegin(gl.GL_POLYGON)

            # Draw polygon vertices using lightmap ST (v[5], v[6]) and Position (v[0..2])
            for v in p.verts[:p.numverts]:
                gl.glTexCoord2f(v[5], v[6])
                gl.glVertex3f(v[0], v[1], v[2])

            gl.glEnd()
            gl_rmain.rs_brushpasses += 1

            p = p.chain



def GLWorld_CreateShaders():
    global texLoc
    global LMTexLoc
    global fullbrightTexLoc
    global useFullbrightTexLoc
    global useOverbrightLoc
    global useAlphaTestLoc
    global useLightmapWideLoc
    global useLightmapOnlyLoc
    global alphaLoc

    global r_world_program

    bindings : list[glquake.glsl_attrib_binding_t] = [
        glquake.glsl_attrib_binding_t('Vert', vertAttrIndex),
        glquake.glsl_attrib_binding_t('TexCoords', texCoordsAttrIndex),
        glquake.glsl_attrib_binding_t('LMCoords', LMCoordsAttrIndex),
    ]

    vertSource = '''#version 110
    attribute vec4 Vert;
    attribute vec2 TexCoords;
    attribute vec2 LMCoords;

    varying float FogFragCoord;

    void main()
    {
       gl_TexCoord[0] = vec4(TexCoords, 0.0, 0.0);
       gl_TexCoord[1] = vec4(LMCoords, 0.0, 0.0);
       gl_Position = gl_ModelViewProjectionMatrix * Vert;
       FogFragCoord = gl_Position.w;
    }'''

    fragSource = '''#version 110
    uniform sampler2D Tex;
    uniform sampler2D LMTex;
    uniform sampler2D FullbrightTex;
    uniform bool UseFullbrightTex;
    uniform bool UseOverbright;
    uniform bool UseAlphaTest;
    uniform bool UseLightmapWide;
    uniform bool UseLightmapOnly;
    uniform float Alpha;

    varying float FogFragCoord;

    void main()
    {
       vec4 result = texture2D(Tex, gl_TexCoord[0].xy);
       if (UseLightmapOnly)
           result = vec4(0.5, 0.5, 0.5, 1.0);
       if (UseAlphaTest && (result.a < 0.666))
           discard;
       result *= texture2D(LMTex, gl_TexCoord[1].xy);
       if (UseLightmapWide)
           result.rgb *= 4.0;
       if (UseOverbright)
           result.rgb *= 2.0;
       if (UseFullbrightTex)
           result += texture2D(FullbrightTex, gl_TexCoord[0].xy);
       result = clamp(result, 0.0, 1.0);
       float fog = exp(-gl_Fog.density * gl_Fog.density * FogFragCoord * FogFragCoord);
       fog = clamp(fog, 0.0, 1.0);
       result = mix(gl_Fog.color, result, fog);
       result.a = Alpha; // FIXME: This will make almost transparent things cut holes though heavy fog
       gl_FragColor = result;
    }'''

    if not gl_vidsdl.gl_glsl_alias_able:
        return

    r_world_program = gl_rmisc.GL_CreateProgram(vertSource, fragSource, len(bindings), bindings)

    if r_world_program != 0:
        texLoc              = gl_rmisc.GL_GetUniformLocation(r_world_program, "Tex")
        LMTexLoc            = gl_rmisc.GL_GetUniformLocation (r_world_program, "LMTex")
        fullbrightTexLoc    = gl_rmisc.GL_GetUniformLocation (r_world_program, "FullbrightTex")
        useFullbrightTexLoc = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseFullbrightTex")
        useOverbrightLoc    = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseOverbright")
        useAlphaTestLoc     = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseAlphaTest")
        useLightmapWideLoc  = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseLightmapWide")
        useLightmapOnlyLoc  = gl_rmisc.GL_GetUniformLocation (r_world_program, "UseLightmapOnly")
        alphaLoc            = gl_rmisc.GL_GetUniformLocation (r_world_program, "Alpha")



def R_DrawTextureChains_GLSL(
    model: quakedef.qmodel_t,
    ent: render.entity_t | None,
    chain: int
) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains_GLSL (qmodel_t *model, entity_t *ent, texchain_t chain)

    Renders brush model surface chains using GLSL shader program ('r_world_program')
    and hardware VBOs. Handles lightmap batching, dynamic texture animation,
    fullbright overlays, entity transparency, and fence alpha testing.
    """
    entalpha: float = (
        protocol.ENTALPHA_DECODE(ent.alpha) if ent is not None else 1.0
    )
    overbright: int = 1 if _cv('gl_overbright') else 0
    wide10bits: int = 1 if _cv('r_lightmapwide') else 0

    # 1. Enable blending and disable depth writes for entity transparency
    if entalpha < 1.0:
        gl.glDepthMask(gl.GL_FALSE)
        gl.glEnable(gl.GL_BLEND)

    gl.glUseProgram(r_world_program)

    # 2. Bind model VBO buffer and index array (indices come from client memory)
    gl_rmisc.GL_BindBuffer(gl.GL_ARRAY_BUFFER, r_brush.gl_bmodel_vbo)
    gl_rmisc.GL_BindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

    # 3. Setup vertex attribute pointers from VBO
    gl.glEnableVertexAttribArray(vertAttrIndex)
    gl.glEnableVertexAttribArray(texCoordsAttrIndex)
    gl.glEnableVertexAttribArray(LMCoordsAttrIndex)

    float_size = ctypes.sizeof(ctypes.c_float)
    stride = gl_model.VERTEXSIZE * float_size

    gl.glVertexAttribPointer(
        vertAttrIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0)
    )
    gl.glVertexAttribPointer(
        texCoordsAttrIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(3 * float_size)
    )
    gl.glVertexAttribPointer(
        LMCoordsAttrIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(5 * float_size)
    )

    # 4. Set shader uniforms
    gl.glUniform1i(texLoc, 0)
    gl.glUniform1i(LMTexLoc, 1)
    gl.glUniform1i(fullbrightTexLoc, 2)
    gl.glUniform1i(useFullbrightTexLoc, 0)
    gl.glUniform1i(useOverbrightLoc, overbright)
    gl.glUniform1i(useAlphaTestLoc, 0)
    gl.glUniform1i(useLightmapWideLoc, wide10bits)
    gl.glUniform1i(useLightmapOnlyLoc, 0)
    gl.glUniform1f(alphaLoc, entalpha)

    # 5. Render textures and surface chains
    frame = ent.frame if ent is not None else 0

    for i in range(model.numtextures):
        t = model.textures[i]

        if (t is None or
            t.texturechains[chain] is None or
            (t.texturechains[chain].flags & (quakedef.SURF_DRAWTURB | quakedef.SURF_DRAWTILED | quakedef.SURF_NOTEXTURE))):
            continue

        # Check fullbright texture overlay on TMU 2
        anim_tex = r_brush.R_TextureAnimation(t, frame)
        fullbright = anim_tex.fullbright if anim_tex is not None else None

        if _cv('gl_fullbrights') and fullbright is not None:
            gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE2)
            gl_texmgr.GL_Bind(fullbright)
            gl.glUniform1i(useFullbrightTexLoc, 1)
        else:
            gl.glUniform1i(useFullbrightTexLoc, 0)

        R_ClearBatch()

        bound: bool = False
        lastlightmap: int = 0

        s = t.texturechains[chain]
        while s is not None:
            if not bound:
                gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE0)
                gl_texmgr.GL_Bind(anim_tex.gltexture)

                # Enable GLSL alpha test uniform for SURF_DRAWFENCE
                if t.texturechains[chain].flags & quakedef.SURF_DRAWFENCE:
                    gl.glUniform1i(useAlphaTestLoc, 1)

                bound = True
                lastlightmap = s.lightmaptexturenum

            # Flush batch if lightmap texture ID changes across surfaces
            if s.lightmaptexturenum != lastlightmap:
                R_FlushBatch()

            gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE1)
            gl_texmgr.GL_Bind(r_brush.lightmaps[s.lightmaptexturenum].texture)
            lastlightmap = s.lightmaptexturenum

            R_BatchSurface(s)
            gl_rmain.rs_brushpasses += 1

            s = s.texturechain

        R_FlushBatch()

        # Disable alpha test uniform after finishing fence chain
        if bound and (t.texturechains[chain].flags & quakedef.SURF_DRAWFENCE):
            gl.glUniform1i(useAlphaTestLoc, 0)

    # 6. Cleanup GL state
    gl.glDisableVertexAttribArray(vertAttrIndex)
    gl.glDisableVertexAttribArray(texCoordsAttrIndex)
    gl.glDisableVertexAttribArray(LMCoordsAttrIndex)

    gl.glUseProgram(0)
    gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE0)

    if entalpha < 1.0:
        gl.glDepthMask(gl.GL_TRUE)
        gl.glDisable(gl.GL_BLEND)





def R_DrawLightmapChains_GLSL(
    model: quakedef.qmodel_t,
    ent: render.entity_t | None,
    chain: int
) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawLightmapChains_GLSL (qmodel_t *model, entity_t *ent, texchain_t chain)

    Renders lightmaps-only using GLSL shader program ('r_world_program') and hardware VBOs.
    Ignores base diffuse textures and streams lightmap textures bound to GL_TEXTURE1.
    """
    overbright: int = 1 if _cv('gl_overbright') else 0
    wide10bits: int = 1 if _cv('r_lightmapwide') else 0

    gl.glUseProgram(r_world_program)

    # 1. Bind buffers
    gl_rmisc.GL_BindBuffer(gl.GL_ARRAY_BUFFER, r_brush.gl_bmodel_vbo)
    gl_rmisc.GL_BindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)  # Indices come from client memory

    # 2. Enable vertex attributes
    gl.glEnableVertexAttribArray(vertAttrIndex)
    gl.glEnableVertexAttribArray(texCoordsAttrIndex)
    gl.glEnableVertexAttribArray(LMCoordsAttrIndex)

    float_size = ctypes.sizeof(ctypes.c_float)
    stride = gl_model.VERTEXSIZE * float_size

    gl.glVertexAttribPointer(
        vertAttrIndex, 3, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(0)
    )
    gl.glVertexAttribPointer(
        texCoordsAttrIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(3 * float_size)
    )
    gl.glVertexAttribPointer(
        LMCoordsAttrIndex, 2, gl.GL_FLOAT, gl.GL_FALSE, stride, ctypes.c_void_p(5 * float_size)
    )

    # 3. Set uniforms (useLightmapOnlyLoc set to 1)
    gl.glUniform1i(texLoc, 0)
    gl.glUniform1i(LMTexLoc, 1)
    gl.glUniform1i(fullbrightTexLoc, 2)
    gl.glUniform1i(useFullbrightTexLoc, 0)
    gl.glUniform1i(useOverbrightLoc, overbright)
    gl.glUniform1i(useAlphaTestLoc, 0)
    gl.glUniform1i(useLightmapWideLoc, wide10bits)
    gl.glUniform1f(alphaLoc, 1.0)
    gl.glUniform1i(useFullbrightTexLoc, 0)
    gl.glUniform1i(useLightmapOnlyLoc, 1)

    R_ClearBatch()
    lastlightmap: int = -1

    # 4. Iterate model textures and render lightmapped surfaces
    for i in range(model.numtextures):
        t = model.textures[i]

        if (t is None or
            t.texturechains[chain] is None or
            (t.texturechains[chain].flags & (quakedef.SURF_DRAWTILED | quakedef.SURF_NOTEXTURE))):
            continue

        # Skip unlit water surfaces
        if t.texturechains[chain].texinfo.flags & gl_model.TEX_SPECIAL:
            continue

        s = t.texturechains[chain]
        while s is not None:
            if s.lightmaptexturenum < 0:
                s = s.texturechain
                continue

            # Flush batch and bind new lightmap texture if sheet ID changes
            if s.lightmaptexturenum != lastlightmap:
                R_FlushBatch()

                gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE1)
                gl_texmgr.GL_Bind(r_brush.lightmaps[s.lightmaptexturenum].texture)
                lastlightmap = s.lightmaptexturenum

            R_BatchSurface(s)
            gl_rmain.rs_brushpasses += 1

            s = s.texturechain

    R_FlushBatch()

    # 5. Clean up GL state
    gl.glDisableVertexAttribArray(vertAttrIndex)
    gl.glDisableVertexAttribArray(texCoordsAttrIndex)
    gl.glDisableVertexAttribArray(LMCoordsAttrIndex)

    gl.glUseProgram(0)
    gl_texmgr.GL_SelectTexture(gl.GL_TEXTURE0)


def R_DrawTextureChains(
    model: quakedef.qmodel_t,
    ent: render.entity_t | None,
    chain: int
) -> None:
    """
    C equivalent (r_brush.c):
    void R_DrawTextureChains (qmodel_t *model, entity_t *ent, texchain_t chain)

    Main dispatch routine for rendering brush model texture chains.
    Handles cheat modes, GLSL programmable pipeline, fixed-function multitexture/multipass,
    and additive fullbright glow passes.
    """
    entalpha: float = (
        protocol.ENTALPHA_DECODE(ent.alpha) if ent is not None else 1.0
    )

    # Always upload dirty lightmaps before drawing surface chains
    r_brush.R_UploadLightmaps()

    # 1. Cheat mode: Flat shaded surfaces
    if gl_rmain.r_drawflat_cheatsafe:
        gl.glDisable(gl.GL_TEXTURE_2D)
        R_DrawTextureChains_Drawflat(model, chain)
        gl.glEnable(gl.GL_TEXTURE_2D)
        return

    # 2. Cheat mode: Fullbright / unlit textures
    if gl_rmain.r_fullbright_cheatsafe:
        R_BeginTransparentDrawing(entalpha)
        R_DrawTextureChains_TextureOnly(model, ent, chain)
        R_EndTransparentDrawing(entalpha)
        _draw_fullbrights(model, ent, chain, entalpha)
        return

    # 3. Cheat mode: Lightmaps only
    if gl_rmain.r_lightmap_cheatsafe:
        if r_world_program != 0:
            R_DrawLightmapChains_GLSL(model, ent, chain)
            return

        if not _cv('gl_overbright'):
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
            gl.glColor3f(0.5, 0.5, 0.5)

        R_DrawLightmapChains()

        if not _cv('gl_overbright'):
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)

        R_DrawTextureChains_White(model, chain)
        return

    # 4. Standard Rendering Pipelines
    R_BeginTransparentDrawing(entalpha)

    R_DrawTextureChains_NoTexture(model, chain)

    # OpenGL 2 GLSL fast path
    if r_world_program != 0:
        R_EndTransparentDrawing(entalpha)
        R_DrawTextureChains_GLSL(model, ent, chain)
        _draw_fullbrights(model, ent, chain, entalpha)
        return

    # Fixed-Function / Legacy Rendering Paths
    if _cv('gl_overbright'):
        if gl_vidsdl.gl_texture_env_combine and gl_vidsdl.gl_mtexable:
            # Case 1: Overbright via GL_COMBINE / Multitexture in 1 pass
            gl_texmgr.GL_EnableMultitexture()
            gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_COMBINE_EXT)
            gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_COMBINE_RGB_EXT, gl.GL_MODULATE)
            gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_SOURCE0_RGB_EXT, gl.GL_PREVIOUS_EXT)
            gl.glTexEnvi(gl.GL_TEXTURE_ENV, gl.GL_SOURCE1_RGB_EXT, gl.GL_TEXTURE)
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_RGB_SCALE_EXT, 2.0)
            gl_texmgr.GL_DisableMultitexture()

            R_DrawTextureChains_Multitexture(model, ent, chain)

            gl_texmgr.GL_EnableMultitexture()
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_RGB_SCALE_EXT, 1.0)
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
            gl_texmgr.GL_DisableMultitexture()
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)

        elif entalpha < 1.0:
            # Case 2: Entity has alpha (cannot do multi-pass)
            R_DrawTextureChains_TextureOnly(model, ent, chain)

        else:
            # Case 3: 2x Modulation multi-pass overbright with fog handling
            gl_fog.Fog_DisableGFog()
            R_DrawTextureChains_TextureOnly(model, ent, chain)
            gl_fog.Fog_EnableGFog()

            gl.glDepthMask(gl.GL_FALSE)
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_DST_COLOR, gl.GL_SRC_COLOR)  # 2x modulate

            gl_fog.Fog_StartAdditive()
            R_DrawLightmapChains()
            gl_fog.Fog_StopAdditive()

            if gl_fog.Fog_GetDensity() > 0:
                gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE)  # Additive fog pass
                gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
                gl.glColor3f(0.0, 0.0, 0.0)
                R_DrawTextureChains_TextureOnly(model, ent, chain)
                gl.glColor3f(1.0, 1.0, 1.0)
                gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)

            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            gl.glDisable(gl.GL_BLEND)
            gl.glDepthMask(gl.GL_TRUE)

    else:
        if gl_vidsdl.gl_mtexable:
            # Case 4: Standard Multitexture modulation
            gl_texmgr.GL_EnableMultitexture()
            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
            gl_texmgr.GL_DisableMultitexture()

            R_DrawTextureChains_Multitexture(model, ent, chain)

            gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)

        elif entalpha < 1.0:
            # Case 5: Entity has alpha (cannot do multi-pass)
            R_DrawTextureChains_TextureOnly(model, ent, chain)

        else:
            # Case 6: Standard multi-pass lightmap modulation with fog handling
            gl_fog.Fog_DisableGFog()
            R_DrawTextureChains_TextureOnly(model, ent, chain)
            gl_fog.Fog_EnableGFog()

            gl.glDepthMask(gl.GL_FALSE)
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_ZERO, gl.GL_SRC_COLOR)  # Modulate

            gl_fog.Fog_StartAdditive()
            R_DrawLightmapChains()
            gl_fog.Fog_StopAdditive()

            if gl_fog.Fog_GetDensity() > 0:
                gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE)  # Additive fog pass
                gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
                gl.glColor3f(0.0, 0.0, 0.0)
                R_DrawTextureChains_TextureOnly(model, ent, chain)
                gl.glColor3f(1.0, 1.0, 1.0)
                gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)

            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            gl.glDisable(gl.GL_BLEND)
            gl.glDepthMask(gl.GL_TRUE)

    R_EndTransparentDrawing(entalpha)

    # 5. Fullbright glow overlay pass
    _draw_fullbrights(model, ent, chain, entalpha)


def _draw_fullbrights(
    model: quakedef.qmodel_t,
    ent: render.entity_t | None,
    chain: int,
    entalpha: float
) -> None:
    """Helper routine executing the fullbright glow pass (C goto fullbrights target)."""
    if _cv('gl_fullbrights'):
        gl.glDepthMask(gl.GL_FALSE)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE)
        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)
        gl.glColor3f(entalpha, entalpha, entalpha)

        gl_fog.Fog_StartAdditive()
        R_DrawTextureChains_Glow(model, ent, chain)
        gl_fog.Fog_StopAdditive()

        gl.glColor3f(1.0, 1.0, 1.0)
        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDisable(gl.GL_BLEND)
        gl.glDepthMask(gl.GL_TRUE)

def R_DrawWorld():
    if not gl_rmain.r_drawworld_cheatsafe:
        return

    R_DrawTextureChains(cl_main.cl.worldmodel, None, quakedef.texchain_t.chain_world)


def R_DrawWorld_Water():
    if not gl_rmain.r_drawworld_cheatsafe:
        return

    R_DrawTextureChains_Water(cl_main.cl.worldmodel, None, quakedef.texchain_t.chain_world)

def R_DrawWorld_ShowTris():
    if not gl_rmain.r_drawworld_cheatsafe:
        return

    R_DrawTextureChains_ShowTris(cl_main.cl.worldmodel, None, quakedef.texchain_t.chain_world)

