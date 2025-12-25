#cl_main.py

from enum import Enum
import keys
import snd_dma
import cl_main
import cl_demo
import _cmd
import console
import gl_screen
import quakedef
import sv_main
import host

# from console import Con_DPrintf

from typing import (
    IO,  # Use if you do not know the encoding of the file object
    TextIO, # Use if you know you are working with a text encoded file
    BinaryIO # Use if you know you are working with a non-text encoded file
)

class cactive_t(Enum):
    ca_dedicated    = 0
    ca_disconnected = 1
    ca_connected    = 2

cls = quakedef.client_static_t()
cl  = quakedef.client_state_t()

cl_static_entities                        = [None for _ in range(quakedef.MAX_STATIC_ENTITIES)]
cl_lightstyle : list[quakedef.lightstyle_t] = [None for _ in range(quakedef.MAX_LIGHTSTYLES)]
cl_dlights    : list[quakedef.dlight_t]     = [None for _ in range(quakedef.MAX_DLIGHTS)]

cl_entities = None

cl_max_edicts = 0
cl_numvisedicts = 0


def CL_Init():
    import cvar
    import _cmd

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
        cl_main.CL_StopPlayback()
    elif cls.state == cactive_t.ca_connected:
        if cls.demorecording:
            cl_main.CL_Stop_f()

        console.Con_DPrintf('sending clc_disconnect\n')
        SZ_Clear(cls.message)
        MSG_WriteByte(cl_main.cls.clc_disconnect)
        NET_SendUnreliableMessage(cl_main.cls.netcon, cl_main.cls.message)
        SZ_Clear(cl_main.cls.message)
        Net_Close(cls.netcon)

        cl_main.cls.state = cl_main.cactive_t.ca_disconnected
        if sv_main.sv.active:
            host.Host_ShutdownServer(False)

    cls.demoplayback = False
    cls.timedemo = False
    cl.intermission = 0

    #cl_demo.CL_ClearSignons()

def CL_NextDemo():
    if cls.demonum == -1:
        return

    if not cls.demos[cls.demonum] or cls.demonum == quakedef.MAX_DEMOS:
        cls.demonum = 0
        if not cls.demos[cls.demonum]:
            console.Con_Printf('no demos listed with startdemos')
            cls.demonum = -1
            CL_Disconnect()
            return

    gl_screen.SCR_BeginLoadingPlaque()

    demoname = f'playdemo {cls.demos[cls.demonum]}\n'
    _cmd.Cbuf_InsertText(demoname)
    cls.demonum += 1
