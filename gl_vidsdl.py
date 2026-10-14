#gl_vidsdl.py

import ctypes
import os
import sys
from enum import Enum

import OpenGL
import OpenGL.GL
import sdl2
import sdl2.ext

import _cmd
import cfgfile
import common
import console
import cvar
import gl_draw
import gl_fog
import gl_mesh
import gl_rmain
import gl_rmisc
import gl_screen
import gl_texmgr
import gl_vidsdl
import host
import in_sdl
import keys
import menu
import quakedef
import r_alias
import r_brush
import r_world
import sbar
import snd_dma
import sys_sdl_unix
import vid

MAX_MODE_LIST  = 600 #johnfitz -- was 30
MAX_BPPS_LIST  = 5
MAX_RATES_LIST = 20
WARP_WIDTH     = 320
WARP_HEIGHT    = 200
MAXWIDTH       = 10000
MAXHEIGHT      = 10000

#DEFAULT_SDL_FLAGS = SDL_OPENGL

DEFAULT_REFRESHRATE = 60

class vmode_t:
    def __init__(self, width, height, refreshrate, bpp):
        self.width = width
        self.height = height
        self.refreshrate = refreshrate
        self.bpp = bpp

gl_vendor = ''
gl_renderer = ''
gl_version = ''
gl_version_major = 0
gl_version_minor = 0
gl_extensions = ''
gl_extensions_nice = ''

modelist: list[vmode_t] = []
nummodes = 0

vid_initialized = False

draw_context:sdl2.SDL_Window  = None
gl_context:sdl2.SDL_GLContext = None

vid_locked = False
vid_changed = False

_vid : vid.viddef_t = vid.viddef_t()
modestate : vid.modestate_t = vid.modestate_t.MS_UNINIT

scr_skipupdate = False

gl_mtexable = False
gl_packed_pixels = False
gl_texture_env_combine = False #johnfitz
gl_texture_env_add = False #johnfitz
gl_swap_control = False #johnfitz
gl_anisotropy_able = False #johnfitz
gl_max_anisotropy = 0.0 #johnfitz
gl_texture_NPOT = False #ericw
gl_vbo_able = False #ericw
gl_glsl_able = False #ericw
gl_max_texture_units = 0 #ericw
gl_glsl_gamma_able = False #ericw
gl_glsl_alias_able = False #ericw
gl_stencilbits = 0

fsaa = 0

class vid_opt_e(Enum):
    VID_OPT_MODE        = 0
    VID_OPT_BPP         = 1
    VID_OPT_REFRESHRATE = 2
    VID_OPT_FULLSCREEN  = 3
    VID_OPT_VSYNC       = 4
    VID_OPT_TEST        = 5
    VID_OPT_APPLY       = 6
    VIDEO_OPTIONS_ITEMS = 7

video_options_cursor = 0

class vid_menu_mode:
    def __init__(self):
        self.width = 0
        self.height = 0

vid_menu_modes : list[vid_menu_mode] = [ vid_menu_mode() for i in range(MAX_MODE_LIST)]
vid_menu_nummodes = 0

vid_menu_bpps = [ 0 for i in range(MAX_BPPS_LIST)]
vid_menu_numbpps = 0

vid_menu_rates = [ 0 for i in range(MAX_RATES_LIST)]
vid_menu_numrates = 0

gammaworks = False


def VID_Gamma_SetGamma():
    if gl_glsl_able:
        return

    vid_gamma = cvar.Cvar_GetCvar('vid_gamma').value

    if draw_context and gammaworks:
        value = vid.GAMMA_MAX
        if vid_gamma > 1.0 / vid.GAMMA_MAX:
            value = 1.0 / vid_gamma

        if sdl2.SDL_SetWindowBrightness(draw_context, value) != 0:
            console.Con_Printf('VID_Gamma_SetGamma: failed on SDL_SetWindowBrightness')



def VID_Gamma_Restore():
    if gl_glsl_able:
        return
    if draw_context and gammaworks:
        if sdl2.SDL_SetWindowBrightness(draw_context, 1) != 0:
            console.Con_Printf('VID_Gamma_Restore: failed on SDL_SetWindowBrightness')


def VID_Gamma_Shutdown():
    VID_Gamma_Restore()


def VID_InitModelist():
    sdlmodes = sdl2.SDL_GetNumDisplayModes(0)

    nummodes = 0
    for i in range(sdlmodes):
        mode = sdl2.SDL_DisplayMode()

        if nummodes >= MAX_MODE_LIST:
            break

        if sdl2.SDL_GetDisplayMode(0, i, mode) == 0:
            modelist.append(vmode_t(mode.w, mode.h, mode.refresh_rate, sdl2.SDL_BITSPERPIXEL(mode.format)))
            nummodes += 1

    for m in modelist:
        print(f'{m.width} {m.height} {m.bpp} {m.refreshrate}')



def VID_Changed_f(var):
    global vid_changed
    vid_changed = True

def VID_Unlock():
    global vid_locked
    vid_locked = False
    VID_SyncCvars()

def VID_Restart():
    if vid_locked or not vid_changed:
        return

    width       = cvar.Cvar_GetCvar('vid_width').value
    height      = cvar.Cvar_GetCvar('vid_height').value
    refreshrate = cvar.Cvar_GetCvar('vid_refreshrate').value
    bpp         = cvar.Cvar_GetCvar('vid_bpp').value
    fullscreen  = True if cvar.Cvar_GetCvar('vid_fullscreen').value else False

    if not VID_ValidMode(width, height, refreshrate, bpp, fullscreen):
        console.Con_Printf(f'{width}x{height}x{bpp} {refreshrate}Hz {"fullscreen" if fullscreen else "windowed"} is not a valid mode')
        return

    gl_texmgr.TexMgr_DeleteTextureObjects()
    gl_rmain.GLSLGamma_DeleteTexture ()
    gl_rmain.R_ScaleView_DeleteTexture ()
    gl_rmisc.R_DeleteShaders ()
    r_brush.GL_DeleteBModelVertexBuffer ()
    gl_mesh.GLMesh_DeleteVertexBuffers ()

    VID_SetMode(width, height, refreshrate, bpp, fullscreen)

    GL_Init()
    gl_texmgr.TexMgr_ReloadImages ();
    r_brush.GL_BuildBModelVertexBuffer ();
    gl_mesh.GLMesh_LoadVertexBuffers ();
    GL_SetupState ();
    gl_fog.Fog_SetupState ();

    # warpimages needs to be recalced
    gl_texmgr.TexMgr_RecalcWarpImageSize()

    scr_conwidth = cvar.Cvar_GetCvar('scr_conwidth').value
    scr_conscale = cvar.Cvar_GetCvar('scr_conscale').value

    if scr_conwidth > 0:
        _vid.conwidth = scr_conwidth
    elif scr_conscale > 0:
        _vid.conwidth = _vid.width/scr_conscale
    else:
        _vid.conwidth = _vid.width

    from common import CLAMP

    _vid.conwidth = CLAMP(320, _vid.conwidth, _vid.width)
    _vid.conwidth = int(_vid.conwidth) & ~7
    _vid.conheight = _vid.conwidth * _vid.height // _vid.width

    VID_SyncCvars()

    if keys.key_dest == keys.keydest_t.key_console or keys.key_dest == keys.keydest_t.key_menu:
        if modestate == vid.modestate_t.MS_WINDOWED:
            in_sdl.IN_Deactivate(True)
        elif modestate == vid.modestate_t.MS_FULLSCREEN:
            in_sdl.IN_Activate()

