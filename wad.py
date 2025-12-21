# wad.py

import struct
import common
import zone

# WAD2 Lump structure is 32 bytes
WAD_LUMP_FORMAT = "<IIIbbh16s"

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
    wad_buffer = common.COM_LoadHunkFile(filename)
    if not wad_buffer:
        common.sys_sdl_unix.Sys_Error(f"W_LoadWadFile: {filename} not found")

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
        
        # Clean the name
        name = name_bytes.split(b'\0', 1)[0].decode('ascii').upper()
        
        lumpinfo.append(lumpinfo_t(name, filepos, size, l_type))

    print(f"W_LoadWadFile: {filename} loaded with {len(lumpinfo)} lumps")

def W_GetLumpName(name):
    """Returns the data for a lump by searching for its name."""
    name = name.upper()
    for i, lump in enumerate(lumpinfo):
        if lump.name == name:
            return W_GetLumpNum(i)
    
    common.sys_sdl_unix.Sys_Error(f"W_GetLumpName: {name} not found")

def W_GetLumpNum(num):
    """Returns a memoryview slice of the lump data from the Hunk."""
    if num < 0 or num >= len(lumpinfo):
        common.sys_sdl_unix.Sys_Error("W_GetLumpNum: bad number")
        
    lump = lumpinfo[num]
    
    # We return a slice of our global WAD buffer. 
    # Because it's a memoryview, this is 'zero-copy'—it's just a window
    # into the existing Hunk memory.
    start = lump.filepos
    end = start + lump.size
    
    return wad_buffer[start:end]
    
def W_CleanupName(name: str) -> str:
    # Quake lump names are max 16 chars, often null-padded
    # This ensures "palette" becomes "PALETTE" and matches correctly
    return name.split('\0')[0].strip().upper()[:16]