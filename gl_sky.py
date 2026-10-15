#gl_sky.py
import math
import re

import numpy as np
import OpenGL.GL as gl

import _cmd
import cl_main
import common
import console
import cvar
import gl_fog
import gl_model
import gl_rmain
import gl_texmgr
import gl_vidsdl
import mathlib
import protocol
import quakedef
import r_brush
import render

MAX_CLIP_VERTS  = 64
BACKFACE_EPSILON = 0.01

skyflatcolor = [0, 0, 0]
#skymins = [[0, 0, 0, 0, 0, 0],[0, 0, 0, 0, 0, 0]]
#skymaxs = [[0, 0, 0, 0, 0, 0],[0, 0, 0, 0, 0, 0]]
skymins = [[99999.0] * 6 for _ in range(2)]
skymaxs = [[-99999.0] * 6 for _ in range(2)]

skybox_name = ''

skybox_textures : list[gl_texmgr.gltexture_t] = []
solidskytexture : gl_texmgr.gltexture_t = None
alphaskytexture : gl_texmgr.gltexture_t = None

skytexorder = [0,2,1,3,4,5]

skyclip = [
    [ 1,  1, 0],
    [ 1, -1, 0],
    [ 0, -1, 1],
    [ 0,  1, 1],
    [ 1,  0, 1],
    [-1,  0, 1]
]

st_to_vec = [
    [ 3, -1, 2],
    [-3,  1, 2],
    [ 1,  3, 2],
    [-1, -3, 2],
    [-2, -1, 3],   #straight up
    [ 2, -1,-3]    # straight down
]

vec_to_st = [
    [-2, 3,  1],
    [ 2, 3, -1],
    [ 1, 3,  2],
    [-1, 3, -2],
    [-2,-1, 3 ],
    [-2, 1, -3],
]

skyfog = 0.0

def Sky_LoadTexture(mod: quakedef.qmodel_t, mt: quakedef.texture_t, pixels: bytes = None):
    """Split a 256x128 sky miptex into its two 128x128 layers and upload them as RGBA.

    pixels: the raw 8-bit mip 0 data of the miptex (width*height bytes).
    Back (solid) layer is the right half, front (cloud) layer the left half; index 0 in the
    front layer is transparent.  Also computes the r_fastsky average colour.
    """
    global solidskytexture, alphaskytexture, skyflatcolor

    if pixels is None:
        pixels = getattr(mt, 'data', None)
    if pixels is None:
        console.Con_Warning(f'Sky_LoadTexture: no pixel data for {mt.name}\n')
        return

    if mt.width != 256 or mt.height != 128:
        console.Con_Warning(
            f"Sky texture {mt.name} is {mt.width} x {mt.height}, expected 256 x 128\n"
        )
        if mt.width < 2 or mt.height < 1:
            return

    w = mt.width
    h = mt.height
    halfwidth = w // 2

    arr = np.frombuffer(bytes(pixels[:w * h]), dtype=np.uint8).reshape(h, w)
    palette = np.frombuffer(gl_texmgr.d_8to24table, dtype=np.uint8).reshape(256, 4)

    back_idx = np.ascontiguousarray(arr[:, halfwidth:halfwidth * 2])
    front_idx = np.ascontiguousarray(arr[:, :halfwidth])

    back_rgba = palette[back_idx].copy()
    back_rgba[..., 3] = 255
    back_bytes = back_rgba.tobytes()

    solidskytexture = gl_texmgr.TexMgr_LoadImage(
        mod, f"{mod.name}:{mt.name}_back", halfwidth, h,
        gl_texmgr.srcformat.SRC_RGBA, back_bytes, "", back_bytes,
        gl_texmgr.TEXPREF_NONE)

    opaque = front_idx != 0
    front_rgba = palette[front_idx].copy()
    front_rgba[..., 3] = np.where(opaque, 255, 0)
    front_bytes = front_rgba.tobytes()

    alphaskytexture = gl_texmgr.TexMgr_LoadImage(
        mod, f"{mod.name}:{mt.name}_front", halfwidth, h,
        gl_texmgr.srcformat.SRC_RGBA, front_bytes, "", front_bytes,
        gl_texmgr.TEXPREF_ALPHA)

    # r_fastsky colour: average of all opaque front-layer pixels
    count = int(opaque.sum())
    if count > 0:
        rgb = palette[front_idx[opaque]][:, :3].astype(np.float64).sum(axis=0)
        skyflatcolor[0] = float(rgb[0]) / (count * 255)
        skyflatcolor[1] = float(rgb[1]) / (count * 255)
        skyflatcolor[2] = float(rgb[2]) / (count * 255)
    else:
        skyflatcolor[0] = skyflatcolor[1] = skyflatcolor[2] = 0.0


