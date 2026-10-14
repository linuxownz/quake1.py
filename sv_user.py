#sv_user.py

import math

import _cmd
import common
import console
import cvar
import host
import keys
import mathlib
import net_main
import progs
import protocol
import quakedef
import server
import sv_main
import sys_sdl_unix
import view
import world

sv_player : progs.edict_t = None

def _cv(name: str) -> float:
    c = cvar.Cvar_GetCvar(name)
    return c.value if c is not None else 0.0

forward : quakedef.vec3_t = [0., 0., 0.]
right   : quakedef.vec3_t = [0., 0., 0.]
up      : quakedef.vec3_t = [0., 0., 0.]

angles = 0.0
origin = 0.0
velocity = 0.0

onground = False

cmd : protocol.usercmd_t = None

MAX_FORWARD = 6

def SV_SetIdealPitch():
    top: quakedef.vec3_t = [0, 0, 0]
    bottom: quakedef.vec3_t = [0, 0, 0]
    z: list[float] = [0 for _ in range(MAX_FORWARD)]

    if not (int(sv_player.v.flags) & server.FL_ONGROUND):
        return

    angleval = sv_player.v.angles[quakedef.YAW] * math.pi * 2 / 360
    sinval = math.sin(angleval)
    cosval = math.cos(angleval)

    for i in range(MAX_FORWARD):
        top[0] = sv_player.v.origin[0] + cosval * (i + 3) * 12
        top[1] = sv_player.v.origin[1] + sinval * (i + 3) * 12
        top[2] = sv_player.v.origin[2] + sv_player.v.view_ofs[2]

        bottom[0] = top[0]
        bottom[1] = top[1]
        bottom[2] = top[2] - 160

        tr = world.SV_Move(top, mathlib.vec3_origin, mathlib.vec3_origin, bottom, 1, sv_player)
        if tr.allsolid:
            return

        if tr.fraction == 1:
            return

        z[i] = top[2] + tr.fraction* ( bottom[2] - top[2] )

    _dir = 0
    steps = 0
    for j in range(1, MAX_FORWARD):
        step = z[j] - z[j-1]
        if step > -quakedef.ON_EPSILON and step < quakedef.ON_EPSILON:
            continue

        if _dir and ( step - _dir > quakedef.ON_EPSILON or step - _dir < -quakedef.ON_EPSILON):
            return

        steps += 1
        _dir = step

    if not _dir:
        sv_player.v.idealpitch = 0
        return

    if steps < 2:
        return

    sv_player.v.idealpitch = -_dir * _cv('sv_idealpitchscale')


def SV_UserFriction():
    start: quakedef.vec3_t = [0, 0, 0]
    stop : quakedef.vec3_t = [0, 0, 0]

    vel = velocity

    speed = math.sqrt(vel[0]*vel[0] +vel[1]*vel[1])
    if not speed:
        return

    start[0] = stop[0] = origin[0] + vel[0]/speed*16
    start[1] = stop[1] = origin[1] + vel[1]/speed*16
    start[2] = origin[2] + sv_player.v.mins[2]
    stop[2] = start[2] - 34

    trace = world.SV_Move(start, mathlib.vec3_origin, mathlib.vec3_origin, stop, 1, sv_player)

    sv_friction = _cv('sv_friction')
    sv_edgefriction = _cv('edgefriction')

    if trace.fraction == 1.0:
        friction = sv_friction * sv_edgefriction
    else:
        friction = sv_friction

    sv_stopspeed = _cv('sv_stopspeed')

    control = sv_stopspeed if speed < sv_stopspeed else speed
    newspeed = speed - host.host_frametime * control * friction

    newspeed = max(newspeed, 0)
    newspeed /= speed

    vel[0] = vel[0] * newspeed
    vel[1] = vel[1] * newspeed
    vel[2] = vel[2] * newspeed

def SV_Accelerate(wishspeed, wishdir: quakedef.vec3_t):
    currentspeed = mathlib.DotProduct(velocity, wishdir)

    addspeed = wishspeed - currentspeed
    if addspeed <= 0:
        return

    accelspeed = _cv('sv_accelerate') * host.host_frametime * wishspeed

    accelspeed = min(accelspeed, addspeed)

    for i in range(3):
        velocity[i] += accelspeed * wishdir[i]


def SV_AirAccelerate(wishspeed, wishveloc: quakedef.vec3_t):
    wishspd = mathlib.VectorNormalize(wishveloc)

    wishspd = min(wishspd, 30)

    currentspeed = mathlib.DotProduct(velocity, wishveloc)
    addspeed = wishspd - currentspeed

    if addspeed <=0:
        return

    accelspeed = _cv('sv_accelerate') * wishspeed * host.host_frametime

    accelspeed = min(accelspeed, addspeed)

    for i in range(3):
        velocity[i] += accelspeed * wishveloc[i]

