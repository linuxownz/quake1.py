#cl_parse.py

import random

#import gl_refrag
import _cmd
import cl_demo
import cl_main
import common
import console
import cvar
import gl_model
import gl_rmisc
import gl_screen
import gl_vidsdl
import glquake
import host
import host_cmd
import mathlib
import net_defs
import net_main
import protocol
import q_sound
import quakedef
import render
import sbar
import snd_dma
import sv_main
import sys_sdl_unix
import vid
import view

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
v_punchangles: list[float] = [0, 0, 0]

net_olddata: bytearray = bytearray(net_defs.NET_MAXMESSAGE)
lastmsg: float = 0.0

def CL_EntityNum(num: int) ->  render.entity_t:
    if num < 0:
        host.Host_Error(f'CL_EntityNum: {num} is an invalid number')

    if num >= cl_main.cl.num_entities:
        if num >= cl_main.cl_max_edicts:
            host.Host_Error(f'CL_EntityNum: {num} is an invalid number')

        while cl_main.cl.num_entities <= num:
            e = cl_main.cl_entities[cl_main.cl.num_entities]
            e.colormap = gl_vidsdl._vid.colormap
            e.lerpflags |= render.LERP_RESETMOVE | render.LERP_RESETANIM
            e.baseline.scale = protocol.ENTSCALE_DEFAULT
            cl_main.cl.num_entities += 1

    return cl_main.cl_entities[num]



def CL_ParseStartSoundPacket():
    volume: int = 0
    attenuation: float = 0.0
    ent: int = 0
    channel: int = 0
    sound_num: int = 0
    pos: list[float] = [0., 0., 0.]

    field_mask = common.MSG_ReadByte()

    if field_mask & protocol.SND_VOLUME:
        volume = common.MSG_ReadByte()
    else:
        volume = protocol.DEFAULT_SOUND_PACKET_VOLUME

    if field_mask & protocol.SND_ATTENUATION:
        attenuation = common.MSG_ReadByte() / 64.0
    else:
        attenuation = protocol.DEFAULT_SOUND_PACKET_ATTENUATION

    if field_mask & protocol.SND_LARGEENTITY:
        ent = common.MSG_ReadShort()
        channel = common.MSG_ReadByte()
    else:
        channel = common.MSG_ReadShort()
        ent = channel >> 3
        channel &= 7

    if field_mask & protocol.SND_LARGESOUND:
        sound_num = common.MSG_ReadShort()
    else:
        sound_num = common.MSG_ReadByte()

    if sound_num >= quakedef.MAX_SOUNDS:
        host.Host_Error(f'CL_ParseStartSoundPacket: {sound_num} > MAX_SOUNDS')

    if ent > cl_main.cl_max_edicts:
        host.Host_Error(f'CL_ParseStartSoundPacket: ent = {ent}')

    for i in range(3):
        pos[i] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

    snd_dma.S_StartSound( ent, channel, cl_main.cl.sound_precache[sound_num], pos, volume / 255, attenuation)


def CL_ParseLocalSound():

    field_mask: int = common.MSG_ReadByte()
    sound_num: int = common.MSG_ReadShort() if ( field_mask & protocol.SND_LARGESOUND ) else common.MSG_ReadByte()

    if sound_num >= quakedef.MAX_SOUNDS:
        host.Host_Error(f'CL_ParseLocalSound: {sound_num} > MAX_SOUNDS')

    snd_dma.S_LocalSound(cl_main.cl.sound_precache[sound_num].name)


def CL_KeepAliveMessage():
    global lastmsg

    if sv_main.sv.active:
        return

    if cl_main.cls.demoplayback:
        return

    olddata:common.sizebuf_s = net_olddata
    old: common.sizebuf_s = net_main.net_message
    net_olddata[:net_main.net_message.cursize] = net_main.net_message.data[:net_main.net_message.cursize]

    ret = cl_demo.CL_GetMessage()

    while ret:
        match ret:
            case 0:
                break
            case 1:
                host.Host_Error('CL_KeepAliveMessage: recieved a message')
                break
            case 2:
                if common.MSG_ReadByte() != protocol.svc_nop:
                    host.Host_Error('CL_KeepAliveMessage:L datagram wasnt a nop')
                break

        ret = cl_demo.CL_GetMessage()

    net_main.net_message = old

    net_main.net_message.data[:net_main.net_message.cursize] = olddata[:net_main.net_message.cursize]

    time: float = sys_sdl_unix.Sys_DoubleTime()
    if time - lastmsg < 5:
        return

    lastmsg = time

    console.Con_Printf('--> client to server keepalive')

    common.MSG_WriteByte(cl_main.cls.message, protocol.clc_nop)
    net_main.NET_SendMessage(cl_main.cls.netcon, cl_main.cls.message)
    common.SZ_Clear(cl_main.cls.message)

