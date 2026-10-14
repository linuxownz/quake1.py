#gl_screen.py

import math

import OpenGL
import OpenGL.GL as gl

import _cmd
import cl_main
import common
import console
import cvar
import gl_draw
import gl_rmain
import gl_vidsdl
import host
#import image
import keys
import menu
import quakedef
import sbar
import snd_dma
import sys_sdl_unix
import view
import vid
import wad

glx = 0
gly = 0
glwidth = 0
glheight = 0

scr_con_current = 0.0
scr_conlines = 0.0

scr_initialized = False

scr_net : wad.qpic_t = None
scr_turtle : wad.qpic_t = None

clearconsole = 0
clearnotify = 0

scr_vrect : vid.vrect_t = vid.vrect_t()

scr_disabled_for_loading = False
scr_drawloading = False
scr_disabled_time = 0.0

scr_tileclear_updates = 0

scr_centerstring = ''
scr_centertime_start = 0.0
scr_centertime_off = 0.0
scr_center_lines = 0
scr_erase_lines = 0
scr_erase_center = 0

scr_notifystring = ''
scr_drawdialog = False


def SCR_CenterPrint(string: str):
    global scr_centerstring, scr_centertime_off, scr_centertime_start, scr_center_lines

    scr_centerstring = string
    scr_centertime_off = cvar.Cvar_GetCvar('scr_centertime').value
    scr_centertime_start = cl_main.cl.time

    scr_center_lines = 1
    string = scr_centerstring
    for s in string:
        if s == '\n':
            scr_center_lines += 1


def SCR_DrawCenterString():
    global scr_erase_center

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)

    scr_printspeed = cvar.Cvar_GetCvar("scr_printspeed").value
    crosshair = cvar.Cvar_GetCvar("crosshair").value

    if cl_main.cl.intermission:
        remaining = int(
            scr_printspeed * (cl_main.cl.time - scr_centertime_start)
        )
    else:
        remaining = 9999

    scr_erase_center = 0
    start = scr_centerstring

    if scr_center_lines <= 4:
        y = int(200 * 0.35)
    else:
        y = 48

    if crosshair:
        y -= 8

    start_idx = 0
    length = len(start)

    while True:
        # Scan the width of the line (up to 40 characters)
        l = 0
        while l < 40:
            pos = start_idx + l
            if pos >= length or start[pos] == "\n" or start[pos] == "\0":
                break
            l += 1

        x = (320 - l * 8) // 2  # johnfitz -- 320x200 screen space

        for j in range(l):
            gl_draw.Draw_Character(x, y, ord(start[start_idx + j]))
            x += 8

            if remaining == 0:
                return
            remaining -= 1

        y += 8

        # Advance start pointer to end of current line
        while start_idx < length and start[start_idx] != "\n":
            if start[start_idx] == "\0":
                break
            start_idx += 1

        if start_idx >= length or start[start_idx] == "\0":
            break

        start_idx += 1


def SCR_CheckDrawCenterString():
    global scr_erase_lines, scr_centertime_off
    if scr_center_lines > scr_erase_lines:
        scr_erase_lines = scr_center_lines

    scr_centertime_off -= host.host_frametime

    if scr_centertime_off <= 0 and not cl_main.cl.intermission:
        return
    if keys.key_dest != keys.keydest_t.key_game:
        return
    if cl_main.cl.paused:
        return

    SCR_DrawCenterString()




def SCR_Conwidth_f(var):
    import common  # Assuming CLAMP is in common
    import cvar

    # 1. Pull the raw values
    scr_conwidth = cvar.Cvar_GetCvar('scr_conwidth').value
    scr_conscale = cvar.Cvar_GetCvar('scr_conscale').value

    vid = gl_vidsdl._vid
    vid.recalc_refdef = 1

    # 2. Determine base virtual width
    if scr_conwidth > 0:
        target_width = scr_conwidth
    elif scr_conscale > 0:
        target_width = vid.width / scr_conscale
    else:
        target_width = vid.width

    # 3. Apply CLAMP(minval, val, maxval)
    # We clamp between 320 and the actual physical window width
    vid.conwidth = common.CLAMP(320, target_width, vid.width)

    # 4. Integer alignment (Required for Quake's character grid)
    vid.conwidth = int(vid.conwidth) & 0xFFFFFFF8

    # 5. Calculate virtual height based on the new virtual width aspect ratio
    # Formula: (Physical Height / Physical Width) * Virtual Width
    vid.conheight = int((vid.height / vid.width) * vid.conwidth)


