#sv_phys.py
import math

import bspfile
import console
import cvar
import host
import mathlib
import pr_edict
import pr_exec
import progs
import server
import sv_main
import sv_user
import sys_sdl_unix
import world

STOP_EPSILON = 0.1
MAX_CLIP_PLANES = 5
STEPSIZE = 18

def SV_CheckAllEnts():
    check: progs.edict_t = progs.NEXT_EDICT(sv_main.sv.edicts)

    for e in range(i, sv_main.sv.num_edicts):
        if check.free:
            continue
        if check.v.movetype in ( server.MOVETYPE_PUSH, server.MOVETYPE_NONE, server.MOVETYPE_NOCLIP):
            continue

        if world.SV_TestEntityPosition(check):
            console.Con_Printf('entity in invalid position')

def SV_CheckVelocity(ent: progs.edict_t):

    sv_maxvelocity = cvar.Cvar_GetCvar('sv_maxvelocity').value

    for i in range(3):
        if mathlib.IS_NAN(ent.v.velocity[i]):
            console.Con_Printf('Got a NaN velocity on %s' % pr_edict.PR_GetString(ent.v.classname))
            ent.v.velocity[i] = 0
        if mathlib.IS_NAN(ent.v.origin[i]):
            console.Con_Printf('Got a NaN origin on %s' % pr_edict.PR_GetString(ent.v.classname))
            ent.v.origin[i] = 0

        if ent.v.velocity[i] > sv_maxvelocity:
            ent.v.velocity[i] = sv_maxvelocity
        elif ent.v.velocity[i] < -sv_maxvelocity:
            ent.v.velocity[i] = -sv_maxvelocity

def SV_RunThink(ent: progs.edict_t) -> bool:
    thinktime: float = ent.v.nextthink

    if thinktime <= 0 or thinktime > sv_main.sv.time + host.host_frametime:
        return True

    thinktime = max(thinktime, sv_main.sv.time)

    ent.oldthinktime = thinktime
    ent.oldframe = ent.v.frame

    ent.v.nextthink = 0
    pr_edict.pr_global_struct.time = thinktime
    pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(ent)
    pr_edict.pr_global_struct.other = progs.EDICT_TO_PROG(sv_main.sv.edicts)
    pr_exec.PR_ExecuteProgram(ent.v.think)

    return not ent.free


def SV_Impact(e1: progs.edict_t, e2: progs.edict_t):
    old_self = pr_edict.pr_global_struct.self
    old_other = pr_edict.pr_global_struct.other

    pr_edict.pr_global_struct.time = sv_main.sv.time

    if e1.v.touch and e1.v.solid != server.SOLID_NOT:
        pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(e1)
        pr_edict.pr_global_struct.other = progs.EDICT_TO_PROG(e2)
        pr_exec.PR_ExecuteProgram(e1.v.touch)

    if e2.v.touch and e2.v.solid != server.SOLID_NOT:
        pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(e2)
        pr_edict.pr_global_struct.other = progs.EDICT_TO_PROG(e1)
        pr_exec.PR_ExecuteProgram(e2.v.touch)

    pr_edict.pr_global_struct.self = old_self
    pr_edict.pr_global_struct.other = old_other

def ClipVelocity(_in: list[float], normal: list[float], out:list[float], overbounce: float) -> int:
    blocked: int = 0

    if normal[2] > 0:
        blocked |= 1
    if not normal[2]:
        blocked |= 2

    backoff: float = mathlib.DotProduct(_in, normal) * overbounce

    for i in range(3):
        change: float = normal[i] * backoff
        out[i] = _in[i] - change
        if out[i] > -STOP_EPSILON and out[i] < STOP_EPSILON:
            out[i] = 0

    return blocked

