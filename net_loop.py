#net_loop.py

import cl_main
import console
import cvar
import net_defs
import net_main
import sv_main
import sys_sdl_unix

def _ensure_buffers(sock):
    """qsocket_t has no receiveMessage buffer of its own; give it one (C: byte receiveMessage[NET_MAXMESSAGE])."""
    size = getattr(net_defs, 'NET_MAXMESSAGE', 65535)
    buf = getattr(sock, 'receiveMessage', None)
    if buf is None or len(buf) < size:
        sock.receiveMessage = bytearray(size)
    return sock.receiveMessage

localconnectpending = False
loop_client : net_defs.qsocket_t = None
loop_server : net_defs.qsocket_t = None

def Loop_Init():
    if cl_main.cls.state == cl_main.cactive_t.ca_dedicated:
        return -1
    return 0

def Loop_Shutdown():
    pass

def Loop_Listen(state=True):
    pass

def Loop_SearchForHosts(xmit=True):
    if not sv_main.sv.active:
        return

    net_main.hostCacheCount = 1
    while len(net_main.hostcache) < 1:
        net_main.hostcache.append(net_defs.hostcache_t())

    hostname = cvar.Cvar_GetCvar('hostname').string

    if hostname == 'UNNAMED':
        net_main.hostcache[0].name = 'local'
    else:
        net_main.hostcache[0].name = hostname

    net_main.hostcache[0].map   = sv_main.sv.name
    net_main.hostcache[0].users = net_main.net_activeconnections
    net_main.hostcache[0].maxusers = sv_main.svs.maxclients
    net_main.hostcache[0].driver = net_main.net_driverlevel
    net_main.hostcache[0].cname = 'local'


def Loop_Connect(host: str):
    global localconnectpending
    global loop_client
    global loop_server

    if host != 'local':
        return None

    localconnectpending = True

    if not loop_client:
        loop_client = net_main.NET_NewQSocket()
        if loop_client is None:
            console.Con_Printf('Loop_Connect: no qsocket available\n')
            return None
        loop_client.address = 'localhost'
    _ensure_buffers(loop_client)

    loop_client.receiveMessageLength = 0
    loop_client.sendMessageLength = 0
    loop_client.canSend = True

    if not loop_server:
        loop_server = net_main.NET_NewQSocket()
        if loop_server is None:
            console.Con_Printf('Loop_Connect: no qsocket available\n')
            return None
        loop_server.address = 'LOCAL'
    _ensure_buffers(loop_server)

    loop_server.receiveMessageLength = 0
    loop_server.sendMessageLength = 0
    loop_server.canSend = True

    loop_client.driverdata = loop_server
    loop_server.driverdata = loop_client

    return loop_client


def Loop_CheckNewConnections():
    global localconnectpending
    if not localconnectpending:
        return None

    localconnectpending = False
    loop_server.sendMessageLength = 0
    loop_server.receiveMessageLength = 0
    loop_server.canSend = True

    loop_client.sendMessageLength = 0
    loop_client.receiveMessageLength = 0
    loop_client.canSend = True

    return loop_server

import common  # Assuming SZ_Clear and SZ_Write are here


def IntAlign(value):
    # Mimics C's (value + 3) & ~3 for 4-byte alignment
    return (value + 3) & ~3

def Loop_GetMessage(sock: net_defs.qsocket_t):
    """
    Reads a message from the internal loopback buffer.
    Returns:
        0: No message
        1: Reliable message
        2: Unreliable message
    """
    _ensure_buffers(sock)
    if sock.receiveMessageLength == 0:
        return 0

    # 1. Extract Header Data
    # ret is the message type (byte 0)
    ret = sock.receiveMessage[0]

    # length is a short (bytes 1 and 2)
    length = sock.receiveMessage[1] + (sock.receiveMessage[2] << 8)

    # 2. Copy data to the global net_message buffer
    # net_main.py initialized net_message as a sizebuf_s
    from net_main import net_message
    common.SZ_Clear(net_message)

    # We copy 'length' bytes starting from index 4 (skipping type, length, and alignment)
    common.SZ_Write(net_message, sock.receiveMessage[4 : 4 + length], length)

    # 3. Calculate how much to "pop" from the buffer
    # Total block size includes 4-byte header + data, then aligned to 4 bytes
    total_read_length = IntAlign(length + 4)

    # 4. Update buffer length and shift remaining data (The "memmove" equivalent)
    sock.receiveMessageLength -= total_read_length

    if sock.receiveMessageLength > 0:
        # Shift the buffer left by slicing
        sock.receiveMessage[0 : sock.receiveMessageLength] = \
            sock.receiveMessage[total_read_length : total_read_length + sock.receiveMessageLength]

    # 5. Handle reliable message flow control
    if sock.driverdata and ret == 1:
        # In loopback, driverdata usually points to the 'other side' of the connection
        sock.driverdata.canSend = True

    return ret


