#r_sprite.py

import math

from OpenGL import GL as gl

import cl_main
import console
import gl_rmain
import glquake
import mathlib
import quakedef
import render
import spritegn


def R_GetSpriteFrame(currentent: render.entity_t) -> quakedef.mspriteframe_t:
    psprite: quakedef.msprite_t = None
    pspritegroup: quakedef.mspritegroup_t = None
    pspriteframe: quakedef.mspriteframe_t = None

    psprite = currentent.model.cache.data
    frame = currentent.frame

    if frame >= psprite.numframes or frame < 0:
        console.Con_Warning(f'R_DrawSprite: no such frame {frame} for "{currentent.model.name}"\n')
        frame = 0

    if psprite.frames[frame].type == spritegn.spriteframetype_t.SPR_SINGLE:
        pspriteframe = psprite.frames[frame].frameptr

    if psprite.frames[frame].type == spritegn.spriteframetype_t.SPR_ANGLED:
        axis: list[quakedef.vec3_t] = [
            [0.0, 0.0, 0.0],  # axis[0] -> forward
            [0.0, 0.0, 0.0],  # axis[1] -> right
            [0.0, 0.0, 0.0]   # axis[2] -> up
        ]
        mathlib.AngleVectors(gl_rmain.currententity.angles, axis[0], axis[1], axis[2])

        f = mathlib.DotProduct(gl_rmain.vpn, axis[0])
        r = mathlib.DotProduct(gl_rmain.vright, axis[0])
        dir = (math.atan2(r, f)+1.125*math.pi)*(4/math.pi)
        pspritegroup = psprite.frames[frame].frameptr
        pspriteframe = pspritegroup.frames[dir & 7]
    else:
        pspritegroup = psprite.frames[frame].frameptr
        pintervals = pspritegroup.intervals
        numframes = pspritegroup.numframes
        fullinterval = pintervals[numframes - 1]

        time = cl_main.cl.time + currentent.syncbase

        targettime = time - ((int)(time / fullinterval)) * fullinterval

        for i in range(numframes-1):
            if pintervals[i] > targettime:
                break
        pspriteframe = pspritegroup.frames[i]

    return pspriteframe



def R_DrawSpriteModel(e: render.entity_t) -> None:
    """
    C equivalent (r_brush.c / gl_rmain.c):
    void R_DrawSpriteModel (entity_t *e)

    Renders view-facing, parallel-upright, oriented, and roll-adjusted
    3D sprite models using geometry vector transformations.
    """
    v_forward: quakedef.vec3_t = [0.0, 0.0, 0.0]
    v_right: quakedef.vec3_t = [0.0, 0.0, 0.0]
    v_up: quakedef.vec3_t = [0.0, 0.0, 0.0]
    point: quakedef.vec3_t = [0.0, 0.0, 0.0]

    # Decode entity scale or default to 1.0
    scale: float = gl_rmain.ENTSCALE_DECODE(e.scale)

    frame = render.R_GetSpriteFrame(e)
    psprite = gl_rmain.currententity.model.cache.data

    s_up: list[float]
    s_right: list[float]

    # 1. Orient sprite coordinate axes based on sprite orientation type
    match psprite.type:
        case glquake.SPR_VP_PARALLEL_UPRIGHT:
            # Faces view plane, up is towards the heavens (0, 0, 1)
            v_up[0], v_up[1], v_up[2] = 0.0, 0.0, 1.0
            mathlib.CrossProduct(gl_rmain.vpn, v_up, v_right)
            mathlib.VectorNormalizeFast(v_right)
            s_up = v_up
            s_right = v_right

        case glquake.SPR_FACING_UPRIGHT:
            # Faces camera origin, up is towards the heavens
            mathlib.VectorSubtract(gl_rmain.currententity.origin, gl_rmain.r_origin, v_forward)
            v_forward[2] = 0.0
            mathlib.VectorNormalizeFast(v_forward)
            v_right[0] = v_forward[1]
            v_right[1] = -v_forward[0]
            v_right[2] = 0.0
            v_up[0], v_up[1], v_up[2] = 0.0, 0.0, 1.0
            s_up = v_up
            s_right = v_right

        case glquake.SPR_VP_PARALLEL:
            # Faces view plane, up is towards top of screen
            s_up = gl_rmain.vup
            s_right = gl_rmain.vright

        case glquake.SPR_ORIENTED:
            # Pitch, yaw, roll independent of camera orientation
            mathlib.AngleVectors(gl_rmain.currententity.angles, v_forward, v_right, v_up)
            s_up = v_up
            s_right = v_right

        case glquake.SPR_VP_PARALLEL_ORIENTED:
            # Faces view plane, but obeys entity roll rotation
            angle = gl_rmain.currententity.angles[quakedef.ROLL] * mathlib.M_PI_DIV_180
            sr = math.sin(angle)
            cr = math.cos(angle)

            v_right[0] = gl_rmain.vright[0] * cr + gl_rmain.vup[0] * sr
            v_right[1] = gl_rmain.vright[1] * cr + gl_rmain.vup[1] * sr
            v_right[2] = gl_rmain.vright[2] * cr + gl_rmain.vup[2] * sr

            v_up[0] = gl_rmain.vright[0] * -sr + gl_rmain.vup[0] * cr
            v_up[1] = gl_rmain.vright[1] * -sr + gl_rmain.vup[1] * cr
            v_up[2] = gl_rmain.vright[2] * -sr + gl_rmain.vup[2] * cr

            s_up = v_up
            s_right = v_right

        case _:
            return

    # 2. Polygon depth offset for decal sprites
    if psprite.type == glquake.SPR_ORIENTED:
        gl_rmain.GL_PolygonOffset(gl_rmain.OFFSET_DECAL)

    gl.glColor3f(1.0, 1.0, 1.0)
    gl_rmain.GL_DisableMultitexture()
    gl_rmain.GL_Bind(frame.gltexture)

    gl.glEnable(gl.GL_ALPHA_TEST)
    gl.glBegin(gl.GL_TRIANGLE_FAN)

    # Vertex 1: Bottom-Left (Down, Left)
    gl.glTexCoord2f(0.0, frame.tmax)
    mathlib.VectorMA(e.origin, frame.down * scale, s_up, point)
    mathlib.VectorMA(point, frame.left * scale, s_right, point)
    gl.glVertex3fv(point)

    # Vertex 2: Top-Left (Up, Left)
    gl.glTexCoord2f(0.0, 0.0)
    mathlib.VectorMA(e.origin, frame.up * scale, s_up, point)
    mathlib.VectorMA(point, frame.left * scale, s_right, point)
    gl.glVertex3fv(point)

    # Vertex 3: Top-Right (Up, Right)
    gl.glTexCoord2f(frame.smax, 0.0)
    mathlib.VectorMA(e.origin, frame.up * scale, s_up, point)
    mathlib.VectorMA(point, frame.right * scale, s_right, point)
    gl.glVertex3fv(point)

    # Vertex 4: Bottom-Right (Down, Right)
    gl.glTexCoord2f(frame.smax, frame.tmax)
    mathlib.VectorMA(e.origin, frame.down * scale, s_up, point)
    mathlib.VectorMA(point, frame.right * scale, s_right, point)
    gl.glVertex3fv(point)

    gl.glEnd()
    gl.glDisable(gl.GL_ALPHA_TEST)

    # Reset polygon depth offset state
    if psprite.type == glquake.SPR_ORIENTED:
        gl_rmain.GL_PolygonOffset(gl_rmain.OFFSET_NONE)