def SV_FlyMove(ent: progs.edict_t, time: float, steptrace: world.trace_t) -> int:
    numbumps: int = 4
    blocked: int = 0
    numplanes : int = 0

    trace: world.trace_t

    _dir: list[float] = [0.0 for _ in range(3)]
    end: list[float] = [0.0 for _ in range(3)]
    original_velocity: list[float] = [0.0 for _ in range(3)]
    primal_velocity: list[float] = [0.0 for _ in range(3)]
    new_velocity: list[float] = [0.0 for _ in range(3)]

    planes = [[0.0, 0.0, 0.0] for _ in range(MAX_CLIP_PLANES)]

    mathlib.VectorCopy(ent.v.velocity, original_velocity)
    mathlib.VectorCopy(ent.v.velocity, primal_velocity)

    time_left: float = time

    for bumpcount in range(numbumps):
        if not ent.v.velocity[0] and not ent.v.velocity[1] and not ent.v.velocity[2]:
            break

        for i in range(3):
            end[i] = ent.v.origin[i] + time_left * ent.v.velocityh[i]

        trace = world.SV_Move(ent.v.origin, ent.v.mins, ent.v.maxs, end, False, ent)

        if trace.allsolid:
            mathlib.VectorCopy(vec3_origin, ent.v.velocity)
            return 3

        if trace.fraction > 0:
            mathlib.VectorCopy(trace.endpos, ent.v.origin)
            mathlib.VectorCopy(ent.v.velocity, original_velocity)
            numplanes = 0

        if trace.fraction == 1:
            break

        if not trace.ent:
            sys_sdl_unix.Sys_Error('SV_FlyMove:L !trace.ent')

        if trace.plane.normal[2] > 0.7:
            blocked |= 1
            if trace.ent.v.solid == server.SOLID_BSP:
                ent.v.flags = int(ent.v.flags) | server.FL_ONGROUND
                ent.v.groundentity = progs.EDICT_TO_PROG(trace.ent)

        if not trace.plane.normal[2]:
            blocked |= 2
            if steptrace:
                steptrace = trace

        SV_Impact(ent, trace.ent)
        if ent.free:
            break

        time_left -= time_left * trace.fraction

        if numplanes >= MAX_CLIP_PLANES:
            mathlib.VectorCopy(vec3_origin, ent.v.velocity)
            return 3

        mathlib.VectorCopy(trace.plane.normal, planes[numplanes])
        numplanes += 1

        for i in range(numplanes):
            ClipVelocity(original_velocity, planes[i], new_velocity, 1)

            for j in range(numplanes):
                if j != i:
                    if mathlib.DotProduct(new_velocity, planes[j]) < 0:
                        break
            if j == numplanes:
                break
        if i != numplanes:
            mathlib.VectorCopy(new_velocity, ent.v.velocity)
        else:
            if numplanes != 2:
                mathlib.VectorCopy(vec3_origin, ent.v.velocity)
                return 7

        mathlib.CrossProduct(planes[0], planes[1], _dir)
        d = mathlib.DotProduct(_dir, ent.v.velocity)
        mathlib.VectorScale(_dir, d, ent.v.velocity)

        if mathlib.DotProduct(ent.v.velocity, primal_velocity) <= 0:
            mathlib.VectorCopy(vec3_origin, ent.v.velocity)
            return blocked

    return blocked


def SV_AddGravity(ent: progs.edict_t):
    ent_gravity: float = 0.0
    val: progs.eval_t

    val = pr_edict.GetEdictFieldValue(ent, 'gravity')
    if val and val._float:
        ent_gravity = val._float
    else:
        ent_gravity = 1.0

    sv_gravity = cvar.Cvar_GetCvar('sv_gravity').value

    ent.v.velocity[2] -= ent_gravity * sv_gravity * host_frametime

def SV_PushEntity(ent: progs.edict_t, push: list[float]) -> world.trace_t:
    trace: world.trace_t = None
    end: list[float] = [0.0, 0.0, 0.0]

    mathlib.VectorAdd(ent.v.origin, push, end)

    if ent.v.movetype == server.MOVETYPE_FLYMISSILE:
        trace = world.SV_Move(ent.v.origin, ent.v.mins, ent.v.maxs, end, world.MOVE_MISSLE, ent)
    elif ent.v.solid == server.SOLID_TRIGGER or ent.v.solid == server.SOLID_NOT:
        trace = world.SV_Move(ent.v.origin, ent.v.mins, ent.v.maxs, end, world.MOVE_NOMONSTERS, ent)
    else:
        trace = world.SV_Move(ent.v.origin, ent.v.mins, ent.v.maxs, end, world.MOVE_NORMAL, ent)

    mathlib.VectorCopy(trace.endpos, ent.v.origin)
    world.SV_LinkEdict(ent, True)

    if trace.ent:
        SV_Impact(ent, trace.ent)

    return trace


