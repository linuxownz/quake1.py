#view.py

import math

import OpenGL.GL as gl

import _cmd
import bspfile
import chase
import cl_main
import common
import console
import cvar
import gl_rmain
import gl_texmgr
import gl_vidsdl
import host
import host_cmd
import mathlib
import protocol
import quakedef
import render

v_punchangles = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]  #johnfitz -- copied from cl.punchangle.  0 is current, 1 is previous value
_punch = [0.0, 0.0, 0.0]  # C: static vec3_t punch in V_CalcRefdef (persists between frames)

v_dmg_time = 0.0
v_dmg_roll = 0.0
v_dmg_pitch = 0.0

v_blend : list[float] = [0.0, 0.0, 0.0, 0.0]


def _new_cshift():
    return quakedef.cshift_t([0, 0, 0], 0)


def _copy_cshift(src):
    """C struct assignment: dest = src (never alias the source object)."""
    return quakedef.cshift_t(list(src.destcolor), src.percent)


def _ensure_cshifts():
    """cl.cshifts / cl.prev_cshifts are cshift_t[NUM_CSHIFTS] in C. Make sure they
    exist as NUM_CSHIFTS *distinct* objects with 3-element destcolor lists."""
    cl = cl_main.cl
    for name in ('cshifts', 'prev_cshifts'):
        arr = getattr(cl, name, None)
        if not isinstance(arr, list) or len(arr) < quakedef.NUM_CSHIFTS:
            arr = [_new_cshift() for _ in range(quakedef.NUM_CSHIFTS)]
            setattr(cl, name, arr)
        else:
            for i in range(quakedef.NUM_CSHIFTS):
                c = arr[i]
                if c is None or not isinstance(getattr(c, 'destcolor', None), list) or len(c.destcolor) < 3:
                    arr[i] = _new_cshift()

def angledelta(a: float) -> float:
    a = mathlib.anglemod(a)
    if a > 180:
        a -= 360
    return a


def V_CalcRoll(angles: quakedef.vec3_t, velocity:quakedef.vec3_t) -> float:
    forward: quakedef.vec3_t = [0, 0, 0]
    right: quakedef.vec3_t = [0, 0, 0]
    up: quakedef.vec3_t = [0, 0, 0]

    mathlib.AngleVectors(angles, forward, right, up)

    side = mathlib.DotProduct(velocity, right)
    sign = -1 if side < 0 else 1
    side = math.fabs(side)

    value = cvar.Cvar_GetCvar('cl_rollangle').value
    rollspeed = cvar.Cvar_GetCvar('cl_rollspeed').value

    if side < rollspeed:
        side = side * value / rollspeed
    else:
        side = value

    return side * sign


def V_CalcBob():

    cl_bobcycle = cvar.Cvar_GetCvar('cl_bobcycle').value
    cl_bobup    = cvar.Cvar_GetCvar('cl_bobup').value
    cl_bob      = cvar.Cvar_GetCvar('cl_bob').value

    if not cl_bobcycle:
        return 0.0

    cycle = cl_main.cl.time - int(cl_main.cl.time/cl_bobcycle)*cl_bobcycle
    cycle /= cl_bobcycle

    if cycle <  cl_bobup:
        cycle = math.pi * cycle / cl_bobup
    else:
        cycle = math.pi + math.pi * ( cycle - cl_bobup ) / ( 1.0 - cl_bobup)

    bob = math.sqrt(cl_main.cl.velocity[0] * cl_main.cl.velocity[0] + cl_main.cl.velocity[1] * cl_main.cl.velocity[1] ) * cl_bob
    bob = bob * 0.3 + bob * 0.7 * math.sin(cycle)

    if bob > 4:
        bob = 4
    elif bob < -7:
        bob = -7

    return bob

def V_cshift_f():
    cshift_empty.destcolor[0] = int(_cmd.Cmd_Argv(1))
    cshift_empty.destcolor[1] = int(_cmd.Cmd_Argv(2))
    cshift_empty.destcolor[2] = int(_cmd.Cmd_Argv(3))
    cshift_empty.percent      = int(_cmd.Cmd_Argv(4))

