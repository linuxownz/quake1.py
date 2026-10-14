#cl_main.py

import math
from enum import Enum
from random import randint

import _cmd
import chase
import cl_demo
import cl_input
import cl_main
import cl_parse
import cl_tent  # temporary entities
import common
import console
import gl_rmain
import gl_screen
import host
import in_sdl
import keys
import mathlib
import net_main
import protocol
import quakedef
import r_part
import render
import snd_dma
import sv_main

# import gl_model

cactive_t = quakedef.cactive_t  # single shared enum; a private copy never compared equal to quakedef's

cls = quakedef.client_static_t()
cl  = quakedef.client_state_t()

cl_static_entities: list[render.entity_t] = [None for _ in range(quakedef.MAX_STATIC_ENTITIES)]
cl_lightstyle : list[quakedef.lightstyle_t] = [None for _ in range(quakedef.MAX_LIGHTSTYLES)]
cl_dlights    : list[quakedef.dlight_t]     = [None for _ in range(quakedef.MAX_DLIGHTS)]

cl_entities: list[render.entity_t] = []
cl_max_edicts = 0

cl_numvisedicts = 0
cl_visedicts: list[quakedef.entity_t] = [None] * quakedef.MAX_VISEDICTS


def _fix_client_state():
    """Make sure the fixed-size arrays that C declares (mtime[2], mvelocity[2][3], ...)
    exist with the right shape, whatever client_state_t's constructor produced."""
    def vec3():
        return [0.0, 0.0, 0.0]

    def need_list(name, n, factory):
        v = getattr(cl, name, None)
        if not isinstance(v, list) or len(v) < n:
            setattr(cl, name, [factory() for _ in range(n)])

    need_list('mtime', 2, float)
    need_list('mvelocity', 2, vec3)
    need_list('mviewangles', 2, vec3)
    need_list('viewangles', 3, float)
    need_list('velocity', 3, float)
    need_list('punchangle', 3, float)
    need_list('stats', quakedef.MAX_CL_STATS, int)
    need_list('item_gettime', 32, float)


_fix_client_state()


def CL_ClearState():
    global cl, cl_dlights, cl_lightstyle
    global cl_max_edicts, cl_entities, cl_static_entities

    if not sv_main.sv.active:
        host.Host_ClearMemory()

    cl = quakedef.client_state_t()
    _fix_client_state()

    # C: SZ_Clear(&cls.message). Replacing it with a bytearray destroyed the sizebuf.
    common.SZ_Clear(cls.message)

    cl_dlights    = [quakedef.dlight_t() for _ in range(quakedef.MAX_DLIGHTS)]
    cl_lightstyle = [quakedef.lightstyle_t() for _ in range(quakedef.MAX_LIGHTSTYLES)]
    cl_tent.cl_temp_entities = [quakedef.entity_t() for _ in range(quakedef.MAX_TEMP_ENTITIES)]
    cl_tent.cl_beams         = [quakedef.beam_t() for _ in range(quakedef.MAX_BEAMS)]

    import cvar
    max_edicts = int(cvar.Cvar_GetCvar('max_edicts').value)

    cl_max_edicts = int(common.CLAMP(quakedef.MIN_EDICTS, max_edicts, quakedef.MAX_EDICTS))
    cl_entities = [render.entity_t() for _ in range(cl_max_edicts)]
    cl_static_entities = [render.entity_t() for _ in range(quakedef.MAX_STATIC_ENTITIES)]