def CL_ParseServerInfo():
    console.Con_DPrintf('Serverinfo packet received')

    if cl_main.cls.demoplayback:
        gl_screen.SCR_BeginLoadingPlaque()

    cl_main.CL_ClearState()

    i = common.MSG_ReadLong()

    if i != protocol.PROTOCOL_NETQUAKE and i != protocol.PROTOCOL_FITZQUAKE and i != protocol.PROTOCOL_RMQ:
        console.Con_Printf('\n')
        host.Host_Error(f'Server returned version {i}, not {protocol.PROTOCOL_FITZQUAKE} or {protocol.PROTOCOL_NETQUAKE} or {protocol.PROTOCOL_RMQ}')

    cl_main.cl.protocol = i

    if cl_main.cl.protocol == protocol.PROTOCOL_RMQ:
        supportedflags = (protocol.PRFL_SHORTANGLE | protocol.PRFL_FLOATANGLE | protocol.PRFL_24BITCOORD | protocol.PRFL_FLOATCOORD | protocol.PRFL_EDICTSCALE | protocol.PRFL_INT32COORD)

        cl_main.cl.protocolflags = common.MSG_ReadLong()

        if 0 != ( cl_main.cl.protocolflags & ( ~supportedflags) ):
            console.Con_Warning(f'PROTOCOL_RMQ protocolflags {cl_main.cl.protocolflags} contains unsupported flags')
    else:
        cl_main.cl.protocolflags = 0

    cl_main.cl.maxclients = common.MSG_ReadByte()
    if cl_main.cl.maxclients < 1 or cl_main.cl.maxclients > quakedef.MAX_SCOREBOARD:
        host.Host_Error(f'Bad maxclients ({cl_main.cl.maxclients}) from server')

    cl_main.cl.scores = [quakedef.scoreboard_t() for _ in range(cl_main.cl.maxclients)]

    cl_main.cl.gametype = common.MSG_ReadByte()

    cl_main.cl.levelname = common.MSG_ReadString()

    console.Con_Printf(f'Using protocol {i}')

    cl_main.cl.model_precache = [ quakedef.qmodel_t() for _ in range(quakedef.MAX_MODELS)]

    model_precache: list[str] = ['' for _ in range(quakedef.MAX_MODELS)]
    sound_precache: list[str] = ['' for _ in range(quakedef.MAX_SOUNDS)]

    for nummodels in range(1, quakedef.MAX_MODELS):
        string = common.MSG_ReadString()
        if not string:
            break

        if nummodels >= quakedef.MAX_MODELS - 1:
            host.Host_Error('server sent too many model precaches')

        model_precache[nummodels] = string
        gl_model.Mod_TouchModel(string)

    if nummodels >=  256:
        console.Con_DWarning(f'{nummodels} models exceeds standard limit of 256 (max = {quakedef.MAX_MODELS})')

    cl_main.cl.sound_precache = [ q_sound.sfx_t() for _ in range(quakedef.MAX_SOUNDS)]

    for numsounds in range ( 1, quakedef.MAX_SOUNDS):
        string = common.MSG_ReadString()
        if not string:
            break

        if numsounds >= quakedef.MAX_SOUNDS - 1:
            host.Host_Error('Server sent too many sound precaches')

        sound_precache[numsounds] = string
        snd_dma.S_TouchSound(string)

    if numsounds >= 256:
        console.Con_DWarning(f'{numsounds} sounds exceeds standard limit of 256 (max = {quakedef.MAX_SOUNDS})')

    cl_main.cl.mapname = common.COM_StripExtension(common.COM_SkipPath(model_precache[1]))

    for i in range( 1, nummodels):
        cl_main.cl.model_precache[i] = gl_model.Mod_ForName(model_precache[i])

        if cl_main.cl.model_precache[i] is None:
            host.Host_Error(f'Model {model_precache[i]} not found')

        CL_KeepAliveMessage()

    #snd_dma.S_BeginPrecaching()  # empty function

    for i in range(1, numsounds):
        cl_main.cl.sound_precache[i] = snd_dma.S_PrecacheSound(sound_precache[i])
        CL_KeepAliveMessage()

    #snd_dma.S_EndPrecaching() # empty function

    cl_main.cl_entities[0].model = cl_main.cl.worldmodel = cl_main.cl.model_precache[1]

    gl_rmisc.R_NewMap()

    console.con_lastcenterstring = ''

    host_cmd.noclip_anglehack = False

    global warn_about_nehahra_protocol
    warn_about_nehahra_protocol = True

    host.dev_stats = glquake.devstats_t()
    host.dev_peakstats = glquake.devstats_t()
    host.dev_overflows = glquake.overflowtimes_t()

