#cl_demo.py

import struct

import _cmd
import cl_main
import common
import console
import host
import host_cmd
import keys
import mathlib
import net_defs
import net_main
import protocol
import quakedef
import sys_sdl_unix

demo_head: bytearray = bytearray()
demo_head_sizes: list[int] = 0

def CL_ClearSignons():
    cl_main.cls.signon = 0

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

def CL_WriteDemoMessage():
    len: int = common.LittleLong(net_main.net_message.cursize)
    cl_main.cls.demofile.write(struct.pack('<i', len))

    for i in range(3):
        f = common.LittleFloat(cl_main.cl.viewangles[i])
        cl_main.cls.demofile.write(struct.pack('<f', f))

    cl_main.cls.demofile.write(net_main.net_message.data[:net_main.net_message.cursize])
    cl_main.cls.demofile.flush()

def CL_GetDemoMessage() -> int:
    if cl_main.cls.demopaused:
        return 0

    if cl_main.cls.signon == client.SIGNONS:  # noqa: SIM102
        if cl_main.cls.timedemo:              # noqa: SIM102
            if host.host_framecount == cl_main.cls.td_lastframe:
                return 0
            cl_main.cls.td_lastframe = host.host_framecount

            if host.host_framecount == cl_main.cls.td_startframe + 1:
                cl_main.cls.td_starttime = host.realtime
        elif cl_main.cl.time <= cl_main.cl.mtime[0]:
            return 0

    data = cl_main.cls.demofile.read(4)
    net_main.net_message.cursize = 0
    if len(data) == 4:
        net_main.net_message.cursize = struct.unpack('<i', data)[0]

    if not net_main.net_message.cursize:
        sys_sdl_unix.Sys_Error('Demo read error')

    mathlib.VectorCopy(cl_main.cl.mviewangles[0], cl_main.cl.mviewangles[1])

    r = 0
    for i in range(3):
        data = cl_main.cls.demofile.read(4)
        r = len(data)

        cl_main.cl.mviewangles[0][i] = common.LittleFloat(data)

    net_main.net_message.cursize = common.LittleLong(net_main.net_message.cursize)

    if net_main.net_message.cursize > quakedef.MAX_MSGLEN:
        sys_sdl_unix.Sys_Error('Demo message > MAX_MSGLEN')

    net_main.net_message.data = cl_main.cls.demofile.read(net_main.net_message.cursize)
    if len(net_main.net_message.data) != net_main.net_message.cursize:
        CL_StopPlayback()
        return 0

    return 1

def CL_GetMessage() -> int:

    if cl_main.cls.demoplayback:
        return CL_GetDemoMessage()

    while True:
        r = net_main.NET_GetMessage(cl_main.cls.netcon)

        if r != 1 and r != 2:
            return r
        if net_main.net_message.cursize == 1 and net_main.net_message.data[0] == protocol.svc_nop:
            print('<-- server to client keepalive')
        else:
            break

    if cl_main.cls.demorecording:
        CL_WriteDemoMessage()

    if cl_main.cls.signon < 2:
        #common.Vec_Append(demo_head, net_main.net_message.data)
        demo_head.append(net_main.net_message.data)

        #common.VEC_PUSH(demo_head_sizes, net_main.net_message.cursize)
        demo_head_sizes.append(net_main.net_message.cursize)

    return r


def CL_Stop_f():
    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    if not cl_main.cls.demorecording:
        console.Con_Printf('not recording a demo')
        return

    common.SZ_Clear(net_main.net_message)
    common.MSG_WriteByte( net_main.net_message, protocol.svc_disconnect)
    CL_WriteDemoMessage()

    cl_main.cls.demofile.close()
    cl_main.cls.demofile = None
    cl_main.cls.demorecording = False
    console.Con_Printf('Completed demo\n')

    host_cmd.DemoList_Rebuild()