def Loop_SendMessage(sock: net_defs.qsocket_t, data: common.sizebuf_s):
    """
    Packs data into the destination socket's receive buffer.
    data: sizebuf_s object containing the message to send.
    """
    # 1. Get the 'other side' of the connection
    dest = sock.driverdata
    if not dest:
        return -1
    _ensure_buffers(dest)

    # 2. Check for buffer overflow
    # Quake buffers are typically 8192 bytes.
    # Header (4 bytes) + aligned data length
    aligned_len = IntAlign(data.cursize)
    if (dest.receiveMessageLength + aligned_len + 4) > len(dest.receiveMessage):
        console.Con_Printf('Loop_SendMessage: overflow\n')
        return -1

    # 3. Write the Header
    # Byte 0: Message Type (1 for Reliable, 2 for Unreliable in this context)
    # Since this is Loop_SendMessage (Reliable), we use 1.
    dest.receiveMessage[dest.receiveMessageLength] = 1

    # Bytes 1-2: Length of the data (Short, Little Endian)
    dest.receiveMessage[dest.receiveMessageLength + 1] = data.cursize & 0xff
    dest.receiveMessage[dest.receiveMessageLength + 2] = (data.cursize >> 8) & 0xff

    # Byte 3: Padding/Alignment byte (skipped)

    # 4. Write the Data
    start_idx = dest.receiveMessageLength + 4
    dest.receiveMessage[start_idx : start_idx + data.cursize] = data.data[:data.cursize]

    # 5. Update the destination length
    dest.receiveMessageLength += (aligned_len + 4)

    # In Loopback, reliable messages are "received" instantly,
    # so we block the sender until the receiver processes it.
    sock.canSend = False
    return 1


def Loop_SendUnreliableMessage(sock: net_defs.qsocket_t, data: common.sizebuf_s):
    """
    Packs data into the destination socket's receive buffer.
    data: sizebuf_s object containing the message to send.
    """
    # 1. Get the 'other side' of the connection
    dest = sock.driverdata
    if not dest:
        return -1
    _ensure_buffers(dest)

    # 2. Check for buffer overflow
    # Quake buffers are typically 8192 bytes.
    # Header (4 bytes) + aligned data length
    aligned_len = IntAlign(data.cursize)
    if (dest.receiveMessageLength + aligned_len + 4) > len(dest.receiveMessage):
        return 0  # unreliable: just drop it

    # 3. Write the Header
    # Byte 0: Message Type (1 for Reliable, 2 for Unreliable in this context)
    # Since this is Loop_SendMessage (Reliable), we use 1.
    dest.receiveMessage[dest.receiveMessageLength] = 2

    # Bytes 1-2: Length of the data (Short, Little Endian)
    dest.receiveMessage[dest.receiveMessageLength + 1] = data.cursize & 0xff
    dest.receiveMessage[dest.receiveMessageLength + 2] = (data.cursize >> 8) & 0xff

    # Byte 3: Padding/Alignment byte (skipped)

    # 4. Write the Data
    start_idx = dest.receiveMessageLength + 4
    dest.receiveMessage[start_idx : start_idx + data.cursize] = data.data[:data.cursize]

    # 5. Update the destination length
    dest.receiveMessageLength += (aligned_len + 4)

    # In Loopback, reliable messages are "received" instantly,
    # so we block the sender until the receiver processes it.
    return 1


def Loop_CanSendMessage(sock: net_defs.qsocket_t):
    if not sock.driverdata:
        return False
    return sock.canSend  # C: return sock->canSend

def Loop_CanSendUnreliableMessage(sock=None):
    return True

def Loop_Close(sock: net_defs.qsocket_t):
    global loop_client
    global loop_server

    if sock.driverdata:
        sock.driverdata.driverdata = None

    sock.receiveMessageLength = 0
    sock.sendMessageLength = 0
    sock.canSend = True

    if sock is loop_client:
        loop_client = None
    else:
        loop_server = None

