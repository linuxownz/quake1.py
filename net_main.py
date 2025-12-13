#net_main.py 

import cl_main
import _cmd
import common
import console
import cvar
import net_bsd
import net_defs
import sv_main
import sys_sdl_unix

net_activeSockets : net_defs.qsocket_t = None
net_freeSockets   : net_defs.qsocket_t = None

net_numsockets = 0
tcpipAvailable = False

my_tcpip_address = ''

net_hostport        = 26000
DEFAULTnet_hostport = 26000

my_tcpip_address = ''

listening = False

slistInProgress = False
slistSilent     = False
slistLocal      = True

slistStartTime = 0.0
slistLastShown = 0

net_message = b'' # sizebuf_t TODO
net_activeconnections = 0

messagesSent = 0
messagesReceived = 0
unreliableMessagesSent = 0
unreliableMessagesReceived = 0

net_time = 0.0

hostCacheCount = 0
hostcache : List[hostcache_t] = []

def SetNetTime():
    global net_time

    net_time = sys_sdl_unix.Sys_DoubleTime();
    return net_time

def NET_Slist_f():
    global slistInProgress
    global slistStartTime
    global hostCacheCount

    if slistInProgress:
        return
    
    if not slistSilent:
        console.Con_Printf('Looking for Quake servers...\n')
        PrintSlistHeader()

    SchedulePollProcedure(slistSendProcedure, 0.0)
    SchedulePollProcedure(slistSendProcedure, 0.1)

    hostCacheCount = 0
    
def NET_Listen_f():
    global listening

    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf(f'listen is {listening}')
        return

    listening = int(_cmd.Cmd_Argv(1))

    for net_driverlevel in range(net_numdrivers):
        if net_drivers[net_driverlevel].initialized == False:
            continue
        net_drivers[net_driverlevel].Listen(listening) # this is different from dfunc define 

    
def MaxPlayers_f():
    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf(f'maxplayers is {sv_main.svs.maxclients}\n')
        return

    if sv_main.sv.active:
        console.Con_Printf('maxplayers cannot be changed while server is running \n')

    n = int(_cmd.Cmd_Argv(1))
    if n < 1:
        n = 1
    
    if n > sv_main.svs.maxclientslimit:
        n = sv_main.svs.maxclientslimit
        console.Con_Printf(f'maxplayers set to {n}')

    if n == 1 and listening:
        Cbuf_AddText('listen 0\n')

    if n > 1 and not listening:
        Cbuf_AddText('listen 1\n')

    sv_main.svs.maxclients = n

    if n == 1:
        Cvar_Set('deathmatch', '0')
    else:
        Cvar_Set('deathmatch', '1')

def NET_Port_f():
    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf(f'port is {net_hostport}')
        return

    n = int(Cmd_Argv(1))
    if n < 1 or n > 65534:
        console.Con_Printf('bad value, must be between 1 and 65534')
        return

    DEFAULTnet_hostport = n
    net_hostport = n

    if listening:
        Cbuf_AddText('listen 0\n')
        Cbuf_AddText('listen 1\n')
        

def NET_Init():
    global net_hostport
    global net_numsockets
    global DEFAULTnet_hostport
    global listening
    global net_freeSockets
    global net_drivers

    i = common.COM_CheckParm('-port')
    if i == 0:
        i = common.COM_CheckParm('-udpport')

    if i != 0:
        if i < common.com_argc - 1:
            DEFAULTnet_hostport = int(common.com_argv[i+1])
        else:
            Sys_Error("NET_Init: you must specify a number after -port like command line option")

    net_hostport = DEFAULTnet_hostport

    net_numsockets = sv_main.svs.maxclientslimit

    if cl_main.cls.state != cl_main.cactive_t.ca_dedicated:
        net_numsockets += 1
    
    if common.COM_CheckParm('-listen') or cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        listening = True

    SetNetTime()

    for i in range(net_numsockets):
        s = net_defs.qsocket_t()
        s.next = net_freeSockets
        net_freeSockets = s
        s.disconnected = True

    net_messagetimeout = {'name': 'net_messagetimeout', 'value':'300',     'flags':cvar.CVAR_NONE}
    hostname           = {'name': 'hostname',           'value':'UNNAMED', 'flags':cvar.CVAR_NONE}

    cvar.Cvar_RegisterVariable(net_messagetimeout)
    cvar.Cvar_RegisterVariable(hostname)

    _cmd.Cmd_AddCommand('slist',      NET_Slist_f)
    _cmd.Cmd_AddCommand('listen',     NET_Listen_f)
    _cmd.Cmd_AddCommand('maxplayers', MaxPlayers_f)
    _cmd.Cmd_AddCommand('port',       NET_Port_f)

    i = 0
    for net_driverlevel in range(net_bsd.net_numdrivers):
        if net_bsd.net_drivers[net_driverlevel].Init() == -1:
            continue
        i += 1

        net_bsd.net_drivers[net_driverlevel].Initialized = True
        if listening:
            net_bsd.net_drivers[net_driverlevel].Listen(True)

    if i == 0 and cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        Sys_Error('network unavailable')

    if my_tcpip_address:
        console.Con_DPrintf(f'tcp/ip address {my_tcpip_address}')


    