suf:list[str] = ["rt", "bk", "lf", "ft", "up", "dn"]

def Sky_LoadSkyBox(name: str):
    global skybox_name
    if skybox_name == name:
        return

    for i in range(6):
        if skybox_textures[i] and skybox_textures[i] != gl_texmgr.notexture:
            gl_texmgr.TexMgr_FreeTexture(skybox_textures[i])
        skybox_textures[i] = None

    if not name:
        skybox_name = ''
        return

    try:
        import image
    except ImportError:
        console.Con_Printf('skybox: image module not available\n')
        skybox_name = ''
        return

    nonefound = True
    for i in range(6):
        filename = f'gfx/env/{name}{suf[i]}'
        data, width, height = image.Image_LoadImage(filename)

        if data:
            skybox_textures[i] = gl_texmgr.TexMgr_LoadImage(
                cl_main.cl.worldmodel, filename, width, height,
                gl_texmgr.srcformat.SRC_RGBA, data, filename, 0, gl_texmgr.TEXPREF_NONE)
            nonefound = False
        else:
            console.Con_Printf(f'Couldn\'t load {filename}\n')
            skybox_textures[i] = gl_texmgr.notexture

    if nonefound:
        for i in range(6):
            if skybox_textures[i] and skybox_textures[i] != gl_texmgr.notexture:
                gl_texmgr.TexMgr_FreeTexture(skybox_textures[i])
            skybox_textures[i] = None

        skybox_name = ''
        return

    skybox_name = name


def Sky_ClearAll():
    global skybox_name, solidskytexture, alphaskytexture

    skybox_name = ''
    for i in range(len(skybox_textures)):
        skybox_textures[i] = None

    solidskytexture = None
    alphaskytexture = None

    r_skyfog = cvar.Cvar_GetCvar('r_skyfog')
    cvar.Cvar_SetQuick(r_skyfog, r_skyfog.default_string)  # this may be wrong


def Sky_NewMap():
    """Read sky/skyfog keys from the worldspawn entity (first {...} block of the entities lump)."""
    global skyfog

    skyfog = cvar.Cvar_GetCvar('r_skyfog').value

    ents = cl_main.cl.worldmodel.entities
    if not ents:
        return
    if isinstance(ents, (bytes, bytearray)):
        ents = bytes(ents).decode('latin-1')

    end = ents.find('}')
    block = ents[:end] if end >= 0 else ents

    for key, value in re.findall(r'"([^"]*)"\s+"([^"]*)"', block):
        if key.startswith('_'):
            key = key[1:]

        if key in ('sky', 'skyname', 'qlsky'):
            Sky_LoadSkyBox(value)
        elif key == 'skyfog':
            try:
                skyfog = float(value)
            except ValueError:
                pass


def Sky_SkyCommand_f():
    match  _cmd.Cmd_Argc():
        case 1:
            console.Con_Printf('sky is %s' % skybox_name)
        case 2:
            Sky_LoadSkyBox(_cmd.Cmd_Argv(1))
        case _:
            console.Con_Printf('usage: sky <skyname>')



def R_SetSkyfog_f(var: cvar.cvar_t):
    global skyfog
    skyfog = var.value

def Sky_Init():
    global skybox_name
    import cvar

    r_fastsky     = {'name':"r_fastsky",    'value':  "0", 'flags': cvar.CVAR_NONE};
    r_sky_quality = {'name':"r_sky_quality",'value': "12", 'flags': cvar.CVAR_NONE};
    r_skyalpha    = {'name':"r_skyalpha",   'value':  "1", 'flags': cvar.CVAR_NONE};
    r_skyfog      = {'name':"r_skyfog",     'value':"0.5", 'flags': cvar.CVAR_NONE};

    cvar.Cvar_RegisterVariable(r_fastsky)
    cvar.Cvar_RegisterVariable(r_sky_quality)
    cvar.Cvar_RegisterVariable(r_skyalpha)
    cvar.Cvar_RegisterVariable(r_skyfog)

    import _cmd
    _cmd.Cmd_AddCommand('sky', Sky_SkyCommand_f)

    skybox_name = ''

    for i in range(6):
        skybox_textures.append(None)