def SCR_Callback_refdef(var):
    gl_vidsdl._vid.recalc_refdef = 1

def SCR_ScreenShot_f():
    global glx, gly, glwidth, glheight
    ext = 'png'

    cmd_argc = _cmd.Cmd_Argc()

    if cmd_argc >= 2:
        requested_ext = _cmd.Cmd_Argv(1)

        if requested_ext not in ['png', 'tga', 'jpg']:
            SCR_ScreenShot_Usage()
            return

    quality = 90
    if cmd_argc >= 3:
        quality = int(_cmd.Cmd_Argv(2))

    if quality < 1 or quality > 100:
        SCR_ScreenShot_Usage()
        return

    for i in range(100):
        imagename = '%s/spasm%04i.%s' % common.com_gamedir, i, ext
        if sys_sdl_unix.Sys_FileType(imagename) == common.FS_ENT_NONE:
            break

    if i == 100:
        console.Con_Printf('SCR_ScreenShot_f: Couldnt find unused filename')
        return

    OpenGL.GL.glPixelStorei(OpenGL.GL.GL_PACK_ALIGNMENT, 1)
    buffer = OpenGL.GL.glReadnPixels(glx, gly, glwidth, glheight, OpenGL.GL.GL_RGB, OpenGL.GL.GL_UNSIGNED_BYTE)

    ok = False
    if ext == 'png':
        ok = Image_WritePNG(imagename, buffer, glwidth, glheight, 24, False)
    elif ext == 'tga':
        ok = Image_WriteTGA(imagename, buffer, glwidth, glheight, 24, False)
    elif ext == 'jpg':
        ok = Image_WriteJPG(imagename, buffer, glwidth, glheight, 24, quality, False)

    if ok:
        console.Con_Printf('wrote %s' % imagename)
    else:
        console.Con_Printf('could not write %s' % imagename)


def SCR_SizeUp_f():
    scr_viewsize = cvar.Cvar_GetCvar('scr_viewsize')
    cvar.Cvar_SetValueQuick('scr_viewsize', int(scr_viewsize.value) + 10)

def SCR_SizeDown_f():
    scr_viewsize = cvar.Cvar_GetCvar('scr_viewsize')
    cvar.Cvar_SetValueQuick('scr_viewsize', int(scr_viewsize.value) - 10)


def SCR_Callback_refdef(var: cvar.cvar_t):
    gl_vidsdl._vid.recalc_refdef = True



def SCR_LoadPics():
    global scr_net, scr_turtle
    scr_net    = gl_draw.Draw_PicFromWad('net')
    scr_turtle = gl_draw.Draw_PicFromWad('turtle')

