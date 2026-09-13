#sv_main.py

import _cmd
import bspfile
import common
import console
import cvar
import gl_model
import gl_screen
import glquake
import host
import host_cmd
import mathlib
import net_defs
import net_main
import pr_edict
import pr_exec
import progs
import protocol
import quakedef
import server
import sv_main
import sv_phys
import sys_sdl_unix
import world

sv : server.server_t        = None
svs: server.server_static_t = server.server_static_t()

localmodels = []

sv_protocol = protocol.PROTOCOL_FITZQUAKE

SIGNON_SIZE = 31500

def SV_Protocol_f():
    match ( _cmd.Cmd_Argc()):
        case 1:
            console.Con_Printf(f'sv_protocol is {sv_protocol}')


def SV_Init():
    global sv
    sv = server.server_t()
    sv.edicts = None

    sv_freezenonclients = {'name': 'sv_freezenonclients', 'value': '0',    'flags' : cvar.CVAR_NONE}
    sv_friction         = {'name': 'sv_friction',         'value': '4',    'flags' : cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
    sv_gravity          = {'name': 'sv_gravity',          'value': '800',  'flags' : cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
    sv_maxvelocity      = {'name': 'sv_maxvelocity',      'value': '2000', 'flags' : cvar.CVAR_NONE}
    sv_nostep           = {'name': 'sv_nostep',           'value': '0',    'flags' : cvar.CVAR_NONE}
    sv_stopspeed        = {'name': 'sv_stopspeed',        'value': '100',  'flags' : cvar.CVAR_NONE}

    sv_edgefriction     = {'name': 'edgefriction',        'value': '2',    'flags': cvar.CVAR_NONE}
    sv_idealpitchscale  = {'name': 'sv_idealpitchscale',  'value':'0.8',   'flags': cvar.CVAR_NONE}
    sv_altnoclip        = {'name': 'sv_altnoclip',        'value':'1',     'flags': cvar.CVAR_ARCHIVE}
    sv_maxspeed         = {'name': 'sv_maxspeed',         'value':'320',   'flags': cvar.CVAR_NOTIFY|cvar.CVAR_SERVERINFO}
    sv_accelerate       = {'name': 'sv_accelerate',       'value':'10',    'flags': cvar.CVAR_NONE}

    sv_aim              = {'name':'sv_aim',               'value':'1',     'flags': cvar.CVAR_NONE}

    cvar.Cvar_RegisterVariable(sv_maxvelocity)
    cvar.Cvar_RegisterVariable(sv_gravity)
    cvar.Cvar_RegisterVariable(sv_friction)

    cvar.Cvar_SetCallback(sv_gravity, host.Host_Callback_Notify)
    cvar.Cvar_SetCallback(sv_friction, host.Host_Callback_Notify)

    cvar.Cvar_RegisterVariable(sv_edgefriction)
    cvar.Cvar_RegisterVariable(sv_stopspeed)
    cvar.Cvar_RegisterVariable(sv_maxspeed)

    cvar.Cvar_SetCallback(sv_maxspeed, host.Host_Callback_Notify)

    cvar.Cvar_RegisterVariable(sv_accelerate)
    cvar.Cvar_RegisterVariable(sv_idealpitchscale)

    cvar.Cvar_RegisterVariable(sv_aim)
    cvar.Cvar_RegisterVariable(sv_nostep)
    cvar.Cvar_RegisterVariable(sv_freezenonclients)
    cvar.Cvar_RegisterVariable(sv_altnoclip)

    _cmd.Cmd_AddCommand('sv_protocol', SV_Protocol_f)

    global localmodels
    for i in range(quakedef.MAX_MODELS):
        localmodels.insert(i, f'*{i}')

    global sv_protocol
    i = common.COM_CheckParm('-protocol')

    if i != 0 and i < com_argc - 1:
        sv_protocol = int(com_argv[i + 1])

    p = ''
    match sv_protocol:
        case protocol.PROTOCOL_NETQUAKE:
            p = 'NetQuake'
        case protocol.PROTOCOL_FITZQUAKE:
            p = 'FitzQuake'
        case protocol.PROTOCOL_RMQ:
            p = 'RMQ'
        case _:
            Sys_Error(f'Bad protocol {sv_protocol}, accepted values {protocol.PROTOCOL_NETQUAKE}, {protocol.PROTOCOL_FITZQUAKE}, {protocol.PROTOCOL_RMQ}')
            return

    sys_sdl_unix.Sys_Printf(f'Server using protocol {sv_protocol} {p}')

def SV_StartParticle(org: list[float], dir: list[float], color: int, count: int):
    if sv_main.sv.datagram.cursize > quakedef.MAX_DATAGRAM - 18:
        return

    common.MSG_WriteByte(sv_main.sv.datagram, protocol.svc_particle)
    common.MSG_WriteCoord(sv_main.sv.datagram, org[0], sv_main.sv.protocolflags)
    common.MSG_WriteCoord(sv_main.sv.datagram, org[1], sv_main.sv.protocolflags)
    common.MSG_WriteCoord(sv_main.sv.datagram, org[2], sv_main.sv.protocolflags)

    for i in range(3):
        v = dir[i] * 16
        if v > 127:
            v = 127
        elif v < -128:
            v = -128
        common.MSG_WriteChar(sv_main.sv.datagram, v)

    common.MSG_WriteByte(sv_main.sv.datagram, count)
    common.MSG_WriteByte(sv_main.sv.datagram, color)



def SV_StartSound(entity: progs.edict_t, channel: int, sample: str, volume: int, attenuation: float):
    if volume < 0 or volume > 255:
        host.Host_Error('SV_StartSound: volume = %i', volume)
    if attenuation < 0 or attenuation > 4.0:
        host.Host_Error('SV_StartSound: attenuation = %f', attenuation)
    if channel < 0 or channel > 7:
        host.Host_Error('SV_StartSound: channel = %i', channel)

    if sv_main.sv.datagram.cursize > quakedef.MAX_DATAGRAM - 21:
        return

    for sound_num in range(quakedef.MAX_SOUNDS):
        if not sv_main.sv.sound_precache[sound_num]:
            break
        if sample == sv_main.sv.sound_precache[sound_num]:
            break

    if sound_num == quakedef.MAX_SOUNDS or not sv_main.sv.sound_precache[sound_num]:
        console.Con_Printf('SV_StartSound: %s not precached\n' % sample)
        return

    ent = pr_edict.NUM_FOR_EDICT(entity)
    field_mask = 0
    if volume != protocol.DEFAULT_SOUND_PACKET_VOLUME:
        field_mask |= protocol.SND_VOLUME
    if attenuation != protocol.DEFAULT_SOUND_PACKET_ATTENUATION:
        field_mask |= protocol.SND_ATTENUATION

    if ent >= 8192:
        if sv_main.sv.protocol == protocol.PROTOCOL_NETQUAKE:
            return
        field_mask |= protocol.SND_LARGEENTITY

    if sound_num >= 256 or channel >= 8:
        if sv_main.sv.protocol == protocol.PROTOCOL_NETQUAKE:
            return
        field_mask |= protocol.PROTOCOL_NETQUAKE

    if sv_main.sv.datagram.cursize > quakedef.MAX_DATAGRAM - 21:
        return

    common.MSG_WriteByte(sv_main.sv.datagram, protocol.svc_sound)
    common.MSG_WriteByte(sv_main.sv.datagram, field_mask)

    if field_mask & protocol.SND_VOLUME:
        common.MSG_WriteByte(sv_main.sv.datagram, volume)
    if field_mask & protocol.SND_ATTENUATION:
        common.MSG_WriteByte(sv_main.sv.datagram, attenuation * 64)

    if field_mask & protocol.SND_LARGEENTITY:
        common.MSG_WriteShort(sv_main.sv.datagram, ent)
        common.MSG_WriteByte(sv_main.sv.datagram, channel)
    else:
        common.MSG_WriteShort(sv_main.sv.datagram, (ent<<3) | channel)

    if field_mask & protocol.SND_LARGESOUND:
        common.MSG_WriteShort(sv_main.sv.datagram, sound_num)
    else:
        common.MSG_WriteByte(sv_main.sv.datagram, sound_num)

    for i in range(3):
        common.MSG_WriteCoord (sv_main.sv.datagram, entity.v.origin[i]+0.5*(entity.v.mins[i]+entity.v.maxs[i]), sv_main.sv.protocolflags)

def SV_LocalSound(client: server.client_t, sample: str):
    for sound_num in range(quakedef.MAX_SOUNDS):
        if not sv_main.sv.sound_precache[sound_num]:
            break
        if sample == sv_main.sv.sound_precache[sound_num]:
            break

    if sound_num == quakedef.MAX_SOUNDS or not sv_main.sv.sound_precache[sound_num]:
        console.Con_Printf('SV_LocalSound: %s not precached\n' % sample)
        return

    field_mask = 0
    if sound_num >= 256:
        if sv_main.sv.protocol == protocol.PROTOCOL_NETQUAKE:
            return
        field_mask = protocol.SND_LARGESOUND

    if client.message.cursize > client.message.maxsize - 4:
        return

    common.MSG_WriteByte(client.message, protocol.svc_localsound)
    common.MSG_WriteByte(client.message, field_mask)

    if field_mask & protocol.SND_LARGESOUND:
        common.MSG_WriteShort(client.message, sound_num)
    else:
        common.MSG_WriteByte(client.message, sound_num)


def SV_IsLocalClient(client: server.client_t) -> bool:
    return net_main.NET_QSocketGetAddressString(client.netconnection) == 'LOCAL'


def SV_SendServerInfo(client: server.client_t):
    common.MSG_WriteByte(client.message, protocol.svc_print)
    message = '%c\nQuakeSpasm %1.2f SERVER' %  ( 2, quakedef.QUAKESPASM_VERSION )
    common.MSG_WriteString(client.message, message)

    common.MSG_WriteByte(client.message, protocol.svc_serverinfo)
    common.MSG_WriteLong(client.message, sv_main.sv.protocol)

    if sv_main.sv.protocol == protocol.PROTOCOL_RMQ:
        common.MSG_WriteLong( client.message, sv_main.sv.protocolflags)

    common.MSG_WriteByte(client.message, sv_main.svs.maxclients)

    coop = cvar.Cvar_GetCvar('coop').value
    deathmatch = cvar.Cvar_GetCvar('deathmatch').value

    if not coop and deathmatch:
        common.MSG_WriteByte(client.message, protocol.GAME_DEATHMATCH)
    else:
        common.MSG_WriteByte(client.message, protocol.GAME_COOP)

    common.MSG_WriteString(client.message, pr_edict.PR_GetString(sv_main.sv.edicts.v.message))

    i = i
    s = sv_main.sv.model_precache[i]
    while s:
        if sv_main.sv.protocol != protocol.PROTOCOL_NETQUAKE or i < 256:
            common.MSG_WriteString(client.message, s)
        i += 1
        s = sv_main.sv.model_precache[i]
    common.MSG_WriteByte(client.message, 0)

    i = i
    s = sv_main.sv.sound_precache[i]
    while s:
        if sv_main.sv.protocol != protocol.PROTOCOL_NETQUAKE or i < 256:
            common.MSG_WriteString(client.message, s)
        i += 1
        s = sv_main.sv.sound_precache[i]
    common.MSG_WriteByte(client.message, 0)

    common.MSG_WriteByte(client.message, protocol.svc_cdtrack )
    common.MSG_WriteByte(client.message, sv_main.sv.edicts.v.sounds)
    common.MSG_WriteByte(client.message, sv_main.sv.edicts.v.sounds)

    common.MSG_WriteByte(client.message, protocol.svc_setview)
    common.MSG_WriteShort(client.message, pr_edict.NUM_FOR_EDICT(client.edict))

    common.MSG_WriteByte(client.message, protocol.svc_signonnum)
    common.MSG_WriteByte(client.message, 1)

    client.sendsignon = server.PRESPAWN_FLUSH
    client.spawned = False

def SV_ConnectClient(clientnum: int):
    client: server.client_t = sv_main.svs.clients[clientnum]

    console.Con_DPrintf('Client %s connected\n' % net_main.NET_QSocketGetAddressString(client.netconnection))

    edictnum = clientnum + 1

    ent = pr_edict.EDICT_NUM(edictnum)

    netconnection = client.netconnection

    spawn_parms = []
    if sv_main.sv.loadgame:
        spawn_parms = client.spawn_parms[:]

    client.name = 'unconnected'
    client.active = True
    client.spawned = False
    client.edict = ent
    client.message.data = client.msgbuf
    client.message.allowoverflow = True

    if sv_main.sv.loadgame:
        client.spawn_parms = spawn_parms[:]
    else:
        pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.SetNewParms)
        for i in range ( server.NUM_SPAWN_PARMS ):
            client.spawn_parms[i] = pr_edict.pr_global_struct.parm1[i]

    SV_SendServerInfo(client)

sv_active = False

def SV_CheckForNewClients():
    ret: net_defs.qsocket_t = None

    while True:
        ret = net_main.NET_CheckNewConnections()
        if ret is None:
            break

        for i in range(svs.maxclients):
            if not svs.clients[i].active:
                break

            if i == svs.maxclients:
                sys_sdl_unix.Sys_Error('Host_CheckForNewClients: no free clients')

            svs.clients[i].netconnection = ret
            SV_ConnectClient(i)

            net_main.net_activeconnections += 1

def SV_ClearDatagram():
    common.SZ_Clear(sv.datagram)


fatbytes: int = 0
fatpvs: bytearray = bytearray()
fatpvs_capacity: int = 0

def SV_AddToFatPVS(org: list[float], node: quakedef.mnode_t, worldmodel: quakedef.qmodel_t):
    global fatpvs

    pvs: bytearray = None
    plane: quakedef.mplane_t = None

    while True:
        if node.contents < 0:
            if node.contents != bspfile.CONTENTS_SOLID:
                pvs = gl_model.Mod_LeadPVS(node, worldmodel)
                for i in range(fatbytes):
                    fatpvs[i] |= pvs[i]

            return

        plane = node.plane
        d = mathlib.DotProduct(org, plane.normal) - plane.dist
        if d > 8:
            node = node.children[0]
        elif d < -8:
            node = node.children[1]
        else:
            SV_AddToFatPVS(org, node.children[0], worldmodel)
            node = node.children[1]

def SV_FatPVS(org: list[float], worldmodel: quakedef.qmodel_t) -> bytes:
    global fatpvs

    fatbytes = ( worldmodel.numleafs + 7 ) >> 3
    if fatpvs is None or fatbytes > fatpvs_capacity:
        fatpvs_capacity = fatbytes
        fatpvs = bytearray(fatpvs_capacity)
        if fatpvs is None:
            sys_sdl_unix.Sys_Error('SV_FatPVS: realloc() failed on %d bytes' % fatpvs_capacity)

    # Q_memset ( fat_pvs, 0, fatbytes);
    SV_AddToFatPVS(org, worldmodel.nodes, worldmodel)
    return fatpvs

def SV_VisibleToClient(client: progs.edict_t, test: progs.edict_t, worldmodel: quakedef.qmodel_t) -> bool:
    org: list[float] = [0, 0, 0]
    mathlib.VectorAdd(client.v.origin, client.v.view_ofs, org)
    pvs = SV_FatPVS(org, worldmodel)

    for i in range(test.num_leafs):
        if pvs[test.leafnums[i] >> 3] & ( 1 << ( test.leafnums[i] & 7)) :
            return True
    return False


def SV_WriteEntitiesToClient(clent: progs.edict_t, msg: common.sizebuf_s): # not client?
    org: list[float] = [0, 0, 0]
    mathlib.VectorAdd(clent.v.origin, clent.v.view_ofs, org)
    pvs = SV_FatPVS(org, sv.worldmodel)
    val: progs.eval_t = None

    gotostats = False

    ent = progs.NEXT_EDICT(sv.edicts)
    for e in range(1, sv.num_edicts):
        if not ent is clent:
            if not ent.v.modelindex or not pr_edict.PR_GetString(ent.v.model)[0]:
                continue

            if sv.protocol == protocol.PROTOCOL_NETQUAKE and int(ent.v.modelindex) & 0xFF00:
                continue

            for i in range(ent.num_leafs):
                if pvs[ent.leafnums[i] >> 3] & ( 1 << (ent.leafnums[i] & 7)):
                    break

            if i == ent.num_leafs and ent.num_leafs < progs.MAX_ENT_LEAFS:
                continue

        if msg.cursize + 40 > msg.maxsize:
            if not host.dev_overflows.packetsize or  host.dev_overflows.packetsize + glquake.CONSOLE_RESPAM_TIME < host.realtime:
                console.Con_Printf('packet overflow\n')
                host.dev_overflows.packetsize = host.realtime
            gotostats = True
            break

        bits = 0

        for i in range(3):
            miss = ent.v.origin[i]  - ent.baseline.origin[i]
            if miss < -0.1 or miss > 0.1:
                bits |= protocol.U_ORIGIN1

        if ent.v.angles[0] != ent.baseline.angles[0]:
            bits |= protocol.U_ANGLE1
        if ent.v.angles[1] != ent.baseline.angles[1]:
            bits |= protocol.U_ANGLE2
        if ent.v.angles[2] != ent.baseline.angles[2]:
            bits |= protocol.U_ANGLE3
        if ent.v.movetype == server.MOVETYPE_STEP:
            bits |= protocol.U_STEP # don't mess up the step animation
        if ent.baseline.colormap != ent.v.colormap:
            bits |= protocol.U_COLORMAP
        if ent.baseline.skin != ent.v.skin:
            bits |= protocol.U_SKIN
        if ent.baseline.frame != ent.v.frame:
            bits |= protocol.U_FRAME
        if (ent.baseline.effects ^ int(ent.v.effects)) & pr_edict.pr_effects_mask:
            bits |= protocol.U_EFFECTS
        if ent.baseline.modelindex != ent.v.modelindex:
            bits |= protocol.U_MODEL

        if pr_edict.pr_alpha_supported:
            val = pr_edict.GetEdictFieldValue(ent, 'alpha')
            if val:
                ent.alpha = protocol.ENTALPHA_ENCODE(val._float)

        if ent.alpha == protocol.ENTALPHA_ZERO and not int(ent.v.effects & pr_edict.pr_effects_mask):
            continue

        val = pr_edict.GetEdictFieldValue(ent, 'scale')
        if val:
            ent.scale = protocol.ENTSCALE_ENCODE(val._float)
        else:
            ent.scale = protocol.ENTSCALE_DEFAULT

        if sv.protocol != protocol.PROTOCOL_NETQUAKE:
            if (ent.baseline.alpha != ent.alpha): bits |= protocol.U_ALPHA
            if (ent.baseline.scale != ent.scale): bits |= protocol.U_SCALE
            if bits & protocol.U_FRAME and int(ent.v.frame & 0xFF00): bits |= protocol.U_FRAME2
            if bits & protocol.U_MODEL and int(ent.v.modelindex & 0xFF00): bits |= protocol.U_MODEL2
            if (ent.sendinterval): bits |= protocol.U_LERPFINISH
            if (bits >= 65536): bits |= protocol.U_EXTEND1
            if (bits >= 16777216): bits |= protocol.U_EXTEND2

        if e >= 256:
            bits |= protocol.U_LONGENTITY

        if bits >= 256:
            bits |= protocol.U_MOREBITS

        common.MSG_WriteByte(msg, bits | protocol.U_SIGNAL)

        if bits & protocol.U_MOREBITS:
            common.MSG_WriteByte(msg, bits >> 8)

        if (bits & protocol.U_EXTEND1):
            MSG_WriteByte(msg, bits>>16)
        if (bits & protocol.U_EXTEND2):
            MSG_WriteByte(msg, bits>>24)
        #johnfitz

        if (bits & protocol.U_LONGENTITY):
            MSG_WriteShort (msg,e)
        else:
            MSG_WriteByte (msg,e)

        if (bits & protocol.U_MODEL):
            MSG_WriteByte (msg, ent.v.modelindex)
        if (bits & protocol.U_FRAME):
            MSG_WriteByte (msg, ent.v.frame)
        if (bits & protocol.U_COLORMAP):
            MSG_WriteByte (msg, ent.v.colormap)
        if (bits & protocol.U_SKIN):
            MSG_WriteByte (msg, ent.v.skin)
        if (bits & protocol.U_EFFECTS):
            MSG_WriteByte (msg, int(ent.v.effects & pr_effects_mask))
        if (bits & protocol.U_ORIGIN1):
            MSG_WriteCoord (msg, ent.v.origin[0], sv.protocolflags)
        if (bits & protocol.U_ANGLE1):
            MSG_WriteAngle(msg, ent.v.angles[0], sv.protocolflags)
        if (bits & protocol.U_ORIGIN2):
            MSG_WriteCoord (msg, ent.v.origin[1], sv.protocolflags)
        if (bits & protocol.U_ANGLE2):
            MSG_WriteAngle(msg, ent.v.angles[1], sv.protocolflags)
        if (bits & protocol.U_ORIGIN3):
            MSG_WriteCoord (msg, ent.v.origin[2], sv.protocolflags)
        if (bits & protocol.U_ANGLE3):
            MSG_WriteAngle(msg, ent.v.angles[2], sv.protocolflags)

        #johnfitz -- PROTOCOL_FITZQUAKE
        if (bits & protocol.U_ALPHA):
            MSG_WriteByte(msg, ent.alpha)
        if (bits & protocol.U_SCALE):
            MSG_WriteByte(msg, ent.scale)
        if (bits & protocol.U_FRAME2):
            MSG_WriteByte(msg, int(ent.v.frame >> 8))
        if (bits & protocol.U_MODEL2):
            MSG_WriteByte(msg, int(ent.v.modelindex >> 8))
        if (bits & protocol.U_LERPFINISH):
            MSG_WriteByte(msg, (byte)(Q_rint((ent.v.nextthink-sv.time)*255)))

        ent = progs.NEXT_EDICT(ent)

# stats:
    if msg.cursize > 1024 and host.dev_peakstats.packetsize <= 1024:
        console.Con_DPrintf('%i byhte packet exceeds standard limit of 1024 (max = %d),\n' % (msg.cursize, msg.maxsize))
        host.dev_stats.packetsize = msg.cursize
        host.dev_peakstats.packetsize = max(msg.cursize, host.dev_peakstats.packetsize)


def SV_CleanupEnts():
    ent: progs.edict_t = progs.NEXT_EDICT(sv.edicts)
    for e in range(1, sv.num_edicts):
        ent.v.effects = ent.v.effects & ~server.EF_MUZZLEFLASH
        ent = progs.NEXT_EDICT(ent)


def SV_WriteClientdataToMessage(ent: progs.edict_t, msg: common.sizebuf_s):
    other: progs.edict_t = None
    val: progs.eval_t = None

    if ent.v.dmg_take or ent.v.dmg_save:
        other = progs.PROG_TO_EDICT(ent.v.dmg_inflictor)
        common.MSG_WriteByte(msg, protocol.svc_damage)
        common.MSG_WriteByte(msg, ent.v.dmg_save)
        common.MSG_WriteByte(msg, ent.v.dmg_take)

        for i in range(3):
            common.MSG_WriteCoord(msg, other.v.origin[i]+ 0.5*(other.v.mins[i] + other.v.maxs[i]), sv.protocolflags )

        ent.v.dmg_take = 0
        ent.v.dmg_save = 0

    SV_SetIdealPitch()

    if ent.v.fixangle:
        common.MSG_WriteByte(msg, protocol.svc_setangle)
        for i in range(3):
            common.MSG_WriteAngle(msg, ent.v.angles[i], sv.protocolflags)
        ent.v.fixangle = 0

    bits = 0

    if ent.v.view_ofs[2] != protocol.DEFAULT_VIEWHEIGHT:
        bits |= protocol.SU_VIEWHEIGHT

    if ent.v.idealpitch:
        bits |= protocol.SU_IDEALPITCH

    val = pr_edict.GetEdictFieldValue(ent, 'items2')

    if val:
        items = int(ent.v.items) | int(val._float << 23)
    else:
        items = int(ent.v.items) | int(pr_edict.pr_global_struct.serverflags << 28)

    bits |= protocol.SU_ITEMS

    if int(ent.v.flags) & server.FL_ONGROUND:
        bits |= protocol.SU_ONGROUND

    if ent.v.waterlevel >= 2:
        bits |= protocol.SU_INWATER

    for i in range(3):
        if ent.v.punchangle[i]:
            bits |= ( protocol.SU_PUNCH1 << i )
        if ent.v.velocity[i]:
            bits |= ( protocol.SU_VELOCITY1 << i )

    if ent.v.weaponframe:
        bits |= protocol.SU_WEAPONFRAME

    if ent.v.armorvalue:
        bits |= protocol.SU_ARMOR

    bits |= protocol.SU_WEAPON

    if sv.protocol != protocol.PROTOCOL_NETQUAKE:
        if bits & protocol.SU_WEAPON and SV_ModelIndex(PR_GetString(ent.v.weaponmodel)) & 0xFF00:
            bits |= protocol.SU_WEAPON2
        if int(ent.v.armorvalue) & 0xFF00:
            bits |= protocol.SU_ARMOR2
        if int(ent.v.currentammo) & 0xFF00:
            bits |= protocol.SU_AMMO2
        if int(ent.v.ammo_shells) & 0xFF00:
            bits |= protocol.SU_SHELLS2
        if int(ent.v.ammo_nails) & 0xFF00:
            bits |= protocol.SU_NAILS2
        if int(ent.v.ammo_rockets) & 0xFF00:
            bits |= protocol.SU_ROCKETS2
        if int(ent.v.ammo_cells) & 0xFF00:
            bits |= protocol.SU_CELLS2
        if bits & protocol.SU_WEAPONFRAME and int(ent.v.weaponframe) & 0xFF00:
            bits |= protocol.SU_WEAPONFRAME2
        if bits & protocol.SU_WEAPON and ent.alpha != protocol.ENTALPHA_DEFAULT:
            bits |= protocol.SU_WEAPONALPHA
        if bits >= 65536:
            bits |= protocol.SU_EXTEND1
        if bits >= 16777216:
            bits |= protocol.SU_EXTEND2

    common.MSG_WriteByte(msg, protocol.svc_clientdata)
    common.MSG_WriteShort(msg, bits)

    if bits & protocol.SU_EXTEND1:
        common.MSG_WriteByte(msg, bits >> 16)
    if bits & protocol.SU_EXTEND2:
        common.MSG_WriteByte(msg, bits >> 24 )

    if bits & protocol.SU_VIEWHEIGHT:
        common.MSG_WriteChar(msg, ent.v.view_ofs[2])

    if bits & protocol.SU_IDEALPITCH:
        common.MSG_WriteChar(msg, ent.v.idealpitch)

    for i in range(3):
        if bits & ( protocol.SU_PUNCH1 << 1):
            common.MSG_WriteChar(msg, ent.v.punchangle[i])
        if bits & ( protocol.SU_VELOCITY1 << 1 ):
            common.MSG_WriteChar(msg, ent.v.velocity[i] / 16)

    common.MSG_WriteLong(msg, items)

    if bits & protocol.SU_WEAPONFRAME:
        common.MSG_WriteByte(msg, ent.v.weaponframe)
    if bits & protocol.SU_ARMOR:
        common.MSG_WriteByte(msg, ent.v.armorvalue)
    if bits & protocol.SU_WEAPON:
        common.MSG_WriteByte (msg, SV_ModelIndex(PR_GetString(ent.v.weaponmodel)))

    MSG_WriteShort (msg, ent.v.health)
    MSG_WriteByte (msg, ent.v.currentammo)
    MSG_WriteByte (msg, ent.v.ammo_shells)
    MSG_WriteByte (msg, ent.v.ammo_nails)
    MSG_WriteByte (msg, ent.v.ammo_rockets)
    MSG_WriteByte (msg, ent.v.ammo_cells)

    if common.standard_quake:
        common.MSG_WriteByte(msg, ent.v.weapon)
    else:
        for i in range(32):
            if int(ent.v.weapon) & ( 1 << i ):
                common.MSG_ReadByte(msg, i)
                break

    if bits & protocol.SU_WEAPON2:
        common.MSG_WriteByte (msg, SV_ModelIndex(PR_GetString(ent.v.weaponmodel)) >> 8)
    if bits & protocol.SU_ARMOR2:
        common.MSG_WriteByte (msg, int(ent.v.armorvalue) >> 8)
    if bits & protocol.SU_AMMO2:
        common.MSG_WriteByte (msg, int(ent.v.currentammo) >> 8)
    if bits & protocol.SU_SHELLS2:
        common.MSG_WriteByte (msg, int(ent.v.ammo_shells) >> 8)
    if bits & protocol.SU_NAILS2:
        common.MSG_WriteByte (msg, int(ent.v.ammo_nails) >> 8)
    if bits & protocol.SU_ROCKETS2:
        common.MSG_WriteByte (msg, int(ent.v.ammo_rockets) >> 8)
    if bits & protocol.SU_CELLS2:
        common.MSG_WriteByte (msg, int(ent.v.ammo_cells) >> 8)
    if bits & protocol.SU_WEAPONFRAME2:
        common.MSG_WriteByte (msg, int(ent.v.weaponframe) >> 8)
    if bits & protocol.SU_WEAPONALPHA:
        common.MSG_WriteByte (msg, ent.alpha)


def SV_SendClientDatagram(client: server.client_t) -> bool:

    buf = bytearray(quakedef.MAX_DATAGRAM)
    msg: common.sizebuf_s = common.sizebuf_s()

    msg.data = buf
    msg.maxsize = quakedef.MAX_DATAGRAM
    msg.cursize = 0

    if net_main.NET_QSocketGetAddressString(client.netconnection) == 'LOCAL':
        msg.maxsize = quakedef.DATAGRAM_MTU

    common.MSG_WriteByte(msg, protocol.svc_time)
    common.MSG_WriteFloat(msg, sv.time)

    SV_WriteClientdataToMessage(client.edict, msg)
    SV_WriteEntitiesToClient(client.edict, msg)

    if msg.cursize + sv.datagram.cursize < msg.maxsize:
        common.SZ_Write(msg, sv.datagram.data, sv.datagram.cursize)

    if net_main.NET_SendUnreliableMessage(client.netconnection, msg) == -1:
        host.SV_DropClient(True)
        return False

    return True

def SV_UpdateToReliableMessages():
    client: server.client_t = None

    for i in range (svs.maxclients):
        host.host_client = svs.clients[i]
        if host.host_client.old_frags != host.host_client.v.frags:
            for j in range (svs.maxclients):
                client = svs.clients[j]
                if not client.active:
                    continue
                common.MSG_WriteByte(client.message, protocol.svc_updatefrags)
                common.MSG_WriteByte(client.message, i)
                common.MSG_WriteShort(client.message, host.host_client.edict.v.frags)

            host.host_client.old_frags = host.host_client.edict.v.frags

    for j in range(svs.maxclients):
        client = svs.clients[j]
        if not client.active:
            continue
        common.SZ_Write(client.message, sv.reliable_datagram.data, sv.reliable_datagram.cursize)

    common.SZ_Clear(sv.reliable_datagram)

def SV_SendNop(client: server.client_t):
    msg: common.sizebuf_s = common.sizebuf_s()
    buf = bytearray(4)

    msg.data = buf
    msg.maxsize = 4
    msg.cursize = 0

    common.MSG_WriteChar(msg, protocol.svc_nop)

    if net_main.NET_SendUnreliableMessage(client.netconnection, msg) == -1:
        host.SV_DropClient(true)
    client.last_message = host.realtime


def SV_SendClientMessages():

    local: bool = False

    SV_UpdateToReliableMessages()

    for i in range(svs.maxclients):
        host.host_client = svs.clients[i]
        if not host.host_client.active:
            continue
        if host.host_client.spawned:
            if not SV_SendClientDatagram(host.host_client):
                continue
        else:
            if not host.host_client.sendsignon:
                if host.realtime - host.host_client.last_message > 5:
                    SV_SendNop(host.host_client)
                continue
            if host.host_client.sendsignon == server.sendsignon_e.PRESPAWN_SIGNONBUFS:
                local = SV_IsLocalClient(host.host_client)
                while host.host_client.signonidx < sv.num_signon_buffers:
                    signon: common.sizebuf_s = sv.signon_buffers[host.host_client.signonidx]
                    if host.host_client.message.cursize + signon.cursize > host.host_client.message.maxsize:
                        break

                    common.SZ_Write(host.host_client.message, signon.data, signon.cursize)
                    host.host_client.signonidx += 1

                    if not local:
                        break

                if host.host_client.signonidx == sv.num_signon_buffers:
                    host.host_client.sendsignon = server.sendsignon_e.PRESPAWN_SIGNONMSG

            if host.host_client.sendsignon == server.sendsignon_e.PRESPAWN_SIGNONMSG:
                if host.host_client.message.cursize + 2 < host.host_client.message.maxsize:
                    common.MSG_WriteByte(host.host_client.message, protocol.svc_signonnum)
                    common.MSG_WriteByte(host.host_client.message, 2)
                    host.host_client.sendsignon = server.sendsignon_e.PRESPAWN_FLUSH

        if host.host_client.message.overflowed:
            host.SV_DropClient(True)
            host.host_client.message.overflowed = False
            continue

        if host.host_client.message.cursize or host.host_client.dropasap:
            if not net_main.NET_CanSendMessage(host.host_client.netconnection):
                continue

            if host.host_client.dropasap:
                host.SV_DropClient(False)
            else:
                if net_main.NET_SendMessage(host.host_client.netconnection, host.host_client.message) == -1:
                    host.SV_DropClient(True)

                common.SZ_Clear(host.host_client.message)
                host.host_client.last_message = host.realtime

                if host.host_client.sendsignon == server.sendsignon_e.PRESPAWN_FLUSH:
                    host.host_client.sendsignon = server.sendsignon_e.PRESPAWN_DONE

    SV_CleanupEnts()


def SV_AddSignonBuffer():
    if sv.num_signon_buffers >= server.MAX_SIGNON_BUFFERS:
        host.Host_Error('SV_AddSignonBuffer overflow\n')

    sb : common.sizebuf_s = common.sizebuf_s()
    sb.data = bytearray(SIGNON_SIZE)
    sb.maxsize = SIGNON_SIZE
    sv.signon_buffers[sv.num_signon_buffers] = sb
    sv.num_signon_buffers += 1
    sv.signon = sb


def SV_ReserveSignonSpace(numbytes: int):
    if sv.signon.cursize + numbytes > sv.signon.maxsize:
        SV_AddSignonBuffer()


def SV_ModelIndex(name: str) -> int:
    if not name or name == '':
        return 0

    for i in range(quakedef.MAX_MODELS):
        if not sv.model_precache[i]:
            break
        if sv.model_precache[i] == name:
            return i
    if i == quakedef.MAX_MODELS or not sv.model_precache[i]:
        sys_sdl_unix.Sys_Error('SV_ModelIndex-: model %s not precached\n' % name)
    return i

def SV_CreateBaseline():
    svent: progs.edict_t = None

    for entnum in range(sv.num_edicts):
        svent = pr_edict.EDICT_NUM(entnum)
        if svent.free:
            continue
        if entnum > svs.maxclients and not svent.v.modelindex:
            continue

        mathlib.VectorCopy(svent.v.origin, svent.baseline.origin)
        mathlib.VectorCopy(svent.v.angles, svent.baseline.angles)
        svent.baseline.frame = svent.v.frame
        svent.baseline.skin = svent.v.skin

        if entnum > 0 and entnumn <= svs.maxclients:
            svent.baseline.colormap = entnum
            svent.baseline.modelindex = SV_ModelIndex('progs/player.mdl')
            svent.baseline.alpha = protocol.ENTALPHA_DEFAULT
            svent.baseline.scale = protocol.ENTSCALE_DEFAULT
        else:
            svent.baseline.colormap = 0
            svent.baseline.modelindex = SV_ModelIndex(pr_edict.PR_GetString(svent.v.model))
            svent.baseline.alpha = svent.alpha
            svent.baseline.scale = protocol.ENTSCALE_DEFAULT
            if sv.protocol == protocol.PROTOCOL_RMQ:
                val: progs.eval_t = pr_edict.GetEdictFieldValue(svent, 'scale')
                if val:
                    svent.baseline.scale = protocol.ENTSCALE_DECODE(val._float)

        bits = 0
        if sv.protocol == protocol.PROTOCOL_NETQUAKE:
            if svent.baseline.modelindex & 0xFF00:
                svent.baseline.modelindex = 0
            if svent.baseline.frame & 0xFF00:
                svent.baseline.frame = 0

            svent.baseline.alpha = protocol.ENTALPHA_DEFAULT
            svent.baseline.scale =  protocol.ENTSCALE_DEFAULT
        else:
            if svent.baseline.modelindex & 0xFF00:
                bits |= protocol.B_LARGEMODEL
            if svent.baseline.frame & 0xFF00:
                bits |= protocol.B_LARGEFRAME
            if svent.baseline.alpha != protocol.ENTALPHA_DEFAULT:
                bits |= protocol.B_ALPHA
            if svent.baseline.scale != protocol.ENTSCALE_DEFAULT:
                bits |= protocol.B_SCALE

        SV_ReserveSignonSpace(35)

        if bits:
            common.MSG_WriteByte(sv.signon, protocol.svc_spawnbaseline2)
        else:
            common.MSG_WriteByte(sv.signon, protocol.svc_spawnbaseline)

        common.MSG_WriteShort(sv.signon, entnum)

        if bits:
            common.MSG_WriteByte(sv.signon, bits)

        if bits & protocol.B_LARGEMODEL:
            common.MSG_WriteShort(sv.signon, svent.baseline.modelindex)
        else:
            common.MSG_WriteByte(sv.signon, svent.baseline.modelindex)

        if bits & protocol.B_LARGEFRAME:
            common.MSG_WriteShort(sv.signon, svent.baseline.frame)
        else:
            common.MSG_WriteByte(sv.signon, svent.baseline.frame)

        common.MSG_WriteByte(sv.signon, svent.baseline.colormap)
        common.MSG_WriteByte(sv.signon, svent.baseline.skin)

        for i in range(3):
            common.MSG_WriteCoord(sv.signon, svent.baseline.origin[i], sv.protocolflags)
            common.MSG_WriteAngle(sv.signon, svent.baseline.angles[i], sv.protocolflags)

        if bits & protocol.B_ALPHA:
            common.MSG_WriteByte(sv.signon, svent.baseline.alpha)

        if bits & protocol.B_SCALE:
            common.MSG_WriteByte(sv.signon, svent.baseline.scale)


def SV_SendReconnect():
    data = bytearray(128)
    msg: common.sizebuf_s = common.sizebuf_s()

    msg.data = data
    msg.cursize = 0
    msg.maxsize = len(data)

    common.MSG_WriteChar(msg, protocol.svc_stufftext)
    common.MSG_WriteString(msg, 'reconnect\n')
    net_main.NET_SendToAll(msg, 5.0)

    if not sys_sdl_unix.isDedicated:
        _cmd.Cmd_ExecuteString('reconnect\n', _cmd.cmd_source_t.src_command)

def SV_SaveSpawnparms():
    svs.serverflags = pr_edict.pr_global_struct.serverflags

    for i in range(svs.maxclients):
        host.host_client = svs.clients[i]
        if not host.host_client.active:
            continue

        pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(host.host_client.edict)
        pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.SetChangeParms)

        for j in range(server.NUM_SPAWN_PARMS):
            # note in original source, pr_global_struct.parm is parm1 to parm16
            host.host_client.spawn_parms[j] = pr_edict.pr_global_struct.parm[j]