def V_BonusFlash_f():
    _ensure_cshifts()
    cl_main.cl.cshifts[quakedef.CSHIFT_BONUS].destcolor[0] = 215
    cl_main.cl.cshifts[quakedef.CSHIFT_BONUS].destcolor[1] = 186
    cl_main.cl.cshifts[quakedef.CSHIFT_BONUS].destcolor[2] = 69
    cl_main.cl.cshifts[quakedef.CSHIFT_BONUS].percent      = 50

def V_StartPitchDrift():
    if cl_main.cl.laststop == cl_main.cl.time:
        return

    if cl_main.cl.nodrift or not cl_main.cl.pitchvel:
        cl_main.cl.pitchvel = cvar.Cvar_GetCvar('v_centerspeed').value
        cl_main.cl.nodrift = False
        cl_main.cl.driftmove = 0

def V_StopPitchDrift():
    cl_main.cl.laststop = cl_main.cl.time
    cl_main.cl.nodrift = True
    cl_main.cl.pitchvel = 0

def V_Init():
    global v_centermove
    global v_centerspeed

    global scr_ofsx
    global scr_ofsy
    global scr_ofsz
    global cl_rollspeed
    global cl_rollangle
    global cl_bob
    global cl_bobcycle
    global cl_bobup

    global v_kicktime
    global v_kickroll
    global v_kickpitch
    global v_gunkick

    global v_iyaw_cycle
    global v_iroll_cycle
    global v_ipitch_cycle
    global v_iyaw_level
    global v_iroll_level
    global v_ipitch_level

    global v_idlescale

    global crosshair

    global gl_cshiftpercent
    global gl_cshiftpercent_contents
    global gl_cshiftpercent_damage
    global gl_cshiftpercent_bonus
    global gl_cshiftpercent_powerup

    global cshift_empty, cshift_water, cshift_slime, cshift_lava

    cshift_empty = quakedef.cshift_t([130, 80, 50],0)
    cshift_water = quakedef.cshift_t([130, 80, 50],128)
    cshift_slime = quakedef.cshift_t([0, 25, 5],150)
    cshift_lava  = quakedef.cshift_t([255, 80, 0],150)

    _cmd.Cmd_AddCommand('v_cshift', V_cshift_f)
    _cmd.Cmd_AddCommand('bf', V_BonusFlash_f)
    _cmd.Cmd_AddCommand('centerview', V_StartPitchDrift)

    v_centermove  = {'name': 'v_centermove',  'value':'0.15', 'flags':cvar.CVAR_NONE}
    v_centerspeed = {'name': 'v_centerspeed', 'value':'500',  'flags':cvar.CVAR_NONE}

    scr_ofsx = {'name':"scr_ofsx",'value':"0", 'flags':cvar.CVAR_NONE};
    scr_ofsy = {'name':"scr_ofsy",'value':"0", 'flags':cvar.CVAR_NONE};
    scr_ofsz = {'name':"scr_ofsz",'value':"0", 'flags':cvar.CVAR_NONE};

    cl_rollspeed = {'name':"cl_rollspeed", 'value':"200", 'flags':cvar.CVAR_NONE};
    cl_rollangle = {'name':"cl_rollangle", 'value':"2.0", 'flags':cvar.CVAR_NONE};

    cl_bob      = {'name':"cl_bob",'value':"0.02", 'flags':cvar.CVAR_NONE};
    cl_bobcycle = {'name':"cl_bobcycle",'value':"0.6", 'flags':cvar.CVAR_NONE}
    cl_bobup    = {'name':"cl_bobup",'value':"0.5", 'flags':cvar.CVAR_NONE};

    v_kicktime  = {'name':"v_kicktime", 'value':"0.5", 'flags':cvar.CVAR_NONE};
    v_kickroll  = {'name':"v_kickroll", 'value':"0.6", 'flags':cvar.CVAR_NONE};
    v_kickpitch = {'name':"v_kickpitch", 'value':"0.6", 'flags':cvar.CVAR_NONE};
    v_gunkick   = {'name':"v_gunkick", 'value':"1", 'flags':cvar.CVAR_NONE}; #johnfitz

    v_iyaw_cycle   = {'name':"v_iyaw_cycle", 'value':"2", 'flags':cvar.CVAR_NONE};
    v_iroll_cycle  = {'name':"v_iroll_cycle", 'value':"0.5", 'flags':cvar.CVAR_NONE};
    v_ipitch_cycle = {'name':"v_ipitch_cycle", 'value':"1", 'flags':cvar.CVAR_NONE};
    v_iyaw_level   = {'name':"v_iyaw_level", 'value':"0.3", 'flags':cvar.CVAR_NONE};
    v_iroll_level  = {'name':"v_iroll_level", 'value':"0.1", 'flags':cvar.CVAR_NONE};
    v_ipitch_level = {'name':"v_ipitch_level", 'value':"0.3", 'flags':cvar.CVAR_NONE};

    v_idlescale = {'name':"v_idlescale", 'value':"0", 'flags':cvar.CVAR_NONE};

    crosshair = {'name':"crosshair", 'value':"0", 'flags':cvar.CVAR_ARCHIVE};

    gl_cshiftpercent          = {'name':"gl_cshiftpercent", 'value':"100", 'flags':cvar.CVAR_NONE};
    gl_cshiftpercent_contents = {'name':"gl_cshiftpercent_contents", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm
    gl_cshiftpercent_damage   = {'name':"gl_cshiftpercent_damage", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm
    gl_cshiftpercent_bonus    = {'name':"gl_cshiftpercent_bonus", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm
    gl_cshiftpercent_powerup  = {'name':"gl_cshiftpercent_powerup", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm

    r_viewmodel_quake = {'name':"r_viewmodel_quake", 'value':"0", 'flags':cvar.CVAR_ARCHIVE};

    cvar.Cvar_RegisterVariable(v_centermove)
    cvar.Cvar_RegisterVariable(v_centerspeed)

    cvar.Cvar_RegisterVariable(v_iyaw_cycle  )
    cvar.Cvar_RegisterVariable(v_iroll_cycle )
    cvar.Cvar_RegisterVariable(v_ipitch_cycle)
    cvar.Cvar_RegisterVariable(v_iyaw_level  )
    cvar.Cvar_RegisterVariable(v_iroll_level )
    cvar.Cvar_RegisterVariable(v_ipitch_level)

    cvar.Cvar_RegisterVariable(v_idlescale)
    cvar.Cvar_RegisterVariable(crosshair)
    cvar.Cvar_RegisterVariable(gl_cshiftpercent         )
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_contents)
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_damage  )
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_bonus   )
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_powerup )

    cvar.Cvar_RegisterVariable(scr_ofsx)
    cvar.Cvar_RegisterVariable(scr_ofsy)
    cvar.Cvar_RegisterVariable(scr_ofsz)
    cvar.Cvar_RegisterVariable(cl_rollspeed)
    cvar.Cvar_RegisterVariable(cl_rollangle)
    cvar.Cvar_RegisterVariable(cl_bob     )
    cvar.Cvar_RegisterVariable(cl_bobcycle)
    cvar.Cvar_RegisterVariable(cl_bobup   )

    cvar.Cvar_RegisterVariable(v_kicktime )
    cvar.Cvar_RegisterVariable(v_kickroll )
    cvar.Cvar_RegisterVariable(v_kickpitch)
    cvar.Cvar_RegisterVariable(v_gunkick  )

    cvar.Cvar_RegisterVariable(r_viewmodel_quake)

