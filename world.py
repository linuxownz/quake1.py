#world.py

import common
import console
import gl_model
import host
import mathlib
import pr_edict
import pr_exec
import progs
import quakedef
import server
import sv_main
import sys_sdl_unix


class plane_t:
    def __init__(self):
        self.normal: list[float] = [0, 0, 0]
        self.dist = 0.0

class trace_t:
    def __init__(self):
        self.allsolid = False
        self.startsolid = False
        self.inopen = False
        self.inwater = False
        self.fraction = 0.0
        self.endpos: list[float] = [0, 0, 0]
        self.plane: plane_t = plane_t()
        self.ent: progs.edict_t = None

MOVE_NORMAL     = 0
MOVE_NOMONSTERS = 1
MOVE_MISSILE    = 2

box_hull: quakedef.hull_t = quakedef.hull_t()
box_clipnodes: list[quakedef.mclipnode_t] = [quakedef.mclipnode_t() for _ in range(6)]
box_planes = [quakedef.mplane_t([0.0, 0.0, 0.0], 0.0, 0, 0) for _ in range(6)]

class moveclip_t:
    def __init__(self):
        self.boxmins: list[float] = [0, 0, 0]
        self.boxmaxs: list[float] = [0, 0, 0]
        self.mins = 0.0
        self.maxs = 0.0
        self.mins2: quakedef.vec3_t = [0, 0, 0]
        self.maxs2: quakedef.vec3_t = [0, 0, 0]
        self.start = 0.0
        self.end = 0.0
        self.trace: trace_t = None
        self.type = 0
        self.passedict: progs.edict_t = None


class areanode_t:
    def __init__(self):
        self.axis = 0
        self.dist = 0.0
        self.children: list[areanode_t] = [None] * 2

        # In C, trigger_edicts and solid_edicts are link_t struct headers
        self.trigger_edicts = quakedef.link_t()
        self.solid_edicts = quakedef.link_t()

        # ClearLink initializes pointers to self for circular head node
        self.trigger_edicts.prev = self.trigger_edicts
        self.trigger_edicts.next = self.trigger_edicts
        self.solid_edicts.prev = self.solid_edicts
        self.solid_edicts.next = self.solid_edicts


AREA_DEPTH = 4
AREA_NODES = 32

sv_areanodes: list[areanode_t] = [ areanode_t() for _ in range(AREA_NODES)]
sv_numareanodes = len(sv_areanodes)

def SV_InitBoxHull():
    box_hull.clipnodes = box_clipnodes
    box_hull.planes = box_planes
    box_hull.firstclipnode = 0
    box_hull.lastclipnode = 5

    for i in range(6):
        box_clipnodes[i].planenum = i

        side = i & 1

        box_clipnodes[i].children[side] = quakedef.CONTENTS_EMPTY
        if i != 5:
            box_clipnodes[i].children[side ^ 1] = i + 1
        else:
            box_clipnodes[i].children[side ^ 1] = quakedef.CONTENTS_SOLID

        box_planes[i].type = i >> 1
        box_planes[i].normal[i>>1] = 1


def SV_HullForBox(mins: quakedef.vec3_t, maxs: quakedef.vec3_t) -> quakedef.hull_t:
    box_planes[0].dist = maxs[0]
    box_planes[1].dist = mins[0]
    box_planes[2].dist = maxs[1]
    box_planes[3].dist = mins[1]
    box_planes[4].dist = maxs[2]
    box_planes[5].dist = mins[2]

    return  box_hull

