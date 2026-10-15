#snd_mem.py  (port of QuakeSpasm snd_mem.c)

import struct
import sys
from array import array

import common
import console
import cvar
import q_sound


class wavinfo_t:
    def __init__(self) -> None:
        self.rate = 0
        self.width = 0
        self.channels = 0
        self.loopstart = -1
        self.samples = 0
        self.dataofs = 0


def _le_short(d, o):
    return struct.unpack_from('<h', d, o)[0]


def _le_long(d, o):
    return struct.unpack_from('<i', d, o)[0]


def GetWavinfo(name: str, wav: bytes, wavlength: int) -> wavinfo_t:
    info = wavinfo_t()

    if not wav or wavlength < 12 or wav[0:4] != b'RIFF' or wav[8:12] != b'WAVE':
        console.Con_Printf(f'Missing RIFF/WAVE chunks ({name})\n')
        return info

    # index the chunks (first occurrence of each id wins, like FindChunk)
    chunks = {}
    ofs = 12
    while ofs + 8 <= wavlength:
        cid = bytes(wav[ofs:ofs + 4])
        clen = _le_long(wav, ofs + 4)
        if clen < 0:
            break
        body = ofs + 8
        chunks.setdefault(cid, (body, min(clen, wavlength - body)))
        ofs = body + ((clen + 1) & ~1)

    if b'fmt ' not in chunks:
        console.Con_Printf(f'Missing fmt chunk ({name})\n')
        return info
    f, flen = chunks[b'fmt ']
    if flen < 16 or _le_short(wav, f) != 1:
        console.Con_Printf(f'Microsoft PCM format only ({name})\n')
        return info

    info.channels = _le_short(wav, f + 2)
    info.rate = _le_long(wav, f + 4)
    bits = _le_short(wav, f + 14)
    if bits not in (8, 16):
        console.Con_Printf(f'Only 8 and 16 bit WAV files supported ({name})\n')
        return info
    info.width = bits // 8

    # cue chunk -> loop start (dwSampleOffset of the first cue point)
    if b'cue ' in chunks:
        c, clen = chunks[b'cue ']
        if clen >= 28:
            info.loopstart = _le_long(wav, c + 24)
            # a following LIST/mark chunk gives the loop length
            if b'LIST' in chunks:
                l, llen = chunks[b'LIST']
                if llen >= 24 and bytes(wav[l + 20:l + 24]) == b'mark':
                    info.samples = info.loopstart + _le_long(wav, l + 16)
    else:
        info.loopstart = -1

    if b'data' not in chunks:
        console.Con_Printf(f'Missing data chunk ({name})\n')
        return info
    d, dlen = chunks[b'data']
    if info.channels < 1:
        return info

    info.dataofs = d
    samples = dlen // info.width // info.channels
    if info.samples:
        if samples < info.samples:
            console.Con_Printf(f'Sound {name} has a bad loop length\n')
            info.samples = samples
    else:
        info.samples = samples

    return info


def ResampleSfx(sfx: q_sound.sfx_t, inrate: int, inwidth: int, pcm: bytes,
                nsamples: int, loopstart: int, shm_speed: int) -> q_sound.sfxcache_t:
    loadas8bit = int(cvar.Cvar_GetCvar('loadas8bit').value)

    stepscale = inrate / shm_speed if shm_speed else 1.0
    outcount = int(nsamples / stepscale)

    sc = q_sound.sfxcache_t()
    sc.length = outcount
    sc.loopstart = int(loopstart / stepscale) if loopstart != -1 else -1
    sc.speed = shm_speed or inrate
    sc.width = 1 if loadas8bit else inwidth
    sc.stereo = 0

    if inwidth == 2:
        src = array('h')
        src.frombytes(bytes(pcm[:nsamples * 2]))
        if sys.byteorder == 'big':
            src.byteswap()
    else:
        src = pcm[:nsamples]

    if stepscale == 1 and inwidth == 1 and sc.width == 1:
        # fast special case: unsigned 8 -> signed 8
        sc.data = bytearray((b - 128) & 0xFF for b in src)
        return sc

    last = nsamples - 1
    fracstep = int(stepscale * 256)
    # samplefrac is just i*fracstep, so source indices can be computed directly
    idx = [min((i * fracstep) >> 8, last) for i in range(outcount)]
    if sc.width == 2:
        if inwidth == 2:
            out = array('h', [src[si] for si in idx])
        else:
            out = array('h', [(src[si] - 128) << 8 for si in idx])
        if sys.byteorder == 'big':
            out.byteswap()
        sc.data = bytearray(out.tobytes())
    else:
        if inwidth == 2:
            sc.data = bytearray([(src[si] >> 8) & 0xFF for si in idx])
        else:
            sc.data = bytearray([src[si] ^ 0x80 for si in idx])
    return sc


def S_LoadSound(sfx: q_sound.sfx_t):
    """Load (and cache on sfx.cache) the sound for `sfx`. Returns an sfxcache_t or None."""
    if not sfx:
        return None

    if sfx.cache is not None:
        return sfx.cache

    name = f'sound/{sfx.name}'
    ffr = common.COM_FOpenFile(name)
    if ffr is None or ffr.file is None or ffr.filesize <= 0:
        console.Con_Printf(f"S_LoadSound: couldn't load {name}\n")
        return None
    try:
        data = ffr.file.read(ffr.filesize)
    finally:
        ffr.file.close()

    info = GetWavinfo(sfx.name, data, len(data))
    if info.channels != 1:
        if info.channels:
            console.Con_Printf(f'{sfx.name} is a stereo sample\n')
        return None
    if info.samples <= 0 or info.dataofs <= 0:
        console.Con_Printf(f'S_LoadSound: invalid wav info for {sfx.name}\n')
        return None

    import snd_dma
    speed = snd_dma.shm.speed if snd_dma.shm is not None else info.rate

    sfx.cache = ResampleSfx(sfx, info.rate, info.width, data[info.dataofs:],
                            info.samples, info.loopstart, speed)
    return sfx.cache