def CL_Record_f():
    track = -1

    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    if cl_main.cls.demoplayback:
        console.Con_Printf('Cant record during demo playback')
        return

    if cl_main.cls.demorecording:
        CL_Stop_f()

    c = _cmd.Cmd_Argc()
    if c != 2 and c != 3 and c != 4:
        console.Con_Printf('record <demoname> [map]')
        return

    if _cmd.Cmd_Argv(1).find('..'):
        console.Con_Printf('Relative pathnames are not allowed')
        return

    if c == 2 and cl_main.cls.state == quakedef.cactive_t.ca_connected:  # noqa: SIM102
        if cl_main.cls.signon < 2:
            console.Con_Printf('Cant record - try again when connected')
            return

    name = common.com_gamedir + '/' + _cmd.Cmd_Argv(1)

    if c > 2:
        _cmd.Cmd_ExecuteString('map ' + _cmd.Cmd_Argv(2), _cmd.cmd_source.src_command)
        if cl_main.cls.state != quakedef.cactive_t.ca_connected:
            return

    common.COM_AddExtension(name, '.dem')

    console.Con_Printf('recording to ' + name)
    try:
        cl_main.cls.demofile = open(name, 'wb')
    except OSError as e:
        console.Con_Printf('Error: couldnt create file ' + name + ' ' + e)
        return

    cl_main.cls.forcetrack = track # -1
    cl_main.cls.demofile.write(b"%d" % cl_main.cls.forcetrack)

    cl_main.cls.demorecording = True

    if c == 2 and cl_main.cls.state == quakedef.cactive_t.ca_connected:
        data_backup = net_main.net_message.data
        cursize_backup = net_main.net_message.cursize
        maxsize_backup = net_main.net_message.maxsize

        # 2. Iterate through buffered demo head blocks
        # If demo_head is a single bytearray/bytes and demo_head_sizes tracks block lengths:
        offset = 0
        for block_size in demo_head_sizes:
            net_main.net_message.data = demo_head[offset : offset + block_size]
            net_main.net_message.cursize = block_size
            CL_WriteDemoMessage()
            offset += block_size

        # Alternatively, if demo_head is stored as a list of chunks (list[bytes]):
        # for chunk in _demo_head_chunks:
        #     net_message.data = chunk
        #     net_message.cursize = len(chunk)
        #     CL_WriteDemoMessage()

        # 3. Setup temporary message buffer for state snapshot
        net_main.net_message.data = bytearray()
        net_main.net_message.maxsize = net_defs.NET_MAXMESSAGE
        common.SZ_Clear(net_main.net_message)

        # 4. Current player names, colors, and frags
        for i in range(cl.maxclients):
            common.MSG_WriteByte(net_main.net_message, protocol.svc_updatename)
            common.MSG_WriteByte(net_main.net_message, i)
            common.MSG_WriteString(net_main.net_message, cl_main.cl.scores[i].name)

            common.MSG_WriteByte(net_main.net_message, protocol.svc_updatefrags)
            common.MSG_WriteByte(net_main.net_message, i)
            common.MSG_WriteShort(net_main.net_message, cl_main.cl.scores[i].frags)

            common.MSG_WriteByte(net_main.net_message, protocol.svc_updatecolors)
            common.MSG_WriteByte(net_main.net_message, i)
            common.MSG_WriteByte(net_main.net_message, cl_main.cl.scores[i].colors)

        # 5. Current light styles
        for i in range(quakedef.MAX_LIGHTSTYLES):
            common.MSG_WriteByte(net_main.net_message, protocol.svc_lightstyle)
            common.MSG_WriteByte(net_main.net_message, i)
            common.MSG_WriteString(net_main.net_message, cl_lightstyle[i].map)

        # 6. Level stats
        common.MSG_WriteByte(net_main.net_message, protocol.svc_updatestat)
        common.MSG_WriteByte(net_main.net_message, quakedef.STAT_TOTALSECRETS)
        common.MSG_WriteLong(net_main.net_message, cl_main.cl.stats[quakedef.STAT_TOTALSECRETS])

        common.MSG_WriteByte(net_main.net_message, protocol.svc_updatestat)
        common.MSG_WriteByte(net_main.net_message, quakedef.STAT_TOTALMONSTERS)
        common.MSG_WriteLong(net_main.net_message, cl_main.cl.stats[quakedef.STAT_TOTALMONSTERS])

        common.MSG_WriteByte(net_main.net_message, protocol.svc_updatestat)
        common.MSG_WriteByte(net_main.net_message, quakedef.STAT_SECRETS)
        common.MSG_WriteLong(net_main.net_message, cl_main.cl.stats[quakedef.STAT_SECRETS])

        common.MSG_WriteByte(net_main.net_message, protocol.svc_updatestat)
        common.MSG_WriteByte(net_main.net_message, quakedef.STAT_MONSTERS)
        common.MSG_WriteLong(net_main.net_message, cl_main.cl.stats[quakedef.STAT_MONSTERS])

        # 7. View entity & Signon stage 3
        common.MSG_WriteByte(net_main.net_message, protocol.svc_setview)
        common.MSG_WriteShort(net_main.net_message, cl_main.cl.viewentity)

        common.MSG_WriteByte(net_main.net_message, protocol.svc_signonnum)
        common.MSG_WriteByte(net_main.net_message, 3)

        # Flush state snapshot packet to demo file
        CL_WriteDemoMessage()

        # 8. Restore original net_message state
        net_main.net_message.data = data_backup
        net_main.net_message.cursize = cursize_backup
        net_main.net_message.maxsize = maxsize_backup







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
    console.Con_Printf(f'Playing demo from {name}\n')

    (handle, length, path_id, is_pak) = common.COM_FOpenFile(name)

    cl_main.cls.demofile = handle

    if not cl_main.cls.demofile:
        console.Con_Printf(f'ERROR: could not open {name}\n')
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



def CL_FinishTimeDemo():
    cl_main.cls.timedemo = False
    frames = (host.host_framecount - cl_main.cls.td_startframe) - 1
    time = host.realtime - cl_main.cls.td_starttime

    if not time:
        time = 1

    console.Con_Printf(f"{frames:d} frames {time:5.1f} seconds {frames / time:5.1f} fps\n")


def CL_TimeDemo_f():
    if _cmd.cmd_source != _cmd.cmd_source_t.src_command:
        return

    if _cmd.Cmd_Argc() != 2:
        console.Con_Printf('timedemo <demoname> : gets demo speeds')
        return

    CL_PlayDemo_f()

    if not cl_main.cls.demofile:
        return

    cl_main.cls.timedemo = True
    cl_main.cls.td_startframe = host.host_framecount
    cl_main.cls.td_lastframe = -1