def SCR_Init():
    import cvar

    scr_menuscale      = {'name':"scr_menuscale",      'value':"1",    'flags': cvar.CVAR_ARCHIVE}
    scr_sbarscale      = {'name':"scr_sbarscale",      'value':"1",    'flags': cvar.CVAR_ARCHIVE}
    scr_sbaralpha      = {'name':"scr_sbaralpha",      'value':"0.75", 'flags': cvar.CVAR_ARCHIVE}
    scr_conwidth       = {'name':"scr_conwidth",       'value':"0",    'flags': cvar.CVAR_ARCHIVE}
    scr_conscale       = {'name':"scr_conscale",       'value':"1",    'flags': cvar.CVAR_ARCHIVE}
    scr_crosshairscale = {'name':"scr_crosshairscale", 'value':"1",    'flags': cvar.CVAR_ARCHIVE}
    scr_showfps        = {'name':"scr_showfps",        'value':"1",    'flags': cvar.CVAR_NONE}
    scr_clock          = {'name':"scr_clock",          'value':"1",    'flags': cvar.CVAR_NONE}
    scr_usekfont       = {'name':"scr_usekfont",       'value':"0",    'flags': cvar.CVAR_NONE}
    scr_viewsize       = {'name':"viewsize",           'value':"100",  'flags': cvar.CVAR_ARCHIVE}
    scr_fov            = {'name':"fov",                'value':"90",   'flags': cvar.CVAR_NONE}
    scr_fov_adapt      = {'name':"fov_adapt",          'value':"1",    'flags': cvar.CVAR_ARCHIVE}
    scr_conspeed       = {'name':"scr_conspeed",       'value':"500",  'flags': cvar.CVAR_ARCHIVE}
    scr_centertime     = {'name':"scr_centertime",     'value':"2",    'flags': cvar.CVAR_NONE}
    scr_showturtle     = {'name':"showturtle",         'value':"0",    'flags': cvar.CVAR_NONE}
    scr_showpause      = {'name':"showpause",          'value':"1",    'flags': cvar.CVAR_NONE}
    scr_printspeed     = {'name':"scr_printspeed",     'value':"8",    'flags': cvar.CVAR_NONE}
    gl_triplebuffer    = {'name':"gl_triplebuffer",    'value':"1",    'flags': cvar.CVAR_ARCHIVE}
    cl_gun_fovscale    = {'name':"cl_gun_fovscale",    'value':"1",    'flags': cvar.CVAR_ARCHIVE}

    cvar.Cvar_RegisterVariable (scr_menuscale)
    cvar.Cvar_RegisterVariable (scr_sbarscale)

    cvar.Cvar_RegisterVariable (scr_sbaralpha)
    cvar.Cvar_RegisterVariable (scr_conwidth)
    cvar.Cvar_RegisterVariable (scr_conscale)

    cvar.Cvar_SetCallback (scr_sbaralpha, SCR_Callback_refdef)
    cvar.Cvar_SetCallback (scr_conwidth, SCR_Conwidth_f)
    cvar.Cvar_SetCallback (scr_conscale, SCR_Conwidth_f)

    cvar.Cvar_RegisterVariable (scr_crosshairscale)
    cvar.Cvar_RegisterVariable (scr_showfps)
    cvar.Cvar_RegisterVariable (scr_clock)
    cvar.Cvar_RegisterVariable (scr_usekfont)

    cvar.Cvar_RegisterVariable (scr_fov)
    cvar.Cvar_RegisterVariable (scr_fov_adapt)
    cvar.Cvar_RegisterVariable (scr_viewsize)

    cvar.Cvar_SetCallback (scr_fov, SCR_Callback_refdef)
    cvar.Cvar_SetCallback (scr_fov_adapt, SCR_Callback_refdef)
    cvar.Cvar_SetCallback (scr_viewsize, SCR_Callback_refdef)

    cvar.Cvar_RegisterVariable (scr_conspeed)
    cvar.Cvar_RegisterVariable (scr_showturtle)
    cvar.Cvar_RegisterVariable (scr_showpause)
    cvar.Cvar_RegisterVariable (scr_centertime)
    cvar.Cvar_RegisterVariable (scr_printspeed)
    cvar.Cvar_RegisterVariable (gl_triplebuffer)
    cvar.Cvar_RegisterVariable (cl_gun_fovscale)

    _cmd.Cmd_AddCommand('screenshot', SCR_ScreenShot_f)
    _cmd.Cmd_AddCommand('sizeup', SCR_SizeUp_f)
    _cmd.Cmd_AddCommand('sizedown', SCR_SizeDown_f)

    SCR_LoadPics()

    global scr_initialized
    scr_initialized = True


oldtime = 0
lastfps = 0
oldframecount = 0
elapsed_time = 0.0
frames = 0