def  VID_Test():
    if vid_locked or not vid_changed:
        return

    old_width       = VID_GetCurrentWidth()
    old_height      = VID_GetCurrentHeight()
    old_refreshrate = VID_GetCurrentRefreshRate()
    old_bpp         = VID_GetCurrentBPP()
    old_fullscreen  = VID_GetFullscreen()

    VID_Restart()

    if not SCR_ModalMessage('Would you like to keep this\nvideo mode? y/n', 5.0):
        cvar.Cvar_SetValueQuick('vid_width', old_width)
        cvar.Cvar_SetValueQuick('vid_height', old_height)
        cvar.Cvar_SetValueQuick('vid_refreshrate', old_refreshrate)
        cvar.Cvar_SetValueQuick('vid_bpp', old_bpp)
        cvar.Cvar_SetValueQuick('vid_fullscreen', old_fullscreen)
        VID_Restart()

def VID_DescribeCurrentMode_f():
    if draw_context:
        console.Con_Printf('%dx%dx%d %dHz %s' % VID_GetCurrentWidth(), VID_GetCurrentHeight(), VID_GetCurrentBpp(), VID_GetCurrentRefreshRate(), ( 'fullscreen' if VID_GetFullScreen() else 'windowed') )

def VID_DescribeModes_f():
    lastwidth = lastheight = lastbpp = count = 0

    for i in range(nummodes):
        if lastwidth != modelist[i].width or lastheight != modelist[i].height or lastbpp != modelist[i].bpp:
            if count > 0:
                console.Con_Printf('\n')
            console.Con_Printf('    %i x %i x %i : %i' % modelist[i].width, modelist[i].height, modelist[i].bpp, modelist[i].refreshrate)
            lastwidth = modelist[i].width
            lastheight = modelist[i].height
            lastbpp = modelist[i].bpp
            count += 1

    console.Con_Printf(f'\n{count} modes\n')

def VID_SDL2_GetDisplayMode(width, height, refreshrate, bpp) -> sdl2.SDL_DisplayMode:
    mode = sdl2.SDL_DisplayMode()
    sdlmodes = sdl2.SDL_GetNumDisplayModes(0)

    for i in range(sdlmodes):
        if sdl2.SDL_GetDisplayMode(0, i, mode) != 0:
            continue

        if mode.w == width and mode.h == height and sdl2.SDL_BITSPERPIXEL(mode.format) == bpp and mode.refresh_rate == refreshrate:
            return mode

    return None

def VID_ValidMode(width, height, refreshrate, bpp, fullscreen):
    if fullscreen and cvar.Cvar_GetCvar('vid_desktopfullscreen').value:
        return True

    if width < 320:
        return False

    if height < 200:
        return False

    if fullscreen and VID_SDL2_GetDisplayMode(width, height, refreshrate, bpp) is None:
        bpp = 0

    return bpp in [16, 24, 32]

def VID_GetFullscreen():
    return (sdl2.SDL_GetWindowFlags(draw_context) & sdl2.SDL_WINDOW_FULLSCREEN) != 0

def VID_GetCurrentWidth():
    w = ctypes.c_int()
    h = ctypes.c_int()
    sdl2.SDL_GetWindowSize(draw_context, w, h)
    return w.value

def VID_GetCurrentHeight():
    w = ctypes.c_int()
    h = ctypes.c_int()

    sdl2.SDL_GetWindowSize(draw_context, w, h)
    return h.value

def VID_GetCurrentBPP():
    pixelFormat = sdl2.SDL_GetWindowPixelFormat(draw_context)
    return sdl2.SDL_BITSPERPIXEL(pixelFormat)

def VID_GetCurrentRefreshRate():
    mode = sdl2.SDL_DisplayMode()
    current_display = sdl2.SDL_GetWindowDisplayIndex(draw_context)

    if sdl2.SDL_GetCurrentDisplayMode(current_display, mode) != 0:
        return DEFAULT_REFRESHRATE

    return mode.refresh_rate

def VID_GetFullscreen() -> bool:
    return ( sdl2.SDL_GetWindowFlags(draw_context) & sdl2.SDL_WINDOW_FULLSCREEN) != 0

def VID_GetDesktopFullscreen() -> bool:
    return (sdl2.SDL_GetWindowFlags(draw_context) & sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP) == sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP

def VID_GetVSync() -> bool:
    return sdl2.SDL_GL_GetSwapInterval() == 1