def SV_PushMove ( pusher: progs.edict_t, movetime: float):
    check: progs.edict_t = None
    block: progs.edict_t = None

    mins:list[float] = [0.0, 0.0, 0.0]
    maxs:list[float] = [0.0, 0.0, 0.0]
    move:list[float] = [0.0, 0.0, 0.0]

    entorig:list[float] = [0.0, 0.0, 0.0]
    pushorig:list[float] = [0.0, 0.0, 0.0]

    if not pusher.v.velocityh[0] and not pusher.v.velocity[1] and not pusher.v.velocity[2]:
        pusher.v.ltime += movetime
        return

    for i in range(3):
        move[i] = pusher.v.velocity[i] * movetime
        mins[i] = pusher.v.absmin[i] + move[i]
        maxs[i] = pusher.v.absmax[i] + move[i]

    mathlib.VectorCopy(pusher.v.origin, pushorig)

    mathlib.VectorAdd(pusher.v.origin, move, pusher.v.origin)
    pusher.v.ltime += movetime

    world.SV_LinkEdict(pusher, False)

    num_edicts = sv_main.sv.num_edicts
    moved_edict = [None] * num_edicts
    moved_from = [[0.0, 0.0, 0.0] for _ in range(num_edicts)]

    num_moved = 0
    check = progs.NEXT_EDICT(sv_main.sv.edicts)

    for e in range(1, sv_main.sv.num_edicts):
        if check.free:
            continue

        if check.v.movetype == server.MOVETYPE_PUSH or check.v.movetype == server.MOVETYPE_NONE or check.v.movetype == server.MOVETYPE_NOCLIP:
            continue

        if not check.v.flags & server.FL_ONGROUND and progs.PROG_TO_EDICT(check.v.groundentity) == pusher:
            if check.v.absmin[0] >= maxs[0] \
                or check.v.absmin[1] >= maxs[1]  \
                or check.absmin[2] >= maxs[2] \
                or check.v.absmax[0] <= ns[0] \
                or check.v.absmax[1] <= ns[1] \
                or check.v.absmax[2] <= mins[2] :
                    continue

            if not SV_TestEntityPosition(check):
                continue

            if check.v.movetype != server.MOVETYPE_WALK:
                check.v.flags = int(check.v.flags & ~server.FL_ONGROUND)

            mathlib.VectorCopy(check.v.origin, entorig)
            mathlib.VectorCopy(check.v.origin, moved_from[num_moved])
            moved_edict[num_moved] = check
            num_moved += 1

            solid_backup = pusher.v.solid

            if solid_backup == server.SOLID_BSP or solid_backup == server.SOLID_BBOX or solid_backup == server.SOLID_SLIDEBOX:
                pusher.v.solid = server.SOLID_NOT
                SV_PushEntity(check, move)
                pusher.v.solid = solid_backup

            block = SV_TestEntityPosition(check)
            if block:
                if check.v.mins[0] == check.v.maxs[0]:
                    continue
                if check.v.solid == server.SOLID_NOT or check.v.solid == server.SOLID_TRIGGER:
                    check.v.mins[0] = check.v.mins[1] = 0
                    mathlib.VectorCopy(check.v.mins, check.v.maxs)
                    continue

                mathlib.VectorCopy(entorig, check.v.origin)
                world.SV_LinkEdict(check, True)

                mathlib.VectorCopy(pushorig, pusher.v.origin)
                world.SV_LinkEdict(pusher, False)
                pusher.v.ltime -= movetime

                if pusher.v.blocked:
                    pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(pusher)
                    pr_edict.pr_global_struct.other = progs.EDICT_TO_PROG(check)
                    pr_exec.PR_ExecuteProgram(pusher.v.blocked)

                for i in range(num_moved):
                    mathlib.VectorCopy(moved_from[i], moved_edict[i].v.origin)
                    world.SV_LinkEdict(moved_edict[i], False)

                return
        check = progs.NEXT_EDICT(check)


