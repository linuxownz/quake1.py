#host.py
import os
import sys
import ctypes

import chase
import client
import cl_main
import _cmd
import common
import console
import cvar
import gl_draw
import gl_model
import gl_texmgr
import gl_vidsdl
import gl_rmisc
import gl_screen
import host_cmd
import host
import in_sdl
import keys
import menu
import net_main
import net_main
import pr_edict
import quakedef
import snd_dma
import sv_main
import sys_sdl_unix
import view
import wad
import zone

host_initialized = False
host_frametime = 0.0
realtime = 0.0
oldrealtime = 0.0

host_framecount = 0

host_client : client_t = None

host_colormap : bytes = b''

parms : quakedef.quakeparms_t = quakedef.quakeparms_t()
parms.basedir = os.getcwd()
parms.userdir = os.getcwd()
parms.argc = len(sys.argv)
parms.argv = sys.argv

DEFAULT_MEMORY = ( 256 * 1024 * 1024 )

membase = None
memsize = DEFAULT_MEMORY

def Max_Fps_f(cvar:cvar_t):
    if cvar.value > 72:
        console.Con_Warning('host_maxfps > 72 breaks physics')

def Max_Edicts_f(cvar:cvar_t):
    if cl_main.cls.state == ca_connected or sv.active:
        console.Con_Printf('Changes to max_edicts will not take effect until next time map is loaded')

def Host_FindMaxClients():
    sv_main.svs.maxclients = 1

    i = common.COM_CheckParm('-dedicated')
    if i:
        cl_main.cls.state = client.cactive_t.ca_dedicated
        if i != (com_argc - 1):
            sv_main.svs.maxclients = int(com_argv[i+1])
        else:
            sv_main.svs.maxclients = 8
    else:
        cl_main.cls.state = client.cactive_t.ca_disconnected

    i = common.COM_CheckParm('-listen')
    if i:
        if cl_main.cls.state == client.cactive_t.ca_dedicated:
            Sys_Error('only one of -dedicated or -listen may be specified')
        if i != (com_argc - 1):
            sv_main.svs.maxclients = int(com_argv[i+1])
        else:
            sv_main.svs.maxclients = 8

    if sv_main.svs.maxclients < 1:
        sv_main.svs.maxclients = 8
    elif sv_main.svs.maxclients > quakedef.MAX_SCOREBOARD:
        sv_main.svs.maxclients = quakedef.MAX_SCOREBOARD

    sv_main.svs.maxclientslimit = sv_main.svs.maxclients
    if sv_main.svs.maxclientslimit < 4:
        sv_main.svs.maxclientslimit = 4

    sv_main.svs.clients = [] # change to numpy.array and set hard max limit?

    if sv_main.svs.maxclients > 1:
        cvar.Cvar_SetQuickByName('deathmatch', "1")
    else:
        cvar.Cvar_SetQuickByName('deathmatch', "0")

def Host_Callback_Notify(cvar):
    if sv.active:
        SV_BroadcastPrintf(f"{var['name']} changed to {var['string']}")

