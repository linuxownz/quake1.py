#sv_move.py

import math
import random

import mathlib
import progs
import pr_cmds
import pr_edict
import quakedef
import server
import sv_main
import world

STEPSIZE = 18

c_yes = 0
c_no = 0

def SV_CheckBottom(ent: progs.edict_t) -> bool:
    global c_yes, c_no

    mins: quakedef.vec3_t = [0, 0, 0]
    maxs: quakedef.vec3_t = [0, 0, 0]
    start: quakedef.vec3_t = [0, 0, 0]
    stop: quakedef.vec3_t = [0, 0, 0]

    mathlib.VectorAdd(ent.v.origin, ent.v.mins, mins)
    mathlib.VectorAdd(ent.v.origin, ent.v.maxs, maxs)

    start[2] = mins[2] - 1

    goto = False
    for x in range(2):
        for y in range(2):
            start[0] = maxs[0] if x else mins[0]
            start[1] = maxs[1] if y else mins[1]
            if world.SV_PointContents(start) !=  quakedef.CONTENTS_SOLID:
                goto = True
                break
        if goto:
            break
    if not goto:
        c_yes += 1
        return True

    c_no += 1

    start[2] = mins[2]

    start[0] = stop[0] = (mins[0] + maxs[0])*0.5;
    start[1] = stop[1] = (mins[1] + maxs[1])*0.5;
    stop[2] = start[2] - 2*STEPSIZE;
    trace = world.SV_Move (start, mathlib.vec3_origin, mathlib.vec3_origin, stop, True, ent)

    if trace.fraction == 1.0:
        return False

    mid = bottom = trace.endpos[2]

    for x in range(2):
        for y in range(2):
            start[0] = stop[0] = maxs[0] if x else mins[0]
            start[1] = stop[1] = maxs[0] if y else mins[0]

            trace = world.SV_Move(start, mathlib.vec3_origin, mathlib.vec3_origin, stop, True, ent)

            if trace.fraction != 1.0 and trace.endpos[2] > bottom:
                bottom = trace.endpos[2]

            if trace.fraction == 1.0 or mid - trace.endpos[2] > STEPSIZE:
                return False

    c_yes += 1

    return True


def SV_movestep(ent: progs.edict_t, move: quakedef.vec3_t, relink: bool) -> bool:
    oldorg: quakedef.vec3_t = [0, 0, 0]
    neworg: quakedef.vec3_t = [0, 0, 0]
    end   : quakedef.vec3_t = [0, 0, 0]

    mathlib.VectorCopy(ent.v.origin, oldorg)
    mathlib.VectorAdd(ent.v.origin, move, neworg)

    if int(ent.v.flags) & ( server.FL_SWIM | server.FL_FLY ):
        for i in range(1):
            mathlib.VectorAdd(ent.v.origin, move, neworg)
            enemy = progs.PROG_TO_EDICT(ent.v.enemy)

            if i == 0 and not sv_main.sv.edicts.index(enemy):
                dz = ent.v.origin[2] - progs.PROG_TO_EDICT(ent.v.enemy).v.origin[2]

                if dz > 40:
                    neworg[2] -=8
                if dz < 30:
                    neworg[2] += 8

                trace = world.SV_Move(ent.v.origin, ent.v.mins, ent.v.maxs, neworg, False, ent)

                if trace.fraction == 1:
                    if int(ent.v.flags) & server.FL_SWIM and world.SV_PointContents(trace.endpos) == quakedef.CONTENTS_EMPTY:
                        return False

                    mathlib.VectorCopy(trace.endpos, ent.v.origin)
                    if relink:
                        world.SV_LinkEdict(ent, True)
                    return True

                try:
                    if sv_main.sv.edicts.index(enemy):
                        break
                except Exception:  # noqa: BLE001
                    pass

        return False

    neworg[2] += STEPSIZE
    mathlib.VectorCopy(neworg, end)
    end[2] -= STEPSIZE * 2

    trace = world.SV_Move(neworg, ent.v.mins, ent.v.maxs, end, False, ent)

    if trace.allsolid:
        return False

    if trace.startsolid:
        neworg[2] -= STEPSIZE
        trace = world.SV_Move(neworg, ent.v.mins, ent.v.maxs, end, False, ent)
        if trace.allsolid or trace.startsolid:
            return False

    if trace.fraction == 1:
        if int(ent.v.flags) & server.FL_PARTIALGROUND:
            mathlib.VectorAdd(ent.v.origin, move, ent.v.origin)
            if relink:
                world.SV_LinkEdict(ent, True)
            ent.v.flags = int(ent.v.flags) & ~server.FL_ONGROUND
            return Trueo
        return False

    mathlib.VectorCopy(trace.endpos, ent.v.origin)

    if not SV_CheckBottom(ent):
        if int(ent.v.flags) & server.FL_PARTIALGROUND:
            if relink:
                world.SV_LinkEdict(ent, True)
            return True

        mathlib.VectorCopy(oldorg, ent.v.origin)
        return False

    if int(ent.v.flags) & server.FL_PARTIALGROUND:
        ent.v.flags = int(ent.v.flags) & ~server.FL_PARTIALGROUND

    ent.v.groundentity = progs.EDICT_TO_PROG(trace.ent)

    if relink:
        world.SV_LinkEdict(ent, True)
    return True