def CL_ParseUpdate(bits: int):
    i: int = 0
    if cl_main.cls.signon == quakedef.SIGNONS - 1:
        cl_main.cls.signon = quakedef.SIGNONS
        cl_main.CL_SignonReply()

    if bits & protocol.U_MOREBITS:
        i = common.MSG_ReadByte()
        bits |= ( i << 8 )

    if cl_main.cl.protocol == protocol.PROTOCOL_FITZQUAKE or cl_main.cl.protocol == protocol.PROTOCOL_RMQ:
        if bits & protocol.U_EXTEND1:
            bits |= common.MSG_ReadByte() << 16
        if bits & protocol.U_EXTEND2:
            bits |= common.MSG_ReadByte() << 24

    if bits & protocol.U_LONGENTITY:
        num = common.MSG_ReadShort()
    else:
        num = common.MSG_ReadByte()

    ent: render.entity_t = CL_EntityNum(num)

    if ent.msgtime != cl_main.cl.mtime[1]:
        forcelink = True
    else:
        forcelink = False

    if ent.msgtime + 0.2 < cl_main.cl.mtime[0]:
        ent.lerpflags |= render.LERP_RESETANIM

    ent.msgtime = cl_main.cl.mtime[0]

    if bits & protocol.U_MODEL:
        modnum = common.MSG_ReadByte()
        if modnum >= quakedef.MAX_MODELS:
            host.Host_Error('CL_ParseUpdate: bad modnum')
    else:
        modnum = ent.baseline.modelindex

    if bits & protocol.U_FRAME:
        ent.frame = common.MSG_ReadByte()
    else:
        ent.frame = ent.baseline.frame

    if bits & protocol.U_COLORMAP:
        i = common.MSG_ReadByte()
    else:
        i = ent.baseline.colormap

    if not i:
        ent.colormap = gl_vidsdl._vid.colormap
    else:
        if i > cl_main.cl.maxclients:
            sys_sdl_unix.Sys_Error( 'i >= cl.maxclients')
        ent.colormap = cl_main.cl.scores[i-1].translations

    if bits & protocol.U_SKIN:
        skin = common.MSG_ReadByte()
    else:
        skin = ent.baseline.skin

    if skin != ent.skinnum:
        ent.skinnum = skin
        if num > 0 and num <= cl_main.cl.maxclients:
            gl_rmisc.R_TranslateNewPlayerSkin(num - 1)

    if bits & protocol.U_EFFECTS:
        ent.effects = common.MSG_ReadByte()
    else:
        ent.effects = ent.baseline.effects

    mathlib.VectorCopy(ent.msg_origins[0], ent.msg_origins[1])
    mathlib.VectorCopy(ent.msg_angles[0], ent.msg_angles[1])

    if bits & protocol.U_ORIGIN1:
        ent.msg_origins[0][0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    else:
        ent.msg_origins[0][0] = ent.baseline.origin[0]

    if bits & protocol.U_ANGLE1:
        ent.msg_angles[0][0] = common.MSG_ReadAngle(cl_main.cl.protocolflags)
    else:
        ent.msg_angles[0][0] = ent.baseline.angles[0]


    if bits & protocol.U_ORIGIN2:
        ent.msg_origins[0][1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    else:
        ent.msg_origins[0][1] = ent.baseline.origin[1]

    if bits & protocol.U_ANGLE2:
        ent.msg_angles[0][1] = common.MSG_ReadAngle(cl_main.cl.protocolflags)
    else:
        ent.msg_angles[0][1] = ent.baseline.angles[1]


    if bits & protocol.U_ORIGIN3:
        ent.msg_origins[0][2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    else:
        ent.msg_origins[0][2] = ent.baseline.origin[2]

    if bits & protocol.U_ANGLE3:
        ent.msg_angles[0][2] = common.MSG_ReadAngle(cl_main.cl.protocolflags)
    else:
        ent.msg_angles[0][2] = ent.baseline.angles[2]

    if bits & protocol.U_STEP:
        ent.lerpflags |= render.LERP_MOVESTEP
        ent.forcelink = True
    else:
        ent.lerpflags &= ~render.LERP_MOVESTEP

    if cl_main.cl.protocol == protocol.PROTOCOL_FITZQUAKE or cl_main.cl.protocol == protocol.PROTOCOL_RMQ:
        if bits & protocol.U_ALPHA:
            ent.alpha = common.MSG_ReadByte()
        else:
            ent.alpha = ent.baseline.alpha

        if bits & protocol.U_SCALE:
            ent.scale = common.MSG_ReadByte()
        else:
            ent.scale = ent.baseline.scale

        if bits & protocol.U_FRAME2:
            ent.frame = ( ent.frame & 0x00ff ) | ( common.MSG_ReadByte() << 8)

        if bits & protocol.U_MODEL2:
            modnum = ( modnum & 0x00FF) | ( common.MSG_ReadByte() << 8)

        if bits & protocol.U_LERPFINISH:
            ent.lerpfinish = ent.msgtime + ( common.MSG_ReadByte() / 255)
            ent.lerpflags |= render.LERP_FINISH
        else:
            ent.lerpflags &= ~render.LERP_FINISH
    elif cl_main.cl.protocol == protocol.PROTOCOL_NETQUAKE:
        if bits & protocol.U_TRANS:
            global warn_about_nehahra_protocol
            if warn_about_nehahra_protocol:
                console.Con_Warning('nonstandard update bit, assuming Mehahra protocol')
                warn_about_nehahra_protocol = False

            a = common.MSG_ReadFloat()
            b = common.MSG_ReadFloat()

            if a == 2:
                common.MSG_ReadFloat()

            ent.alpha = protocol.ENTALPHA_DECODE(b)
        else:
            ent.alpha = ent.baseline.alpha
        ent.scale = ent.baseline.scale

    model: quakedef.qmodel_t = cl_main.cl.model_precache[modnum]

    if model != ent.model:
        ent.model = model

        if model:
            if model.synctype == quakedef.synctype_t.ST_RAND:
                ent.syncbase = random.random()
            else:
                ent.syncbase = 0.0
        else:
            forcelink = True

        if num > 0 and num < cl_main.cl.maxclients:
            gl_rmisc.R_TranslateNewPlayerSkin(num - 1)

        ent.lerpflags |= render.LERP_RESETANIM

    if forcelink:
        mathlib.VectorCopy( ent.msg_origins[0], ent.msg_origins[1] )
        mathlib.VectorCopy( ent.msg_origins[0], ent.origin )
        mathlib.VectorCopy( ent.msg_angles[0],  ent.msg_angles[1] )
        mathlib.VectorCopy( ent.msg_angles[0], ent.angles )
        ent.forcelink = True

def CL_ParseBaseline(ent: render.entity_t, version: int):
    bits = 0

    if version == 2:
        bits = common.MSG_ReadByte()

    ent.baseline.modelindex = common.MSG_ReadShort() if bits & protocol.B_LARGEMODEL else common.MSG_ReadByte()
    ent.baseline.frame = common.MSG_ReadShort() if bits & protocol.B_LARGEFRAME else common.MSG_ReadByte()

    ent.baseline.colormap = common.MSG_ReadByte()
    ent.baseline.skin = common.MSG_ReadByte()

    for i in range(3):
        ent.baseline.origin[i] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
        ent.baseline.angles[i] = common.MSG_ReadAngle(cl_main.cl.protocolflags)

    ent.baseline.alpha = common.MSG_ReadByte() if bits & protocol.B_ALPHA else protocol.ENTALPHA_DEFAULT
    ent.baseline.scale = common.MSG_ReadByte() if bits & protocol.B_SCALE else protocol.ENTSCALE_DEFAULT

def CL_ParseClientdata():

    bits = common.MSG_ReadShort()

    if bits & protocol.SU_EXTEND1:
        bits |= (common.MSG_ReadByte() << 16)
    if bits & protocol.SU_EXTEND2:
        bits |= (common.MSG_ReadByte() << 24)

    if bits & protocol.SU_VIEWHEIGHT:
        cl_main.cl.viewheight = common.MSG_ReadChar()
    else:
        cl_main.cl.viewheight = protocol.DEFAULT_VIEWHEIGHT

    if bits & protocol.SU_IDEALPITCH:
        cl_main.cl.idealpitch = common.MSG_ReadChar()
    else:
        cl_main.cl.idealpitch = 0

    mathlib.VectorCopy(cl_main.cl.mvelocity[0], cl_main.cl.mvelocity[1])

    for i in range(3):
        if bits & ( protocol.SU_PUNCH1 << i ):
            cl_main.cl.punchangle[i] = common.MSG_ReadChar()
        else:
            cl_main.cl.punchangle[i] = 0

        if bits & ( protocol.SU_VELOCITY1 << i):
            cl_main.cl.mvelocity[0][i] = common.MSG_ReadChar() * 16
        else:
            cl_main.cl.mvelocity[0][i] = 0

    # C: vec3_t v_punchangles[2] -- [0] = current, [1] = previous
    _pv = getattr(view, 'v_punchangles', None)
    if not (isinstance(_pv, list) and len(_pv) >= 2
            and all(isinstance(x, list) and len(x) >= 3 for x in _pv)):
        view.v_punchangles = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

    if view.v_punchangles[0][0] != cl_main.cl.punchangle[0] or \
        view.v_punchangles[0][1] != cl_main.cl.punchangle[1] or \
        view.v_punchangles[0][2] != cl_main.cl.punchangle[2]:
        mathlib.VectorCopy(view.v_punchangles[0], view.v_punchangles[1])
        mathlib.VectorCopy(cl_main.cl.punchangle, view.v_punchangles[0])

    i = common.MSG_ReadLong()

    if cl_main.cl.items != i:
        sbar.Sbar_Changed()

        for j in range(32):
            if ( i & ( 1 << j)) and not ( cl_main.cl.items & ( 1 << j)):
                cl_main.cl.item_gettime[j] = cl_main.cl.time
        cl_main.cl.items = i

    cl_main.cl.onground = ( bits & protocol.SU_ONGROUND ) != 0
    cl_main.cl.inwater  = ( bits & protocol.SU_INWATER  ) != 0

    if bits & protocol.SU_WEAPONFRAME:
        cl_main.cl.stats[quakedef.STAT_WEAPONFRAME] = common.MSG_ReadByte()
    else:
        cl_main.cl.stats[quakedef.STAT_WEAPONFRAME] = 0

    if bits & protocol.SU_ARMOR:
        i = common.MSG_ReadByte()
    else:
        i = 0

    if cl_main.cl.stats[quakedef.STAT_ARMOR] != i:
        cl_main.cl.stats[quakedef.STAT_ARMOR] = i
        sbar.Sbar_Changed()

    if bits & protocol.SU_WEAPON:
        i = common.MSG_ReadByte()
    else:
        i = 0

    if cl_main.cl.stats[quakedef.STAT_WEAPON] != i:
        cl_main.cl.stats[quakedef.STAT_WEAPON] = i
        sbar.Sbar_Changed()

    i = common.MSG_ReadShort()
    if cl_main.cl.stats[quakedef.STAT_HEALTH] != i:
        cl_main.cl.stats[quakedef.STAT_HEALTH] = i
        sbar.Sbar_Changed()

    i = common.MSG_ReadByte()
    if cl_main.cl.stats[quakedef.STAT_AMMO] != i:
        cl_main.cl.stats[quakedef.STAT_AMMO] = i
        sbar.Sbar_Changed()

    for i in range(4):
        j = common.MSG_ReadByte()
        if cl_main.cl.stats[quakedef.STAT_SHELLS + i] != j:
            cl_main.cl.stats[quakedef.STAT_SHELLS + i] = j
            sbar.Sbar_Changed()

    i = common.MSG_ReadByte()

    if common.standard_quake:
        if cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] != i:
            cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] = i
            sbar.Sbar_Changed()
    else:
        if cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] != ( 1 << i ):
            cl_main.cl.stats[quakedef.STAT_ACTIVEWEAPON] = ( 1 << i )
            sbar.Sbar_Changed()

    if bits & protocol.SU_WEAPON2:
        cl_main.cl.stats[quakedef.STAT_WEAPON] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_ARMOR2:
        cl_main.cl.stats[quakedef.STAT_ARMOR] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_AMMO2:
        cl_main.cl.stats[quakedef.STAT_AMMO] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_SHELLS2:
        cl_main.cl.stats[quakedef.STAT_SHELLS] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_NAILS2:
        cl_main.cl.stats[quakedef.STAT_NAILS] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_ROCKETS2:
        cl_main.cl.stats[quakedef.STAT_ROCKETS] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_CELLS2:
        cl_main.cl.stats[quakedef.STAT_CELLS] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_WEAPONFRAME2:
        cl_main.cl.stats[quakedef.STAT_WEAPONFRAME] |= ( common.MSG_ReadByte() << 8)
    if bits & protocol.SU_WEAPONALPHA:
        cl_main.cl.viewent.alpha = common.MSG_ReadByte()
    else:
        cl_main.cl.viewent.alpha = protocol.ENTALPHA_DEFAULT


    if cl_main.cl.viewent.model != cl_main.cl.model_precache[cl_main.cl.stats[quakedef.STAT_WEAPON]]:
        cl_main.cl.viewent.lerpflags |= render.LERP_RESETANIM


