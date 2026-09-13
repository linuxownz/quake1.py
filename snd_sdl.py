#snd_sdl.py 

import sdl2
import sdl2.ext

import console
import cvar
import q_sound

buffersize = 0

def paint_audio(unused, stream, len):
    pass

def SNDDMA_Init(dma : q_sound.dma_t):

    snd_mixspeed = int(cvar.Cvar_GetCvar('snd_mixspeed').value)
    loadas8bit   = int(cvar.Cvar_GetCvar('loadas8bit').value)

    if sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_AUDIO) < 0:
        console.Con_Printf('couldnt init SDL audio %s\n' % sdl2.SDL_GetError())

    freq     = snd_mixspeed
    aformat   = sdl2.AUDIO_U8 if loadas8bit else sdl2.AUDIO_S16SYS
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

    AUDIO_CALLBACK_FUNC = sdl2.SDL_AudioCallback(paint_audio)

    desired = sdl2.SDL_AudioSpec(
        freq     = freq,
        aformat  = aformat,
        channels = channels,
        samples  = samples,
        callback = AUDIO_CALLBACK_FUNC,
        userdata = None
    )

    if sdl2.SDL_OpenAudio(desired, None) == -1:
        console.Con_Printf('Couldnt open SDL audio %s' % sdl2.SDL_GetError())
        sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_AUDIO)
        return False
    
    import snd_dma
    snd_dma.shm = dma

    snd_dma.shm.samplebits = desired.format & 0xFF
    snd_dma.shm.signed8    = desired.format == sdl2.AUDIO_S8
    snd_dma.shm.speed      = desired.freq
    snd_dma.shm.channels   = desired.channels

    tmp = ( desired.samples * desired.channels * 10 )
    if tmp & ( tmp - 1 ):
        val = 1
        while val < tmp:
            val <<= 1
            
        tmp = val
    
    snd_dma.shm.samples   = tmp
    snd_dma.shm.samplepos = 0
    snd_dma.shm.submission_chunk = 1

    console.Con_Printf('SDL audio spec  : %d Hz, %d samples, %d channels\n' % (desired.freq, desired.samples, desired.channels))

    driver = sdl2.SDL_GetCurrentAudioDriver()
    device = sdl2.SDL_GetAudioDeviceName(0, sdl2.SDL_FALSE)

    drivername = driver + b' : ' + device

    buffersize = snd_dma.shm.samples * snd_dma.shm.samplebits / 8
    console.Con_Printf ("SDL audio driver: %s, %d bytes buffer\n" % ( drivername, buffersize) )

    snd_dma.shm.buffer = bytearray(int(buffersize))

    sdl2.SDL_PauseAudio(0)

    return True


    
    