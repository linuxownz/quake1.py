#snd_mix.py

import q_sound

PAINTBUFFER_SIZE = 2048

paintbuffer : list[q_sound.portable_samplepair_t] = []
snd_scaletable = [ [ 0 for _ in range(256)] for _ in range(32)]

#####print(snd_scaletable)
