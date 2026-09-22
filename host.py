#host.py
import os
import sys

import _cmd
import chase
import cl_main
import common
import console
import cvar
import gl_draw
import gl_model
import gl_rmain
import gl_rmisc
import gl_screen
import gl_sky
import gl_texmgr
import gl_vidsdl
import glquake
import host_cmd
import in_sdl
import keys
import mathlib
import menu
import net_main
import pr_edict
import pr_exec
import progs
import protocol
import quakedef
import r_part
import sbar
import server
import snd_dma
import sv_main
import sys_sdl_unix
import view
import wad
import zone


class HostAbortServerException(Exception):
    pass

host_hunklevel = 0
host_initialized = False
host_frametime = 0.0
realtime = 0.0
oldrealtime = 0.0

host_framecount = 0

host_client : server.client_t = None

host_colormap : bytes = b''

parms : quakedef.quakeparms_t = quakedef.quakeparms_t()
parms.basedir = os.getcwd()
parms.userdir = os.getcwd()
parms.argc = len(sys.argv)
parms.argv = sys.argv
parms.errstate = 0

DEFAULT_MEMORY = ( 256 * 1024 * 1024 )

membase = None
memsize = DEFAULT_MEMORY

dev_overflows: glquake.overflowtimes_t = glquake.overflowtimes_t()
dev_stats: glquake.devstats_t = glquake.devstats_t()
dev_peakstats: glquake.devstats_t = glquake.devstats_t()

def Max_Fps_f(cvar:cvar.cvar_t):
    if cvar.value > 72:
        console.Con_Warning('host_maxfps > 72 breaks physics')

def Max_Edicts_f(cvar:cvar.cvar_t):
    if cl_main.cls.state == quakedef.cactive_t.ca_connected or sv_main.sv_active:
        console.Con_Printf('Changes to max_edicts will not take effect until next time map is loaded')

def Host_EndGame(fmt, *msg):
    message = fmt
    if msg:
        message = fmt % msg

    console.Con_DPrintf("Host_EndGame: " + message)

    if sv_main.sv_active:
        Host_ShutdownServer(False)

    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        sys_sdl_unix.Sys_Error('Host_EndGame: ' + message)

    if cl_main.cls.demonum != -1 and not cl_main.cls.timedemo:
        cl_main.CL_NextDemo()
    else:
        cl_main.CL_Disconnect()

    raise HostAbortServerException()

inerror = False
def Host_Error (format:str, *args):
    global inerror
    if inerror:
        sys_sdl_unix.Sys_Error("Host_Error: recursively entered")

    inerror = True

    gl_screen.SCR_EndLoadingPlaque()

    string = format
    if args:
        string = format % args

    console.Con_Printf(string)

    if sv_main.sv_active:
        Host_ShutdownServer(False)

    if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
        sys_sdl_unix.Sys_Error("Host_Error %s\n", string)

    cl_main.CL_Disconnect()
    cl_main.cls.demonum = -1

    cl_main.cl.intermission = 0
    inerror = False

    raise HostAbortServerException()

def Host_FindMaxClients():
    sv_main.svs.maxclients = 1

    i = common.COM_CheckParm('-dedicated')
    if i:
        cl_main.cls.state = quakedef.cactive_t.ca_dedicated
        if i != (common.com_argc - 1):
            sv_main.svs.maxclients = int(common.com_argv[i+1])
        else:
            sv_main.svs.maxclients = 8
    else:
        cl_main.cls.state = quakedef.cactive_t.ca_disconnected

    i = common.COM_CheckParm('-listen')
    if i:
        if cl_main.cls.state == quakedef.cactive_t.ca_dedicated:
            sys_sdl_unix.Sys_Error('only one of -dedicated or -listen may be specified')
        if i != (common.com_argc - 1):
            sv_main.svs.maxclients = int(common.com_argv[i+1])
        else:
            sv_main.svs.maxclients = 8

    if sv_main.svs.maxclients < 1:
        sv_main.svs.maxclients = 8
    elif sv_main.svs.maxclients > quakedef.MAX_SCOREBOARD:
        sv_main.svs.maxclients = quakedef.MAX_SCOREBOARD

    sv_main.svs.maxclientslimit = sv_main.svs.maxclients
    sv_main.svs.maxclientslimit = max(sv_main.svs.maxclientslimit, 4)

    sv_main.svs.clients = [] # change to numpy.array and set hard max limit?

    if sv_main.svs.maxclients > 1:
        cvar.Cvar_SetQuickByName('deathmatch', "1")
    else:
        cvar.Cvar_SetQuickByName('deathmatch', "0")

