#gl_rmisc.py

import ctypes

import OpenGL
import OpenGL.GL

import _cmd
import cl_main
import common
import console
import cvar
import gl_fog
import gl_model
import gl_rmain
import gl_screen
import gl_sky
import gl_texmgr
import gl_vidsdl
import gl_warp
import glquake
import host
import quakedef
import r_alias
import r_brush
import r_part
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


def R_DeleteShaders():
    if not gl_vidsdl.gl_glsl_able:
        return

    for i in range(gl_num_programs):
        OpenGL.GL.glDeleteProgram(gl_programs[i])
        gl_programs[i] = 0

    gl_num_programs = 0


def GL_BindBuffer(target: int, buffer: int):
    global current_array_buffer, current_element_array_buffer

    if not gl_vidsdl.gl_vbo_able:
        return

    match target:
        case OpenGL.GL.GL_ARRAY_BUFFER:
            if current_array_buffer != buffer:
                current_array_buffer = buffer
                OpenGL.GL.glBindBuffer(target, buffer)

        case OpenGL.GL.GL_ELEMENT_ARRAY_BUFFER:
            if current_element_array_buffer != buffer:
                current_element_array_buffer = buffer
                OpenGL.GL.glBindBuffer(target, buffer)

        case _:
            host.Host_Error(f"GL_BindBuffer: unsupported target {int(target)}")




def GL_GetUniformLocation(program, name) -> int: # returns location
    return OpenGL.GL.glGetUniformLocation(program, name)


def R_TimeRefresh_f():
    if cl_main.cls.state != quakedef.cactive_t.ca_connected:
        console.Con_Printf('not connected to a server')
        return

    start = sys_sdl_unix.Sys_DoubleTime()

    for i in range(128):
        glquake.GL_BeginRendering(gl_screen.glx, gl_screen.gly, gl_screen.glwidth, gl_screen.glheight)
        gl_rmain.r_refdef.viewangles[1] = i/128.0*360.0
        gl_rmain.R_RenderView()
        glquake.GL_EndRendering()

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
    # d_8to24table has 4 bytes (RGBA) per palette entry
    v1 = gl_texmgr.d_8to24table[r_clearcolor * 4 + 0]
    v2 = gl_texmgr.d_8to24table[r_clearcolor * 4 + 1]
    v3 = gl_texmgr.d_8to24table[r_clearcolor * 4 + 2]

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

def GL_WaterAlphaForSurface(fa: quakedef.msurface_t) -> float:
    if fa.flags & quakedef.SURF_DRAWLAVA:
        return gl_rmain.map_lavaalpha if gl_rmain.map_lavaalpha else gl_rmain.map_wateralpha
    if fa.flags & quakedef.SURF_DRAWTELE:
        return gl_rmain.map_telealpha if gl_rmain.map_telealpha else gl_rmain.map_wateralpha
    if fa.flags & quakedef.SURF_DRAWSLIME:
        return gl_rmain.map_slimealpha if gl_rmain.map_slimealpha else gl_rmain.map_wateralpha
    return gl_rmain.map_wateralpha

def R_Init():
    _cmd.Cmd_AddCommand('timerefresh', R_TimeRefresh_f)
    _cmd.Cmd_AddCommand('pointfile', R_ReadPointFile_f)

    cvar.Cvar_RegisterVariable({'name': 'r_lightmapwide', 'value': '0', 'flag': cvar.CVAR_ROM})

    import gl_rmain
    gl_rmain.gl_rmain_Init()

    r_part.R_InitParticles ()
    R_SetClearColor_f (None) #johnfitz

    from gl_sky import Sky_Init
    Sky_Init () #johnfitz

    from gl_fog import Fog_Init
    Fog_Init () #johnfitz

def R_TranslatePlayerSkin(playernum: int):
    top = ( cl_main.cl.scores[playernum].colors & 0xF0 ) >> 4
    bottom = ( cl_main.cl.scores[playernum].colors) & 15

    if not cvar.Cvar_GetCvar('gl_nocolors').value:  # noqa: SIM102
        if r_alias.playertextures[playernum]:
            gl_texmgr.TexMgr_ReLoadImage(r_alias.playertextures[playernum], top, bottom)

