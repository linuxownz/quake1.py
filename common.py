# common.py

from __future__ import annotations

import os
import sys
import struct

import console
import cl_main
import _cmd
import cvar
import io
import main_sdl
import net_main

import sys_sdl_unix
import console

from enum import Enum
from enum import Flag, auto

standard_quake = True
safemode = False
rogue = False
hipnotic = False
fitzmode = False

FS_ENT_NONE      = 0
FS_ENT_FILE      = 1
FS_ENT_DIRECTORY = 2

registered = {'name': 'registered', 'value': '1', 'flags': cvar.CVAR_ROM}
cmdline    = {'name': 'cmdline',    'value':  '', 'flags': cvar.CVAR_ROM}

com_modified = False
com_filesize = 0
com_cmdline = '.'

com_token = ''
com_argc = 0
com_argv = []

com_gamedir = '.'
com_basedir = '.'


msg_readcount = 0
msg_badread = False

pop = [
    0x0000,0x0000,0x0000,0x0000,0x0000,0x0000,0x0000,0x0000,
    0x0000,0x0000,0x6600,0x0000,0x0000,0x0000,0x6600,0x0000,
    0x0000,0x0066,0x0000,0x0000,0x0000,0x0000,0x0067,0x0000,
    0x0000,0x6665,0x0000,0x0000,0x0000,0x0000,0x0065,0x6600,
    0x0063,0x6561,0x0000,0x0000,0x0000,0x0000,0x0061,0x6563,
    0x0064,0x6561,0x0000,0x0000,0x0000,0x0000,0x0061,0x6564,
    0x0064,0x6564,0x0000,0x6469,0x6969,0x6400,0x0064,0x6564,
    0x0063,0x6568,0x6200,0x0064,0x6864,0x0000,0x6268,0x6563,
    0x0000,0x6567,0x6963,0x0064,0x6764,0x0063,0x6967,0x6500,
    0x0000,0x6266,0x6769,0x6a68,0x6768,0x6a69,0x6766,0x6200,
    0x0000,0x0062,0x6566,0x6666,0x6666,0x6666,0x6562,0x0000,
    0x0000,0x0000,0x0062,0x6364,0x6664,0x6362,0x0000,0x0000,
    0x0000,0x0000,0x0000,0x0062,0x6662,0x0000,0x0000,0x0000,
    0x0000,0x0000,0x0000,0x0061,0x6661,0x0000,0x0000,0x0000,
    0x0000,0x0000,0x0000,0x0000,0x6500,0x0000,0x0000,0x0000,
    0x0000,0x0000,0x0000,0x0000,0x6400,0x0000,0x0000,0x0000
]

class _fshandle_t:
    def __init__(self, file, pak, start, length, pos):
        self.file : io.FileIO = file
        self.pak  = pak
        self.start = start
        self.length = length
        self.pos = pos

class packfile_t():
    def __init__(self, name, filepos, filelen):
        self.name = name
        self.filepos = filepos
        self.filelen = filelen

class pack_t():
    def __init__(self, filename, handle, numfiles, files: List[packfile_t] | None):
        self.filename = filename
        self.handle = handle #file object
        self.numfiles = numfiles
        self.files = files
    def __str__(self):
        return f'{self.filename} numfiles: {self.numfiles}, files: {"has files" if self.files else "None"} handle: {self.handle}'

class searchpath_t():
    def __init__(self, path_id, filename, pack:pack_t, next: searchpath_t | None):
        self.path_id = path_id
        self.filename = filename
        self.pack = pack
        self.next = next
    def __str__(self):
        return f'{self.filename} {self.path_id} {self.pack}'

class sizebuf_s():
    def __init__(self):
        self.allowoverflow = False
        self.overflowed = False
        self.data : bytes = None
        self.maxsize: int = 0
        self.cursize: int = 0


com_searchpaths      : searchpath_t = None
com_base_searchpaths : searchpath_t = None

def CLAMP(minval, val, maxval):
    if val < minval:
        return minval
    elif val > maxval:
        return maxval
    return val

def ShortSwap(l):
    b1 = l & 255
    b2 = (l>>8) & 255
    return (b1<<8) + b2

def ShortNoSwap(l):
    return l

def LongSwap(l):
    b1 = l&255;
    b2 = (l>>8)&255;
    b3 = (l>>16)&255;
    b4 = (l>>24)&255;

    return (b1<<24) + (b2<<16) + (b3<<8) + b4;

