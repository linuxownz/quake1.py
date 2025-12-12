#menu.py 

import _cmd

def M_Init():

    _cmd.Cmd_AddCommand('togglemenu', M_ToggleMenu_f)

    _cmd.Cmd_AddCommand('menu_main', M_Menu_Main_f)
    _cmd.Cmd_AddCommand('menu_singleplayer', M_Menu_SinglePlayer_f)
    _cmd.Cmd_AddCommand('menu_load', M_Menu_Load_f)
    _cmd.Cmd_AddCommand('menu_save', M_Menu_Save_f)
    _cmd.Cmd_AddCommand('menu_multiplayer', M_Menu_Multiplayer_f)
    _cmd.Cmd_AddCommand('menu_setup', M_Menu_Setup_f)
    _cmd.Cmd_AddCommand('menu_options', M_Menu_Options_f)
    _cmd.Cmd_AddCommand('menu_keys', M_Menu_Keys_f)
    _cmd.Cmd_AddCommand('menu_video', M_Menu_Video_f)
    _cmd.Cmd_AddCommand('help', M_Menu_Help_f)
    _cmd.Cmd_AddCommand('menu_quit', M_Menu_Quit_f)
    _cmd.Cmd_AddCommand('menu_credits', M_Menu_Credits_f)