def SCR_DrawFPS():
    global oldtime, lastfps, oldframecount, elapsed_time, frames

    elapsed_time = host.realtime - oldtime
    frames = gl_rmain.r_framecount - oldframecount

    if elapsed_time < 0 or frames < 0:
        oldtime = host.realtime
        oldframecount = gl_rmain.r_framecount
        return

    if elapsed_time > 0.75:
        lastfps = frames / elapsed_time
        oldtime = host.realtime
        oldframecount = gl_rmain.r_framecount

    if cvar.Cvar_GetCvar('scr_showfps').value:
        st = f'{lastfps:4.0f} fps'
        x = 320 - len(st) * 8
        y = 200 - 8

        if cvar.Cvar_GetCvar('scr_clock').value:
            y -= 8

        gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_BOTTOMRIGHT)
        gl_draw.Draw_String(x, y, st)
        global scr_tileclear_updates
        scr_tileclear_updates = 0

def SCR_DrawClock():
    if cvar.Cvar_GetCvar('scr_clock').value == 1:
        minutes = cl_main.cl.time // 60
        seconds = int(cl_main.cl.time) % 60

        string = f'{minutes}:{seconds}'
    else:
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_BOTTOMRIGHT)
    gl_draw.Draw_String(320 - (len(string)<<3), 200 - 8, string)

    global scr_tileclear_updates
    scr_tileclear_updates = 0


def SCR_DrawDevStats():

    if not cvar.Cvar_GetCvar('devstats').value:
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_BOTTOMLEFT)

    gl_draw.Draw_Fill(x, y * 8, 19 * 8, 9 * 8, 0, 0.5)

    gl_draw.Draw_String(x, y * 8 - x,  'devstats |Curr Peak' ); y += 1
    gl_draw.Draw_String(x, y * 8 - x,  '---------+---------' ); y += 1
    gl_draw.Draw_String(x, y * 8 - x, f'Edicts   |{host.dev_stats.edicts:04}{host.dev_peakstats.edicts:04}'); y += 1
    gl_draw.Draw_String(x, y * 8 - x, f'Packet   |{host.dev_stats.packetsize:04}{host.dev_peakstats.packetsize:04}'); y += 1
    gl_draw.Draw_String(x, y * 8 - x, f'Visedicts|{host.dev_stats.videdicts:04}{host.dev_peakstats.videdicts:04}'); y += 1
    gl_draw.Draw_String(x, y * 8 - x, f'Efrags   |{host.dev_stats.efrags:04}{host.dev_peakstats.efrags:04}'); y += 1
    gl_draw.Draw_String(x, y * 8 - x, f'Dlights  |{host.dev_stats.dlights:04}{host.dev_peakstats.dlights:04}'); y += 1
    gl_draw.Draw_String(x, y * 8 - x, f'Beams    |{host.dev_stats.beams:04}{host.dev_peakstats.beams:04}'); y += 1
    gl_draw.Draw_String(x, y * 8 - x, f'Tempents |{host.dev_stats.tempents:04}{host.dev_peakstats.tempents:04}'); y += 1


count = 0
def SCR_DrawTurtle():
    global count
    if not cvar.Cvar_GetCvar('showturtle').value:
        return

    if host.host_frametime < 0.1:
        count = 0
        return

    count += 1

    if count < 3:
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_DEFAULT)

    gl_draw.Draw_Pic(scr_vrect.x, scr_vrect.y, scr_turtle)

def SCR_DrawNet():
    if host.realtime - cl_main.cl.last_received_message < 0.3:
        return
    if cl_main.cls.demoplayback:
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_DEFAULT)
    gl_draw.Draw_Pic(scr_vrect.x + 64, scr_vrect.y, scr_net)

def SCR_DrawPause():
    if not cl_main.cl.paused:
        return

    if not cvar.Cvar_GetCvar('scr_showpause').value:
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)
    pic: wad.qpic_t = gl_draw.Draw_CachePic('gfx/pause.lmp')
    gl_draw.Draw_Pic((320 - pic.width)/2, (240 - 48 - pic.height)/2, pic)

    global scr_tileclear_updates
    scr_tileclear_updates = 0


