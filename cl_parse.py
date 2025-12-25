#cl_parse.py

import _cmd
import cl_main
import net_main
import common
import host
import host_cmd
import console
import quakedef
import gl_screen
import gl_model
import sys_sdl_unix
import protocol
import gl_vidsdl

svc_strings = [
    "svc_bad",
    "svc_nop",
    "svc_disconnect",
    "svc_updatestat",
    "svc_version",      # [long] server version
    "svc_setview",      # [short] entity number
    "svc_sound",        # <see code>
    "svc_time",         # [float] server time
    "svc_print",        # [string] null terminated string
    "svc_stufftext",    # [string] stuffed into client's console buffer
                        # the string should be \n terminated
    "svc_setangle",     # [vec3] set the view angle to this absolute value

    "svc_serverinfo",   # [long] version
                        # [string] signon string
                        # [string]..[0]model cache [string]...[0]sounds cache
                        # [string]..[0]item cache
    "svc_lightstyle",   # [byte] [string]
    "svc_updatename",   # [byte] [string]
    "svc_updatefrags",  # [byte] [short]
    "svc_clientdata",   # <shortbits + data>
    "svc_stopsound",    # <see code>
    "svc_updatecolors", # [byte] [byte]
    "svc_particle",     # [vec3] <variable>
    "svc_damage",           # [byte] impact [byte] blood [vec3] from

    "svc_spawnstatic",
    "OBSOLETE svc_spawnbinary",
    "svc_spawnbaseline",

    "svc_temp_entity",  # <variable>
    "svc_setpause",
    "svc_signonnum",
    "svc_centerprint",
    "svc_killedmonster",
    "svc_foundsecret",
    "svc_spawnstaticsound",
    "svc_intermission",
    "svc_finale",       # [string] music [string] text
    "svc_cdtrack",      # [byte] track [byte] looptrack
    "svc_sellscreen",
    "svc_cutscene",
#johnfitz -- new server messages
    "", # 35
    "", # 36
    "svc_skybox",      # 37                 # [string] skyname
    "svc_botchat",      # 38 (2021 RE-RELEASE)
    "", # 39
    "svc_bf", # 40                     # no data
    "svc_fog", # 41                    # [byte] density [byte] red [byte] green [byte] blue [float] time
    "svc_spawnbaseline2", #42          # support for large modelindex, large framenum, alpha, using flags
    "svc_spawnstatic2", # 43           # support for large modelindex, large framenum, alpha, using flags
    "svc_spawnstaticsound2", # 44      # [coord3] [short] samp [byte] vol [byte] aten
#johnfitz

# 2021 RE-RELEASE:
    "svc_setviews", # 45
    "svc_updateping", # 46
    "svc_updatesocial", # 47
    "svc_updateplinfo", # 48
    "svc_rawprint", # 49
    "svc_servervars", # 50
    "svc_seq", # 51
    "svc_achievement", # 52
    "svc_chat", # 53
    "svc_levelcompleted", # 54
    "svc_backtolobby", # 55
    "svc_localsound" # 56

]

warn_about_nehahra_protocol = False
v_punchangles = [0, 0, 0]

def SHOWNET(x):
    cl_shownet = int(cvar.Cvar_GetCvar('cl_shownet').value)
    if cl_shownet == 2:
        console.Con_Printf('%3i: %s\n' % (common.msg_readcount-1, x))

