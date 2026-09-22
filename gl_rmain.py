#gl_rmain.py

from __future__ import annotations

import ctypes
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import quakedef

import OpenGL.GL as gl
import OpenGL.GLU as glu

import bspfile
import cl_main
import common
import console
import cvar
import gl_fog
import gl_model
import gl_rlight
import gl_rmisc
import gl_screen
import gl_sky
import gl_texmgr
import gl_vidsdl
import gl_warp
import glquake
import mathlib
import progs
import protocol

# import quakedef
import r_alias
import r_brush
import r_part
import r_world
import render
import sbar
import snd_dma
import sv_main
import sv_user
import sys_sdl_unix
import view


class NotInitedError(RuntimeError):
    pass

modelorg    = [0, 0, 0]
r_entorigin = [0, 0, 0]

currententity : render.entity_t = None

r_visframecount = 0
r_framecount = 0

#frustum : list[quakedef.mplane_t] = [ quakedef.mplane_t(0, 0, 0, 0) for i in range(4)]

rs_brushpolys       = 0
rs_aliaspolys       = 0
rs_skypolys         = 0
rs_dynamiclightmaps = 0
rs_brushpasses      = 0
rs_aliaspasses      = 0
rs_skypasses        = 0

vup       = [0, 0, 0]
vpn       = [0, 0, 0]
vright    = [0, 0, 0]
r_origin  = [0, 0, 0]

r_fovx = 0.0
r_fovy = 0.0

#r_refdef : quakedef.refdef_t = quakedef.refdef_t()

r_viewleaf    : quakedef.mleaf_t = None
r_oldviewleaf : quakedef.mleaf_t = None

d_lightstylevalue = [ 0 for i in range(256)]

map_wateralpha = 0
map_lavaalpha  = 0
map_telealpha  = 0
map_slimealpha = 0

r_drawflat_cheatsafe   = False
r_fullbright_cheatsafe = False
r_lightmap_cheatsafe   = False
r_drawworld_cheatsafe  = False

r_gamma_texture = 0
r_gamma_program = 0

r_gamma_texture_width = 0
r_gamma_texture_height = 0

gammaLoc = 0
contrastLoc = 0
textureLoc = 0

NEARCLIP = 4

frustum_skew = 0.0

inited = False

r_scaleview_texture: int = 0
r_scaleview_texture_width: int = 0
r_scaleview_texture_height: int = 0

def GLSLGamma_CreateShaders():
    vertSource = """
    #version 110
    void main(void) {
        gl_Position = vec4(gl_Vertex.xy, 0.0, 1.0);
        gl_TexCoord[0] = gl_MultiTexCoord0;
    }
    """

    fragSource = """
    #version 110

    uniform sampler2D GammaTexture;
    uniform float GammaValue;
    uniform float ContrastValue;

    void main(void) {
        vec4 frag = texture2D(GammaTexture, gl_TexCoord[0].xy);
        frag.rgb = frag.rgb * ContrastValue;
        gl_FragColor = vec4(pow(frag.rgb, vec3(GammaValue)), 1.0);
    }
    """

    if not gl_vidsdl.gl_glsl_gamma_able:
        return

    global r_gamma_program, gammaLoc, contrastLoc, textureLoc
    r_gamma_program = gl_rmisc.GL_CreateProgram(vertSource, fragSource, 0, None)

    gammaLoc = gl_rmisc.GL_GetUniformLocation( r_gamma_program, 'GammaValue')
    contrastLoc = gl_rmisc.GL_GetUniformLocation( r_gamma_program, 'ContrastValue')
    gammaLoc = gl_rmisc.GL_GetUniformLocation( r_gamma_program, 'GammaTexture')


def GLSLGamma_GammaCorrect():
    global r_gamma_texture, r_gamma_texture_width, r_gamma_texture_height
    global r_gamma_program, gammaLoc, contrastLoc, textureLoc

    smax: float = 0.0
    tmax: float = 0.0

    if not gl_vidsdl.gl_glsl_gamma_able:
        return

    if  cvar.Cvar_GetCvar('vid_gamma').value == 1 and cvar.Cvar_GetCvar('vid_contrast').value == 1:
        return

    if not r_gamma_texture:
        tex_id = (ctypes.c_uint * 1)()
        gl.glGenTextures(1, tex_id)
        r_gamma_texture = tex_id[0]

        gl.glBindTexture(gl.GL_TEXTURE_2D, r_gamma_texture)

        r_gamma_texture_width = gl_screen.glwidth
        r_gamma_texture_height = gl_screen.glheight

        if not gl_vidsdl.gl_texture_NPOT:
            r_gamma_texture_width = gl_texmgr.TexMgr_Pad(r_gamma_texture_width)
            r_gamma_texture_height = gl_texmgr.TexMgr_Pad(r_gamma_texture_height)

        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, r_gamma_texture_width, r_gamma_texture_height, 0, gl.GL_BGRA, gl.GL_UNSIGNED_INT_8_8_8_8_REV, None)
        gl.glTexParameteri (gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri (gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)

    if not r_gamma_program:
        GLSLGamma_CreateShaders()
        if not r_gamma_program:
            sys_sdl_unix.Sys_Error('GLSLGamma_CreateShaders failed')

    gl_texmgr.GL_DisableMultitexture()
    gl.glBindTexture(gl.GL_TEXTURE_2D, r_gamma_texture)
    gl.glCopyTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, gl_screen.glx, gl_screen.gly, gl_screen.glwidth, gl_screen.glheight)

    gl.glUseProgram(r_gamma_program)
    vid_gamma = cvar.Cvar_GetCvar("vid_gamma").value
    vid_contrast = cvar.Cvar_GetCvar("vid_contrast").value

    contrast_val = min(2.0, max(1.0, vid_contrast))

    gl.glUniform1f(gammaLoc, vid_gamma)
    gl.glUniform1f(contrastLoc, contrast_val)
    gl.glUniform1i(textureLoc, 0)

    gl.glDisable(gl.GL_ALPHA_TEST)
    gl.glDisable(gl.GL_DEPTH_TEST)

    gl.glViewport(gl_screen.glx, gl_screen.gly, gl_screen.glwidth, gl_screen.glheight)

    smax = gl_screen.glwidth/r_gamma_texture_width
    tmax = gl_screen.glheight/r_gamma_texture_height

    gl.glBegin(gl.GL_QUADS)
    gl.glTexCoord2f (0, 0);
    gl.glVertex2f (-1, -1);
    gl.glTexCoord2f (smax, 0);
    gl.glVertex2f (1, -1);
    gl.glTexCoord2f (smax, tmax)
    gl.glVertex2f (1, 1);
    gl.glTexCoord2f (0, tmax);
    gl.glVertex2f (-1, 1);
    gl.glEnd ();

    gl.glUseProgram(0)

    gl_texmgr.GL_ClearBindings ();