def SCR_DrawLoading():
    if not scr_drawloading:
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)
    pic: wad.qpic_t = gl_draw.Draw_CachePic('gfx/loading.lmp')

    gl_draw.Draw_Pic ( (320 - pic.width)/2, (240 - 48 - pic.height)/2, pic)

    global scr_tileclear_updates
    scr_tileclear_updates = 0

def SCR_DrawCrosshairREMOVEME():
    if not cvar.Cvar_GetCvar('crosshair').value:
        return

    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_CROSSHAIR)
    gl_draw.Draw_Character(-4, -4, '+')


def SCR_SetUpToDrawConsole():
    global scr_conlines, scr_con_current

    console.Con_CheckResize()

    if scr_drawloading:
        return

    console.con_forcedup = not cl_main.cl.worldmodel or cl_main.cls.signon != quakedef.SIGNONS

    if console.con_forcedup:
        scr_conlines = glheight
        scr_con_current = scr_conlines
    elif keys.key_dest == keys.keydest_t.key_console:
        scr_conlines = glheight // 2
    else:
        scr_conlines = 0

    host_timescale = cvar.Cvar_GetCvar('host_timescale').value
    scr_conspeed   = cvar.Cvar_GetCvar('scr_conspeed').value

    timescale = host_timescale if host_timescale > 0 else 1
    conspeed  = scr_conspeed if scr_conspeed > 0 else 1e6

    if scr_conlines < scr_con_current:
        scr_con_current -= conspeed * (glheight/600) * host.host_frametime / timescale
        if scr_conlines > scr_con_current:
            scr_con_current = scr_conlines
    elif scr_conlines > scr_con_current:
        scr_con_current += conspeed * (glheight/600) * host.host_frametime/timescale
        if scr_conlines < scr_con_current:
            scr_con_current = scr_conlines

    global clearconsole
    if clearconsole < gl_vidsdl._vid.numpages:
        sbar.Sbar_Changed()

    clearconsole += 1

    global scr_tileclear_updates
    if not console.con_forcedup and scr_con_current:
        scr_tileclear_updates = 0


def SCR_DrawConsole():
    global clearconsole
    if scr_con_current:
        console.Con_DrawConsole(scr_con_current, True)
        clearconsole = 0
    else:
        if keys.key_dest == keys.keydest_t.key_game or keys.key_dest == keys.keydest_t.key_message:
            console.Con_DrawNotify()



def SCR_ScreenShot_Usage():
    string = """usage: screenshot <format> <quality>
    format must be png or tga or jpg
    quality must be 1-100
    """
    console.Con_Printf(string)



def SCR_ScreenShot_f():
    ext = 'png'

    if _cmd.Cmd_Argc() >= 2:
        requested_ext = _cmd.Cmd_Argv(1)

        if requested_ext in ['png', 'tga', 'jpg']:
            ext = requested_ext
        else:
            SCR_ScreenShot_Usage()
            return

    quality = 90

    if _cmd.Cmd_Argc() >= 3:
        quality = int(_cmd.Cmd_Argv(2))

    if quality < 1 or quality > 100:
        SCR_ScreenShot_Usage()
        return

    for i in range(10000):
        imagename = f'spasm{i:04}.{ext}'
        checkname = f'{common.com_gamedir}/{imagename}'

        if sys_sdl_unix.Sys_FileType(checkname) == common.FS_ENT_NONE:
            break

    if i == 10000:
        console.Con_Printf('SCR_ScreenShot_f: couldnt find an unused filename')
        return

    buffer = bytearray(glwidth * glheight * 3)

    gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
    gl.glReadPixels(glx, gly, glwidth, glheight, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, buffer)

    ok = False
    match ext:
        case 'png':
            ok = image.Image_WritePNG (imagename, buffer, glwidth, glheight, 24, False)
        case 'tga':
            ok = image.Image_WriteTGA (imagename, buffer, glwidth, glheight, 24, False)
        case 'jpg':
            ok = image.Image_WriteJPG (imagename, buffer, glwidth, glheight, 24, quality, False)

    if ok:
        console.Con_Printf(f'Write {imagename}')
    else:
        console.Con_Printf(f'SCR_ScreenShot_f: couldnt create {imagename}')



