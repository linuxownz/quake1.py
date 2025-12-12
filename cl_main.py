#cl_main.py 

from enum import Enum
import keys
import snd_dma

from console import Con_DPrintf

from typing import (
    IO,  # Use if you do not know the encoding of the file object
    TextIO, # Use if you know you are working with a text encoded file
    BinaryIO # Use if you know you are working with a non-text encoded file
)

class cactive_t(Enum):
    ca_dedicated    = 0
    ca_disconnected = 1
    ca_connected    = 2

class client_static_t():
    def __init__(self):
        self.state : cactive_t = cactive_t.ca_disconnected
        self.spawnparms = ''
        self.demonum = 0
        self.demos : List[str] = []
        self.demorecording = False
        self.demoplayback = False
        self.demopaused = False
        self.timedemo = False
        self.forcetrace = 0
        self.demofile : BinaryIO = None
        self.td_lastframe = 0
        self.td_startframe = 0
        self.td_starttime = 0.0

        self.signon = 0
        self.netcon : qsocket_s = None
        self.message : bytes = None
    
    def SZ_ClearMessage():
        self.message = None

cls = client_static_t()

def CL_Disconnect():
    if keys.key_dest == key_message:
        Key_EndChat()

    S_StopAllSounds(True)
    #BGM_Stop()     # red book audio?
    #CDAudio_Stop() # not going to implement

    if cls.demoplayback:
        CL_StopPlayback()
    elif cls.state == cactive_t.ca_connected:
        if cls.demorecording:
            CL_Stop_f()
        
        Con_DPrintf('sending clc_disconnect\n')
        SZ_Clear(cls.message)
    
        Net_Close(cls.netcon)

        cls.state = cactive_t.ca_disconnected
        if sv.active:
            Host_ShutdownServer(False)

    cls.demoplayback = False
    cls.timedemo = False
    cl.intermission = 0

    CL_ClearSignons()