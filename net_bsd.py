#net_bsd.py 

import net_loop
import net_dgrm

class net_driver_t():
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