def CL_ParseServerMessage():
    import cvar
    cl_shownet = int(cvar.Cvar_GetCvar('cl_shownet').value)
    if cl_shownet == 1:
        console.Con_Printf(f'{net_main.net_message.cursize} ')
    elif cl_shownet == 2:
        console.Con_Printf('---------------\n')


    common.MSG_BeginReading()

    lastcmd = 0

    while True:
        if common.msg_badread:
            host.Host_Error('CL_ParseServerMessage: bad server message')

        cmd = MSG_ReadByte()

        if cmd == -1:
            SHOWNET('END OF MESSAGE')
            return

        if cmd & protocol.U_SIGNAL:
            SHOWNET('fast update')
            CL_ParseUpdate(cmd & 127)
            continue

        if cmd < len(svc_strings):
            SHOWNET(svc_strings[cmd])

        match cmd:
            case protocol.svc_nop:
                pass

            case protocol.svc_time:
                cl_main.cl.mtime[1] = cl_main.cl.mtime[0]
                cl_main.cl.mtime[0] = common.MSG_ReadFloat()

            case protocol.svc_clientdata:
                CL_ParseClientdata()

            case protocol.svc_version:
                i = common.MSG_ReadLong()
                if i != protocol.PROTOCOL_NETQUAKE and i != protocol.PROTOCOL_FITZQUAKE and i != protocol.PROTOCOL_RMQ:
                    host.Host_Error(f'Server returned version {i} not {protocol.PROTOCOL_NETQUAKE} or {protocol.PROTOCOL_FITZQUAKE} or  {protocol.PROTOCOL_RMQ}')

                cl_main.cl.protocol = i

            case protocol.svc_disconnect:
                host.Host_EndGame('Server disconnected\n')

            case protocol.svc_print:
                console.Con_Printf('%s' % common.MSG_ReadString())

            case protocol.svc_centerprint:
                s = common.MSG_ReadString()
                gl_screen.SCR_CenterPrint(s)
                console.Con_LogCenterPrint(s)

            case protocol.svc_stufftext:
                _cmd.Cbuf_AddText(common.MSG_ReadString())

            case protocol.svc_damage:
                V_ParseDamage()

            case protocol.svc_serverinfo:
                CL_ParseServerInfo()
                gl_vidsdl._vid.recalc_refdef = True

            case protocol.svc_setangle:
                for i in range(3):
                    cl_main.cl.viewangles[i] = MSG_ReadAngle(cl_main.cl.protocolflags)

            case protocol.svc_setview:
                cl_main.cl.viewentity = MSG_ReadShort()

            case protocol.svc_lightstyle:
                i = MSG_ReadByte()
                if i >= quakedef.MAX_LIGHTSTYLES:
                    sys_sdl_unix.Sys_Error('svc_lightstyle > MAX_LIGHTSTYLES')

                cl_main.cl_lightstyle[i].map = MSG_ReadString()
                cl_main.cl_lightstyle[i].length = len(cl_main.cl_lightstyle[i].map)

                if cl_main.cl_lightstyle[i].length:
                    total = 0
                    cl_main.cl_lightstyle[i].peak = 'a'

                    for j in range(cl_main.cl_lightstyle[i].length):
                        total += cl_main.cl_lightstyle[i].map[j] = ord('a')
                        cl_main.cl_lightstyle[i].peak = max(cl_main.cl_lightstyle[i].peak, cl_main.cl_lightstyle[i].map[j])

                    cl_main.cl_lightstyle[i].average = total / cl_main.cl_lightstyle[i].length + ord('a')
                else:
                    cl_main.cl_lightstyle[i].average = cl_main.cl_lightstyle[i].peak = 'm'

            case protocol.svc_sound:
                CL_ParseStartSoundPacket()

            case protocol.svc_stopsound:
                i = MSG_ReadShort()
                S_StopSound(i >> 3, i & 7)

            case protocol.svc_updatename:
                Sbar_Changed()
                i = MSG_ReadByte()
                if i >= cl_main.cl.maxclients:
                    host.Host_Error('CL_ParseServerMessage: svc_updatename > MAX_SCOREBOARD')
                cl_main.cl.scores[i].name = MSG_ReadString()

            case protocol.svc_updatefrags:
                Sbar_Changed()
                i = MSG_ReadByte()
                if i >= cl_main.cl.maxclients:
                    host.Host_Error('CL_ParseServerMessage: svc_updatefrags > MAX_SCOREBOARD')
                cl_main.cl.scores[i].frags = MSG_ReadShort()

            case protocol.svc_updatecolors:
                Sbar_Changed()
                i = MSG_ReadByte()
                if i >= cl_main.cl.maxclients:
                    host.Host_Error('CL_ParseServerMessage: svc_updatecolors > MAX_SCOREBOARD')
                cl_main.cl.scores[i].colors = MSG_ReadByte ();

            case protocol.svc_particle:
                R_ParseParticleEffect()

            case protocol.svc_spawnbaseline:
                i = MSG_ReadShort()
                CL_ParseBaseline(CL_EntityNum(i), 1)

            case protocol.svc_spawnstatic:
                CL_ParseStatic(1)

            case protocol.svc_temp_entity:
                CL_ParseTEnt()

            case protocol.svc_setpause:
                cl_main.cl.paused = MSG_ReadByte()
                if cl_main.cl.paused:
                    pass

            case protocol.svc_signonnum:
                i = MSG_ReadByte()
                if i <= cl_main.cls.signon:
                    host.Host_Error('received signon %i when at %i' % ( i, cl_main.cls.signon))

                cl_main.cls.signon = i

                if i == 2:
                    if cl_main.cl.num_statics > 128:
                        console.Con_Warning('i static entities exceeds standard limit of 128 (max = %d).\n' % (cl_main.cl.num_statics, client.MAX_STATIC_ENTITIES))
                    R_CheckEfrags()

                CL_SignonReply()

            case protocol.svc_killedmonster:
                cl_main.cl.stats[quakedef.STAT_MONSTERS] += 1

            case protocol.svc_foundsecret:
                cl_main.cl.stats[quakedef.STAT_SECRETS] += 1

            case protocol.svc_updatestat:
                i = MSG_ReadByte()

                if i < 0 or i >= quakedef.MAX_CL_STATS:
                    sys_sdl_unix.Sys_Error('svc_updatestat %i is invalid' % i)

                cl_main.cl.stats[i] = MSG_ReadLong()

            case protocol.svc_spawnstaticsound:
                CL_ParseStaticSound(1)

            case protocol.svc_cdtrace:
                raise NotImplementedError

            case protocol.svc_intermission:
                cl_main.cl.intermission = 1
                cl_main.cl.completed_time = cl_main.cl.time

                gl_vidsdl._vid.recalc_refdef = True
                V_RestoreAngles()

            case protocol.svc_finale:
                cl_main.cl.intermission = 2
                cl_main.cl.completed_time = cl_main.cl.time
                gl_vidsdl._vid.recalc_refdef = True

                s = MSG_ReadString()
                gl_screen.SCR_CenterPrint(s)
                console.Con_LogCenterPrint(s)

                V_RestoreAngles()

            case protocol.svc_cutscene:
                cl_main.cl.intermission = 3
                cl_main.cl.completed_time = cl_main.cl.time
                gl_vidsdl._vid.recalc_refdef = True

                s = MSG_ReadString()
                gl_screen.SCR_CenterPrint(s)
                console.Con_LogCenterPrint(s)

                V_RestoreAngles()

            case protocol.svc_sellscreen:
                _cmd.Cmd_ExecuteString('help', _cmd.cmd_source_t.src_command)

            case protocol.svc_skybox:
                gl_sky.Sky_LoadSkyBox(MSG_ReadString())

            case protocol.svc_bf:
                _cmd.Cmd_ExecuteString('bf', _cmd.cmd_source_t.src_command)

            case protocol.svc_fog:
                Fog_ParseServerMessage()

            case protocol.svc_spawnbaseline2:
                i = MSG_ReadShort()
                CL_ParseBaseline(CL_EntityNum(i), 2)

            case protocol.svc_spawnstatic2:
                CL_ParseStatic(2)

            case protocol.svc_spawnstaticsound2:
                CL_ParseStaticSound(2)

            case protocol.svc_achievement:
                raise NotImplementedError

            case protocol.svc_localsound:
                CL_ParseLocalSound()

            case _:
                host.Host_Error('Illegible server message %d (previous was %s)' % ( cmd, svc_strings[lastcmd]))


        lastcmd = cmd


