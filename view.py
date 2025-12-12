#view.py 

import _cmd
import cvar
import view

v_centermove  = {'name': 'v_centermove',  'value':'0.15', 'flags':cvar.CVAR_NONE}
v_centerspeed = {'name': 'v_centerspeed', 'value':'500',  'flags':cvar.CVAR_NONE}

scr_ofsx = {'name':"scr_ofsx",'value':"0", 'flags':cvar.CVAR_NONE};
scr_ofsy = {'name':"scr_ofsy",'value':"0", 'flags':cvar.CVAR_NONE};
scr_ofsz = {'name':"scr_ofsz",'value':"0", 'flags':cvar.CVAR_NONE};

cl_rollspeed = {'name':"cl_rollspeed", 'value':"200", 'flags':cvar.CVAR_NONE};
cl_rollangle = {'name':"cl_rollangle", 'value':"2.0", 'flags':cvar.CVAR_NONE};

cl_bob      = {'name':"cl_bob",'value':"0.02", 'flags':cvar.CVAR_NONE};
cl_bobcycle = {'name':"cl_bobcycle",'value':"0.6", 'flags':cvar.CVAR_NONE}
cl_bobup    = {'name':"cl_bobup",'value':"0.5", 'flags':cvar.CVAR_NONE};

v_kicktime  = {'name':"v_kicktime", 'value':"0.5", 'flags':cvar.CVAR_NONE};
v_kickroll  = {'name':"v_kickroll", 'value':"0.6", 'flags':cvar.CVAR_NONE};
v_kickpitch = {'name':"v_kickpitch", 'value':"0.6", 'flags':cvar.CVAR_NONE};
v_gunkick   = {'name':"v_gunkick", 'value':"1", 'flags':cvar.CVAR_NONE}; #johnfitz
                                                                                            
v_iyaw_cycle   = {'name':"v_iyaw_cycle", 'value':"2", 'flags':cvar.CVAR_NONE};
v_iroll_cycle  = {'name':"v_iroll_cycle", 'value':"0.5", 'flags':cvar.CVAR_NONE};
v_ipitch_cycle = {'name':"v_ipitch_cycle", 'value':"1", 'flags':cvar.CVAR_NONE};
v_iyaw_level   = {'name':"v_iyaw_level", 'value':"0.3", 'flags':cvar.CVAR_NONE};
v_iroll_level  = {'name':"v_iroll_level", 'value':"0.1", 'flags':cvar.CVAR_NONE};
v_ipitch_level = {'name':"v_ipitch_level", 'value':"0.3", 'flags':cvar.CVAR_NONE};

v_idlescale = {'name':"v_idlescale", 'value':"0", 'flags':cvar.CVAR_NONE};

crosshair = {'name':"crosshair", 'value':"0", 'flags':cvar.CVAR_ARCHIVE};

gl_cshiftpercent          = {'name':"gl_cshiftpercent", 'value':"100", 'flags':cvar.CVAR_NONE};
gl_cshiftpercent_contents = {'name':"gl_cshiftpercent_contents", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm
gl_cshiftpercent_damage   = {'name':"gl_cshiftpercent_damage", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm
gl_cshiftpercent_bonus    = {'name':"gl_cshiftpercent_bonus", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm
gl_cshiftpercent_powerup  = {'name':"gl_cshiftpercent_powerup", 'value':"100", 'flags':cvar.CVAR_NONE}; # QuakeSpasm

r_viewmodel_quake = {'name':"r_viewmodel_quake", 'value':"0", 'flags':cvar.CVAR_ARCHIVE};

v_punchangles = []; #johnfitz -- copied from cl.punchangle.  0 is current, 1 is previous valu

def V_Init():
    global v_centermove
    global v_centerspeed

    global scr_ofsx
    global scr_ofsy
    global scr_ofsz
    global cl_rollspeed
    global cl_rollangle
    global cl_bob     
    global cl_bobcycle
    global cl_bobup   

    global v_kicktime 
    global v_kickroll 
    global v_kickpitch
    global v_gunkick  

    global v_iyaw_cycle  
    global v_iroll_cycle 
    global v_ipitch_cycle
    global v_iyaw_level  
    global v_iroll_level 
    global v_ipitch_level

    global v_idlescale

    global crosshair

    global gl_cshiftpercent         
    global gl_cshiftpercent_contents
    global gl_cshiftpercent_damage  
    global gl_cshiftpercent_bonus   
    global gl_cshiftpercent_powerup 


    _cmd.Cmd_AddCommand('v_cshift', V_cshift_f)
    _cmd.Cmd_AddCommand('bf', V_BonusFlash_f)
    _cmd.Cmd_AddCommand('centerview', V_StartPitchDrift)

    cvar.Cvar_RegisterVariable(v_centermove)
    cvar.Cvar_RegisterVariable(v_centerspeed)

    cvar.Cvar_RegisterVariable(v_iyaw_cycle  )
    cvar.Cvar_RegisterVariable(v_iroll_cycle )
    cvar.Cvar_RegisterVariable(v_ipitch_cycle)
    cvar.Cvar_RegisterVariable(v_iyaw_level  )
    cvar.Cvar_RegisterVariable(v_iroll_level )
    cvar.Cvar_RegisterVariable(v_ipitch_level)

    cvar.Cvar_RegisterVariable(v_idlescale)
    cvar.Cvar_RegisterVariable(crosshair)
    cvar.Cvar_RegisterVariable(gl_cshiftpercent         )
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_contents)
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_damage  )
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_bonus   )
    cvar.Cvar_RegisterVariable(gl_cshiftpercent_powerup )

    cvar.Cvar_RegisterVariable(scr_ofsx)
    cvar.Cvar_RegisterVariable(scr_ofsy)
    cvar.Cvar_RegisterVariable(scr_ofsz)
    cvar.Cvar_RegisterVariable(cl_rollspeed)
    cvar.Cvar_RegisterVariable(cl_rollangle)
    cvar.Cvar_RegisterVariable(cl_bob     )
    cvar.Cvar_RegisterVariable(cl_bobcycle)
    cvar.Cvar_RegisterVariable(cl_bobup   )

    cvar.Cvar_RegisterVariable(v_kicktime )
    cvar.Cvar_RegisterVariable(v_kickroll )
    cvar.Cvar_RegisterVariable(v_kickpitch)
    cvar.Cvar_RegisterVariable(v_gunkick  )

    cvar.Cvar_RegisterVariable(r_viewmodel_quake)

