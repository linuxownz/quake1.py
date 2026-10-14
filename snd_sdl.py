#snd_sdl.py  (port of QuakeSpasm snd_sdl.c, SDL2 via pysdl2)

import atexit
import ctypes

import sdl2

import console
import cvar
import q_sound

buffersize = 0          # bytes in the DMA ring buffer

# SDL's audio thread keeps calling this for as long as the device is open.
# It MUST live in a module-level variable: as a local it was garbage-collected
# when SNDDMA_Init returned, and SDL then called freed memory (segfault, exit 245).
_audio_callback = None
_dma: q_sound.dma_t = None
_opened = False


def paint_audio(unused, stream, length):
    """SDL audio callback: copy the next `length` bytes of the DMA ring buffer to SDL."""
    try:
        shm = _dma
        if shm is None or not shm.buffer or buffersize <= 0:
            ctypes.memset(stream, 0, length)
            return

        addr = ctypes.cast(stream, ctypes.c_void_p).value
        sample_bytes = max(shm.samplebits // 8, 1)

        pos = shm.samplepos * sample_bytes
        if pos >= buffersize:
            shm.samplepos = pos = 0

        tobufend = buffersize - pos     # bytes to the end of the buffer
        len1 = length
        len2 = 0
        if len1 > tobufend:
            len1 = tobufend
            len2 = length - len1

        ctypes.memmove(addr, bytes(shm.buffer[pos:pos + len1]), len1)
        if len2 <= 0:
            shm.samplepos += len1 // sample_bytes
        else:
            # wraparound
            ctypes.memmove(addr + len1, bytes(shm.buffer[0:len2]), len2)
            shm.samplepos = len2 // sample_bytes

        if shm.samplepos >= shm.samples:
            shm.samplepos = 0
    except Exception:
        # never let an exception escape into SDL's thread
        try:
            ctypes.memset(stream, 0, length)
        except Exception:
            pass


def SNDDMA_Init(dma: q_sound.dma_t) -> bool:
    global buffersize, _audio_callback, _dma, _opened

    snd_mixspeed = int(cvar.Cvar_GetCvar('snd_mixspeed').value)
    loadas8bit   = int(cvar.Cvar_GetCvar('loadas8bit').value)

    if sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_AUDIO) < 0:
        console.Con_Printf('couldnt init SDL audio %s\n' % sdl2.SDL_GetError())
        return False

    freq    = snd_mixspeed
    aformat = sdl2.AUDIO_U8 if loadas8bit else sdl2.AUDIO_S16SYS
    channels = 2

    if freq <= 11025:
        samples = 256
    elif freq <= 22050:
        samples = 512
    elif freq <= 44100:
        samples = 1024
    elif freq <= 56000:
        samples = 2048
    else:
        samples = 4096

    _audio_callback = sdl2.SDL_AudioCallback(paint_audio)   # keep alive (module global)

    desired = sdl2.SDL_AudioSpec(
        freq     = freq,
        aformat  = aformat,
        channels = channels,
        samples  = samples,
        callback = _audio_callback,
        userdata = None
    )
    obtained = sdl2.SDL_AudioSpec(0, 0, 0, 0)

    if sdl2.SDL_OpenAudio(desired, obtained) == -1:
        console.Con_Printf('Couldnt open SDL audio %s\n' % sdl2.SDL_GetError())
        sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_AUDIO)
        _audio_callback = None
        return False

    if obtained.format not in (sdl2.AUDIO_S8, sdl2.AUDIO_U8, sdl2.AUDIO_S16SYS):
        console.Con_Printf('Unsupported audio format received (%u)\n' % obtained.format)
        sdl2.SDL_CloseAudio()
        sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_AUDIO)
        _audio_callback = None
        return False

    import snd_dma
    snd_dma.shm = dma

    dma.samplebits = obtained.format & 0xFF
    dma.signed8    = obtained.format == sdl2.AUDIO_S8
    dma.speed      = obtained.freq
    dma.channels   = obtained.channels

    tmp = obtained.samples * obtained.channels * 10
    if tmp & (tmp - 1):
        val = 1
        while val < tmp:
            val <<= 1
        tmp = val

    dma.samples          = tmp
    dma.samplepos        = 0
    dma.submission_chunk = 1

    console.Con_Printf('SDL audio spec  : %d Hz, %d samples, %d channels\n' %
                       (obtained.freq, obtained.samples, obtained.channels))

    driver = sdl2.SDL_GetCurrentAudioDriver() or b'?'
    device = sdl2.SDL_GetAudioDeviceName(0, sdl2.SDL_FALSE) or b'?'
    drivername = driver.decode('utf-8', 'replace') + ' : ' + device.decode('utf-8', 'replace')

    buffersize = dma.samples * dma.samplebits // 8
    console.Con_Printf('SDL audio driver: %s, %d bytes buffer\n' % (drivername, buffersize))

    # the buffer must be fully set up before the callback thread starts reading it
    dma.buffer = bytearray(buffersize)
    _dma = dma
    _opened = True
    atexit.register(SNDDMA_Shutdown)   # close the device before interpreter teardown

    sdl2.SDL_PauseAudio(0)
    return True


def SNDDMA_GetDMAPos() -> int:
    return _dma.samplepos if _dma is not None else 0


def SNDDMA_Shutdown():
    global _opened, _dma, _audio_callback, buffersize
    if not _opened:
        return
    _opened = False
    sdl2.SDL_PauseAudio(1)
    sdl2.SDL_CloseAudio()          # waits for the callback thread to finish
    sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_AUDIO)
    _dma = None
    buffersize = 0
    _audio_callback = None


def SNDDMA_LockBuffer():
    if _opened:
        sdl2.SDL_LockAudio()


def SNDDMA_Submit():
    # C: SDL_UnlockAudio() -- Submit releases the lock taken by LockBuffer
    if _opened:
        sdl2.SDL_UnlockAudio()


def SNDDMA_UnlockBuffer():
    if _opened:
        sdl2.SDL_UnlockAudio()


def SNDDMA_BlockSound():
    if _opened:
        sdl2.SDL_PauseAudio(1)


def SNDDMA_UnblockSound():
    if _opened:
        sdl2.SDL_PauseAudio(0)
