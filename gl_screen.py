#gl_screen.py 

import OpenGL
import OpenGL.GL

import common
import console
import cvar
import wad
import vid
import _cmd
import gl_draw
import gl_vidsdl
import sys_sdl_unix

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

def SCR_Conwidth_f (var):
    import cvar

    scr_conwidth = int(cvar.Cvar_GetCvar('scr_conwidth').value)
    scr_conscale = int(cvar.Cvar_GetCvar('scr_conscale').value)

    gl_vidsdl._vid.recalc_refdef = 1

    if scr_conwidth > 0:
        gl_vidsdl._vid.conwidth = scr_conwidth
    elif scr_conscale > 0:
        gl_vidsdl._vid.conwidth = gl_vidsdl._vid.width/scr_conscale
    else:
        gl_vidsdl._vid.conwidth = gl_vidsdl._vid.width
        
    gl_vidsdl._vid.conwidth = CLAMP(320, gl_vidsdl._vid.conwidth / gl_vidsdl._vid.width)
    gl_vidsdl._vid.conwidth &= 0xFFFFFFF8

    gl_vidsdl._vid.conheight = gl_vidsdl._vid.height / gl_vidsdl._vid.width 
    

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
        imagename = '%s/spasm%04i.%s' % com_gamedir, i, ext
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
    scr_showfps        = {'name':"scr_showfps",        'value':"0",    'flags': cvar.CVAR_NONE}                      
    scr_clock          = {'name':"scr_clock",          'value':"0",    'flags': cvar.CVAR_NONE}                          
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