def CL_Init():
    global _cmd, cvar
    import _cmd
    import cvar

    # C: SZ_Alloc(&cls.message, 1024)
    if not isinstance(cls.message, common.sizebuf_s):
        cls.message = common.sizebuf_s()
    common.SZ_Alloc(cls.message, 1024)

    # registers +forward/-forward, +attack, +jump, impulse, +mlook ... (C: CL_InitInput in CL_Init)
    cl_input.CL_InitInput()

    cl_name       = {'name': "_cl_name",      'value': "player", 'flags': cvar.CVAR_ARCHIVE}
    cl_color      = {'name': "_cl_color",     'value': "0",      'flags': cvar.CVAR_ARCHIVE}
    cl_shownet    = {'name': "cl_shownet",    'value': "0",      'flags': cvar.CVAR_NONE}  # can be 0, 1, or 2
    cl_nolerp     = {'name': "cl_nolerp",     'value': "0",      'flags': cvar.CVAR_NONE}
    cfg_unbindall = {'name': "cfg_unbindall", 'value': "1",      'flags': cvar.CVAR_ARCHIVE}
    lookspring    = {'name': "lookspring",    'value': "0",      'flags': cvar.CVAR_ARCHIVE}
    lookstrafe    = {'name': "lookstrafe",    'value': "0",      'flags': cvar.CVAR_ARCHIVE}
    sensitivity   = {'name': "sensitivity",   'value': "3",      'flags': cvar.CVAR_ARCHIVE}

    m_pitch   = {'name': "m_pitch",   'value':"0.022", 'flags': cvar.CVAR_ARCHIVE}
    m_yaw     = {'name': "m_yaw",     'value':"0.022", 'flags': cvar.CVAR_ARCHIVE}
    m_forward = {'name': "m_forward", 'value':"1",     'flags': cvar.CVAR_ARCHIVE}
    m_side    = {'name': "m_side",    'value':"0.8",   'flags': cvar.CVAR_ARCHIVE}

    cl_maxpitch   = {'name': "cl_maxpitch",   'value':"90",  'flags': cvar.CVAR_ARCHIVE} #johnfitz -- variable pitch clamping
    cl_minpitch   = {'name': "cl_minpitch",   'value':"-90", 'flags': cvar.CVAR_ARCHIVE} #johnfitz -- variable pitch clamping
    cl_startdemos = {'name': "cl_startdemos", 'value':"1",   'flags': cvar.CVAR_ARCHIVE}

    cl_upspeed       = {'name':"cl_upspeed",       'value':"200", 'flags': cvar.CVAR_NONE}
    cl_forwardspeed  = {'name':"cl_forwardspeed",  'value':"200", 'flags': cvar.CVAR_ARCHIVE}
    cl_backspeed     = {'name':"cl_backspeed",     'value':"200", 'flags': cvar.CVAR_ARCHIVE}
    cl_sidespeed     = {'name':"cl_sidespeed",     'value':"350", 'flags': cvar.CVAR_NONE}
    cl_movespeedkey  = {'name':"cl_movespeedkey",  'value':"2.0", 'flags': cvar.CVAR_NONE}
    cl_yawspeed      = {'name':"cl_yawspeed",      'value':"140", 'flags': cvar.CVAR_NONE}
    cl_pitchspeed    = {'name':"cl_pitchspeed",    'value':"150", 'flags': cvar.CVAR_NONE}
    cl_anglespeedkey = {'name':"cl_anglespeedkey", 'value':"1.5", 'flags': cvar.CVAR_NONE}
    cl_alwaysrun     = {'name':"cl_alwaysrun",     'value':"0",   'flags': cvar.CVAR_ARCHIVE} # QuakeSpasm -- new always run

    cvar.Cvar_RegisterVariable (cl_name)
    cvar.Cvar_RegisterVariable (cl_color)
    cvar.Cvar_RegisterVariable (cl_upspeed)
    cvar.Cvar_RegisterVariable (cl_forwardspeed)
    cvar.Cvar_RegisterVariable (cl_backspeed)
    cvar.Cvar_RegisterVariable (cl_sidespeed)
    cvar.Cvar_RegisterVariable (cl_movespeedkey)
    cvar.Cvar_RegisterVariable (cl_yawspeed)
    cvar.Cvar_RegisterVariable (cl_pitchspeed)
    cvar.Cvar_RegisterVariable (cl_anglespeedkey)
    cvar.Cvar_RegisterVariable (cl_shownet)
    cvar.Cvar_RegisterVariable (cl_nolerp)
    cvar.Cvar_RegisterVariable (lookspring)
    cvar.Cvar_RegisterVariable (lookstrafe)
    cvar.Cvar_RegisterVariable (sensitivity)

    cvar.Cvar_RegisterVariable (cl_alwaysrun)

    cvar.Cvar_RegisterVariable (m_pitch)
    cvar.Cvar_RegisterVariable (m_yaw)
    cvar.Cvar_RegisterVariable (m_forward)
    cvar.Cvar_RegisterVariable (m_side)

    cvar.Cvar_RegisterVariable (cfg_unbindall)

    cvar.Cvar_RegisterVariable (cl_maxpitch) #johnfitz -- variable pitch clamping
    cvar.Cvar_RegisterVariable (cl_minpitch) #johnfitz -- variable pitch clamping

    cvar.Cvar_RegisterVariable (cl_startdemos)

    # _cmd.Cmd_AddCommand ("entities", CL_PrintEntities_f)
    # _cmd.Cmd_AddCommand ("disconnect", CL_Disconnect_f)
    # _cmd.Cmd_AddCommand ("record", CL_Record_f)
    # _cmd.Cmd_AddCommand ("stop", CL_Stop_f)
    _cmd.Cmd_AddCommand ("playdemo", cl_demo.CL_PlayDemo_f)
    # _cmd.Cmd_AddCommand ("timedemo", CL_TimeDemo_f)

    # _cmd.Cmd_AddCommand ("tracepos", CL_Tracepos_f) #johnfitz
    # _cmd.Cmd_AddCommand ("viewpos", CL_Viewpos_f) #johnfitz