def VID_SetMode(width, height, refreshrate, bpp, fullscreen):
    global draw_context
    global gl_context
    global modestate
    global gl_stencilbits

    temp = gl_screen.scr_disabled_for_loading
    gl_screen.scr_disabled_for_loading = True

    #CDAudio_Pause()
    #BGM_Pause()

    depthbits = 24
    stencilbits = 8

    if bpp == 16:
        depthbits = 16
        stencilbits = 0

    sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DEPTH_SIZE, depthbits)
    sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_STENCIL_SIZE, stencilbits)

    sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLEBUFFERS, 1 if int(fsaa) > 0 else 0)
    sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLESAMPLES, int(fsaa))

    caption = f'QuakeSpasm {quakedef.QUAKESPASM_VER_STRING}'

    previous_display = 0

    flags = 0
    if not draw_context:
        flags = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_HIDDEN

        if cvar.Cvar_GetCvar('vid_borderless').value:
            flags |= sdl2.SDL_WINDOW_BORDERLESS

        width = int(width)
        height = int(height)

        draw_context = sdl2.SDL_CreateWindow(caption.encode('utf-8'), sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, width, height, flags)

        if draw_context is None:
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLEBUFFERS, 0)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLESAMPLES, 0)
            draw_context = sdl2.SDL_CreateWindow(caption, sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, width, height, flags)

        if draw_context is None:
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DEPTH_SIZE, 16)
            draw_context = sdl2.SDL_CreateWindow(caption, sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, width, height, flags)

        if draw_context is None:
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_STENCIL_SIZE, 0)
            draw_context = sdl2.SDL_CreateWindow(caption, sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, width, height, flags)

        if draw_context is None:
            Sys_Error('Couldnt create window')

        previous_display = -1

    else:
        previous_display = sdl2.SDL_GetWindowDisplayIndex(draw_context)

    if VID_GetFullscreen() and sdl2.SDL_SetWindowFullscreen(draw_context, 0) != 0:
        sys_sdl_unix.Sys_Error('Couldnt set fullscreen state mode')

    sdl2.SDL_SetWindowSize(draw_context, width, height)

    if previous_display >= 0:
        sdl2.SDL_SetWindowPosition(draw_context, sdl2.SDL_WINDOWPOS_CENTERED_DISPLAY(previous_display), sdl2.SDL_WINDOWPOS_CENTERED_DISPLAY(previous_display))
    else:
        sdl2.SDL_SetWindowPosition(draw_context, sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED)

    sdl2.SDL_SetWindowDisplayMode(draw_context, VID_SDL2_GetDisplayMode(width, height, refreshrate, bpp))

    sdl2.SDL_SetWindowBordered(draw_context, int(cvar.Cvar_GetCvar('vid_borderless').value)) # cvar get may return "" instead of int

    if fullscreen:
        flag = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP if cvar.Cvar_GetCvar('vid_borderless').value else sdl2.SDL_WINDOW_FULLSCREEN

        if sdl2.SDL_SetWindowFullscreen(draw_context, flag) != 0:
            sys_sdl_unix.Sys_Error('couldnt set fullscreen state mode')

    sdl2.SDL_ShowWindow(draw_context)
    sdl2.SDL_RaiseWindow(draw_context)

    if gl_context is None:
        gl_context = sdl2.SDL_GL_CreateContext(draw_context)

        if gl_context is None:
            sys_sdl_unix.Sys_Error('failed to create GL context')

    global gl_swap_control
    gl_swap_control = True

    if sdl2.SDL_GL_SetSwapInterval(int(cvar.Cvar_GetCvar('vid_vsync').value)) == -1:
        gl_swap_control = False

    _vid.width = VID_GetCurrentWidth()
    _vid.height = VID_GetCurrentHeight()
    _vid.conwidth = _vid.width & ~7
    _vid.conheight = _vid.conwidth * _vid.height // _vid.width
    _vid.numpages = 2

    _depthbits = ctypes.c_int()
    if sdl2.SDL_GL_GetAttribute(sdl2.SDL_GL_DEPTH_SIZE, _depthbits) == -1:
        depthbits = 0
    else:
        depthbits = _depthbits.value

    _fsaa_obtained = ctypes.c_int()
    if sdl2.SDL_GL_GetAttribute(sdl2.SDL_GL_MULTISAMPLESAMPLES, _fsaa_obtained) == -1:
        fsaa_obtained = 0
    else:
        fsaa_obtained = _fsaa_obtained.value

    _gl_stencilbits = ctypes.c_int()
    if sdl2.SDL_GL_GetAttribute(sdl2.SDL_GL_STENCIL_SIZE, _gl_stencilbits) == -1:
        gl_stencilbits = 0
    else:
        gl_stencilbits = _gl_stencilbits.value

    modestate = vid.modestate_t.MS_FULLSCREEN if VID_GetFullscreen() else vid.modestate_t.MS_WINDOWED

    gl_screen.scr_disabled_for_loading = temp

    ClearAllStates()

    console.Con_Printf('Video mode %dx%dx%d %dHz (%d-bit z-buffer, %dx FSAA) initialized' %
       (VID_GetCurrentWidth(),
        VID_GetCurrentHeight(),
        VID_GetCurrentBPP(),
        VID_GetCurrentRefreshRate(),
        depthbits,
        fsaa_obtained))

def ClearAllStates():
    keys.Key_ClearStates()
    in_sdl.IN_ClearStates()

def GL_MakeNiceExtensionList(gl_ext):
    global gl_extensions_nice

    gl_extensions_nice = gl_ext.split(' ')

    #print(gl_extensions_nice)

    return gl_extensions_nice

def GL_ParseExtensionList(list, name):
    return name in list