def R_CullBox(emins: list[float], emaxs: list[float]) -> bool:
    if not inited:
        raise NotInitedError

    for i in range(4):
        p = frustum[i]
        signbits = p.signbits

        p0 = (emins if (signbits & 1) else emaxs)[0]
        p1 = (emins if (signbits & 2) else emaxs)[1]
        p2 = (emins if (signbits & 4) else emaxs)[2]

        if (p.normal[0] * p0 + p.normal[1] * p1 + p.normal[2] * p2) < p.dist:
            return True

    return False


def R_CullModelForEntity(e: render.entity_t):

    mins: list[float] = [0, 0, 0]
    maxs: list[float] = [0, 0, 0]

    if e.angles[0] or e.angles[2]:
        minbounds = e.model.rmins
        maxbounds = e.model.rmaxs
    elif e.angles[1]:
        minbounds = e.model.ymins
        maxbounds = e.model.ymaxs
    else:
        minbounds = e.model.mins
        maxbounds = e.model.maxs

    scalefactor = protocol.ENTSCALE_DECODE(e.scale)

    if scalefactor != 1.0:
        mathlib.VectorMA(e.origin, scalefactor, minbounds, mins)
        mathlib.VectorMA(e.origin, scalefactor, maxbounds, maxs)
    else:
        mathlib.VectorAdd(e.origin, minbounds, mins)
        mathlib.VectorAdd(e.origin, maxbounds, maxs)

    return R_CullBox(mins, maxs)


def R_RotateForEntity(origin: list[float], angles:list[float], scale: int):
    scalefactor = protocol.ENTSCALE_DECODE(scale)

    gl.glTranslatef(origin[0], origin[1], origin[2])
    gl.glRotatef (angles[1],  0, 0, 1);
    gl.glRotatef (-angles[0],  0, 1, 0);
    gl.glRotatef (angles[2],  1, 0, 0);

    if scalefactor != 1.0:
        gl.glScalef(scalefactor, scalefactor, scalefactor);


def GL_PolygonOffset(offset: int):
    if offset > 0:
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glEnable(gl.GL_POLYGON_OFFSET_LINE)
        gl.glPolygonOffset(1, offset)
    elif offset < 0:
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glEnable(gl.GL_POLYGON_OFFSET_LINE)
        gl.glPolygonOffset(-1, offset)
    else:
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glDisable(gl.GL_POLYGON_OFFSET_LINE)



def SignbitsForPlane(out: quakedef.mplane_t):
    bits = 0
    for j in range(3):
        if out.normal[j] < 0:
            bits |= 1 << j
    return bits



def TurnVector(out: list[float], forward: list[float], side: list[float], angle: float):
    scale_forward = math.cos(mathlib.DEG2RAD(angle))
    scale_side    = math.sin(mathlib.DEG2RAD(angle))

    out[0] = scale_forward * forward[0] + scale_side * side[0]
    out[1] = scale_forward * forward[1] + scale_side * side[1]
    out[2] = scale_forward * forward[2] + scale_side * side[2]


def R_SetFrustum(fovx: float, fovy: float):
    if cvar.Cvar_GetCvar('r_stereo').value:
        fovx += 10

    TurnVector(frustum[0].normal, vpn, vright, fovx/2 - 90)
    TurnVector(frustum[1].normal, vpn, vright, 90 - fovx/2)
    TurnVector(frustum[2].normal, vpn, vup, 90 - fovy/2)
    TurnVector(frustum[3].normal, vpn, vup, fovy/2 - 90)

    for i in range(4):
        frustum[i].type = quakedef.PLANE_ANYZ
        frustum[i].dist = mathlib.DotProduct(r_origin, frustum[i].normal)
        frustum[i].signbits = SignbitsForPlane(frustum[i])


def GL_SetFrustum(fovx, fovy):
    xmax = NEARCLIP * math.tan(fovx * math.pi / 360.0)
    ymax = NEARCLIP * math.tan(fovy * math.pi / 360.0)

    farclip = cvar.Cvar_GetCvar('gl_farclip').value

    gl.glFrustum(-xmax + frustum_skew, xmax + frustum_skew, -ymax, ymax, NEARCLIP, farclip)


