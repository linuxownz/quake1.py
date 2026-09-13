#cl_input.py

import _cmd
import cl_main
import common
import console
import cvar
import host
import mathlib
import net_main
import protocol
import quakedef
from view import V_StartPitchDrift, V_StopPitchDrift


class kbutton_t:
    def __init__(self):
        self.state = -1  # bit 0 = down, bit 1 = stayed down
        self.down: list[int] = [-1, 0]

# Global button instances

in_mlook: kbutton_t = kbutton_t()
in_klook: kbutton_t = kbutton_t()

in_forward: kbutton_t  = kbutton_t()
in_back: kbutton_t     = kbutton_t()
in_lookup: kbutton_t   = kbutton_t()
in_lookdown: kbutton_t = kbutton_t()
in_moveleft: kbutton_t = kbutton_t()
in_moveright: kbutton_t = kbutton_t()
in_up: kbutton_t  = kbutton_t()
in_down: kbutton_t  = kbutton_t()
#in_left: kbutton_t  = kbutton_t()
#in_right: kbutton_t  = kbutton_t()
in_speed: kbutton_t  = kbutton_t()
in_strafe: kbutton_t  = kbutton_t()
in_attack: kbutton_t  = kbutton_t()
in_use: kbutton_t  = kbutton_t()
in_strafe_left  = kbutton_t() # Was 'in_left'
in_strafe_right = kbutton_t() # Was 'in_right'

# Rotation buttons
in_turn_left: kbutton_t     = kbutton_t()
in_turn_right: kbutton_t    = kbutton_t()
in_pitch_up: kbutton_t      = kbutton_t()
in_pitch_down: kbutton_t    = kbutton_t()
in_jump: kbutton_t = kbutton_t()

in_impulse = 0

def KeyDown(b: kbutton_t):
    k = -1
    c = _cmd.Cmd_Argv(1)

    if c:
        k = int(c)


    if k == b.down[0] or k == b.down[1]:
        return

    if not b.down[0] :
        b.down[0] = k
    elif not b.down[1]:
        b.down[1] = k
    else:
        console.Con_Printf('Three keys down for a button')
        return

    if b.state & 1:
        return

    b.state |= 1 + 2

def KeyUp(b: kbutton_t):
    k = 0
    c = _cmd.Cmd_Argv(1)

    if c[0]:
        k = int(c)
    else:
        b.down[0] = b.down[1] = 0
        b.state = 4
        return

    if b.down[0] == k:
        b.down[0] = 0
    elif b.down[1] == k:
        b.down[1] = 0
    else:
        return

    if b.down[0] or b.down[1]:
        return

    if not ( b.state & 1):
        return

    b.state &= ~1
    b.state |= 4


def IN_KLookDown() -> None:
    KeyDown(in_klook)

def IN_KLookUp() -> None:
    KeyUp(in_klook)

def IN_MLookDown() -> None:
    KeyDown(in_mlook)

def IN_MLookUp() -> None:
    KeyUp(in_mlook)
    lookspring = cvar.Cvar_GetCvar('lookspring').value
    if not (in_mlook.state & 1) and lookspring:
        V_StartPitchDrift()

def IN_UpDown() -> None:
    KeyDown(in_up)

def IN_UpUp() -> None:
    KeyUp(in_up)

def IN_DownDown() -> None:
    KeyDown(in_down)

def IN_DownUp() -> None:
    KeyUp(in_down)

def IN_LeftDown() -> None:
    KeyDown(in_turn_left)

def IN_LeftUp() -> None:
    KeyUp(in_turn_left)

def IN_RightDown() -> None:
    KeyDown(in_turn_right)

def IN_RightUp() -> None:
    KeyUp(in_turn_right)

def IN_ForwardDown() -> None:
    KeyDown(in_forward)

def IN_ForwardUp() -> None:
    KeyUp(in_forward)

def IN_BackDown() -> None:
    KeyDown(in_back)

def IN_BackUp() -> None:
    KeyUp(in_back)

def IN_LookupDown() -> None:
    KeyDown(in_lookup)

def IN_LookupUp() -> None:
    KeyUp(in_lookup)

def IN_LookdownDown() -> None:
    KeyDown(in_lookdown)

def IN_LookdownUp() -> None:
    KeyUp(in_lookdown)

def IN_MoveleftDown() -> None:
    KeyDown(in_moveleft)

def IN_MoveleftUp() -> None:
    KeyUp(in_moveleft)

def IN_MoverightDown() -> None:
    KeyDown(in_moveright)

def IN_MoverightUp() -> None:
    KeyUp(in_moveright)

def IN_SpeedDown() -> None:
    KeyDown(in_speed)

def IN_SpeedUp() -> None:
    KeyUp(in_speed)

def IN_StrafeDown() -> None:
    KeyDown(in_strafe)

def IN_StrafeUp() -> None:
    KeyUp(in_strafe)

def IN_AttackDown() -> None:
    KeyDown(in_attack)