def GL_CheckExtensions():
    global gl_vbo_able
    global gl_mtexable
    global gl_max_texture_units
    global gl_texture_env_combine
    global gl_texture_env_add
    global gl_anisotropy_able
    global gl_max_anisotropy
    global gl_texture_NPOT
    global gl_glsl_able
    global gl_glsl_gamma_able
    global gl_packed_pixels
    global gl_glsl_alias_able

    swap_control = False
    gl_swap_control = False

    if common.COM_CheckParm('-novbo'):
        console.Con_Warning('Vertex buffer objects disabled at command line')
    elif gl_version_major < 1 or ( gl_version_major == 1 and gl_version_minor < 5 ):
        console.Con_Warning('OpenGL version < 1.5, skipping ARB_vertex_buffer_object check')
    else:
        console.Con_Printf('Found: ARB_vertex_buffer_object')
        gl_vbo_able = True

    if common.COM_CheckParm('-nomtex'):
        console.Con_Warning('Multitexture disabled at command line')
    elif GL_ParseExtensionList(gl_extensions, 'GL_ARB_multitexture'):
        gl_mtexable = True

        max_tex_units = ctypes.c_int()
        OpenGL.GL.glGetInteger(OpenGL.GL.GL_MAX_TEXTURE_UNITS, max_tex_units)
        gl_max_texture_units = max_tex_units.value
    else:
        console.Con_Warning('multitexture not supported ( ext not found )')

    if common.COM_CheckParm('-nocombine'):
        console.Con_Warning('texture_env_combine disabled at command line')
    elif GL_ParseExtensionList(gl_extensions, 'GL_ARB_texture_env_combine') or GL_ParseExtensionList(gl_extensions, 'GL_EXT_texture_env_combine'):
        gl_texture_env_combine = True
    else:
        console.Con_Warning('texture_env_combine not supported')

    if common.COM_CheckParm('-noadd'):
        console.Con_Warning('texture_env_add disabled at command line')
    elif GL_ParseExtensionList(gl_extensions, 'GL_ARB_texture_env_add') or GL_ParseExtensionList(gl_extensions, 'GL_EXT_texture_env_add'):
        gl_texture_env_add = True
    else:
        console.Con_Warning('texture_env_add not supported')

    if not gl_swap_control:
        console.Con_Warning('vert sync not supported')
    elif sdl2.SDL_GL_GetSwapInterval() == -1:
        swap_control    = False
        gl_swap_control = False
        console.Con_Warning('vert sync not supported')
    elif int(cvar.Cvar_GetCvar('vid_sync').value) and swap_control != 1 or int(cvar.Cvar_GetCvar('vid_sync').value) and swap_control != 0:
        gl_swap_control = False
        console.Con_Warning('vert sync not supported')
    else:
        console.Con_Printf('Found: SDL_GL_SetSwapInterval')

    if GL_ParseExtensionList(gl_extensions, 'GL_EXT_texture_filter_anisotropic'):
        test1 = ctypes.c_float()
        test2 = ctypes.c_float()

        tex = OpenGL.GL.glGenTextures(1)
        OpenGL.GL.glBindTexture(OpenGL.GL.GL_TEXTURE_2D, tex)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAX_ANISOTROPY, 1.0)
        OpenGL.GL.glGetTexParameterfv(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAX_ANISOTROPY, test1)
        OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAX_ANISOTROPY, 2.0)
        OpenGL.GL.glGetTexParameterfv(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAX_ANISOTROPY, test2)
        OpenGL.GL.glDeleteTextures(1, tex)


        if test1.value == 1 and test2.value == 2:
            console.Con_Printf('Found: EXT_texture_filter_anisotropic')
            gl_anisotropy_able = True
        else:
            console.Con_Warning(f'anisotropic filtering locked by driver, current setting is {test1:f}')


        max_anisotropy = ctypes.c_float()
        OpenGL.GL.glGetFloatv(OpenGL.GL.GL_MAX_TEXTURE_MAX_ANISOTROPY, max_anisotropy)
        gl_max_anisotropy = max_anisotropy.value
        if ( gl_max_anisotropy < 2):
            gl_anisotropy_able = False
            gl_max_anisotropy = 1
            console.Con_Warning('anisotropic filtering broken: disabled')
    else:
        gl_max_anisotropy = 1
        console.Con_Warning('texture_filter_anisotropic not supported')


    if common.COM_CheckParm('-notexturenpot'):
        console.Con_Warning('texture_non_power_of_two disabled at command line')
    elif GL_ParseExtensionList(gl_extensions, 'GL_ARB_texture_non_power_of_two'):
        console.Con_Printf('Found: GL_ARB_texture_non_power_of_two')
        gl_texture_NPOT = True
    else:
        console.Con_Warning('texture_non_power_of_two not supported\n')

    if common.COM_CheckParm('-noglsl'):
        console.Con_Warning('texture_non_power_of_two disabled at command line')
    elif gl_version_major >= 2:
        gl_glsl_able = True
    else:
        console.Con_Warning('GLSL not available\n')

    if common.COM_CheckParm('-noglslgamma'):
        console.Con_Warning('glsl gamma disabled at command line')
    elif gl_glsl_able:
        gl_glsl_gamma_able = True
        console.Con_Printf('enabled: GLSL gamma')
    else:
        console.Con_Warning('GLSL gamma not available, using hardware gamma')

    if common.COM_CheckParm('-noglslalias'):
        console.Con_Warning('glsl alias model rendering disabled at command line')
    elif gl_glsl_able and gl_vbo_able and gl_max_texture_units >= 3:
        gl_glsl_alias_able = True
        console.Con_Printf('enabled: GLSL alias model rendering')
    else:
        console.Con_Warning('GLSL alias model rendering not available, using fitz renderer')

    if common.COM_CheckParm('-nopackedpixels'):
        console.Con_Warning('EXT_packed_pixels disabled at command line')
    elif sys.byteorder == 'big':
        console.Con_Warning('EXT_packed_pixels disabled on big endian systems')
    elif gl_glsl_alias_able:
        gl_packed_pixels = True
        console.Con_Printf('Enabled: EXT_packed_pixels')

    if common.COM_CheckParm('-nowarpmipmaps'):
        console.Con_Warning('glGenerateMipmap disabled at command line')
    else:
        if gl_version_major >= 3 or GL_ParseExtensionList(gl_extensions, 'GL_ARB_framebuffer_object') or GL_ParseExtensionList(gl_extensions, 'GL_EXT_framebuffer_object'):
            console.Con_Printf('Found: glGenerateMipmap')
        else:
            console.Con_Warning('glGenerateMipmap not available, liquids wont have mipmaps')


def GL_SetupState():
    OpenGL.GL.glClearColor(0.15, 0.15, 0.15, 0)
    OpenGL.GL.glCullFace(OpenGL.GL.GL_BACK)
    OpenGL.GL.glFrontFace(OpenGL.GL.GL_CW)
    OpenGL.GL.glEnable(OpenGL.GL.GL_TEXTURE_2D)
    OpenGL.GL.glEnable(OpenGL.GL.GL_ALPHA_TEST)
    OpenGL.GL.glAlphaFunc(OpenGL.GL.GL_GREATER, 0.666)
    OpenGL.GL.glPolygonMode(OpenGL.GL.GL_FRONT_AND_BACK, OpenGL.GL.GL_FILL)
    OpenGL.GL.glShadeModel(OpenGL.GL.GL_FLAT)
    OpenGL.GL.glHint(OpenGL.GL.GL_PERSPECTIVE_CORRECTION_HINT, OpenGL.GL.GL_NICEST)
    OpenGL.GL.glBlendFunc(OpenGL.GL.GL_SRC_ALPHA, OpenGL.GL.GL_ONE_MINUS_SRC_ALPHA)
    OpenGL.GL.glTexEnvf(OpenGL.GL.GL_TEXTURE_ENV, OpenGL.GL.GL_TEXTURE_ENV_MODE, OpenGL.GL.GL_REPLACE)
    OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MIN_FILTER, OpenGL.GL.GL_NEAREST)
    OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_MAG_FILTER, OpenGL.GL.GL_NEAREST)
    OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_WRAP_S, OpenGL.GL.GL_REPEAT)
    OpenGL.GL.glTexParameterf(OpenGL.GL.GL_TEXTURE_2D, OpenGL.GL.GL_TEXTURE_WRAP_T, OpenGL.GL.GL_REPEAT)
    OpenGL.GL.glDepthRange(0, 1)
    OpenGL.GL.glDepthFunc(OpenGL.GL.GL_LEQUAL)

    OpenGL.GL.glClearColor(0.15, 0.15, 0.15, 1.0)
    OpenGL.GL.glEnable(OpenGL.GL.GL_DEPTH_TEST) # Ensure depth testing is ON
    OpenGL.GL.glDepthFunc(OpenGL.GL.GL_LEQUAL)

    OpenGL.GL.glEnable(OpenGL.GL.GL_CULL_FACE)
    OpenGL.GL.glCullFace(OpenGL.GL.GL_BACK)
    OpenGL.GL.glFrontFace(OpenGL.GL.GL_CW) # Quake uses clockwise winding

    OpenGL.GL.glEnable(OpenGL.GL.GL_TEXTURE_2D)
    OpenGL.GL.glShadeModel(OpenGL.GL.GL_SMOOTH) # Better for lightmaps

    # Standard Quake alpha testing for fences/grates
    OpenGL.GL.glEnable(OpenGL.GL.GL_ALPHA_TEST)
    OpenGL.GL.glAlphaFunc(OpenGL.GL.GL_GREATER, 0.5)