def R_SetupGL():
    gl.glMatrixMode(gl.GL_PROJECTION)

    gl.glLoadIdentity()

    scale = common.CLAMP(1, cvar.Cvar_GetCvar('r_scale').value, 4 )

    gl.glViewport(gl_screen.glx + r_refdef.vrect.x, gl_screen.gly + gl_screen.glheight - r_refdef.vrect.y - r_refdef.vrect.height,
            r_refdef.vrect.width / scale, r_refdef.vrect.height / scale)

    GL_SetFrustum(r_fovx, r_fovy)

    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

    gl.glRotate(-90, 1, 0, 0)
    gl.glRotate(90, 0, 0, 1)
    gl.glRotatef (-r_refdef.viewangles[2],  1, 0, 0)
    gl.glRotatef (-r_refdef.viewangles[0],  0, 1, 0)
    gl.glRotatef (-r_refdef.viewangles[1],  0, 0, 1)
    gl.glTranslatef (-r_refdef.vieworg[0],  -r_refdef.vieworg[1],  -r_refdef.vieworg[2])

    if cvar.Cvar_GetCvar('gl_cull').value:
        gl.glEnable(gl.GL_CULL_FACE)
    else:
        gl.glDisable(gl.GL_CULL_FACE)

    gl.glDisable(gl.GL_BLEND)
    gl.glDisable(gl.GL_ALPHA_TEST)
    gl.glEnable(gl.GL_DEPTH_TEST)

    if not inited:
        gl_rmain_Init()


def R_Clear():
    clearbits = gl.GL_DEPTH_BUFFER_BIT

    if gl_vidsdl.gl_stencilbits:
        clearbits |= gl.GL_STENCIL_BUFFER_BIT

    if cvar.Cvar_GetCvar('gl_clear').value:
        clearbits |= gl.GL_COLOR_BUFFER_BIT

    gl.glClear(clearbits)



