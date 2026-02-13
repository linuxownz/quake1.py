#net_defs.py

from dataclasses import dataclass
import struct
import socket

import quakedef
import net_defs

#NET_HEADERSIZE      (2 * sizeof(unsigned int))
SIZEOFUNSIGNEDINT = struct.calcsize('I')
assert(SIZEOFUNSIGNEDINT == 4)
NET_HEADERSIZE    = (2 * SIZEOFUNSIGNEDINT)
NET_DATAGRAMSIZE  = (quakedef.MAX_DATAGRAM + NET_HEADERSIZE)

NETFLAG_LENGTH_MASK = 0x0000ffff
NETFLAG_DATA        = 0x00010000
NETFLAG_ACK         = 0x00020000
NETFLAG_NAK         = 0x00040000
NETFLAG_EOM         = 0x00080000
NETFLAG_UNRELIABLE  = 0x00100000
NETFLAG_CTL         = 0x80000000

NET_PROTOCOL_VERSION = 3

CCREQ_CONNECT       = 0x01
CCREQ_SERVER_INFO   = 0x02
CCREQ_PLAYER_INFO   = 0x03
CCREQ_RULE_INFO     = 0x04

CCREP_ACCEPT        = 0x81
CCREP_REJECT        = 0x82
CCREP_SERVER_INFO   = 0x83
CCREP_PLAYER_INFO   = 0x84
CCREP_RULE_INFO     = 0x85

MAX_NET_DRIVERS = 8

NET_NAMELEN = 64
NET_MAXMESSAGE = 64000

class qsocket_t():
    def __init__(self):
        self.next : qsocket_t = None
        self.connecttime = 0
        self.lastMessageTime = 0
        self.lastSendTime = 0

        self.disconnected = False
        self.canSend = False
        self.sendNext = False

        self.driver = 0
        self.landriver = 0

        self.socket     : socket.socket = None
        self.driverdata : net_defs.qsocket_t = None

        self.ackSequence = 0
        self.sendSequence = 0
        self.unreliableSendSequence = 0

        self.sendMessageLength = 0
        self.sendMessage : bytearray(net_defs.NET_MAXMESSAGE)

        self.receiveSequence = 0
        self.unreliableReceiveSequence = 0
        self.receiveMessageLength = 0
        self.receiveMessage : bytearray(net_defs.NET_MAXMESSAGE)

        self.addr : tuple[str, str] = ('', '') # host, port
        self.address = ''

# class NetLanDriver:
#     def __init__(self):
#         raise NotImplementedError
#         # Data Fields
#         self.name = ""           # const char *name
#         self.initialized = False  # qboolean initialized
#         self.control_sock = -1    # sys_socket_t controlSock
#
#     # Interface Methods (The function pointers from the C struct)
#     def init(self):
#         raise NotImplementedError
#
#     def shutdown(self):
#         raise NotImplementedError
#
#     def listen(self, state):
#         raise NotImplementedError
#
#     def open_socket(self, port):
#         raise NotImplementedError
#
#     def close_socket(self, socketid):
#         raise NotImplementedError
#
#     def connect(self, socketid, qsockaddr_addr):
#         raise NotImplementedError
#
#     def check_new_connections(self):
#         raise NotImplementedError
#
#     def read(self, socketid, buf, length, qsockaddr_addr):
#         """Reads data into a buffer, returns bytes read"""
#         raise NotImplementedError
#
#     def write(self, socketid, buf, length, qsockaddr_addr):
#         """Writes data from a buffer, returns bytes written"""
#         raise NotImplementedError
#
#     def broadcast(self, socketid, buf, length):
#         raise NotImplementedError
#
#     # Address Utilities
#     def addr_to_string(self, qsockaddr_addr):
#         raise NotImplementedError
#
#     def string_to_addr(self, string, qsockaddr_addr):
#         raise NotImplementedError
#
#     def get_socket_addr(self, socketid, qsockaddr_addr):
#         raise NotImplementedError
#
#     def get_name_from_addr(self, qsockaddr_addr):
#         raise NotImplementedError
#
#     def get_addr_from_name(self, name, qsockaddr_addr):
#         raise NotImplementedError
#
#     def addr_compare(self, addr1, addr2):
#         raise NotImplementedError
#
#     def get_socket_port(self, qsockaddr_addr):
#         raise NotImplementedError
#
#     def set_socket_port(self, qsockaddr_addr, port):
#         raise NotImplementedError
#
#
# class NetDriver:
#     def __init__(self):
#         raise NotImplementedError
#         self.name = ""           # const char *name
#         self.initialized = False  # qboolean initialized
#
#     def init(self) -> int:
#         """Equivalent to int (*Init) (void)"""
#         raise NotImplementedError
#
#     def listen(self, state: bool):
#         """Equivalent to void (*Listen) (qboolean state)"""
#         raise NotImplementedError
#
#     def search_for_hosts(self, xmit: bool):
#         """Equivalent to void (*SearchForHosts) (qboolean xmit)"""
#         raise NotImplementedError
#
#     def connect(self, host: str):
#         """
#         Returns a qsocket_t object or None.
#         Equivalent to qsocket_t *(*Connect) (const char *host)
#         """
#         raise NotImplementedError
#
#     def check_new_connections(self):
#         """Returns a qsocket_t or None if no new connection exists."""
#         raise NotImplementedError
#
#     def get_message(self, sock) -> int:
#         """
#         Reads from the socket into net_message buffer.
#         Returns message type (1=data, 2=unreliable, etc)
#         """
#         raise NotImplementedError
#
#     def send_message(self, sock, data) -> int:
#         """Equivalent to int (*QSendMessage) (qsocket_t *sock, sizebuf_t *data)"""
#         raise NotImplementedError
#
#     def send_unreliable_message(self, sock, data) -> int:
#         raise NotImplementedError
#
#     def can_send_message(self, sock) -> bool:
#         raise NotImplementedError
#
#     def can_send_unreliable_message(self, sock) -> bool:
#         raise NotImplementedError
#
#     def close(self, sock):
#         raise NotImplementedError
#
#     def shutdown(self):
#         raise NotImplementedError

@dataclass
class hostcache_t:
    name: str = ""          # Server name (hostname)
    map: str = ""           # Current map name
    cname: str = ""         # Connect name (IP string)
    users: int = 0          # Current player count
    maxusers: int = 0       # Max player capacity
    driver: int = 0         # Index of the net_driver
    ldriver: int = 0        # Index of the net_landriver
    addr: tuple = None      # qsockaddr (IP, Port)

# Replace the externs with a simple list
hostcache : list[hostcache_t] = []
HOSTCACHESIZE = 8 # Original Quake limit

class PollProcedure:
    def __init__(self, procedure, arg=None, next_time=0.0):
        self.next = None          # Link to the next PollProcedure object
        self.nextTime = next_time # When this should run (realtime)
        self.procedure = procedure # The Python function to call
        self.arg = arg            # Arguments for that function

