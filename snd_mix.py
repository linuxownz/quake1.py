#snd_mix.py  (port of QuakeSpasm snd_mix.c -- portable code to mix sounds for snd_dma)
#
# Data conventions (see snd_mem.py):
#   sfx.cache is an sfxcache_t; sc.data is a bytearray holding signed 8-bit samples
#   (width 1) or little-endian signed 16-bit samples (width 2), mono.
#
# Not ported yet: the underwater low-pass filter (snd_filterquality) -- plain mixing only.

import sys

import cvar
import q_sound
import snd_dma
import snd_mem

PAINTBUFFER_SIZE = 2048

paintbuffer = [q_sound.portable_samplepair_t() for _ in range(PAINTBUFFER_SIZE)]

# Kept for compatibility with snd_dma.Snd_InitScaletable(). The mixer below scales samples
# directly (data * vol >> 8), so the table is not used.
snd_scaletable = [[0] * 256 for _ in range(32)]
snd_vol = 0


def SND_InitScaletable():
    sfxvolume = float(cvar.Cvar_GetCvar('volume').value)
    for i in range(32):
        scale = i * 8 * 256 * sfxvolume
        for j in range(256):
            snd_scaletable[i][j] = int((j if j < 128 else j - 256) * scale)


SND_InitScaleTable = SND_InitScaletable   # old spelling used by snd_dma's callback


def _sample_view(sc):
    """Zero-copy signed view of sc.data (cached on the sfxcache_t)."""
    v = getattr(sc, '_view', None)
    if v is None:
        mv = memoryview(sc.data)
        v = mv.cast('h') if sc.width == 2 else mv.cast('b')
        sc._view = v
    return v


def SND_PaintChannelFrom8(ch, sc, count, offset):
    leftvol, rightvol = ch.leftvol, ch.rightvol
    sfx = _sample_view(sc)
    pos = int(ch.pos)
    pb = paintbuffer
    for i in range(count):
        data = sfx[pos + i]            # signed 8 bit; (data << 8) * vol >> 8 == data * vol
        p = pb[offset + i]
        p.left += data * leftvol
        p.right += data * rightvol
    ch.pos = pos + count


def SND_PaintChannelFrom16(ch, sc, count, offset):
    leftvol, rightvol = ch.leftvol, ch.rightvol
    sfx = _sample_view(sc)
    pos = int(ch.pos)
    pb = paintbuffer
    for i in range(count):
        data = sfx[pos + i]
        p = pb[offset + i]
        p.left += (data * leftvol) >> 8
        p.right += (data * rightvol) >> 8
    ch.pos = pos + count


def S_TransferPaintBuffer(endtime):
    """Copy the mixed paintbuffer into the DMA ring buffer."""
    shm = snd_dma.shm
    painted = snd_dma.paintedtime
    nframes = endtime - painted
    out_mask = shm.samples - 1
    out_idx = (painted * shm.channels) & out_mask
    stereo = shm.channels == 2
    vol = snd_vol
    pb = paintbuffer

    if shm.samplebits == 16:
        mv = memoryview(shm.buffer).cast('h')
        try:
            for i in range(nframes):
                p = pb[i]
                v = (p.left * vol) >> 8
                mv[out_idx] = 32767 if v > 32767 else (-32768 if v < -32768 else v)
                out_idx = (out_idx + 1) & out_mask
                if stereo:
                    v = (p.right * vol) >> 8
                    mv[out_idx] = 32767 if v > 32767 else (-32768 if v < -32768 else v)
                    out_idx = (out_idx + 1) & out_mask
        finally:
            mv.release()
    else:
        buf = shm.buffer
        bias = 0 if shm.signed8 else 128
        for i in range(nframes):
            p = pb[i]
            for side in ((p.left, p.right) if stereo else (p.left,)):
                v = (side * vol) >> 8
                v = 32767 if v > 32767 else (-32768 if v < -32768 else v)
                buf[out_idx] = ((v >> 8) + bias) & 0xFF
                out_idx = (out_idx + 1) & out_mask


def S_PaintChannels(endtime: int):
    global snd_vol

    snd_vol = int(float(cvar.Cvar_GetCvar('volume').value) * 256)

    while snd_dma.paintedtime < endtime:
        painted = snd_dma.paintedtime

        # if paintbuffer is smaller than DMA buffer
        end = endtime
        if endtime - painted > PAINTBUFFER_SIZE:
            end = painted + PAINTBUFFER_SIZE
        n = end - painted

        # clear the paint buffer
        for i in range(n):
            paintbuffer[i].left = 0
            paintbuffer[i].right = 0

        # streamed raw samples (music) -- S_RawSamples fills s_rawsamples
        if snd_dma.s_rawend >= painted:
            stop = min(end, snd_dma.s_rawend)
            raw = snd_dma.s_rawsamples
            mask = q_sound.MAX_RAW_SAMPLES - 1
            for t in range(painted, stop):
                src = raw[t & mask]
                p = paintbuffer[t - painted]
                p.left += src.left >> 8
                p.right += src.right >> 8

        # paint in the channels
        for ci in range(snd_dma.total_channels):
            ch = snd_dma.snd_channels[ci]
            if not ch.sfx:
                continue
            if not ch.leftvol and not ch.rightvol:
                continue

            sc = snd_mem.S_LoadSound(ch.sfx)
            if not sc:
                ch.sfx = None
                continue

            ltime = painted
            while ltime < end:                      # paint up to end
                count = (ch.end - ltime) if ch.end < end else (end - ltime)
                if count > 0:
                    if sc.width == 1:
                        SND_PaintChannelFrom8(ch, sc, count, ltime - painted)
                    else:
                        SND_PaintChannelFrom16(ch, sc, count, ltime - painted)
                    ltime += count

                # if at end of loop, restart
                if ltime >= ch.end:
                    if sc.loopstart >= 0:
                        ch.pos = sc.loopstart
                        ch.end = ltime + sc.length - ch.pos
                    else:                           # channel just stopped
                        ch.sfx = None
                        break

        # transfer out according to DMA format
        S_TransferPaintBuffer(end)
        snd_dma.paintedtime = end