def GL_Init():
    global gl_vendor, gl_renderer
    global gl_version, gl_version_major, gl_version_minor
    global gl_extensions #, gl_extensions_nice

    gl_vendor     = OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR).decode('ascii')
    gl_renderer   = OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER).decode('ascii')
    gl_version    = OpenGL.GL.glGetString(OpenGL.GL.GL_VERSION).decode('ascii')
    gl_extensions = OpenGL.GL.glGetString(OpenGL.GL.GL_EXTENSIONS).decode('ascii')

    console.Con_Printf(f'GL_VENDOR: {gl_vendor}')
    console.Con_Printf(f'GL_RENDERER: {gl_renderer}')
    console.Con_Printf(f'GL_VERSION: {gl_version}')

    if gl_version is None:
        gl_version_major = gl_version_minor = 0
    else:
        gl_version_major, gl_version_minor, *rest = str(gl_version).split('.')
        gl_version_major = int(gl_version_major)
        gl_version_minor = int(gl_version_minor)

    console.Con_Printf(f'GL_VERSION major: {gl_version_major}')
    console.Con_Printf(f'GL_VERSION minor: {gl_version_minor}')

    gl_extensions = GL_MakeNiceExtensionList(gl_extensions)

    GL_CheckExtensions()

    r_alias.GLAlias_CreateShaders()
    r_world.GLWorld_CreateShaders()
    gl_rmisc.GL_ClearBufferBindings()


def GL_Info_f():
    console.Con_Printf(f'GL_VENDOR {gl_vendor}' )
    console.Con_Printf(f'GL_RENDERER {gl_renderer}' )
    console.Con_Printf(f'GL_VERSION {gl_version}' )
    console.Con_Printf('GL_EXTENSIONS {}'.format('\n'.join(gl_extensions_nice)) )

