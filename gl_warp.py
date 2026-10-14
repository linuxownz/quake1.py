#gl_warp.py

import math

import OpenGL.GL as gl

import cl_main
import common
import cvar
import gl_draw
import gl_rmain
import gl_screen
import gl_texmgr
import mathlib
import quakedef
import sbar
import sys_sdl_unix

gl_warpimagesize:int = 0
load_subdivide_size:float = 0.0

warpface: quakedef.msurface_t = None

def GL_WarpInit():
    import cvar

    cvar.Cvar_RegisterVariable({'name': 'r_oldwater', 'value': '0', 'flag': cvar.CVAR_ARCHIVE})
    cvar.Cvar_RegisterVariable({'name': 'r_waterquality', 'value': '8', 'flag': cvar.CVAR_NONE})
    cvar.Cvar_RegisterVariable({'name': 'r_waterwarp', 'value': '1', 'flag': cvar.CVAR_NONE})
    cvar.Cvar_RegisterVariable({'name': 'r_subdivide_size', 'value': '128', 'flag': cvar.CVAR_ARCHIVE})


turbsin: list[float] = [
  0,          0.19633,    0.392541,   0.588517,
  0.784137,   0.979285,   1.17384,    1.3677,
  1.56072,    1.75281,    1.94384,    2.1337,
  2.32228,    2.50945,    2.69512,    2.87916,
  3.06147,    3.24193,    3.42044,    3.59689,
  3.77117,    3.94319,    4.11282,    4.27998,
  4.44456,    4.60647,    4.76559,    4.92185,
  5.07515,    5.22538,    5.37247,    5.51632,
  5.65685,    5.79398,    5.92761,    6.05767,
  6.18408,    6.30677,    6.42566,    6.54068,
  6.65176,    6.75883,    6.86183,    6.9607,
  7.05537,    7.14579,    7.23191,    7.31368,
  7.39104,    7.46394,    7.53235,    7.59623,
  7.65552,    7.71021,    7.76025,    7.80562,
  7.84628,    7.88222,    7.91341,    7.93984,
  7.96148,    7.97832,    7.99036,    7.99759,
  8,          7.99759,    7.99036,    7.97832,
  7.96148,    7.93984,    7.91341,    7.88222,
  7.84628,    7.80562,    7.76025,    7.71021,
  7.65552,    7.59623,    7.53235,    7.46394,
  7.39104,    7.31368,    7.23191,    7.14579,
  7.05537,    6.9607,     6.86183,    6.75883,
  6.65176,    6.54068,    6.42566,    6.30677,
  6.18408,    6.05767,    5.92761,    5.79398,
  5.65685,    5.51632,    5.37247,    5.22538,
  5.07515,    4.92185,    4.76559,    4.60647,
  4.44456,    4.27998,    4.11282,    3.94319,
  3.77117,    3.59689,    3.42044,    3.24193,
  3.06147,    2.87916,    2.69512,    2.50945,
  2.32228,    2.1337,     1.94384,    1.75281,
  1.56072,    1.3677,     1.17384,    0.979285,
  0.784137,   0.588517,   0.392541,   0.19633,
  9.79717e-16,-0.19633,  -0.392541,  -0.5885
 -0.784137,  -0.979285,  -1.17384,   -1.3677,
 -1.56072,   -1.75281,   -1.94384,   -2.1337,
 -2.32228,   -2.50945,   -2.69512,   -2.87916,
 -3.06147,   -3.24193,   -3.42044,   -3.59689,
 -3.77117,   -3.94319,   -4.11282,   -4.27998,
 -4.44456,   -4.60647,   -4.76559,   -4.92185,
 -5.07515,   -5.22538,   -5.37247,   -5.51632,
 -5.65685,   -5.79398,   -5.92761,   -6.05767,
 -6.18408,   -6.30677,   -6.42566,   -6.54068,
 -6.65176,   -6.75883,   -6.86183,   -6.9607,
 -7.05537,   -7.14579,   -7.23191,   -7.31368,
 -7.39104,   -7.46394,   -7.53235,   -7.59623,
 -7.65552,   -7.71021,   -7.76025,   -7.80562,
 -7.84628,   -7.88222,   -7.91341,   -7.93984,
 -7.96148,   -7.97832,   -7.99036,   -7.99759,
 -8,         -7.99759,   -7.99036,   -7.97832,
 -7.96148,   -7.93984,   -7.91341,   -7.88222,
 -7.84628,   -7.80562,   -7.76025,   -7.71021,
 -7.65552,   -7.59623,   -7.53235,   -7.46394,
 -7.39104,   -7.31368,   -7.23191,   -7.14579,
 -7.05537,   -6.9607,    -6.86183,   -6.75883,
 -6.65176,   -6.54068,   -6.42566,   -6.30677,
 -6.18408,   -6.05767,   -5.92761,   -5.79398,
 -5.65685,   -5.51632,   -5.37247,   -5.22538,
 -5.07515,   -4.92185,   -4.76559,   -4.60647,
 -4.44456,   -4.27998,   -4.11282,   -3.94319,
 -3.77117,   -3.59689,   -3.42044,   -3.24193,
 -3.06147,   -2.87916,   -2.69512,   -2.50945,
 -2.32228,   -2.1337,    -1.94384,   -1.75281,
 -1.56072,   -1.3677,    -1.17384,   -0.979285,
 -0.784137,  -0.588517,  -0.392541,  -0.19633,
]

