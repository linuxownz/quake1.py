#net_udp.py

import select
import socket

import common
import console
import net_dgrm
import net_main
import sys_sdl_unix

INVALID_SOCKET = -1
net_acceptsocket    : socket.socket = None
net_controlsocket   : socket.socket = None
net_broadcastsocket : socket.socket = None

myAddr = None

def UDP_Init():
    global myAddr
    global net_controlsocket

    local = ''
    ok = False

    if common.COM_CheckParm('-noudp'):
        return INVALID_SOCKET

    myAddr = socket.htonl(socket.INADDR_LOOPBACK)
    try:
        buff = socket.gethostname()
        ok = True
    except OSError as e:
        console.Con_Printf('UDP_Init: WARNING: gethostname failed ', e.strerror)

    try:
        local = socket.gethostbyname(buff)
        ok &= True
    except socket.gaierror as e:
        console.Con_Printf('UDP_Init: Warning: gethostbyname failed ', e.strerror)

    if not ok:
        i = common.COM_CheckParm('-ip')

        if i:
            if i < common.com_argc - 1:
                try:
                    myAddr = socket.inet_aton(common.com_argv[i + 1])
                except socket.gaierror as e:
                    sys_sdl_unix.Sys_Error(f'{common.com_argv[i+1]} is not a valid address {e.strerror}')
                net_main.my_tcpip_address = common.com_argv[i+1]
            else:
                sys_sdl_unix.Sys_Error('NET_Init: you must specify an IP address after -ip')
        else:
            myAddr = local

    net_controlsocket = UDP_OpenSocket(0)

    if net_controlsocket == INVALID_SOCKET:
        console.Con_Printf('UDP_Init: Unable to open control socket, UDP disabled\n')
        return INVALID_SOCKET

    addr = UDP_GetSocketAddr(net_controlsocket)
    net_main.my_tcpip_address = UDP_AddrToString(addr)
    net_main.my_tcpip_address = net_main.my_tcpip_address.split(':')[0]

    console.Con_Printf('UDP Initialized')
    net_main.tcpipAvailable = True

    return net_controlsocket

def UDP_Shutdown():
    UDP_Listen(False)
    UDP_CloseSocket(net_controlsocket)

def UDP_Listen(state: bool):
    global net_acceptsocket
    if state:
        if net_acceptsocket != INVALID_SOCKET:
            return
        net_acceptsocket = UDP_OpenSocket(net_main.net_hostport)
        if net_acceptsocket == INVALID_SOCKET:
            sys_sdl_unix.Sys_Error('UDP_Listen: Unable to open accept socket')
        return

    if net_acceptsocket == INVALID_SOCKET:
        return
    UDP_CloseSocket(net_acceptsocket)
    net_acceptsocket = INVALID_SOCKET


def UDP_OpenSocket(port) -> socket.socket:
    newsocket = None
    try:
        newsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    except OSError as e:
        console.Con_Printf('UDP_OpenSocket: %s\n' % ( e.strerror ))
        return INVALID_SOCKET

    newsocket.setblocking(False)

    try:
        newsocket.bind(('', port))
        return newsocket
    except OSError as e:
        console.Con_Printf('UDP_OpenSocket bind failed %s\n' % e.strerror )
        UDP_CloseSocket(newsocket)
        return INVALID_SOCKET

def UDP_CloseSocket(sock: socket.socket):
    global net_broadcastsocket
    if sock is net_broadcastsocket:
        net_broadcastsocket = 0
    return sock.close()

def PartialIPAddress():
    raise NotImplementedError

def UDP_Connect(sock, addr):
    return 0

def UDP_CheckNewConnections():
    if net_acceptsocket == INVALID_SOCKET:
        return INVALID_SOCKET

    if UDP_CanRead(net_acceptsocket):
        return net_acceptsocket

    data, addr = net_acceptsocket.recvfrom(1, 0)

def UDP_CanRead(sock):
    ready_to_read, _, _ = select.select([sock], [], [], 0)

    if ready_to_read:
        return True
    return False

def UDP_Read(sock: socket.socket, len) -> tuple[bytes, str]:
    try:
        data, addr = sock.recvfrom(len, 0)
        return (data, addr)
    except OSError as e:
        console.Con_Printf('UDP_Read, recvfrom failed %s\n' % e.strerror)

    return (None, None)


def UDP_MakeSocketBroadcastCapable(sock : socket.socket):
    global net_broadcastsocket
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except OSError as e:
        console.Con_Printf('UDP, setsockopt %s\n' % e.strerror)
        return -1

    net_broadcastsocket = sock

    return 0

def UDP_Broadcast(sock: socket.socket, buf, len):

    if sock is not net_broadcastsocket:
        if net_broadcastsocket is not None:
            sys_sdl_unix.Sys_Error('attempted to use multiple broadcast sockets')

        ret = UDP_MakeSocketBroadcastCapable(sock)
        if ret == -1:
            console.Con_Printf('Unable to make socket broadcast capable\n')
            return ret

    return UDP_Write(sock, buf, len)

def UDP_Write(sock : socket.socket, buf: net_dgrm.packetBuffer, len, addr):
    ret = 0
    try:
        ret = sock.sendto(buf.data, addr)
    except OSError as e:
        if e.errno == socket.EWOULDBLOCK:
            return 0
        console.Con_Printf('UDP_Write, sendto; %s\n' % e.strerror)

    return ret

def UDP_AddrToString(addr : tuple[str, str]) -> str: # (host, port)
    return f'{addr[0]}:{addr[1]}'

def UDP_StringToAddr(string:str)-> tuple[str, str]:
    host, port = string.split(":")
    return ((host, port))

def UDP_GetSocketAddr(sock: socket.socket) -> tuple[str,str]:
    return sock.getsockname()

def UDP_GetNameFromAddr(addr: tuple[str, str]) -> str:
    return socket.gethostbyaddr(addr[0])

def UDP_GetAddrFromName(name) -> str:
    return socket.gethostbyname(name)

def UDP_AddrCompare(addr1, addr2) -> bool:
    return addr1 == addr2

def UDP_GetSocketPort(addr) -> str:
    return addr[1]

def UDP_SetSocketPort(addr, port):
    return ((addr[0], port))