def LongNoSwap(l):
    return l

def FloatSwap(f):
    if sys.byteorder == 'little':
        unpacked_float = struct.pack('<f', f)
    else:
        unpacked_float = struct.pack('>f', f)

    return unpacked_float

def FloatNoSwap(f):
    return f

def COM_InitArgv():
    global safemode
    global standard_quake
    global rogue, hipnotic
    global com_cmdline

    #breakpoint()

    com_cmdline = ' '.join(sys.argv)

    if '-safe' in sys.argv:
        safemode = True

    if '-rogue' in sys.argv:
        rogue = True
        standard_quake = False

    if '-hipnotic' in sys.argv or '-quoth' in sys.argv:
        hipnotic = True
        standard_quake = False

    print(f'COM_InitArgv safemode:{safemode} rogue:{rogue} hipnotic:{hipnotic}')

def COM_Init():
    global com_argc, com_argv
    # check endianess...

    com_argc = len(sys.argv)
    com_argv = sys.argv

    if '-fitz' in sys.argv:
        global fitzmode
        fitzmode = True

    print("System endianess: ", sys.byteorder)

    if sys.byteorder == 'big':
        global BigFloat
        global BigLong
        global BigShort
        global LittleFloat
        global LittleLong
        global LittleShort

        BigShort = ShortNoSwap
        LittleShort = ShortSwap
        BigLong = LongNoSwap
        LittleLong = LongSwap
        BigFloat = FloatNoSwap
        LittleFloat = FloatSwap

def COM_Path_f():
    for path in com_searchpaths:
        Con_Printf (path.filename)

def COM_Game_f():
    if Cmd_Argc() <= 1:
        Con_Printf(f"com_gamedir {com_gamedir}")
        return

    p = Cmd_Argv(1)
    p2 = Cmd_Argv(2)

    if p2 != 'hipnotic' and p2 != 'rogue' and p2 != 'quoth':
        Con_Printf("invalid mission pack argument to -game")
        return

    if not os.path.isdir(com_basedir + p):
        Con_Printf("no such 'game' directory")
        return

    com_modified = True

    CL_Disconnect()
    Host_ShutdownServer(True)

class dpackfile_t():
    def __init__(self, name, filepos, filelen):
        self.name = name
        self.filepos = filepos
        self.filelen = filelen

class dpackheader_t():
    def __init__(self, id, dirofs, dirlen):
        self.id = id
        self.dirofs = dirofs
        self.dirlen = dirlen

def COM_FileBase(path):
    """ take 'somedir/otherdir/filename.ext', write only 'filename' to the output """
    return os.path.basename(path).split('.')[0]

def COM_LoadFile(path):
    # Unpack the 4th variable locally
    handle, filelen, pathid, is_pak = COM_OpenFile(path)

    if handle is None or handle == -1:
        return None

    data = sys_sdl_unix.Sys_FileRead(handle, filelen)

    # Use the LOCAL is_pak variable
    if not is_pak:
        sys_sdl_unix.Sys_FileClose(handle)

    return data

def COM_LoadMallocFile(filename):
    h, size, path_id, is_pak = COM_FindFile(filename)
    if h is None or size <= 0:
        return None

    # Allocate from the DYNAMIC/FREEABLE Zone
    import zone
    buf = zone.Z_Malloc(size)

    # Read the data into our managed memory
    data = sys_sdl_unix.Sys_FileRead(h, size)
    buf[:size] = data

    # If it's a loose file, close it so we don't leak handles
    if not is_pak:
        sys_sdl_unix.Sys_FileClose(h)

    return buf

def COM_LoadHunkFile(filename):
    h, size, path_id, is_pak = COM_FindFile(filename)
    if h is None or size <= 0:
        return None

    # Allocate from PERMANENT Hunk space
    import zone
    buf = zone.Hunk_AllocName(size, filename)

    data = sys_sdl_unix.Sys_FileRead(h, size)
    buf[:size] = data

    if not is_pak:
        sys_sdl_unix.Sys_FileClose(h)

    return buf


