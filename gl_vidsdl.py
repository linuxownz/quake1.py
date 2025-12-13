#gl_vidsdl.py 

import os
import sdl2
import sdl2.ext

import cfgfile
import _cmd
import gl_vidsdl
import sys_sdl_unix
from vid import modestate_t

MAX_MODE_LIST  = 600 #johnfitz -- was 30 
MAX_BPPS_LIST  = 5
MAX_RATES_LIST = 20
WARP_WIDTH     = 320
WARP_HEIGHT    = 200
MAXWIDTH       = 10000
MAXHEIGHT      = 10000

#DEFAULT_SDL_FLAGS = SDL_OPENGL

DEFAULT_REFRESHRATE = 60

class vmode_t():
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

modelist: List[vmode_t] = []
nummodes = 0

vid_initialized = False

draw_context:sdl2.SDL_Window  = None
gl_context:sdl2.SDL_GLContext = None

vid_locked = False
vid_changed = False

vid : vid.viddef_t = None

modestate : vid.modestate_t = modestate_t.MS_UNINIT

scr_skipupdate = False

gl_mtexable = False;
gl_packed_pixels = False;
gl_texture_env_combine = False; #johnfitz
gl_texture_env_add = False; #johnfitz
gl_swap_control = False; #johnfitz
gl_anisotropy_able = False; #johnfitz
max_anisotropy = 0.0; #johnfitz
gl_texture_NPOT = False; #ericw
gl_vbo_able = False; #ericw
gl_glsl_able = False; #ericw
gl_max_texture_units = 0; #ericw
gl_glsl_gamma_able = False; #ericw
gl_glsl_alias_able = False; #ericw
gl_stencilbits = 0

fsaa = 0

def VID_InitModelist():
    sdlmodes = sdl2.SDL_GetNumDisplayModes(0)



def VID_Init():
    import cvar
    global read_vars

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

    cvar.Cvar_Register(vid_fullscreen)
    cvar.Cvar_Register(vid_width)
    cvar.Cvar_Register(vid_height)
    cvar.Cvar_Register(vid_bpp)
    cvar.Cvar_Register(vid_refreshrate)
    cvar.Cvar_Register(vid_vsync)
    cvar.Cvar_Register(vid_fsaa)
    cvar.Cvar_Register(vid_desktopfullscreen)
    cvar.Cvar_Register(vid_borderless)
    #cvar.Cvar_Register(vid_gamma)
    #cvar.Cvar_Register(vid_contrast)

    cvar.Cvar_SetCallback(vid_fullscreen, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_width, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_height, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_refreshrate, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_bpp, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_vsync, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_fsaa, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_desktopfullscreen, VID_Changed_f)
    cvar.Cvar_SetCallback(vid_borderless, VID_Changed_f)

    cmd.Cmd_AddCommand('vid_unlock', VID_Unlock)
    cmd.Cmd_AddCommand('vid_restart', VID_Restart)
    cmd.Cmd_AddCommand('vid_test', VID_Test)
    cmd.Cmd_AddCommand('vid_describecurrentmode', VID_DescribeCurrentMode_f)
    cmd.Cmd_AddCommand('vid_describemodes', VID_DescribeModes_f)

    os.putenv('SDL_VIDEO_CENTERED=center')

    if sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_VIDEO) < 0:
        sys_sdl_unix.Sys_Error(f'Couldnt init SDL Video {sdl2.SDL_GetError()}')

    displaymode = sdl2.SDL_DisplayMode()

    mode = sdl2.SDL_GetDesktopDisplayMode(0, displaymode)

    display_width  = mode.w
    display_height = mode.h
    display_refreshrate = mode.refresh_rate
    display_bpp = sdl2.SDL_BITSPERPIXEL(mode.format)
    
    cvar.Cvar_SetValueQuick(vid_bpp, display_bpp)

    if cfgfile.CFG_OpenConfig('config.cfg') == 0:
        cfgfile.CFG_ReadCvars(read_vars)
        cfgfile.CFG_CloseConfig()

    cfgfile.CFG_ReadCvarOverrides(read_vars)

    VID_InitModelist()
    

    
    



def VID_IsMinimized():
    global window
    return sdl2.video.SDL_GetWindowFlags(window.sdlwindow) & sdl2.SDL_WINDOW_SHOWN

def VID_HasMouseOrInputFocus():
    global window
    flags = sdl2.video.SDL_GetWindowFlags(window.sdlwindow)

    if flags & sdl2.SDL_WINDOW_INPUT_FOCUS or flags & sdl2.SDL_WINDOW_MOUSE_FOCUS:
        return True
    
    return False