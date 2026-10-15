#cl_tent.py

import math
import random

import cl_main
import common
import console
import gl_model
import gl_vidsdl
import host
import mathlib
import protocol
import q_sound
import quakedef
import r_part
import render
import snd_dma
import sys_sdl_unix

num_temp_entities: int = 0
cl_temp_entities: list[render.entity_t] = []
cl_beams: list[quakedef.beam_t] = []

cl_sfx_wizhit: q_sound.sfx_t = None
cl_sfx_knighthit: q_sound.sfx_t = None
cl_sfx_tink1: q_sound.sfx_t = None
cl_sfx_ric1: q_sound.sfx_t = None
cl_sfx_ric2: q_sound.sfx_t = None
cl_sfx_ric3: q_sound.sfx_t = None
cl_sfx_r_exp3: q_sound.sfx_t = None


def CL_InitTEnts():
    global cl_sfx_wizhit, cl_sfx_knighthit, cl_sfx_tink1
    global cl_sfx_ric1, cl_sfx_ric2, cl_sfx_ric3, cl_sfx_r_exp3

    cl_sfx_wizhit = snd_dma.S_PrecacheSound('wizard/hit.wav')
    cl_sfx_knighthit = snd_dma.S_PrecacheSound('hknight/hit.wav')
    cl_sfx_tink1 = snd_dma.S_PrecacheSound('weapons/tink1.wav')
    cl_sfx_ric1 = snd_dma.S_PrecacheSound('weapons/ric1.wav')
    cl_sfx_ric2 = snd_dma.S_PrecacheSound('weapons/ric2.wav')
    cl_sfx_ric3 = snd_dma.S_PrecacheSound('weapons/ric3.wav')
    cl_sfx_r_exp3 = snd_dma.S_PrecacheSound('weapons/r_exp3.wav')


