#net_dgrm.py

import socket
import struct

import _cmd
import common
import console
import cvar
import gl_screen
import menu
import net_bsd
import net_defs
import net_main
import net_udp
import quakedef
import sv_main

net_landriverlevel = 0

packetsSent = 0
packetsReSent = 0
packetsReceived = 0
receivedDuplicateCount = 0
shortPacketCount = 0
droppedDatagrams = 0

class packetBuffer:
    def __init__(self):
        self.length: int = 0
        self.sequence: int = 0
        self.data: bytearray = bytearray(quakedef.MAX_DATAGRAM)

myDriverLevel: int = 0

pb = packetBuffer()

def StrAddr(addr: tuple) -> str:
    """
    Converts a (host, port) tuple into a 32-character hex string.
    Matches the logic of the C StrAddr function.
    """
    # 1. Convert the IP string to 4 bytes and Port to 2 bytes
    # Quake's C version typically looks at a 16-byte structure.
    try:
        # Get raw bytes of the IP (4 bytes for IPv4)
        ip_bytes = socket.inet_aton(addr[0])
        # Get raw bytes of the port (2 bytes, Big Endian)
        port_bytes = struct.pack('>H', int(addr[1]))

        # 2. Combine and pad to 16 bytes to match 'for (n = 0; n < 16; n++)'
        raw_data = ip_bytes + port_bytes
        raw_data = raw_data.ljust(16, b'\x00')

        # 3. Convert to hex string
        # %02x in C is equivalent to .hex() in Python
        return raw_data.hex()

    except Exception:
        # Fallback for local/loopback or malformed addresses
        return "00" * 16

def Datagram_SendMessage(sock: net_defs.qsocket_t, data: common.sizebuf_s):
    global packetsSent
    global pb

    packetLen = 0
    dataLen = 0
    eom = 0

    sock.sendMessage[:data.cursize] = data.data
    sock.sendMessageLength = data.cursize

    if data.cursize <= quakedef.MAX_DATAGRAM:
        dataLen = data.cursize
        eom = net_defs.NETFLAG_EOM
    else:
        dataLen = quakedef.MAX_DATAGRAM
        eom = 0

    packetLen = net_defs.NET_HEADERSIZE + dataLen

    # 1. Pack the header into pb.data[0:8]
    # We combine packetLen with flags, then pack as Big Endian (>II)
    header_val = packetLen | (net_defs.NETFLAG_DATA | eom)
    struct.pack_into('>II', pb.data, 0, header_val, sock.sendSequence)

    # 2. Copy the actual game message into pb.data starting at index 8
    pb.data[net_defs.NET_HEADERSIZE : packetLen] = sock.sendMessage[0:dataLen]

    sock.sendSequence += 1
    sock.canSend = False

    # 3. Pass the actual data buffer to the driver
    if net_bsd.net_landrivers[sock.landriver].Write(sock.socket, pb.data, packetLen, sock.addr) == -1:
        return -1

    sock.lastSendTime = net_main.net_time
    packetsSent += 1

def SendMessageNext(sock: net_defs.qsocket_t):
    global packetsSent
    global pb

    packetLen = 0
    dataLen = 0
    eom = 0

    # 1. Determine fragment size
    if sock.sendMessageLength <= quakedef.MAX_DATAGRAM:
        dataLen = sock.sendMessageLength
        eom = net_defs.NETFLAG_EOM
    else:
        dataLen = quakedef.MAX_DATAGRAM
        eom = 0

    packetLen = net_defs.NET_HEADERSIZE + dataLen

    # 2. Pack the 8-byte header into pb.data[0:8]
    # This combines flags, length, and sequence into Big Endian format
    header_val = packetLen | (net_defs.NETFLAG_DATA | eom)
    struct.pack_into('>II', pb.data, 0, header_val, sock.sendSequence)

    # 3. Copy game data with the 8-byte offset
    # Starting at index 8 prevents overwriting the header we just packed
    pb.data[net_defs.NET_HEADERSIZE : packetLen] = sock.sendMessage[0:dataLen]

    sock.sendSequence += 1
    sock.sendNext = False

    # 4. Pass the actual buffer (pb.data) to the driver
    # Note: Use sock.socket and sock.addr to match the expected driver signature
    if net_bsd.net_landrivers[sock.landriver].Write(sock.socket, pb.data, packetLen, sock.addr) == -1:
        return -1

    sock.lastSendTime = net_main.net_time
    packetsSent += 1
    return 1