def Host_Version_f():
    console.Con_Printf("Quake Version %1.2f\n" % quakedef.VERSION)
    console.Con_Printf("QuakeSpasm Version " + quakedef.QUAKESPASM_VERSION)

def Host_Callback_Notify(cvar):
    if sv_main.sv_active:
        SV_BroadcastPrintf(f"{cvar['name']} changed to {cvar['string']}")

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


def SV_ClientPrintf(fmt, *args):
    string = fmt
    if args:
        string = fmt % args

    common.MSG_WriteByte(host_client.message, protocol.sv_print)
    common.MSG_WriteString(host_client.message, string)

def SV_BroadcastPrintf(fmt, *args):
    string = fmt
    if args:
        string = fmt % args

    for i in range(sv_main.svs.maxclients):
        if sv_main.svs.clients[i].active and sv_main.svs.clients[i].spawned:
            common.MSG_WriteByte(sv_main.svs.clients[i].message, protocol.svc_print)
            common.MSG_WriteString(sv_main.svs.clients[i].message, string)

def Host_ClientCommands(fmt, *args):
    string = fmt
    if args:
        string = fmt % args

    common.MSG_WriteByte(host_client.message, protocol.svc_stufftext)
    common.MSG_WriteString(host_client.message, string)


def SV_DropClient(crash: bool):

    if not crash:
        # 1. Send the disconnect notification to the leaving client
        if host_client.netconnection and net_main.NET_CanSendMessage(host_client.netconnection):
            common.MSG_WriteByte(host_client.message, protocol.svc_disconnect)
            net_main.NET_SendMessage(host_client.netconnection, host_client.message)

        # 2. Run QuakeC ClientDisconnect (important for clearing player-owned entities)
        if host_client.edict and host_client.spawned:
            saveSelf = pr_edict.pr_global_struct.self
            pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(host_client.edict)
            pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.ClientDisconnect)
            pr_edict.pr_global_struct.self = saveSelf

        sys_sdl_unix.Sys_Printf(f'Client {host_client.name} removed\n')

    # 3. Cache the index before we wipe the data
    client_num = sv_main.svs.clients.index(host_client)

    # 4. Tear down network state
    if host_client.netconnection:
        net_main.NET_Close(host_client.netconnection)
        host_client.netconnection = None

    # 5. Reset client state
    host_client.active = False
    host_client.name = ''
    host_client.old_frags = -999999
    net_main.net_activeconnections -= 1

    # 6. Broadcast the "Clear Scoreboard" message to all remaining players
    for i in range(sv_main.svs.maxclients):
        client = sv_main.svs.clients[i]

        # Only send to players who are actually in the game and NOT the one leaving
        if not client.active or client == host_client:
            continue

        # Tell this client that the slot occupied by 'client_num' is now empty
        common.MSG_WriteByte(client.message, protocol.svc_updatename)
        common.MSG_WriteByte(client.message, client_num)
        common.MSG_WriteString(client.message, '')

        common.MSG_WriteByte(client.message, protocol.svc_updatefrags)
        common.MSG_WriteByte(client.message, client_num)
        common.MSG_WriteShort(client.message, 0)

        common.MSG_WriteByte(client.message, protocol.svc_updatecolors)
        common.MSG_WriteByte(client.message, client_num)
        common.MSG_WriteByte(client.message, 0)


