#net_bsd.py

import net_dgrm
import net_loop
import net_udp


class net_driver_t:
    def __init__(self, name, initialized, Init, Listen,
                SearchForHosts, Connect, CheckNewConnections,
                QGetMessage, QSendMessage, SendUnreliableMessage,
                CanSendMessage, CanSendUnreliableMessage,
                Close, Shutdown):

        self.name = name
        self.initialized = initialized
        self.Init = Init
        self.Listen = Listen
        self.SearchForHosts = SearchForHosts
        self.Connect = Connect
        self.CheckNewConnections = CheckNewConnections
        self.QGetMessage = QGetMessage
        self.QSendMessage = QSendMessage
        self.SendUnreliableMessage = SendUnreliableMessage
        self.CanSendMessage = CanSendMessage
        self.CanSendUnreliableMessage = CanSendUnreliableMessage
        self.Close = Close
        self.Shutdown = Shutdown

loopback_driver = net_driver_t('Loopback', False,
    net_loop.Loop_Init,
    net_loop.Loop_Listen,
    net_loop.Loop_SearchForHosts,
    net_loop.Loop_Connect,
    net_loop.Loop_CheckNewConnections,
    net_loop.Loop_GetMessage,
    net_loop.Loop_SendMessage,
    net_loop.Loop_SendUnreliableMessage,
    net_loop.Loop_CanSendMessage,
    net_loop.Loop_CanSendUnreliableMessage,
    net_loop.Loop_Close,
    net_loop.Loop_Shutdown
)

datagrm_driver = net_driver_t('Datagram', False,
    net_dgrm.Datagram_Init,
    net_dgrm.Datagram_Listen,
    net_dgrm.Datagram_SearchForHosts,
    net_dgrm.Datagram_Connect,
    net_dgrm.Datagram_CheckNewConnections,
    net_dgrm.Datagram_GetMessage,
    net_dgrm.Datagram_SendMessage,
    net_dgrm.Datagram_SendUnreliableMessage,
    net_dgrm.Datagram_CanSendMessage,
    net_dgrm.Datagram_CanSendUnreliableMessage,
    net_dgrm.Datagram_Close,
    net_dgrm.Datagram_Shutdown
)

net_drivers = [
    loopback_driver,
    datagrm_driver
]

net_numdrivers = len(net_drivers)

class net_landriver_t:
    def __init__(self, Init, Shutdown, Listen, OpenSocket, CloseSocket, Connect, CheckNewConnections,
    Read, Write, Broadcast, AddrToString, StringToAddr, GetSocketAddr, GetNameFromAddr, GetAddrFromName, AddrCompare,
    GetSocketPort, SetSocketPort):
        self.name = 'UDP'
        self.initialized = False
        self.controlSock = 0
        self.Init = Init
        self.Shutdown = Shutdown
        self.Listen = Listen
        self.OpenSocket = OpenSocket
        self.CloseSocket = CloseSocket
        self.Connect = Connect
        self.CheckNewConnections = CheckNewConnections
        self.Read = Read
        self.Write = Write
        self.Broadcast = Broadcast
        self.AddrToString = AddrToString
        self.StringToAddr = StringToAddr
        self.GetSocketAddr =   GetSocketAddr
        self.GetNameFromAddr = GetNameFromAddr
        self.GetAddrFromName = GetAddrFromName
        self.AddrCompare = AddrCompare
        self.GetSocketPort = GetSocketPort
        self.SetSocketPort = SetSocketPort

lan_driver = net_landriver_t(
    net_udp.UDP_Init,
    net_udp.UDP_Shutdown,
    net_udp.UDP_Listen,
    net_udp.UDP_OpenSocket,
    net_udp.UDP_CloseSocket,
    net_udp.UDP_Connect,
    net_udp.UDP_CheckNewConnections,
    net_udp.UDP_Read,
    net_udp.UDP_Write,
    net_udp.UDP_Broadcast,
    net_udp.UDP_AddrToString,
    net_udp.UDP_StringToAddr,
    net_udp.UDP_GetSocketAddr,
    net_udp.UDP_GetNameFromAddr,
    net_udp.UDP_GetAddrFromName,
    net_udp.UDP_AddrCompare,
    net_udp.UDP_GetSocketPort,
    net_udp.UDP_SetSocketPort
)

net_landrivers = [
    lan_driver
]

net_numlandrvers = len(net_landrivers)


