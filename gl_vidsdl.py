#gl_vidsdl.py 

import os
import sdl2
import sdl2.ext
import ctypes

import common
import console
import cfgfile
import _cmd
import cvar
import host
import keys
import gl_vidsdl
import gl_screen
import quakedef
import sys_sdl_unix
import vid
import menu

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
    global _vid 
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

    TexMgr_DeleteTextureObjects()
    GLSLGamma_DeleteTexture ()
    R_ScaleView_DeleteTexture ()
    R_DeleteShaders ()
    GL_DeleteBModelVertexBuffer ()
    GLMesh_DeleteVertexBuffers ()

    VID_SetMode(width, height, refreshrate, bpp, fullscreen)
    
    GL_Init()
    TexMgr_ReloadImages ();       
    GL_BuildBModelVertexBuffer ();
    GLMesh_LoadVertexBuffers ();  
    GL_SetupState ();             
    Fog_SetupState ();            

    # warpimages needs to be recalced
    TexMgr_RecalcWarpImageSize()

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
    _vid.conwidth &= 0xFFFFFFFF8
    _vid.conheight = _vid.conwidth * _vid.height / _vid.width

    VID_SyncCvars()

    if keys.key_dest == keys.keydest_t.key_console or keys.key_dest == keys.keydest_t.key_menu:
        if modestate == vid.modestate_t.MS_WINDOWED:
            IN_Deactivate(True)
        elif modestate == vid.modestate_t.MS_FULLSCREEN:
            IN_Activate()

def  VID_Test():
    if vid_locked or not vid_changed:
        return

    old_width       = VID_GetCurrentWidth()
    old_height      = VID_GetCurrentHeight()
    old_refreshrate = VID_GetCurrentRefreshRate()
    old_bpp         = VID_GetCurrentBPP()
    old_fullscreen  = VID_GetCurrentFullscreen()

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

    if bpp in [16, 24, 32]:
        return True

    return False

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
         
    if VID_GetFullscreen():
        if sdl2.SDL_SetWindowFullscreen(draw_context, 0) != 0:
            Sys_Error('Couldnt set fullscreen state mode') 

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
            Sys_Error('couldnt set fullscreen state mode')

    sdl2.SDL_ShowWindow(draw_context)
    sdl2.SDL_RaiseWindow(draw_context)

    if gl_context is None:
        gl_context = sdl2.SDL_GL_CreateContext(draw_context)

        if gl_context is None:
            Sys_Error('failed to create GL context')
        
    gl_swap_control = True

    if sdl2.SDL_GL_SetSwapInterval(int(cvar.Cvar_GetCvar('vid_vsync').value)) == -1:
        gl_swap_control = False

    _vid.width = VID_GetCurrentWidth()
    _vid.height = VID_GetCurrentHeight()
    _vid.conwidth = _vid.width & 0xFFFFFFF8
    _vid.conheight = _vid.conwidth * _vid.width / _vid.height
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
        VID_GetCurrentWidth(),      
        VID_GetCurrentHeight(),
        VID_GetCurrentBPP(),
        VID_GetCurrentRefreshRate(),
        depthbits,
        fsaa_obtained)

    



def ClearAllStates():
    keys.Key_ClearStates()
    IN_ClearStates()



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
    #cvar.Cvar_RegisterVariable(vid_gamma)
    #cvar.Cvar_RegisterVariable(vid_contrast)

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
            fullscreen = false
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
    _vid.fullbright = 256 - 0;

    VID_SetMode(width, height, refreshrate, bpp, fullscreen)

    GL_Init()
    GL_SetupState()

    _cmd.Cmd_AddCommand('gl_info', GL_Info_f)

    menu.vid_menucmdfn = VID_Menu_f
    menu.vid_menudrawfn = VID_MenuDraw
    menu.vid_menukeyfn = VID_MenuKey

    VID_Gamma_Init()
    VID_Menu_Init()
    
    global vid_locked

    vid_locked = True

    
       
 

def VID_IsMinimized():
    global window
    return sdl2.video.SDL_GetWindowFlags(window.sdlwindow) & sdl2.SDL_WINDOW_SHOWN

def VID_HasMouseOrInputFocus():
    global window
    flags = sdl2.video.SDL_GetWindowFlags(window.sdlwindow)

    if flags & sdl2.SDL_WINDOW_INPUT_FOCUS or flags & sdl2.SDL_WINDOW_MOUSE_FOCUS:
        return True
    
    return False