def CL_Disconnect_f():
    CL_Disconnect()
    if sv_main.sv.active:
        host.Host_ShutdownServer(False)

def CL_Disconnect():
    import console
    if keys.key_dest == keys.keydest_t.key_message:
        keys.Key_EndChat()

    snd_dma.S_StopAllSounds(True)

    if cl_main.cls.demoplayback:
        cl_demo.CL_StopPlayback()
    elif cls.state == cactive_t.ca_connected:
        if cls.demorecording:
            stop = globals().get('CL_Stop_f') or getattr(cl_demo, 'CL_Stop_f', None)
            if stop:
                stop()

        console.Con_DPrintf('sending clc_disconnect\n')
        common.SZ_Clear(cls.message)
        common.MSG_WriteByte(cls.message, protocol.clc_disconnect)
        net_main.NET_SendUnreliableMessage(cls.netcon, cls.message)
        common.SZ_Clear(cls.message)
        net_main.NET_Close(cls.netcon)

        cls.state = cactive_t.ca_disconnected
        if sv_main.sv.active:
            host.Host_ShutdownServer(False)

    cls.demoplayback = False
    cls.timedemo = False
    cl.intermission = 0

    cls.signon = 0


def CL_EstablishConnection(_host: str):
    if cls.state == quakedef.cactive_t.ca_dedicated:
        return

    if cls.demoplayback:
        return

    CL_Disconnect()

    cls.netcon = net_main.NET_Connect(_host)

    if not cls.netcon:
        host.Host_Error('CL_Connect: connect failed')

    console.Con_DPrintf(f'CL_EstablishConnection: connect to {_host}\n')

    cls.demonum = -1
    cls.state =  quakedef.cactive_t.ca_connected
    cl_demo.CL_ClearSignons()
    common.MSG_WriteByte(cls.message, protocol.clc_nop)

def CL_SignonReply():
    console.Con_DPrintf(f'CL_SignonReply: {cls.signon}\n')

    match cls.signon:
        case 1:
            common.MSG_WriteByte(cls.message, protocol.clc_stringcmd)
            common.MSG_WriteString(cls.message, 'prespawn')
        case 2:
            cl_name  = cvar.Cvar_GetCvar('_cl_name').string
            cl_color = int(cvar.Cvar_GetCvar('_cl_color').value)
            common.MSG_WriteByte(cls.message, protocol.clc_stringcmd)
            common.MSG_WriteString(cls.message, f'name "{cl_name}"\n')

            common.MSG_WriteByte(cls.message, protocol.clc_stringcmd)
            common.MSG_WriteString(cls.message, f'color {cl_color>>4} {cl_color & 15}\n')

            common.MSG_WriteByte(cls.message, protocol.clc_stringcmd)
            common.MSG_WriteString(cls.message, f'spawn {cls.spawnparms}')
        case 3:
            common.MSG_WriteByte(cls.message, protocol.clc_stringcmd)
            common.MSG_WriteString(cls.message, 'begin')
        case 4:
            gl_screen.SCR_EndLoadingPlaque()

