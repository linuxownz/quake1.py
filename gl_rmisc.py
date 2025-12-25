#gl_rmisc.py

import ctypes

import OpenGL
import OpenGL.GL

import client
import _cmd
import cvar
import console
import gl_model
import gl_rmain
import gl_screen
import glquake
import gl_texmgr
import gl_vidsdl
import host
import quakedef
import r_part
import r_brush
import sys_sdl_unix

gl_programs = [0 for i in range(16)]
gl_num_programs = 0

current_array_buffer = 0
current_element_array_buffer = 0

def GL_CheckShader(shader):
    status = ctypes.c_int()
    OpenGL.GL.glGetShaderiv(shader, OpenGL.GL.GL_COMPILE_STATUS, status)
    status = status.value

    if status != OpenGL.GL.GL_TRUE:
        infolog = OpenGL.GL.glGetShaderInfoLog(shader)
        console.Con_Warning(f'GLSL program failed to compile: {infolog}')
        return False

    return True

def GL_CheckProgram(program):
    status = ctypes.c_int()
    OpenGL.GL.glGetProgramiv(program, OpenGL.GL.GL_LINK_STATUS, status)

    if status.value != OpenGL.GL.GL_TRUE:
        infolog = OpenGL.GL.glGetShaderInfoLog(shader)
        console.Con_Warning(f'GLSL program failed to link: {infolog}')
        return False

    return True

def GL_CreateProgram(vertSource, fragSource, numbindings, bindings: list[glquake.glsl_attrib_binding_t]):
    global gl_programs, gl_num_programs

    if not gl_vidsdl.gl_glsl_alias_able:
        return 0

    vertShader = OpenGL.GL.glCreateShader(OpenGL.GL.GL_VERTEX_SHADER)
    OpenGL.GL.glShaderSource(vertShader, vertSource)
    OpenGL.GL.glCompileShader(vertShader)

    if not GL_CheckShader(vertShader):
        OpenGL.GL.glDeleteShader(vertShader)
        return 0

    fragShader = OpenGL.GL.glCreateShader(OpenGL.GL.GL_FRAGMENT_SHADER)
    OpenGL.GL.glShaderSource(fragShader, fragSource)
    OpenGL.GL.glCompileShader(fragShader)

    if not GL_CheckShader(fragShader):
        OpenGL.GL.glDeleteShader(fragShader)
        return 0

    program = OpenGL.GL.glCreateProgram()
    OpenGL.GL.glAttachShader(program, vertShader)
    OpenGL.GL.glDeleteShader(vertShader)
    OpenGL.GL.glAttachShader(program, fragShader)
    OpenGL.GL.glDeleteShader(fragShader)

    for i in range(numbindings):
        OpenGL.GL.glBindAttribLocation(program, bindings[i].attrib, bindings[i].name)

    OpenGL.GL.glLinkProgram(program)

    if not GL_CheckProgram(program):
        OpenGL.GL.glDeleteProgram(program)
        return 0
    else:
        if gl_num_programs >= len(gl_programs):
            host.Host_Error('gl_programs overflow')

        gl_programs[gl_num_programs] = program
        gl_num_programs += 1

        return program

def GL_GetUniformLocation(program, name) -> int: # returns location
    return OpenGL.GL.glGetUniformLocation(program, name)


def R_TimeRefresh_f():
    if client.cls.state != client.cactive_t.ca_connected:
        console.Con_Printf('not connected to a server')
        return

    start = sys_sdl_unix.Sys_DoubleTime()

    for i in range(128):
        glquake.GL_BeginRendering(gl_screen.glx, gl_screen.gly, gl_screen.glwidth, gl_screen.glheight)
        gl_rmain.r_refdef.viewangles[1] = i/128.0*360.0
        gl_rmain.R_RenderView()
        glquake.GL_EndRendering

    OpenGL.GL.glFinish()
    stop = sys_sdl_unix.Sys_DoubleTime()
    time = stop - start
    console.Con_Printf(f'{time} seconds ({128/time} fps)')

def R_ReadPointFile_f():
    raise NotImplementedError

def R_SetWateralpha_f(var : cvar.cvar_t):
    gl_rmain.map_wateralpha = float(var.value)

def R_SetClearColor_f(var: cvar.cvar_t):

    r_clearcolor = int(cvar.Cvar_GetCvar('r_clearcolor').value) & 0xFF
    v1 = gl_texmgr.d_8to24table[r_clearcolor + 0]
    v2 = gl_texmgr.d_8to24table[r_clearcolor + 1]
    v3 = gl_texmgr.d_8to24table[r_clearcolor + 2]

    OpenGL.GL.glClearColor(v1/255.0, v2/255.0, v3/255.0, 0)


