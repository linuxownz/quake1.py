#gl_rlight.py

import math

import OpenGL.GL as gl

import cl_main
import cvar
import gl_rmain
import mathlib
import quakedef
import view

r_dlightframecount = 0

lightspot: list[float] = [0, 0, 0]
lightcolor: list[float] = [0, 0, 0]

def R_AnimateLight():
    """Calculates frame-by-frame light style interpolation values.

    C equivalent:
    void R_AnimateLight (void) in r_main.c
    """
    i = int(cl_main.cl.time * 10)

    r_flatlightstyles = cvar.Cvar_GetCvar("r_flatlightstyles").value

    for j in range(quakedef.MAX_LIGHTSTYLES):
        ls = cl_main.cl_lightstyle[j]

        if not ls.length:
            gl_rmain.d_lightstylevalue[j] = 256
            continue

        if r_flatlightstyles == 2:
            val = ls.peak
            k = (ord(val) if isinstance(val, str) else val) - ord("a")
        elif r_flatlightstyles == 1:
            val = ls.average
            k = (ord(val) if isinstance(val, str) else val) - ord("a")
        else:
            idx = i % ls.length
            val = ls.map[idx]
            k = (ord(val) if isinstance(val, str) else val) - ord("a")

        gl_rmain.d_lightstylevalue[j] = k * 22


def AddLightBlend(r: float, g: float, b: float, a2: float):
    a: float = 0.0

    view.v_blend[3] = a = view.v_blend[3] + a2 * ( 1 - view.v_blend[3])

    a2 = a2/a

    view.v_blend[0] = view.v_blend[0] * (1-a2) + r * a2
    view.v_blend[1] = view.v_blend[1] * (1-a2) + g * a2
    view.v_blend[2] = view.v_blend[2] * (1-a2) + b * a2

def R_RenderDlight(light: quakedef.dlight_t):
    v:list[float] = [0, 0, 0]
    rad = light.radius * 0.35

    mathlib.VectorSubtract(light.origin, gl_rmain.r_origin, v)

    if mathlib.VectorLength(v) < rad:
        AddLightBlend(1, 0.5, 0, light.radius * 0.0003)
        return

    gl.glBegin(gl.GL_TRIANGLE_FAN)
    gl.glColor3f(0.2, .1, 0)

    for i in range(3):
        v[i] = light.origin[i] - gl_rmain.vpn[i] * rad

    gl.glVertex3fv(v)
    gl.glColor3f(0, 0, 0)

    for i in range(16, -1, -1):
        a = ( i / 16.0 )  * math.pi * 2.
        for j in range(3):
            v[j] = light.origin[j] + gl_rmain.vright[j] * math.cos(a) * rad + gl_rmain.vup[j] * math.sin(a) * rad

        gl.glVertex3fv(v)

    gl.glEnd()

def R_RenderDlights():
    global r_dlightframecount

    if cvar.Cvar_GetCvar('gl_flashblend').value:
        return

    r_dlightframecount = gl_rmain.r_framecount + 1
    gl.glDepthMask(0)
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glShadeModel(gl.GL_SMOOTH)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE)

    for i in range(quakedef.MAX_DLIGHTS):
        dl = cl_main.cl_dlights[i]
        if dl.die < cl_main.cl.time or not dl.radius:
            continue

        R_RenderDlight(dl)

    gl.glColor3f(1.0, 1.0, 1.0)
    gl.glDisable(gl.GL_BLEND)
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glDepthMask(1)
    gl.glShadeModel(gl.GL_FLAT)


import cl_main
import gl_rmain
import mathlib