def SCR_BeginLoadingPlaque():
    snd_dma.S_StopAllSounds(True)

    if cl_main.cls.state != quakedef.cactive_t.ca_connected:
        return
    if cl_main.cls.signon != quakedef.SIGNONS:
        return

    console.Con_ClearNotify()
    global scr_centertime_off, scr_con_current, scr_drawloading, scr_disabled_for_loading, scr_disabled_time

    scr_centertime_off = 0
    scr_con_current = 0

    scr_drawloading = True;
    Sbar_Changed ()
    SCR_UpdateScreen ()
    scr_drawloading = False

    scr_disabled_for_loading = True
    scr_disabled_time = host.realtime


def SCR_EndLoadingPlaque():
    global scr_disabled_for_loading
    scr_disabled_for_loading = False
    console.Con_ClearNotify()


def SCR_DrawNotifyString():
    gl_draw.GL_SetCanvas(quakedef.canvastype.CANVAS_MENU)

    start = scr_notifystring

    y = 200 * 0.35

    while True:
        # Scan the width of the line (up to 40 characters)
        l = 0
        while l < 40:
            pos = start_idx + l
            if pos >= length or start[pos] == "\n" or start[pos] == "\0":
                break
            l += 1

        # Calculate centered X position for l characters (8px width per character)
        x = (320 - l * 8) // 2  # johnfitz -- 320x200 virtual screen space

        # Draw character line
        for j in range(l):
            gl_draw.Draw_Character(x, y, ord(start[start_idx + j]))
            x += 8

        y += 8

        # Advance start pointer to end of current line
        while start_idx < length and start[start_idx] != "\n":
            if start[start_idx] == "\0":
                break
            start_idx += 1

        if start_idx >= length or start[start_idx] == "\0":
            break

        start_idx += 1  # Skip the '\n'



def SCR_ModalMessage(text: str, timeout: float) -> bool:
    global scr_notifystring, scr_drawdialog
    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        return True

    scr_notifystring = text

    scr_drawdialog = True
    SCR_UpdateScreen()
    scr_drawdialog = False

    snd_dma.S_ClearBuffer()

    time1 = sys_sdl_unix.Sys_DoubleTime() + timeout
    time2 = 0.0

    keys.key_BeginInputGrab()

    lastkey = 0
    lastchar = 0

    while True:
        sys_sdl_unix.Sys_SendKeyEvents()
        lastkey, lastchar = keys.Key_GetGrabbedInput()
        sys_sdl_unix.Sys_Sleep(16)

        if timeout:
            time2 = sys_env.Sys_DoubleTime()

        # Loop termination condition evaluation
        ch = chr(lastchar) if isinstance(lastchar, int) and 0 <= lastchar < 128 else ""

        if (
            ch in ("y", "Y", "n", "N")
            or lastkey == keys.K_ESCAPE
            or lastkey == keys.K_ABUTTON
            or lastkey == keys.K_BBUTTON
            or time2 > time1
        ):
            break

    keys.Key_EndInputGrab()

    if time2 > time1:
        return False

    return lastchar in 'yY' or lastkey == keys.K_ABUTTON




def SCR_TileClear():
    global scr_tileclear_updates

    gl_clear = cvar.Cvar_GetCvar('gl_clear').value
    vid_gamma = cvar.Cvar_GetCvar('gamma').value

    if scr_tileclear_updates >= gl_vidsdl._vid.numpages and not gl_clear and not (gl_vidsdl.gl_glsl_able and vid_gamma != 1):
        return

    scr_tileclear_updates += 1

    if gl_rmain.r_refdef.vrect.x > 0:
        gl_draw.Draw_TileClear(0, 0, gl_rmain.r_refdef.vrect.x, glheight - sbar.sb_lines)
        gl_draw.Draw_TileClear(gl_rmain.r_refdef.vrect.x + gl_rmain.r_refdef.vrect.width, 0, glwidth - gl_rmain.r_refdef.vrect.x - gl_rmain.r_refdef.vrect.width, glheight - sbar.b_lines)

    if gl_rmain.r_refdef.vrect.y > 0:
        gl_draw.Draw_TileClear (gl_rmain.r_refdef.vrect.x, 0, gl_rmain.r_refdef.vrect.width, gl_rmain.r_refdef.vrect.y)
        gl_draw.Draw_TileClear (gl_rmain.r_refdef.vrect.x, gl_rmain.r_refdef.vrect.y + gl_rmain.r_refdef.vrect.height, gl_rmain.r_refdef.vrect.width, glheight - gl_rmain.r_refdef.vrect.y - gl_rmain.r_refdef.vrect.height - sbar.sb_lines)





