def V_SetContentsColor (contents):
    _ensure_cshifts()

    # CONTENTS_EMPTY -1, SOLID -2, WATER -3, SLIME -4, LAVA -5, SKY -6
    if contents in (-1, -2, -6):
        src = cshift_empty
    elif contents == -5:
        src = cshift_lava
    elif contents == -4:
        src = cshift_slime
    else:
        src = cshift_water

    cl_main.cl.cshifts[quakedef.CSHIFT_CONTENTS] = _copy_cshift(src)

def V_CalcBlend():
    _ensure_cshifts()
    cshiftpercent_cvars = [
        cvar.Cvar_GetCvar('gl_cshiftpercent_contents').value,
        cvar.Cvar_GetCvar('gl_cshiftpercent_damage').value,
        cvar.Cvar_GetCvar('gl_cshiftpercent_bonus').value,
        cvar.Cvar_GetCvar('gl_cshiftpercent_powerup').value
    ]

    r = 0
    g = 0
    b = 0
    a = 0
    a2 = 0

    gl_cshiftpercent = cvar.Cvar_GetCvar('gl_cshiftpercent').value
    for j in range(quakedef.NUM_CSHIFTS):
        if not gl_cshiftpercent:
            continue

        if cl_main.cl.intermission and j != quakedef.CSHIFT_CONTENTS:
            continue

        a2 = ((cl_main.cl.cshifts[j].percent * gl_cshiftpercent) / 100.0) / 255.0
        a2 *= (cshiftpercent_cvars[j] / 100.0)

        if not a2:
            continue

        a = a + a2*(1-a)
        a2 = a2/a if a else 0.0

        r = r*(1-a2) + cl_main.cl.cshifts[j].destcolor[0]*a2
        g = g*(1-a2) + cl_main.cl.cshifts[j].destcolor[1]*a2
        b = b*(1-a2) + cl_main.cl.cshifts[j].destcolor[2]*a2

    v_blend[0] = r/255.0
    v_blend[1] = g/255.0
    v_blend[2] = b/255.0
    v_blend[3] = a

    v_blend[3] = min(v_blend[3], 1)
    v_blend[3] = max(v_blend[3], 0)