def IN_AttackUp() -> None:
    KeyUp(in_attack)

def IN_UseDown() -> None:
    KeyDown(in_use)

def IN_UseUp() -> None:
    KeyUp(in_use)

def IN_JumpDown() -> None:
    KeyDown(in_jump)

def IN_JumpUp() -> None:
    KeyUp(in_jump)

def IN_Impulse() -> None:
    global in_impulse
    in_impulse = int(_cmd.Cmd_Argv(1))


def CL_KeyState(key: kbutton_t) -> float:
    impulsedown = key.state & 2
    impulseup   = key.state & 4
    down        = key.state & 1
    val         = 0

    if impulsedown and not impulseup:
        if down:
            val = 0.5
        else:
            val = 0.

    if impulseup and not impulsedown:
        if down:
            val = 0
        else:
            val = 0

    if not impulsedown and not impulseup:
        if down:
            val = 1.0
        else:
            val = 0

    if impulsedown and impulseup:
        if down:
            val = 0.75
        else:
            val = 0.25

    key.state &= 1

    return val


def CL_AdjustAngles():

    cl_alwaysrun     = cvar.Cvar_GetCvar('cl_alwaysrun').value
    cl_anglespeedkey = cvar.Cvar_GetCvar('cl_anglespeedkey').value
    cl_yawspeed      = cvar.Cvar_GetCvar('cl_yawspeed').value
    cl_pitchspeed    = cvar.Cvar_GetCvar('cl_pitchspeed').value
    cl_maxpitch      = cvar.Cvar_GetCvar('cl_maxpitch').value
    cl_minpitch      = cvar.Cvar_GetCvar('cl_minpitch').value

    if (in_speed.state & 1) ^ ( cl_alwaysrun != 0.0):
        speed = host.host_frametime * cl_anglespeedkey
    else:
        speed = host.host_frametime

    if not ( in_strafe.state & 1):
        cl_main.cl.viewangles[quakedef.YAW] -= speed * cl_yawspeed * CL_KeyState(in_strafe_right)
        cl_main.cl.viewangles[quakedef.YAW] += speed * cl_yawspeed * CL_KeyState(in_strafe_left)
        cl_main.cl.viewangles[quakedef.YAW] = mathlib.anglemod(cl_main.cl.viewangles[quakedef.YAW])

    if in_klook.state & 1:
        V_StopPitchDrift()
        cl_main.cl.viewangles[quakedef.PITCH] -= speed * cl_pitchspeed * CL_KeyState(in_forward)
        cl_main.cl.viewangles[quakedef.PITCH] += speed * cl_pitchspeed * CL_KeyState(in_back)

    up   = CL_KeyState(in_lookup)
    down = CL_KeyState(in_lookdown)

    cl_main.cl.viewangles[quakedef.PITCH] -= speed * cl_pitchspeed * up
    cl_main.cl.viewangles[quakedef.PITCH] += speed * cl_pitchspeed * down

    if up or down:
        V_StopPitchDrift()

    cl_main.cl.viewangles[quakedef.PITCH] = min(cl_main.cl.viewangles[quakedef.PITCH], cl_maxpitch)
    cl_main.cl.viewangles[quakedef.PITCH] = max(cl_main.cl.viewangles[quakedef.PITCH], cl_minpitch)

    cl_main.cl.viewangles[quakedef.ROLL] = min(cl_main.cl.viewangles[quakedef.ROLL], 50)
    cl_main.cl.viewangles[quakedef.ROLL] = max(cl_main.cl.viewangles[quakedef.ROLL], -50)


def CL_BaseMove(command: protocol.usercmd_t):

    if cl_main.cls.signon != quakedef.SIGNONS:
        return

    CL_AdjustAngles()

    command = protocol.usercmd_t()

    cl_sidespeed    = cvar.Cvar_GetCvar('cl_sidespeed').value
    cl_upspeed      = cvar.Cvar_GetCvar('cl_upspeed').value
    cl_forwardspeed = cvar.Cvar_GetCvar('cl_forwardspeed').value
    cl_backspeed    = cvar.Cvar_GetCvar('cl_backspeed').value
    cl_alwaysrun    = cvar.Cvar_GetCvar('cl_alwaysrun').value
    cl_movespeedkey = cvar.Cvar_GetCvar('cl_movespeedkey').value

    if in_strafe.state & 1:
        command.sidemove += cl_sidespeed * CL_KeyState(in_turn_right)
        command.sidemove -= cl_sidespeed * CL_KeyState(in_turn_left)

    command.sidemove += cl_sidespeed * CL_KeyState(in_moveright)
    command.sidemove -= cl_sidespeed * CL_KeyState(in_moveleft)

    command.upmove += cl_upspeed * CL_KeyState(in_up)
    command.upmove -= cl_upspeed * CL_KeyState(in_down)

    if not ( in_klook.state & 1 ):
        command.forwardmove += cl_forwardspeed * CL_KeyState(in_forward)
        command.forwardmove -= cl_backspeed    * CL_KeyState(in_back)

    if ( in_speed.state & 1 ) ^ ( cl_alwaysrun != 0.0 ):
        command.forwardmove *= cl_movespeedkey
        command.sidemove    *= cl_movespeedkey
        command.upmove      *= cl_movespeedkey