def SV_Physics_Pusher(ent: progs.edict_t):

    oldtime: float = ent.v.ltime
    thinktime: float = ent.v.nextthink

    if thinktime < ent.v.ltime + host.host_frametime:
        movetime = thinktime - ent.v.ltime
        movetime = max(movetime, 0)
    else:
        movetime = host.host_frametime

    if movetime:
        SV_PushMove(ent, movetime)

    if thinktime > oldtime and thinktime <= ent.v.ltime:
        ent.v.nextthink = 0
        pr_edict.pr_global_struct.time = sv_main.sv.time
        pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(ent)
        pr_edict.pr_global_struct.other = progs.EDICT_TO_PROG(sv_main.sv.edicts)
        pr_exec.PR_ExecuteProgram(ent.v.think)
        if ent.free:
            return


# CLIENT MOVEMENT

def SV_CheckStuck ( ent: progs.edict_t ):

    org: list[float] = [0.0, 0.0, 0.0]

    if not world.SV_TestEntityPosition(ent):
        mathlib.VectorCopy(ent.v.origin, ent.v.oldorigin)
        return

    mathlib.VectorCopy(ent, org)
    mathlib.VectorCopy(ent.v.oldorigin, ent.v.origin)

    if not world.SV_TestEntityPosition(ent):
        console.Con_DPrintf('unstuck\n')
        world.SV_LinkEdict(ent, True)
        return

    for z in range(18):
        for i in range(-1, 2):
            for j in range(-1, 2):
                ent.v.origin[0] = org[0] + i
                ent.v.origin[1] = org[1] + j
                ent.v.origin[2] = org[2] + z

                if not world.SV_TestEntityPosition(ent):
                    console.Con_DPrintf('unstuck\n')
                    world.SV_LinkEdict(ent, True)
                    return

    mathlib.VectorCopy(org, ent.v.origin)
    console.Con_DPrintf('player is stuck')


def SV_CheckWater(ent: progs.edict_t) -> bool:

    point: list[float] = [0.0, 0.0, 0.0]

    point[0] = ent.v.origin[0]
    point[1] = ent.v.origin[1]
    point[2] = ent.v.origin[2]

    ent.v.waterlevel = 0
    ent.v.watertype = bspfile.CONTENTS_EMPTY
    cont = world.SV_PointContents(point)

    if cont <= bspfile.CONTENTS_WATER:
        ent.v.watertype = cont
        ent.v.waterlevel = 1

        point[2] = ent.v.origin[2] + ( ent.v.mins[2] + ent.v.maxs[2]) * 0.5
        cont = world.SV_PointContents(point)

        if cont <= bspfile.CONTENTS_WATER:
            ent.v.waterlevel = 2
            point[2] = ent.v.origin[2] + ent.v.view_ofs[2]
            cont = world.SV_PointContents(point)
            if cont <= bspfile.CONTENTS_WATER:
                ent.v.waterlevel = 3

    return ent.v.waterlevel > 1


def SV_WallFriction ( ent: progs.edict_t, trace: world.trace_t ):

    forward: list[float] = [0.0, 0.0, 0.0]
    right  : list[float] = [0.0, 0.0, 0.0]
    up     : list[float] = [0.0, 0.0, 0.0]
    into   : list[float] = [0.0, 0.0, 0.0]
    side   : list[float] = [0.0, 0.0, 0.0]

    mathlib.AngleVectors(ent.v.v_angle, forward, right, up)
    d = mathlib.DotProduct(trace.plane.normal, forward)

    d += 0.5
    if d >= 0:
        return

    i = mathlib.DotProduct(trace.plane.normal, ent.v.velocity)

    mathlib.VectorScale(trace.plane.normal, i, into)
    mathlib.VectorSubtract(ent.v.velocity, into, side)

    ent.v.velocity[0] = side[0] * ( 1 + d )
    ent.v.velocity[1] = side[1] * ( 1 + d )