def SV_StepDirection(ent: progs.edict_t, yaw: float, dist: float) -> bool:
    move: quakedef.vec3_t = [0, 0, 0]
    oldorigin: quakedef.vec3_t = [0, 0, 0]

    ent.v.ideal_yaw = yaw
    pr_cmds.PF_changeyaw()

    yaw = yaw * math.pi * 2 / 360

    move[0] = math.cos(yaw) * dist
    move[1] = math.sin(yaw) * dist
    move[2] = 0

    mathlib.VectorCopy(ent.v.origin, oldorigin)
    if SV_movestep(ent, move, False):
        delta = ent.v.angles[quakedef.YAW] - ent.v.ideal_yaw
        if delta > 45 and delta < 315:
            mathlib.VectorCopy(oldorigin, ent.v.origin)

        world.SV_LinkEdict(ent, True)
        return True

    world.SV_LinkEdict(ent, True)

    return False


def SV_FixCheckBottom(ent: progs.edict_t):
    ent.v.flags = int(ent.v.flags) | server.FL_PARTIALGROUND


DI_NODIR = -1

def SV_NewChaseDir(actor: progs.edict_t, enemy: progs.edict_t, dist: float):
    d:list[float] = [0, 0, 0]

    olddir = mathlib.anglemod(int(actor.v.ideal_yaw/45) * 45)
    turnaround = mathlib.anglemod(olddir - 180)

    deltax = enemy.v.origin[0] - actor.v.origin[0]
    deltay = enemy.v.origin[1] - actor.v.origin[1]

    if deltax > 10:
        d[1] = 0
    elif deltax < -10:
        d[1] = 180
    else:
        d[1] = DI_NODIR

    if deltay < -10:
        d[2] = 270
    elif deltay > 10:
        d[2] = 90
    else:
        d[2] = DI_NODIR

    if d[1] != DI_NODIR and d[2] != DI_NODIR:
        if d[1] == 0:
            tdir = 45 if d[2] == 90 else 315
        else:
            tdir = 135 if d[2] == 90 else 215

        if tdir != turnaround and SV_StepDirection(actor, tdir, dist):
            return

    if (random.randrange(4) & 1) or abs(int(deltay)) > abs(int(deltax)):
        tdir = d[1]
        d[1] = d[2]
        d[2] = tdir

    if d[1] != DI_NODIR and d[1] != turnaround and SV_StepDirection(actor, d[1], dist):
        return

    if d[2] != DI_NODIR and d[2] != turnaround and SV_StepDirection(actor, d[2], dist):
        return

    if olddir != DI_NODIR and SV_StepDirection(actor, olddir, dist):
        return

    if random.randint(0, 32768) & 1:
        for tdir in range(0 , 315, 45):
            if tdir != turnaround and SV_StepDirection(actor, tdir, dist):
                return

    else:
        for tdir in range(315, 0, -45):
            if tdir != turnaround and SV_StepDirection(actor, tdir, dist):
                return

    if turnaround != DI_NODIR and SV_StepDirection(actor, turnaround, dist):
        return

    actor.v.ideal_yaw = olddir

    if not SV_CheckBottom(actor):
        SV_FixCheckBottom(actor)


def SV_CloseEnough(ent: progs.edict_t, goal: progs.edict_t, dist: float) -> bool:
    for i in range(3):
        if goal.v.absmin[i] > ent.v.absmax[i] + dist:
            return False
        if goal.v.absmax[i] < ent.v.absmin[i] - dist:
            return False

    return True


def SV_MoveToGoal():

    ent = progs.PROG_TO_EDICT(pr_edict.pr_global_struct.self)
    goal = progs.PROG_TO_EDICT(ent.v.goalentity)
    dist = progs.G_FLOAT(pr_edict.OFS_PARM0)

    if not int(ent.v.flags) & ( server.FL_ONGROUND | server.FL_FLY | server.FL_SWIM ):
        pr_edict.pr_globals[pr_edict.OFS_RETURN] = 0
        return

    if progs.PROG_TO_EDICT(ent.v.enemy) not in sv_main.sv.edicts and SV_CloseEnough(ent, goal, dist):
        return

    if random.randint(0, 32768) & 3 == 1 or not SV_StepDirection(ent, ent.v.ideal_yaw, dist):
        SV_NewChaseDir(ent, goal, dist)

