def V_DriftPitch():

    if host_cmd.noclip_anglehack or not cl_main.cl.onground or cl_main.cls.demoplayback:
        cl_main.cl.driftmove = 0
        cl_main.cl.pitchvel = 0
        return

    cl_forwardspeed = cvar.Cvar_GetCvar('cl_forwardspeed').value
    v_centermove = cvar.Cvar_GetCvar('v_centermove').value
    v_centerspeed = cvar.Cvar_GetCvar('v_centerspeed').value
    lookspring = cvar.Cvar_GetCvar('lookspring').value

    if cl_main.cl.nodrift:
        if math.fabs(cl_main.cl.cmd.forwardmove) < cl_forwardspeed:
            cl_main.cl.driftmove = 0
        else:
            cl_main.cl.driftmove += host.host_frametime

        if cl_main.cl.driftmove > v_centermove:  # noqa: SIM102
            if lookspring:
                V_StartPitchDrift()

        return

    delta = cl_main.cl.idealpitch - cl_main.cl.viewangles[quakedef.PITCH]

    if not delta:
        cl_main.cl.pitchvel = 0
        return

    move = host.host_frametime * cl_main.cl.pitchvel
    cl_main.cl.pitchvel += host.host_frametime * v_centerspeed

    if delta > 0:
        if move > delta:
            cl_main.cl.pitchvel = 0
            move = delta
        cl_main.cl.viewangles[quakedef.PITCH] += move

    elif delta < 0:
        if move > -delta:
            cl_main.cl.pitchvel = 0
            move = -delta

        cl_main.cl.viewangles[quakedef.PITCH] -= move