def SV_TryUnstick(ent: progs.edict_t, oldvel: list[float]) -> int:
    oldorg: list[float] = [0.0, 0.0, 0.0]
    dir   : list[float] = [0.0, 0.0, 0.0]
    steptrace: world.trace_t = None

    mathlib.VectorCopy(ent.v.origin, oldorg)
    mathlib.VectorCopy(mathlib.vec3_origin, dir)

    for i in range(8):
        match i:
            case 0:
                dir[0] = 2
                dir[1] = 0
            case 1:
                dir[0] = 0
                dir[1] = 2
            case 2:
                dir[0] = -2
                dir[1] = 0
            case 3:
                dir[0] = 0
                dir[1] = -2
            case 4:
                dir[0] = 2
                dir[1] = 2
            case 5:
                dir[0] = -2
                dir[1] = 2
            case 6:
                dir[0] = 2
                dir[1] = -2
            case 7:
                dir[0] = -2
                dir[1] = -2

        SV_PushEntity(ent, dir)

        ent.v.velocity[0] = oldvel[0]
        ent.v.velocity[1] = oldvel[1]
        ent.v.velocity[2] = 0
        clip = SV_FlyMove(ent, 0.1, steptrace)

        if math.fabs(oldor[1] - ent.v.origin[1]) > 4 or math.fabs(oldorg[0] - ent.v.origin[0]) > 4:
            return clip

        mathlib.VectorCopy(oldorg, ent.v.origin)

    mathlib.VectorCopy(mathlib.vec3_origin, ent.v.velocity)
    return 7


def SV_WalkMove(ent: progs.edict_t):
    upmove  : list[float] = [0.0, 0.0, 0.0]
    downmove: list[float] = [0.0, 0.0, 0.0]

    oldorg  : list[float] = [0.0, 0.0, 0.0]
    oldvel  : list[float] = [0.0, 0.0, 0.0]

    nosteporg  : list[float] = [0.0, 0.0, 0.0]
    nostepvel  : list[float] = [0.0, 0.0, 0.0]

    steptrace: world.trace_t = None
    downtrace: world.trace_t = None

    oldonground = int(ent.v.flags & server.FL_ONGROUND)
    ent.v.flags = int(ent.v.flags & ~server.FL_ONGROUND)

    mathlib.VectorCopy(ent.v.origin, oldorg)
    mathlib.VectorCopy(ent.v.velocity, oldvel)

    clip = SV_FlyMove(ent, host.host_frametime, steptrace)

    if not ( clip & 2 ):
        return

    if not oldonground and ent.v.waterlevel == 0:
        return

    if ent.v.movetype != server.MOVETYPE_WALK:
        return

    sv_nostep = cvar.Cvar_GetCvar('sv_nostep').value
    if not sv_nostep:
        return

    if int(sv_user.sv_player.v.flags & server.FL_WATERJUMP):
        return

    mathlib.VectorCopy(ent.v.origin, nosteporg)
    mathlib.VectorCopy(ent.v.velocity, nostepvel)

    mathlib.VectorCopy(oldorg, ent.v.origin)

    mathlib.VectorCopy(mathlib.vec3_origin, upmove)
    mathlib.VectorCopy(mathlib.vec3_origin, downmove)
    upmove[2] = STEPSIZE
    downmove[2] = -STEPSIZE + oldvel[2] * host.host_frametime

    SV_PushEntity(ent, upmove)

    ent.v.velocity[0] = oldvel[0]
    ent.v.velocity[1] = oldvel[1]
    ent.v.velocity[2] = 0
    clip = SV_FlyMove(ent, host.host_frametime, steptrace)

    if clip:
        if math.fabs(oldorg[1] - ent.v.origin[1]) < 0.03125 and \
            math.fabs(oldorg[0] - ent.v.origin[0]) < 0.03125:
            clip = SV_TryUnstick(ent, oldvel)

    if clip & 2:
        SV_WallFriction(ent, steptrace)

    downtrace = SV_PushEntity(ent, downmove)

    if downtrace.plane.normal[2] > 0.7:
        if ent.v.solid == server.SOLID_BSP:
            ent.v.flags = int(ent.v.flags | server.FL_ONGROUND)
            ent.v.groundentity = progs.EDICT_TO_PROG(downtrace.ent)

    else:
        mathlib.VectorCopy(nosteporg, ent.v.origin)
        mathlib.VectorCopy(nostepvel, ent.v.velocity)