def CL_NextDemo():
    if cls.demonum == -1:
        return

    if cls.demonum >= len(cls.demos) or cls.demonum >= quakedef.MAX_DEMOS or not cls.demos[cls.demonum]:
        cls.demonum = 0
        if not cls.demos or not cls.demos[0]:
            console.Con_Printf('no demos listed with startdemos')
            cls.demonum = -1
            CL_Disconnect()
            return

    gl_screen.SCR_BeginLoadingPlaque()

    demoname = f'playdemo {cls.demos[cls.demonum]}\n'
    _cmd.Cbuf_InsertText(demoname)
    cls.demonum += 1

def CL_PrintEntities_f():
    if cls.state != quakedef.cactive_t.ca_connected:
        return

    for i, ent in enumerate(cl_entities):
        console.Con_Printf(f'{i:3d}')
        if not ent.model:
            console.Con_Printf('EMPTY')
            continue

        # Format model name (safely handling None), frame, origin vector, and angles vector
        model_name = ent.model.name if ent.model else "NONE"

        console.Con_Printf(
            f"{model_name}:{ent.frame:2d}  ("
            f"{ent.origin[0]:5.1f},{ent.origin[1]:5.1f},{ent.origin[2]:5.1f}) ["
            f"{ent.angles[0]:5.1f} {ent.angles[1]:5.1f} {ent.angles[2]:5.1f}]\n"
        )


def CL_AllocDlight( key: int) -> quakedef.dlight_t:
    dl = None
    if key:
        i = 0
        for dl in cl_dlights:
            if dl.key == key:
                dl.key = key
                dl.color[0] = dl.color[1] = dl.color[2] = 1
                return dl
            i += 1
            if i >= quakedef.MAX_DLIGHTS:
                break

    i = 0
    for dl in cl_dlights:
        if dl.die < cl.time:
            dl.key = key
            dl.color[0] = dl.color[1] = dl.color[2] = 1
            return dl
        i += 1
        if i >= quakedef.MAX_DLIGHTS:
            break

    dl = cl_dlights[0]
    dl.key = key
    dl.color[0] = dl.color[1] = dl.color[2] = 1
    return dl


def CL_DecayLights():
    time = cl.time - cl.oldtime

    i = -1
    for dl in cl_dlights:
        i += 1
        if dl.die < cl.time or not dl.radius:
            continue

        dl.radius -= time * dl.decay
        dl.radius = max(dl.radius, 0)

        if i >= quakedef.MAX_DLIGHTS:
            break


def CL_LerpPoint() -> float:
    f = cl.mtime[0] - cl.mtime[1]

    if not f or cls.timedemo or sv_main.sv.active:
        cl.time = cl.mtime[0]
        return 1

    if f > 0.1:
        cl.mtime[1] = cl.mtime[0] - 0.1
        f = 0.1

    frac = ( cl.time - cl.mtime[1] ) / f

    if frac < 0:
        if frac < -0.01:
            cl.time = cl.mtime[1]
        frac = 0
    elif frac > 1:
        if frac > 1.01:
            cl.time = cl.mtime[0]
        frac = 1

    if cvar.Cvar_GetCvar('cl_nolerp').value:
        return 1

    return frac