def V_ParseDamage():
    forward: quakedef.vec3_t = [0, 0, 0]
    right: quakedef.vec3_t = [0, 0, 0]
    up: quakedef.vec3_t = [0, 0, 0]
    _from: quakedef.vec3_t = [0, 0, 0]

    armor = common.MSG_ReadByte()
    blood = common.MSG_ReadByte()

    for i in range(3):
        _from[i] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

    count = blood * 0.5 + armor * 0.5
    count = max(count, 10)

    _ensure_cshifts()
    cl_main.cl.faceanimtime = cl_main.cl.time + 0.2

    cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent += 3 * count
    cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent = max(cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent, 0);
    cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent = min(cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent, 150);

    if armor > blood:
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[0] = 200;
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[1] = 100;
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[2] = 100;
    elif armor:
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[0] = 220;
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[1] = 50;
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[2] = 50;
    else:
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[0] = 255;
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[1] = 0;
        cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].destcolor[2] = 0;

    ent = cl_main.cl_entities[cl_main.cl.viewentity]

    mathlib.VectorSubtract(_from, ent.origin, _from)
    mathlib.VectorNormalize(_from)

    mathlib.AngleVectors(ent.angles, forward, right, up)

    global v_dmg_pitch, v_dmg_roll, v_dmg_time

    side = mathlib.DotProduct(_from, right)
    v_dmg_roll = count * side * cvar.Cvar_GetCvar('v_kickroll').value

    side = mathlib.DotProduct(_from, forward)
    v_dmg_pitch = count * side * cvar.Cvar_GetCvar('v_kickpitch').value

    v_dmg_time = cvar.Cvar_GetCvar('v_kicktime').value


def V_CalcPowerupCshift():
    _ensure_cshifts()

    if cl_main.cl.items & quakedef.IT_QUAD:
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[0] = 0
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[1] = 0
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[2] = 255
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].percent = 30
    elif cl_main.cl.items & quakedef.IT_SUIT:
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[0] = 0
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[1] = 255
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[2] = 0
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].percent = 20
    elif cl_main.cl.items & quakedef.IT_INVISIBILITY:
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[0] = 100
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[1] = 100
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[2] = 100
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].percent = 100
    elif cl_main.cl.items & quakedef.IT_INVULNERABILITY:
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[0] = 255
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[1] = 255
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].destcolor[2] = 0
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].percent = 30
    else:
        cl_main.cl.cshifts[quakedef.CSHIFT_POWERUP].percent = 0


def V_UpdateBlend():
    _ensure_cshifts()

    V_CalcPowerupCshift()

    blend_changed = False

    for i in range(quakedef.NUM_CSHIFTS):
        if cl_main.cl.cshifts[i].percent != cl_main.cl.prev_cshifts[i].percent:
            blend_changed = True
            cl_main.cl.prev_cshifts[i].percent = cl_main.cl.cshifts[i].percent

        for j in range(3):
            if cl_main.cl.cshifts[i].destcolor[j] != cl_main.cl.prev_cshifts[i].destcolor[j]:
                blend_changed = True
                cl_main.cl.prev_cshifts[i].destcolor[j] = cl_main.cl.cshifts[i].destcolor[j]

    cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent -= host.host_frametime*150
    cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent = max(0, cl_main.cl.cshifts[quakedef.CSHIFT_DAMAGE].percent)

    cl_main.cl.cshifts[quakedef.CSHIFT_BONUS].percent -= host.host_frametime*100
    cl_main.cl.cshifts[quakedef.CSHIFT_BONUS].percent = max(0, cl_main.cl.cshifts[quakedef.CSHIFT_BONUS].percent)

    if blend_changed:
        V_CalcBlend()


def V_PolyBlend():
    if not cvar.Cvar_GetCvar('gl_polyblend').value or not v_blend[3]:
        return

    gl_texmgr.GL_DisableMultitexture()

    gl.glDisable(gl.GL_ALPHA_TEST)
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glDisable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_BLEND)

    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity ()
    gl.glOrtho (0, 1, 1, 0, -99999, 99999)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity ()

    gl.glBegin (gl.GL_QUADS)

    gl.glColor4fv (v_blend)

    gl.glVertex2f (0,0)
    gl.glVertex2f (1, 0)
    gl.glVertex2f (1, 1)
    gl.glVertex2f (0, 1)
    gl.glEnd ()

    gl.glDisable(gl.GL_BLEND)
    gl.glEnable (gl.GL_DEPTH_TEST)
    gl.glEnable (gl.GL_TEXTURE_2D)
    gl.glEnable (gl.GL_ALPHA_TEST)



