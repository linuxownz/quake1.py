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
import host
import quakedef

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

# net_message : common.sizebuf_s = common.sizebuf_s()
net_activeconnections = 0

messagesSent = 0
messagesReceived = 0
unreliableMessagesSent = 0
unreliableMessagesReceived = 0

net_driverlevel = 0
net_time = 0.0

hostCacheCount = 0
hostcache : list[net_defs.hostcache_t] = []
pollProcedureList : net_defs.PollProcedure = None

# initialized in NET_Init
slistSendProcedure = None #net_defs.PollProcedure(None, 0.0, Slist_Send)
slistPollProcedure = None #net_defs.PollProcedure(None, 0.0, Slist_Poll)

def SetNetTime():
    global net_time

    net_time = sys_sdl_unix.Sys_DoubleTime()
    return net_time

def NET_NewQSocket():
    global net_freeSockets
    global net_activeSockets
    if net_freeSockets is None:
        return None

    if net_activeconnections >= sv_main.svs.maxclients:
        return None

    sock = net_freeSockets
    net_freeSockets = sock.next
    sock.next = net_activeSockets
    net_activeSockets = sock

    sock.disconnected = False
    sock.connecttime = net_time
    sock.address = "UNSET ADDRESS"
    sock.driver = net_driverlevel
    sock.socket = 0
    sock.driverdata = None
    sock.canSend = True
    sock.sendNext = False
    sock.lastMessageTime = net_time
    sock.ackSequence = 0
    sock.sendSequence = 0
    sock.unreliableSendSequence = 0
    sock.sendMessageLength = 0
    sock.receiveSequence = 0
    sock.unreliableReceiveSequence = 0
    sock.receiveMessageLength = 0

    return sock

def NET_FreeQSocket(sock: net_defs.qsocket_t):
    global net_activeSockets
    global net_freeSockets

    if sock == net_activeSockets:
        net_activeSockets = net_activeSockets.next
    else:
        s = net_activeSockets
        while s:
            if s.next == sock:
                s.next = sock.next
                break
            s = s.next

        if s is None:
            sys_sdl_unix.Sys_Error("NET_FreeQSocket: not active")

    sock.next = net_freeSockets
    net_freeSockets = sock
    sock.disconnected = True


def NET_QSocketGetTime(s: net_defs.qsocket_t):
    return s.connecttime


def NET_QSocketGetAddressString(s: net_defs.qsocket_t):
    return s.address


def NET_Listen_f():
    global listening
    global net_driverlevel

    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf(f'"listen" is {listening}')
        return

    listening = True if int(_cmd.Cmd_Argv(1)) else False

    for i in range(net_bsd.net_numdrivers):
        net_driverlevel = i
        if not net_bsd.net_drivers[net_driverlevel].initialized:
            continue
        net_bsd.net_drivers[net_driverlevel].Listen(listening)


def PrintSlistHeader():
    global slistLastShown

    console.Con_Printf("Server        Map           Users\n")
    console.Con_Printf("------------- ------------- -----\n")
    slistLastShown = 0

def PrintSlist():
    global slistLastShown

    for n in range(hostCacheCount):
        hc = hostcache[n]
        if hostcache[n].maxusers:
            console.Con_Printf("%-15.15s %-15.15s %2u/%2u\n" % (hc.name, hc.map, hc.users, hc.maxusers))
        else:
            console.Con_Printf("%-15.15s %-15.15s\n" % (hc.name, hc.map))

    slistLastShown = n

def PrintSlistTrailer():
    if hostCacheCount:
        console.Con_Printf("== end list ==\n\n")
    else:
        console.Con_Printf("No quake servers found\n\n")

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
    SchedulePollProcedure(slistPollProcedure, 0.1)

    hostCacheCount = 0

def NET_SlistSort():
    global hostcache
    if hostCacheCount > 1:
        hostcache = sorted(hostcache, key=lambda hc : hc.name)

def NET_SlistPrintServer(idx):
    if idx < 0 or idx >= hostCacheCount:
        return ''
    string = ""
    hc = hostcache[idx]
    if hc.maxusers:
        string = "%-15.15s %-15.15s %2u/%2u\n" % ( hc.name, hc.map, hc.users, hc.maxusers )
    else:
        string = "%-15.15s %-15.15s \n" % ( hc.name, hc.map )

    return string


def NET_SlistPrintServerName(idx):
    if idx < 0 or idx >= hostCacheCount:
        return ""
    return hostcache[idx].cname

def IS_LOOP_DRIVER(p):
    return p == 0