def SV_HullForEntity(ent: progs.edict_t, mins: quakedef.vec3_t, maxs: quakedef.vec3_t, offset: quakedef.vec3_t) -> quakedef.hull_t:

    size: quakedef.vec3_t = [0, 0, 0]
    hullmins: quakedef.vec3_t = [0, 0, 0]
    hullmaxs: quakedef.vec3_t = [0, 0, 0]

    if ent.v.solid == server.SOLID_BSP:
        if ent.v.movetype != server.MOVETYPE_PUSH:
            host.Host_Error(f'SOLID_BSP without MOVETYPE_PUSH ( {pr_edict.PR_GetString(ent.v.classname)} at {ent.v.origin[0]} {ent.v.origin[1]} {ent.v.origin[2]})')

        model = sv_main.sv.models[int(ent.v.modelindex)]

        if not model or model.type != quakedef.modtype_t.mod_brush:
            host.Host_Error(f'SOLID_BSP with a non bsp model ({pr_edict.PR_GetString(ent.v.classname)} at {ent.v.origin[0]} {ent.v.origin[1]} {ent.v.origin[2]})')

        mathlib.VectorSubtract(maxs, mins, size)

        if size[0] < 3:
            hull = model.hulls[0]
        elif size[0] <= 32:
            hull = model.hulls[1]
        else:
            hull = model.hulls[2]

        mathlib.VectorSubtract(hull.clip_mins, mins, offset)
        mathlib.VectorAdd(offset, ent.v.origin, offset)
    else:
        mathlib.VectorSubtract(ent.v.mins, maxs, hullmins)
        mathlib.VectorSubtract(ent.v.maxs, mins, hullmaxs)

        hull = SV_HullForBox(hullmins, hullmaxs)

        mathlib.VectorCopy(ent.v.origin, offset)

    return hull

def SV_CreateAreaNode( depth: int, mins: quakedef.vec3_t, maxs: quakedef.vec3_t) -> areanode_t:
    global sv_numareanodes

    mins1: quakedef.vec3_t = [0, 0, 0]
    mins2: quakedef.vec3_t = [0, 0, 0]
    maxs1: quakedef.vec3_t = [0, 0, 0]
    maxs2: quakedef.vec3_t = [0, 0, 0]
    size : quakedef.vec3_t = [0, 0, 0]

    anode: areanode_t = sv_areanodes[sv_numareanodes]
    sv_numareanodes += 1

    common.ClearLink(anode.trigger_edicts)
    common.ClearLink(anode.solid_edicts)

    if depth == AREA_DEPTH:
        anode.axis = -1
        anode.children[0] = anode.children[1] = None
        return anode

    mathlib.VectorSubtract(maxs, mins, size)

    if size[0] > size[1]:
        anode.axis = 0
    else:
        anode.axis = 1

    anode.dist = 0.5 * (maxs[anode.axis] + mins[anode.axis])

    mathlib.VectorCopy(mins, mins1)
    mathlib.VectorCopy(mins, mins2)
    mathlib.VectorCopy(maxs, maxs1)
    mathlib.VectorCopy(maxs, maxs2)

    maxs1[anode.axis] = mins2[anode.axis] = anode.dist

    anode.children[0] = SV_CreateAreaNode(depth + 1, mins2, maxs2)
    anode.children[1] = SV_CreateAreaNode(depth + 1, mins1, maxs1)

    return anode

def SV_ClearWorld():
    global sv_numareanodes
    SV_InitBoxHull()

    #sv_areanodes.clear()
    sv_numareanodes = 0

    SV_CreateAreaNode(0, sv_main.sv.worldmodel.mins, sv_main.sv.worldmodel.maxs)

def SV_UnlinkEdict(ent: progs.edict_t):
    if ent.area is None or ent.area.prev is None:
        return

    common.RemoveLink(ent.area)
    ent.area.prev = None
    ent.area.next = None


def EDICT_FROM_AREA(link) -> progs.edict_t:
    """C: STRUCT_FROM_LINK(l, edict_t, area). SV_LinkEdict sets link.entity."""
    return link.entity


def SV_AreaTriggerEdicts(ent: quakedef.edict_t, node: quakedef.areanode_t, touch_list: list) -> None:
    """Traverses the area node tree to find all trigger entities overlapping with 'ent'."""
    # Touch linked edicts in current node
    l = node.trigger_edicts.next
    while l is not node.trigger_edicts:
        next_link = l.next
        touch = EDICT_FROM_AREA(l)

        l = next_link

        if touch is ent:
            continue

        # Check if entity has a touch callback and is a trigger solid
        if not touch.v.touch or touch.v.solid != server.SOLID_TRIGGER:
            continue

        # Axis-Aligned Bounding Box (AABB) overlap check
        if (ent.v.absmin[0] > touch.v.absmax[0] or
            ent.v.absmin[1] > touch.v.absmax[1] or
            ent.v.absmin[2] > touch.v.absmax[2] or
            ent.v.absmax[0] < touch.v.absmin[0] or
            ent.v.absmax[1] < touch.v.absmin[1] or
            ent.v.absmax[2] < touch.v.absmin[2]):
            continue

        touch_list.append(touch)

    # Recurse down sub-trees if node is split along an axis
    if node.axis == -1:
        return

    if ent.v.absmax[node.axis] > node.dist:
        SV_AreaTriggerEdicts(ent, node.children[0], touch_list)
    if ent.v.absmin[node.axis] < node.dist:
        SV_AreaTriggerEdicts(ent, node.children[1], touch_list)