def gl_rmain_Init():
    global cvar, quakedef
    global frustum, r_refdef
    import cvar
    import quakedef

    r_refdef = quakedef.refdef_t()
    frustum = [ quakedef.mplane_t(0, 0, 0, 0) for i in range(4)]

    r_norefresh           = {'name': "r_norefresh",       'value':"0",        'flags': cvar.CVAR_NONE}
    r_drawentities        = {'name': "r_drawentities",    'value':"1",        'flags': cvar.CVAR_NONE}
    r_drawviewmodel       = {'name': "r_drawviewmodel",   'value':"1",        'flags': cvar.CVAR_NONE}
    r_speeds              = {'name': "r_speeds",          'value':"0",        'flags': cvar.CVAR_NONE}
    r_pos                 = {'name': "r_pos",             'value':"0",        'flags': cvar.CVAR_NONE}
    r_fullbright          = {'name': "r_fullbright",      'value':"0",        'flags': cvar.CVAR_NONE}
    r_lightmap            = {'name': "r_lightmap",        'value':"0",        'flags': cvar.CVAR_NONE}
    r_shadows             = {'name': "r_shadows",         'value':"0",        'flags': cvar.CVAR_ARCHIVE}
    r_wateralpha          = {'name': "r_wateralpha",      'value':"1",        'flags': cvar.CVAR_ARCHIVE}
    r_litwater            = {'name': "r_litwater",        'value':"1",        'flags': cvar.CVAR_NONE}
    r_dynamic             = {'name': "r_dynamic",         'value':"1",        'flags': cvar.CVAR_ARCHIVE}
    r_novis               = {'name': "r_novis",           'value':"0",        'flags': cvar.CVAR_ARCHIVE}

    gl_finish             = {'name': "gl_finish",         'value':"0",        'flags': cvar.CVAR_NONE}
    gl_clear              = {'name': "gl_clear",          'value':"1",        'flags': cvar.CVAR_NONE}
    gl_cull               = {'name': "gl_cull",           'value':"1",        'flags': cvar.CVAR_NONE}
    gl_smoothmodels       = {'name': "gl_smoothmodels",   'value':"1",        'flags': cvar.CVAR_NONE}
    gl_affinemodels       = {'name': "gl_affinemodels",   'value':"0",        'flags': cvar.CVAR_NONE}
    gl_polyblend          = {'name': "gl_polyblend",      'value':"1",        'flags': cvar.CVAR_NONE}
    gl_flashblend         = {'name': "gl_flashblend",     'value':"0",        'flags': cvar.CVAR_ARCHIVE}
    gl_playermip          = {'name': "gl_playermip",      'value':"0",        'flags': cvar.CVAR_NONE}
    gl_nocolors           = {'name': "gl_nocolors",       'value':"0",        'flags': cvar.CVAR_NONE}

    r_stereo              = {'name': "r_stereo",          'value':"0",        'flags': cvar.CVAR_NONE}
    r_stereodepth         = {'name': "r_stereodepth",     'value':"128",      'flags': cvar.CVAR_NONE}
    r_clearcolor          = {'name': "r_clearcolor",      'value':"2",        'flags': cvar.CVAR_ARCHIVE}
    r_drawflat            = {'name': "r_drawflat",        'value':"0",        'flags': cvar.CVAR_NONE}
    r_flatlightstyles     = {'name': "r_flatlightstyles", 'value': "0",       'flags': cvar.CVAR_NONE}
    gl_fullbrights        = {'name': "gl_fullbrights",    'value': "1",       'flags': cvar.CVAR_ARCHIVE}
    gl_farclip            = {'name': "gl_farclip",        'value': "65536",   'flags': cvar.CVAR_ARCHIVE}
    gl_overbright         = {'name': "gl_overbright",     'value': "1",       'flags': cvar.CVAR_ARCHIVE}
    gl_overbright_models  = {'name': "gl_overbright_models", 'value': "1",    'flags': cvar.CVAR_ARCHIVE}
    r_oldskyleaf          = {'name': "r_oldskyleaf",       'value': "0",      'flags': cvar.CVAR_NONE}
    r_drawworld           = {'name': "r_drawworld",        'value': "1",      'flags': cvar.CVAR_NONE}
    r_showtris            = {'name': "r_showtris",         'value': "0",      'flags': cvar.CVAR_NONE}
    r_showbboxes          = {'name': "r_showbboxes",       'value': "0",      'flags': cvar.CVAR_NONE}
    r_lerpmodels          = {'name': "r_lerpmodels",       'value': "1",      'flags': cvar.CVAR_NONE}
    r_lerpmove            = {'name': "r_lerpmove",         'value': "1",      'flags': cvar.CVAR_NONE}
    r_nolerp_list         = {'name': "r_nolerp_list",      'value': "progs/flame.mdl,progs/flame2.mdl,progs/braztall.mdl,progs/brazshrt.mdl,progs/longtrch.mdl,progs/flame_pyre.mdl,progs/v_saw.mdl,progs/v_xfist.mdl,progs/h2stuff/newfire.mdl", 'flags' : cvar.CVAR_NONE}

    r_noshadow_list       = {'name': "r_noshadow_list",    'value': "progs/flame2.mdl,progs/flame.mdl,progs/bolt1.mdl,progs/bolt2.mdl,progs/bolt3.mdl,progs/laser.mdl", 'flags':cvar.CVAR_NONE}

    r_lavaalpha           = {'name': "r_lavaalpha",        'value':"0",        'flags': cvar.CVAR_NONE}
    r_telealpha           = {'name': "r_telealpha",        'value':"0",        'flags': cvar.CVAR_NONE}
    r_slimealpha          = {'name': "r_slimealpha",       'value':"0",        'flags': cvar.CVAR_NONE}
    r_scale               = {'name': "r_scale",            'value': "1",       'flags': cvar.CVAR_ARCHIVE}

    import gl_rmisc
    import gl_vidsdl

    cvar.Cvar_RegisterVariable(r_norefresh)
    cvar.Cvar_RegisterVariable(r_drawentities)
    cvar.Cvar_RegisterVariable(r_drawviewmodel)
    cvar.Cvar_RegisterVariable(r_speeds)
    cvar.Cvar_RegisterVariable(r_pos)
    cvar.Cvar_RegisterVariable(r_fullbright)
    cvar.Cvar_RegisterVariable(r_lightmap)
    cvar.Cvar_RegisterVariable(r_shadows)
    cvar.Cvar_RegisterVariable(r_wateralpha)
    cvar.Cvar_SetCallback (r_wateralpha, gl_rmisc.R_SetWateralpha_f)
    cvar.Cvar_RegisterVariable(r_litwater)
    cvar.Cvar_RegisterVariable(r_dynamic)
    cvar.Cvar_RegisterVariable(r_novis)

    cvar.Cvar_RegisterVariable(gl_finish)
    cvar.Cvar_RegisterVariable(gl_clear)
    cvar.Cvar_RegisterVariable(gl_cull)
    cvar.Cvar_RegisterVariable(gl_smoothmodels)
    cvar.Cvar_RegisterVariable(gl_affinemodels)
    cvar.Cvar_RegisterVariable(gl_polyblend)
    cvar.Cvar_RegisterVariable(gl_flashblend)
    cvar.Cvar_RegisterVariable(gl_playermip)
    cvar.Cvar_RegisterVariable(gl_nocolors)

    cvar.Cvar_RegisterVariable(r_stereo)
    cvar.Cvar_RegisterVariable(r_stereodepth)
    cvar.Cvar_RegisterVariable(r_clearcolor)
    cvar.Cvar_SetCallback (r_clearcolor, gl_rmisc.R_SetClearColor_f)
    cvar.Cvar_RegisterVariable(r_drawflat)
    cvar.Cvar_RegisterVariable(r_flatlightstyles)
    cvar.Cvar_RegisterVariable(gl_fullbrights)
    cvar.Cvar_RegisterVariable(gl_farclip)
    cvar.Cvar_RegisterVariable(gl_overbright)
    cvar.Cvar_RegisterVariable(gl_overbright_models)
    cvar.Cvar_RegisterVariable(r_oldskyleaf)
    cvar.Cvar_RegisterVariable(r_drawworld)
    cvar.Cvar_RegisterVariable(r_showtris)
    cvar.Cvar_RegisterVariable(r_showbboxes)
    cvar.Cvar_RegisterVariable(r_lerpmodels)
    cvar.Cvar_RegisterVariable(r_lerpmove)
    cvar.Cvar_RegisterVariable(r_nolerp_list)

    cvar.Cvar_RegisterVariable(r_noshadow_list)

    cvar.Cvar_RegisterVariable(r_lavaalpha)
    cvar.Cvar_RegisterVariable(r_telealpha)
    cvar.Cvar_RegisterVariable(r_slimealpha)
    cvar.Cvar_RegisterVariable(r_scale)

    cvar.Cvar_SetCallback (gl_fullbrights, gl_rmisc.GL_Fullbrights_f)
    cvar.Cvar_SetCallback (gl_overbright,  gl_rmisc.GL_Overbright_f)

    cvar.Cvar_SetCallback (r_nolerp_list,   gl_rmisc.R_Model_ExtraFlags_List_f)
    cvar.Cvar_SetCallback (r_noshadow_list, gl_rmisc.R_Model_ExtraFlags_List_f)

    cvar.Cvar_SetROM ("r_lightmapwide", "1" if gl_vidsdl.gl_packed_pixels else "0")

    cvar.Cvar_SetCallback (r_lavaalpha,  gl_rmisc.R_SetLavaalpha_f)
    cvar.Cvar_SetCallback (r_telealpha,  gl_rmisc.R_SetTelealpha_f)
    cvar.Cvar_SetCallback (r_slimealpha, gl_rmisc.R_SetSlimealpha_f)

    global inited
    inited = True