def VID_Init():
    import cvar
    global read_vars
    global fsaa

    vid_fullscreen        = {'name':'vid_fullscreen',        'value': '0', 'flags': cvar.CVAR_ARCHIVE}
    vid_width             = {'name':'vid_width',             'value': '0', 'flags': cvar.CVAR_ARCHIVE}
    vid_height            = {'name':'vid_height',            'value': '0', 'flags': cvar.CVAR_ARCHIVE}
    vid_bpp               = {'name':'vid_bpp',               'value':'16', 'flags': cvar.CVAR_ARCHIVE}
    vid_refreshrate       = {'name':'vid_refreshrate',       'value':'60', 'flags': cvar.CVAR_ARCHIVE}
    vid_vsync             = {'name':'vid_vsync',             'value': '0', 'flags': cvar.CVAR_ARCHIVE}
    vid_fsaa              = {'name':'vid_fsaa',              'value': '0', 'flags': cvar.CVAR_ARCHIVE}
    vid_desktopfullscreen = {'name':'vid_desktopfullscreen', 'value': '0', 'flags': cvar.CVAR_ARCHIVE}
    vid_borderless        = {'name':'vid_borderless',        'value': '0', 'flags': cvar.CVAR_ARCHIVE}

    vid_gamma    = {'name':'gamma',    'value':'1', 'flags': cvar.CVAR_ARCHIVE}
    vid_contrast = {'name':'contrast', 'value':'1', 'flags': cvar.CVAR_ARCHIVE}

    read_vars = [
       'vid_fullscreen',
       'vid_width',
       'vid_height',
       'vid_refreshrate',
       'vid_bpp',
       'vid_vsync',
       'vid_fsaa',
       'vid_desktopfullscreen',
       'vid_borderless',
    ]

    cvar.Cvar_RegisterVariable(vid_fullscreen)
    cvar.Cvar_RegisterVariable(vid_width)
    cvar.Cvar_RegisterVariable(vid_height)
    cvar.Cvar_RegisterVariable(vid_bpp)
    cvar.Cvar_RegisterVariable(vid_refreshrate)
    cvar.Cvar_RegisterVariable(vid_vsync)
    cvar.Cvar_RegisterVariable(vid_fsaa)
    cvar.Cvar_RegisterVariable(vid_desktopfullscreen)
    cvar.Cvar_RegisterVariable(vid_borderless)
    cvar.Cvar_RegisterVariable(vid_gamma)
    cvar.Cvar_RegisterVariable(vid_contrast)

    cvar.Cvar_SetCallback(vid_fullscreen, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_width, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_height, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_refreshrate, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_bpp, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_vsync, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_fsaa, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_desktopfullscreen, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_borderless, VID_Changed_f)

    _cmd.Cmd_AddCommand('vid_unlock', VID_Unlock)
    _cmd.Cmd_AddCommand('vid_restart', VID_Restart)
    _cmd.Cmd_AddCommand('vid_test', VID_Test)
    _cmd.Cmd_AddCommand('vid_describecurrentmode', VID_DescribeCurrentMode_f)
    _cmd.Cmd_AddCommand('vid_describemodes', VID_DescribeModes_f)

    os.putenv('SDL_VIDEO_CENTERED', 'center' )

    if sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_VIDEO) < 0:
        sys_sdl_unix.Sys_Error(f'Couldnt init SDL Video {sdl2.SDL_GetError()}')

    displaymode = sdl2.SDL_DisplayMode()

    sdl2.SDL_GetDesktopDisplayMode(0, displaymode)

    display_width  = displaymode.w
    display_height = displaymode.h
    display_refreshrate = displaymode.refresh_rate
    display_bpp = sdl2.SDL_BITSPERPIXEL(displaymode.format)

    cvar.Cvar_SetValueQuick('vid_bpp', display_bpp)

    if cfgfile.CFG_OpenConfig('config.cfg') == 0:
        cfgfile.CFG_ReadCvars(read_vars)
        cfgfile.CFG_CloseConfig()

    cfgfile.CFG_ReadCvarOverrides(read_vars)

    VID_InitModelist()

    width  = cvar.Cvar_GetCvar('vid_width').value
    height = cvar.Cvar_GetCvar('vid_height').value
    refreshrate = cvar.Cvar_GetCvar('vid_refreshrate').value
    bpp = cvar.Cvar_GetCvar('vid_bpp').value
    fullscreen = cvar.Cvar_GetCvar('vid_fullscreen').value
    fsaa  = int(cvar.Cvar_GetCvar('vid_fsaa').value)

    if common.COM_CheckParm('-current'):
        width = display_width
        height = display_height
        refreshrate = display_refreshrate
        bpp = display_bpp
        fullscreen = True
    else:
        p = common.COM_CheckParm('-width')
        if p and p < common.com_argc - 1:
            width = int(common.argv[p+1])
            if not common.COM_CheckParm('-height'):
                height = width * float(3/4)

        p = common.COM_CheckParm('-height')
        if p and p < common.com_argc - 1:
            height = int(common.argv[p+1])
            if not common.COM_CheckParm('-width'):
                height = width * float(4/3)

        p = common.COM_CheckParm('-refreshrate')
        if p and p < common.com_argc - 1:
            refreshrate = int(common.argv[p+1])

        p = common.COM_CheckParm('-bpp')
        if p and p < common.com_argc - 1:
            bpp = int(common.argv[p+1])

        if common.COM_CheckParm('-window') or common.COM_CheckParm('-w'):
            fullscreen = False
        elif common.COM_CheckParm('-fullscreen') or common.COM_CheckParm('-f'):
            fullscreen = True

    p = common.COM_CheckParm('-fsaa')
    if p and p < common.com_argc - 1:
        fsaa = int(common.com_argv[p+1])

    if not VID_ValidMode(width, height, refreshrate, bpp, fullscreen):
        width  = cvar.Cvar_GetCvar('vid_width').value
        height = cvar.Cvar_GetCvar('vid_height').value
        refreshrate = cvar.Cvar_GetCvar('vid_refreshrate').value
        bpp = cvar.Cvar_GetCvar('vid_bpp').value
        fullscreen = cvar.Cvar_GetCvar('vid_fullscreen').value

    if not VID_ValidMode(width, height, refreshrate, bpp, fullscreen):
        width  = 640
        height = 480
        refreshrate = display_refreshrate
        bpp =  display_bpp
        fullscreen = False

    global vid_initialized
    vid_initialized = True

    _vid.maxwarpwidth = WARP_WIDTH
    _vid.maxwarpheight = WARP_HEIGHT
    _vid.colormap = host.host_colormap
    _vid.fullbright = 256 - 0; # vid.fullbright = 256 - LittleLong (*((int *)vid.colormap + 2048));

    VID_SetMode(width, height, refreshrate, bpp, fullscreen)

    GL_Init()
    GL_SetupState()

    _cmd.Cmd_AddCommand('gl_info', GL_Info_f)

    menu.vid_menucmdfn = VID_Menu_f
    menu.vid_menudrawfn = VID_MenuDraw
    menu.vid_menukeyfn = VID_MenuKey

    VID_Gamma_Init()
    VID_Menu_Init()

    import gl_warp
    gl_warp.GL_WarpInit()

    global vid_locked
    vid_locked = True

def VID_Menu_Init():
    global vid_menu_nummodes

    i = j = h = w = 0

    for i in range(nummodes):
        w = modelist[i].width
        h = modelist[i].height

        for j in range(vid_menu_nummodes):
            if vid_menu_modes[i].width == w and vid_menu_modes[i].height == h:
                break

        if j == vid_menu_nummodes:
            vid_menu_modes[j].width = w
            vid_menu_modes[j].height = h
            vid_menu_nummodes += 1

def VID_Gamma_f():
    if gl_glsl_gamma_able:
        return

    # shouldn't get here
    raise NotImplementedError
    VID_Gamma_SetGamma()

def VID_Gamma_Init():
    global gammaworks
    import cvar

    vid_gamma    = {'name':"gamma",    'value':"1", 'flags': cvar.CVAR_ARCHIVE}; #johnfitz -- moved here from view.c
    vid_contrast = {'name':"contrast", 'value':"1", 'flags': cvar.CVAR_ARCHIVE}; #QuakeSpasm, MarkV

    cvar.Cvar_RegisterVariable(vid_gamma)
    cvar.Cvar_RegisterVariable(vid_contrast)
    cvar.Cvar_SetCallback(vid_gamma,    VID_Gamma_f)
    cvar.Cvar_SetCallback(vid_contrast, VID_Gamma_f)

    if gl_glsl_gamma_able:
        return

    gammaworks = bool( sdl2.SDL_SetWindowBrightness(draw_context, 1) == 0)

    if not gammaworks:
        console.Con_Printf('gamma adjustment not available')





def VID_Menu_RebuildBppList():
    global vid_menu_numbpps
    global vid_menu_bpps

    vid_menu_numbpps = 0

    for i in range(nummodes):
        if vid_menu_numbpps >= MAX_BPPS_LIST:
            break
        if modelist[i].width != cvar.Cvar_GetCvar('vid_width').value or modelist[i].height != cvar.Cvar_GetCvar('vid_height').value:
            continue

        b = modelist[i].bpp

        for j in range(vid_menu_numbpps):
            if vid_menu_bpps[j] == b:
                break

        if j == vid_menu_numbpps:
            vid_menu_bpps[j] = b
            vid_menu_numbpps += 1

    if vid_menu_numbpps == 0:
        cvar.Cvar_SetValueQuick('vid_bpp', modelist[0].bpp)
        return


    for i in range(vid_menu_numbpps):
        if vid_menu_bpps[i] == int(cvar.Cvar_GetCvar('vid_bpp').value):
            break

    if i == vid_menu_numbpps:
        cvar.Cvar_SetValueQuick('vid_bpp', vid_menu_bpps[0])