def WARPCALC(s, t):
    return  ((s + turbsin[int((t*2)+(cl_main.cl.time*(128.0/math.pi))) & 255 - 1]) * (1.0/64))

def WARPCALC2(s,t):
    return ((s + turbsin[int((t*0.125+cl_main.cl.time)*(128.0/math.pi)) & 255]) * (1.0/64))


def BoundPoly(numverts: int, verts: list[float], mins: list[float], maxs: list[float]):
    mins[0] = mins[1] = mins[2] = mathlib.FLT_MAX
    maxs[0] = maxs[1] = maxs[2] = -mathlib.FLT_MAX

    v_idx = 0
    for i in range(numverts):
        for j in range(3):
            val = verts[v_idx]
            mins[j] = min(mins[j], val)
            maxs[j] = max(maxs[j], val)
            v_idx += 1


def SubdividePolygon(numverts: int, verts: list[float]) -> None:
    """Recursively subdivides a polygon along world axes based on gl_subdivide_size.

    Once bounded, creates a new glpoly_t node, links it to warpface->polys,
    and projects (s, t) texture coordinates via texinfo vectors.

    C equivalent:
    static void SubdividePolygon (int numverts, float *verts) in r_surf.c
    """
    if numverts > 60:
        sys_sdl_unix.Sys_Error(f"SubdividePolygon: numverts = {numverts}")

    mins: list[float] = [0.0, 0.0, 0.0]
    maxs: list[float] = [0.0, 0.0, 0.0]
    BoundPoly(numverts, verts, mins, maxs)

    subdivide_size = cvar.Cvar_GetCvar("r_subdivide_size").value

    for i in range(3):
        m = (mins[i] + maxs[i]) * 0.5
        m = subdivide_size * math.floor(m / subdivide_size + 0.5)

        if maxs[i] - m < 8:
            continue
        if m - mins[i] < 8:
            continue

        # Cut plane distances
        dist = [0.0] * 64
        v_idx = i
        for j in range(numverts):
            dist[j] = verts[v_idx] - m
            v_idx += 3

        # Wrap case (copy first vertex to end to close edge loop)
        dist[numverts] = dist[0]

        # Temporary 2D vertex array buffers (64 vertices x 3 float components)
        front: list[list[float]] = [[0.0, 0.0, 0.0] for _ in range(64)]
        back: list[list[float]] = [[0.0, 0.0, 0.0] for _ in range(64)]

        f = 0
        b = 0
        v_idx = 0

        for j in range(numverts):
            v_curr = verts[v_idx : v_idx + 3]

            if dist[j] >= 0:
                mathlib.VectorCopy(v_curr, front[f])
                f += 1

            if dist[j] <= 0:
                mathlib.VectorCopy(v_curr, back[b])
                b += 1

            if dist[j] == 0 or dist[j + 1] == 0:
                v_idx += 3
                continue

            if (dist[j] > 0) != (dist[j + 1] > 0):
                # Calculate edge intersection fraction along cut plane
                frac = dist[j] / (dist[j] - dist[j + 1])
                v_next = (
                    verts[v_idx + 3 : v_idx + 6]
                    if (v_idx + 3 < numverts * 3)
                    else verts[:3]
                )

                # Interpolate split vertex coordinates
                for k in range(3):
                    front[f][k] = back[b][k] = v_curr[k] + frac * (
                        v_next[k] - v_curr[k]
                    )

                f += 1
                b += 1

            v_idx += 3

        # Flatten 2D front and back vertex buffers for recursive call
        front_flat = [coord for vert in front[:f] for coord in vert]
        back_flat = [coord for vert in back[:b] for coord in vert]

        SubdividePolygon(f, front_flat)
        SubdividePolygon(b, back_flat)
        return

    # Polygon is small enough; create glpoly_t object and link to warpface chain
    poly = quakedef.glpoly_t(numverts)

    # Insert node into linked list: poly->next = warpface->polys->next
    poly.next = warpface.polys.next
    warpface.polys.next = poly
    poly.numverts = numverts

    v_idx = 0
    texinfo = warpface.texinfo

    for i in range(numverts):
        v_curr = verts[v_idx : v_idx + 3]

        # Copy 3D position
        mathlib.VectorCopy(v_curr, poly.verts[i])

        # Project texture (s, t) coordinates using texinfo plane vectors
        s = (
            mathlib.DotProduct(v_curr, texinfo.vecs[0][:3])
            + texinfo.vecs[0][3]
        )
        t = (
            mathlib.DotProduct(v_curr, texinfo.vecs[1][:3])
            + texinfo.vecs[1][3]
        )

        # Assign calculated texture coordinates to vertex stride offset [3] and [4]
        poly.verts[i][3] = s
        poly.verts[i][4] = t

        v_idx += 3

