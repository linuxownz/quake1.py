#in_sdl.py 

from enum import Enum
from enum import Flag, auto

import sdl2
import sdl2.ext

import cvar
import keys
import common

windowhasfocus = True
textmode = False

in_debugkeys = {'name':'in_debugkeys', 'value':'0', 'flags':cvar.CVAR_NONE}

joy_deadzone_look =        { 'name':"joy_deadzone_look",        'value':"0.175", 'flags':CVAR_ARCHIVE };
joy_deadzone_move =        { 'name':"joy_deadzone_move",        'value':"0.175", 'flags':CVAR_ARCHIVE };
joy_outer_threshold_look = { 'name':"joy_outer_threshold_look", 'value':"0.02",  'flags':CVAR_ARCHIVE };
joy_outer_threshold_move = { 'name':"joy_outer_threshold_move", 'value':"0.02",  'flags':CVAR_ARCHIVE };
joy_deadzone_trigger =     { 'name':"joy_deadzone_trigger",     'value':"0.2",   'flags':CVAR_ARCHIVE };
joy_sensitivity_yaw =      { 'name':"joy_sensitivity_yaw",      'value':"240",   'flags':CVAR_ARCHIVE };
joy_sensitivity_pitch =    { 'name':"joy_sensitivity_pitch",    'value':"130",   'flags':CVAR_ARCHIVE };
joy_invert =               { 'name':"joy_invert",               'value': "0",    'flags':CVAR_ARCHIVE };
joy_exponent =             { 'name':"joy_exponent",             'value': "2",    'flags':CVAR_ARCHIVE };
joy_exponent_move =        { 'name':"joy_exponent_move",        'value': "2",    'flags':CVAR_ARCHIVE };
joy_swapmovelook =         { 'name':"joy_swapmovelook",         'value': "0",    'flags':CVAR_ARCHIVE };
joy_enable =               { 'name':"joy_enable",               'value': "1",    'flags':CVAR_ARCHIVE };

joy_active_instanceid: SDL_JoystickID  = -1
joy_active_controller: SDL_GameController = None

no_mouse = False

buttonremap = [
    keys.K_MOUSE1,
    keys.K_MOUSE3,
    keys.K_MOUSE2,
    keys.K_MOUSE4,
    keys.K_MOUSE5
]

total_dx = 0
total_dy = 0

def IN_FilterMouseEvents(event:sdl2.SDL_Event):
    match sdl2.event.type:
        case  sdl2.SDL_MOUSEMOTION:
            return 0
    
    return 1

def IN_SDL2_FilterMouseEvents(userdata, event: sdl2.SDL_Event):
    return IN_FilterMouseEvents(event)


def IN_Init():
    global textmode
    global no_mouse

    textmode = keys.Key_TextEntry()

    if textmode:
        sdl2.SDL_StartTextInput()
    else:
        sdl2.SDL_StopTextInput()

    if common.safemode or COM_CheckParm('-nomouse'):
        no_mouse = True
        IN_BeginIgnoringMouseEvents()

    cvar.Cvar_RegisterVariable(in_debugkeys);             
    cvar.Cvar_RegisterVariable(joy_sensitivity_yaw);
    cvar.Cvar_RegisterVariable(joy_sensitivity_pitch);
    cvar.Cvar_RegisterVariable(joy_deadzone_look);
    cvar.Cvar_RegisterVariable(joy_deadzone_move);
    cvar.Cvar_RegisterVariable(joy_outer_threshold_look);
    cvar.Cvar_RegisterVariable(joy_outer_threshold_move);
    cvar.Cvar_RegisterVariable(joy_deadzone_trigger);
    cvar.Cvar_RegisterVariable(joy_invert);
    cvar.Cvar_RegisterVariable(joy_exponent);
    cvar.Cvar_RegisterVariable(joy_exponent_move); 
    cvar.Cvar_RegisterVariable(joy_swapmovelook);
    cvar.Cvar_RegisterVariable(joy_enable);

    IN_Activate()
    IN_StartupJoystick()
