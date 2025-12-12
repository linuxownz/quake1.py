#snd_dma.py 

import sdl2.sdlmixer

MAX_DYNAMIC_CHANNELS = 1024
NUM_AMBIENTS = 4

def SNDDMA_LockBuffer():
    SDL_LockAudio()

def S_ClearBuffer():
    if not sound_started:
        return

    SNDDMA_LockBuffer()
    

def S_StopAllSounds(clear):
    if not sound_started:
        return

    total_channels = MAX_DYNAMIC_CHANNELS + NUM_AMBIENTS

    if clear:
        S_ClearBuffer()