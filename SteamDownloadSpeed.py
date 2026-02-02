import os
import re
import time
import winreg

RE_APP_DOWNLOADING = re.compile(r'AppID\s+([\w-]+).*Downloading')
RE_DOWNLOAD_RATE = re.compile(r'Current download rate:\s+([\d.]+)')
RE_APP_SUSPENDED = re.compile(r'AppID\s+([\w-]+).*staying in schedule')
RE_APP_NAME = re.compile(r'"name"\s+"([^"]+)"')

END_REGEXES = [
    re.compile(r'AppID\s+([\w-]+).*Fully Installed'),
    re.compile(r'AppID\s+([\w-]+).*Uninstalled'),
    re.compile(r'AppID\s+([\w-]+).*finished update'),
    re.compile(r'AppID\s+([\w-]+).*finished uninstall'),
    re.compile(r'AppID\s+([\w-]+).*removed from schedule')
]

KEY = winreg.HKEY_LOCAL_MACHINE
SUBKEY_PATH = r"SOFTWARE\WOW6432Node\Valve\Steam"
VALUE_NAME = "InstallPath"

games_state = {}  # key = app_id, value = {"name": str, "status": str}

def find_steam(key=KEY, subkey_path=SUBKEY_PATH, value_name=VALUE_NAME):
    try:
        with winreg.ConnectRegistry(None, key) as reg_key:
            with winreg.OpenKey(reg_key, subkey_path, 0, winreg.KEY_READ) as key_handle:       
                steam_path, _ = winreg.QueryValueEx(key_handle, value_name)
                return steam_path
    except OSError as e: 
        print(f"Ошибка доступа к регистру: {e}")
        return None

def steam_log(path):
    print('Скрипт запущен!')

    steam_log_path = os.path.join(path, "logs/content_log.txt")
    last_position = 0
    
    for minute in range(5):
        try:
            with open(steam_log_path, "r", encoding="utf-8", errors="ignore") as file:
                if last_position == 0:
                    file.seek(0)
                else:
                    file.seek(last_position)
                file_lines = file.readlines()
                last_position = file.tell()
            if file_lines:
                speed = read_logs(file_lines)
                if games_state:
                    print(f'Очередь загрузки на {time.strftime('%H:%M:%S')}:')
                    for _, info in games_state.items():
                        name = info["name"]
                        status = info["status"]
                        if speed and status is not "Загрузка приостановлена":
                            print(f"{name} - {status}, скорость {speed} Mbps")
                        else:
                            print(f"{name} - {status}")
                else:
                    print(f'Очередь загрузки пуста на {time.strftime('%H:%M:%S')}!')
            time.sleep(60)
        except OSError as e:
            print(f'Ошибка открытия файла журнала: {e}')
            return
    print('Скрипт завершил работу!')
    
def read_logs(logs):
    app_id = None  
    dspeed = None

    for line in logs:
        for end_re in END_REGEXES:
            match_end = end_re.search(line)
            if match_end:
                if match_end.groups():
                    finished_app = match_end.group(1)
                    games_state.pop(finished_app, None)
                else:
                    if app_id:
                        games_state.pop(app_id, None)
                continue

        match_id = RE_APP_DOWNLOADING.search(line)
        match_dspeed = RE_DOWNLOAD_RATE.search(line)
        match_id_suspended = RE_APP_SUSPENDED.search(line)

        if match_id:
            app_id = match_id.group(1)
            app_name = get_app_name_from_manifest(app_id)
            if not app_name:
                app_name = f"Приложение с id {app_id}"

            if app_id not in games_state:
                games_state[app_id] = {"name": app_name, "status": "Загружается"}
            else:
                games_state[app_id]["status"] = "Загружается"
                games_state[app_id]["name"] = app_name

        if match_id_suspended:
            app_id = match_id_suspended.group(1)
            if app_id in games_state:
                games_state[app_id]["status"] = "Загрузка приостановлена"
            else:
                app_name = get_app_name_from_manifest(app_id)
                if not app_name:
                    app_name = f"приложение с id {app_id}"
                games_state[app_id] = {"name": app_name, "status": "Загрузка приостановлена"}
        
        if match_dspeed and app_id:
            dspeed = match_dspeed.group(1)
    return dspeed
    

def get_app_name_from_manifest(app_id):
    manifest_path = os.path.join(find_steam(), f"steamapps/appmanifest_{app_id}.acf")
    try:
        with open(manifest_path, "r", encoding="utf-8", errors="ignore") as manifest:
            manifest_lines = manifest.readlines()
            for line in manifest_lines:
                match_id = RE_APP_NAME.search(line)
                if match_id:
                    return match_id.group(1) if match_id else None
    except Exception as e:
        #print(f"Ошибка при чтении манифеста: {e}")
        return None


if __name__ == "__main__":
    steam_path = find_steam()
    steam_log(steam_path)