def Host_ShutdownServer(crash: bool):
    global host_client

    if not sv_main.sv_active:
        return

    sv_main.sv_active = False

    if cl_main.cls.state == quakedef.cactive_t.ca_connected:
        cl_main.CL_Disconnect()

    start = sys_sdl_unix.Sys_DoubleTime()

    while True:
        count = 0
        for i in range(sv_main.svs.maxclients):
            host_client = sv_main.svs.clients[i]
            if host_client.active and host_client.message.cursize:
                if net_main.NET_CanSendMessage(host_client.netconnection):
                    net_main.NET_SendMessage(host_client.netconnection, host_client.message)
                    common.SZ_Clear(host_client.message)
                else:
                    net_main.NET_GetMessage(host_client.netconnection)
                    count += 1

        if sys_sdl_unix.Sys_DoubleTime() - start > 3.0:
            break

        if not count:
            break

    buf : common.sizebuf_s = common.sizebuf_s()
    buf.data = bytearray(4)
    buf.maxsize = 4
    buf.cursize = 0

    common.MSG_WriteByte(buf, protocol.svc_disconnect)
    count = net_main.NET_SendToAll(buf, 5.0)
    if count:
        console.Con_Printf(f'Host_ShutdownServer: NET_SendToAll failed for {count} clients\n')

    for i in range(sv_main.svs.maxclients):
        host_client = sv_main.svs.clients[i]
        if host_client.active:
            SV_DropClient(crash)

    sv_main.svs.clients = [ server.client_t() for i in range(sv_main.svs.maxclients) ]

def Host_ClearMemory():

    console.Con_DPrintf('Clearing Memory\n')
    #D_FlushCaches()
    gl_model.Mod_ClearAll()
    gl_sky.Sky_ClearAll()

    zone.Hunk_FreeToLowMark(host_hunklevel)

    cl_main.cls.signon = 0
    sv_main.sv.edicts  = []
    sv_main.sv = server.server_t()
    cl_main.cl = quakedef.client_state_t()


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

    if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
        keys.Key_Init()
        console.Con_Init()

    pr_edict.PR_Init()
    gl_model.Mod_Init()
    net_main.NET_Init()
    sv_main.SV_Init()

    global host_colormap
    if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
        host_colormap = common.COM_LoadHunkFile('gfx/colormap.lmp')
        if host_colormap is None:
            sys_sdl_unix.Sys_Error('couldnt load gfx/colormap.lmp')

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
        snd_dma.S_Init()
        sbar.Sbar_Init()
        cl_main.CL_Init()

    zone.Hunk_AllocName(0, '-HOST_HUNKLEVEL-')
    host_hunklevel = zone.Hunk_LowMark()

    global host_initialized
    host_initialized = True
    console.Con_Printf('\n============Quake Initialized===============\n')

    if cl_main.cls.state != cl_main.cactive_t.ca_dedicated:
        _cmd.Cbuf_InsertText('exec quake.rc\n')
        _cmd.Cbuf_AddText('\n\nvid_unlock\n')

    if cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        _cmd.Cbuf_AddText ("exec autoexec.cfg\n")
        _cmd.Cbuf_AddText ("stuffcmds")
        _cmd.Cbuf_Execute ()
        if not sv_main.sv_active:
            _cmd.Cbuf_AddText ("map start\n")

    _cmd.Cbuf_AddText("map start\n")
    # _cmd.cmd_source = _cmd.cmd_source_t.src_command
    # _cmd.Cbuf_Execute()

    # keys.key_dest = keys.keydest_t.key_console


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

def Host_GetConsoleCommands():
    if not sys_sdl_unix.isDedicated:
        return

    while True:
        cmd = sys_sdl_unix.Sys_ConsoleInput()
        if not cmd:
            break
        _cmd.Cbuf_AddText(cmd)


