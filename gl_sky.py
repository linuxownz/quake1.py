#gl_sky.py
import math
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
import quakedef
import r_brush
import render
import zone

MAX_CLIP_VERTS  = 64

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

def Sky_LoadTexture(mod: quakedef.qmodel_t, mt: quakedef.texture_t):
    global solidskytexture, alphaskytexture, skyflatcolor

    if mt.width != 256 or mt.height != 128:
        console.Con_Warning(
            f"Sky texture {mt.name} is {mt.width} x {mt.height}, expected 256 x 128\n"
        )
        if mt.width < 2 or mt.height < 1:
            return

    halfwidth = mt.width // 2
    skytex_size = halfwidth * mt.height * 2

    # Allocate hunk memory for both layers (halfwidth * height * 2 bytes)
    back_data = zone.Hunk_AllocName(skytex_size, "skytex")

    # In C: (byte *)(mt + 1) points to raw pixel data packed right after the texture_t struct
    if hasattr(mt, "buffer"):
        src_bytes = memoryview(mt.buffer)[ctypes.sizeof(mt) :]
    else:
        src_bytes = memoryview(mt.data)

    # ------------------------------------
    # Extract back layer and upload
    # ------------------------------------
    for y in range(mt.height):
        dest_offset = y * halfwidth
        src_offset = halfwidth + (y * mt.width)
        back_data[dest_offset : dest_offset + halfwidth] = src_bytes[
            src_offset : src_offset + halfwidth
        ]

    texturename_back = f"{mod.name}:{mt.name}_back"
    solidskytexture = gl_texmgr.TexMgr_LoadImage(
        mod,
        texturename_back,
        halfwidth,
        mt.height,
        gl_texmgr.SRC_INDEXED,
        back_data,
        "",
        back_data,
        gl_texmgr.TEXPREF_NONE,
    )

    # ------------------------------------
    # Extract front layer and upload
    # ------------------------------------
    front_data_offset = halfwidth * mt.height
    front_data = memoryview(back_data)[front_data_offset:]

    r = g = b = count = 0

    for y in range(mt.height):
        row_src_offset = y * mt.width
        row_front_offset = y * halfwidth

        for x in range(halfwidth):
            p = src_bytes[row_src_offset + x]

            if p == 0:
                p = 255
            else:
                # Direct 1:1 mapping of d_8to24table palette lookup
                # d_8to24table[p] stores a 32-bit integer formatted as 0xAABBGGRR or [R, G, B, A]
                rgba = gl_texmgr.d_8to24table[p]

                # Extract byte channels (matches ((byte *)rgba)[0..2] in C)
                r += rgba & 0xFF
                g += (rgba >> 8) & 0xFF
                b += (rgba >> 16) & 0xFF
                count += 1

            front_data[row_front_offset + x] = p

    texturename_front = f"{mod.name}:{mt.name}_front"
    alphaskytexture = texmgr.TexMgr_LoadImage(
        mod,
        texturename_front,
        halfwidth,
        mt.height,
        texmgr.SRC_INDEXED,
        front_data,
        "",
        front_data,
        texmgr.TEXPREF_ALPHA,
    )

    # ------------------------------------
    # Calculate r_fastsky color based on average of all opaque foreground colors
    # ------------------------------------
    if count > 0:
        skyflatcolor[0] = float(r) / (count * 255)
        skyflatcolor[1] = float(g) / (count * 255)
        skyflatcolor[2] = float(b) / (count * 255)
    else:
        skyflatcolor[0] = 0.0
        skyflatcolor[1] = 0.0
        skyflatcolor[2] = 0.0



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

    for i in range(6):
        mark = zone.Hunk_LowMark()
        filename = f'gfx/env/{name}{suf[i]}'
        data, width, height = image.Image_LoadImage(filename)

        if data:
            skybox_textures[i] = gl_texmgr.TexMgr_LoadImage(cl_main.cl.worldmodel, filename, width, height, gl_texmgr.srcformat.SRC_RGBA, data, filename, 0, gl_texmgr.TEXPREF_NONE)
            nonefound = False
        else:
            console.Con_Printf(f'Couldnt load {filename}')
            skybox_textures[i] = gl_texmgr.notexture

        zone.Hunk_FreeToLowMark(mark)

    if nonefound:
        for i in range(6):
            if skybox_textures[i] and skybox_textures[i] != gl_texmgr.notexture:
                gl_texmgr.TexMgr_FreeTexture(skybox_textures[i])
            skybox_textures[i] = None

        skybox_name = ''
        return

    skybox_name = name