def R_SetView():
    # 1. Projection (The Lens)
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    aspect = gl_vidsdl._vid.width / gl_vidsdl._vid.height
    glu.gluPerspective(90, aspect, 4, 8192)

    # 2. View Matrix (The Camera)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

    # Get angles from the cl_main path you specified
    angles = cl_main.cl.viewangles
    pitch = angles[0]
    yaw   = angles[1]
    roll  = angles[2]

    # --- THE MAGIC QUAKE SEQUENCE ---
    # In OpenGL's default state:
    # 1. Tilt head (Roll) around Z
    gl.glRotatef(-roll, 0, 0, 1)
    # 2. Look up/down (Pitch) around X
    gl.glRotatef(-pitch, 1, 0, 0)
    # 3. Turn left/right (Yaw) around Y
    gl.glRotatef(-yaw, 0, 1, 0)

    # 3. The Coordinate Shift
    # This aligns Quake's "X=Forward, Y=Left, Z=Up" to OpenGL's default
    gl.glRotatef(-90, 1, 0, 0) # Flip Z up
    gl.glRotatef(90, 0, 0, 1)  # Rotate X forward

    # 4. Translation
    origin = cl_main.cl.vieworg
    # Move the world away from the eye (Z + 22 units for eye level)
    gl.glTranslatef(-origin[0], -origin[1], -(origin[2] + 22.0))




def R_SetupScene():
    R_SetupGL()

def R_SetupView():
    global r_framecount
    global r_origin
    global r_fovx, r_fovy
    global r_oldviewleaf
    global r_viewleaf

    gl_rlight.R_PushDlights()
    gl_rlight.R_AnimateLight()

    r_framecount += 1

    gl_fog.Fog_SetupFrame()

    mathlib.VectorCopy( r_refdef.vieworg, r_origin)
    vpn, vright, vup = mathlib.AngleVectors(r_refdef.viewangles)

    r_oldviewleaf = r_viewleaf
    r_viewleaf = gl_model.Mod_PointInLeaf(r_origin, cl_main.cl.worldmodel)

    view.V_SetContentsColor(r_viewleaf.contents)
    view.V_CalcBlend()

    r_fovx = r_refdef.fov_x
    r_fovy = r_refdef.fov_y

    if cvar.Cvar_GetCvar('r_waterwarp').value:
        contents = gl_model.Mod_PointInLeaf(r_origin, cl_main.cl.worldmodel).contents

        if contents == bspfile.CONTENTS_WATER or contents == bspfile.CONTENTS_SLIME or contents == bspfile.CONTENTS_LAVA:
            r_fovx = math.atan(math.tan(mathlib.DEG2RAD(r_refdef.fov_x)/2) * (0.97 + math.sin(cl_main.cl.time * 1.5) * 0.03)) * 2 / math.pi / 180
            r_fovy = math.atan(math.tan(mathlib.DEG2RAD(r_refdef.fov_y)/2) * (1.03 + math.sin(cl_main.cl.time * 1.5) * 0.03)) * 2 / math.pi / 180

    R_SetFrustum(r_fovx, r_fovy)

    r_world.R_MarkSurfaces()

    gl_warp.R_UpdateWarpTextures()

    R_Clear()

    global r_drawflat_cheatsafe, r_fullbright_cheatsafe, r_lightmap_cheatsafe,  r_drawworld_cheatsafe
    r_drawflat_cheatsafe = r_fullbright_cheatsafe = r_lightmap_cheatsafe = False
    r_drawworld_cheatsafe = True

    if cl_main.cl.maxclients == 1:
        if not cvar.Cvar_GetCvar('r_drawworld').value:
            r_drawflat_cheatsafe = False

        if cvar.Cvar_GetCvar('r_drawflat').value:
            r_drawworld_cheatsafe = False
        elif cvar.Cvar_GetCvar('r_fullbright').value or not cl_main.cl.worldmodel.lightdata:
            r_fullbright_cheatsafe = True
        elif cvar.Cvar_GetCvar('r_lightmap').value:
            r_lightmap_cheatsafe = True


def R_DrawEntitiesOnList(alphapass: bool):
    global currententity

    if not cvar.Cvar_GetCvar('r_drawentities').value:
        return

    for i in range(cl_main.cl_numvisedicts):
        currententity = cl_main.cl_visedicts[i]

        if ( protocol.ENTALPHA_DECODE(currententity.alpha) < 1 and not alphapass or
            protocol.ENTALPHA_DECODE(currententity.alpha) == 1 and alphapass ):
            continue

        if currententity == cl_main.cl_entities[cl_main.cl.viewentity]:
            currententity.angles[0] *= 0.3

        match currententity.model.type:
            case quakedef.modtype_t.mod_alias:
                r_alias.R_DrawAliasModel(currententity)
            case quakedef.modtype_t.mod_brush:
                r_alias.R_DrawBrushModel(currententity)
            case quakedef.modtype_t.mod_sprite:
                r_alias.R_DrawSpriteModel(currententity)