def Host_ServerFrame():
    active = 0
    pr_edict.pr_global_struct.frametime = host_frametime

    sv_main.SV_ClearDatagram()
    sv_main.SV_CheckForNewClients()
    sv_main.SV_RunClients()

    if not sv_main.sv.paused and ( sv_main.svs.maxclients > 1 or keys.key_dest == keys.keydest_t.key_game):
        sv_main.SV_Physics()

    if cl_main.cls.signon == quakedef.SIGNONS: # (4)
        active = 0
        for i in range(sv_main.sv.num_edicts):
            ent: progs.edict_t = pr_edict.EDICT_NUM(i)
            if not ent.free:
                active += 1

        if active > 600 and dev_peakstats.edicts <= 600:
            console.Con_Warning(f'{active} edicts exceeds standard limit of 600 ( max = {sv_main.sv.max_edicts})')
            dev_stats.edicts = active
            dev_peakstats.edicts = max(active, dev_peakstats.edicts)

    sv_main.SV_SendClientMessages()



time1 = 0
time2 = 0
time3 = 0

def _Host_Frame(time):
    # Declare globals so we can modify variables defined at the top of the file
    global host_framecount, time1, time2, time3
    import random

    random.random()

    try:
        if not Host_FilterTime(time):
            return

        console.Con_CheckResize()

        # --- Input and Commands (Uncomment these as you implement the modules) ---
        keys.Key_UpdateForDest()
        in_sdl.IN_UpdateInputMode()
        sys_sdl_unix.Sys_SendKeyEvents()

        in_sdl.IN_Commands() # not implemented.  joystick functionality

        _cmd.Cbuf_Execute()

        net_main.NET_Poll()

        if sv_main.sv_active:
            cl_main.CL_SendCmd()

        Host_GetConsoleCommands()


        # --- Server Operations ---
        if sv_main.sv_active:
            Host_ServerFrame() # Added sv_main prefix

        # --- Client Operations ---
        if not sv_main.sv_active:
            cl_main.CL_SendCmd()

        if cl_main.cls.state == cl_main.cactive_t.ca_connected:
            cl_main.CL_ReadFromServer()

        # --- Video/Rendering ---
        host_speeds = cvar.Cvar_GetCvar('host_speeds')
        if int(host_speeds.value):
            time1 = sys_sdl_unix.Sys_DoubleTime()

        # ? in_sdl.IN_MouseMove()
        # ? cl_main.CL_Move(time)

        gl_screen.SCR_UpdateScreen()

        r_part.CL_RunParticles() # Added prefix

        if int(host_speeds.value):
            time2 = sys_sdl_unix.Sys_DoubleTime()
            # Note: Logic for pass1/pass2/pass3 goes here if needed

        if cl_main.cls.signon == quakedef.SIGNONS:
            snd_dma.S_Update(gl_rmain.r_origin, gl_rmain.vpn, gl_rmain.vright, gl_rmain.vup)
            cl_main.CL_DecayLights()
        else:
            snd_dma.S_Update(mathlib.vec3_origin, mathlib.vec3_origin, mathlib.vec3_origin, mathlib.vec3_origin )

        if host_speeds.value:
            pass1 = ( time1 - time3) * 1000
            time3 = sys_sdl_unix.Sys_DoubleTime()
            pass2 = ( time2 - time1) * 1000
            pass3 = ( time3 - time2) * 1000
            console.Con_Printf("%3i tot %3i server %3i gfx %3i snd\n" % (pass1+pass2+pass3, pass1, pass2, pass3))

        host_framecount += 1
    except HostAbortServerException:
        console.Con_Printf('caught HostAbortServerException\n')
        return


timetotal = 0
timecount = 0
def Host_Frame(time):
    global timetotal
    global timecount

    serverprofile = int(cvar.Cvar_GetCvar('serverprofile').value)

    if not serverprofile:
        _Host_Frame(time)
        return

    time1 = sys_sdl_unix.Sys_DoubleTime ()
    _Host_Frame (time)
    time2 = sys_sdl_unix.Sys_DoubleTime ()

    timetotal += time2 - time1
    timecount += 1

    if timecount < 1000:
        return

    m = timetotal*1000/timecount
    timecount = 0
    timetotal = 0
    c = 0
    for i in range(sv_main.svs.maxclients):
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

    if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
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

            f.writelines(f'{var.name} "{var.string}"\n' for var in archived_cvars)

            print(f"Config saved to {config_path}")
    except Exception as e:
        console.Con_Printf(f"ERROR: Could not save config: {e}\n")




