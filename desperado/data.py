APPLICATION_DATA = (
        (730, 'Counter-Strike: Global Offensive', 'csgo'),
        (620, 'Portal 2', 'portal2'),
        (723, 'Steam', 'steam'),
        (570, 'Dota 2', 'dota2'),
        (440, 'Team Fortress 2', 'tf2')
)

APP_IDS = []
APP_NAMES = {}
APP_SHORT_NAMES = {}
APP_SHORT_NAME_TO_ID = {}

def __init_module():
    for app_id, app_long_name, app_short_name in APPLICATION_DATA:
        APP_IDS.append(app_id)
        APP_NAMES[app_id] = app_long_name
        APP_SHORT_NAMES[app_id] = app_short_name
        APP_SHORT_NAME_TO_ID[app_short_name] = app_id

UNKNOWN_APP_NAME       = 'Unknown Application Name'
UNKNOWN_SHORT_APP_NAME = 'unknown_app'

def __get_name(app_id, name_dict, default_value):
    try:
        app_id = int(app_id)
    except ValueError:
        return 'INVALID_APP_ID'

    if app_id in name_dict:
        return name_dict[app_id]
    return default_value

def app_id(short_name):
    return APP_SHORT_NAME_TO_ID[short_name]

def application_name(app_id):
    return __get_name(app_id, APP_NAMES, UNKNOWN_APP_NAME)

def application_short_name(app_id):
    return __get_name(app_id, APP_SHORT_NAMES, UNKNOWN_SHORT_APP_NAME)

__init_module()