def SV_TouchLinks(ent: quakedef.edict_t) -> None:
    """Finds and executes trigger touch functions for all entities overlapping 'ent'."""
    touch_list = []

    # Recursively collect all potential triggers from area nodes
    SV_AreaTriggerEdicts(ent, sv_areanodes[0], touch_list)

    for touch in touch_list:
        # Re-validate in case previous QuakeC execution modified state
        if touch is ent:
            continue

        if not touch.v.touch or touch.v.solid != server.SOLID_TRIGGER:
            continue

        if (ent.v.absmin[0] > touch.v.absmax[0] or
            ent.v.absmin[1] > touch.v.absmax[1] or
            ent.v.absmin[2] > touch.v.absmax[2] or
            ent.v.absmax[0] < touch.v.absmin[0] or
            ent.v.absmax[1] < touch.v.absmin[1] or
            ent.v.absmax[2] < touch.v.absmin[2]):
            continue

        # Write the VM globals directly (ints for entity refs) instead of going
        # through pr_global_struct, which may not write through to pr_globals.
        G = pr_edict.pr_globals
        old_self = G[pr_edict.OFS_SELF]
        old_other = G[pr_edict.OFS_OTHER]

        G[pr_edict.OFS_SELF] = pr_edict.EDICT_TO_PROG(touch)
        G[pr_edict.OFS_OTHER] = pr_edict.EDICT_TO_PROG(ent)
        G[pr_edict.OFS_TIME] = sv_main.sv.time

        pr_exec.PR_ExecuteProgram(int(touch.v.touch))

        G[pr_edict.OFS_SELF] = old_self
        G[pr_edict.OFS_OTHER] = old_other


_leaf_index_cache: dict = {'model': None, 'map': {}}


def _leaf_index(leaf) -> int:
    """Index of a leaf in sv.worldmodel.leafs (C: leaf - worldmodel->leafs).

    mleaf_t has no 'num' attribute, so look the index up by identity. The map
    is built once per loaded world model and reused for every SV_LinkEdict.
    """
    wm = sv_main.sv.worldmodel
    cache = _leaf_index_cache
    if cache['model'] is not wm:
        cache['model'] = wm
        cache['map'] = {id(lf): i for i, lf in enumerate(wm.leafs)}
    idx = cache['map'].get(id(leaf))
    if idx is None:
        host.Host_Error('SV_FindTouchedLeafs: leaf is not part of the world model')
        return 0
    return idx


def SV_FindTouchedLeafs(ent, node):
    """Traverses BSP tree from root node (nodes[0]) to find all leafs touched by entity."""
    # 1. Resolve integer node/leaf index
    if isinstance(node, int):
        if node < 0:
            # ~node converts negative child index to leaf array index
            leaf_idx = ~node
            if 0 <= leaf_idx < len(sv_main.sv.worldmodel.leafs):
                node = sv_main.sv.worldmodel.leafs[leaf_idx]
            else:
                return
        elif node < len(sv_main.sv.worldmodel.nodes):
            node = sv_main.sv.worldmodel.nodes[node]
        else:
            return

    # 2. Direct contents check
    contents = node.contents
    if contents == quakedef.CONTENTS_SOLID:
        return

    # 3. Leaf node reached (contents < 0 in Quake BSP)
    if contents < 0:
        if ent.num_leafs < progs.MAX_ENT_LEAFS:
            # C: leafnum = leaf - sv.worldmodel->leafs - 1
            # leafnums may be shorter than MAX_ENT_LEAFS (e.g. an empty list)
            while len(ent.leafnums) <= ent.num_leafs:
                ent.leafnums.append(0)
            ent.leafnums[ent.num_leafs] = _leaf_index(node) - 1
            ent.num_leafs += 1
        return

    # 4. Interior split node traversal
    plane = node.plane
    if plane.type < 3:
        # Axis-aligned split (0 = X, 1 = Y, 2 = Z)
        dist = ent.v.absmax[plane.type] - plane.dist
        dist2 = ent.v.absmin[plane.type] - plane.dist
    else:
        # Non-axis-aligned split plane
        dist = (ent.v.absmax[0] * plane.normal[0] +
                ent.v.absmax[1] * plane.normal[1] +
                ent.v.absmax[2] * plane.normal[2]) - plane.dist
        dist2 = (ent.v.absmin[0] * plane.normal[0] +
                 ent.v.absmin[1] * plane.normal[1] +
                 ent.v.absmin[2] * plane.normal[2]) - plane.dist

    # Recurse down front/back subtrees
    if dist >= 0:
        SV_FindTouchedLeafs(ent, node.children[0])
    if dist2 < 0:
        SV_FindTouchedLeafs(ent, node.children[1])

