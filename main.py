import os
import subprocess
import re
import sys
import time
import requests
import ctypes
import platform
import ctypes.wintypes
import errno

# Constants
API_VERSION = "2"
API_USER_AGENT = "SGDBoop/v1.2.3"
OS_Windows = platform.system() == 'Windows'

# Define constants based on crc.h
WIDTH = 32
TOPBIT = 1 << (WIDTH - 1)
INITIAL_REMAINDER = 0xFFFFFFFF
FINAL_XOR_VALUE = 0xFFFFFFFF
POLYNOMIAL = 0x04C11DB7
REFLECT_DATA = True
REFLECT_REMAINDER = True

# Populate the CRC lookup table
crcTable = [0] * 256


def crc_init():
    global crcTable
    for dividend in range(256):
        remainder = (dividend << (WIDTH - 8)) & 0xFFFFFFFF
        for bit in range(8, 0, -1):
            if remainder & TOPBIT:
                remainder = (remainder << 1) ^ POLYNOMIAL
            else:
                remainder = (remainder << 1)
        crcTable[dividend] = remainder


def reflect(data, nBits):
    reflection = 0
    for bit in range(nBits):
        if data & 0x01:
            reflection |= (1 << (nBits - 1 - bit))
        data >>= 1
    return reflection


def crc_slow(message, nBytes):
    remainder = INITIAL_REMAINDER
    for byte in message[:nBytes]:
        remainder ^= (reflect(byte, 8) << (WIDTH - 8))
        for bit in range(8, 0, -1):
            if remainder & TOPBIT:
                remainder = (remainder << 1) ^ POLYNOMIAL
            else:
                remainder = (remainder << 1)
    return (reflect(remainder, WIDTH) ^ FINAL_XOR_VALUE)


def crc_fast(message, nBytes):
    remainder = INITIAL_REMAINDER
    for byte in message[:nBytes]:
        data = reflect(byte, 8) ^ (remainder >> (WIDTH - 8))
        remainder = crcTable[data] ^ (remainder << 8)
    return (reflect(remainder, WIDTH) ^ FINAL_XOR_VALUE)


# Function to create a symbolic link on Windows
def symlink(a, b):
    if OS_Windows:
        try:
            ctypes.windll.kernel32.CreateHardLinkW(b, a, 0)
            return 0
        except OSError as e:
            return e.errno
    else:
        # Implement symbolic link creation for non-Windows systems here
        return -1