def VID_Menu_RebuildRateList():
    global vid_menu_numrates
    global vid_menu_rates

    vid_menu_numrates = 0

    for i in range(nummodes):
        if modelist[i].width != cvar.Cvar_GetCvar('vid_width').value or \
            modelist[i].height != cvar.Cvar_GetCvar('vid_height').value or \
            modelist[i].bpp != cvar.Cvar_GetCvar('vid_bpp').value:
            continue

        r = modelist[i].refreshrate

        for j in range(vid_menu_numrates):
            if vid_menu_rates[j] == r:
                break

        if j == vid_menu_numrates:
            vid_menu_rates[j] = r
            vid_menu_numrates += 1

    if vid_menu_numrates == 0:
        cvar.Cvar_SetValue('vid_refreshrate', modelist[0].refreshrate)
        return

    for i in range(vid_menu_numrates):
        if vid_menu_rates[i] == int(cvar.Cvar_GetCvar('vid_refreshrate').value):
            break

    if i == vid_menu_numrates:
        cvar.Cvar_SetValue('vid_refreshrate', vid_menu_rates[0])

def VID_MenuDraw():
    y = 4

    p = gl_draw.Draw_CachePic('gfx/qplaque.lmp')
    menu.M_DrawTransPic(16, y, p)

    p = gl_draw.Draw_CachePic('gfx/p_option.lmp')
    menu.M_DrawPic ( ( 320 - p.width) / 2, y, p)

    y += 28

    title = 'Video Options'

    menu.M_PrintWhite((320-8*len(title))/2, y, title)

    y += 16

    for i in range(gl_vidsdl.VIDEO_OPTIONS_ITEMS):
        match i:
            case gl_vidsdl.vid_opt_e.VID_OPT_MODE:
                menu.M_Print(16, y, "        Video mode")
                menu.M_Print (184, y, va("%ix%i", int(cvar.Cvar_GetCvar('vid_width').value), int(cvar.Cvar_GetCvar('vid_height').value)))

            case gl_vidsdl.vid_opt_e.VID_OPT_BPP:
                menu.M_Print (16, y, "       Color depth");
                menu.M_Print (184, y, f'{int(cvar.Cvar_GetCvar('vid_bpp').value)}')

            case gl_vidsdl.vid_opt_e.VID_OPT_REFRESHRATE:
                menu.M_Print (16, y, "      Refresh rate");
                menu.M_Print (184, y, f"{int(cvar.Cvar_GetCvar('vid_refreshrate').value)}")

            case gl_vidsdl.vid_opt_e.VID_OPT_FULLSCREEN:
                menu.M_Print (16, y, "        Fullscreen");
                menu.M_DrawCheckbox (184, y, int(cvar.Cvar_GetCvar('vid_fullscreen').value))

            case gl_vidsdl.vid_opt_e.VID_OPT_VSYNC:
                menu.M_Print (16, y, "     Vertical sync");
                if gl_swap_control:
                    M_DrawCheckbox (184, y, int(cvar.Cvar_GetCvar('vid_vsync').value))
                else:
                    menu.M_Print (184, y, "N/A");

            case gl_vidsdl.vid_opt_e.VID_OPT_TEST:
                y += 8
                menu.M_Print(16, y, "      Test changes")

            case gl_vidsdl.vid_opt_e.VID_OPT_APPLY:
                menu.M_Print (16, y, "     Apply changes")

        if video_options_cursor == i:
            menu.M_DrawCharacter(168, y, 12 + (int(host.realtime)*4)&1)

        y += 8











def VID_Menu_ChooseNextMode(_dir):
    if vid_menu_nummodes:
        for i in range(vid_menu_nummodes):
            if vid_menu_modes[i].width == cvar.Cvar_GetCvar('vid_width').value and vid_menu_modes[i].height == cvar.Cvar_GetCvar('vid_height').value:
                break
        if i == vid_menu_nummodes:
            i = 0
        else:
            i += _dir
            if i >= vid_menu_nummodes:
                i = 0
            elif i < 0:
                i = vid_menu_nummodes - 1

        cvar.Cvar_SetValueQuick('vid_width', vid_menu_modes[i].width)
        cvar.Cvar_SetValueQuick('vid_height', vid_menu_modes[i].height)

        VID_Menu_RebuildBppList()
        VID_Menu_RebuildRateList()

def VID_Menu_ChooseNextBPP(dir):
    if vid_menu_numbpps:
        for i in range(vid_menu_numbpps):
            if vid_menu_bpps[i] == cvar.Cvar_GetCvar('vid_bpp').value:
                break
        if i == vid_menu_numbpps:
            i = 0
        else:
            i += dir
            if i >= vid_menu_numbpps:
                i = 0
            elif i < 0:
                i = vid_menu_numbpps - 1

        cvar.Cvar_SetValueQuick('vid_bpp', vid_menu_bpps[i])


def VID_Menu_ChooseNextRate(_dir):
    if vid_menu_numrates:
        for i in range(vid_menu_numrates):
            if vid_menu_rates[i] == cvar.Cvar_GetCvar('vid_refreshrate').value:
                break
        if i == vid_menu_numrates:
            i = 0
        else:
            i += _dir
            if i >= vid_menu_numrates:
                i = 0
            elif i < 0:
                i = vid_menu_numrates - 1

        cvar.Cvar_SetValueQuick('vid_refreshrate', vid_menu_rates[i])