def ReSendMessage(sock: net_defs.qsocket_t):
    global packetsSent
    global pb

    packetLen = 0
    dataLen = 0
    eom = 0

    # 1. Determine fragment size (same as SendMessageNext)
    if sock.sendMessageLength <= quakedef.MAX_DATAGRAM:
        dataLen = sock.sendMessageLength
        eom = net_defs.NETFLAG_EOM
    else:
        dataLen = quakedef.MAX_DATAGRAM
        eom = 0

    packetLen = net_defs.NET_HEADERSIZE + dataLen

    # 2. Pack the 8-byte header into pb.data[0:8]
    # IMPORTANT: We use (sock.sendSequence - 1) because this is a re-transmission
    header_val = packetLen | (net_defs.NETFLAG_DATA | eom)
    struct.pack_into('>II', pb.data, 0, header_val, sock.sendSequence - 1)

    # 3. Copy the payload with the 8-byte offset
    # Starting at index 8 prevents overwriting the header we just packed
    pb.data[net_defs.NET_HEADERSIZE : packetLen] = sock.sendMessage[0:dataLen]

    sock.sendNext = False

    # 4. Write the buffer using the driver's expected signature
    if net_bsd.net_landrivers[sock.landriver].Write(sock.socket, pb.data, packetLen, sock.addr) == -1:
        return -1

    sock.lastSendTime = net_main.net_time
    packetsSent += 1
    return 1


def Datagram_CanSendMessage(sock: net_defs.qsocket_t):
    if sock.sendNext:
        SendMessageNext(sock)
    return sock.canSend


def Datagram_CanSendUnreliableMessage(sock):
    return True

def Datagram_SendUnreliableMessage(sock: net_defs.qsocket_t, data: common.sizebuf_s):
    global packetsSent

    # 1. Total size includes the 8-byte header
    packetLen = net_defs.NET_HEADERSIZE + data.cursize

    # 2. Pack the header directly into pb.data starting at index 0
    # This replaces the need for common.BigLong on the integers themselves
    header_val = packetLen | net_defs.NETFLAG_UNRELIABLE
    struct.pack_into('>II', pb.data, 0, header_val, sock.unreliableSendSequence)

    # 3. Copy game data starting at index 8 (the offset)
    pb.data[net_defs.NET_HEADERSIZE : packetLen] = data.data[0:data.cursize]

    # 4. Use the socket and the buffer to write
    if net_bsd.net_landrivers[sock.landriver].Write(sock.socket, pb.data, packetLen, sock.addr) == -1:
        return -1

    packetsSent += 1
    return 1

