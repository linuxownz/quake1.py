#sv_main.py

import _cmd
import common
import console
import cvar
import host
import pr_cmds
import pr_edict
import protocol
import quakedef
import server
import sv_phys
import sv_user
import sys_sdl_unix

sv : server.server_t        = server.server_t()
svs: server.server_static_t = server.server_static_t()

localmodels = []

sv_protocol = protocol.PROTOCOL_FITZQUAKE

def SV_Protocol_f():
    match ( Cmd_Argc()):
        case 1:
            console.Con_Printf(f'sv_protocol is {sv_protocol}')


def SV_Init():
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
    cvar.Cvar_RegisterVariable(sv_stopspeed)

    cvar.Cvar_SetCallback(sv_stopspeed, host.Host_Callback_Notify)

    cvar.Cvar_RegisterVariable(sv_accelerate)
    cvar.Cvar_RegisterVariable(sv_idealpitchscale)

    cvar.Cvar_RegisterVariable(sv_aim)
    cvar.Cvar_RegisterVariable(sv_nostep)
    cvar.Cvar_RegisterVariable(sv_freezenonclients)
    cvar.Cvar_RegisterVariable(sv_altnoclip)
    cvar.Cvar_RegisterVariable(sv_maxspeed)

    cvar.Cvar_RegisterVariable(sv_aim)

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


# sv_main.py

sv_active = False

def SV_SpawnServer(mapname):
    global sv_active
    import gl_model
    import cl_main

    print(f"SV_SpawnServer (Stub): Loading {mapname}...")

    # Just load the model and flip the bit
    full_path = f"maps/{mapname}.bsp"
    mod = gl_model.Mod_ForName(full_path)

    if mod:
        cl_main.cl.worldmodel = mod
        sv_active = True
        return True

    return False