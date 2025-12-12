#sv_main.py 

import cvar
import sv_phys
import sv_user
import pr_edict
import pr_cmds
import host
import _cmd
import console
import protocol
import quakedef
import server

sv : server_t = None
svs: server_static_t = server.server_static_t()

localmodels = []

sv_protocol = protocol.PROTOCOL_FITZQUAKE

def SV_Protocol_f():
    match ( Cmd_Argc()):
        case 1:
            console.Con_Printf(f'sv_protocol is {sv_protocol}')


def SV_Init():
    sv.edicts = None

    cvar.Cvar_RegisterVariable(sv_phys.sv_maxvelocity)
    cvar.Cvar_RegisterVariable(sv_phys.sv_gravity)
    cvar.Cvar_RegisterVariable(sv_phys.sv_friction)
    
    cvar.Cvar_SetCallback(sv_phys.sv_gravity, host.Host_Callback_Notify)
    cvar.Cvar_SetCallback(sv_phys.sv_friction, host.Host_Callback_Notify)

    cvar.Cvar_RegisterVariable(sv_user.sv_edgefriction)
    cvar.Cvar_RegisterVariable(sv_phys.sv_stopspeed)
    cvar.Cvar_RegisterVariable(sv_phys.sv_stopspeed)

    cvar.Cvar_SetCallback(sv_phys.sv_stopspeed, host.Host_Callback_Notify)

    cvar.Cvar_RegisterVariable(sv_user.sv_accelerate)
    cvar.Cvar_RegisterVariable(sv_user.sv_idealpitchscale)

    cvar.Cvar_RegisterVariable(pr_cmds.sv_aim)
    cvar.Cvar_RegisterVariable(sv_phys.sv_nostep)
    cvar.Cvar_RegisterVariable(sv_phys.sv_freezenonclients)
    cvar.Cvar_RegisterVariable(sv_phys.sv_altnoclip)

    _cmd.Cmd_AddCommand('sv_protocol', SV_Protocol_f)

    global localmodels
    for i in range(quakedef.MAX_MODELS):
        localmodels[i] = f'*{i}'

    global sv_protocol
    i = COM_CheckParm('-protocol')

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

    Sys_Printf(f'Server using protocol {sv_protocol} {p}')