# Function to call the BOOP API
def call_api(grid_types, grid_ids, mode):
    auth_header = "Bearer 62696720-6f69-6c79-2070-65656e75733f"
    api_version_header = f"X-BOOP-API-VER"
    url = f"https://www.steamgriddb.com/api/sgdboop/{grid_types}/{grid_ids}"

    if mode == "nonsteam":
        url += "?nonsteam=1"

    headers = {
        "User-Agent": API_USER_AGENT,
        "Authorization": auth_header,
        api_version_header: API_VERSION
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.text.splitlines()
        values_array = []

        for line in data:
            values = line.split(',')
            values_array.append(values)

        return values_array
    except requests.exceptions.RequestException as e:
        log_error(f"API Error: {e}", e.response.status_code if hasattr(e, 'response') else -1)
        return None


# Function to log error messages
def log_error(error, error_code):
    now = time.time()
    time_info = time.localtime(now)
    log_filepath = get_log_filepath()

    with open(log_filepath, "a") as log_file:
        log_file.write(f"{time.asctime(time_info)} {error} [{error_code}]\n\n")

    print(f"Created logfile in {log_filepath}")


# Function to exit with an error message and code
def exit_with_error(error, error_code):
    log_error(error, error_code)
    sys.exit(error_code)


# Function to get the log file path
def get_log_filepath():
    if OS_Windows:
        path = os.path.abspath(sys.executable)
        filename = os.path.basename(path)
        filename = filename.split('.')[0] + "_error.log"
        return os.path.join(os.path.dirname(path), filename)
    else:
        xdg_state_home = os.environ.get("XDG_STATE_HOME")
        if xdg_state_home and len(xdg_state_home) > 0:
            state_home = xdg_state_home
        else:
            state_home = os.environ.get("HOME", "~") + "/.local/state"

        # Try creating folder
        try:
            os.makedirs(state_home, exist_ok=True)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        return os.path.join(state_home, "sgdboop_error.log")


# Add an icon to the application (not implemented in this code)

# Global variables
non_steam_apps_count = 0
source_mods_count = 0
gold_source_mods_count = 0
api_returned_lines = 0


# Function to download an asset file
def download_asset_file(app_id, url, asset_type, orientation, destination_dir, non_steam_app_data=None):
    # Try creating folder
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    outfilename = os.path.join(destination_dir, app_id)
    if asset_type == "hero":
        outfilename += "_hero.jpg"
    elif asset_type == "logo":
        outfilename += "_logo.jpg"
    elif asset_type == "grid" and orientation == "p":
        outfilename += "p.jpg"
    elif asset_type == "grid":
        outfilename += ".jpg"
    elif asset_type == "icon":
        if non_steam_app_data is None:
            outfilename += "_icon.jpg"
        else:
            # Add new icon to grid folder using its original extension
            extension = os.path.splitext(url)[1]
            outfilename += f"_icon{extension}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        with open(outfilename, "wb") as fp:
            fp.write(response.content)

        return outfilename
    except requests.exceptions.RequestException as e:
        os.remove(outfilename)
        return None


# Function to create the SGDB URI protocol
def create_uri_protocol():
    log_filepath = get_log_filepath()
    popup_message = ""

    if OS_Windows:
        cwd = os.path.abspath(sys.executable)

        ret_val_reg = subprocess.call(
            ["C:\\Windows\\System32\\reg.exe", "ADD", "HKCR\\sgdb", "/t", "REG_SZ", "/d", "URL:sgdb protocol", "/f"]
        )

        if ret_val_reg != 0:
            ret_val_exists = subprocess.call(
                ["C:\\Windows\\System32\\reg.exe", "query", "HKCR\\sgdb\\Shell\\Open\\Command", "/ve"]
            )

            if ret_val_exists != 0:
                popup_message = "Please run this program as Administrator to register it!\n"
            else:
                popup_message = (
                    "SGDBoop is already registered!\n"
                    "Head over to https://www.steamgriddb.com/boop to continue setup.\n\n"
                    "If you moved the program and want to register again, run SGDBoop as Administrator.\n"
                )
                print(popup_message)
            return 1

        subprocess.call(
            ["C:\\Windows\\System32\\reg.exe", "ADD", "HKCR\\sgdb\\Shell\\Open\\Command",
             "/t", "REG_SZ", "/d", f"\"{cwd}\" \"{os.path.abspath(__file__)}\" \"%1\" -new_console:z", "/f"])
        subprocess.call(
            ["C:\\Windows\\System32\\reg.exe", "ADD", "HKCR\\sgdb\\DefaultIcon", "/t", "REG_SZ", "/d", cwd, "/f"]
        )

        subprocess.call(
            ["C:\\Windows\\System32\\reg.exe", "ADD", "HKCR\\sgdb", "/v", "URL Protocol", "/t", "REG_SZ", "/d", "",
             "/f"]
        )

        popup_message = (
            "Program registered successfully!\n\n"
            "SGDBoop is meant to be run from a browser!\n"
            "Head over to https://www.steamgriddb.com/boop to continue setup."
        )
    else:
        # Do nothing on Linux
        popup_message = "SGDBoop is meant to be run from a browser!\n" "Head over to https://www.steamgriddb.com/boop to continue setup."

    popup_message += f"\n\nLog file path: {log_filepath}"
    print("SGDBoop Information:", popup_message)
    return 0


# Function to delete the SGDB URI protocol
def delete_uri_protocol():
    if OS_Windows:
        ret_val = subprocess.call(["C:\\Windows\\System32\\reg.exe", "DELETE", "HKCR\\sgdb", "/f"])
        if ret_val != 0:
            print("Please run this program as Administrator!")
            return 1

        print("Program unregistered successfully!")
        return 0
    else:
        # Do nothing on Linux
        print("A SGDB URL argument is required.")
        print("Example: SGDBoop sgdb://boop/[ASSET_TYPE]/[ASSET_ID]")
        return 1


# Function to get Steam's base directory
def get_steam_base_dir():
    steam_base_dir = None
    found_value = 0

    if OS_Windows:
        try:
            result = subprocess.check_output(
                ["C:\\Windows\\System32\\reg.exe", "query", "HKCU\\Software\\Valve\\Steam", "/v", "SteamPath"],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            lines = result.splitlines()
            for line in lines:
                if "SteamPath" in line:
                    extracted_value = line.split("REG_SZ")[1].strip()
                    steam_base_dir = extracted_value
                    found_value = 1
                    break
        except subprocess.CalledProcessError as e:
            pass

        if not found_value:
            return None

        steam_base_dir = steam_base_dir.replace("\n", "").replace("\r", "")
    else:
        found_value = 1
        steam_base_dir = os.environ.get("HOME", "")
        steam_flatpak_dir = os.path.join(steam_base_dir, ".var/app/com.valvesoftware.Steam/data/Steam")

        # If flatpaked Steam is installed
        if os.path.exists(steam_flatpak_dir):
            steam_base_dir = steam_flatpak_dir
        else:
            # Steam installed on host
            steam_base_dir = os.path.join(steam_base_dir, ".steam/steam")

    if not found_value:
        return None

    return steam_base_dir


# Function to find the most recently logged-in user
def get_most_recent_user(steam_base_dir):
    steamid = ""
    steam_config_file = os.path.join(steam_base_dir, "config", "loginusers.vdf")

    try:
        with open(steam_config_file, "r") as fp:
            lines = fp.readlines()
            for line in lines:
                if re.search(r"7656119", line) and not re.search(r"PersonaName", line):
                    steamid = re.search(r"7656119[0-9]+", line).group(0)
                elif (re.search(r"mostrecent", line) or re.search(r"MostRecent", line)) and re.search(r"\"1\"", line):
                    steamid_long_long = int(steamid) - 76561197960265728
                    steamid = str(steamid_long_long)
                    break
    except FileNotFoundError:
        exit_with_error("Couldn't find logged in user", 95)

    return steamid


# Function to get Steam's destination directory based on artwork type
def get_steam_destination_dir(steam_base_dir, asset_type, non_steam_app_data):
    if not steam_base_dir:
        return None

    if asset_type == "icon" and non_steam_app_data is None:
        # If it's a Steam app icon
        steam_base_dir = os.path.join(steam_base_dir, "appcache", "librarycache")
    else:
        # If it's not a Steam app icon, read the loginusers.vdf to find the most recent user
        steamid = get_most_recent_user(steam_base_dir)
        steam_base_dir = os.path.join(steam_base_dir, "userdata", steamid, "config", "grid")

    return steam_base_dir


# Function to get source mods appids
def get_source_mods(asset_type):
    goldsource = asset_type == "goldsource"

    # Get source mod install path
    found_value = False
    source_mod_path = ""
    reg_value = "ModInstallPath" if goldsource else "SourceModInstallPath"

    if OS_Windows:
        # Windows: Query registry
        regedit_command = f"C:\\Windows\\System32\\reg.exe query HKCU\\Software\\Valve\\Steam /v {reg_value}"

        try:
            result = subprocess.check_output(
                regedit_command,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            lines = result.splitlines()
            for line in lines:
                if reg_value in line:
                    extracted_value = re.search(r"REG_SZ\s+(.+)", line)
                    if extracted_value:
                        source_mod_path = extracted_value.group(1)
                        found_value = True
                        break
        except subprocess.CalledProcessError:
            pass

        source_mod_path = source_mod_path.replace("\n", "").replace("\r", "")
    else:
        # Linux: Read registry.vdf
        reg_value_temp = f'"{reg_value}"'
        reg_file_location = get_steam_base_dir()
        reg_file_location = reg_file_location.replace("/.steam/steam", "/.steam/registry.vdf")

        try:
            with open(reg_file_location, "r") as fp_reg:
                lines = fp_reg.readlines()
                for line in lines:
                    if reg_value_temp in line:
                        extracted_value = re.search(r"\"(.+)\"", line)
                        if extracted_value:
                            source_mod_path = extracted_value.group(1)
                            source_mod_path = source_mod_path.replace("\\\\", "/")
                            found_value = True
                            break
        except FileNotFoundError:
            log_error(f"File registry.vdf could not be found in {reg_file_location}", 96)
            return None

    if not found_value:
        log_error(f"Could not find {reg_value} (either in regedit or registry.vdf)", 97)
        return None

    source_mods = []
    mods_count = 0

    for dir_entry in os.listdir(source_mod_path):
        dir_path = os.path.join(source_mod_path, dir_entry)
        game_info_path = ""

        if goldsource:
            # Goldsource mods
            game_info_path = os.path.join(dir_path, "liblist.gam")
        else:
            # Source mods
            game_info_path = os.path.join(dir_path, "gameinfo.txt")

        if not os.path.exists(game_info_path):
            continue

        try:
            with open(game_info_path, "r") as fp:
                lines = fp.readlines()
                mod_name = ""
                steam_app_id = None
                found_game_key = False

                for line in lines:
                    comment_char = re.search(r"//", line)
                    name_start_char = re.search(r"game", line)
                    steam_app_id_start_char = re.search(r"SteamAppId", line)

                    if name_start_char and not comment_char and not found_game_key:
                        name_start_char = re.search(r"\"(.+)\"", line)
                        if name_start_char:
                            mod_name = name_start_char.group(1)
                            found_game_key = True

                    if steam_app_id_start_char and found_game_key:
                        steam_app_id_start_char = re.search(r"SteamAppId\s+(\d+)", line)
                        if steam_app_id_start_char:
                            steam_app_id = int(steam_app_id_start_char.group(1))
                            break

                if mod_name and steam_app_id is not None:
                    source_mods.append({
                        "name": mod_name,
                        "steam_app_id": steam_app_id
                    })
                    mods_count += 1
        except FileNotFoundError:
            continue

    if goldsource:
        _goldSourceModsCount = mods_count
    else:
        _sourceModsCount = mods_count

    return source_mods


# Function to parse shortcuts file and return a list of app data structs
def get_non_steam_apps(include_mods):
    shortcuts_vdf_path = get_steam_base_dir()
    steamid = get_most_recent_user(shortcuts_vdf_path)
    apps = []
    crc_init()

    # Get the shortcuts.vdf file
    shortcuts_vdf_path = os.path.join(shortcuts_vdf_path, "userdata", steamid, "config", "shortcuts.vdf")

    # Parse the file
    try:
        with open(shortcuts_vdf_path, "rb") as fp:
            file_content = fp.read()
            real_file_content = file_content
            current_file_byte = 0

            # Load the vdf in memory and fix string-related issues
            while current_file_byte < len(file_content):
                if file_content[current_file_byte] == 0x00:
                    real_file_content = real_file_content[:current_file_byte] + b'\x03' + real_file_content[
                                                                                          current_file_byte + 1:]
                current_file_byte += 1

            real_file_content += b'\x08\x03'

            parsing_char = file_content
            parsing_appid = bytearray()
            int_bytes = [0, 0, 0, 0]

            # Parse the vdf content
            while b"\x01AppName" in parsing_char:
                appid_old = 0
                appid = 0

                # Find app name
                name_start_char = re.search(b"\x01AppName(.+)\x03", parsing_char).group(1)
                name_end_char = name_start_char.find(b"\x03")

                # Find exe path
                exe_start_char = re.search(b"\001exe(.+)\x03", parsing_char).group(1)
                exe_end_char = exe_start_char.find(b"\x03")

                appid_ptr = re.search(b"\x02appid", parsing_char)
                app_block_end_ptr = parsing_char.find(b"\x08", appid_ptr) + 1

                # If appid was found in this app block
                if appid_ptr > 0 and appid_ptr < app_block_end_ptr:
                    hex_bytes = real_file_content[appid_ptr + 7:appid_ptr + 11]
                    int_bytes[0] = hex_bytes[3]
                    int_bytes[1] = hex_bytes[2]
                    int_bytes[2] = hex_bytes[1]
                    int_bytes[3] = hex_bytes[0]

                    appid = ((int_bytes[0] << 24) |
                             (int_bytes[1] << 16) |
                             (int_bytes[2] << 8) |
                             (int_bytes[3]))

                # Calculate old app id
                name_end_char = name_end_char.decode("utf-8")
                exe_end_char = exe_end_char.decode("utf-8")

                parsing_appid.extend(exe_start_char)
                parsing_appid.extend(name_start_char)
                appid_old = crc_fast(parsing_appid.decode("utf-8"))

                if appid == 0:
                    appid = appid_old

                # Do math magic. Valve pls fix
                appid = ((appid | 0x80000000) << 32 | 0x02000000) >> 32
                appid_old = ((appid_old | 0x80000000) << 32 | 0x02000000)

                apps.append({
                    "index": len(apps),
                    "name": name_start_char.decode("utf-8"),
                    "appid": str(appid),
                    "type": "nonsteam-app",
                    "appid_old": str(appid_old)
                })

                # Move parser to end of app data
                parsing_char = file_content[app_block_end_ptr + 2:]

    except FileNotFoundError:
        exit_with_error("Couldn't find shortcuts.vdf file", 95)

    # Add source (and goldsource) mods if requested
    if include_mods:
        source_mods = get_source_mods("source")
        gold_source_mods = get_source_mods("goldsource")

        for mod in source_mods:
            apps.append({
                "index": len(apps),
                "name": mod["name"],
                "appid": mod["appid"],
                "type": "source-mod",
                "appid_old": mod["appid_old"]
            })

        for mod in gold_source_mods:
            apps.append({
                "index": len(apps),
                "name": mod["name"],
                "appid": mod["appid"],
                "type": "goldsource-mod",
                "appid_old": mod["appid_old"]
            })

    # Exit with an error if no non-Steam apps were found
    if len(apps) < 1:
        exit_with_error("Could not find any non-Steam apps", 91)

    return apps


# Function to select a non-Steam app from a dropdown list and return its ID
def select_non_steam_app(sgdb_name, apps):
    app_data = None

    title = f"SGDBoop: Pick a game for '{sgdb_name}'"

    values = [app["name"] for app in apps]
    values.sort()

    try:
        selection = values.index(sgdb_name) + 1
    except ValueError:
        selection = 1

    # retval = IupListDialog(1, title, len(values), values, selection, len(title) - 12, 14, None)
    retval = len(values)
    # Exit when the user clicks cancel
    if retval < 0:
        exit(0)

    # Find the matching app
    for app in apps:
        if app["name"] == values[retval - 1]:
            app_data = app
            break

    return app_data


# Function to create a symlink for a file that has the old nonsteam appid format
def create_old_id_symlink(app_data, steam_dest_dir):
    link_path = os.path.join(steam_dest_dir, app_data["appid_old"] + ".jpg")
    target_path = os.path.join(steam_dest_dir, app_data["appid"] + ".jpg")

    try:
        os.symlink(target_path, link_path)
        return 0
    except OSError as e:
        error_message = f"Could not create symlink for file: {link_path}. If you're having issues, try deleting this file and apply the asset again."
        log_error(error_message, 99)
        return 1


# Function to update shortcuts.vdf with the new icon value
def update_vdf(app_data, file_path):
    shortcuts_vdf_path = get_steam_base_dir()
    steamid = get_most_recent_user(shortcuts_vdf_path)

    shortcuts_vdf_path = os.path.join(shortcuts_vdf_path, "userdata", steamid, "config", "shortcuts.vdf")

    try:
        with open(shortcuts_vdf_path, "rb") as fp:
            file_content = fp.read()
            real_file_content = file_content

            # Load the vdf in memory and fix string-related issues
            file_content = file_content.replace(b"\x00", b"\x03")
            file_content += b'\x08\x03'

            app_block_start = file_content
            app_block_end_ptr = file_content
            icon_start_char = None
            icon_end_char = None
            icon_content = bytearray(b"\x01icon\x03" + file_path.encode() + b"\x03")

            # Find the app's block
            for _ in range(app_data["index"] + 1):
                app_block_start = app_block_end_ptr
                app_block_end_ptr = app_block_start.find(b"\x08", app_block_start) + 1
                while app_block_end_ptr < len(file_content) and (
                        file_content[app_block_end_ptr] != 0x03 and file_content[app_block_end_ptr] != 0x00):
                    app_block_end_ptr = app_block_start.find(b"\x08", app_block_end_ptr) + 1

            if app_block_start:
                # Find icon key
                icon_start_char = app_block_start.find(b"\x01icon")
                icon_end_char = app_block_start.find(b"\x03", icon_start_char) + 1
                icon_end_char = app_block_start.find(b"\x03", icon_end_char)

                exe_start_char = app_block_start.find(b"\x01exe") + 5
                exe_end_char = app_block_start.find(b"\x03", exe_start_char)

                if icon_start_char == -1 or icon_start_char > app_block_end_ptr:
                    # Didn't find icon block
                    icon_start_char = exe_end_char + 1
                    icon_end_char = icon_start_char

                icon_start_char = icon_start_char if icon_start_char != -1 else 0

                # Set the new file contents
                new_file_content = real_file_content[:icon_start_char] + icon_content + real_file_content[
                                                                                        icon_end_char + 1:]

                # Write the file back
                with open(shortcuts_vdf_path, "wb") as fp_w:
                    for i in range(len(new_file_content) - 2):
                        # Revert 0x03 to 0x00
                        if new_file_content[i] == 0x03:
                            new_file_content[i] = 0x00
                        # Write byte to file
                        fp_w.write(new_file_content[i].to_bytes(1, byteorder='big'))

    except FileNotFoundError:
        exit_with_error("Shortcuts vdf could not be found.", 93)
    except Exception as e:
        exit_with_error("Could not write to shortcuts vdf file.", 94)


# Main function
def main(argc, argv):
    if argc == 0 or (argc == 1 and not argv[0].startswith("sgdb://")):
        # # Enable IUP GUI
        # IupOpen(argc, argv)
        # load_iup_icon()

        # Create the sgdb URI protocol
        if create_uri_protocol() == 1:
            exit_with_error("Could not create URI protocol.", 80)
    else:
        # If argument is unregister, unregister and exit
        if argv[1] == "unregister":
            if delete_uri_protocol() == 1:
                exit_with_error("Could not unregister the URI protocol.", 85)
            return 0

        # If sgdb:// arguments were passed, run the program normally

        # If the arguments aren't of the SGDB URI, return with an error
        if not argv[1].startswith("sgdb://boop"):
            exit_with_error("Invalid URI schema.", 81)

        # Test mode
        if argv[1] == "sgdb://boop/test":

            # Enable IUP GUI and show a message
            # IupOpen(argc, argv)
            # load_iup_icon()
            # IupMessage("SGDBoop Test", "^_^/   SGDBoop is working!   \\^_^")
            return 0

        # Get the params from the string
        uri_components = argv[1].removeprefix("sgdb://boop/").split('/')
        types = uri_components[0]
        grid_ids = uri_components[1]
        mode = uri_components[2] if len(uri_components) > 2 else "default"

        # Get asset URL
        api_values = call_api(types, grid_ids, mode)
        if api_values is None:
            exit_with_error("API didn't return an appropriate response.", 82)

        non_steam_app_data = None

        for api_value in api_values:
            app_id = api_value[0]
            orientation = api_value[1]
            asset_url = api_value[2]
            asset_type = api_value[3]

            # If the game is a non-steam app, select an imported app
            if app_id.startswith("nonsteam-"):
                if non_steam_app_data is None:
                    # # Enable IUP GUI
                    # IupOpen(argc, argv)
                    # load_iup_icon()

                    # Do not include mods in the dropdown list if the only asset selected was an icon
                    include_mods = 1
                    if types == "icon" or (types == "steam" and asset_type == "icon"):
                        include_mods = 0

                    # Get non-steam apps
                    apps = get_non_steam_apps(include_mods)

                    # Show selection screen and return the struct
                    non_steam_app_data = select_non_steam_app(app_id.split("-")[1], apps)

                # Skip icons for source/goldsource mods
                if asset_type == "icon" and (
                        non_steam_app_data["type"] == "source-mod" or non_steam_app_data["type"] == "goldsource-mod"):
                    continue

                app_id = non_steam_app_data["appid"]

            # Get Steam base dir
            steam_dest_dir = get_steam_destination_dir(asset_type, non_steam_app_data)
            if steam_dest_dir is None:
                exit_with_error("Could not locate Steam destination directory.", 83)

            # Download asset file
            outfilename = download_asset_file(app_id, asset_url, asset_type, orientation, steam_dest_dir,
                                              non_steam_app_data)
            if outfilename is None:
                exit_with_error("Could not download asset file.", 84)

            # Non-Steam specific actions
            if non_steam_app_data:
                # If the asset is a non-Steam horizontal grid, create a symlink (for back. compat.)
                if asset_type == "grid" and orientation == "l":
                    if not create_old_id_symlink(non_steam_app_data, steam_dest_dir):
                        error_message = f"Could not create symlink for file: {os.path.join(steam_dest_dir, non_steam_app_data['appid_old'] + '.jpg')}. If you're having issues, try deleting this file and apply the asset again."
                        log_error(error_message, 99)
                # If the asset is a non-Steam icon, add the icon to shortcuts.vdf
                elif asset_type == "icon":
                    update_vdf(non_steam_app_data, outfilename)


if __name__ == "__main__":
    argc = len(sys.argv)
    argv = sys.argv
    main(argc, argv)