def Sky_ClearAll():
    global skybox_name

    skybox_name = ''
    for i in range(6):
        skybox_textures[i] = None

    solidskytexture = None
    alphaskytexture = None

    r_skyfog = cvar.Cvar_GetCvar('r_skyfog')
    cvar.Cvar_SetQuick(r_skyfog, r_skyfog.default_string)  # this may be wrong



def Sky_NewMap():
    skyfog = cvar.Cvar_GetCvar('r_skyfog').value

    data = cl_main.cl.worldmodel.entities
    if not data:
        return

    data = common.COM_Parse(data)
    if not data:
        return
    if common.com_token[0] != '{':
        return

    while True:
        data = common.COM_Parse(data)

        if not data:
            return
        if common.com_token[0] == '}':
            break
        if common.com_token[0] == '_':
            key = common.com_token[1:]
        else:
            key = common.com_token[:]

        key.rstrip()

        data = common.COM_ParseEx(data)
        if not data:
            return

        value = com_token[:]

        if key == 'sky':
            Sky_LoadSkyBox(value)

        if key == 'skyfog':
            skyfog = float(value)
        elif key in ['skyname', 'qlsky']:
            Sky_LoadSkyBox(value)


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
    void Sky_ProjectPoly (int nump, vec3_t vecs) in gl_rsurf.c / r_sky.c
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
    static void Sky_ClipPoly (int nump, vec3_t vecs, int stage) in gl_rsurf.c / r_sky.c
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

        if d > ON_EPSILON:
            front = True
            sides[i] = SIDE_FRONT
        elif d < -ON_EPSILON:  # Note: d < -ON_EPSILON matches C's d < -ON_EPSILON logic
            back = True
            sides[i] = SIDE_BACK
        else:
            sides[i] = SIDE_ON

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

        if sides[i] == SIDE_FRONT:
            newv_0.append([v[0], v[1], v[2]])
            newc_0 += 1
        elif sides[i] == SIDE_BACK:
            newv_1.append([v[0], v[1], v[2]])
            newc_1 += 1
        elif sides[i] == SIDE_ON:
            newv_0.append([v[0], v[1], v[2]])
            newc_0 += 1
            newv_1.append([v[0], v[1], v[2]])
            newc_1 += 1

        # Check if an edge splits across the plane
        if (
            sides[i] == SIDE_ON
            or sides[i + 1] == SIDE_ON
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
    R_DrawSkyChains in gl_rsurf.c
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



import mathlib
import quakedef
import render
import zone

BACKFACE_EPSILON = 0.01


def Sky_ProcessEntities():
    """Traverses visible brush entities (e.g. moving platforms/doors with sky brushes),

    transforms their sky polygon vertices from local model space to world space,
    and passes them to the sky rendering/projection pipeline.

    C equivalent:
    void Sky_ProcessEntities (void) in gl_rsurf.c / r_sky.c
    """
    if not render.r_drawentities.value:
        return

    modelorg = [0.0, 0.0, 0.0]

    for i in range(render.cl_numvisedicts):
        e: quakedef.entity_t = render.cl_visedicts[i]

        if not e or not e.model or e.model.type != quakedef.mod_brush:
            continue

        if render.R_CullModelForEntity(e):
            continue

        if e.alpha == quakedef.ENTALPHA_ZERO:
            continue

        # Calculate camera origin relative to entity origin
        mathlib.VectorSubtract(render.r_refdef.vieworg, e.origin, modelorg)

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

                    # Emulate temporary arena allocation via Hunk mark
                    mark = zone.Hunk_LowMark()

                    # Copy polygon structure and transform vertices into world-space
                    p = quakedef.glpoly_t()
                    p.numverts = s.polys.numverts
                    p.verts = [[0.0, 0.0, 0.0] for _ in range(p.numverts)]

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

                    zone.Hunk_FreeToLowMark(mark)



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
        skymins[0][i] = 1
        skymins[1][i] = 1

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


def Sky_GetTexCoord(v: quakedef.vec3_t, speed: float) -> tuple[float, float]:
    _dir: quakedef.vec3_t = [0.,0.,0.]

    mathlib.VectorSubtract(v, gl_rmain.r_origin, _dir)
    _dir[2] *= 3

    length = _dir[0] * _dir[0] + _dir[1] * _dir[1] + _dir[2] * _dir[2]
    length = math.sqrt(length)
    length = 6 * 63 / length

    scroll  = cl_main.cl.time * speed
    scroll -= int(scroll) & ~127

    s = (scroll + _dir[0] * length) * (1.0/128)
    t = (scroll + _dir[1] * length) * (1.0/128)

    return (s, t)

def Sky_DrawFaceQuad(p: quakedef.glpoly_t):
    s: float = 0.0
    t: float = 0.0

    r_skyalpha = cvar.Cvar_GetCvar('r_skyalpha').value

    if gl_vidsdl.gl_mtexable and r_skyalpha >= 1.0:
        gl_texmgr.GL_Bind(solidskytexture)
        gl_texmgr.GL_EnableMultitexture()
        gl_texmgr.GL_Bind(alphaskytexture)

        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_DECAL)

        gl.glBegin(gl.GL_QUADS)

        for i in range(4):
            v = p.verts[i]

            s, t = Sky_GetTexCoord(v, 8)
            gl.glMultiTexCoord2f(gl.GL_TEXTURE0, s, t)
            s, t = Sky_GetTexCoord(v, 16)
            gl.glMultiTexCoord2f(gl.GL_TEXTURE1, s, t)
            gl.glVertex3fv(v)

        gl.glEnd()

        gl_texmgr.GL_DisableMultitexture()

        gl_rmain.rs_skypasses += 1
        gl_rmain.rs_skypolys += 1
    else:
        gl_texmgr.GL_Bind(solidskytexture)

        if r_skyalpha < 1.0:
            gl.glColor3f(1., 1., 1.)

        gl.glBegin(gl.GL_QUADS)
        for i in range(4):
            v = p.verts[i]
            s, t = Sky_GetTexCoord(v, 8)
            gl.glTexCoord2f(s, t)
            gl.glVertex3fv(v)
        gl.glEnd()

        gl_texmgr.GL_Bind(alphaskytexture)
        gl.glEnable(gl.GL_BLEND)

        if r_skyalpha < 1.0:
            gl.glColor4f(1., 1., 1., r_skyalpha)

        gl.glBegin(gl.GL_QUADS)
        for i in range(4):
            v = p.verts[i]
            s, t = Sky_GetTexCoord(v, 16)
            gl.glTexCoord2f(s, t)
            gl.glVertex3fv(v)
        gl.glEnd()

        gl.glDisable(gl.GL_BLEND)

        gl_rmain.rs_skypolys += 1
        gl_rmain.rs_skypasses += 2

    if gl_fog.Fog_GetDensity() > 0 and skyfog > 0:
        c = gl_fog.Fog_GetColor()
        gl.glEnable(gl.GL_BLEND)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glColor4f(c[0], c[1], c[2], common.CLAMP(0.0, skyfog, 1.0))

        gl.glBegin(gl.GL_QUADS)
        for i in range(4):
            v = p.verts[i]
            gl.glVertex3fv(v)
        gl.glEnd()

        gl.glColor3f(1., 1., 1.)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_BLEND)

        gl_rmain.rs_skypasses += 1

