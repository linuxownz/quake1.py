#gl_rmain.py

import math

import OpenGL.GL as gl

import bspfile
import cl_main
import common
import console
import cvar
import gl_fog
import gl_model
import gl_rlight
import gl_screen
import mathlib
import quakedef
import r_brush
import render
import sys_sdl_unix
import view

modelorg    = [0, 0, 0]
r_entorigin = [0, 0, 0]

currententity : render.entity_t = None

r_visframecount = 0
r_framecount = 0

frustum : list[quakedef.mplane_t] = [ quakedef.mplane_t(0, 0, 0, 0) for i in range(4)]

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

r_refdef : quakedef.refdef_t = quakedef.refdef_t()

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

def gl_rmain_Init():
    import cvar

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


def R_SetView():
    import OpenGL.GL as gl
    import OpenGL.GLU as glu

    import gl_vidsdl

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


def R_SetupScene():
    R_SetupGL()

def R_RenderScene():
    R_SetupScene()

    Fog_EnableFog()

    Sky_DrawSky()

    S_ExtraUpdate()

    R_DrawShadows()

    R_DrawEntitiesOnList(False)

    R_DrawWorld_Water()

    R_DrawEntitiesOnList(True)

    R_RenderDlights()

    R_DrawParticles()

    Fog_DisableFog()

    R_DrawViewModel()

    R_ShowTris()

    R_ShowBoundingBoxes()

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

    R_MarkSurfaces()

    R_UpdateWarpTextures()

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

def R_RenderView():
    if cvar.Cvar_GetCvar('r_norefresh').value:
        return

    if not cl_main.cl.worldmodel:
        sys_sdl_unix.Sys_Error('R_RenderView: NULL worldmodel')

    if cvar.Cvar_GetCvar('r_speeds').value:
        gl.glFinish()

    R_SetupView()

    if cvar.Cvar_GetCvar('r_stereo').value:
        raise NotImplementedError
    else:
        R_RenderScene()

    R_ScaleView()




def R_RenderViewGemini():
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