def AdaptFovx(fov_x, width, height):

    if fov_x < 1 or fov_x > 179:
        sys_sdl_unix.Sys_Error("bad fov")

    if not cvar.Cvar_GetCvar('fov_adapt').value:
        return fov_x

    x = height/width

    if x == 0.75:
        return fov_x

    a = math.atan(0.75 / x * math.tan(fov_x / 360 * math.pi))
    a = a * 360 / math.pi

    return a

def CalcFovy(fov_x, width, height):
    if fov_x < 1 or fov_x > 179:
        sys_sdl_unix.Sys_Error("bad fov")

    x = width / math.tan(fov_x / 360 * math.pi)
    a = math.atan(height / x)
    a = a * 360 / math.pi
    return a




def SCR_CalcRefdef():
    global scr_tileclear_updates

    sbar.Sbar_Changed()

    scr_tileclear_updates = 0

    scr_viewsize = cvar.Cvar_GetCvar('viewsize').value

    if scr_viewsize < 30:
        cvar.Cvar_SetQuickByName('viewsize', "30")
    elif scr_viewsize > 120:
        cvar.Cvar_SetQuickByName('viewsize', "120")

    scr_fov = cvar.Cvar_GetCvar('fov').value
    if scr_fov < 10:
        cvar.Cvar_SetQuickByName('fov', "10")
    elif scr_fov > 170:
        cvar.Cvar_SetQuickByName('fov', "170")

    gl_vidsdl._vid.recalc_refdef = 0

    size = cvar.Cvar_GetCvar('viewsize').value
    scale = common.CLAMP(1.0, float(cvar.Cvar_GetCvar('scr_sbarscale').value), glwidth / 320.0)

    if size >= 120 or cl_main.cl.intermission or cvar.Cvar_GetCvar('scr_sbaralpha').value < 1:
        sbar.sb_lines = 0
    elif size >= 110:
        sbar.sb_lines = 24  * scale
    else:
        sbar.sb_lines = 48 * scale

    size = min(size, 100.0) / 100


    gl_rmain.r_refdef.vrect.width = max(glwidth * size, 96.0)
    gl_rmain.r_refdef.vrect.height = min(glheight * size, glheight - sbar.sb_lines)
    gl_rmain.r_refdef.vrect.x = ( glwidth - gl_rmain.r_refdef.vrect.width) / 2
    gl_rmain.r_refdef.vrect.y = ( glheight - sbar.sb_lines - gl_rmain.r_refdef.vrect.height) / 2

    scr_fov = cvar.Cvar_GetCvar('fov').value
    gl_rmain.r_refdef.fov_x = AdaptFovx(scr_fov, gl_vidsdl._vid.width, gl_vidsdl._vid.height);
    gl_rmain.r_refdef.fov_y = CalcFovy (gl_rmain.r_refdef.fov_x, gl_rmain.r_refdef.vrect.width, gl_rmain.r_refdef.vrect.height);

    global scr_vrect
    scr_vrect = gl_rmain.r_refdef.vrect