def Slist_Send():
    global net_driverlevel
    for net_driverlevel in range(net_bsd.net_numdrivers):
        if not slistLocal and IS_LOOP_DRIVER(net_driverlevel):
            continue
        if not net_bsd.net_drivers[net_driverlevel].initialized:
            continue

        net_bsd.net_drivers[net_driverlevel].SearchForHosts(True)

    if sys_sdl_unix.Sys_DoubleTime() - slistStartTime < 0.5:
        SchedulePollProcedure(slistSendProcedure, 0.75)


def Slist_Poll():
    global net_driverlevel
    global slistInProgress, slistSilent, slistLocal

    for net_driverlevel in range(net_bsd.net_numdrivers):
        if not slistLocal and IS_LOOP_DRIVER(net_driverlevel):
            continue
        if not net_bsd.net_drivers[net_driverlevel].initialized:
            continue

        net_bsd.net_drivers[net_driverlevel].SearchForHosts(False)

    if not slistSilent:
        PrintSlist()


    if sys_sdl_unix.Sys_DoubleTime() - slistStartTime < 1.5:
        SchedulePollProcedure(slistPollProcedure, 0.1)

    if not slistSilent:
        PrintSlistTrailer()

    slistInProgress = False
    slistSilent = False
    slistLocal = True

def NET_Connect(host: str):
    global slistSilent

    num_drivers = net_bsd.net_numdrivers

    justdoit = False
    SetNetTime()

    if host == "":
        host = None

    if host:
        if host == 'local':
            num_drivers = 1
            justdoit = True
        else:
            if hostCacheCount:
                for n in range(hostCacheCount):
                    if host == hostcache[n].name:
                        host = hostcache[n].name
                        break
                if n < hostCacheCount:
                    justdoit = True

    if not justdoit:
        slistSilent = True if host else False
        NET_Slist_f()

        while slistInProgress:
            NET_Poll()

        if host is None:
            if hostCacheCount != 1:
                return None

            host = hostcache[0].cname
            console.Con_Printf("Connecting to ...\n%s @ %s\n\n" % (hostcache[n].name, host))

        if hostCacheCount:
            for n in range(hostCacheCount):
                if host == hostcache[n].name:
                    host = hostcache[n].cname
                    break
    else: #justdoit
        for net_driverlevel in range(num_drivers):
            if not net_bsd.net_drivers[net_driverlevel].initialized:
                continue
            result = net_bsd.net_drivers[net_driverlevel].Connect(host)
            if result:
                return result

        if host:
            console.Con_Printf('\n')
            PrintSlistHeader()
            PrintSlist()
            PrintSlistTrailer()

    return None

def NET_CheckNewConnections():
    global net_driverlevel

    SetNetTime()

    for net_driverlevel in range(net_bsd.net_numdrivers):
        if not net_bsd.net_drivers[net_driverlevel].initialized:
            continue
        if not IS_LOOP_DRIVER(net_driverlevel) and not listening:
            continue
            result = net_bsd.net_drivers[net_driverlevel].CheckNewConnections()
            if result:
                return result

    return None


def NET_Close(sock: net_defs.qsocket_t):
    if sock is None:
        return
    if sock.disconnected:
        return

    SetNetTime()
    net_bsd.net_drivers[sock.driver].Close(sock)
    NET_FreeQSocket(sock)


def NET_GetMessage(sock: net_defs.qsocket_t):
    global messagesReceived
    global unreliableMessagesReceived

    if sock is None:
        return -1

    if sock.disconnected:
        console.Con_Printf('NET_GetMessage: disconnected socket\n')
        return -1

    SetNetTime()

    net_messagetimeout = cvar.Cvar_GetCvar('net_messagetimeout').value

    ret = net_bsd.net_drivers[sock.driver].QGetMessage(sock)

    if ret == 0 and not IS_LOOP_DRIVER(sock.driver):
        if net_time - sock.lastMessageTime > net_messagetimeout:
            NET_Close(sock)
            return -1

    if ret > 0:
        if not IS_LOOP_DRIVER(sock.driver):
            sock.lastMessageTime = net_time
            if ret == 1:
                messagesReceived+= 1
            elif ret == 2:
                unreliableMessagesReceived += 1

    return ret

def NET_SendMessage(sock: net_defs.qsocket_t, data: common.sizebuf_s):
    global messagesSent
    if not sock:
        return -1

    if sock.disconnected:
        console.Con_Printf("Net_SendMessage: disconnected socket\n")
        return -1

    SetNetTime()
    res = net_bsd.net_drivers[sock.driver].QSendMessage(sock, data)
    if res == 1 and not IS_LOOP_DRIVER(sock.driver):
        messagesSent += 1

    return res