def CL_ParseServerInfo():

    console.Con_DPrintf('server info packet received \n')

    if cl_main.cls.demoplayback:
        gl_screen.SCR_BeginLoadingPlaque()


    CL_ClearState()

    i = MSG_ReadLong()

    if i not in (protocol.PROTOCOL_NETQUAKE, protocol.PROTOCOL_FITZQUAKE, protocol.PROTOCOL_RMQ):
        console.Con_Printf('\n')
        host.Host_Error(f'Server returned version {i}, not supported')

    cl_main.cl.protocol = i

    if cl_main.cl.protocol == protocol.PROTOCOL_RMQ:
        supportedflags = (PRFL_SHORTANGLE | PRFL_FLOATANGLE | PRFL_24BITCOORD | PRFL_FLOATCOORD | PRFL_EDICTSCALE | PRFL_INT32COORD)

        cl_main.cl.protocolflags = MSG_ReadLong()

        if 0 != ( cl_main.cl.protocolflags & ( ~supportedflags)):
            console.Con_Warning('PROTOCOL_RMQ protocolflags %i contains unsupported flags\n' % cl_main.cl.protocolflags)

    else:
        cl_main.cl.protocolflags = 0

    cl_main.cl.maxclients = MSG_ReadByte()


    cl_main.cl.maxclients = MSG_ReadByte()
    if cl_main.cl.maxclients < 1 or cl_main.cl.maxclients > quakedef.MAX_SCOREBOARD:
        host.Host_Error('bad maxclients %u from server' % cl_main.cl.maxclients)

    cl_main.cl.scores = [client.scoreboard_t() for _ in range(cl_main.cl.maxclients)]

    cl_main.cl.gametype = MSG_ReadByte()

    s = MSG_ReadString()
    cl_main.cl.levelname = s

    console.Con_Printf('\n%s\n' % console.Con_Quakebar(40))
    console.Con_Printf('%c%s\n' % (2, s))

    console.Con_Printf('using protocol %i' % i)

    cl_main.cl.model_precache = []

    nummodels = 1
    model_precache = []
    while True:
        s = MSG_ReadString()
        if not s:
            break

        if nummodels >= quakedef.MAX_MODELS:
            host.Host_Error('Server sent too many model precaches')

        model_precache.append(s)
        gl_model.Mod_TouchModel(s)

        nummodels += 1

    if nummodels >= 256:
        console.Con_Warning('%i models exceeds the standard limit of 256 ' % nummodels)


    cl_main.cl.model_precache = [None] * (nummodels + 1)

    sound_precache = []
    cl_main.cl.sound_precache = []
    numsounds = 1
    while True:
        s = MSG_ReadString()
        if not s:
            break

        if numsounds >= quakedef.MAX_SOUNDS:
            host.Host_Error('server sent too many sound precaches')

        sound_precache.append(s)
        S_TouchSound(s)
        numsounds += 1

    if numsounds >= 256:
        console.Con_Warning('%i sounds exceed standard limit of 256' % numsounds)

    cl_main.cl.mapname = common.COM_StripExtension(common.COM_SkipPath(model_precache[0]))

    # Following the C source's 1-based indexing for models
    for i in range(len(model_precache)):
        model_name = model_precache[i]
        # Quake models start at index 1 (World is always 1)
        cl_main.cl.model_precache[i + 1] = gl_model.Mod_ForName(model_name, False)

        if cl_main.cl.model_precache[i + 1] is None:
            host.Host_Error(f"Model {model_name} not found")

        host.CL_KeepaliveMessage()

    # Pre-allocate sound list
    cl_main.cl.sound_precache = [None] * (numsounds + 1)

    S_BeginPrecaching()
    for i in range(len(sound_precache)):
        sound_name = sound_precache[i]
        # In Quake, sound index 0 is null, index 1 is the first real sound
        cl_main.cl.sound_precache[i + 1] = S_PrecacheSound(sound_name)
        host.CL_KeepaliveMessage()
    S_EndPrecaching()

    cl_main.cl_entities[0].model = cl_main.cl.worldmodel = cl_main.cl.model_precache[1]

    R_NewMap()

    console.con_lastcenterstring = ''

    #Hunk_Check() ????

    host_cmd.noclip_anglehack = False

    warn_about_nehahra_protocol = True

    #host.dev_stats = 0
    #host.dev_peakstats = 0
    #host.dev_overflows = 0