def COM_LoadPackFile(packfile) -> pack_t:
    (handle, filelength) = sys_sdl_unix.Sys_FileOpenRead(packfile)

    if filelength == -1:
        return None

    PAK_HEADER_FORMAT = '<4sII'
    PAK_ENTRY_FORMAT  = '<56sII'

    header_data = sys_sdl_unix.Sys_FileRead(handle, struct.calcsize(PAK_HEADER_FORMAT))

    magic, dirofs, dirlen = struct.unpack(PAK_HEADER_FORMAT, header_data)

    if magic != b'PACK':
        Sys_Error(f'{packfile} is not a packfile')

    print (f'{magic} {dirofs} {dirlen}')

    numpackfiles = dirlen // struct.calcsize(PAK_ENTRY_FORMAT)

    print (f'num pack files in pack: {numpackfiles}')

    if dirlen < 0 or dirofs < 0:
        Sys_Error(f'invalid packfile {packfile} {dirlen} {dirofs}')

    if numpackfiles == 0:
        Sys_Printf(f'Warning packfile {packfile} has no files')
        Sys_FileClose(handle)
        return None

    if numpackfiles > 2048:
        Sys_Error(f'packfile {packfile} has too many files {numpackfiles} > 2048')

    if numpackfiles != 339:
        sys_sdl_unix.Sys_Printf("Warning: packfile has been modified, count mismatch.  count != 339")
        com_modified = True

    sys_sdl_unix.Sys_FileSeek(handle, dirofs)

    num_entries = dirlen // struct.calcsize(PAK_ENTRY_FORMAT)

    assert(numpackfiles == num_entries)

    newfiles = []
    for _ in range(num_entries):
        entry_data = sys_sdl_unix.Sys_FileRead(handle,struct.calcsize(PAK_ENTRY_FORMAT))
        name_bytes, file_offset, file_size = struct.unpack(PAK_ENTRY_FORMAT, entry_data)

        try:
            name = name_bytes.strip(b'\x00').decode('ascii')
        except:
            name = name_bytes.split(b'\x00A')[0]
            if name == b'progs.dat':
                name = name.decode('ascii')
            else:
                raise FileNotFoundError

        print(f"File: {name}, Offset: {file_offset}, Size: {file_size}")

        newfiles.append(packfile_t(name, file_offset, file_size))

    pack = pack_t(packfile, handle, len(newfiles), newfiles)
    return pack



def COM_AddGameDirectory(base, dir):
    global com_searchpaths
    global com_gamedir
    global com_modified

    path_id = 1
    search = None
    pak = None
    qspak = None
    been_here = False

    com_gamedir = f'{base}/{dir}'

    if com_searchpaths:
        path_id = com_searchpaths.path_id << 1
    else:
        path_id = 1

    # _add_path:
    while True:
        search = searchpath_t(path_id, com_gamedir, None, com_searchpaths)

        com_searchpaths = search

        for i in range (32):
            name = f'{com_gamedir}/pak{i}.pak'
            pak = COM_LoadPackFile(name)

            if i != 0 or path_id != 1 or fitzmode:
                qspak = None
            else:
                old = com_modified
                if been_here:
                    base = main_sdl.parms.userdir
                qspak = COM_LoadPackFile(f'{base}/quakespasm.pak')
                com_modified = old

            if pak:
                search = searchpath_t(path_id, '', pak, com_searchpaths)
                com_searchpaths = search

            if qspak:
                search = searchpath_t(path_id, f'{base}/quakespasm.pak', qspak, com_searchpaths)
                com_searchpaths = search

            if not pak:
                break
        if not pak:
            break

        if not been_here and main_sdl.parms.userdir != main_sdl.parms.basedir:
            been_here = True
            com_gamedir = f'{main_sdl.parms.userdir}/{dir}'
            sys_sdl_unix.Sys_mkdir(com_gamedir)
            # goto _add_path

        break
    pass

    s = com_searchpaths
    while s:
        print (s)
        s = s.next

    #breakpoint()
    pass

def COM_CheckRegistered():
    # Unpack 4 values
    handle, filelen, path_id, is_pak = COM_OpenFile('gfx/pop.lmp')

    if handle == -1 or handle is None:
        cvar.Cvar_SetROM('registered', '0')
        return

    data = sys_sdl_unix.Sys_FileRead(handle, 256)

    # Use the local flag
    if not is_pak:
        sys_sdl_unix.Sys_FileClose(handle)

    if len(data) != 256:
        sys_sdl_unix.Sys_Error('pop.lmp is corrupt')

    #print(data)

    datapos = 0
    for i in range(128):
        short = pop[i]
        sdata1 = struct.unpack('>H', data[datapos:datapos + 2])[0]
        datapos += 2

        if short != sdata1:
            Sys_Error('Corrupted data file')

    cvar.Cvar_SetROM('cmdline', com_cmdline)
    cvar.Cvar_SetROM('registered', '1')
    console.Con_Printf('Playing registered version\n')