def Datagram_GetMessage(sock: net_defs.qsocket_t):
    global shortPacketCount
    global packetsReceived
    global droppedDatagrams

    ret = 0

    if not sock.canSend:
        if net_main.net_time - sock.lastSendTime > 1.0:
            ReSendMessage(sock)

    while True:
        (data, addr) = net_bsd.net_landrivers[net_landriverlevel].Read(sock.socket, net_defs.NET_DATAGRAMSIZE)

        length = len(data)

        if length == 0:
            break

        if length == -1:
            console.Con_Printf('read error\n')
            return -1

        if net_bsd.net_landrivers[net_landriverlevel].AddrCompare(addr, sock.addr) != 0:
            console.Con_Printf('forged packet received\n')
            console.Con_Printf('expected: %s\n' % sock.addr)
            console.Con_Printf('received: %s\n' % addr)
            continue

        if length < net_defs.NET_HEADERSIZE:
            shortPacketCount += 1
            continue

        # 1. Unpack header using Network Byte Order (>I)
        raw_length_flags = struct.unpack_from('>I', data, 0)[0]
        raw_sequence = struct.unpack_from('>I', data, 4)[0]

        # 2. Separate flags from the total size
        flags = raw_length_flags & (~net_defs.NETFLAG_LENGTH_MASK)
        total_size = raw_length_flags & net_defs.NETFLAG_LENGTH_MASK

        # 3. Calculate payload size (Total size minus 8-byte header)
        payload_len = total_size - net_defs.NET_HEADERSIZE

        # 4. Synchronize the pb object with the cleaned payload
        pb.data = data[8:8 + payload_len]
        pb.length = payload_len
        pb.sequence = raw_sequence

        if flags & net_defs.NETFLAG_CTL:
            continue

        #sequence = common.BigLong(pb.sequence)
        packetsReceived += 1

        if flags & net_defs.NETFLAG_UNRELIABLE:
            if pb.sequence < sock.unreliableReceiveSequence:
                console.Con_DPrintf('got a stale datagram\n')
                ret = 0
                break

            if pb.sequence != sock.unreliableReceiveSequence:
                count = pb.sequence - sock.unreliableReceiveSequence
                droppedDatagrams += count
                console.Con_DPrintf('Dropped %u datagrams\n' % count)

            sock.unreliableReceiveSequence = pb.sequence + 1

            #length -= net_defs.NET_HEADERSIZE

            common.SZ_Clear(net_main.net_message)
            common.SZ_Write(net_main.net_message, pb.data, pb.length)

            ret = 2
            break

        if flags & net_defs.NETFLAG_ACK:
            if pb.sequence != (sock.sendSequence - 1):
                console.Con_DPrintf('stale ACK received\n')
                continue
            if pb.sequence == sock.ackSequence:
                sock.ackSequence += 1
                if sock.ackSequence != sock.sendSequence:
                    console.Con_DPrintf('ack sequencing error\n')
            else:
                console.Con_DPrintf('duplicate ACK received\n')
                continue

            sock.sendMessageLength -= quakedef.MAX_DATAGRAM

            if sock.sendMessageLength > 0:
                sock.sendMessage[0:sock.sendMessageLength] = sock.sendMessage[quakedef.MAX_DATAGRAM : quakedef.MAX_DATAGRAM + sock.sendMessageLength]
                sock.sendNext = True
            else:
                sock.sendMessageLength = 0
                sock.canSend = True
            continue

        if flags & net_defs.NETFLAG_DATA:
            # 1. Properly pack the ACK header into the bytearray
            # Assigning to pb.length/pb.sequence doesn't change pb.data automatically
            ack_header = net_defs.NET_HEADERSIZE | net_defs.NETFLAG_ACK
            struct.pack_into('>II', pb.data, 0, ack_header, pb.sequence)

            # 2. Write the 8-byte buffer (pb.data) back to the server
            net_bsd.net_landrivers[net_landriverlevel].Write(sock.socket, pb.data, net_defs.NET_HEADERSIZE, addr)

            if pb.sequence != sock.receiveSequence:
                global receivedDuplicateCount
                receivedDuplicateCount += 1
                continue

            sock.receiveSequence += 1

            # 3. Handle End of Message (EOM) or Fragment reassembly
            if flags & net_defs.NETFLAG_EOM:
                common.SZ_Clear(net_main.net_message)
                common.SZ_Write(net_main.net_message, sock.receiveMessage, sock.receiveMessageLength)
                # Use pb.length (the clean payload size)
                common.SZ_Write(net_main.net_message, pb.data, pb.length)
                sock.receiveMessageLength = 0
                ret = 1
                break

            # 4. Copy fragment using pb.length to avoid including the header
            sock.receiveMessage[sock.receiveMessageLength : sock.receiveMessageLength + pb.length] = pb.data[0:pb.length]
            sock.receiveMessageLength += pb.length

            continue

    if sock.sendNext:
        SendMessageNext(sock)

    return ret

def PrintStats(s: net_defs.qsocket_t):
    console.Con_Printf('canSend = %4u    \n' % s.canSend)
    console.Con_Printf('sendSeq = %4u    \n' % s.sendSequence)
    console.Con_Printf('recvSeq = %4u    \n' % s.receiveSequence)
    console.Con_Printf('\n')