def CL_RelinkEntities():
    global cl_numvisedicts

    oldorg = None
    delta = [0, 0, 0]

    frac = CL_LerpPoint()

    cl_numvisedicts = 0

    for i in range(3):
        cl.velocity[i] = cl.mvelocity[1][i] + frac * ( cl.mvelocity[0][i] - cl.mvelocity[1][i])

    if cls.demoplayback:
        for j in range(3):
            d = cl.mviewangles[0][j] - cl.mviewangles[1][j]
            if d > 180:
                d -=360
            elif d < -180:
                d += 360
            cl.viewangles[j] = cl.mviewangles[1][j] + frac * d

    bobjrotate = mathlib.anglemod( 100 * cl.time )

    i = 0

    for ent in cl_entities[1:]:
        i += 1
        if i >= cl.num_entities:
            break

        if not ent.model:
            continue

        if ent.msgtime != cl.mtime[0]:
            ent.model = None
            ent.lerpflags |= render.LERP_RESETMOVE | render.LERP_RESETANIM
            continue


        oldorg = list(ent.origin)

        if ent.forcelink:
            mathlib.VectorCopy(ent.msg_origins[0], ent.origin)
            mathlib.VectorCopy(ent.msg_angles[0], ent.angles)
        else:
            f = frac
            for j in range(3):
                delta[j] = ent.msg_origins[0][j] - ent.msg_origins[1][j]
                if delta[j] > 100 or delta[j] < -100:
                    f = 1
                    ent.lerpflags |= render.LERP_RESETMOVE

            if cvar.Cvar_GetCvar('r_lerpmove').value and ( ent.lerpflags & render.LERP_MOVESTEP):
                f = 1

            for j in range(3):
                ent.origin[j] = ent.msg_origins[1][j] + f * delta[j]

                d = ent.msg_angles[0][j] - ent.msg_angles[1][j]
                if d > 180:
                    d -= 360
                elif d < -180:
                    d += 360

                ent.angles[j] = ent.msg_angles[1][j]  + f * d

        if ent.model.flags & quakedef.EF_ROTATE:
            ent.angles[1] = bobjrotate

        if ent.effects & quakedef.EF_BRIGHTFIELD:
            r_part.R_EntityParticles(ent)

        if ent.effects & quakedef.EF_MUZZLEFLASH:
            fv = [0, 0, 0]
            rv = [0, 0, 0]
            uv = [0, 0, 0]

            dl = CL_AllocDlight(i)
            mathlib.VectorCopy(ent.origin, dl.origin)
            dl.origin[2] += 16
            mathlib.AngleVectors(ent.angles, fv, rv, uv)

            mathlib.VectorMA(dl.origin, 18, fv, dl.origin)
            dl.radius = 200 + (randint(0, 2147483647) & 31)
            dl.minlight = 32
            dl.die = cl.time + 0.1

            if cvar.Cvar_GetCvar('r_lerpmodels').value != 2:
                if ent == cl_entities[cl.viewentity]:
                    cl.viewent.lerpflags |= render.LERP_RESETANIM | render.LERP_RESETANIM2
                else:
                    ent.lerpflags |= render.LERP_RESETANIM | render.LERP_RESETANIM2

        if ent.effects & quakedef.EF_BRIGHTLIGHT:
            dl = CL_AllocDlight(i)
            mathlib.VectorCopy(ent.origin, dl.origin)
            dl.origin[2] += 16
            dl.radius = 400 + ( randint(0,2147483647) & 31)
            dl.die = cl.time + 0.001

        if ent.effects & quakedef.EF_DIMLIGHT:
            dl = CL_AllocDlight(i)
            mathlib.VectorCopy(ent.origin, dl.origin)
            dl.radius = 200 + ( randint(0,2147483647) & 31)
            dl.die = cl.time + 0.001

        if ent.effects & quakedef.EF_QEX_QUADLIGHT:
            dl = CL_AllocDlight(i)
            mathlib.VectorCopy(ent.origin, dl.origin)
            dl.radius = 200 + ( randint(0, 2147483647) & 31)
            dl.die = cl.time + 0.001
            dl.color[0] = 0.25
            dl.color[1] = 0.25
            dl.color[2] = 1.

        if ent.effects & quakedef.EF_QEX_PENTALIGHT:
            dl = CL_AllocDlight(i)
            mathlib.VectorCopy(ent.origin, dl.origin)
            dl.radius = 200 + ( randint(0, 2147483647) & 31)
            dl.die = cl.time + 0.001
            dl.color[0] = 1.0
            dl.color[1] = 0.25
            dl.color[2] = 0.25

        if ent.model.flags & quakedef.EF_GIB:
            r_part.R_RocketTrail( oldorg, ent.origin, 2)
        elif ent.model.flags & quakedef.EF_ZOMGIB:
            r_part.R_RocketTrail( oldorg, ent.origin, 4)
        elif ent.model.flags & quakedef.EF_TRACER:
            r_part.R_RocketTrail( oldorg, ent.origin, 3)
        elif ent.model.flags & quakedef.EF_TRACER2:
            r_part.R_RocketTrail( oldorg, ent.origin, 5)
        elif ent.model.flags & quakedef.EF_ROCKET:
            r_part.R_RocketTrail( oldorg, ent.origin, 0)
            dl = CL_AllocDlight(i)
            mathlib.VectorCopy( ent.origin, dl.origin)
            dl.radius = 200
            dl.die = cl.time + 0.01
        elif ent.model.flags & quakedef.EF_GRENADE:
            r_part.R_RocketTrail( oldorg, ent.origin, 1)
        elif ent.model.flags & quakedef.EF_TRACER3:
            r_part.R_RocketTrail( oldorg, ent.origin, 6)

        ent.forcelink = False

        if i == cl.viewentity and not cvar.Cvar_GetCvar('chase_active').value:
            continue

        if cl_numvisedicts < quakedef.MAX_VISEDICTS:
            cl_visedicts[cl_numvisedicts] = ent
            cl_numvisedicts += 1