def R_DrawViewModel():
    global currententity

    r_drawviewmodel = cvar.Cvar_GetCvar('r_drawviewmodel').value
    r_drawentities  = cvar.Cvar_GetCvar('r_drawentities').value
    chase_active    = cvar.Cvar_GetCvar('chase_active').value

    if not r_drawviewmodel or not r_drawentities or chase_active:
        return

    if cl_main.cl.items & quakedef.IT_INVISIBILITY or cl_main.cl.stats[quakedef.STAT_HEALTH] <= 0:
        return

    currententity = cl_main.cl.viewent

    if not currententity.model:
        return

    if currententity.model.type != quakedef.modtype_t.mod_alias:
        return

    gl.glDepthRange(0, 0.3)
    r_alias.R_DrawAliasModel(currententity)
    gl.glDepthRange(0, 1)



def R_EmitWirePoint(origin: list[float]):
    size = 8

    gl.glBegin (gl.GL_LINES)
    gl.glVertex3f (origin[0]-size, origin[1], origin[2])
    gl.glVertex3f (origin[0]+size, origin[1], origin[2])
    gl.glVertex3f (origin[0], origin[1]-size, origin[2])
    gl.glVertex3f (origin[0], origin[1]+size, origin[2])
    gl.glVertex3f (origin[0], origin[1], origin[2]-size)
    gl.glVertex3f (origin[0], origin[1], origin[2]+size)
    gl.glEnd ()


def R_EmitWireBox(mins: list[float], maxs: list[float]):

    gl.glBegin (gl.GL_QUAD_STRIP)
    gl.glVertex3f (mins[0], mins[1], mins[2])
    gl.glVertex3f (mins[0], mins[1], maxs[2])
    gl.glVertex3f (maxs[0], mins[1], mins[2])
    gl.glVertex3f (maxs[0], mins[1], maxs[2])
    gl.glVertex3f (maxs[0], maxs[1], mins[2])
    gl.glVertex3f (maxs[0], maxs[1], maxs[2])
    gl.glVertex3f (mins[0], maxs[1], mins[2])
    gl.glVertex3f (mins[0], maxs[1], maxs[2])
    gl.glVertex3f (mins[0], mins[1], mins[2])
    gl.glVertex3f (mins[0], mins[1], maxs[2])
    gl.glEnd ()


def R_ShowBoundingBoxes():
    mins: list[float] = [0, 0, 0]
    maxs: list[float] = [0, 0, 0]

    if ( not cvar.Cvar_GetCvar('r_showbboxes').value or cl_main.cl.maxclients > 1 or
         not cvar.Cvar_GetCvar('r_drawentities').value or not sv_main.sv.active ):
         return

    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
    GL_PolygonOffset(quakedef.OFFSET_SHOWTRIS)
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glDisable(gl.GL_CULL_FACE)
    gl.glColor3f(1, 1, 1)

    ed:progs.edict_t = progs.NEXT_EDICT(sv_main.sv.edicts)

    for i in range(1, sv_main.sv.num_edicts):
        if ed == sv_user.sv_player or ed.free:
            continue

        if ed.v.mins[0] == ed.v.maxs[0] and ed.v.mins[1] == ed.v.maxs[1] and ed.v.mins[2] == ed.v.maxs[2]:
            R_EmitWirePoint(ed.v.origin)
        else:
            mathlib.VectorAdd(ed.v.mins, ed.v.origin, mins)
            mathlib.VectorAdd(ed.v.maxs, ed.v.origin, maxs)
            R_EmitWireBox(mins, maxs)

        ed = progs.NEXT_EDICT(ed)

    gl.glColor3f (1,1,1);
    gl.glEnable (gl.GL_TEXTURE_2D);
    gl.glEnable (gl.GL_CULL_FACE);
    gl.glPolygonMode (gl.GL_FRONT_AND_BACK, gl.GL_FILL)
    GL_PolygonOffset (quakedef.OFFSET_NONE);
    gl.glEnable (gl.GL_DEPTH_TEST);

    sbar.Sbar_Changed()


def R_ShowTris():
    global currententity

    r_showtris = cvar.Cvar_GetCvar('r_showtris').value
    r_particles = cvar.Cvar_GetCvar('r_particles').value
    r_drawworld = cvar.Cvar_GetCvar('r_drawworld').value
    r_drawentities = cvar.Cvar_GetCvar('r_drawentities').value

    if r_showtris < 1 or r_showtris > 2 or cl_main.cl.maxclients > 1:
        return

    if r_showtris == 1:
        gl.glDisable(gl.GL_DEPTH_TEST)

    gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
    GL_PolygonOffset(quakedef.OFFSET_SHOWTRIS)
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glColor3f(1, 1, 1)

    if r_drawworld:
        r_world.R_DrawWorld_ShowTris()

    if r_drawentities:
        for i in range(cl_main.cl_visedicts):
            currententity = cl_main.cl_visedicts[i]

            if currententity == cl_main.cl_entities[cl_main.cl.viewentity]:
                currententity.angles[0] *= 0.3

            match currententity.model.type:
                case quakedef.modtype_t.mod_brush:
                    r_alias.R_DrawBrushModel_ShowTris(currententity)
                case quakedef.modtype_t.mod_alias:
                    r_alias.R_DrawAliasModel_ShowTris(currententity)
                case quakedef.modtype_t.mod_sprite:
                    r_alias.R_DrawSpriteModel(currententity)

        currententity = cl_main.cl.viewent

        r_drawviewmodel = cvar.Cvar_GetCvar('r_drawviewmodel').value
        chase_active    = cvar.Cvar_GetCvar('chase_active').value
        if (
            r_drawviewmodel and not chase_active and
            cl_main.cl.stats[quakedef.STAT_HEALTH] > 0 and
            not ( cl_main.cl.items & quakedef.IT_INVISIBILITY) and
            currententity.model and currententity.model.type == quakedef.modtype_t.mod_alias
        ):
            gl.glDepthRange(0, 0.3)
            r_alias.R_DrawAliasModel_ShowTris(currententity)
            gl.glDepthRange(0, 1)


    gl.glColor3f(1, 1, 1)
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)

    GL_PolygonOffset(glquake.OFFSET_NONE)

    if r_showtris == 1:
        gl.glEnable(gl.GL_DEPTH_TEST)

    sbar.Sbar_Changed()



