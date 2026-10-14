# wad.py

import struct

import common

# WAD2 Lump structure is 32 bytes
WADFILENAME = 'gfx.wad'
WAD_LUMP_FORMAT = "<IIIbbh16s"

class qpic_t:
    def __init__(self, width, height, data=None):
        self.width = width
        self.height = height
        self.data = data # This will store the 8-bit indexed pixels


class lumpinfo_t:
    def __init__(self, name, filepos, size, type):
        self.name = name
        self.filepos = filepos
        self.size = size
        self.type = type

# Global state
lumpinfo = []
wad_buffer = None  # This will hold the memoryview of the whole WAD

def W_LoadWadFile(filename):
    global lumpinfo, wad_buffer

    # Load the entire WAD into the Hunk
    result = common.COM_LoadMallocFile(filename, False)

    if not isinstance(result, bytearray):
        raise Exception('bad result not bytearray')

    if not result:
        common.sys_sdl_unix.Sys_Error(f"W_LoadWadFile: {filename} not found")

    # Unpack the raw bytes buffer from the tuple (buffer, size)
    wad_buffer = memoryview(result)

    # Header: magic (4), numlumps (4), infotableofs (4)
    magic, numlumps, infotableofs = struct.unpack_from("<4sII", wad_buffer, 0)

    if magic != b'WAD2':
        common.sys_sdl_unix.Sys_Error(f"W_LoadWadFile: {filename} is not a WAD2 file")

    lumpinfo = []
    for i in range(numlumps):
        entry_offset = infotableofs + (i * 32)

        filepos, disksize, size, l_type, comp, pad, name_bytes = struct.unpack_from(
            WAD_LUMP_FORMAT, wad_buffer, entry_offset
        )

        # Clean the name (strip null bytes and convert to uppercase)
        name = name_bytes.split(b'\0', 1)[0].decode('ascii', errors='ignore').upper()

        lumpinfo.append(lumpinfo_t(name, filepos, size, l_type))

    print(f"W_LoadWadFile: {filename} loaded with {len(lumpinfo)} lumps")

def W_GetLumpName(name):
    """Returns (data, filepos) for a lump by name."""
    name = name.upper()
    for i, lump in enumerate(lumpinfo):
        if lump.name == name:
            return W_GetLumpNum(i)

    # Instead of hard error, return None so gl_draw can use pic_nul
    return None, 0

def W_GetLumpNum(num):
    """Returns (memoryview_slice, filepos)."""
    if num < 0 or num >= len(lumpinfo):
        return None, 0

    lump = lumpinfo[num]
    start = lump.filepos
    end = start + lump.size

    return wad_buffer[start:end], lump.filepos

def W_CleanupName(name: str) -> str:
    # Quake lump names are max 16 chars, often null-padded
    # This ensures "palette" becomes "PALETTE" and matches correctly
    return name.split('\0')[0].strip().upper()[:16]

def SwapPic(pic: qpic_t):
    pic.width  = common.LittleLong(pic.width)
    pic.height = common.LittleLong(pic.height)