def GL_SubdivideSurface(fa: quakedef.msurface_t) -> None:
    # Buffer to hold up to 64 vertices * 3 components (x, y, z)
    verts: list[float] = [0.0] * (64 * 3)

    if fa.polys.numverts > 64:
        sys_sdl_unix.Sys_Error(
            f"GL_SubdivideSurface: numverts = {fa.polys.numverts}"
        )

    # Set active warpface reference
    global warpface
    warpface = fa

    # Copy 3D vertex position coordinates into flat contiguous float buffer
    v_idx = 0
    for i in range(fa.polys.numverts):
        mathlib.VectorCopy(fa.polys.verts[i], verts[v_idx : v_idx + 3])
        v_idx += 3

    # Pass the flattened vertex coordinate list directly
    SubdividePolygon(fa.polys.numverts, verts)


def DrawWaterPoly(p: quakedef.glpoly_t) -> None:
    subdivide_size = cvar.Cvar_GetCvar("r_subdivide_size").value

    gl.glBegin(gl.GL_POLYGON)

    if subdivide_size > 48:
        for i in range(p.numverts):
            v = p.verts[i]
            # Emit warped texture coordinates (s, t)
            gl.glTexCoord2f(
                WARPCALC2(v[3], v[4]),
                WARPCALC2(v[4], v[3]),
            )
            # Emit 3D vertex position (x, y, z)
            gl.glVertex3fv(v[:3])
    else:
        for i in range(p.numverts):
            v = p.verts[i]
            gl.glTexCoord2f(
                WARPCALC(v[3], v[4]),
                WARPCALC(v[4], v[3]),
            )
            gl.glVertex3fv(v[:3])

    gl.glEnd()


def R_UpdateWarpTextures():
    r_oldwater     = cvar.Cvar_GetCvar('r_oldwater').value
    r_waterquality = cvar.Cvar_GetCvar('r_waterquality').value

    if r_oldwater or cl_main.cl.paused or gl_rmain.r_drawflat_cheatsafe or gl_rmain.r_lightmap_cheatsafe:
        return

    warptess = 128.0/common.CLAMP (3.0, math.floor(r_waterquality), 64.0)

    for i in range(cl_main.cl.worldmodel.numtextures):
        tx: quakedef.texture_t = cl_main.cl.worldmodel.textures[i]

        if not tx:
            continue

        if not tx.update_warp:
            continue

        gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_WARPIMAGE)
        gl_texmgr.GL_Bind(tx.gltexture)

        x = 0.0
        while x < 128.0:
            x2 = x + warptess
            gl.glBegin(gl.GL_TRIANGLE_STRIP)

            y = 0.0
            while y < 128.01:
                gl.glTexCoord2f( WARPCALC(x, y), WARPCALC(y, x) )
                gl.glVertex2f(x, y)
                gl.glTexCoord2f(WARPCALC(x2, y), WARPCALC(y, x2))
                gl.glVertex2f(x2, y)
                y += warptess

            gl.glEnd()
            x = x2

        gl_texmgr.GL_Bind(tx.warpimage)
        gl.glCopyTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, gl_screen.glx, gl_screen.gly + gl_screen.glheight - gl_warpimagesize, gl_warpimagesize, gl_warpimagesize)

        gl.glGenerateMipmap(gl.GL_TEXTURE_2D)

        tx.update_warp = False

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_DEFAULT)

    if gl_warpimagesize + sbar.sb_lines > gl_screen.glheight:
        sbar.Sbar_Changed()

    gl_screen.scr_tileclear_updates = 0