def NET_Stats_f():
    if _cmd.Cmd_Argc() == 1:
        console.Con_Printf('unreliable message sent = %i\n' % net_main.unreliableMessagesSent)
        console.Con_Printf('unreliable message recv = %i\n' % net_main.unreliableMessagesReceived)
        console.Con_Printf('reliable messages sent = %i\n' % net_main.messagesSent)
        console.Con_Printf('reliable messages recv = %i\n' % net_main.messagesReceived)
        console.Con_Printf('packetsSent = %i\n' % packetsSent)
        console.Con_Printf('packetsResent = %i\n' % packetsReSent)
        console.Con_Printf('packetsReceived = %i\n' % packetsReceived)
        console.Con_Printf('receivedDuplicateCount = %i\n' % receivedDuplicateCount)
        console.Con_Printf('shortPacketCound = %i\n' % shortPacketCount)
        console.Con_Printf('droppedDatagrams = %i\n' % droppedDatagrams)
    elif _cmd.Cmd_Argv(1) == "*":
        s = net_main.net_activeSockets
        while s:
            PrintStats(s)
            s = s.next

        s = net_main.net_freeSockets
        while s:
            PrintStats(s)
            s = s.next
    else:
        s = net_main.net_activeSockets
        while s:
            if _cmd.Cmd_Argv(1) == s.address:
                break
                s = s.next
        if s is None:
            s = net_main.net_freeSockets
            while s:
                if _cmd.Cmd_Argv(1) == s.address:
                    break
                s = s.next

        if s is None:
            return
        PrintStats(s)


def Datagram_Init():
    global myDriverLevel
    myDriverLevel = net_main.net_driverlevel

    _cmd.Cmd_AddCommand('net_stats', NET_Stats_f)

    if common.safemode or common.COM_CheckParm('-nolan'):
        return -1

    num_inited = 0

    for i in range(net_bsd.net_numlandrvers):
        csock = net_bsd.net_landrivers[i].Init()
        if csock == net_udp.INVALID_SOCKET:
            continue
        net_bsd.net_landrivers[i].initialized = True
        net_bsd.net_landrivers[i].controlSock = csock
        num_inited += 1

    if num_inited == 0:
        return -1

    return 0


def Datagram_Shutdown():
    for i in range(net_bsd.net_numlandrvers):
        if net_bsd.net_landrivers[i].initialized:
            net_bsd.net_landrivers[i].Shutdown()
            net_bsd.net_landrivers[i].initialized = False

def Datagram_Close(sock: net_defs.qsocket_t):
    net_bsd.net_landrivers[sock.landriver].CloseSocket(sock)

def Datagram_Listen(state: bool):
    for i in range(net_bsd.net_numlandrvers):
        if net_bsd.net_landrivers[i].initialized:
            net_bsd.net_landrivers[i].Listen(state)