def DropPunchAngle():
    length = mathlib.VectorNormalize(sv_player.v.punchangle)

    length -= 10 * host.host_frametime
    length = max(length, 0)

    mathlib.VectorScale(sv_player.v.punchangle, length, sv_player.v.punchangle)

def SV_WaterMove():
    wishvel: quakedef.vec3_t = [0, 0, 0]

    mathlib.AngleVectors(sv_player.v.v_angle, forward, right, up)

    for i in range(3):
        wishvel[i] = forward[i] * cmd.forwardmove + right[i] * cmd.sidemove

    if not cmd.forwardmove and not cmd.sidemove and not cmd.upmove:
        wishvel[2] -= 60
    else:
        wishvel[2] += cmd.upmove

    sv_maxspeed = _cv('sv_maxspeed')
    wishspeed = mathlib.VectorLength(wishvel)
    if wishspeed > sv_maxspeed:
        mathlib.VectorScale(wishvel, sv_maxspeed/wishspeed, wishvel)
        wishspeed = sv_maxspeed

    wishspeed *= 0.7

    speed = mathlib.VectorLength(velocity)
    if speed:
        newspeed = speed - host.host_frametime * speed * _cv('sv_friction')
        newspeed = max(newspeed, 0)
        mathlib.VectorScale(velocity, newspeed/speed, velocity)
    else:
        newspeed = 0

    if not wishspeed:
        return

    addspeed = wishspeed - newspeed
    if addspeed <= 0:
        return

    mathlib.VectorNormalize(wishvel)
    accelspeed = _cv('sv_accelerate') * wishspeed * host.host_frametime

    accelspeed = min(accelspeed, addspeed)

    for i in range(3):
        velocity[i] += accelspeed * wishvel[i]

def SV_WaterJump():
    if sv_main.sv.time > sv_player.v.teleport_time or not sv_player.v.waterlevel:
        sv_player.v.flags = int(sv_player.v.flags) & ~server.FL_WATERJUMP
        sv_player.v.teleport_time = 0

    sv_player.v.velocity[0] = sv_player.v.movedir[0]
    sv_player.v.velocity[1] = sv_player.v.movedir[1]

def SV_NoclipMove():

    mathlib.AngleVectors(sv_player.v.v_angle, forward, right, up)

    velocity[0] = forward[0] * cmd.forwardmove + right[0] * cmd.sidemove
    velocity[1] = forward[1] * cmd.forwardmove + right[1] * cmd.sidemove
    velocity[2] = forward[2] * cmd.forwardmove + right[2] * cmd.sidemove
    velocity[2] += cmd.upmove * 2

    sv_maxspeed = _cv('sv_maxspeed')

    if mathlib.VectorLength(velocity) > sv_maxspeed:
        mathlib.VectorNormalize(velocity)
        mathlib.VectorScale(velocity, sv_maxspeed, velocity)


def SV_AirMove():
    wishvel: quakedef.vec3_t = [0, 0, 0]
    wishdir: quakedef.vec3_t = [0, 0, 0]

    mathlib.AngleVectors(sv_player.v.angles, forward, right, up)

    fmove = cmd.forwardmove
    smove = cmd.sidemove

    if sv_main.sv.time < sv_player.v.teleport_time and fmove < 0:
        fmove = 0

    for i in range(3):
        wishvel[i] = forward[i]*fmove + right[i]*smove

    if int(sv_player.v.movetype) != server.MOVETYPE_WALK:
        wishvel[2] = cmd.upmove
    else:
        wishvel[2] = 0

    sv_maxspeed = _cv('sv_maxspeed')
    mathlib.VectorCopy(wishvel, wishdir)
    wishspeed = mathlib.VectorNormalize(wishdir)
    if wishspeed > sv_maxspeed:
        mathlib.VectorScale(wishvel, sv_maxspeed/wishspeed, wishvel)
        wishspeed = sv_maxspeed

    if sv_player.v.movetype == server.MOVETYPE_NOCLIP:
        mathlib.VectorCopy(wishvel, velocity)
    elif onground:
        SV_UserFriction()
        SV_Accelerate(wishspeed, wishdir)
    else:
        SV_AirAccelerate(wishspeed, wishvel)