def COM_InitFilesytem():
    global com_basedir
    global com_base_searchpaths, com_searchpaths

    cvar.Cvar_RegisterVariable(registered)
    cvar.Cvar_RegisterVariable(cmdline)

    _cmd.Cmd_AddCommand('path', COM_Path_f)
    _cmd.Cmd_AddCommand('game', COM_Game_f)

    i = COM_CheckParm('-basedir')

    if i != 0 and i < com_argc - 1:
        com_basedir = com_argv[i + 1]
    else:
        com_basedir = main_sdl.parms.basedir

    if len(com_basedir) == 0:
        sys_sdl_unix.Sys_Error("bad argument to -basedir")

    COM_AddGameDirectory(com_basedir, 'id1') # GAMENAME

    com_base_searchpaths = com_searchpaths

    if '-rogue' in sys.argv:
        COM_AddGameDirectory(com_basedir, 'rogue')
    elif '-hipnotic' in sys.argv:
        COM_AddGameDirectory(com_basedir, 'hipnotic')

    if '-game' in sys.argv:
        gamename = ''
        for index, item in enumerate(sys.argv):
            if item == '-game':
                gamename = sys.argv[item+1]

        if gamename:
            if gamename != '-rogue' and gamename != 'rogue' and gamename != '-hipnotic' and gamename != 'hipnotic':
                COM_AddGameDirectory(com_basedir, gamename)

    COM_CheckRegistered()

def COM_CheckParm(parm) -> int:
    for i in range(1, com_argc):
        if not com_argv[i]:
            continue
        if parm == com_argv[i]:
            return i

    return 0


def FS_fread(size, fh:_fshandle_t) -> str:
    if fh is None:
        return 0

    if size == 0:
        return 0

    if fh.pos + size > fh.length:
        size = fh.length - fh.pos

    data = fh.file.read(size)

    fh.pos = fh.file.tell()

    return data

def FS_fseek(fh:_fshandle_t, offset, whence) -> int:
    if fh is None:
        return -1

    match whence:
        case io.SEEK_SET:
            pass
        case io.SEEK_CUR:
            offset += fh.pos
        case io.SEEK_END:
            offset = fh.length + offset
        case _:
            return -1

    if offset < 0:
        return -1

    if offset > fh.length:
        offset = fh.length

    fh.pos = fh.file.seek(fh.start + offset, io.SEEK_SET)

    assert(fh.pos == offset)

    return 0

def FS_fclose(fh: _fshandle_t) -> int:
    if fh is None:
        return -1

    return fh.file.close()

def FS_ftell(fh:_fshandle_t) -> int:
    if fh is None:
        return -1

    pos = fh.file.tell()
    assert(pos == fh.pos)

    return pos

def FS_rewind(fh:_fshandle_t):
    if fh is None:
        return
    fh.file.seek(fh.start, io.SEEK_SET)
    fh.pos = 0

    assert(fh.file.tell() == 0)

def FS_feof(fh:_fshandle_t) -> int:
    if fh is None:
        return -1

    if fh.pos >= fh.length:
        return -1

    return 0

def FS_ferror(fh:_fshandle_t)-> int:
    if fh is None:
        return -1

    return 0

def FS_fgetc(fh:_fshandle_t) -> str:
    if fh is None:
        return -1

    if fh.pos >= fh.length:
        return -1

    fh.pos += 1
    return fh.file.read(1)

def FS_fgets(size, fh:_fshandle_t) -> str:

    if FS_feof(fh):
        return None

    if size > ( fh.length - fh.pos ) + 1:
        size = ( fh.length - fh.pos ) + 1

    data = fh.file.read(size)
    fh.pos = fh.file.tell() - fh.start

    return data

def FS_fgetl(fh:_fshandle_t) -> str:

    if FS_feof(fh):
        return None

    data = fh.file.readline()
    fh.pos = fh.file.tell() - fh.start

    return data


def FS_filelength(fh:_fshandle_t):
    if fh is None:
        return -1

    return fh.length

def Host_Say_f():
    Host_Say(False)

def Host_Say_Team_f():
    Host_Say(True)