def Sky_ProjectPoly(nump: int, vecs: list):
    """Projects sky world polygons onto sky box faces (0..5) to establish minimal

    S/T bounds for sky clipping and drawing.

    C equivalent:
    void Sky_ProjectPoly (int nump, vec3_t vecs) in r_brush.c / r_sky.c
    """
    global skymins, skymaxs

    # Helper function to access vertex coordinates regardless of storage format
    is_flat = len(vecs) > 0 and isinstance(vecs[0], (float, int))

    def get_vert(idx: int) -> list[float]:
        if is_flat:
            offset = idx * 3
            return [vecs[offset], vecs[offset + 1], vecs[offset + 2]]
        return vecs[idx]

    # ------------------------------------
    # 1. Decide which sky face the polygon maps to
    # ------------------------------------
    v = [0.0, 0.0, 0.0]

    for i in range(nump):
        vp = get_vert(i)
        v[0] += vp[0]
        v[1] += vp[1]
        v[2] += vp[2]

    av = [abs(v[0]), abs(v[1]), abs(v[2])]

    if av[0] > av[1] and av[0] > av[2]:
        axis = 1 if v[0] < 0 else 0
    elif av[1] > av[2] and av[1] > av[0]:
        axis = 3 if v[1] < 0 else 2
    else:
        axis = 5 if v[2] < 0 else 4

    # ------------------------------------
    # 2. Project new texture coordinates (S, T) and accumulate min/max bounds
    # ------------------------------------
    for i in range(nump):
        vert = get_vert(i)

        # Distance value (dv) projection
        j = vec_to_st[axis][2]
        if j > 0:
            dv = vert[j - 1]
        else:
            dv = -vert[-j - 1]

        # Zero guard to avoid division by zero on degenerate polygons
        if dv == 0.0:
            continue

        # S-coordinate projection
        j = vec_to_st[axis][0]
        if j < 0:
            s = -vert[-j - 1] / dv
        else:
            s = vert[j - 1] / dv

        # T-coordinate projection
        j = vec_to_st[axis][1]
        if j < 0:
            t = -vert[-j - 1] / dv
        else:
            t = vert[j - 1] / dv

        # Bounding box updates
        if s < skymins[0][axis]:
            skymins[0][axis] = s
        if t < skymins[1][axis]:
            skymins[1][axis] = t
        if s > skymaxs[0][axis]:
            skymaxs[0][axis] = s
        if t > skymaxs[1][axis]:
            skymaxs[1][axis] = t



def Sky_ClipPoly(nump: int, vecs: list, stage: int):
    """Recursively clips a sky polygon against the 6 skybox frustum planes (stages 0..5).

    Once stage 6 is reached, projects the fully clipped polygon onto sky box faces.

    C equivalent:
    static void Sky_ClipPoly (int nump, vec3_t vecs, int stage) in r_brush.c / r_sky.c
    """
    if stage == 6:  # Fully clipped against all 6 planes
        Sky_ProjectPoly(nump, vecs)
        return

    front = False
    back = False
    norm = skyclip[stage]

    # Helper function to extract individual vertex coordinates safely
    # regardless of whether vecs is flat float list or list of 3-element lists
    is_flat = len(vecs) > 0 and isinstance(vecs[0], (float, int))

    def get_vert(idx: int) -> list[float]:
        if is_flat:
            offset = idx * 3
            return [vecs[offset], vecs[offset + 1], vecs[offset + 2]]
        return [vecs[idx][0], vecs[idx][1], vecs[idx][2]]

    sides = [0] * (nump + 1)
    dists = [0.0] * (nump + 1)

    # Classify each vertex relative to the current clipping plane
    for i in range(nump):
        v = get_vert(i)
        d = v[0] * norm[0] + v[1] * norm[1] + v[2] * norm[2]  # DotProduct

        if d > quakedef.ON_EPSILON:
            front = True
            sides[i] = quakedef.SIDE_FRONT
        elif d < -quakedef.ON_EPSILON:  # Note: d < -ON_EPSILON matches C's d < -ON_EPSILON logic
            back = True
            sides[i] = quakedef.SIDE_BACK
        else:
            sides[i] = quakedef.SIDE_ON

        dists[i] = d

    # If polygon is entirely on front or entirely on back, pass along unclipped
    if not front or not back:
        Sky_ClipPoly(nump, vecs, stage + 1)
        return

    # Wrap around the last vertex to close the polygon loop
    sides[nump] = sides[0]
    dists[nump] = dists[0]

    newc_0 = 0
    newc_1 = 0
    newv_0 = []
    newv_1 = []

    # Perform polygon splitting across the clipping plane
    for i in range(nump):
        v = get_vert(i)

        if sides[i] == quakedef.SIDE_FRONT:
            newv_0.append([v[0], v[1], v[2]])
            newc_0 += 1
        elif sides[i] == quakedef.SIDE_BACK:
            newv_1.append([v[0], v[1], v[2]])
            newc_1 += 1
        elif sides[i] == quakedef.SIDE_ON:
            newv_0.append([v[0], v[1], v[2]])
            newc_0 += 1
            newv_1.append([v[0], v[1], v[2]])
            newc_1 += 1

        # Check if an edge splits across the plane
        if (
            sides[i] == quakedef.SIDE_ON
            or sides[i + 1] == quakedef.SIDE_ON
            or sides[i + 1] == sides[i]
        ):
            continue

        # Interpolate edge intersection vertex
        v_next = get_vert(0) if i == nump - 1 else get_vert(i + 1)
        d = dists[i] / (dists[i] - dists[i + 1])

        e = [
            v[0] + d * (v_next[0] - v[0]),
            v[1] + d * (v_next[1] - v[1]),
            v[2] + d * (v_next[2] - v[2]),
        ]

        newv_0.append(e)
        newc_0 += 1
        newv_1.append(e)
        newc_1 += 1

    # Recursively process front and back clipped fragments
    Sky_ClipPoly(newc_0, newv_0, stage + 1)
    Sky_ClipPoly(newc_1, newv_1, stage + 1)