def SCR_UpdateScreen():
    global scr_disabled_for_loading

    gl_vidsdl._vid.numpages = 3 if cvar.Cvar_GetCvar('gl_triplebuffer').value else 2

    if scr_disabled_for_loading:
        if host.realtime - scr_disabled_time > 60:
            scr_disabled_for_loading = False
            console.Con_Printf('load failed\n')
        else:
            return

    if not scr_initialized or not console.con_initialized:
        return

    gl_vidsdl.GL_BeginRendering()

    if gl_vidsdl._vid.recalc_refdef:
        SCR_CalcRefdef()

    SCR_SetUpToDrawConsole()

    view.V_RenderView()

    gl_draw.GL_Set2D()

    SCR_TileClear()

    if scr_drawdialog:
        if console.con_forcedup:
            gl_draw.Draw_ConsoleBackground()
        else:
            sbar.Sbar_Draw()
        gl_draw.Draw_FadeScreen()

        SCR_DrawNotifyString()
    elif scr_drawloading:
        SCR_DrawLoading()
        sbar.Sbar_Draw()
    elif cl_main.cl.intermission == 1 and keys.key_dest == keys.keydest_t.key_game:
        sbar.Sbar_IntermissionOverlay()
    elif cl_main.cl.intermission == 2 and keys.key_dest == keys.keydest_t.key_game:
        sbar.Sbar_FinaleOverlay()
        SCR_CheckDrawCenterString()
    else:
        SCR_DrawCrosshair ()
        SCR_DrawNet ()
        SCR_DrawTurtle ()
        SCR_DrawPause ()
        SCR_CheckDrawCenterString ()
        sbar.Sbar_Draw ()
        SCR_DrawDevStats ()
        SCR_DrawFPS ()
        SCR_DrawClock ()
        SCR_DrawConsole ()
        menu.M_Draw ();
    view.V_UpdateBlend()

    gl_rmain.GLSLGamma_GammaCorrect()

    gl_vidsdl.GL_EndRendering()


def SCR_UpdateScreen_gemini():
    # 1. Draw the 3D World first
    # This function handles its own clearing (the blue sky) and 3D projection
    gl_rmain.R_RenderView()

    # 2. NOW setup the 2D Viewport/Projection for the overlay
    w = gl_vidsdl._vid.width
    h = gl_vidsdl._vid.height

    gl.glViewport(0, 0, w, h)
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()

    # CHANGE: Use variables instead of 640 and 480
    gl.glOrtho(0, w, h, 0, -10, 10)

    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

    # 3. Global 2D States (Ensure we draw ON TOP of the 3D world)
    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    if keys.key_dest == keys.keydest_t.key_game:
        SCR_DrawCrosshair()

    # 4. Draw the Console last so it covers the world
    console.Con_DrawConsole()

    # 5. Finally, show the result
    gl_vidsdl.VID_SwapBuffers()

# Inside your frame update logic
def SCR_UpdateConsole():
    global con_current
    # If console is opening, increase height until 200
    if console.console_is_open and con_current < 200:
        con_current += 10 # Adjust speed here
    # If console is closing, decrease until 0
    elif not console.console_is_open and con_current > 0:
        con_current -= 10

def Sbar_Changed():
    sbar.sb_updates = 0


def SCR_DrawCrosshair():
    import gl_draw
    import gl_vidsdl

    if gl_draw.pic_crosshair is None:
        return

    # Calculate center
    x = (gl_vidsdl._vid.width // 2) - 4
    y = (gl_vidsdl._vid.height // 2) - 4

    # The Draw_MakePic function uses SRC_INDEXED (Palette colors)
    # Color 8 and 9 in the Quake palette are typically Greys/Whites
    # You can tint it here if you want:
    gl.glColor4f(1.0, 1.0, 1.0, 1.0)

    gl_draw.Draw_Pic(x, y, gl_draw.pic_crosshair)



def SCR_Set2D():
    import OpenGL.GL as gl

    import gl_vidsdl

    # 1. Use the actual window dimensions
    width = gl_vidsdl._vid.width
    height = gl_vidsdl._vid.height

    # 2. Set the Viewport (the actual box on your monitor)
    gl.glViewport(0, 0, width, height)

    # 3. Setup the Projection Matrix for 2D
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()

    # glOrtho(left, right, bottom, top, near, far)
    # This makes 0,0 the top-left and width,height the bottom-right
    gl.glOrtho(0, width, height, 0, -1, 1)

    # 4. Reset the ModelView matrix
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()