def SV_LinkEdict(ent: progs.edict_t, touch_triggers: bool):

    # area is an embedded link_t in C and is never NULL; make sure it exists
    if ent.area is None:
        ent.area = quakedef.link_t()
        ent.area.prev = None
        ent.area.next = None
    ent.area.entity = ent  # lets EDICT_FROM_AREA get back to the edict

    if ent.area.prev is not None:
        SV_UnlinkEdict(ent)

    if ent is sv_main.sv.edicts[0]:  # never link the world
        return

    if ent.free:
        return

    mathlib.VectorAdd(ent.v.origin, ent.v.mins, ent.v.absmin)
    mathlib.VectorAdd(ent.v.origin, ent.v.maxs, ent.v.absmax)

    if int(ent.v.flags) & server.FL_ITEM:
        ent.v.absmin[0] -= 15
        ent.v.absmin[1] -= 15
        ent.v.absmax[0] += 15
        ent.v.absmax[1] += 15
    else:
        ent.v.absmin[0] -= 1
        ent.v.absmin[1] -= 1
        ent.v.absmin[2] -= 1
        ent.v.absmax[0] += 1
        ent.v.absmax[1] += 1
        ent.v.absmax[2] += 1

    ent.num_leafs = 0
    leafnums = getattr(ent, 'leafnums', None)
    if leafnums is None:
        ent.leafnums = [0] * progs.MAX_ENT_LEAFS
    elif len(leafnums) < progs.MAX_ENT_LEAFS:
        leafnums.extend([0] * (progs.MAX_ENT_LEAFS - len(leafnums)))
    if ent.v.modelindex:
        SV_FindTouchedLeafs(ent, sv_main.sv.worldmodel.nodes[0])

    if ent.v.solid == server.SOLID_NOT:
        return

    node = sv_areanodes[0]
    while True:
        if node.axis == -1:
            break
        if ent.v.absmin[node.axis] > node.dist:
            node = node.children[0]
        elif ent.v.absmax[node.axis] < node.dist:
            node = node.children[1]
        else:
            break

    if ent.v.solid == server.SOLID_TRIGGER:
        common.InsertLinkBefore(ent.area, node.trigger_edicts)
    else:
        common.InsertLinkBefore(ent.area, node.solid_edicts)

    if touch_triggers:
        SV_TouchLinks(ent)


def SV_HullPointContents(hull: quakedef.hull_t, num: int, p: quakedef.vec3_t) -> int:
    while num >= 0:
        if num < hull.firstclipnode or num > hull.lastclipnode:
            sys_sdl_unix.Sys_Error('SV_HullPointContents: bad node number')

        node = hull.clipnodes[num]
        plane = hull.planes[node.planenum]

        if plane.type < 3:
            d = p[plane.type] - plane.dist
        else:
            d = mathlib.DoublePrecisionDotProduct(plane.normal, p) - plane.dist

        if d < 0:
            num = node.children[1]
        else:
            num = node.children[0]

    return num


def SV_PointContents(p: quakedef.vec3_t) -> int:

    cont = SV_HullPointContents(sv_main.sv.worldmodel.hulls[0], 0, p)

    if cont <= quakedef.CONTENTS_CURRENT_0 and cont >= quakedef.CONTENTS_CURRENT_DOWN:
        cont = quakedef.CONTENTS_WATER

    return cont

def SV_TruePointContents(p: quakedef.vec3_t) -> int:
    return SV_HullPointContents(sv_main.sv.worldmodel.hulls[0], 0, p)


def SV_TestEntityPosition(ent: progs.edict_t) -> progs.edict_t:

    trace: trace_t = SV_Move(ent.v.origin, ent.v.mins, ent.v.maxs, ent.v.origin, 0, ent)
    if trace.startsolid:
        return sv_main.sv.edicts[0]
    return None