oldyaw = 0
oldpitch = 0
def CalcGunAngle():
    global oldpitch, oldyaw

    yaw = gl_rmain.r_refdef.viewangles[quakedef.YAW]
    pitch = -gl_rmain.r_refdef.viewangles[quakedef.PITCH]

    yaw = angledelta(yaw - gl_rmain.r_refdef.viewangles[quakedef.YAW]) * 0.4
    yaw = min(yaw, 10)
    yaw = max(yaw, -10)

    pitch = angledelta(-pitch - gl_rmain.r_refdef.viewangles[quakedef.PITCH]) * 0.4
    pitch = min(pitch, 10)
    pitch = max(pitch, -10)

    move = host.host_frametime * 20

    if yaw > oldyaw:
        yaw = min(yaw, oldyaw + move)
    else:
        yaw = max(yaw, oldyaw - move)

    if pitch > oldpitch:
        pitch = min(pitch, oldpitch + move)
    else:
        pitch = max(pitch, oldpitch - move)

    oldyaw = yaw
    oldpitch = pitch

    v_iroll_level = cvar.Cvar_GetCvar('v_iroll_level').value
    v_ipitch_level = cvar.Cvar_GetCvar('v_ipitch_level').value
    v_iyaw_level = cvar.Cvar_GetCvar('v_iyaw_level').value
    v_iroll_cycle = cvar.Cvar_GetCvar('v_iroll_cycle').value
    v_ipitch_cycle = cvar.Cvar_GetCvar('v_ipitch_cycle').value
    v_iyaw_cycle = cvar.Cvar_GetCvar('v_iyaw_cycle').value
    v_idlescale = cvar.Cvar_GetCvar('v_idlescale').value

    cl_main.cl.viewent.angles[quakedef.YAW] = gl_rmain.r_refdef.viewangles[quakedef.YAW] + yaw
    cl_main.cl.viewent.angles[quakedef.PITCH] = - (gl_rmain.r_refdef.viewangles[quakedef.PITCH] + pitch)

    cl_main.cl.viewent.angles[quakedef.ROLL]  -= v_idlescale* math.sin(cl_main.cl.time*v_iroll_cycle) * v_iroll_level
    cl_main.cl.viewent.angles[quakedef.PITCH] -= v_idlescale* math.sin(cl_main.cl.time*v_ipitch_cycle) * v_ipitch_level
    cl_main.cl.viewent.angles[quakedef.YAW]   -= v_idlescale* math.sin(cl_main.cl.time*v_iyaw_cycle) * v_iyaw_level


def V_BoundOffsets():
    ent: render.entity_t = cl_main.cl_entities[cl_main.cl.viewentity]

    if (gl_rmain.r_refdef.vieworg[0] < ent.origin[0] - 14):
        gl_rmain.r_refdef.vieworg[0] = ent.origin[0] - 14
    elif (gl_rmain.r_refdef.vieworg[0] > ent.origin[0] + 14):
        gl_rmain.r_refdef.vieworg[0] = ent.origin[0] + 14
    if (gl_rmain.r_refdef.vieworg[1] < ent.origin[1] - 14):
        gl_rmain.r_refdef.vieworg[1] = ent.origin[1] - 14
    elif (gl_rmain.r_refdef.vieworg[1] > ent.origin[1] + 14):
        gl_rmain.r_refdef.vieworg[1] = ent.origin[1] + 14
    if (gl_rmain.r_refdef.vieworg[2] < ent.origin[2] - 22):
        gl_rmain.r_refdef.vieworg[2] = ent.origin[2] - 22
    elif (gl_rmain.r_refdef.vieworg[2] > ent.origin[2] + 30):
        gl_rmain.r_refdef.vieworg[2] = ent.origin[2] + 30