def NET_SendUnreliableMessage(sock: net_defs.qsocket_t, data: common.sizebuf_s):
    global messagesSent
    if not sock:
        return -1

    if sock.disconnected:
        console.Con_Printf("Net_SendUnreliableMessage: disconnected socket\n")
        return -1

    SetNetTime()
    res = net_bsd.net_drivers[sock.driver].SendUnreliableMessage(sock, data)
    if res == 1 and not IS_LOOP_DRIVER(sock.driver):
        messagesSent += 1

    return res


def NET_CanSendMessage(sock:net_defs.qsocket_t):
    if not sock:
        return False

    if sock.disconnected:
        return False

    SetNetTime()
    res = net_bsd.net_drivers[sock.driver].CanSendMessage(sock)
    return res

def NET_SendToAll(data: common.sizebuf_s, blocktime: float):

    msg_init: list[bool] = [False for i in range (quakedef.MAX_SCOREBOARD)]
    msg_sent: list[bool] = [False for i in range (quakedef.MAX_SCOREBOARD)]

    start = 0.0
    count = 0

    for i in range(sv_main.svs.maxclients):
        host.host_client = sv_main.svs.clients[i]

        if host.host_client.netconnection and host.host_client.active:
            if IS_LOOP_DRIVER(host.host_client.netconnection.driver):
                NET_SendMessage(host.host_client.netconnection, data)
                msg_init[i] = True
                msg_sent[i] = True
                continue
            count += 1
            msg_init[i] = False
            msg_sent[i] = False

        else:
            msg_init[i] = True
            msg_sent[i] = True

    start = sys_sdl_unix.Sys_DoubleTime()
    while ( count ):
        count = 0

        for i in range(sv_main.svs.maxclients):
            host.host_client = sv_main.svs.clients[i]

            if not msg_init[i]:
                if NET_CanSendMessage(host.host_client.netconnection):
                    msg_init[i] = True
                    NET_SendMessage(host.host_client.netconnection, data)
                else:
                    NET_GetMessage(host.host_client.netconnection)
                count += 1
                continue
            if not msg_sent[i]:
                if NET_CanSendMessage(host.host_client.netconnection):
                    msg_sent[i] = True
                else:
                    NET_GetMessage(host.host_client.netconnection)
                count += 1
                continue
        if sys_sdl_unix.Sys_DoubleTime() - start > blocktime:
            break

    return count


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
        _cmd.Cbuf_AddText('listen 0\n')

    if n > 1 and not listening:
        _cmd.Cbuf_AddText('listen 1\n')

    sv_main.svs.maxclients = n

    if n == 1:
        cvar.Cvar_Set('deathmatch', '0')
    else:
        cvar.Cvar_Set('deathmatch', '1')

def NET_Port_f():
    global DEFAULTnet_hostport
    global net_hostport

    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf(f'port is {net_hostport}')
        return

    n = int(_cmd.Cmd_Argv(1))
    if n < 1 or n > 65534:
        console.Con_Printf('bad value, must be between 1 and 65534')
        return

    DEFAULTnet_hostport = n
    net_hostport = n

    if listening:
        _cmd.Cbuf_AddText('listen 0\n')
        _cmd.Cbuf_AddText('listen 1\n')


def NET_Init():
    global net_hostport
    global net_numsockets
    global DEFAULTnet_hostport
    global listening
    global net_freeSockets
    global net_drivers
    global net_message
    global slistSendProcedure
    global slistPollProcedure

    slistSendProcedure = net_defs.PollProcedure(None, 0.0, Slist_Send)
    slistPollProcedure = net_defs.PollProcedure(None, 0.0, Slist_Poll)

    import common
    net_message = common.sizebuf_s()

    i = common.COM_CheckParm('-port')
    if i == 0:
        i = common.COM_CheckParm('-udpport')

    if i != 0:
        if i < common.com_argc - 1:
            DEFAULTnet_hostport = int(common.com_argv[i+1])
        else:
            sys_sdl_unix.Sys_Error("NET_Init: you must specify a number after -port like command line option")

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
        sys_sdl_unix.Sys_Error('network unavailable')

    if my_tcpip_address:
        console.Con_DPrintf(f'tcp/ip address {my_tcpip_address}')

def NET_Poll():
    global pollProcedureList
    SetNetTime()

    while pollProcedureList:
        pp = pollProcedureList
        if pp.nextTime > net_time:
            break
        pollProcedureList = pp.next
        if pp.procedure:
            pp.procedure(pp.arg)

def SchedulePollProcedure( proc: net_defs.PollProcedure, timeOffset):
    global pollProcedureList

    proc.nextTime = sys_sdl_unix.Sys_DoubleTime() + timeOffset
    prev = None
    pp = pollProcedureList

    while pp:
        if pp.nextTime >= proc.nextTime:
            break
        prev = pp
        pp = pp.next

    if prev is None:
        proc.next = pollProcedureList
        pollProcedureList = proc
        return

    proc.next = pp
    prev.next =  proc

