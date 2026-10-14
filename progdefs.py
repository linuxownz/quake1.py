#progdefs.py

from dataclasses import dataclass, field

import traceback

# ==============================================================================
# globalvars_t (Global variables shared between Engine and QuakeC)
# ==============================================================================

PROGHEADER_CRC = 5927

@dataclass(slots=True)
class globalvars_t:
    """Quake 1 globalvars_t interface (progdefs.h)."""

    self: int = 0
    other: int = 0
    world: int = 0
    time: float = 0.0
    frametime: float = 0.0
    force_retouch: float = 0.0
    mapname: int = 0  # QuakeC string table offset
    startspot: int = 0
    deathmatch: float = 0.0
    coop: float = 0.0
    teamplay: float = 0.0
    serverflags: float = 0.0
    total_secrets: float = 0.0
    total_monsters: float = 0.0
    found_secrets: float = 0.0
    killed_monsters: float = 0.0
    parm1: float = 0.0
    parm2: float = 0.0
    parm3: float = 0.0
    parm4: float = 0.0
    parm5: float = 0.0
    parm6: float = 0.0
    parm7: float = 0.0
    parm8: float = 0.0
    parm9: float = 0.0
    parm10: float = 0.0
    parm11: float = 0.0
    parm12: float = 0.0
    parm13: float = 0.0
    parm14: float = 0.0
    parm15: float = 0.0
    parm16: float = 0.0
    v_forward: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    v_up: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    v_right: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    trace_allsolid: float = 0.0
    trace_startsolid: float = 0.0
    trace_fraction: float = 0.0
    trace_endpos: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    trace_plane_normal: list[float] = field(
        default_factory=lambda: [0.0, 0.0, 0.0]
    )
    trace_plane_dist: float = 0.0
    trace_ent: int = 0
    trace_inopen: float = 0.0
    trace_inwater: float = 0.0
    msg_entity: int = 0
    main: int = 0  # QuakeC function indices
    StartFrame: int = 0
    PlayerPreThink: int = 0
    PlayerPostThink: int = 0
    ClientKill: int = 0
    ClientConnect: int = 0
    PutClientInServer: int = 0
    ClientDisconnect: int = 0
    SetNewParms: int = 0
    SetChangeParms: int = 0

    def reset_fields(self) -> None:
        """Resets all globals to zero/default state."""
        self.__init__()


# ==============================================================================
# entvars_t (Entity variables for every edict)
# ==============================================================================


@dataclass(slots=True)
class entvars_t:
    """Quake 1 entvars_t interface (progdefs.h)."""

    modelindex: float = 0.0
    absmin: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    absmax: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    ltime: float = 0.0
    movetype: float = 0.0
    solid: float = 0.0
    origin: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    oldorigin: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    angles: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    avelocity: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    punchangle: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    #_classname: int = 0
    classname: int = 0
    model: int = 0
    frame: float = 0.0
    skin: float = 0.0
    effects: float = 0.0
    mins: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    maxs: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    size: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    touch: int = 0
    use: int = 0
    think: int = 0
    blocked: int = 0
    nextthink: float = 0.0
    groundentity: int = 0
    health: float = 0.0
    frags: float = 0.0
    weapon: float = 0.0
    weaponmodel: int = 0
    weaponframe: float = 0.0
    currentammo: float = 0.0
    ammo_shells: float = 0.0
    ammo_nails: float = 0.0
    ammo_rockets: float = 0.0
    ammo_cells: float = 0.0
    items: float = 0.0
    takedamage: float = 0.0
    chain: int = 0
    deadflag: float = 0.0
    view_ofs: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    button0: float = 0.0
    button1: float = 0.0
    button2: float = 0.0
    impulse: float = 0.0
    fixangle: float = 0.0
    v_angle: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    idealpitch: float = 0.0
    netname: int = 0
    enemy: int = 0
    flags: float = 0.0
    colormap: float = 0.0
    team: float = 0.0
    max_health: float = 0.0
    teleport_time: float = 0.0
    armortype: float = 0.0
    armorvalue: float = 0.0
    waterlevel: float = 0.0
    watertype: float = 0.0
    ideal_yaw: float = 0.0
    yaw_speed: float = 0.0
    aiment: int = 0
    goalentity: int = 0
    spawnflags: float = 0.0
    target: int = 0
    targetname: int = 0
    dmg_take: float = 0.0
    dmg_save: float = 0.0
    dmg_inflictor: int = 0
    owner: int = 0
    movedir: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    message: int = 0
    sounds: float = 0.0
    noise: int = 0
    noise1: int = 0
    noise2: int = 0
    noise3: int = 0

#   @property
#   def classname(self) -> float:
#       return self._classname

#   @classname.setter
#   def classname(self, value):
#       val_int = int(value) if isinstance(value, (int, float)) else None
#       if val_int is not None and (val_int == -1 or val_int == 0xFFFFFFFF):
#           print("\n" + "=" * 60)
#           print(f"[EVAL WATCHDOG] Caught attempt to set classname to {value}!")
#           traceback.print_stack()
#           print("=" * 60 + "\n")
#           print('\n\n\n\n\n\n')
#           breakpoint()

#       self._classname = value


    def reset_fields(self) -> None:
        """memset(&ent->v, 0, sizeof(entvars_t)) parity."""
        self.__init__()