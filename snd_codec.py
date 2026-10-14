#snd_codec.py

import io
from enum import Enum

import common
import console
import snd_wave


class snd_codec_t:
    def __init__(self):
        self.type: int = 0
        self.initialized: bool = False
        self.ext: str = ''
        self.initialize = None
        self.shutdown = None
        self.codec_open = None
        self.codec_read = None
        self.codec_rewind = None
        self.codec_jump = None
        self.codec_close = None
        self.next: snd_codec_t = None

class snd_info_t:
    def __init__(self):
        self.rate: int = 0
        self.bits: int = 0
        self.width: int = 0
        self.channels:int = 0
        self.samples: int = 0
        self.blocksize: int = 0
        self.size: int = 0
        self.dataofs: int = 0

class stream_status_t(Enum):
    STREAM_NONE = -1
    STREAM_INIT = 0
    STREAM_PAUSE = 1
    STREAM_PLAY = 2

class snd_stream_t:
    def __init__(self):
        self.fh: common._fshandle_t = None
        self.pak: bool = False
        self.name = ''
        self.info: snd_info_t = None
        self.status: stream_status_t = stream_status_t.STREAM_NONE
        self.codec: snd_codec_t = None
        self.loop: bool = False
        self.priv: bytes = None


CODECTYPE_NONE   =  0
CODECTYPE_MID    =  (1 << 0)
CODECTYPE_MOD    =  (1 << 1)
CODECTYPE_FLAC   =  (1 << 2)
CODECTYPE_WAV    =  (1 << 3)
CODECTYPE_MP3    =  (1 << 4)
CODECTYPE_VORBIS =  (1 << 5)
CODECTYPE_OPUS   =  (1 << 6)
CODECTYPE_UMX    =  (1 << 7)

CODECTYPE_WAVE   =  CODECTYPE_WAV
CODECTYPE_MIDI   =  CODECTYPE_MID



codecs: snd_codec_t = None

USE_CODEC_UMX = 0
USE_CODEC_MODPLUG = 0
USE_CODEC_MIKMOD = 0
USE_CODEC_XMP = 0
USE_CODEC_WAVE = 1
USE_CODEC_FLAC = 0
USE_CODEC_MP3 = 0
USE_CODEC_VORBIS = 0
USE_CODEC_OPUS = 0

def S_CodecRegister(codec: snd_codec_t):
    global codecs
    codec.next = codecs
    codecs = codec

def S_CodecInit():
    global codecs
    codecs = None

    # if USE_CODEC_UMX:
    #     S_CodecRegister(umx_codec)
    # if USE_CODEC_MODPLUG:
    #     S_CodecRegister(umx_codec)
    # if USE_CODEC_MIKMOD:
    #     S_CodecRegister(umx_codec)
    # if USE_CODEC_XMP:
    #     S_CodecRegister(umx_codec)
    if USE_CODEC_WAVE:
        S_CodecRegister(snd_wave.wav_codec)
    # if USE_CODEC_FLAC:
    #     S_CodecRegister(umx_codec)
    # if USE_CODEC_MP3:
    #     S_CodecRegister(umx_codec)
    # if USE_CODEC_VORBIS:
    #     S_CodecRegister(umx_codec)
    # if USE_CODEC_OPUS:
    #     S_CodecRegister(umx_codec)

    codec:snd_codec_t = codecs
    while codec:
        codec.initialized = bool(codec.initialize())
        codec = codec.next


def S_CodecShutdown():
    global codecs
    codec:snd_codec_t = codecs
    while codec:
        codec.shutdown()
        codec = codec.next

    codecs = None

def S_CodecOpenStreamType(filename: str, _type: int, loop: bool) -> snd_stream_t:

    if _type == CODECTYPE_NONE:
        console.Con_Printf(f'Bad type for {filename}')
        return None

    codec = codecs
    while codec:
        if _type == codec.type:
            break
        codec = codec.next

    if not codec:
        console.Con_Printf(f'Unknown type for {filename}\n')
        return None

    stream: snd_stream_t = S_CodecUtilOpen(filename, codec, loop)
    if stream:
        if codec.codec_open(stream):
            stream.status = stream_status_t.STREAM_PLAY
        else:
            S_CodecUtilClose(stream)

    return stream