def SV_Physics_Client(ent: progs.edict_t, num: int):
    if not sv_main.svs.clients[num-1].active:
        return

    pr_edict.pr_global_struct.time = sv_main.sv.time
    pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(ent)
    pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.PlayerPreThink)

    SV_CheckVelocity(ent)

    match(int(ent.v.movetype)):
        case server.MOVETYPE_NONE:
            if not SV_RunThink(ent):
                return
        case server.MOVETYPE_WALK:
            if not SV_RunThink(ent):
                return
            if not SV_CheckWater(ent) and not ( int(ent.v.flags & server.FL_WATERJUMP)):
                SV_AddGravity(ent)
            SV_CheckStuck(ent)
            SV_WalkMove(ent)
        case server.MOVETYPE_TOSS | server.MOVETYPE_BOUNCE | server.MOVETYPE_GIB:
            SV_Physics_Toss(ent)
        case server.MOVETYPE_FLY:
            if not SV_RunThink(ent):
                return
            SV_FlyMove(ent, host.host_frametime, None)
        case server.MOVETYPE_NOCLIP:
            if not SV_RunThink(ent):
                return
            mathlib.VectorMA(ent.v.origin, host.host_frametime, ent.v.velocity, ent.v.origin)
        case _:
            sys_sdl_unix.Sys_Error(f'SV_Physics client: bad movetype {int(ent.v.movetype)}')

    world.SV_LinkEdict(ent, True)

    pr_edict.pr_global_struct.time = sv_main.sv.time
    pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(ent)
    pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.PlayerPostThink)

def SV_Physics_None(ent: progs.edict_t):
    SV_RunThink(ent)

def SV_Physics_Noclip(ent: progs.edict_t):
    if not SV_RunThink(ent):
        return
    mathlib.VectorMA(ent.v.angles, host.host_frametime, ent.v.avelocity, ent.v.angles)
    mathlib.VectorMA(ent.v.origin, host.host_frametime, ent.v.velocity, ent.v.origin)

    world.SV_LinkEdict(ent, False)

def SV_CheckWaterTransition(ent: progs.edict_t):
    cont = world.SV_PointContents(ent.v.origin)

    if not ent.v.watertype:
        ent.v.watertype = cont
        ent.v.waterlevel = 1
        return

    if cont <= bspfile.CONTENTS_WATER:
        if ent.v.watertype == bspfile.CONTENTS_EMPTY:
            sv_main.SV_StartSound(ent, 0, 'misc/h2ohit1.wav', 255, 1)
        ent.v.watertype = cont
        ent.v.waterlevel = 1
    else:
        if ent.v.watertype != bspfile.CONTENTS_EMPTY:
            sv_main.SV_StartSound(ent, 0, 'misc/h2ohit1.wav', 255, 1)
        ent.v.watertype = bspfile.CONTENTS_EMPTY
        ent.v.waterlevel = cont

def SV_Physics_Toss(ent: progs.edict_t):
    trace: world.trace_t = None
    move: list[float] = [0.0, 0.0, 0.0]

    if not SV_RunThink(ent):
        return

    if int(ent.v.flags) & server.FL_ONGROUND:
        return

    SV_CheckVelocity(ent)

    if ent.v.movetype != server.MOVETYPE_FLY and ent.v.movetype != server.MOVETYPE_FLYMISSILE:
        SV_AddGravity(ent)

    mathlib.VectorMA(ent.v.angles, host.host_frametime, ent.v.avelocity, ent.v.angles)

    mathlib.VectorScal(ent.v.velocity, host.host_frametime, move)
    trace = SV_PushEntity(ent, move)

    if trace.fraction == 1:
        return

    if ent.free:
        return

    if ent.v.movetype == server.MOVETYPE_BOUNCE:
        backoff = 1.5
    else:
        backoff = 1

    ClipVelocity(ent.v.velocity, trace.plane.normal, ent.v.velocity, backoff)

    if trace.plane.normal[2] > 0.7:
        if ent.v.velocity[2] < 60 or ent.v.movetype != server.MOVETYPE_BOUNCE:
            ent.v.flags = int(ent.v.flags) | server.FL_ONGROUND
            ent.v.groundentity = progs.EDICT_TO_PROG(trace.ent)
            mathlib.VectorCopy(mathlib.vec3_origin, ent.v.velocity)
            mathlib.VectorCopy(mathlib.vec3_origin, ent.v.avelocity)

    SV_CheckWaterTransition(ent)


