#net_defs.py 

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

        self.socket = 0
        self.driverdata = None
        
        self.ackSequence = 0
        self.sendSequence = 0
        self.unreliableSendSequence = 0

        self.sendMessageLength = 0
        self.sendMessage : bytes = b''

        self.receiveSequence = 0
        self.unreliableReceiveSequence = 0
        self.receiveMessageLength = 0
        self.receiveMessage : bytes = b''

        self.addr = None
        self.address = ''