def CL_SendMove(command: protocol.usercmd_t):
    global in_impulse

    data: bytearray = bytearray(128)
    buf: common.sizebuf_s = common.sizebuf_s()
    buf.maxsize = 128
    buf.cursize = 0
    buf.data    = data

    cl_main.cl.cmd = command

    common.MSG_WriteByte(buf, protocol.clc_move)
    common.MSG_WriteFloat(buf, cl_main.cl.mtime[0])

    for i in range(3):
        if cl_main.cl.protocol == protocol.PROTOCOL_NETQUAKE:
            common.MSG_WriteAngle(buf, cl_main.cl.viewangles[i], cl_main.cl.protocolflags)
        else:
            common.MSG_WriteAngle16(buf, cl_main.cl.viewangles[i], cl_main.cl.protocolflags)

    common.MSG_WriteShort(buf, command.forwardmove)
    common.MSG_WriteShort(buf, command.sidemove)
    common.MSG_WriteShort(buf, command.upmove)

    bits = 0

    if in_attack.state & 3:
        bits |= 1
    in_attack.state &= ~2

    if in_jump.state & 3:
        bits |= 2
    in_jump.state &= 2

    common.MSG_WriteByte(buf, bits)

    common.MSG_WriteByte(buf, in_impulse)
    in_impulse = 0

    if cl_main.cls.demoplayback:
        return

    cl_main.cl.movemessages += 1
    if cl_main.cl.movemessages <= 2:
        return

    res = net_main.NET_SendUnreliableMessage(cl_main.cls.netcon, buf)

    if res == -1:
        console.Con_Printf('CL_SendMove: lost server connection')
        cl_main.CL_Disconnect()



def CL_InitInput():
    _cmd.Cmd_AddCommand ("+moveup",IN_UpDown);
    _cmd.Cmd_AddCommand ("-moveup",IN_UpUp);
    _cmd.Cmd_AddCommand ("+movedown",IN_DownDown);
    _cmd.Cmd_AddCommand ("-movedown",IN_DownUp);
    _cmd.Cmd_AddCommand ("+left",IN_LeftDown);
    _cmd.Cmd_AddCommand ("-left",IN_LeftUp);
    _cmd.Cmd_AddCommand ("+right",IN_RightDown);
    _cmd.Cmd_AddCommand ("-right",IN_RightUp);
    _cmd.Cmd_AddCommand ("+forward",IN_ForwardDown);
    _cmd.Cmd_AddCommand ("-forward",IN_ForwardUp);
    _cmd.Cmd_AddCommand ("+back",IN_BackDown);
    _cmd.Cmd_AddCommand ("-back",IN_BackUp);
    _cmd.Cmd_AddCommand ("+lookup", IN_LookupDown);
    _cmd.Cmd_AddCommand ("-lookup", IN_LookupUp);
    _cmd.Cmd_AddCommand ("+lookdown", IN_LookdownDown);
    _cmd.Cmd_AddCommand ("-lookdown", IN_LookdownUp);
    _cmd.Cmd_AddCommand ("+strafe", IN_StrafeDown);
    _cmd.Cmd_AddCommand ("-strafe", IN_StrafeUp);
    _cmd.Cmd_AddCommand ("+moveleft", IN_MoveleftDown);
    _cmd.Cmd_AddCommand ("-moveleft", IN_MoveleftUp);
    _cmd.Cmd_AddCommand ("+moveright", IN_MoverightDown);
    _cmd.Cmd_AddCommand ("-moveright", IN_MoverightUp);
    _cmd.Cmd_AddCommand ("+speed", IN_SpeedDown);
    _cmd.Cmd_AddCommand ("-speed", IN_SpeedUp);
    _cmd.Cmd_AddCommand ("+attack", IN_AttackDown);
    _cmd.Cmd_AddCommand ("-attack", IN_AttackUp);
    _cmd.Cmd_AddCommand ("+use", IN_UseDown);
    _cmd.Cmd_AddCommand ("-use", IN_UseUp);
    _cmd.Cmd_AddCommand ("+jump", IN_JumpDown);
    _cmd.Cmd_AddCommand ("-jump", IN_JumpUp);
    _cmd.Cmd_AddCommand ("impulse", IN_Impulse);
    _cmd.Cmd_AddCommand ("+klook", IN_KLookDown);
    _cmd.Cmd_AddCommand ("-klook", IN_KLookUp);
    _cmd.Cmd_AddCommand ("+mlook", IN_MLookDown);
    _cmd.Cmd_AddCommand ("-mlook", IN_MLookUp);