def V_AddIdle():

    v_idlescale   = cvar.Cvar_GetCvar('v_idlescale').value
    v_iroll_cycle = cvar.Cvar_GetCvar('v_iroll_cycle').value
    v_ipitch_cycle = cvar.Cvar_GetCvar('v_ipitch_cycle').value
    v_iyaw_cycle = cvar.Cvar_GetCvar('v_iyaw_cycle').value
    v_iroll_level = cvar.Cvar_GetCvar('v_iroll_level').value
    v_ipitch_level = cvar.Cvar_GetCvar('v_ipitch_level').value
    v_iyaw_level = cvar.Cvar_GetCvar('v_iyaw_level').value

    gl_rmain.r_refdef.viewangles[quakedef.ROLL]  += v_idlescale * math.sin(cl_main.cl.time*v_iroll_cycle) * v_iroll_level;
    gl_rmain.r_refdef.viewangles[quakedef.PITCH] += v_idlescale * math.sin(cl_main.cl.time*v_ipitch_cycle) * v_ipitch_level
    gl_rmain.r_refdef.viewangles[quakedef.YAW]   += v_idlescale * math.sin(cl_main.cl.time*v_iyaw_cycle) * v_iyaw_level;


def V_CalcViewRoll():
    global v_dmg_time

    side = V_CalcRoll(cl_main.cl_entities[cl_main.cl.viewentity].angles, cl_main.cl.velocity)
    gl_rmain.r_refdef.viewangles[quakedef.ROLL] += side

    if v_dmg_time > 0:
        v_kicktime = cvar.Cvar_GetCvar('v_kicktime').value
        gl_rmain.r_refdef.viewangles[quakedef.ROLL] += v_dmg_time/v_kicktime*v_dmg_roll;
        gl_rmain.r_refdef.viewangles[quakedef.PITCH] += v_dmg_time/v_kicktime*v_dmg_pitch
        v_dmg_time -= host.host_frametime;

    if cl_main.cl.stats[quakedef.STAT_HEALTH] <= 0:
        gl_rmain.r_refdef.viewangles[quakedef.ROLL] = 80
        return

def V_CalcIntermissionRefdef():

    ent = cl_main.cl_entities[cl_main.cl.viewentity]
    view = cl_main.cl.viewent

    mathlib.VectorCopy(ent.origin, gl_rmain.r_refdef.vieworg)
    mathlib.VectorCopy(ent.angles, gl_rmain.r_refdef.viewangles)
    view.model = None

    old = cvar.Cvar_GetCvar('v_idlescale').value
    cvar.Cvar_SetValue('v_idlescale', 1)
    V_AddIdle()
    cvar.Cvar_SetValue('v_idlescale', old)