def Sky_ProcessPoly(p: quakedef.glpoly_t):
    r_brush.DrawGLPoly(p)
    gl_rmain.rs_brushpasses += 1

    if not cvar.Cvar_GetCvar("r_fastsky").value:
        num_verts = p.numverts

        # Allocate vertex buffer for view-relative coordinates
        verts: list[quakedef.vec3_t] = [
            [0.0, 0.0, 0.0] for _ in range(num_verts)
        ]

        # Subtract camera origin: v_rel = p.verts[i] - r_origin
        for i in range(num_verts):
            mathlib.VectorSubtract(p.verts[i], gl_rmain.r_origin, verts[i])

        # Submit relative vertex array to stage 0 of sky plane clipping
        Sky_ClipPoly(num_verts, verts, 0)


def Sky_ProcessTextureChains():
    """Traverses world model texture chains marked with SURF_DRAWSKY, sending all

    sky surface polygons to Sky_ProcessPoly for rendering and projection.

    C equivalent:
    R_DrawSkyChains in r_brush.c
    """
    if not gl_rmain.r_drawworld_cheatsafe:
        return

    worldmodel = cl_main.cl.worldmodel
    if not worldmodel or not worldmodel.textures:
        return

    for i in range(worldmodel.numtextures):
        t: quakedef.texture_t = worldmodel.textures[i]

        if not t:
            continue

        # Get head of the world texture chain
        s: quakedef.msurface_t = t.texturechains[
            quakedef.texchain_t.chain_world
        ]
        if not s:
            continue

        # Check if surfaces in this texture chain carry the SURF_DRAWSKY flag
        if not (s.flags & quakedef.SURF_DRAWSKY):
            continue

        # Traverse the linked list of surfaces in this texture chain (s = s->texturechain)
        while s:
            p: quakedef.glpoly_t = s.polys

            # Traverse all GL polygons attached to this surface (p = p->next)
            while p:
                Sky_ProcessPoly(p)
                p = p.next

            s = s.texturechain