def CL_ReadFromServer():
    cl.oldtime = cl.time
    cl.time += host.host_frametime

    while True:
        ret = cl_demo.CL_GetMessage()
        if ret == -1:
            host.Host_Error('CL_ReadFromServer: lost server connection')

        if not ret:
            break

        cl.last_received_message = host.realtime
        cl_parse.CL_ParseServerMessage()

        if not ( ret and cls.state == quakedef.cactive_t.ca_connected ) :
            break

    if cvar.Cvar_GetCvar('cl_shownet').value:
        console.Con_Printf('\n')

    cl_main.CL_RelinkEntities()
    cl_tent.CL_UpdateTEnts()

    if cl_numvisedicts > 256 and host.dev_peakstats.visedicts <= 256:
        console.Con_DWarning(f"{cl_numvisedicts:d} visedicts exceeds standard limit of 256 (max = {quakedef.MAX_VISEDICTS:d}).\n")

    host.dev_stats.visedicts = cl_numvisedicts
    host.dev_peakstats.visedicts = max(cl_numvisedicts, host.dev_peakstats.visedicts)

    ntemp = getattr(cl_tent, 'num_temp_entities', 0)
    if ntemp > 64 and host.dev_peakstats.tempents <= 64:
        console.Con_DWarning(f"{ntemp:d} tempentities exceeds standard limit of 64 (max = {quakedef.MAX_TEMP_ENTITIES:d}).\n")

    host.dev_stats.tempents = ntemp
    host.dev_peakstats.tempents = max(ntemp, host.dev_peakstats.tempents)

    num_beams = sum(1 for b in cl_tent.cl_beams if b.model and b.endtime >= cl.time)

    if num_beams > 24 and host.dev_peakstats.beams <= 24:
        console.Con_DWarning(f"{num_beams:d} beams exceeded standard limit of 24 (max = {quakedef.MAX_BEAMS:d}).\n")

    host.dev_stats.beams = num_beams
    host.dev_peakstats.beams = max(num_beams, host.dev_peakstats.beams)

    num_dlights = sum(1 for l in cl_dlights if l.die >= cl.time and l.radius)

    if num_dlights > 32 and host.dev_peakstats.dlights <= 32:
        console.Con_DWarning(f"{num_dlights:d} dlights exceeded standard limit of 32 (max = {quakedef.MAX_DLIGHTS:d}).\n")

    host.dev_stats.dlights = num_dlights
    host.dev_peakstats.dlights = max(num_dlights, host.dev_peakstats.dlights)

    return 0