def CL_NewTranslation( slot: int):
    if slot > cl_main.cl.maxclients:
        sys_sdl_unix.Sys_Error('CL_NewTranslation: slot > cl.maxclients')

    dest:   bytearray = bytearray()
    source: bytearray = bytearray()

    dest = cl_main.cl.scores[slot].translations
    source = gl_vidsdl._vid.colormap

    translation_size = len(cl_main.cl.scores[slot].translations)
    cl_main.cl.scores[slot].translations[:translation_size] = gl_vidsdl._vid.colormap[:translation_size]

    top = cl_main.cl.scores[slot].colors & 0xf0
    bottom = ( cl_main.cl.scores[slot].colors & 15 ) << 4

    gl_rmisc.R_TranslatePlayerSkin(slot)

    dest_offset = 0
    source_offset = 0

    for i in range(vid.VID_GRADES):
        # Copy 256 bytes from source to dest at current offsets
        dest[dest_offset : dest_offset + 256] = source[source_offset : source_offset + 256]

        # Increment offsets by 256
        dest_offset += 256
        source_offset += 256

        # TOP / SHIRT RANGE
        if top < 128:
            dest[render.TOP_RANGE : render.TOP_RANGE + 16] = source[top : top + 16]
        else:
            # Slice the 16 bytes and step backwards (-1) to reverse them
            dest[render.TOP_RANGE : render.TOP_RANGE + 16] = source[top : top + 16][::-1]

        # BOTTOM / PANTS RANGE
        if bottom < 128:
            dest[render.BOTTOM_RANGE : render.BOTTOM_RANGE + 16] = source[bottom : bottom + 16]
        else:
            # Slice the 16 bytes and step backwards (-1) to reverse them
            dest[render.BOTTOM_RANGE : render.BOTTOM_RANGE + 16] = source[bottom : bottom + 16][::-1]