def SV_SpawnServer2(mapname):
    global sv_active
    import cl_main
    import gl_model

    print(f"SV_SpawnServer (Stub): Loading {mapname}...")

    # Just load the model and flip the bit
    full_path = f"maps/{mapname}.bsp"
    mod = gl_model.Mod_ForName(full_path)

    if mod:
        cl_main.cl.worldmodel = mod
        sv_active = True
        return True

    return False

def SV_SpawnServer(_server: str):

    hostname: cvar.cvar_t = cvar.Cvar_GetCvar('hostname').string
    if not hostname or hostname == '':
        cvar.Cvar_Set('hostname', 'UNNAMED')
        gl_screen.scr_centertime_off = 0

    console.Con_DPrintf('SpawnServer: %s' % _server)
    svs.changelevel_issued = False

    if sv.active:
        SV_SendReconnect()

    coop  = cvar.Cvar_GetCvar('coop').value
    skill = cvar.Cvar_GetCvar('skill').value
    deathmatch = cvar.Cvar_GetCvar('deathmatch').value

    if coop:
        cvar.Cvar_Set('deathmatch', '0')

    host_cmd.current_skill = int(skill + 0.5)

    host_cmd.current_skill = max(host_cmd.current_skill, 0)
    host_cmd.current_skill = min(host_cmd.current_skill, 3)

    cvar.Cvar_SetValue('skill', float(host_cmd.current_skill))

    host.Host_ClearMemory()

    sv.name = _server
    sv.protocol = sv_protocol

    if sv.protocol == protocol.PROTOCOL_RMQ:
        sv.protocolflags = protocol.PRFL_INT32COORD | protocol.PRFL_SHORTANGLE
    else:
        sv.protocolflags = 0

    pr_edict.PR_LoadProgs()

    max_edicts = cvar.Cvar_GetCvar('max_edicts').value

    sv.max_edicts = common.CLAMP(quakedef.MIN_EDICTS, int(max_edicts), quakedef.MAX_EDICTS)
    sv.edicts = [None for _ in range(sv.max_edicts)] # <---

    sv.datagram.maxsize = len(sv.datagram_buf)
    sv.datagram.cursize = 0
    sv.datagram.data = sv.datagram_buf

    sv.reliable_datagram.maxsize = len(sv.reliable_datagram_buf)
    sv.reliable_datagram.cursize = 0
    sv.reliable_datagram.data = sv.reliable_datagram_buf

    SV_AddSignonBuffer()

    sv.num_edicts = svs.maxclients + 1
    # sv.edicts = [None for _ in range(sv.max_edicts)] # see line 1028
    for i in range(svs.maxclients):
        ent = pr_edict.EDICT_NUM(i + 1)
        svs.clients[i].edict = ent

    sv.state = server.server_state_t.ss_loading
    sv.paused = False
    nomonsters = cvar.Cvar_GetCvar('nomonsters').value
    sv.nomonsters = nomonsters != 0.0

    sv.time = 1.0

    sv.name = _server
    sv.modelname = f'maps/{_server}.bsp'
    sv.worldmodel = gl_model.Mod_ForName(sv.modelname, False)
    if not sv.worldmodel:
        console.Con_Printf('Couldnt spawn server %s\n' % sv.modelname)
        sv.active = False
        return

    sv.models[1] = sv.worldmodel

    world.SV_ClearWorld()

    sv.sound_precache = ['', '', '', '', '', '', '', '']
    sv.model_precache = ['', '', '', '', '', '', '', '']
    sv.model_precache[1] = sv.modelname

    for i in range(1, sv.worldmodel.numsubmodels):
        sv.model_precache[i + 1] = localmodels[i]
        sv.models[i + 1] = gl_model.Mod_ForName(localmodels[i], False)

    ent = pr_edict.EDICT_NUM(0)
    # ent.v = LEFT OFF HERE sv_main:1575
    ent.free = False
    ent.v.model = pr_edict.PR_SetEngingString(sv.worldmodel.name)
    ent.v.modelindex = 1
    ent.v.solid = server.SOLID_BSP
    ent.v.movetype = server.MOVETYPE_PUSH

    if coop.value:
        pr_edict.pr_global_struct.coop = coop
    else:
        pr_edict.pr_global_struct.deathmatch = deathmatch

    pr_edict.pr_global_struct.mapname = pr_edict.PR_SetEngineString(sv.name)

    pr_edict.pr_global_struct.serverflags = svs.serverflags

    sv.active = True

    sv.state = server.server_state_t.ss_active

    host.host_frametime = 0.1

    sv_phys.SV_Physics()
    sv_phys.SV_Physics()

    SV_CreateBaseline()

    signonsize = 0
    for i in range(sv.num_signon_buffers):
        signonsize += sv.signon_buffers[i].cursize

    if signonsize > 64000 - 2:
        console.Con_Warning("%i byte signon buffer exceeds QS limit of 63998", signonsize)
    elif signonsize > 8000 - 2:
        console.Con_Warning("%i byte signon buffer exceeds QS limit of 7998", signonsize)

    host.host_client = svs.clients

    for host.host_client in svs.clients:
        if host.host_client.active:
            SV_SendServerInfo(host.host_client)

    console.Con_DPrintf('Server spawned')