def Host_InitLocal():
    _cmd.Cmd_AddCommand('version', '1.0')

    host_cmd.Host_InitCommands()


    host_framerate = {'name':'host_framerate', 'value': '0',   'flags': cvar.CVAR_NONE}
    host_speeds    = {'name':'host_speeds',    'value': '0',   'flags': cvar.CVAR_NONE}
    host_maxfps    = {'name':'host_maxfps',    'value':'72',   'flags': cvar.CVAR_ARCHIVE}
    host_timescale = {'name':'host_timescale', 'value': '0',   'flags': cvar.CVAR_NONE}
    max_edicts     = {'name':'max_edicts',     'value':'8192', 'flags': cvar.CVAR_NONE}
    sys_ticrate    = {'name':'sys_ticrate',    'value':'0.05', 'flags': cvar.CVAR_NONE}
    serverprofile  = {'name':'serverprofile',  'value': '0',   'flags': cvar.CVAR_NONE}
    fraglimit      = {'name':'fraglimit',      'value': '0',   'flags': cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
    timelimit      = {'name':'timelimit',      'value': '0',   'flags': cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
    teamplay       = {'name':'teamplay',       'value': '0',   'flags': cvar.CVAR_NOTIFY |cvar.CVAR_SERVERINFO}
    samelevel      = {'name':'samelevel',      'value': '0',   'flags': cvar.CVAR_NONE}
    noexit         = {'name':'noexit',         'value': '0',   'flags': cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
    skill          = {'name':'skill',          'value': '1',   'flags': cvar.CVAR_NONE}
    deathmatch     = {'name':'deathmatch',     'value': '0',   'flags': cvar.CVAR_NONE}
    coop           = {'name':'coop',           'value': '0',   'flags': cvar.CVAR_NONE}
    pausable       = {'name':'pausable',       'value': '1',   'flags': cvar.CVAR_NONE}
    developer      = {'name':'developer',      'value': '0',   'flags': cvar.CVAR_NONE}
    temp1          = {'name':'temp1',          'value': '0',   'flags': cvar.CVAR_NONE}
    devstats       = {'name':'devstats',       'value': '0',   'flags': cvar.CVAR_NONE}
    campaign       = {'name':'campaign',       'value': '0',   'flags': cvar.CVAR_NONE}
    horde          = {'name':'horde',          'value': '0',   'flags': cvar.CVAR_NONE}
    sv_cheats      = {'name':'sv_cheats',      'value': '0',   'flags': cvar.CVAR_NONE}

    sys_throttle = {'name':'sys_throttle', 'value':'0.02', 'flags':cvar.CVAR_ARCHIVE}

    cvar.Cvar_RegisterVariable(host_framerate)
    cvar.Cvar_RegisterVariable(host_speeds)

    cvar.Cvar_RegisterVariable(host_maxfps)
    cvar.Cvar_SetCallback(host_maxfps, Max_Fps_f)

    cvar.Cvar_RegisterVariable(host_timescale)

    cvar.Cvar_RegisterVariable(max_edicts)
    cvar.Cvar_SetCallback(max_edicts, Max_Edicts_f)

    cvar.Cvar_RegisterVariable(devstats)
    cvar.Cvar_RegisterVariable(sys_ticrate)

    cvar.Cvar_RegisterVariable(sys_throttle)
    cvar.Cvar_RegisterVariable(serverprofile)

    cvar.Cvar_RegisterVariable(fraglimit)
    cvar.Cvar_RegisterVariable(timelimit)
    cvar.Cvar_RegisterVariable(teamplay)
    cvar.Cvar_SetCallback(fraglimit, Host_Callback_Notify)
    cvar.Cvar_SetCallback(timelimit, Host_Callback_Notify)
    cvar.Cvar_SetCallback(teamplay,  Host_Callback_Notify)

    cvar.Cvar_RegisterVariable(samelevel)

    cvar.Cvar_RegisterVariable(noexit)
    cvar.Cvar_SetCallback(noexit,  Host_Callback_Notify)

    cvar.Cvar_RegisterVariable(skill)
    cvar.Cvar_RegisterVariable(developer)
    cvar.Cvar_RegisterVariable(coop)
    cvar.Cvar_RegisterVariable(deathmatch)

    cvar.Cvar_RegisterVariable(campaign)
    cvar.Cvar_RegisterVariable(horde)
    cvar.Cvar_RegisterVariable(sv_cheats)

    cvar.Cvar_RegisterVariable(pausable)
    cvar.Cvar_RegisterVariable(temp1)

    Host_FindMaxClients()


def Host_Init():
    zone.Memory_Init(membase, memsize)

    _cmd.Cbuf_Init()
    _cmd.Cmd_Init()

    console.LOG_Init()

    cvar.Cvar_Init()

    common.COM_Init()
    common.COM_InitFilesytem()

    Host_InitLocal()

    wad.W_LoadWadFile("gfx.wad")

    if cl_main.cls.state != client.cactive_t.ca_dedicated:
        keys.Key_Init()
        console.Con_Init()

    pr_edict.PR_Init()
    gl_model.Mod_Init()
    net_main.NET_Init()
    sv_main.SV_Init()

    global host_colormap
    if cl_main.cls.state != client.cactive_t.ca_dedicated:
        host_colormap = common.COM_LoadHunkFile('gfx/colormap.lmp')
        if host_colormap is None:
            Sys_Error('couldnt load gfx/colormap.lmp')

        view.V_Init()
        chase.Chase_Init()
        menu.M_Init()
        host_cmd.ExtraMaps_Init()
        host_cmd.ModList_Init()
        host_cmd.DemoList_Init()
        gl_vidsdl.VID_Init()
        in_sdl.IN_Init()
        gl_texmgr.TexMgr_Init()
        gl_draw.Draw_Init()
        gl_screen.SCR_Init()
        gl_rmisc.R_Init()
        #snd_dma.S_Init()
        #Sbar_Init()
        cl_main.CL_Init()

    global host_initialized
    host_initialized = True
    console.Con_Printf('\n============Quake Initialized===============\n')

    if cl_main.cls.state != cl_main.cactive_t.ca_dedicated:
        _cmd.Cbuf_InsertText('exec quake.rc\n')
        #_cmd.Cbuf_AddText('\n\nvid_lock\n')

    if cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        _cmd.Cbuf_AddText ("exec autoexec.cfg\n")
        _cmd.Cbuf_AddText ("stuffcmds")
        _cmd.Cbuf_Execute ()
        if not sv_main.sv.active:
            _cmd.Cbuf_AddText ("map start\n")



    keys.key_dest = keys.keydest_t.key_console
    #raise NotImplementedError


def SV_ClientPrintf(msg):
    raise NotImplementedError

def Host_FilterTime(time):
    global realtime, oldrealtime, host_frametime # Required to modify these

    host_maxfps = cvar.Cvar_GetCvar('host_maxfps')
    host_timescale = cvar.Cvar_GetCvar('host_timescale')
    host_framerate = cvar.Cvar_GetCvar('host_framerate')

    realtime += time

    # Use the value attribute of the cvar object
    maxfps_val = common.CLAMP(10.0, float(host_maxfps.value), 1000.0)

    # Note: Ensure cl_main.cls is accessible
    if not cl_main.cls.timedemo and (realtime - oldrealtime) < (1.0 / maxfps_val):
        return False

    host_frametime = realtime - oldrealtime
    oldrealtime = realtime

    if float(host_timescale.value) > 0:
        host_frametime *= float(host_timescale.value)
    elif float(host_framerate.value) > 0:
        host_frametime = float(host_framerate.value)
    else:
        host_frametime = common.CLAMP(0.001, host_frametime, 0.1)

    return True


time1 = 0
time2 = 0
time3 = 0

def _Host_Frame(time):
    # Declare globals so we can modify variables defined at the top of the file
    global host_framecount, time1, time2, time3
    import random

    random.random()

    if not Host_FilterTime(time):
        return


    console.Con_CheckResize()

    # --- Input and Commands (Uncomment these as you implement the modules) ---
    # keys.Key_UpdateForDest()
    in_sdl.IN_SendKeyEvents() #sys_sdl_unix.Sys_SendKeyEvents()
    _cmd.Cbuf_Execute()
    # net_main.NET_Poll()

    if sv_main.sv.active:
        cl_main.CL_SendCmd()

    # --- Server Operations ---
    if sv_main.sv.active:
        sv_main.Host_ServerFrame() # Added sv_main prefix

    # --- Client Operations ---
    if not sv_main.sv.active:
        pass # cl_main.CL_SendCmd()

    if cl_main.cls.state == cl_main.cactive_t.ca_connected:
        pass # cl_main.CL_ReadFromServer()

    # --- Video/Rendering ---
    host_speeds = cvar.Cvar_GetCvar('host_speeds')
    if int(host_speeds.value):
        time1 = sys_sdl_unix.Sys_DoubleTime()

    gl_screen.SCR_UpdateScreen()

    # cl_main.CL_RunParticles() # Added prefix

    if int(host_speeds.value):
        time2 = sys_sdl_unix.Sys_DoubleTime()
        # Note: Logic for pass1/pass2/pass3 goes here if needed

    # --- Sound (Disabled) ---
    # S_Update calls should stay commented out for now

    host_framecount += 1


def Host_Frame(time):
    serverprofile = int(cvar.Cvar_GetCvar('serverprofile').value)

    if not serverprofile:
        _Host_Frame(time)
        return

    time1 = Sys_DoubleTime ()
    _Host_Frame (time)
    time2 = Sys_DoubleTime ()

    timetotal += time2 - time1
    timecount += 1

    if timecount < 1000:
        return

    m = timetotal*1000/timecount
    timecount = 0
    timetotal = 0
    c = 0
    for i in range(svs.maxclients):
        if sv_main.svs.clients[i].active:
            c += 1

    console.Con_Printf ("serverprofile: %2i clients %2i msec\n" % ( c,  m ) )


isdown = False
def Host_Shutdown():
    global isdown

    if isdown:
        console.Con_Printf('recursive shutdown')
        return

    isdown = True

    gl_screen.scr_disabled_for_loading = True

    Host_WriteConfiguration()

    #net_main.NET_Shutdown()

    if cl_main.cls.state != client.cactive_t.ca_dedicated:
        if console.con_initialized:
            #History_Shutdown()
            pass
        #S_Shutdown()
        in_sdl.IN_Shutdown()
        gl_vidsdl.VID_Shutdown()

    console.LOG_Close()

def Host_WriteConfiguration():
    try:
        # Save to the current game directory (e.g., id1/config.cfg)
        config_path = os.path.join(common.com_gamedir, "config.cfg")

        archived_cvars = []
        with open(config_path, "w") as f:
            f.write("// Generated by quake\n")
            f.write("unbindall\n")

            # 1. Save Key Bindings
            keys.WriteBindings(f)

            # 2. Save Archivable Cvars
            import cvar
            for v in cvar.__cvars:
                if v.flags & cvar.CVAR_ARCHIVE:
                    archived_cvars.append(v)

            archived_cvars.sort(key = lambda x: x.name)

            for var in archived_cvars:
                f.write(f'{var.name} "{var.string}"\n')

            print(f"Config saved to {config_path}")
    except Exception as e:
        console.Con_Printf(f"ERROR: Could not save config: {e}\n")

inerror = False
def Host_Error(error):
    global inerror
    if inerror:
        sys_sdl_unix.Sys_Error('Host_Error: recursively entered')
    inerror = True

    gl_screen.SCR_EndLoadingPlaque()

    console.Con_Printf('Host_Error: %s\n' % error)

    if sv_main.sv.active:
        host.Host_ShutdownServer(False)

    if cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        sys_sdl_unix.Sys_Error('Host_Error: %s\n' % error)

    cl_main.CL_Disconnect()
    cl_main.cls.demonum = -1
    cl_main.cl.intermission = 0

    inerror = False