def CL_ParseStatic(version: int):

    i = cl_main.cl.num_statics

    if i >= quakedef.MAX_STATIC_ENTITIES:
        host.Host_Error('Too many static entities')

    ent: render.entity_t = cl_main.cl_static_entities[i]

    cl_main.cl.num_statics += 1
    CL_ParseBaseline(ent, version)

    ent.model = cl_main.cl.model_precache[ent.baseline.modelindex]
    ent.lerpflags |= render.LERP_RESETANIM
    ent.frame = ent.baseline.frame

    ent.colormap = gl_vidsdl._vid.colormap
    ent.skinnum = ent.baseline.skin
    ent.effects = ent.baseline.effects
    ent.alpha = ent.baseline.alpha
    ent.scale = ent.baseline.scale
    mathlib.VectorCopy(ent.baseline.origin, ent.origin)
    mathlib.VectorCopy(ent.baseline.angles, ent.angles)

    import gl_refrag
    gl_refrag.R_AddEfrags(ent)


def CL_ParseStaticSound(version: int):
    org: list[float] = [0, 0, 0]

    for i in range(3):
        org[i] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

    if version == 2:
        sound_num = common.MSG_ReadShort()
    else:
        sound_num = common.MSG_ReadByte()

    vol = common.MSG_ReadByte()
    atten = common.MSG_ReadByte()

    snd_dma.S_StaticSound(cl_main.cl.sound_precache[sound_num], org, vol, atten)

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

        cmd = common.MSG_ReadByte()

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
                console.Con_Printf(f'{common.MSG_ReadString()}')

            case protocol.svc_centerprint:
                s = common.MSG_ReadString()
                gl_screen.SCR_CenterPrint(s)
                console.Con_LogCenterPrint(s)

            case protocol.svc_stufftext:
                _cmd.Cbuf_AddText(common.MSG_ReadString())

            case protocol.svc_damage:
                view.V_ParseDamage()

            case protocol.svc_serverinfo:
                CL_ParseServerInfo()
                gl_vidsdl._vid.recalc_refdef = True

            case protocol.svc_setangle:
                for i in range(3):
                    cl_main.cl.viewangles[i] = common.MSG_ReadAngle(cl_main.cl.protocolflags)

            case protocol.svc_setview:
                cl_main.cl.viewentity = common.MSG_ReadShort()

            case protocol.svc_lightstyle:
                i = common.MSG_ReadByte()
                if i >= quakedef.MAX_LIGHTSTYLES:
                    sys_sdl_unix.Sys_Error('svc_lightstyle > MAX_LIGHTSTYLES')

                cl_main.cl_lightstyle[i].map = common.MSG_ReadString()
                cl_main.cl_lightstyle[i].length = len(cl_main.cl_lightstyle[i].map)

                if cl_main.cl_lightstyle[i].length:
                    total = 0
                    cl_main.cl_lightstyle[i].peak = 'a'

                    for j in range(cl_main.cl_lightstyle[i].length):
                        total += ord(cl_main.cl_lightstyle[i].map[j]) - ord('a')
                        cl_main.cl_lightstyle[i].peak = max(cl_main.cl_lightstyle[i].peak, cl_main.cl_lightstyle[i].map[j])

                    cl_main.cl_lightstyle[i].average = total // cl_main.cl_lightstyle[i].length + ord('a')
                else:
                    cl_main.cl_lightstyle[i].peak = 'm'
                    cl_main.cl_lightstyle[i].average = ord('m')

            case protocol.svc_sound:
                CL_ParseStartSoundPacket()

            case protocol.svc_stopsound:
                i = common.MSG_ReadShort()
                snd_dma.S_StopSound(i >> 3, i & 7)

            case protocol.svc_updatename:
                sbar.Sbar_Changed()
                i = common.MSG_ReadByte()
                if i >= cl_main.cl.maxclients:
                    host.Host_Error('CL_ParseServerMessage: svc_updatename > MAX_SCOREBOARD')
                cl_main.cl.scores[i].name = common.MSG_ReadString()

            case protocol.svc_updatefrags:
                sbar.Sbar_Changed()
                i = common.MSG_ReadByte()
                if i >= cl_main.cl.maxclients:
                    host.Host_Error('CL_ParseServerMessage: svc_updatefrags > MAX_SCOREBOARD')
                cl_main.cl.scores[i].frags = common.MSG_ReadShort()

            case protocol.svc_updatecolors:
                sbar.Sbar_Changed()
                i = common.MSG_ReadByte()
                if i >= cl_main.cl.maxclients:
                    host.Host_Error('CL_ParseServerMessage: svc_updatecolors > MAX_SCOREBOARD')
                cl_main.cl.scores[i].colors = common.MSG_ReadByte ();

            case protocol.svc_particle:
                import r_part
                r_part.R_ParseParticleEffect()

            case protocol.svc_spawnbaseline:
                i = common.MSG_ReadShort()
                CL_ParseBaseline(CL_EntityNum(i), 1)

            case protocol.svc_spawnstatic:
                CL_ParseStatic(1)

            case protocol.svc_temp_entity:
                import cl_tent
                cl_tent.CL_ParseTEnt()

            case protocol.svc_setpause:
                cl_main.cl.paused = common.MSG_ReadByte()
                if cl_main.cl.paused:
                    pass

            case protocol.svc_signonnum:
                i = common.MSG_ReadByte()
                if i <= cl_main.cls.signon:
                    host.Host_Error('received signon %i when at %i' % ( i, cl_main.cls.signon))

                cl_main.cls.signon = i

                if i == 2:
                    if cl_main.cl.num_statics > 128:
                        console.Con_Warning('%i static entities exceeds standard limit of 128 (max = %d).\n' % (cl_main.cl.num_statics, quakedef.MAX_STATIC_ENTITIES))
                    import gl_refrag
                    gl_refrag.R_CheckEfrags()

                cl_main.CL_SignonReply()

            case protocol.svc_killedmonster:
                cl_main.cl.stats[quakedef.STAT_MONSTERS] += 1

            case protocol.svc_foundsecret:
                cl_main.cl.stats[quakedef.STAT_SECRETS] += 1

            case protocol.svc_updatestat:
                i = common.MSG_ReadByte()

                if i < 0 or i >= quakedef.MAX_CL_STATS:
                    sys_sdl_unix.Sys_Error('svc_updatestat %i is invalid' % i)

                cl_main.cl.stats[i] = common.MSG_ReadLong()

            case protocol.svc_spawnstaticsound:
                CL_ParseStaticSound(1)

            case protocol.svc_cdtrack:
                cl_main.cl.cdtrack = common.MSG_ReadByte()
                cl_main.cl.looptrack = common.MSG_ReadByte()
                print('case protocol.svc_cdtrack: not implemented')

            case protocol.svc_intermission:
                cl_main.cl.intermission = 1
                cl_main.cl.completed_time = cl_main.cl.time

                gl_vidsdl._vid.recalc_refdef = True
                view.V_RestoreAngles()

            case protocol.svc_finale:
                cl_main.cl.intermission = 2
                cl_main.cl.completed_time = cl_main.cl.time
                gl_vidsdl._vid.recalc_refdef = True

                s = common.MSG_ReadString()
                gl_screen.SCR_CenterPrint(s)
                console.Con_LogCenterPrint(s)

                view.V_RestoreAngles()

            case protocol.svc_cutscene:
                cl_main.cl.intermission = 3
                cl_main.cl.completed_time = cl_main.cl.time
                gl_vidsdl._vid.recalc_refdef = True

                s = common.MSG_ReadString()
                gl_screen.SCR_CenterPrint(s)
                console.Con_LogCenterPrint(s)

                view.V_RestoreAngles()

            case protocol.svc_sellscreen:
                _cmd.Cmd_ExecuteString('help', _cmd.cmd_source_t.src_command)

            case protocol.svc_skybox:
                import gl_sky
                gl_sky.Sky_LoadSkyBox(common.MSG_ReadString())

            case protocol.svc_bf:
                _cmd.Cmd_ExecuteString('bf', _cmd.cmd_source_t.src_command)

            case protocol.svc_fog:
                import gl_fog
                gl_fog.Fog_ParseServerMessage()

            case protocol.svc_spawnbaseline2:
                i = common.MSG_ReadShort()
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