def CL_ParseBeam(m: quakedef.qmodel_t):
    start: list[float] = [0, 0, 0]
    end  : list[float] = [0, 0, 0]

    ent = common.MSG_ReadShort()

    start[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    start[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    start[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

    end[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    end[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
    end[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

    for b in cl_beams:
        if b.entity == ent:
            b.entity = ent
            b.model = m
            b.endtime = cl_main.cl.time + 0.2
            mathlib.VectorCopy(start, b.start)
            mathlib.VectorCopy(end, b.end)
            return

    for b in cl_beams:
        if not b.model or b.endtime < cl_main.cl.time:
            b.entity = ent
            b.model = m
            b.endtime = cl_main.cl.time + 0.2
            mathlib.VectorCopy(start, b.start)
            mathlib.VectorCopy(end, b.end)
            return

    if host.dev_overflows.beams == 0 or host.dev_overflows.beams + 3 < host.realtime:
        console.Con_Printf('Beam list overflow')
        host.dev_overflows.beams = host.realtime


def CL_ParseTEnt():
    pos: list[float] = [0, 0, 0]
    dl: quakedef.dlight_t = None

    _type = common.MSG_ReadByte()
    match _type:
        case protocol.TE_WIZSPIKE:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_RunParticleEffect(pos, mathlib.vec3_origin, 20, 30)
            snd_dma.S_StartSound(-1, 0, cl_sfx_wizhit, pos, 1, 1)

        case protocol.TE_KNIGHTSPIKE:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_RunParticleEffect(pos, mathlib.vec3_origin, 226, 20)
            snd_dma.S_StartSound(-1, 0, cl_sfx_knighthit, pos, 1, 1)

        case protocol.TE_SPIKE:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_RunParticleEffect(pos, mathlib.vec3_origin, 0, 10)

            if random.random() < 0.8:
                snd_dma.S_StartSound(-1, 0, cl_sfx_tink1, pos, 1, 1)
            else:
                rnd =  random.randrange(4)
                if rnd == 1:
                    snd_dma.S_StartSound(-1, 0, cl_sfx_ric1, pos, 1, 1)
                elif rnd == 2:
                    snd_dma.S_StartSound(-1, 0, cl_sfx_ric2, pos, 1, 1)
                else:
                    snd_dma.S_StartSound(-1, 0, cl_sfx_ric3, pos, 1, 1)

        case protocol.TE_SUPERSPIKE:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_RunParticleEffect(pos, mathlib.vec3_origin, 0, 20)

            if random.random() < 0.8:
                snd_dma.S_StartSound(-1, 0, cl_sfx_tink1, pos, 1, 1)
            else:
                rnd =  random.randrange(4)
                if rnd == 1:
                    snd_dma.S_StartSound(-1, 0, cl_sfx_ric1, pos, 1, 1)
                elif rnd == 2:
                    snd_dma.S_StartSound(-1, 0, cl_sfx_ric2, pos, 1, 1)
                else:
                    snd_dma.S_StartSound(-1, 0, cl_sfx_ric3, pos, 1, 1)

        case protocol.TE_GUNSHOT:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_RunParticleEffect(pos, mathlib.vec3_origin, 0, 20)

        case protocol.TE_EXPLOSION:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_ParticleExplosion(pos)
            dl = cl_main.CL_AllocDlight(0)
            mathlib.VectorCopy( pos, dl.origin)
            dl.radius = 350
            dl.die = cl_main.cl.time + 0.5
            dl.decay = 300
            snd_dma.S_StartSound(-1, 0, cl_sfx_r_exp3, pos, 1, 1)

        case protocol.TE_TAREXPLOSION:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_BlobExplosion(pos)

            snd_dma.S_StartSound(-1, 0, cl_sfx_r_exp3, pos, 1, 1)

        case protocol.TE_LIGHTNING1:
            CL_ParseBeam(gl_model.Mod_ForName('progs/bolt.mdl'))

        case protocol.TE_LIGHTNING2:
            CL_ParseBeam(gl_model.Mod_ForName('progs/bolt2.mdl'))

        case protocol.TE_LIGHTNING3:
            CL_ParseBeam(gl_model.Mod_ForName('progs/bolt3.mdl'))

        case protocol.TE_BEAM:
            CL_ParseBeam(gl_model.Mod_ForName('progs/beam.mdl'))

        case protocol.TE_LAVASPLASH:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_LavaSplash(pos)

        case protocol.TE_TELEPORT:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            r_part.R_TeleportSplash(pos)

        case protocol.TE_EXPLOSION2:
            pos[0] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[1] = common.MSG_ReadCoord(cl_main.cl.protocolflags)
            pos[2] = common.MSG_ReadCoord(cl_main.cl.protocolflags)

            colorStart = common.MSG_ReadByte()
            colorLength = common.MSG_ReadByte()

            r_part.R_ParticleExplosion2(pos, colorStart, colorLength)

            dl = cl_main.CL_AllocDlight(0)
            mathlib.VectorCopy(pos, dl.origin)

            dl.radius = 350
            dl.die = cl_main.cl.time + 0.5
            dl.decay = 300

            snd_dma.S_StartSound(-1, 0, cl_sfx_r_exp3, pos, 1, 1)

        case _:
            sys_sdl_unix.Sys_Error('CL_ParseTEnt: bad type')


def CL_NewTempEntity() -> render.entity_t:
    global num_temp_entities

    if cl_main.cl_numvisedicts == quakedef.MAX_VISEDICTS:
        return None
    if num_temp_entities == quakedef.MAX_TEMP_ENTITIES:
        return None

    ent:render.entity_t = cl_temp_entities[num_temp_entities]
    ent.__init__()

    num_temp_entities += 1

    cl_main.cl_visedicts[cl_main.cl_numvisedicts] = ent
    cl_main.cl_numvisedicts += 1

    ent.scale = protocol.ENTSCALE_DEFAULT
    ent.colormap = gl_vidsdl._vid.colormap

    return ent

def CL_UpdateTEnts():
    global num_temp_entities
    num_temp_entities = 0

    dist: list[float] = [0, 0, 0]
    org: list[float] = [0, 0, 0]

    random.seed(cl_main.cl.time * 1000)

    for b in cl_beams:
        if not b.model or b.endtime < cl_main.cl.time:
            continue
        if b.entity == cl_main.cl.viewentity:
            mathlib.VectorCopy(cl_main.cl_entities[cl_main.cl.viewentity].origin, b.start)

        mathlib.VectorSubtract(b.end, b.start, dist)

        if dist[1] == 0 and dist[0] == 0:
            yaw = 0

            if dist[2] > 0:
                pitch = 90
            else:
                pitch = 270
        else:
            yaw = math.atan2(dist[1], dist[0]) * 180 / math.pi
            if yaw < 0:
                yaw += 360

            forward = math.sqrt(dist[0] * dist[0] + dist[1] * dist[1])
            pitch = math.atan2(dist[2], forward) * 180 / math.pi
            if pitch < 0:
                pitch += 360


        mathlib.VectorCopy(b.start, org)
        d = mathlib.VectorNormalize(dist)

        while d > 0:
            ent = CL_NewTempEntity()
            if not ent:
                return

            mathlib.VectorCopy(org, ent.origin)

            ent.model = b.model
            ent.angles[0] = pitch
            ent.angles[1] = yaw
            ent.angles[2] = random.randrange(360)

            for j in range(3):
                org[j] += dist[j] * 30
            d -= 30


# end
