def SV_RecursiveHullCheck(hull: quakedef.hull_t, num, p1f, p2f, p1: quakedef.vec3_t, p2: quakedef.vec3_t, trace: trace_t) -> bool:

    if num < 0:
        if num != quakedef.CONTENTS_SOLID:
            trace.allsolid = False

            if num == quakedef.CONTENTS_EMPTY:
                trace.inopen = True
            else:
                trace.inwater = True

        else:
            trace.startsolid = True

        return True

    if num < hull.firstclipnode or num > hull.lastclipnode:
        sys_sdl_unix.Sys_Error('SV_RecursiveHullCheck: bad node number')

    node = hull.clipnodes[num]
    plane = hull.planes[node.planenum]

    if plane.type < 3:
        t1 = p1[plane.type] - plane.dist
        t2 = p2[plane.type] - plane.dist
    else:
        t1 = mathlib.DoublePrecisionDotProduct(plane.normal, p1) - plane.dist
        t2 = mathlib.DoublePrecisionDotProduct(plane.normal, p2) - plane.dist

    if (t1 >= 0 and t2 >= 0):
        return SV_RecursiveHullCheck (hull, node.children[0], p1f, p2f, p1, p2, trace)
    if (t1 < 0 and t2 < 0):
        return SV_RecursiveHullCheck (hull, node.children[1], p1f, p2f, p1, p2, trace)

    if t1 < 0:
        frac = ( t1 + quakedef.DIST_EPSILON ) / (t1-t2)
    else:
        frac = ( t1 - quakedef.DIST_EPSILON ) / (t1-t2)

    if frac < 0:
        frac = 0

    if frac > 1:
        frac = 1

    midf = p1f + ( p2f - p1f ) * frac
    mid = [0.0, 0.0, 0.0]

    for i in range(3):
        mid[i] = p1[i] + frac*(p2[i] - p1[i])

    side = 1 if t1 < 0 else 0

    if not SV_RecursiveHullCheck (hull, node.children[side], p1f, midf, p1, mid, trace):
        return False

    if SV_HullPointContents(hull, node.children[side^1], mid) != quakedef.CONTENTS_SOLID:
        return SV_RecursiveHullCheck (hull, node.children[side^1], midf, p2f, mid, p2, trace)

    if trace.allsolid:
        return False

    if not side:
        mathlib.VectorCopy(plane.normal, trace.plane.normal)
        trace.plane.dist = plane.dist
    else:
        mathlib.VectorSubtract(mathlib.vec3_origin, plane.normal, trace.plane.normal)
        trace.plane.dist = -plane.dist

    while SV_HullPointContents (hull, hull.firstclipnode, mid) == quakedef.CONTENTS_SOLID:
        frac -= 0.1

        if frac < 0:
            trace.fraction = midf
            mathlib.VectorCopy(mid, trace.endpos)
            console.Con_DPrintf('backup past 0\n')
            return False

        midf = p1f + (p2f - p1f)*frac
        for i in range(3):
            mid[i] = p1[i] + frac*(p2[i] - p1[i])

    trace.fraction = midf
    mathlib.VectorCopy(mid, trace.endpos)

    return False

def SV_ClipMoveToEntity(ent: progs.edict_t, start: quakedef.vec3_t, mins: quakedef.vec3_t, maxs: quakedef.vec3_t, end: quakedef.vec3_t) -> trace_t:

    trace: trace_t = trace_t()
    offset: quakedef.vec3_t = [0, 0, 0]
    start_l: quakedef.vec3_t = [0, 0, 0]
    end_l: quakedef.vec3_t = [0, 0, 0]

    trace.fraction = 1
    trace.allsolid = True
    mathlib.VectorCopy(end, trace.endpos)

    hull = SV_HullForEntity(ent, mins, maxs, offset)

    mathlib.VectorSubtract(start, offset, start_l)
    mathlib.VectorSubtract(end, offset, end_l)

    SV_RecursiveHullCheck(hull, hull.firstclipnode, 0, 1, start_l, end_l, trace)

    if trace.fraction != 1:
        mathlib.VectorAdd(trace.endpos, offset, trace.endpos)

    if trace.fraction < 1 or trace.startsolid:
        trace.ent = ent

    return trace