def VID_MenuKey(key):
    global video_options_cursor

    match key:
        case keys.K_ESCAPE | keys.K_BBUTTON:
            VID_SyncCvars()
            snd_dma.S_LocalSound('misc/menu1.wav')
            menu.M_Menu_Options_f()
        case keys.K_UPARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            video_options_cursor -= 1
            if video_options_cursor < 0:
                video_options_cursor = vid_opt_e.VIDEO_OPTIONS_ITEMS - 1
        case keys.K_DOWNARROW:
            snd_dma.S_LocalSound('misc/menu1.wav')
            video_options_cursor += 1
            if video_options_cursor > vid_opt_e.VIDEO_OPTIONS_ITEMS:
                video_options_cursor = 0
        case keys.K_LEFTARROW:
            snd_dma.S_LocalSound('misc/menu3.wav')
            match video_options_cursor:
                case vid_opt_e.VID_OPT_MODE:
                    VID_Menu_ChooseNextMode(1)
                case vid_opt_e.VID_OPT_BPP:
                    VID_Menu_ChooseNextBPP(1)
                case vid_opt_e.VID_OPT_REFRESHRATE:
                    VID_Menu_ChooseNextRate(1)
                case vid_opt_e.VID_OPT_FULLSCREEN:
                    Cbuf_AddText('toggle vid_fullscreen\n')
                case vid_opt_e.VID_OPT_VSYNC:
                    Cbuf_AddText('toggle vid_vsync\n')
        case keys.K_RIGHTARROW:
            snd_dma.S_LocalSound('misc/menu3.wav')
            match video_options_cursor:
                case vid_opt_e.VID_OPT_MODE:
                    VID_Menu_ChooseNextMode(-1)
                case vid_opt_e.VID_OPT_BPP:
                    VID_Menu_ChooseNextBPP(-1)
                case vid_opt_e.VID_OPT_REFRESHRATE:
                    VID_Menu_ChooseNextRate(-1)
                case vid_opt_e.VID_OPT_FULLSCREEN:
                    Cbuf_AddText('toggle vid_fullscreen\n')
                case vid_opt_e.VID_OPT_VSYNC:
                    Cbuf_AddText('toggle vid_vsync\n')


        case keys.K_ENTER | keys.K_KP_ENTER | keys.K_ABUTTON:
            m_entersound = True
            match video_options_cursor:
                case vid_opt_e.VID_OPT_MODE:
                    VID_Menu_ChooseNextMode(1)
                case vid_opt_e.VID_OPT_BPP:
                    VID_Menu_ChooseNextBPP(1)
                case vid_opt_e.VID_OPT_REFRESHRATE:
                    VID_Menu_ChooseNextRate(1)
                case vid_opt_e.VID_OPT_FULLSCREEN:
                    Cbuf_AddText('toggle vid_fullscreen\n')
                case vid_opt_e.VID_OPT_VSYNC:
                    Cbuf_AddText('toggle vid_vsync\n')
                case vid_opt_e.VID_OPT_APPLY:
                    Cbuf_AddText('vid_restart\n')
                    keys.key_dest = keys.keydest_t.key_game
                    menu.m_state = menu.m_state_e.m_none
                    IN_Activate()


def VID_Shutdown():
    global gl_context
    global draw_context

    if vid_initialized:
        sdl2.SDL_GL_DeleteContext(gl_context)
        gl_context = None
        sdl2.SDL_DestroyWindow(draw_context)
        sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_VIDEO)
        draw_context = None


def VID_Menu_f():
    in_sdl.IN_Deactivate(modestate == vid.modestate_t.MS_WINDOWED)
    keys.key_dest = keys.keydest_t.key_menu
    menu.m_state = menu.m_state_e.m_video
    menu.m_entersound = True

    VID_SyncCvars()

    VID_Menu_RebuildBppList()
    VID_Menu_RebuildRateList()

def VID_SyncCvars():
    global vid_changed
    if draw_context:
        if not VID_GetDesktopFullscreen():
            cvar.Cvar_SetValueQuick('vid_width', VID_GetCurrentWidth())
            cvar.Cvar_SetValueQuick('vid_height', VID_GetCurrentHeight())

        cvar.Cvar_SetValueQuick('vid_refreshrate', VID_GetCurrentRefreshRate())
        cvar.Cvar_SetValueQuick('vid_bpp', VID_GetCurrentBPP())
        cvar.Cvar_SetValueQuick('vid_fullscreen', '1' if VID_GetFullscreen() else "0")
        cvar.Cvar_SetValueQuick('vid_vsync', '1' if VID_GetVSync() else "0")

    vid_changed = False


def VID_SwapBuffers():
    global draw_context
    sdl2.SDL_GL_SwapWindow(draw_context)


def VID_IsMinimized():
    return sdl2.video.SDL_GetWindowFlags(draw_context) & sdl2.SDL_WINDOW_SHOWN

def VID_HasMouseOrInputFocus():
    flags = sdl2.video.SDL_GetWindowFlags(draw_context)

    return bool(flags & sdl2.SDL_WINDOW_INPUT_FOCUS or flags & sdl2.SDL_WINDOW_MOUSE_FOCUS)

def GL_BeginRendering():
    gl_screen.glx = 0
    gl_screen.gly = 0
    gl_screen.glwidth = gl_vidsdl._vid.width
    gl_screen.glheight = gl_vidsdl._vid.height

def GL_EndRendering():
    if not gl_vidsdl.scr_skipupdate:
        sdl2.SDL_GL_SwapWindow(gl_vidsdl.draw_context)


def VID_Changed_f(var: cvar.cvar_t):
    global vid_changed
    vid_changed = True


def VID_Unlock():
    global vid_locked
    vid_locked = False
    VID_SyncCvars()

def Vid_Lock():
    global vid_locked
    vid_locked = True


def VID_FSAA_f(var):
    if vid_initialized:
        console.Con_Printf(f'{var.name} {var.value} requires engine restart to take effect')



vid_toggle_works = False
def VID_Toggle():
    global vid_toggle_works
    global modestate

    toggleWorked = False
    flags = 0

    snd_dma.S_ClearBuffer()

    if not vid_toggle_works:
        cvar.Cvar_SetQuick(cvar.Cvar_GetCvar('vid_fullscreen'), "0" if VID_GetFullscreen() else "1")
        _cmd.Cbuf_AddText('vid_restart')
        return

    if gl_vbo_able:
        vid_toggle_works = False
        cvar.Cvar_SetQuick(cvar.Cvar_GetCvar('vid_fullscreen'), "0" if VID_GetFullscreen() else "1")
        _cmd.Cbuf_AddText('vid_restart')
        return

    if not VID_GetFullscreen():
        flags = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP if cvar.Cvar_GetCvar('vid_desktopfullscreen').value else sdl2.SDL_WINDOW_FULLSCREEN

    toggleWorked = sdl2.SDL_SetWindowFullscreen(draw_context, flags) == 0

    if toggleWorked:
        sbar.Sbar_Changed()

        modestate = vid.modestate_t.MS_FULLSCREEN if VID_GetFullscreen() else vid.modestate_t.MS_WINDOWED

        VID_SyncCvars()

        if keys.key_dest in [keys.keydest_t.key_console, keys.keydest_t.key_menu]:
            if modestate == vid.modestate_t.MS_WINDOWED:
                in_sdl.IN_Deactivate(True)
            elif modestate == vid.modestate_t.MS_FULLSCREEN:
                in_sdl.IN_Activate()

    else:
        vid_toggle_works = False
        console.Con_Printf('SDL_WM_ToggleFullScreen failed, attempting VID_Restart\n')
        cvar.Cvar_SetQuick(cvar.Cvar_GetCvar('vid_fullscreen'), "0" if VID_GetFullscreen() else "1")
        _cmd.Cbuf_AddText('vid_restart')