def Sky_ProcessEntities():
    """Traverses visible brush entities (e.g. moving platforms/doors with sky brushes),

    transforms their sky polygon vertices from local model space to world space,
    and passes them to the sky rendering/projection pipeline.

    C equivalent:
    void Sky_ProcessEntities (void) in r_brush.c / r_sky.c
    """
    r_drawentities = cvar.Cvar_GetCvar('r_drawentities').value
    if not r_drawentities:
        return

    modelorg = [0.0, 0.0, 0.0]

    for i in range(cl_main.cl_numvisedicts):
        e: quakedef.entity_t = cl_main.cl_visedicts[i]

        if not e or not e.model or e.model.type != quakedef.modtype_t.mod_brush:
            continue

        if gl_rmain.R_CullModelForEntity(e):
            continue

        if e.alpha == protocol.ENTALPHA_ZERO:
            continue

        # Calculate camera origin relative to entity origin
        mathlib.VectorSubtract(gl_rmain.r_refdef.vieworg, e.origin, modelorg)

        forward = [0.0, 0.0, 0.0]
        right = [0.0, 0.0, 0.0]
        up = [0.0, 0.0, 0.0]

        # Rotate modelorg into entity-local coordinate space if rotated
        if e.angles[0] or e.angles[1] or e.angles[2]:
            rotated = True
            mathlib.AngleVectors(e.angles, forward, right, up)

            temp = list(modelorg)
            modelorg[0] = mathlib.DotProduct(temp, forward)
            modelorg[1] = -mathlib.DotProduct(temp, right)
            modelorg[2] = mathlib.DotProduct(temp, up)
        else:
            rotated = False

        first_surf = e.model.firstmodelsurface
        num_surfs = e.model.nummodelsurfaces

        for j in range(num_surfs):
            s: quakedef.msurface_t = e.model.surfaces[first_surf + j]

            if s.flags & quakedef.SURF_DRAWSKY:
                # Calculate backface distance relative to model-space plane
                dot = (
                    mathlib.DotProduct(modelorg, s.plane.normal) - s.plane.dist
                )

                # Backface cull check
                if (
                    s.flags & quakedef.SURF_PLANEBACK
                    and dot < -BACKFACE_EPSILON
                ) or (
                    not (s.flags & quakedef.SURF_PLANEBACK)
                    and dot > BACKFACE_EPSILON
                ):

                    # Copy polygon structure and transform vertices into world-space
                    p = quakedef.glpoly_t()
                    p.numverts = s.polys.numverts
                    p.verts = [[0.0] * 7 for _ in range(p.numverts)]

                    for k in range(p.numverts):
                        if rotated:
                            # Apply inverse-rotation matrix + origin translation
                            p.verts[k][0] = (
                                e.origin[0]
                                + s.polys.verts[k][0] * forward[0]
                                - s.polys.verts[k][1] * right[0]
                                + s.polys.verts[k][2] * up[0]
                            )
                            p.verts[k][1] = (
                                e.origin[1]
                                + s.polys.verts[k][0] * forward[1]
                                - s.polys.verts[k][1] * right[1]
                                + s.polys.verts[k][2] * up[1]
                            )
                            p.verts[k][2] = (
                                e.origin[2]
                                + s.polys.verts[k][0] * forward[2]
                                - s.polys.verts[k][1] * right[2]
                                + s.polys.verts[k][2] * up[2]
                            )
                        else:
                            # Direct origin translation offset
                            mathlib.VectorAdd(
                                s.polys.verts[k], e.origin, p.verts[k]
                            )

                    # Submit transformed world-space polygon to sky processing
                    Sky_ProcessPoly(p)



def Sky_EmitSkyBoxVertex(s: float, t: float, axis: int):
    v: quakedef.vec3_t = [0., 0., 0.]
    b: quakedef.vec3_t = [0., 0., 0.]

    gl_farclip = cvar.Cvar_GetCvar('gl_farclip').value
    sqrt3 = math.sqrt(3.0)

    b[0] = s * gl_farclip / sqrt3
    b[1] = t * gl_farclip / sqrt3
    b[2] = gl_farclip / sqrt3

    for j in range(3):
        k = st_to_vec[axis][j]
        if k < 0:
            v[j] = -b[-k - 1]
        else:
            v[j] = b[k - 1]
        v[j] += gl_rmain.r_origin[j]

    s = ( s + 1. ) * 0.5
    t = ( t + 1. ) * 0.5

    w = skybox_textures[skytexorder[axis]].width
    h = skybox_textures[skytexorder[axis]].height

    s = s * (w-1)/w + 0.5/w
    t = t * (h-1)/h + 0.5/h

    t = 1.0 - t

    gl.glTexCoord2f(s, t)
    gl.glVertex3fv(v)