def R_MarkLights(light, num, node):
    """Traverses the BSP tree to tag world surfaces affected by dynamic lights.

    C equivalent:
    void R_MarkLights (dlight_t *light, int num, mnode_t *node) in r_main.c
    """
    # 1. BSP Node Traversal Loop (replaces C goto start)
    while node:
        if node.contents < 0:  # Leaf node reached
            return

        splitplane = node.plane
        if splitplane.type < 3:
            dist = light.origin[splitplane.type] - splitplane.dist
        else:
            dist = (
                mathlib.DotProduct(light.origin, splitplane.normal)
                - splitplane.dist
            )

        if dist > light.radius:
            node = node.children[0]
            continue

        if dist < -light.radius:
            node = node.children[1]
            continue

        break

    if not node or node.contents < 0:
        return

    maxdist = light.radius * light.radius
    impact = [0.0, 0.0, 0.0]

    # 2. Test dynamic light influence on node surfaces
    # Access surfaces slice from worldmodel.surfaces array
    first_surf_idx = node.firstsurface
    surfaces = cl_main.cl.worldmodel.surfaces

    for i in range(node.numsurfaces):
        surf = surfaces[first_surf_idx + i]

        # Calculate light projection onto surface plane
        for j in range(3):
            impact[j] = light.origin[j] - surf.plane.normal[j] * dist

        # S-coordinate distance check
        vec_s = surf.texinfo.vecs[0]
        l = (
            mathlib.DotProduct(impact, vec_s)
            + vec_s[3]
            - surf.texturemins[0]
        )
        s = int(l + 0.5)
        if s < 0:
            s = 0
        elif s > surf.extents[0]:
            s = surf.extents[0]
        s = l - s

        # T-coordinate distance check
        vec_t = surf.texinfo.vecs[1]
        l = (
            mathlib.DotProduct(impact, vec_t)
            + vec_t[3]
            - surf.texturemins[1]
        )
        t = int(l + 0.5)
        if t < 0:
            t = 0
        elif t > surf.extents[1]:
            t = surf.extents[1]
        t = l - t

        # Compare squared radial distance to surface light bounds
        if (s * s + t * t + dist * dist) < maxdist:
            bit_index = num >> 5
            bit_flag = 1 << (num & 31)

            if surf.dlightframe != r_dlightframecount:
                surf.dlightbits = [0, 0]
                surf.dlightframe = r_dlightframecount
            surf.dlightbits[bit_index] |= bit_flag

    # 3. Recurse down both child branches
    if node.children[0].contents >= 0:
        R_MarkLights(light, num, node.children[0])

    if node.children[1].contents >= 0:
        R_MarkLights(light, num, node.children[1])


def R_PushDlights():
    global r_dlightframecount

    if cvar.Cvar_GetCvar('gl_flashblend').value:
        return

    r_dlightframecount = gl_rmain.r_framecount + 1

    for i in range(quakedef.MAX_DLIGHTS):
        l = cl_main.cl_dlights[i]
        if l.die < cl_main.cl.time or not l.radius:
            continue
        R_MarkLights(l, i, cl_main.cl.worldmodel.nodes[0])
        #R_MarkLights(l, 1 << i, cl_main.cl.worldmodel.nodes)


SURF_DRAWTILED = 0x20
MAXLIGHTMAPS = 4