oldz = 0.0
def V_CalcRefdef():
    global oldz

    V_DriftPitch()

    ent = cl_main.cl_entities[cl_main.cl.viewentity]
    view = cl_main.cl.viewent

    ent.angles[quakedef.YAW]   = cl_main.cl.viewangles[quakedef.YAW]
    ent.angles[quakedef.PITCH] = -cl_main.cl.viewangles[quakedef.PITCH]

    bob = V_CalcBob()

    mathlib.VectorCopy(ent.origin, gl_rmain.r_refdef.vieworg)
    gl_rmain.r_refdef.vieworg[2] += cl_main.cl.viewheight + bob

    gl_rmain.r_refdef.vieworg[0] += 1.0/32
    gl_rmain.r_refdef.vieworg[1] += 1.0/32
    gl_rmain.r_refdef.vieworg[2] += 1.0/32

    mathlib.VectorCopy(cl_main.cl.viewangles, gl_rmain.r_refdef.viewangles)
    V_CalcViewRoll()
    V_AddIdle()

    angles: quakedef.vec3_t = [0, 0, 0]
    forward: quakedef.vec3_t = [0, 0, 0]
    right: quakedef.vec3_t = [0, 0, 0]
    up: quakedef.vec3_t = [0, 0, 0]

    angles[quakedef.PITCH] = -ent.angles[quakedef.PITCH]
    angles[quakedef.YAW] =    ent.angles[quakedef.YAW]
    angles[quakedef.ROLL] =   ent.angles[quakedef.ROLL]

    mathlib.AngleVectors(angles, forward, right, up)

    scr_ofsx = cvar.Cvar_GetCvar('scr_ofsx').value
    scr_ofsy = cvar.Cvar_GetCvar('scr_ofsy').value
    scr_ofsz = cvar.Cvar_GetCvar('scr_ofsz').value

    if cl_main.cl.maxclients <= 1:
        for i in range(3):
            gl_rmain.r_refdef.vieworg[i] += scr_ofsx*forward[i] + scr_ofsy*right[i] + scr_ofsz*up[i]

    V_BoundOffsets()

    mathlib.VectorCopy(cl_main.cl.viewangles, view.angles)

    CalcGunAngle()

    mathlib.VectorCopy(ent.origin, view.origin)
    view.origin[2] += cl_main.cl.viewheight

    for i in range(3):
        view.origin[i] += forward[i] * bob * 0.4
    view.origin[2] += bob

    if cvar.Cvar_GetCvar('r_viewmodel_quake').value:
        scr_viewsize = cvar.Cvar_GetCvar('scr_viewsize').value
        if scr_viewsize == 110:
            view.origin[2] += 1
        elif scr_viewsize == 100:
            view.origin[2] += 2
        elif scr_viewsize == 90:
            view.origin[2] += 1
        elif scr_viewsize == 80:
            view.origin[2] += 0.5

    if ent.lerpflags & render.LERP_FINISH:
        view.lerpflags |= render.LERP_FINISH
        view.lerpfinish = ent.lerpfinish
    else:
        view.lerpflags &= ~render.LERP_FINISH

    view.model = cl_main.cl.model_precache[cl_main.cl.stats[quakedef.STAT_WEAPON]]
    view.frame = cl_main.cl.stats[quakedef.STAT_WEAPONFRAME];
    view.colormap = gl_vidsdl._vid.colormap;
    view.scale = protocol.ENTSCALE_DEFAULT;

    v_gunkick = cvar.Cvar_GetCvar('v_gunkick').value
    punch = _punch

    if v_gunkick == 1:
        mathlib.VectorAdd(gl_rmain.r_refdef.viewangles, cl_main.cl.punchangle, gl_rmain.r_refdef.viewangles)
    elif v_gunkick == 2:
        for i in range(3):
            if punch[i] != v_punchangles[0][i]:
                delta = (v_punchangles[0][i]-v_punchangles[1][i]) * host.host_frametime * 10

                if delta > 0:
                    punch[i] = min(punch[i]+delta, v_punchangles[0][i])
                elif delta < 0:
                    punch[i] = max(punch[i]+delta, v_punchangles[0][i])

        mathlib.VectorAdd(gl_rmain.r_refdef.viewangles, punch, gl_rmain.r_refdef.viewangles)

    if not host_cmd.noclip_anglehack and cl_main.cl.onground and ent.origin[2] - oldz > 0:
        steptime = cl_main.cl.time - cl_main.cl.oldtime
        steptime = max(steptime, 0)

        oldz += steptime * 80
        oldz = min(oldz, ent.origin[2])
        if ent.origin[2] - oldz > 12:
            oldz = ent.origin[2] - 12
        gl_rmain.r_refdef.vieworg[2] += oldz - ent.origin[2]
        view.origin[2] += oldz - ent.origin[2]
    else:
        oldz = ent.origin[2]

    if cvar.Cvar_GetCvar('chase_active').value:
        chase.Chase_UpdateForDrawing()


def V_RestoreAngles():
    ent = cl_main.cl_entities[cl_main.cl.viewentity]
    mathlib.VectorCopy(ent.msg_angles[0], ent.angles)

def V_RenderView():

    if console.con_forcedup:
        return

    if cl_main.cl.intermission:
        V_CalcIntermissionRefdef()
    elif not cl_main.cl.paused:
        V_CalcRefdef()

    gl_rmain.R_RenderView()

    V_PolyBlend()










