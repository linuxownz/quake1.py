#host.py

from main_sdl import parms

import chase
import client
import cl_main
import _cmd
import common
import console
import cvar
import gl_model
import gl_vidsdl
import host_cmd
import keys
import menu
import net_main
import net_main
import pr_edict
import quakedef
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

    cvar.Cvar_RegisterVariable(host_framerate)
    cvar.Cvar_RegisterVariable(host_speeds)

    cvar.Cvar_RegisterVariable(host_maxfps)
    cvar.Cvar_SetCallback(host_maxfps, Max_Fps_f)

    cvar.Cvar_RegisterVariable(host_timescale)

    cvar.Cvar_RegisterVariable(max_edicts)
    cvar.Cvar_SetCallback(max_edicts, Max_Edicts_f)

    cvar.Cvar_RegisterVariable(devstats)
    cvar.Cvar_RegisterVariable(sys_ticrate)

    cvar.Cvar_RegisterVariable(sys_sdl_unix.sys_throttle)
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
    zone.Memory_Init()

    _cmd.Cbuf_Init()
    _cmd.Cmd_Init()

    console.LOG_Init()

    cvar.Cvar_Init()

    common.COM_Init()
    common.COM_InitFilesytem()

    Host_InitLocal()

    wad.W_LoadWadFile()

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
        TexMgr_Init()
        Draw_Init()
        


def SV_ClientPrintf(msg):
    raise NotImplementedError
    