def Sky_DrawSkyBox():

    for i in range(6):
        if skymins[0][i] >= skymaxs[0][i] or skymins[1][i] >= skymaxs[1][i]:
            continue

        gl_texmgr.GL_Bind(skybox_textures[skytexorder[i]])

        skymins[0][i] = -1
        skymins[1][i] = -1
        skymaxs[0][i] = 1
        skymaxs[1][i] = 1

        gl.glBegin(gl.GL_QUADS)
        Sky_EmitSkyBoxVertex (skymins[0][i], skymins[1][i], i)
        Sky_EmitSkyBoxVertex (skymins[0][i], skymaxs[1][i], i)
        Sky_EmitSkyBoxVertex (skymaxs[0][i], skymaxs[1][i], i)
        Sky_EmitSkyBoxVertex (skymaxs[0][i], skymins[1][i], i)
        gl.glEnd()

        gl_rmain.rs_skypolys += 1
        gl_rmain.rs_skypasses += 1

        if gl_fog.Fog_GetDensity() > 0 and skyfog > 0:
            c = gl_fog.Fog_GetColor()
            gl.glEnable(gl.GL_BLEND)
            gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glColor4f(c[0],c[1],c[2], common.CLAMP(0.0,skyfog,1.0))

            gl.glBegin(gl.GL_QUADS)
            Sky_EmitSkyBoxVertex (skymins[0][i], skymins[1][i], i)
            Sky_EmitSkyBoxVertex (skymins[0][i], skymaxs[1][i], i)
            Sky_EmitSkyBoxVertex (skymaxs[0][i], skymaxs[1][i], i)
            Sky_EmitSkyBoxVertex (skymaxs[0][i], skymins[1][i], i)
            gl.glEnd()

            gl.glColor3f(1, 1, 1)
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glDisable(gl.GL_BLEND)

            gl_rmain.rs_skypasses += 1

def Sky_SetBoxVert(s: float, t: float, axis: int, v: quakedef.vec3_t):

    b: quakedef.vec3_t = [0.,0.,0.]
    gl_farclip = cvar.Cvar_GetCvar('gl_farclip').value
    sqrt3 = math.sqrt(3.0)

    b[0] = s * gl_farclip / sqrt3
    b[1] = t * gl_farclip / sqrt3
    b[2] = gl_farclip / sqrt3

    for j in range(3):
        k = st_to_vec[axis][j]
        if k < 0:
            v[j] = -b[-k - 1]
        else:
            v[j] = b[k - 1]
        v[j] += gl_rmain.r_origin[j]


def _sky_texcoords(verts, speed: float):
    """Vectorised Sky_GetTexCoord for an (n,3) float32 array; returns (n,2) float32."""
    d = verts - np.asarray(gl_rmain.r_origin, dtype=np.float32)
    d[:, 2] *= 3
    length = 6 * 63 / np.sqrt((d * d).sum(axis=1))

    scroll = cl_main.cl.time * speed
    scroll -= int(scroll) & ~127

    st = np.empty((len(verts), 2), dtype=np.float32)
    st[:, 0] = (scroll + d[:, 0] * length) * (1.0 / 128)
    st[:, 1] = (scroll + d[:, 1] * length) * (1.0 / 128)
    return st


def _draw_sky_arrays(verts, texcoords=None):
    """Draw GL_QUADS from client-side arrays (verts: (4n,3) f32, texcoords: (4n,2) f32 or None)."""
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glVertexPointer(3, gl.GL_FLOAT, 0, verts)
    if texcoords is not None:
        gl.glClientActiveTexture(gl.GL_TEXTURE0)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, texcoords)
    gl.glDrawArrays(gl.GL_QUADS, 0, len(verts))
    if texcoords is not None:
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
    gl.glDisableClientState(gl.GL_VERTEX_ARRAY)