# Module global state matching C globals in gl_mesh.c
numorder: int = 0
numcommands: int = 0
used: list[int] = []
commands: list[int] = []
vertexorder: list[int] = []


def BuildTris(
    pheader: any,
    triangles: list[any],
    stverts: list[any],
) -> None:
    """Builds optimized GL triangle strips/fans for alias model rendering.

    Args:
        pheader: Model header object containing numtris, skinwidth, and skinheight.
        triangles: List of mtriangle_t mesh triangles.
        stverts: List of stvert_t texture coordinate entries.

    C equivalent:
    static void BuildTris (void) in gl_mesh.c
    """
    global numorder, numcommands, used, commands, vertexorder
    global stripverts, striptris

    MAX_COMMANDS = 16384  # Matches C command array sizing

    numorder = 0
    numcommands = 0
    commands = [0] * MAX_COMMANDS
    vertexorder = [0] * MAX_COMMANDS
    used = [0] * pheader.numtris

    bestverts = [0] * 128
    besttris = [0] * 128

    for i in range(pheader.numtris):
        # Pick an unused triangle and attempt starting a strip or fan
        if used[i]:
            continue

        bestlen = 0
        besttype = 0

        for type_idx in range(2):  # 0 = Fan, 1 = Strip
            for startv in range(3):
                if type_idx == 1:
                    length = StripLength(i, startv, triangles, pheader, used)
                else:
                    length = FanLength(i, startv, triangles, pheader, used)

                if length > bestlen:
                    besttype = type_idx
                    bestlen = length
                    for j in range(bestlen + 2):
                        bestverts[j] = stripverts[j]
                    for j in range(bestlen):
                        besttris[j] = striptris[j]

        # Mark used triangles for the winning strip/fan
        for j in range(bestlen):
            used[besttris[j]] = 1

        # Command code: positive count = TRIANGLE_STRIP, negative = TRIANGLE_FAN
        if besttype == 1:
            commands[numcommands] = bestlen + 2
        else:
            commands[numcommands] = -(bestlen + 2)
        numcommands += 1

        for j in range(bestlen + 2):
            # Emit vertex index into the reorder buffer
            k = bestverts[j]
            vertexorder[numorder] = k
            numorder += 1

            # Extract texture coordinates
            s = float(stverts[k].s)
            t = float(stverts[k].t)

            # Adjust s-coordinate if triangle is on back face skin seam
            if not triangles[besttris[0]].facesfront and stverts[k].onseam:
                s += pheader.skinwidth / 2.0

            # Normalize UV coordinates to [0.0, 1.0] range
            s = (s + 0.5) / float(pheader.skinwidth)
            t = (t + 0.5) / float(pheader.skinheight)

            # Reinterpret float bits as int (C memcpy (&tmp, &s, 4))
            s_int = struct.unpack("i", struct.pack("f", s))[0]
            t_int = struct.unpack("i", struct.pack("f", t))[0]

            commands[numcommands] = s_int
            numcommands += 1
            commands[numcommands] = t_int
            numcommands += 1

    # End of command stream marker
    commands[numcommands] = 0
    numcommands += 1

isdown: bool = False
def Host_Shutdown():
    if isdown:
        print('recursive shutdown\n')
        return
    isdown = True

    gl_screen.scr_disabled_for_loading = True

    Host_WriteConfiguration()

    net_main.NET_Shutdown()

    if cl_main.cls.state != quakedef.cactive_t.ca_dedicated:
        if console.con_initialized:
            keys.History_Shutdown()

        snd_dma.S_Shutdown()
        in_sdl.IN_Shutdown()
        gl_vidsdl.VID_Shutdown()

    console.LOG_Close()