def R_TranslateNewPlayerSkin(playernum: int):
    gl_rmain.currententity = cl_main.cl_entities[1+playernum]

    if not gl_rmain.currententity.model or gl_rmain.currententity.model.type != quakedef.modtype_t.mod_alias:
        return

    paliashdr: quakedef.aliashdr_t = gl_model.Mod_Extradata(gl_rmain.currententity.model)
    skinnum = gl_rmain.currententity.skinnum

    if skinnum < 0 or skinnum >= paliashdr.numskins:
        console.Con_DPrintf(f'{playernum}: Invalid player skin #{skinnum}')
        skinnum = 0

    offset = paliashdr.texels[skinnum]
    pixels = paliashdr.data[offset:]

    name = f'player_{playernum}'

    r_alias.playertextures[playernum] = gl_texmgr.TexMgr_LoadImage (
        gl_rmain.currententity.model, name, paliashdr.skinwidth, paliashdr.skinheight,
        gl_texmgr.SRC_INDEXED, pixels, paliashdr.gltextures[skinnum][0].source_file,
        paliashdr.gltextures[skinnum][0].source_offset,
        gl_texmgr.TEXPREF_PAD | gl_texmgr.TEXPREF_OVERWRITE
    )

    R_TranslatePlayerSkin(playernum)

def R_NewGame():
    for i in range(quakedef.MAX_SCOREBOARD):
        r_alias.playertextures[i] = None


def R_ParseWorldspawn():
    gl_rmain.map_wateralpha = cvar.Cvar_GetCvar('r_wateralpha').value
    gl_rmain.map_lavaalpha  = cvar.Cvar_GetCvar('r_lavaalpha').value
    gl_rmain.map_telealpha  = cvar.Cvar_GetCvar('r_telealpha').value
    gl_rmain.map_slimealpha  = cvar.Cvar_GetCvar('r_slimealpha').value

    data = common.COM_Parse(cl_main.cl.worldmodel.entities)
    if not data:
        return
    if common.com_token[0] != '{':
        return

    while True:
        data = common.COM_Parse(data)
        if not data:
            return
        if common.com_token[0] == '}':
            return
        if common.com_token[o] == '_':
            key = common.com_token[1:]
        else:
            key = common.com_token[:]

        key = key.strip()

        data = common.COM_ParseEx(data)
        if not data:
            return

        value = common.com_token[:]

        if key == 'wateralpha':
            gl_rmain.map_wateralpha = float(value)
        if key == 'lavaalpha':
            gl_rmain.map_lavaalpha = float(value)
        if key == 'telealpha':
            gl_rmain.map_telealpha = float(value)
        if key == 'slimealpha':
            gl_rmain.map_slimealpha = float(value)

def R_NewMap():
    for i in range(256):
        gl_rmain.d_lightstylevalue[i] = 264

    for i in range(cl_main.cl.worldmodel.numleafs):
        cl_main.cl.worldmodel.leafs[i].efrags = None

    gl_rmain.r_viewleaf = None
    r_part.R_ClearParticles()

    r_brush.GL_BuildLightmaps()
    r_brush.GL_BuildBModelVertexBuffer()

    gl_rmain.r_framecount = 0
    gl_rmain.r_visframecount = 0

    gl_sky.Sky_NewMap()
    gl_fog.Fog_NewMap()

    R_ParseWorldspawn()

    gl_warp.load_subdivide_size = cvar.Cvar_GetCvar('r_subdivide_size').value



def D_FlushCaches():
    pass


def GL_ClearBufferBindings():
    global current_array_buffer
    global current_element_array_buffer

    if not gl_vidsdl.gl_vbo_able:
        return

    current_array_buffer = 0
    current_element_array_buffer = 0

    OpenGL.GL.glBindBuffer(OpenGL.GL.GL_ARRAY_BUFFER, 0)
    OpenGL.GL.glBindBuffer(OpenGL.GL.GL_ELEMENT_ARRAY_BUFFER, 0)

