#gl_screen.py 

import wad
import vid
import _cmd

glx = 0
gly = 0
glwidth = 0
glheight = 0

scr_con_current = 0.0
scr_conlines = 0.0

scr_initialized = False

scr_net : wad.qpic_t = None
scr_turtel : wad.qpic_t = None

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
    cvar.Cvar_SetCallback (scr_sbaralpha, SCR_Callback_refdef)
    cvar.Cvar_RegisterVariable (scr_sbaralpha)
    cvar.Cvar_SetCallback (scr_conwidth, SCR_Conwidth_f)
    cvar.Cvar_SetCallback (scr_conscale, SCR_Conwidth_f)
    cvar.Cvar_RegisterVariable (scr_conwidth)
    cvar.Cvar_RegisterVariable (scr_conscale)
    cvar.Cvar_RegisterVariable (scr_crosshairscale)
    cvar.Cvar_RegisterVariable (scr_showfps)
    cvar.Cvar_RegisterVariable (scr_clock)
    cvar.Cvar_RegisterVariable (scr_usekfont) 
    cvar.Cvar_SetCallback (scr_fov, SCR_Callback_refdef)
    cvar.Cvar_SetCallback (scr_fov_adapt, SCR_Callback_refdef)
    cvar.Cvar_SetCallback (scr_viewsize, SCR_Callback_refdef)
    cvar.Cvar_RegisterVariable (scr_fov)
    cvar.Cvar_RegisterVariable (scr_fov_adapt)
    cvar.Cvar_RegisterVariable (scr_viewsize)
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