def R_DrawShadows():
    global currententity

    r_shadows      = cvar.Cvar_GetCvar('r_shadows').value
    r_drawentities = cvar.Cvar_GetCvar('r_drawentities').value

    if gl_vidsdl.gl_stencilbits:
        gl.glClear(gl.GL_STENCIL_BUFFER_BIT)
        gl.glStencilFunc(gl.GL_EQUAL, 0, ~0)
        gl.glStencilOp(gl.GL_KEEP, gl.GL_KEEP, gl.GL_INCR)
        gl.glEnable(gl.GL_STENCIL_TEST)

    for i in range(cl_main.cl_numvisedicts):
        currententity = cl_main.cl_visedicts[i]

        if currententity.model.type != quakedef.modtype_t.mod_alias:
            continue

        if currententity == cl_main.cl.viewent:
            return

        r_alias.GL_DrawAliasShadow(currententity)

    if gl_vidsdl.gl_stencilbits:
        gl.glDisable(gl.GL_STENCIL_BITS)


def R_RenderScene():
    R_SetupScene()

    gl_fog.Fog_EnableFog()

    gl_sky.Sky_DrawSky()

    r_world.R_DrawWorld()

    snd_dma.S_ExtraUpdate()

    R_DrawShadows()

    R_DrawEntitiesOnList(False)

    r_world.R_DrawWorld_Water()

    R_DrawEntitiesOnList(True)

    gl_rlight.R_RenderDlights()

    r_part.R_DrawParticles()

    gl_fog.Fog_DisableFog()

    R_DrawViewModel()

    R_ShowTris()

    R_ShowBoundingBoxes()


def R_ScaleView_DeleteTexture():
    global r_scaleview_texture
    gl.glDeleteTextures(1, r_scaleview_texture)
    r_scaleview_texture = 0