def _Datagram_CheckNewConnections():
    acceptsock = net_bsd.net_landrivers[net_landriverlevel].CheckNewConnections()
    if acceptsock == net_udp.INVALID_SOCKET:
        return None

    common.SZ_Clear(net_main.net_message)

    (data, clientaddr) = net_bsd.net_landrivers[net_landriverlevel].Read(acceptsock, net_main.net_message.maxsize)

    length = len(data)
    # if length is less than sizeof(int)
    if length < struct.calcsize('i'):
        return None

    net_main.net_message.data[0:length] = data[0:length]
    net_main.net_message.cursize = length

    common.MSG_BeginReading()
    control = struct.unpack_from('>I', net_main.net_message.data, 0)[0]
    common.msg_readcount = 4
    common.MSG_ReadLong()

    if control == -1:
        return None
    if ( control & ( ~net_defs.NETFLAG_LENGTH_MASK)) != net_defs.NETFLAG_CTL:
        return None
    if ( control & net_defs.NETFLAG_LENGTH_MASK) != length:
        return None

    command = common.MSG_ReadByte()
    if command == net_defs.CCREQ_SERVER_INFO:
        if common.MSG_ReadString() != 'QUAKE':
            return None

        common.SZ_Clear(net_main.net_message)

        common.MSG_WriteLong(net_main.net_message, 0)
        common.MSG_WriteByte(net_main.net_message, net_defs.CCREP_SERVER_INFO)

        (host, port) = net_bsd.net_landrivers[net_landriverlevel].GetSocketAddr(acceptsock)
        newaddr = net_bsd.net_landrivers[net_landriverlevel].AddrToString((host, port))
        common.MSG_WriteString(net_main.net_message, newaddr)
        hostname = cvar.Cvar_GetCvar('hostname').string
        common.MSG_WriteString(net_main.net_message, hostname)
        common.MSG_WriteString(net_main.net_message, sv_main.sv.name)
        common.MSG_WriteByte(net_main.net_message, net_main.net_activeconnections)
        common.MSG_WriteByte(net_main.net_message, sv_main.svs.maxclients)
        common.MSG_WriteByte(net_main.net_message, net_defs.NET_PROTOCOL_VERSION)
        # Create the header value: combine the Control flag with the masked size
        header_value = net_defs.NETFLAG_CTL | (net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
        # Convert to Big Endian (Network Byte Order) and write to the first 4 bytes
        net_main.net_message.data[0:4] = struct.pack('>I', header_value)
        net_bsd.net_landrivers[net_landriverlevel].Write(acceptsock, net_main.net_message.data, net_main.net_message.cursize, clientaddr)
        common.SZ_Clear(net_main.net_message)
        return None

    if command == net_defs.CCREQ_PLAYER_INFO:
        playerNumber = common.MSG_ReadByte()
        activeNumber = -1
        clientNumber = 0

        for client in sv_main.svs.clients:
            if client.active:
                activeNumber += 1
                if activeNumber == playerNumber:
                    break

        if clientNumber == sv_main.svs.maxclients:
            return None

        common.SZ_Clear(net_main.net_message)
        common.MSG_WriteLong(net_main.net_message, 0)
        common.MSG_WriteByte(net_main.net_message, net_defs.CCREP_PLAYER_INFO)
        common.MSG_WriteByte(net_main.net_message, playerNumber)
        common.MSG_WriteString(net_main.net_message, client.name)
        common.MSG_WriteLong(net_main.net_message, client.colors)
        common.MSG_WriteLong(net_main.net_message, client.edict.v.frags)
        common.MSG_WriteLong(net_main.net_message, net_main.net_time - client.netconnection.connecttime)
        common.MSG_WriteString(net_main.net_message, client.netconnection.address)
        header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
        net_main.net_message[0:4] = struct.pack('>I', header)
        net_bsd.net_landrivers[net_landriverlevel].Write(acceptsock, net_main.net_message.data, net_main.net_message.cursize, clientaddr)
        common.SZ_Clear(net_main.net_message)

        return None

    if command == net_defs.CCREQ_RULE_INFO:
        prevCvarName = common.MSG_ReadString()
        var = cvar.Cvar_FindVarAfter(prevCvarName, cvar.CVAR_SERVERINFO)

        common.SZ_Clear(net_main.net_message)

        common.MSG_WriteLong(net_main.net_message, 0)
        common.MSG_WriteByte(net_main.net_message, net_defs.CCREP_RULE_INFO)
        if var is not None:
            common.MSG_WriteString(net_main.net_message, var.name)
            common.MSG_WriteString(net_main.net_message, var.string)
        header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
        net_main.net_message[0:4] = struct.pack('>I', header)
        net_bsd.net_landrivers[net_landriverlevel].Write(acceptsock, net_main.net_message.data, net_main.net_message.cursize, clientaddr)
        common.SZ_Clear(net_main.net_message)

        return None

    if command != net_defs.CCREQ_CONNECT:
        return None

    if common.MSG_ReadString() != "QUAKE":
        return None

    if common.MSG_ReadByte() != net_defs.NET_PROTOCOL_VERSION:
        common.SZ_Clear( net_main.net_message )

        common.MSG_WriteLong(net_main.net_message, 0)
        common.MSG_WriteByte(net_main.net_message, net_defs.CCREP_REJECT)
        common.MSG_WriteString(net_main.net_message, "Incompatible version\n")

        header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
        net_main.net_message[0:4] = struct.pack('>I', header)
        net_bsd.net_landrivers[net_landriverlevel].Write(acceptsock, net_main.net_message.data, net_main.net_message.cursize, clientaddr)
        common.SZ_Clear(net_main.net_message)

        return None

    s = net_main.net_activeSockets
    while s:
        if s.driver != net_main.net_driverlevel:
            s = s.next
            continue

        ret = net_bsd.net_landrivers[net_landriverlevel].AddrCompare(clientaddr, s.addr)
        if ret >= 0:
            if ret == 0 and net_main.net_time - s.connecttime < 2.0:
                common.SZ_Clear(net_main.net_message)
                common.MSG_WriteLong(net_main.net_message, 0)
                common.MSG_WriteByte(net_main.net_message, net_defs.CCREP_ACCEPT)
                (host, port) = net_bsd.net_landrivers[net_landriverlevel].GetSocketAddr(s.socket)
                common.MSG_WriteLong(net_main.net_message, port)

                header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
                net_main.net_message[0:4] = struct.pack('>I', header)
                net_bsd.net_landrivers[net_landriverlevel].Write(acceptsock, net_main.net_message.data, net_main.net_message.cursize, clientaddr)
                common.SZ_Clear(net_main.net_message)

                return None

            net_main.NET_Close(s)
            return None

    sock = net_main.NET_NewQSocket()
    if sock is None:
        common.SZ_Clear(net_main.net_message)
        common.MSG_WriteLong(net_main.net_message, 0)
        common.MSG_WriteByte(net_main.net_message, net_defs.CCREP_REJECT)
        common.MSG_WriteString(net_main.net_message, "Server is full\n")
        header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
        net_main.net_message[0:4] = struct.pack('>I', header)
        net_bsd.net_landrivers[net_landriverlevel].Write(acceptsock, net_main.net_message.data, net_main.net_message.cursize, clientaddr)
        common.SZ_Clear(net_main.net_message)

        return None

    newsock = net_bsd.net_landrivers[net_landriverlevel].OpenSocket(0)
    if newsock == net_udp.INVALID_SOCKET:
        net_main.NET_FreeQSocket(sock)
        return None

    if net_bsd.net_landrivers[net_landriverlevel].Connect(newsock, clientaddr) == -1:
        net_bsd.net_landrivers[net_landriverlevel].CloseSocket(newsock)
        net_main.NET_FreeQSocket(sock)
        return None

    sock.socket = newsock
    sock.landriver = net_landriverlevel
    sock.addr = clientaddr
    sock.address = net_bsd.net_landrivers[net_landriverlevel].AddrToString(clientaddr)

    common.SZ_Clear(net_main.net_message)
    common.MSG_WriteLong(net_main.net_message, 0)
    common.MSG_WriteByte(net_main.net_message, net_defs.CCREP_ACCEPT)
    newport = net_bsd.net_landrivers[net_landriverlevel].GetSocketPort(newaddr)
    common.MSG_WriteLong(net_main.net_message, newport)
    header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
    net_main.net_message[0:4] = struct.pack('>I', header)
    net_bsd.net_landrivers[net_landriverlevel].Write(acceptsock, net_main.net_message.data, net_main.net_message.cursize, clientaddr)
    common.SZ_Clear(net_main.net_message)

    return sock

def Datagram_CheckNewConnections() -> net_defs.qsocket_t:
    ret : net_defs.qsocket_t = None
    for net_landriverlevel in range(net_bsd.net_numlandrvers):
        if net_bsd.net_landrivers[net_landriverlevel].initialized:
            ret = _Datagram_CheckNewConnections()
            if ret is not None:
                break

    return ret


def _Datagram_SearchForHosts(xmit : bool) -> None:
    # myaddr ( host, port )
    myaddr : tuple[str, str] = net_bsd.net_landrivers[net_landriverlevel].GetSocketAddr(net_bsd.net_landrivers[net_landriverlevel].controlSock)

    if xmit:
        common.SZ_Clear(net_main.net_message)
        common.MSG_WriteLong(net_main.net_message, 0)
        common.MSG_WriteByte(net_main.net_message, net_defs.CCREQ_SERVER_INFO)
        common.MSG_WriteString(net_main.net_message, "QUAKE")
        common.MSG_WriteByte( net_main.net_message, net_defs.NET_PROTOCOL_VERSION)

    header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
    net_main.net_message[0:4] = struct.pack('>I', header)
    net_bsd.net_landrivers[net_landriverlevel].Broadcast(net_bsd.net_landrivers[net_landriverlevel].controlSock, net_main.net_message.data, net_main.net_message.cursize)
    common.SZ_Clear(net_main.net_message)

    data, readaddr = net_bsd.net_landrivers[net_landriverlevel].Read(net_bsd.net_landrivers[net_landriverlevel].controlSock)
    while data:

        if len(data) < struct.calcsize('i'):
            continue

        net_main.net_message.cursize = len(data)

        if net_bsd.net_landrivers[net_landriverlevel].AddrCompare(readaddr, myaddr):
            continue

        if net_main.hostCacheCount == net_defs.HOSTCACHESIZE:
            continue

        common.MSG_BeginReading()
        control = struct.unpack_from('>I', net_main.net_message.data, 0)[0]
        common.msg_readcount = 4
        common.MSG_ReadLong()
        if control == -1:
            continue
        if ( control & (~net_defs.NETFLAG_LENGTH_MASK)) != net_defs.NETFLAG_CTL:
            continue
        if (control & net_defs.NETFLAG_LENGTH_MASK) != len(data):
            continue

        if common.MSG_ReadByte() != net_defs.CCREP_SERVER_INFO:
            continue

        readaddr = net_bsd.net_landrivers[net_landriverlevel].GetAddrFromName(common.MSG_ReadString())

        for n in range(net_main.hostCacheCount):
            if net_bsd.net_landrivers[net_landriverlevel].AddrCompare(readaddr, net_main.hostcache[n].addr):
                break

        if n < net_main.hostCacheCount:
            continue

        net_main.hostCacheCount += 1
        net_main.hostcache[n].name = common.MSG_ReadString()
        net_main.hostcache[n].map  = common.MSG_ReadString()
        net_main.hostcache[n].users = common.MSG_ReadByte()
        net_main.hostcache[n].maxusers = common.MSG_ReadByte()
        if common.MSG_ReadByte() != net_defs.NET_PROTOCOL_VERSION:
            net_main.hostcache[n].cname = net_main.hostcache[n].name[:14]
            net_main.hostcache[n].name = "*" + net_main.hostcache[n].cname
        net_main.hostcache[n].addr = readaddr
        net_main.hostcache[n].driver = net_main.net_driverlevel
        net_main.hostcache[n].ldriver = net_landriverlevel
        net_main.hostcache[n].cname = net_bsd.net_landrivers[net_landriverlevel].AddrToString(readaddr)

        collision = True
        while collision:
            collision = False
            for i in range(net_main.hostCacheCount):
                if i == n:
                    continue

                if net_main.hostcache[n].name.lower() == net_main.hostcache[i].name.lower():
                    name = net_main.hostcache[n].name
                    if not name:
                        net_main.hostcache[n].name = "0"
                    elif name[-1].isdigit() and name[-1] < '9':
                        # Increment last digit: "Server0" -> "Server1"
                        net_main.hostcache[n].name = name[:-1] + chr(ord(name[-1]) + 1)
                    elif len(name) < 15:
                        # Append a digit: "Server" -> "Server0"
                        net_main.hostcache[n].name += "0"
                    else:
                        # Last resort for long names ending in 9
                        net_main.hostcache[n].name = name[:-1] + "!"

                    collision = True # Found a conflict, check the whole list again
                    break

def Datagram_SearchForHosts(xmit: bool):
    for net_landriverlevel in range(net_bsd.net_numlandrvers):
        if net_main.hostCacheCount == net_defs.HOSTCACHESIZE:
            break
        if net_bsd.net_landrivers[net_landriverlevel].initialized:
            _Datagram_SearchForHosts(xmit)


def errorReturn(sock):
    net_main.NET_FreeQSocket(sock)
    errorReturn2()

def errorReturn2(sock):
    net_bsd.net_landrivers[net_landriverlevel].CloseSocket(sock)
    import gl_vidsdl
    import in_sdl
    import keys
    import menu
    import vid

    if menu.m_return_onerror:
        in_sdl.IN_Deactivate(gl_vidsdl.modestate == vid.MS_WINDOWED)
        keys.key_dest = keys.keydest_t.key_menu
        menu.m_state = menu.m_state_e.m_return_state
        menu.m_return_onerror = False

def _Datagram_Connect(host: str):
    sendaddr = net_bsd.net_landrivers[net_landriverlevel].GetAddrFromName(host)
    if sendaddr is None or sendaddr == '':
        console.Con_Printf('could not resolve %s\n' % host)
        return None

    newsock = net_bsd.net_landrivers[net_landriverlevel].OpenSocket(0)
    if newsock == net_udp.INVALID_SOCKET:
        return None

    sock = net_main.NET_NewQSocket()
    if sock is None:
        errorReturn2(sock)
        return None

    sock.driverdata = newsock
    sock.socket = newsock
    sock.landriver = net_landriverlevel

    if net_bsd.net_landrivers[net_landriverlevel].Connect(newsock, sendaddr) == -1: # always succeeds
        errorReturn(sock)
        return None

    console.Con_Printf('trying..\n')
    gl_screen.SCR_UpdateScreen()

    start_time = net_main.net_time

    for reps in range(3):
        common.SZ_Clear(net_main.net_message)
        common.MSG_WriteLong(net_main.net_message, 0)
        common.MSG_WriteByte(net_main.net_message, net_defs.CCREQ_CONNECT)
        common.MSG_WriteString(net_main.net_message, "QUAKE")
        common.MSG_WriteByte(net_main.net_message, net_defs.NET_PROTOCOL_VERSION)

        header = common.BigLong(net_defs.NETFLAG_CTL | net_main.net_message.cursize & net_defs.NETFLAG_LENGTH_MASK)
        net_main.net_message[0:4] = struct.pack('>I', header)

        net_bsd.net_landrivers[net_landriverlevel].Write(newsock, net_main.net_message.data, net_main.net_message.cursize, sendaddr)
        common.SZ_Clear(net_main.net_message)

        firstpass = True
        ret = 0
        while firstpass or ( ret == 0 and ( net_main.SetNetTime() - start_time) < 2.5):
            data, readaddr = net_bsd.net_landrivers[net_landriverlevel].Read(newsock, net_main.net_message.data, net_main.net_message.maxsize)

            length = len(data)
            if length > 0:
                if not net_bsd.net_landrivers[sock.landriver].AddrCompare(readaddr, sendaddr):
                    console.Con_Printf('wrong reply address\n')
                    console.Con_Printf('expected %s | %s\n' % ( net_bsd.net_landrivers[sock.landriver].AddrToString(sendaddr), StrAddr(sendaddr)))
                    console.Con_Printf('received %s | %s\n' % ( net_bsd.net_landrivers[sock.landriver].AddrToString(readaddr), StrAddr(readaddr)))
                    gl_screen.SCR_UpdateScreen()
                    length = 0
                    firstpass = False
                    continue
                if length < 4: # sizeof(int)
                    length = 0
                    firstpass = False
                    continue

                net_main.net_message.cursize = length
                common.MSG_BeginReading()
                control = struct.unpack_from('>I', net_main.net_message.data, 0)[0]
                common.msg_readcount = 4
                #common.MSG_ReadLong()
                if control == -1:
                    length = 0
                    firstpass = False
                    continue

                if (control & (~net_defs.NETFLAG_LENGTH_MASK)) != net_defs.NETFLAG_CTL:
                    length = 0
                    firstpass = False
                    continue

                if control & net_defs.NETFLAG_LENGTH_MASK != length:
                    length = 0
                    firstpass = False
                    continue

            firstpass = False

        if length > 0:
            break

        console.Con_Printf('still trying ...\n')
        gl_screen.SCR_UpdateScreen()
        start_time = net_main.SetNetTime()

    if length == 0:
        reason = 'No response'
        console.Con_Printf('%s\n' % reason)
        menu.m_return_reason = reason
        errorReturn(sock)
        return None

    if length == -1: # this will never fire, logic error in my code
        reason = 'Network error'
        console.Con_Printf(reason)
        menu.m_return_reason = reason
        errorReturn(sock)
        return None

    ret = common.MSG_ReadByte()
    if ret == net_defs.CCREP_REJECT:
        reason = common.MSG_ReadString()
        console.Con_Printf(reason)
        menu.m_return_reason = reason
        errorReturn(sock)
        return None

    if ret == net_defs.CCREP_ACCEPT:
        sock.addr = sendaddr
        net_bsd.net_landrivers[net_landriverlevel].SetSocketPort(sock.addr, common.BigLong(common.MSG_ReadLong()))
    else:
        reason = 'Bad response'
        console.Con_Printf('%s\n', reason)
        menu.m_return_reason = reason
        errorReturn(sock)
        return None

    sock.address = net_bsd.net_landrivers[net_landriverlevel].GetNameFromAddr(sendaddr)

    console.Con_Printf('Connection accepted\n')

    sock.lastMessageTime = net_main.SetNetTime()

    if net_bsd.net_landrivers[net_landriverlevel].Connect(newsock, sock.addr) == -1:
        reason = 'Connect to Game failed'
        console.Con_Printf('%s\n' % reason)
        menu.m_return_reason = reason
        errorReturn(sock)
        return None

    menu.m_return_onerror = False
    return sock

def Datagram_Connect(host: str) -> net_defs.qsocket_t:
    ret : net_defs.qsocket_t = None
    host, net_main.net_hostport = host.split(':')

    for net_landriverlevel in range(net_bsd.net_numlandrvers):
        if net_bsd.net_landrivers[net_landriverlevel].initialized:
            ret = _Datagram_Connect(host)
            if ret is not None:
                break

    return ret





