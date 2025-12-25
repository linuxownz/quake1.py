#cl_demo.py

import struct

import console
import common
import cl_main
import host
import _cmd
import net_main
import keys
import net_main


def CL_StopPlayback():
    if not cl_main.cls.demoplayback:
        return

    cl_main.cls.demoplayback.close()
    cl_main.cls.demoplayback = False
    cl_main.cls.demopaused = False
    cl_main.cls.demofile = None
    cl_main.cls.state = cl_main.cactive_t.ca_disconnected

    if cl_main.cls.timedemo:
        CL_FinishTimeDemo()

def CL_Stop_f():
    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    if not cl_main.cls.demorecording:
        console.Con_Printf('not recording a demo')
        return

    SZ_Clear(net_main.net_message)
    MSG_WriteByte( net_main.net_message, svc_disconnect)
    CL_WriteDemoMessage()

    cl_main.cls.demofile.close()
    cl_main.cls.demofile = None
    cl_main.cls.demorecording = False
    Con_Printf('Completed demo\n')

    DemoList_Rebuild()


def CL_GetDemoMessage():

    if cl_main.cls.demopaused:
        return 0

    if cl_main.cls.signon == client.SIGNONS:
        if cl_main.cls.timedemo:
            if host.host_framecount == cl_main.cls.td_lastframe:
                return 0
            cl_main.cls.td_lastframe = host.host_framecount

            if host.host_framecount == cl_main.cls.td_startframe + 1:
                cl_main.cls.td_startframe = host.realtime
        elif cl_main.cl.time <= cl_main.cl.mtime[0]:
            return 0

    # 1. Read the size of the next message block (4 bytes)
    # Using the file handle cl_main.cls.demofile opened in CL_PlayDemo_f
    data = cl_main.cls.demofile.read(4)
    if not data or len(data) < 4:
        cl_main.CL_NextDemo()
        return 0

    msg_len = struct.unpack('<I', data)[0]

    # A 0 length message or a massive one indicates a corrupt demo or EOF
    if msg_len <= 0 or msg_len > 8192:
        cl_main.CL_NextDemo()
        return 0

    # 2. Read the actual message data
    message = cl_main.cls.demofile.read(msg_len)
    if len(message) < msg_len:
        cl_main.CL_NextDemo()
        return 0

    # 3. Populate the global net_message buffer for CL_ParseServerMessage
    # This buffer should be accessible to your parser
    net_main.net_message.data = message
    net_main.net_message.cursize = msg_len
    net_main.net_message.readcount = 0

    # 4. Read the view angles for this block
    # Every block in a Quake demo is followed by 12 bytes of angle data (3 floats)
    # used to interpolate the player's view
    angle_data = cl_main.cls.demofile.read(12)
    if len(angle_data) == 12:
        cl_main.cl.mtime[0] = cl_main.cl.time # Update timing
        # Some ports store these in cl.mviewangles[0] for interpolation
        cl_main.cl.viewangles = list(struct.unpack('<3f', angle_data))

        console.Con_DPrintf(f"Demo Read: {msg_len} bytes, Angles: {angles}\n")

    return 1



def CL_GetMessage():
    if cl_main.cls.demoplayback:
        return CL_GetDemoMessage()

    raise NotImplementedError

def CL_PlayDemo_f():

    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf('playdemo <demoname> : plays a demo\n')
        return

    cl_main.CL_Disconnect()

    name = common.COM_AddExtension(_cmd.Cmd_Argv(1), '.dem')
    console.Con_Printf('Playing demo from %s\n' % name)

    (handle, length, path_id, is_pak) = common.COM_FOpenFile(name)

    cl_main.cls.demofile = handle

    if not cl_main.cls.demofile:
        console.Con_Printf('ERROR: could not open %s\n' % name)
        cl_main.cls.demonum = -1
        return

    cl_main.cls.demoplayback = True
    cl_main.cls.demopaused = False
    cl_main.cls.state = cl_main.cactive_t.ca_connected

    keys.key_dest = keys.keydest_t.key_game

    # Demos start with 3 floats for the initial view angles
    # We need to read them so the camera starts in the right spot
    try:
        import struct
        # Read 12 bytes (3 floats * 4 bytes)
        angle_data = cl_main.cls.demofile.read(12)
        if len(angle_data) == 12:
            cl_main.cl.viewangles = list(struct.unpack('<3f', angle_data))

        # Now trigger the first block of network data
        CL_GetMessage()

    except Exception as e:
        console.Con_Printf(f"ERROR: Failed to read demo header: {e}\n")
        cl_main.CL_Disconnect()