def RecursiveLightPoint(color, node, rayorg, start, end, maxdist):
    """Raycasts down the world BSP tree to sample interpolated lightmap color.

    C equivalent:
    int RecursiveLightPoint (vec3_t color, mnode_t *node, vec3_t rayorg,
                             vec3_t start, vec3_t end, float *maxdist) in r_main.c
    """
    # 1. BSP Node Traversal Loop (replaces C goto loc0)
    while node:
        if node.contents < 0:  # Leaf node reached (no collision)
            return False

        plane = node.plane
        if plane.type < 3:
            front = start[plane.type] - plane.dist
            back = end[plane.type] - plane.dist
        else:
            front = mathlib.DotProduct(start, plane.normal) - plane.dist
            back = mathlib.DotProduct(end, plane.normal) - plane.dist

        # LordHavoc optimized branch recursion check
        if (back < 0) == (front < 0):
            node = node.children[1 if front < 0 else 0]
            continue
        break

    if not node or node.contents < 0:
        return False

    # 2. Calculate mid intersection point along splitting plane
    frac = front / (front - back)
    mid = [
        start[0] + (end[0] - start[0]) * frac,
        start[1] + (end[1] - start[1]) * frac,
        start[2] + (end[2] - start[2]) * frac,
    ]

    # 3. Traverse down front side
    front_child_idx = 1 if front < 0 else 0
    if RecursiveLightPoint(color, node.children[front_child_idx], rayorg, start, mid, maxdist):
        return True

    # 4. Check surfaces on current node for ray impact
    lightspot[0] = mid[0]
    lightspot[1] = mid[1]
    lightspot[2] = mid[2]

    surfaces = cl_main.cl.worldmodel.surfaces
    first_surf_idx = node.firstsurface

    for i in range(node.numsurfaces):
        surf = surfaces[first_surf_idx + i]

        if surf.flags & SURF_DRAWTILED:
            continue

        # Double precision dot product simulation for texcoord calculation
        vec_s = surf.texinfo.vecs[0]
        vec_t = surf.texinfo.vecs[1]
        ds = int(mathlib.DotProduct(mid, vec_s) + vec_s[3])
        dt = int(mathlib.DotProduct(mid, vec_t) + vec_t[3])

        if ds < surf.texturemins[0] or dt < surf.texturemins[1]:
            continue

        ds -= surf.texturemins[0]
        dt -= surf.texturemins[1]

        if ds > surf.extents[0] or dt > surf.extents[1]:
            continue

        surf_plane = surf.plane
        if surf_plane.type < 3:
            sfront = rayorg[surf_plane.type] - surf_plane.dist
            sback = end[surf_plane.type] - surf_plane.dist
        else:
            sfront = mathlib.DotProduct(rayorg, surf_plane.normal) - surf_plane.dist
            sback = mathlib.DotProduct(end, surf_plane.normal) - surf_plane.dist

        raydelta = [0.0, 0.0, 0.0]
        mathlib.VectorSubtract(end, rayorg, raydelta)
        dist = (sfront / (sfront - sback)) * mathlib.VectorLength(raydelta)

        if surf.samples is None:
            nearby = 8.0
            dist += nearby
            maxdist[0] = min(maxdist[0], dist)
            continue

        if dist < maxdist[0]:
            # Bilinear lightmap color interpolation (LordHavoc colored lighting)
            dsfrac = ds & 15
            dtfrac = dt & 15
            w = (surf.extents[0] >> 4) + 1
            h = (surf.extents[1] >> 4) + 1
            line3 = w * 3

            sample_offset = ((dt >> 4) * w + (ds >> 4)) * 3
            sample_stride = w * h * 3

            # surf.samples is an integer offset into worldmodel.lightdata
            lightdata = cl_main.cl.worldmodel.lightdata
            base = surf.samples

            r00 = g00 = b00 = 0
            r01 = g01 = b01 = 0
            r10 = g10 = b10 = 0
            r11 = g11 = b11 = 0

            for maps in range(MAXLIGHTMAPS):
                if surf.styles[maps] == 255:
                    break

                scale = int(gl_rmain.d_lightstylevalue[surf.styles[maps]])
                lm_ptr = sample_offset + (maps * sample_stride)

                r00 += lightdata[base + lm_ptr + 0] * scale
                g00 += lightdata[base + lm_ptr + 1] * scale
                b00 += lightdata[base + lm_ptr + 2] * scale

                r01 += lightdata[base + lm_ptr + 3] * scale
                g01 += lightdata[base + lm_ptr + 4] * scale
                b01 += lightdata[base + lm_ptr + 5] * scale

                r10 += lightdata[base + lm_ptr + line3 + 0] * scale
                g10 += lightdata[base + lm_ptr + line3 + 1] * scale
                b10 += lightdata[base + lm_ptr + line3 + 2] * scale

                r11 += lightdata[base + lm_ptr + line3 + 3] * scale
                g11 += lightdata[base + lm_ptr + line3 + 4] * scale
                b11 += lightdata[base + lm_ptr + line3 + 5] * scale

            # Bilinear sampling with integer shifts (as in C); the style scale is
            # an integer (~256 = 1.0), so divide by 256 once at the end.
            def _bilerp(v00, v01, v10, v11):
                top = (((v01 - v00) * dsfrac) >> 4) + v00
                bot = (((v11 - v10) * dsfrac) >> 4) + v10
                return (((bot - top) * dtfrac) >> 4) + top

            color[0] += _bilerp(r00, r01, r10, r11) / 256.0
            color[1] += _bilerp(g00, g01, g10, g11) / 256.0
            color[2] += _bilerp(b00, b01, b10, b11) / 256.0

        return True

    # 5. Traverse down back side
    back_child_idx = 0 if front < 0 else 1
    return RecursiveLightPoint(color, node.children[back_child_idx], rayorg, mid, end, maxdist)


def R_LightPoint(p: list[float]) -> int:
    end: list[float] = [0, 0, 0]
    maxdist: float = 8192.0

    if not cl_main.cl.worldmodel.lightdata:
        lightcolor[0] = lightcolor[1] = lightcolor[2] = 255
        return 255

    end[0] = p[0]
    end[1] = p[1]
    end[2] = p[2] - maxdist

    lightcolor[0] = lightcolor[1] = lightcolor[2] = 0
    # maxdist is a float* in C, so pass a one-element list; nodes[0] is the root node
    RecursiveLightPoint(lightcolor, cl_main.cl.worldmodel.nodes[0], p, p, end, [maxdist])

    return (lightcolor[0] + lightcolor[1] + lightcolor[2]) * (1.0 / 3.0)