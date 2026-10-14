#gl_refrag.py

import bspfile
import console
import cl_main
import gl_rmain
import host
import mathlib
import protocol
import quakedef
import render

r_pefragtopnode: quakedef.mnode_t = None

r_emins: list[float] = [0, 0, 0]
r_emaxs: list[float] = [0, 0, 0]
r_addent: quakedef.entity_t = None

EXTRA_EFRAGS  =  128

def R_GetEfrag():
    if cl_main.cl.free_efrags:
        ef:render.efrag_t = cl_main.cl.free_efrags
        cl_main.cl.free_efrags = ef.leafnext
        ef.leafnext = None
        cl_main.cl.num_efrags += 1
        return ef
    else:
        # Allocate a batch of efrag_t nodes and link them into free_efrags
        new_efrags = [render.efrag_t() for _ in range(EXTRA_EFRAGS)]

        for i in range(EXTRA_EFRAGS - 1):
            new_efrags[i].leafnext = new_efrags[i + 1]

        new_efrags[EXTRA_EFRAGS - 1].leafnext = None
        cl_main.cl.free_efrags = new_efrags[0]

        # Call recursively to pop a newly allocated efrag
        return R_GetEfrag()

def R_SplitEntityOnNode(node: quakedef.mnode_t):
    global r_pefragtopnode

    leaf: quakedef.mleaf_t = None
    ef: render.efrag_t = None

    if node.contents == quakedef.CONTENTS_SOLID:
        return

    if node.contents < 0:
        if not r_pefragtopnode:
            r_pefragtopnode = node
        leaf = node

        ef = R_GetEfrag()
        ef.entity = r_addent

        ef.leafnext = leaf.efrags
        leaf.efrags = ef

        return

    splitplane = node.plane
    sides = mathlib.BoxOnPlaneSide(r_emins, r_emaxs, splitplane)

    if sides == 3:  # noqa: SIM102
        if not r_pefragtopnode:
            r_pefragtopnode = node

    if sides & 1:
        R_SplitEntityOnNode(node.children[0])
    if sides & 2:
        R_SplitEntityOnNode(node.children[1])

def R_CheckEfrags():
    if cl_main.cls.signon < 2:
        return
    if cl_main.cl.num_efrags > 640 and host.dev_peakstats.efrags <= 640:
        console.Con_DPrintf(f'{cl_main.cl.num_efrags} efrags exceeds standard limit of 640')

    host.dev_stats.efrags = cl_main.cl.num_efrags
    host.dev_peakstats.efrags = max(cl_main.cl.num_efrags, host.dev_peakstats.efrags)


def R_AddEfrags(ent: render.entity_t):
    global r_addent, r_pefragtopnode

    if not ent.model:
        return

    r_addent = ent
    r_pefragtopnode = None

    entmodel: quakedef.qmodel_t = ent.model
    scalefactor = protocol.ENTSCALE_DECODE(ent.scale)

    if scalefactor != 1.0:
        mathlib.VectorMA(ent.origin, scalefactor, entmodel.mins, r_emins)
        mathlib.VectorMA(ent.origin, scalefactor, entmodel.maxs, r_emaxs)
    else:
        mathlib.VectorAdd(ent.origin, entmodel.mins, r_emins)
        mathlib.VectorAdd(ent.origin, entmodel.maxs, r_emaxs)

    R_SplitEntityOnNode(cl_main.cl.worldmodel.nodes[0])

    ent.topnode = r_pefragtopnode

    R_CheckEfrags()


def R_StoreEfrags(pefrag):
    """Walks the efrag linked list for a leaf and adds unvisited entities to visedicts.

    C equivalent:
    void R_StoreEfrags (efrag_t **ppefrag) in r_efrag.c
    """
    while pefrag:
        pent = pefrag.entity

        if (
            pent.visframe != gl_rmain.r_framecount
            and cl_main.cl_numvisedicts < quakedef.MAX_VISEDICTS
        ):
            cl_main.cl_visedicts[cl_main.cl_numvisedicts] = pent
            cl_main.cl_numvisedicts += 1
            pent.visframe = gl_rmain.r_framecount

        pefrag = pefrag.leafnext