def Host_Tell_f():
    quoted = False

    if _cmd.cmd_source == src_command:
        Cmd_ForwardToServer()
        return

    if Cmd_Argc() < 3:
        return

    text = Cmd_Args()

    text.replace('"', '')
    text = host_client.name + ': ' + text
    text = text[:256]

    save = host_client
    for client in svs.clients:
        if not client.active or not client.spawned:
            continue
        if client.name != Cmd_Argv(1):
            continue

        host_client = client
        SV_ClientPrintf(text)
        break

    host_client = save

def Host_Color_f():
    raise NotImplementedError

def Host_Kill_f():
    if _cmd.cmd == src_command:
        Cmd_ForwardToServer()
        return

    if sv_player.v.health <= 0:
        SV_ClientPrintf('cant suicide -- already dead')
        return

    pr_global_struct.time = sv.time
    pr_global_struct.self = EDICT_TO_PROG(sv_player)
    PR_ExecuteProgram(pr_global_struct.ClientKill)

def Host_Pause_f():
    if cls.demoplayback:
        cls.demopaused = not cls.demopaused
        cl.paused = cls.demopaused
        return

    if _cmd.cmd_source == src_command:
        Cmd_ForwardToServer()
        return

    if not pausable.value:
        SV_ClientPrintf('pause not allowed\n')
    else:
        sv.paused ^= 1;

        if sv.paused:
            SV_BroadcastPrintf(f'{PR_GetString(sv_player.v.netname)} paused the game')
        else:
            SV_BroadcastPrintf(f'{PR_GetString(sv_player.v.netname)} unpaused the game')

        MSG_WriteByte(sv.reliable_datagram, svc_setpause)
        MSG_WriteByte(sv.reliable_datagram, sv.paused)

def Host_Spawn_f():
    if _cmd.cmd_source == src_command:
        console.Con_Printf('spawn is not valid from the console\n')
        return
    if host_client.spawned:
        console.Con_Printf('spawn not valid -- already spawned\n')
        return

    if sv.loadgame:
        sv.paused = False
    else:
        ent = host_client.edict

BigShort    = ShortSwap
LittleShort = ShortNoSwap
BigLong     = LongSwap
LittleLong  = LongNoSwap
BigFloat    = FloatSwap
LittleFloat = FloatNoSwap

def COM_FindFile(filename) -> (io.FileIO, int, int, bool): # Added bool

    search = com_searchpaths
    while search:
        if search.pack:
            pak = search.pack
            for i in range(pak.numfiles):
                if filename.lower() == pak.files[i].name.lower():
                    # Localize the logic
                    com_filesize = pak.files[i].filelen
                    path_id = search.path_id
                    handle = pak.handle
                    sys_sdl_unix.Sys_FileSeek(handle, pak.files[i].filepos)
                    return (handle, com_filesize, path_id, True) # Return True for PAK
        else:
            netpath = f'{search.filename}/{filename}'
            if os.path.isfile(netpath):
                path_id = search.path_id
                handle, length = sys_sdl_unix.Sys_FileOpenRead(netpath)
                return (handle, length, path_id, False) # Return False for loose file

        search = search.next
    return (None, 0, 0, False)


def COM_FileIOFromHandle(handle) -> io.FileIO:
    import sys_sdl_unix
    return sys_sdl_unix.sys_handles[handle]

def COM_FileExists(filename, path_id) -> bool:
    h, size, path_id, is_pak = COM_FindFile(filename)
    return size >= 0


def COM_OpenFile(filename):
    # wants handle, path_id
    return COM_FindFile(filename)

def COM_CloseFile(handle):
    global com_searchpaths

    search = com_searchpaths

    while search:
        if search.pack and search.pack.handle == handle:
            return # dont really close a pack file

    Sys_FileClose(handle)

def COM_FOpenFile(filename) -> (int, int, int, bool):
    return COM_FindFile(filename)

def COM_FileGetExtension(file):
    raise NotImplementedError

def COM_AddExtension(name, ext):
    return name + ext

def MSG_BeginReading():
    global msg_readcount
    global msg_badread

    msg_readcount = 0
    msg_badread = False

def MSG_ReadByte():
    global msg_readcount
    global msg_badread

    if msg_readcount+1 > net_main.net_message.cursize:
        msg_badread = True
        return -1

    c = net_main.net_message.data[msg_readcount]
    msg_readcount += 1

    return c

def COM_SkipPath(pathname):
    return os.path.basename(pathname)

def COM_StripExtension(name):
    return os.path.splitext(name)[0]