def SV_Physics_Step(ent: progs.edict_t):

    hitsound: bool = False

    sv_gravity = cvar.Cvar_GetCvar('sv_gravity').value

    if not int(ent.v.flags) & ( server.FL_ONGROUND | server.FL_FLY | server.FL_SWIM ):
        if ent.v.velocity[2] < sv_gravity * -0.1:
            hitsound = True
        else:
            hitsound = False

        SV_AddGravity(ent)
        SV_CheckVelocity(ent)
        SV_FlyMove(ent, host.host_frametime, None)
        world.SV_LinkEdict(ent, True)

        if int(ent.v.flags) & server.FL_ONGROUND:
            if hitsound:
                sv_main.SV_StartSound(ent, 0, 'demon/dland2.wav', 255, 1)

    SV_RunThink(ent)
    SV_CheckWaterTransition(ent)


def SV_Physics():
    pr_edict.pr_global_struct.self = progs.EDICT_TO_PROG(sv_main.sv.edicts)
    pr_edict.pr_global_struct.other = progs.EDICT_TO_PROG(sv_main.sv.edicts)
    pr_edict.pr_global_struct.time = sv_main.sv.time

    pr_exec.PR_ExecuteProgram(pr_edict.pr_global_struct.StartFrame)

    ent: progs.edict_t = sv_main.sv.edicts

    sv_freezenonclients = cvar.Cvar_GetCvar('sv_freezenonclients').value

    entity_cap = 0
    if sv_freezenonclients:
        entity_cap = sv_main.svs.maxclients + 1
    else:
        entity_cap = sv_main.sv.num_edicts

    for i in range(entity_cap):
        if ent.free:
            continue

        if pr_edict.pr_global_struct.force_retouch:
            world.SV_LinkEdict(ent, True)

        if i > 0 and i <= sv_main.svs.maxclients:
            SV_Physics_Client(ent, i)
        elif (ent.v.movetype == server.MOVETYPE_PUSH):
            SV_Physics_Pusher(ent)
        elif ent.v.movetype == server.MOVETYPE_NONE:
            SV_Physics_None(ent)
        elif ent.v.movetype == server.MOVETYPE_NOCLIP:
            SV_Physics_Noclip(ent)
        elif ent.v.movetype == server.MOVETYPE_TOSS or \
            ent.v.movetype == server.MOVETYPE_GIB or \
            ent.v.movetype == server.MOVETYPE_BOUNCE or \
            ent.v.movetype == server.MOVETYPE_FLY or \
            ent.v.movetype == server.MOVETYPE_FLYMISSILE:
            SV_Physics_Toss(ent)
        else:
            sys_sdl_unix.Sys_Error('SV_Physics: bad movetype {ent.v.movetype}')

        ent.sendinterval = False

        if not ent.free and ent.v.nextthink > sv_main.sv.time and \
            ( ent.v.movetype == server.MOVETYPE_STEP or ent.v.movetype == server.MOVETYPE_WALK or ent.v.frame != ent.oldframe):
            j = mathlib.Q_rint(ent.v.nextthink - ent.oldthinktime) * 255
            if j >= 0 and j < 256 and j != 25 and j != 26:
                ent.sendinterval = True

        if pr_edict.pr_global_struct.force_retouch:
            pr_edict.pr_global_struct.force_retouch -= 1

        if not sv_freezenonclients:
            sv_main.sv.time += host.host_frametime

        ent = progs.NEXT_EDICT(ent)

















