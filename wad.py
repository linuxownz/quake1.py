#wad.py 

import struct

import common
import console

class NotTestedError(NotImplementedError):
    def __init__(self):
        pass

class qpic_t():
    unpack_string = '<IIBBBB'
    def __init__(self, width, height, data: bytes):
        #raise NotTestedError()
        self.width = width
        self.height = height
        self.data = data

class wadinfo_t():
    unpack_string = '<4sII'
    def __init__(self, id, numlumps, infotableofs):
        self.identification = id
        self.numlumps = numlumps
        self.infotableofs = infotableofs

class lumpinfo_t():
    unpack_string = '<IIIccxx16s'
    def __init__(self, filepos, disksize, size, _type, compression, name):
        self.filepos = filepos
        self.disksize = disksize
        self.size = size
        self.type = _type
        self.compression = compression
        self.name = name

class wad_t():
    def __init__(self, name, id, fh:common._fshandle_t, numlumps, lumps:lumpinfo_t|None, next: wad_t|None):
        self.name = name
        self.id = id
        self.fh = fh
        self.numlumps = numlumps
        self.lumps = lumps
        self.next = next


wad_numlumps = 0
wad_lumps : list[lumpinfo_t] = []
wad_base : bytes = None

WADFILENAME = 'gfx.wad'

def W_CleanupName(name):
    return name.lower()

def W_LoadWadFile():
    global wad_base

    filename = WADFILENAME

    if wad_base:
        wad_base = None
    
    wad_base = common.COM_LoadMallocFile(filename)

    if not wad_base:
        error = f'''W_LoadWadFile: could not load {filename}
        Basedir = {com_basedir}
        Check that this has an {GAMENAME} subdirectory containing pak0.pak and pak1.pak
        or use the -basedir command-line option to specify another directory'''
        Sys_Error(error)

    header = wad_base[:12]

    magic, wad_numlumps, infotableofs = struct.unpack('<4sii', header)

    if magic != b'WAD2':
        Sys_Error(f'wad file {filename} doesnt have a WAD2 id')

    wad_lumpbase = wad_base[infotableofs:] # skip header

    lump_size = struct.calcsize(lumpinfo_t.unpack_string)
    assert(lump_size == 32)

    for i in range(wad_numlumps):
        wad_lump = wad_lumpbase[i * lump_size: i * lump_size + lump_size]
        assert(len(wad_lump) == 32 )
        filepos, disksize, size, _type, compression, name = struct.unpack(lumpinfo_t.unpack_string, wad_lump)

        name = str(name.strip(b'\x00').decode('ascii'))

        name = W_CleanupName(name)
        print(name)
        wad_lumps.append(lumpinfo_t(filepos, disksize, size, _type, compression, name))

def W_GetLumpInfo(lumps: list[lumpinfo_t], numlumps, name) -> lumpinfo_t:
    name = W_CleanupName(name)

    for lump in lumps:
        if lump.name == name:
            return lump

    console.Con_Printf(f'W_GetLumpInfo: {name} not found')

    raise FileNotFoundError

    return None

def W_GetLumpName(name):
    lump : lumpinfo_t = W_GetLumpInfo(wad_lumps, wad_numlumps, name)

    if lump is None:
        return None

    return wad_base[lump.filepos:], lump.filepos



        
        
        