def R_ScaleView():
    global r_scaleview_texture_height, r_scaleview_texture_width

    r_scale = cvar.Cvar_GetCvar('r_scale').value

    scale = common.CLAMP(1, r_scale, 4)
    srcx = gl_screen.glx + r_refdef.vrect.x;
    srcy = gl_screen.gly + gl_screen.glheight - r_refdef.vrect.y - r_refdef.vrect.height
    srcw = r_refdef.vrect.width / scale;
    srch = r_refdef.vrect.height / scale;

    if scale == 1:
        return

    gl_texmgr.GL_DisableMultiTexture()

    if not r_scaleview_texture:
        tex_id = (ctypes.c_uint * 1)()
        gl.glGenTextures(1, tex_id)
        r_scaleview_texture = tex_id[0]

    gl.glBindTexture(gl.GL_TEXTURE_2D, r_scaleview_texture)

    if r_scaleview_texture_width < srcw or r_scaleview_texture_height < srch:
        r_scaleview_texture_width = srcw
        r_scaleview_texture_height = srch

        if not gl_vidsdl.gl_texture_NPOT:
            r_scaleview_texture_width  = gl_texmgr.TexMgr_Pad(r_scaleview_texture_width)
            r_scaleview_texture_height = gl_texmgr.TexMgr_Pad(r_scaleview_texture_height)

        gl.glTexImage2D( gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, r_scaleview_texture_width, r_scaleview_texture_height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)
        gl.glTexParameteri (gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri (gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)

    gl.glBindTexture (gl.GL_TEXTURE_2D, r_scaleview_texture);
    gl.glCopyTexSubImage2D (gl.GL_TEXTURE_2D, 0, 0, 0, srcx, srcy, srcw, srch);

    gl.glDisable (gl.GL_ALPHA_TEST);
    gl.glDisable (gl.GL_DEPTH_TEST);
    gl.glDisable (gl.GL_CULL_FACE);
    gl.glDisable (gl.GL_BLEND);

    gl.glViewport (srcx, srcy, r_refdef.vrect.width, r_refdef.vrect.height);

    gl.glMatrixMode(gl.GL_PROJECTION);
    gl.glLoadIdentity ();
    gl.glMatrixMode(gl.GL_MODELVIEW);
    gl.glLoadIdentity ();

    smax = srcw/r_scaleview_texture_width;
    tmax = srch/r_scaleview_texture_height;

    gl.glBegin (gl.GL_QUADS);
    gl.glTexCoord2f (0, 0);
    gl.glVertex2f (-1, -1);
    gl.glTexCoord2f (smax, 0);
    gl.glVertex2f (1, -1);
    gl.glTexCoord2f (smax, tmax);
    gl.glVertex2f (1, 1);
    gl.glTexCoord2f (0, tmax);
    gl.glVertex2f (-1, 1);
    gl.glEnd ();

    gl_texmgr.GL_ClearBindings ();





def R_RenderView():
    if cvar.Cvar_GetCvar('r_norefresh').value:
        return

    if not cl_main.cl.worldmodel:
        sys_sdl_unix.Sys_Error('R_RenderView: NULL worldmodel')

    if cvar.Cvar_GetCvar('r_speeds').value:
        gl.glFinish()
        time1 = sys_sdl_unix.Sys_DoubleTime()

        rs_brushpolys = rs_aliaspolys = rs_skypolys = rs_dynamiclightmaps = rs_aliaspasses = rs_skypasses = rs_brushpasses = 0
    elif cvar.Cvar_GetCvar('gl_finish').value:
        gl.glFinish()

    R_SetupView()

    r_stereo      = cvar.Cvar_GetCvar('r_stereo').value
    r_stereodepth = cvar.Cvar_GetCvar('r_stereodepth').value

    if r_stereo:
        eyesep = common.CLAMP(-8, r_stereo, 8)
        fdepth = common.CLAMP(32, r_stereodepth, 1024)

        mathlib.AngleVectors(r_refdef.viewangles, vpn, vright, vup)

        gl.glColorMask(1,0,0,1)
        mathlib.VectorMA(r_refdef.vieworg, -.5 * eyesep, vright, r_refdef.vieworg)
        frustum_skew = 0.5 * eyesep * NEARCLIP / fdepth;
        random.seed(cl_main.cl.time * 1000)

        R_RenderScene ();

        gl.glClear (gl.GL_DEPTH_BUFFER_BIT)
        gl.glColorMask(0, 1, 1, 1)
        mathlib.VectorMA (r_refdef.vieworg, 1.0 * eyesep, vright, r_refdef.vieworg)
        frustum_skew = -frustum_skew
        random.seed(cl.time * 1000)

        R_RenderScene ()

        gl.glColorMask(1, 1, 1, 1)
        mathlib.VectorMA (r_refdef.vieworg, -0.5 * eyesep, vright, r_refdef.vieworg)
        frustum_skew = 0.0

    else:
        R_RenderScene()

    R_ScaleView()

    time2 = sys_sdl_unix.Sys_DoubleTime()

    r_pos = cvar.Cvar_GetCvar('r_pos').value
    r_speeds = cvar.Cvar_GetCvar('r_speeds').value

    if r_pos:
        console.Con_Printf( "x %i y %i z %i (pitch %i yaw %i roll %i)\n" % (
            int(cl_main.cl_entities[cl_main.cl.viewentity].origin[0]),
            int(cl_main.cl_entities[cl_main.cl.viewentity].origin[1]),
            int(cl_main.cl_entities[cl_main.cl.viewentity].origin[2]),
            int(cl_main.cl.viewangles[quakedef.PITCH]),
            int(cl_main.cl.viewangles[quakedef.YAW]),
            int(cl_main.cl.viewangles[quakedef.ROLL]),
        )
    )
    elif r_speeds == 2:
        console.Con_Printf( "%3i ms  %4i/%4i wpoly %4i/%4i epoly %3i lmap %4i/%4i sky %1.1f mtex\n" % (
            int((time2 - time1) * 1000.0),
            rs_brushpolys,
            rs_brushpasses,
            rs_aliaspolys,
            rs_aliaspasses,
            rs_dynamiclightmaps,
            rs_skypolys,
            rs_skypasses,
            gl_texmgr.TexMgr_FrameUsage(),
        )
    )
    elif r_speeds:
        console.Con_Printf ("%3i ms  %4i wpoly %4i epoly %3i lmap\n" % (
            ( time2-time1 ) * 1000,
            rs_brushpolys,
            rs_aliaspolys,
            rs_dynamiclightmaps
        )
    )









def R_RenderViewGeminixx():
    raise Exception('DontUse')
    global r_visframecount

    if not cl_main.cl or not cl_main.cl.worldmodel:
        return

    r_visframecount += 1

    # 1. Sync camera data
    gl_rmain.r_refdef.vieworg = list(cl_main.cl.vieworg)
    gl_rmain.r_refdef.viewangles = list(cl_main.cl.viewangles)

    # 2. CLEAR AND SETUP
    gl.glClearColor(0.3, 0.5, 0.9, 1.0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

    # --- CRITICAL ADDITIONS START ---
    gl.glEnable(gl.GL_TEXTURE_2D)       # MUST be enabled for world textures!
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0) # Clear any bound UI textures
    gl.glColor4f(1, 1, 1, 1)            # Reset color so world isn't tinted
    # --- CRITICAL ADDITIONS END ---

    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glDepthFunc(gl.GL_LEQUAL)
    gl.glEnable(gl.GL_CULL_FACE)
    gl.glFrontFace(gl.GL_CW)
    gl.glCullFace(gl.GL_BACK)

    # 3. SET CAMERA
    R_SetView()

    # 4. DRAW
    r_brush.r_visframecount = r_visframecount
    r_brush.r_refdef = gl_rmain.r_refdef
    r_brush.r_worldmodel = cl_main.cl.worldmodel

    r_brush.R_RecursiveWorldNode(cl_main.cl.worldmodel.nodes[0])

    # Note: If you draw the console here, make sure it cleans up after itself!
    console.Con_DrawConsole()