def SV_ClientThink():
    global onground, origin, velocity
    global cmd, angles

    v_angle: quakedef.vec3_t = [0, 0, 0]

    if sv_player.v.movetype == server.MOVETYPE_NONE:
        return

    onground = int(sv_player.v.flags) & server.FL_ONGROUND

    origin = sv_player.v.origin
    velocity = sv_player.v.velocity

    DropPunchAngle()

    if sv_player.v.health <= 0:
        return

    cmd = host.host_client.cmd
    angles = sv_player.v.angles

    mathlib.VectorAdd(sv_player.v.v_angle, sv_player.v.punchangle, v_angle)

    angles[quakedef.ROLL] = view.V_CalcRoll(sv_player.v.angles, sv_player.v.velocity) * 4

    if not sv_player.v.fixangle:
        angles[quakedef.PITCH] = -v_angle[quakedef.PITCH] / 3
        angles[quakedef.YAW] = v_angle[quakedef.YAW]

    if int(sv_player.v.flags) & server.FL_WATERJUMP:
        SV_WaterJump()
        return

    if sv_player.v.movetype == server.MOVETYPE_NOCLIP and _cv('sv_altnoclip'):
        SV_NoclipMove()
    elif sv_player.v.waterlevel >= 2 and int(sv_player.v.movetype) != server.MOVETYPE_NOCLIP:
        SV_WaterMove()
    else:
        SV_AirMove()

def SV_ReadClientMove(move: protocol.usercmd_t):
    angle: quakedef.vec3_t = [0, 0, 0]

    host.host_client.ping_times[host.host_client.num_pings % server.NUM_PING_TIMES] = sv_main.sv.time - common.MSG_ReadFloat()
    host.host_client.num_pings += 1

    for i in range(3):
        if sv_main.sv.protocol == protocol.PROTOCOL_NETQUAKE:
            angle[i] = common.MSG_ReadAngle(sv_main.sv.protocolflags)
        else:
            angle[i] = common.MSG_ReadAngle16(sv_main.sv.protocolflags)

    mathlib.VectorCopy(angle, host.host_client.edict.v.v_angle)

    move.forwardmove = common.MSG_ReadShort()
    move.sidemove = common.MSG_ReadShort()
    move.upmove = common.MSG_ReadShort()

    bits = common.MSG_ReadByte()
    host.host_client.edict.v.button0 = bits & 1
    host.host_client.edict.v.button2 = ( bits & 2 ) >> 1

    i = common.MSG_ReadByte()
    if i:
        host.host_client.edict.v.impulse = i



# client console commands the server will accept (matched by prefix, case-insensitive,
# exactly like the q_strncasecmp chain in the C code; "say_team" is covered by "say")
_ALLOWED_CLIENT_CMDS = (
    'status', 'god', 'notarget', 'fly', 'name', 'noclip', 'setpos',
    'say', 'tell', 'color', 'kill', 'pause', 'spawn', 'begin',
    'prespawn', 'kick', 'ping', 'give', 'ban',
)


def SV_ReadClientMessage() -> bool:
    """Read and execute everything the current host.host_client has sent.

    Returns False if the client should be dropped (error / disconnect),
    True when there is nothing more to read.
    """
    while True:  # C: do { nextmsg: ... } -- every exit is a return or "goto nextmsg"
        ret = net_main.NET_GetMessage(host.host_client.netconnection)
        if ret == -1:
            sys_sdl_unix.Sys_Printf('SV_ReadClientMessage: NET_GetMessage failed\n')
            return False
        if not ret:
            return True

        common.MSG_BeginReading()

        while True:
            if not host.host_client.active:
                return False  # a command caused an error

            # msg_badread is rebound inside common, so always read it via the module
            if common.msg_badread:
                sys_sdl_unix.Sys_Printf('SV_ReadClientMessage: badread\n')
                return False

            ccmd = common.MSG_ReadChar()

            if ccmd == -1:
                break  # end of message -> fetch the next one (goto nextmsg)

            elif ccmd == protocol.clc_nop:
                pass

            elif ccmd == protocol.clc_stringcmd:
                s = common.MSG_ReadString()
                if s.lower().startswith(_ALLOWED_CLIENT_CMDS):
                    _cmd.Cmd_ExecuteString(s, _cmd.cmd_source_t.src_client)
                else:
                    console.Con_DPrintf(f'{host.host_client.name} tried to {s}\n')

            elif ccmd == protocol.clc_disconnect:
                return False

            elif ccmd == protocol.clc_move:
                SV_ReadClientMove(host.host_client.cmd)

            else:
                sys_sdl_unix.Sys_Printf('SV_ReadClientMessage: unknown command char\n')
                return False



def SV_RunClients():
    global sv_player

    for host.host_client in sv_main.svs.clients:

        if not host.host_client.active:
            continue

        sv_player = host.host_client.edict

        if not SV_ReadClientMessage():
            host.SV_DropClient(False)
            continue

        if not host.host_client.spawned:
            host.host_client.cmd = protocol.usercmd_t()
            continue

        if not sv_main.sv.paused and (sv_main.svs.maxclients > 1 or keys.key_dest == keys.keydest_t.key_game):
            SV_ClientThink()