def Sky_DrawFace(axis: int):

    verts: list[quakedef.vec3_t] = [[0.,0.,0.], [0.,0.,0.], [0.,0.,0.], [0.,0.,0.]]
    up: quakedef.vec3_t = [0., 0., 0.]
    right: quakedef.vec3_t = [0., 0., 0.]
    temp: quakedef.vec3_t = [0., 0., 0.]
    temp2: quakedef.vec3_t = [0., 0., 0.]

    Sky_SetBoxVert(-1.0, -1.0, axis, verts[0])
    Sky_SetBoxVert(-1.0,  1.0, axis, verts[1])
    Sky_SetBoxVert(1.0,   1.0, axis, verts[2])
    Sky_SetBoxVert(1.0,  -1.0, axis, verts[3])

    p: quakedef.glpoly_t = quakedef.glpoly_t()

    mathlib.VectorSubtract(verts[2],verts[3],up);
    mathlib.VectorSubtract(verts[2],verts[1],right)

    di = max(int(cvar.Cvar_GetCvar('r_sky_quality').value), 1)
    qi = 1.0 / di
    dj = di * 2 if axis < 4 else di
    qj = 1.0 / dj

    for i in range(di):
        for j in range(dj):
            if i*qi < skymins[0][axis]/2+0.5 - qi or i*qi > skymaxs[0][axis]/2+0.5  or \
                j*qj < skymins[1][axis]/2+0.5 - qj or j*qj > skymaxs[1][axis]/2+0.5:
                continue

            mathlib.VectorScale (right, qi*i, temp)
            mathlib.VectorScale (up, qj*j, temp2)
            mathlib.VectorAdd(temp,temp2,temp)
            mathlib.VectorAdd(verts[0],temp,p.verts[0])

            mathlib.VectorScale (up, qj, temp)
            mathlib.VectorAdd (p.verts[0],temp,p.verts[1])

            mathlib.VectorScale (right, qi, temp)
            mathlib.VectorAdd (p.verts[1],temp,p.verts[2])

            mathlib.VectorAdd (p.verts[0],temp,p.verts[3])

            Sky_DrawFaceQuad (p)