def SV_ClipToLinks(node: quakedef.areanode_t, clip: moveclip_t) -> None:
    """Traverses area nodes to clip a movement trace against all solid entities."""
    # Process solid entities linked to this area node
    l = node.solid_edicts.next
    while l is not node.solid_edicts:
        next_link = l.next
        touch = EDICT_FROM_AREA(l)
        l = next_link

        if touch.v.solid == server.SOLID_NOT:
            continue
        if touch is clip.passedict:
            continue
        if touch.v.solid == server.SOLID_TRIGGER:
            raise RuntimeError("Trigger in clipping list")

        if clip.type == MOVE_NOMONSTERS and touch.v.solid != server.SOLID_BSP:
            continue

        # Axis-Aligned Bounding Box (AABB) overlap check
        if (clip.boxmins[0] > touch.v.absmax[0] or
            clip.boxmins[1] > touch.v.absmax[1] or
            clip.boxmins[2] > touch.v.absmax[2] or
            clip.boxmaxs[0] < touch.v.absmin[0] or
            clip.boxmaxs[1] < touch.v.absmin[1] or
            clip.boxmaxs[2] < touch.v.absmin[2]):
            continue

        # Points never interact
        if clip.passedict and clip.passedict.v.size[0] and not touch.v.size[0]:
            continue

        # Stop tracing if already trapped inside solid geometry
        if clip.trace.allsolid:
            return

        if clip.passedict:
            # Don't clip against own missiles
            if pr_edict.PROG_TO_EDICT(touch.v.owner) is clip.passedict:
                continue
            # Don't clip against owner
            if pr_edict.PROG_TO_EDICT(clip.passedict.v.owner) is touch:
                continue

        # Monster entities use offset bounding boxes (mins2 / maxs2)
        if int(touch.v.flags) & server.FL_MONSTER:
            trace = SV_ClipMoveToEntity(touch, clip.start, clip.mins2, clip.maxs2, clip.end)
        else:
            trace = SV_ClipMoveToEntity(touch, clip.start, clip.mins, clip.maxs, clip.end)

        # Update trace result if closer hit or newly embedded in solid
        if trace.allsolid or trace.startsolid or trace.fraction < clip.trace.fraction:
            trace.ent = touch
            if clip.trace.startsolid:
                clip.trace = trace
                clip.trace.startsolid = True
            else:
                clip.trace = trace
        elif trace.startsolid:
            clip.trace.startsolid = True

    # Recurse down sub-trees if node is split along an axis
    if node.axis == -1:
        return

    if clip.boxmaxs[node.axis] > node.dist:
        SV_ClipToLinks(node.children[0], clip)
    if clip.boxmins[node.axis] < node.dist:
        SV_ClipToLinks(node.children[1], clip)


def SV_MoveBounds(start: quakedef.vec3_t, mins: quakedef.vec3_t, maxs: quakedef.vec3_t, end:quakedef.vec3_t, boxmins: quakedef.vec3_t, boxmaxs: quakedef.vec3_t):

    for i in range(3):
        if end[i] > start[i]:
            boxmins[i] = start[i] + mins[i] - 1
            boxmaxs[i] = end[i] + maxs[i] + 1
        else:
            boxmins[i] = end[i] + mins[i] - 1
            boxmaxs[i] = start[i] + maxs[i] + 1


def SV_Move (start: quakedef.vec3_t, mins: quakedef.vec3_t, maxs: quakedef.vec3_t, end: quakedef.vec3_t, _type: int, passedict: progs.edict_t) -> trace_t:

    clip: moveclip_t = moveclip_t()

    clip.trace = SV_ClipMoveToEntity(sv_main.sv.edicts[0], start, mins, maxs, end)

    clip.start = start
    clip.end = end
    clip.mins = mins
    clip.maxs = maxs
    clip.type = _type
    clip.passedict = passedict

    if _type == MOVE_MISSILE:
        for i in range(3):
            clip.mins2[i] = -15
            clip.maxs2[i] =  15
    else:
        mathlib.VectorCopy(mins, clip.mins2)
        mathlib.VectorCopy(maxs, clip.maxs2)

    SV_MoveBounds(start, clip.mins2, clip.maxs2, end, clip.boxmins, clip.boxmaxs)

    SV_ClipToLinks(sv_areanodes[0], clip)

    return clip.trace