def CL_SendCmd():
    ucmd_cls = getattr(protocol, 'usercmd_t', None) or getattr(quakedef, 'usercmd_t', None) or getattr(cl_input, 'usercmd_t', None)
    cmd = ucmd_cls() if ucmd_cls else None

    if cls.state != quakedef.cactive_t.ca_connected:
        return

    if cls.signon == quakedef.SIGNONS:
        cl_input.CL_BaseMove(cmd)

        in_sdl.IN_Move(cmd)

        cl_input.CL_SendMove(cmd)

    if cl_main.cls.demoplayback:
        common.SZ_Clear(cl_main.cls.message)
        return

    if not cl_main.cls.message.cursize:
        return

    if not net_main.NET_CanSendMessage(cl_main.cls.netcon):
        console.Con_DPrintf('CL_SendCmd: cant send')
        return

    if net_main.NET_SendMessage(cl_main.cls.netcon, cl_main.cls.message) == -1:
        host.Host_Error('CL_SendCmd: lost server connection')

    common.SZ_Clear(cl_main.cls.message)


def CL_Tracepos_f():
    if cl_main.cls.state != quakedef.cactive_t.ca_connected:
        return

    v: list[float] = [0., 0., 0.]
    w: list[float] = [0., 0., 0.]

    mathlib.VectorMA(gl_rmain.r_refdef.vieworg, 8192, gl_rmain.vpn, v)
    chase.TraceLine(gl_rmain.r_refdef.vieworg, v, w)

    if mathlib.VectorLength(w) == 0:
        console.Con_Printf('Tracepos: trace didnt hit anything')
    else:
        Con_Printf(f"Tracepos: ({int(w[0]):d} {int(w[1]):d} {int(w[2]):d})\n")


def CL_Viewpos_f():
    if cl_main.cls.state != quakedef.cactive_t.ca_connected:
        return

    view_ent = cl_main.cl_entities[cl_main.cl.viewentity]

    Con_Printf(
        f"Viewpos: ({int(view_ent.origin[0]):d} {int(view_ent.origin[1]):d} {int(view_ent.origin[2]):d}) "
        f"{int(cl.viewangles[PITCH]):d} {int(cl.viewangles[YAW]):d} {int(cl.viewangles[ROLL]):d}\n"
    )








def CL_Move(time_step):
    class DoNotUse(Exception):
        pass
    raise DoNotUse()

    if keys.key_dest != keys.keydest_t.key_game:
        return

    # 1. Update Angles (Rotation)
    turn_speed = 140.0 * time_step
    if cl_input.in_turn_left.state & 1:   cl_main.cl.viewangles[1] += turn_speed
    if cl_input.in_turn_right.state & 1:  cl_main.cl.viewangles[1] -= turn_speed
    if cl_input.in_pitch_up.state & 1:    cl_main.cl.viewangles[0] -= turn_speed
    if cl_input.in_pitch_down.state & 1:  cl_main.cl.viewangles[0] += turn_speed

    # Clamp Pitch to prevent looking too far up/down
    cl_main.cl.viewangles[0] = max(-80, min(80, cl_main.cl.viewangles[0]))

    # 2. Update Position (Translation)
    movespeed = 400.0 * time_step
    yaw_rad = math.radians(cl_main.cl.viewangles[1])

    # Forward/Back Vector
    fwd_move = 0
    if cl_input.in_forward.state & 1: fwd_move += 1
    if cl_input.in_back.state & 1:    fwd_move -= 1

    # Strafe Vector
    side_move = 0
    if cl_input.in_strafe_right.state & 1: side_move += 1
    if cl_input.in_strafe_left.state & 1:  side_move -= 1

    # Apply math to the origin (vieworg)
    # Forward calculation
    cl_main.cl.vieworg[0] += math.cos(yaw_rad) * fwd_move * movespeed
    cl_main.cl.vieworg[1] += math.sin(yaw_rad) * fwd_move * movespeed

    # Strafe calculation (90 degrees off the yaw)
    cl_main.cl.vieworg[0] += math.cos(yaw_rad - math.pi/2) * side_move * movespeed
    cl_main.cl.vieworg[1] += math.sin(yaw_rad - math.pi/2) * side_move * movespeed