def GL_Fullbrights_f(var: cvar.cvar_t):
    gl_texmgr.TexMgr_ReloadNobrightsImages()

def GL_Overbright_f(var: cvar.cvar_t):
    r_brush.R_RebuildAllLightmaps()


def R_Model_ExtraFlags_List_f(var:cvar.cvar_t):
    import client
    for i in range(quakedef.MAX_MODELS):
        gl_model.Mod_SetExtraFlags(client.cl.model_precache[i])


def R_SetLavaalpha_f(var: cvar.cvar_t):
    gl_rmain.map_lavaalpha = float(var.value)

def R_SetTelealpha_f(var:cvar.cvar_t):
    gl_rmain.map_telealpha = float(var.value)

def R_SetSlimealpha_f(var:cvar.cvar_t):
    gl_rmain.map_slimealpha = float(var.value)


def R_Init():
    import cvar
    _cmd.Cmd_AddCommand('timerefresh', R_TimeRefresh_f)
    _cmd.Cmd_AddCommand('pointfile', R_ReadPointFile_f)

    import gl_rmain

    gl_rmain.gl_rmain_Init()

    # # cvars in gl_rmisc
    # cvar.Cvar_RegisterVariable (gl_rmain.r_norefresh)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_lightmap)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_fullbright)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_drawentities)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_drawviewmodel)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_shadows)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_wateralpha)
    # cvar.Cvar_SetCallback (gl_rmain.r_wateralpha, R_SetWateralpha_f)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_litwater)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_dynamic)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_novis)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_speeds)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_pos)

    # cvar.Cvar_RegisterVariable (gl_rmain.gl_finish)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_clear)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_cull)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_smoothmodels)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_affinemodels)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_polyblend)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_flashblend)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_playermip)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_nocolors)

    # #johnfitz -- new cvars
    # cvar.Cvar_RegisterVariable (gl_rmain.r_stereo)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_stereodepth)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_clearcolor)
    # cvar.Cvar_SetCallback (gl_rmain.r_clearcolor, R_SetClearColor_f)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_waterquality)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_oldwater)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_waterwarp)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_drawflat)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_flatlightstyles)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_oldskyleaf)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_drawworld)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_showtris)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_showbboxes)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_farclip)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_fullbrights)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_overbright)
    # cvar.Cvar_SetCallback (gl_rmain.gl_fullbrights, GL_Fullbrights_f)
    # cvar.Cvar_SetCallback (gl_rmain.gl_overbright, GL_Overbright_f)
    # cvar.Cvar_RegisterVariable (gl_rmain.gl_overbright_models)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_lerpmodels)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_lerpmove)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_nolerp_list)
    # cvar.Cvar_SetCallback (gl_rmain.r_nolerp_list, R_Model_ExtraFlags_List_f)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_noshadow_list)
    # cvar.Cvar_SetCallback (gl_rmain.r_noshadow_list, R_Model_ExtraFlags_List_f)
    # #johnfitz
    # cvar.Cvar_RegisterVariable (gl_rmain.r_lightmapwide)
    # cvar.Cvar_SetROM ("r_lightmapwide", "1" if gl_vidsdl.gl_packed_pixels else "0")

    # cvar.Cvar_RegisterVariable (gl_rmain.gl_zfix) # QuakeSpasm z-fighting fix
    # cvar.Cvar_RegisterVariable (gl_rmain.r_lavaalpha)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_telealpha)
    # cvar.Cvar_RegisterVariable (gl_rmain.r_slimealpha)

    # cvar.Cvar_RegisterVariable (gl_rmain.r_scale)
    # cvar.Cvar_SetCallback (gl_rmain.r_lavaalpha, R_SetLavaalpha_f)
    # cvar.Cvar_SetCallback (gl_rmain.r_telealpha, R_SetTelealpha_f)
    # cvar.Cvar_SetCallback (gl_rmain.r_slimealpha, R_SetSlimealpha_f)

    r_part.R_InitParticles ()
    R_SetClearColor_f (None); #johnfitz

    from gl_sky import Sky_Init
    Sky_Init (); #johnfitz

    from gl_fog import Fog_Init
    Fog_Init (); #johnfitz


def GL_ClearBufferBindings():
    global current_array_buffer
    global current_element_array_buffer

    if not gl_vidsdl.gl_vbo_able:
        return

    current_array_buffer = 0
    current_element_array_buffer = 0

    OpenGL.GL.glBindBuffer(OpenGL.GL.GL_ARRAY_BUFFER, 0)
    OpenGL.GL.glBindBuffer(OpenGL.GL.GL_ELEMENT_ARRAY_BUFFER, 0)

