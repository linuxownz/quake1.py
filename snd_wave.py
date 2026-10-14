#snd_wave.py  (port of QuakeSpasm snd_wave.c -- streaming WAV codec, used for music/CD tracks)

import io
import struct

import console

# NOTE: snd_codec imports this module, so don't import snd_codec at load time
# (circular). The codec object below just duck-types snd_codec.snd_codec_t.
CODECTYPE_WAV = 1 << 3

WAV_FORMAT_PCM = 1


def S_WAV_CodecInitialize():
    return True


def S_WAV_CodecShutdown():
    pass


def S_WAV_CodecOpenStream(stream) -> bool:
    import snd_codec

    f: io.FileIO = stream.fh.file
    start = stream.fh.start
    length = stream.fh.length

    f.seek(start)
    hdr = f.read(12)
    if len(hdr) < 12 or hdr[0:4] != b'RIFF' or hdr[8:12] != b'WAVE':
        console.Con_Printf(f'{stream.name} is not a valid .wav file\n')
        return False

    fmt = None
    data_ofs = None
    data_len = 0
    pos = 12
    while pos + 8 <= length:
        f.seek(start + pos)
        ch = f.read(8)
        if len(ch) < 8:
            break
        cid = ch[0:4]
        clen = struct.unpack('<i', ch[4:8])[0]
        if clen < 0:
            break
        body = pos + 8
        if cid == b'fmt ' and fmt is None:
            f.seek(start + body)
            fmt = f.read(min(clen, 16))
        elif cid == b'data':
            data_ofs = body
            data_len = min(clen, length - body)
            break
        pos = body + ((clen + 1) & ~1)

    if fmt is None or len(fmt) < 16:
        console.Con_Printf(f'{stream.name} is missing the fmt chunk\n')
        return False
    if data_ofs is None:
        console.Con_Printf(f'{stream.name} is missing the data chunk\n')
        return False

    tag, channels, rate, _byterate, _align, bits = struct.unpack('<HHIIHH', fmt[:16])
    if tag != WAV_FORMAT_PCM:
        console.Con_Printf(f'{stream.name} is not Microsoft PCM format\n')
        return False
    if bits not in (8, 16) or channels not in (1, 2):
        console.Con_Printf(f'{stream.name}: unsupported wav (bits={bits}, channels={channels})\n')
        return False

    info = snd_codec.snd_info_t()
    info.rate = rate
    info.bits = bits
    info.width = bits // 8
    info.channels = channels
    info.dataofs = data_ofs
    info.size = data_len
    info.samples = data_len // (info.width * channels)
    info.blocksize = info.samples
    stream.info = info
    stream.priv = {'pos': 0}

    f.seek(start + data_ofs)
    return True


def S_WAV_CodecReadStream(stream, nbytes: int, buffer: bytearray) -> int:
    info = stream.info
    st = stream.priv
    remaining = info.size - st['pos']
    nbytes = min(nbytes, remaining)
    if nbytes <= 0:
        return 0

    stream.fh.file.seek(stream.fh.start + info.dataofs + st['pos'])
    data = stream.fh.file.read(nbytes)
    n = len(data)

    if info.width == 1:
        data = bytes((b - 128) & 0xFF for b in data)   # unsigned 8 -> signed 8

    buffer[:n] = data
    st['pos'] += n
    return n


def S_WAV_CodecRewindStream(stream) -> int:
    stream.priv['pos'] = 0
    stream.fh.file.seek(stream.fh.start + stream.info.dataofs)
    return 0


def S_WAV_CodecCloseStream(stream):
    stream.fh.file.close()


class _WavCodec:
    def __init__(self):
        self.type = CODECTYPE_WAV
        self.initialized = False
        self.ext = 'wav'
        self.initialize = S_WAV_CodecInitialize
        self.shutdown = S_WAV_CodecShutdown
        self.codec_open = S_WAV_CodecOpenStream
        self.codec_read = S_WAV_CodecReadStream
        self.codec_rewind = S_WAV_CodecRewindStream
        self.codec_jump = None
        self.codec_close = S_WAV_CodecCloseStream
        self.next = None


wav_codec = _WavCodec()