def Sky_DrawFace(axis: int):
    """Draw the two scrolling sky layers on one face of the sky cube, subdivided into a
    di x dj grid (r_sky_quality) so the projection looks right; all quads of the face go
    out in one array draw per layer."""
    verts = [[0., 0., 0.] for _ in range(4)]
    Sky_SetBoxVert(-1.0, -1.0, axis, verts[0])
    Sky_SetBoxVert(-1.0,  1.0, axis, verts[1])
    Sky_SetBoxVert(1.0,   1.0, axis, verts[2])
    Sky_SetBoxVert(1.0,  -1.0, axis, verts[3])

    v0 = np.asarray(verts[0], dtype=np.float32)
    up = np.asarray(verts[2], dtype=np.float32) - np.asarray(verts[3], dtype=np.float32)
    right = np.asarray(verts[2], dtype=np.float32) - np.asarray(verts[1], dtype=np.float32)

    di = max(int(cvar.Cvar_GetCvar('r_sky_quality').value), 1)
    qi = 1.0 / di
    dj = di * 2 if axis < 4 else di
    qj = 1.0 / dj

    smin = skymins[0][axis] / 2 + 0.5
    smax = skymaxs[0][axis] / 2 + 0.5
    tmin = skymins[1][axis] / 2 + 0.5
    tmax = skymaxs[1][axis] / 2 + 0.5

    cells = []
    for i in range(di):
        if i * qi < smin - qi or i * qi > smax:
            continue
        for j in range(dj):
            if j * qj < tmin - qj or j * qj > tmax:
                continue
            cells.append((i, j))

    if not cells:
        return

    ij = np.asarray(cells, dtype=np.float32)
    base = v0 + right * (qi * ij[:, 0:1]) + up * (qj * ij[:, 1:2])
    p1 = base + up * qj
    p2 = p1 + right * qi
    p3 = base + right * qi
    quad_verts = np.ascontiguousarray(np.stack([base, p1, p2, p3], axis=1).reshape(-1, 3), dtype=np.float32)

    r_skyalpha = cvar.Cvar_GetCvar('r_skyalpha').value

    # layer 1: opaque back layer
    gl_texmgr.GL_Bind(solidskytexture)
    if r_skyalpha < 1.0:
        gl.glColor3f(1., 1., 1.)
    _draw_sky_arrays(quad_verts, np.ascontiguousarray(_sky_texcoords(quad_verts, 8)))

    # layer 2: alpha-blended cloud layer, scrolling twice as fast
    gl_texmgr.GL_Bind(alphaskytexture)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    if r_skyalpha < 1.0:
        gl.glColor4f(1., 1., 1., r_skyalpha)
    _draw_sky_arrays(quad_verts, np.ascontiguousarray(_sky_texcoords(quad_verts, 16)))
    gl.glDisable(gl.GL_BLEND)

    gl_rmain.rs_skypolys += len(cells)
    gl_rmain.rs_skypasses += 2

    if gl_fog.Fog_GetDensity() > 0 and skyfog > 0:
        c = gl_fog.Fog_GetColor()
        gl.glEnable(gl.GL_BLEND)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glColor4f(c[0], c[1], c[2], common.CLAMP(0.0, skyfog, 1.0))
        _draw_sky_arrays(quad_verts)
        gl.glColor3f(1., 1., 1.)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_BLEND)
        gl_rmain.rs_skypasses += 1


def Sky_DrawSkyLayers():
    r_skyalpha = cvar.Cvar_GetCvar('r_skyalpha').value

    gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE,
                 gl.GL_MODULATE if r_skyalpha < 1.0 else gl.GL_REPLACE)

    for i in range(6):
        if skymins[0][i] < skymaxs[0][i] and skymins[1][i] < skymaxs[1][i]:
            Sky_DrawFace (i);

    gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)
    gl.glColor3f(1., 1., 1.)


def Sky_DrawSky():

    if gl_rmain.r_drawflat_cheatsafe or gl_rmain.r_lightmap_cheatsafe:
        return

    for i in range(6):
        skymins[0][i] = skymins[1][i] = mathlib.FLT_MAX
        skymaxs[0][i] = skymaxs[1][i] = -mathlib.FLT_MAX

    gl.glUseProgram(0)  # sky is drawn with the fixed-function pipeline
    gl_fog.Fog_DisableGFog()
    gl.glDisable(gl.GL_TEXTURE_2D)
    if gl_fog.Fog_GetDensity() > 0:
        gl.glColor3fv(gl_fog.Fog_GetColor())
    else:
        gl.glColor3fv(skyflatcolor)

    Sky_ProcessTextureChains()
    Sky_ProcessEntities()

    gl.glColor3f(1, 1, 1)
    gl.glEnable(gl.GL_TEXTURE_2D)


    if not cvar.Cvar_GetCvar('r_fastsky').value and not (gl_fog.Fog_GetDensity() > 0 and skyfog >= 1):
        gl.glDepthFunc(gl.GL_GEQUAL)
        gl.glDepthMask(0)

        if skybox_name:
            Sky_DrawSkyBox()
        else:
            Sky_DrawSkyLayers()

        gl.glDepthMask(1)
        gl.glDepthFunc(gl.GL_LEQUAL)

    gl_fog.Fog_EnableGFog()