def Sky_DrawSkyLayers():
    r_skyalpha = cvar.Cvar_GetCvar('r_skyalpha').value

    if r_skyalpha < 1.0:
        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE)

    for i in range(6):
        if skymins[0][i] < skymaxs[0][i] and skymins[1][i] < skymaxs[1][i]:
            Sky_DrawFace (i);

    if r_skyalpha < 1.0:
        gl.glTexEnvf(gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_REPLACE)


def Sky_DrawSky():

    if gl_rmain.r_drawflat_cheatsafe or gl_rmain.r_lightmap_cheatsafe:
        return

    for i in range(6):
        skymins[0][i] = skymins[1][i] = mathlib.FLT_MAX
        skymaxs[0][i] = skymaxs[1][i] = -mathlib.FLT_MAX

    gl_fog.Fog_DisbleGFog()
    gl.glDisable(gl.GL_TEXTURE_2D)
    if gl_fog.Fog_GetDensity() > 0:
        gl.glColor3fv(gl_fog.Fog_GetColor())
    else:
        gl.glColor3fv(skyflatcolor)

    Sky_ProcessTextureChains()
    Sky_ProcessEntities()

    gl.glColor3f(1, 1, 1)
    gl.glEnable(gl.GL_TEXTURE_2D)


    if cvar.Cvar_GetCvar('r_fastsky').value and not ( gl_fog.Fog_GetDensity() > 0 and skyfog >= 1):
        gl.glDepthFunc(gl.GL_GEQUAL)
        gl.glDepthMask(0)

        if skybox_name:
            Sky_DrawSkyBox()
        else:
            Sky_DrawSkyLayers()

        gl.glDepthMask(1)
        gl.glDepthFunc(gl.GL_LEQUAL)

    gl_fog.Fog_EnableGFog()

