def S_CodecOpenStreamExt(filename: str, loop: bool) -> snd_stream_t:
    ext = common.COM_FileGetExtension(filename)
    if not ext:
        console.Con_Printf(f'No extension for {filename}')
        return None

    codec: snd_codec_t = codecs
    while codec:
        if ext.lower() == codec.ext.lower():
            break
        codec = codec.next

    if not codec:
        console.Con_Printf(f'Unknown extension for {filename}\n')
        return None

    stream: snd_stream_t = S_CodecUtilOpen(filename, codec, loop)
    if stream:
        if codec.codec_open(stream):
            stream.status = stream_status_t.STREAM_PLAY
        else:
            S_CodecUtilClose(stream)

    return stream

def S_CodecOpenStreamAny(filename: str, loop: bool) -> snd_stream_t:

    codec: snd_codec_t = None
    stream: snd_stream_t = None

    ext = common.COM_FileGetExtension(filename)
    if not ext:
        codec = codecs
        while codec:
            tmp = filename + '.' + codec.ext
            stream = S_CodecUtilOpen(tmp, codec, loop)
            if stream:
                if codec.codec_open(stream):
                    stream.status = stream_status_t.STREAM_PLAY
                    return stream
                S_CodecUtilClose(stream)
            codec = codec.next

        return None
    else:
        codec = codecs
        while codec:
            if ext.lower() == codec.ext.lower():
                break
            codec = codec.next
        if not codec:
            console.Con_Printf(f'Unknown extension for {filename}\n')
            return None

        stream = S_CodecUtilOpen(filename, codec, loop)
        if stream:
            if codec.codec_open(stream):
                stream.status = stream_status_t.STREAM_PLAY
            else:
                S_CodecUtilClose(stream)
        return stream


def S_CodecForwardStream(stream: snd_stream_t, _type:int) -> bool:
    codec: snd_codec_t = codecs
    while codec:
        if _type == codec.type:
            break
        codec = codec.next

    if not codec:
        return False

    stream.codec = codec
    return codec.codec_open(stream)

def S_CodecCloseStream(stream: snd_stream_t):
    stream.status = stream_status_t.STREAM_NONE
    stream.codec.codec_close(stream)

def S_CodecRewindStream(stream: snd_stream_t) -> int:
    return stream.codec.codec_rewind(stream)

def S_CodecJumpToOrder(stream: snd_stream_t, to: int) -> int:
    if stream.codec.codec_jump:
        return stream.codec.codec_jump(stream, to)
    return -1

def S_CodecReadStream(stream: snd_stream_t, _bytes: int, buffer: bytearray) -> int:
    return stream.codec.codec_read(stream, _bytes, buffer)


def S_CodecUtilOpen(filename: str, codec: snd_codec_t, loop: bool) -> snd_stream_t:
    ffr = common.COM_FOpenFile(filename)

    if ffr is None or ffr.file is None or ffr.filesize == -1:
        console.Con_Printf(f'Couldnt open {filename}\n')
        return None

    stream: snd_stream_t = snd_stream_t()

    stream.codec = codec
    stream.loop = loop
    # file is already positioned at the start of the entry (loose file or inside a pak)
    stream.fh = common._fshandle_t(ffr.file, ffr.is_pak, ffr.file.tell(), ffr.filesize, 0)
    stream.pak = ffr.is_pak
    stream.name = filename

    return stream

def S_CodecUtilClose(stream: snd_stream_t):
    stream.fh.file.close()


def S_CodecIsAvailable(_type: int) -> int:
    codec: snd_codec_t = codecs
    while codec:
        if _type == codec.type:
            return codec.initialized
        codec = codec.next

    return -1









