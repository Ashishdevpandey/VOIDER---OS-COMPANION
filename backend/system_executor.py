"""
System Executor for VOIDER - OS Companion
Provides advanced system control, GUI automation, and window/workspace dispatching for Hyprland (Wayland)
"""

import subprocess
import os
import time
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SystemExecutor:
    """Wayland and system-level capability executor for Voider OS"""

    def __init__(self):
        pass

    def wait(self, seconds: float) -> str:
        """Waits for a specified number of seconds."""
        try:
            time.sleep(float(seconds))
            return f"Waited for {seconds} seconds."
        except Exception as e:
            return f"Error waiting: {str(e)}"

    def run_command(self, command: str) -> str:
        """Executes a shell command and returns output."""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                return f"Error ({result.returncode}): {result.stderr.strip()}"
            return result.stdout.strip() if result.stdout.strip() else result.stderr.strip()
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 15 seconds."
        except Exception as e:
            return f"Exception: {str(e)}"

    def get_all_apps(self) -> List[str]:
        """Returns a list of all installed app names from desktop files and flatpaks."""
        apps = set()
        # From desktop files
        try:
            cmd = "grep -rh '^Name=' /usr/share/applications ~/.local/share/applications 2>/dev/null | cut -d= -f2-"
            names = subprocess.check_output(cmd, shell=True).decode().splitlines()
            apps.update([n.strip().lower() for n in names if n.strip()])
        except Exception as e:
            logger.debug(f"Error listing desktop apps: {e}")
        
        # From Flatpaks
        try:
            cmd = "flatpak list --columns=name"
            names = subprocess.check_output(cmd, shell=True).decode().splitlines()
            apps.update([n.strip().lower() for n in names if n.strip() and "Name" not in n])
        except Exception as e:
            logger.debug(f"Error listing flatpaks: {e}")
        
        return sorted(list(apps))

    def focus_window(self, class_name: str) -> str:
        """Focuses a window by its class name."""
        return self.run_command(f"hyprctl dispatch focuswindow class:{class_name}")

    def open_app(self, app_name: str) -> str:
        """Dynamically finds and opens an application with search logic."""
        app_name = app_name.lower().strip()
        logger.info(f"SystemExecutor: Searching for '{app_name}'...")
        
        # Check if already running to focus instead of launching another instance
        try:
            clients = self.run_command("hyprctl clients -j")
            clients_data = json.loads(clients)
            for client in clients_data:
                if app_name in client.get('class', '').lower() or app_name in client.get('title', '').lower():
                    logger.info(f"SystemExecutor: App '{app_name}' is already running. Focusing.")
                    self.focus_window(client['class'])
                    return f"{app_name} is already open. Focusing window."
        except Exception as e:
            logger.debug(f"Focus check error: {e}")

        # 1. Search in desktop files (Name, GenericName, Comment)
        try:
            search_cmd = f"grep -riE '(Name|GenericName|Comment)=.*{app_name}' /usr/share/applications ~/.local/share/applications 2>/dev/null | head -n 1 | cut -d: -f1"
            desktop_file = subprocess.check_output(search_cmd, shell=True).decode().strip()
            
            if desktop_file:
                exec_cmd = subprocess.check_output(f"grep '^Exec=' '{desktop_file}' | head -n 1 | cut -d= -f2- | sed 's/ %.*//'", shell=True).decode().strip()
                if exec_cmd:
                    # Remove quotes if present
                    exec_cmd = exec_cmd.replace('"', '').replace("'", "")
                    logger.info(f"SystemExecutor: Found app in {desktop_file} -> Exec: {exec_cmd}")
                    self.run_command(f"hyprctl dispatch exec {exec_cmd}")
                    return f"Opening {app_name}."
        except Exception as e:
            logger.debug(f"Search desktop files error: {e}")

        # 2. Search in Flatpaks (Application ID and Name)
        try:
            flatpak_cmd = f"flatpak list --columns=application,name | grep -i '{app_name}' | head -n 1 | awk '{{print $1}}'"
            flatpak_id = subprocess.check_output(flatpak_cmd, shell=True).decode().strip()
            if flatpak_id:
                logger.info(f"SystemExecutor: Found flatpak -> {flatpak_id}")
                self.run_command(f"hyprctl dispatch exec flatpak run {flatpak_id}")
                return f"Launching {app_name} via Flatpak."
        except Exception as e:
            logger.debug(f"Search flatpaks error: {e}")

        # 3. Check if binary exists in PATH
        check_binary = subprocess.run(f"which {app_name}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if check_binary.returncode == 0:
            self.run_command(f"hyprctl dispatch exec {app_name}")
            return f"Found {app_name} in system path. Launching."
        
        return f"I couldn't find {app_name} on your system."

    def media_control(self, action: str) -> str:
        """Controls media (play, pause, play-pause, next, previous)."""
        action = action.lower().strip()
        if action == "play/pause" or action == "playpause":
            action = "play-pause"
        return self.run_command(f"playerctl {action}")

    def set_volume(self, level: str) -> str:
        """Sets system volume (0-100 or relative e.g., +10%, -10%)."""
        level_str = str(level).strip()
        # Handle relative modifications
        if level_str.startswith('+') or level_str.startswith('-'):
            sign = level_str[0]
            val = level_str[1:].replace('%', '').strip()
            return self.run_command(f"pactl set-sink-volume @DEFAULT_SINK@ {sign}{val}%")
        else:
            val = level_str.replace('%', '').strip()
            return self.run_command(f"pactl set-sink-volume @DEFAULT_SINK@ {val}%")

    def get_volume(self) -> str:
        """Gets current system volume percentage."""
        vol = self.run_command(r"pactl get-sink-volume @DEFAULT_SINK@ | grep -oP '\d+(?=%)' | head -n 1")
        if not vol or "Error" in vol:
            # Fallback
            vol = self.run_command("amixer get Master | grep -oQ '\\[[0-9]*%\\]' | grep -o '[0-9]*' | head -n 1")
        return vol if vol else "50"

    def set_brightness(self, level: str) -> str:
        """Sets screen brightness (0-100 or relative)."""
        level_str = str(level).strip()
        if level_str.startswith('+') or level_str.startswith('-'):
            sign = level_str[0]
            val = level_str[1:].replace('%', '').strip()
            if sign == '+':
                return self.run_command(f"brightnessctl set +{val}%")
            else:
                return self.run_command(f"brightnessctl set {val}%-")
        else:
            val = level_str.replace('%', '').strip()
            return self.run_command(f"brightnessctl set {val}%")

    def get_brightness(self) -> str:
        """Gets current brightness percentage."""
        try:
            curr = int(self.run_command("brightnessctl get"))
            mx = int(self.run_command("brightnessctl max"))
            return str(round((curr * 100) / mx))
        except:
            return "70"

    def take_screenshot(self, full: bool = False) -> str:
        """Takes a screenshot using grim. If full=False, uses slurp for selection."""
        filename = f"screenshot_{int(time.time())}.png"
        pictures_dir = os.path.expanduser("~/Pictures")
        if not os.path.exists(pictures_dir):
            os.makedirs(pictures_dir)
            
        path = os.path.join(pictures_dir, filename)
        
        if full:
            # Full screen, save to temp for vision
            temp_path = "/tmp/voider_screen.png"
            self.run_command(f"grim {temp_path}")
            # Also copy to pictures
            self.run_command(f"cp {temp_path} {path}")
            return temp_path
        else:
            self.run_command(f"grim -g \"$(slurp)\" {path}")
            return path

    def move_window(self, workspace: str) -> str:
        """Moves active window to a specific workspace."""
        return self.run_command(f"hyprctl dispatch movetoworkspace {workspace}")

    def switch_workspace(self, workspace: str) -> str:
        """Switches to a specific workspace."""
        return self.run_command(f"hyprctl dispatch workspace {workspace}")

    def run_shell(self, command: str) -> str:
        """Executes an arbitrary shell command. For interactive tools, launches alacritty."""
        interactive_keywords = ['pacman', 'yay', 'paru', 'nano', 'vim', 'btop', 'htop', 'systemctl']
        if any(kw in command for kw in interactive_keywords):
            # Run in terminal
            term_cmd = f"hyprctl dispatch exec \"alacritty -e bash -c '{command}; echo Press Enter to close...; read'\""
            subprocess.Popen(term_cmd, shell=True)
            return "Command launched in external terminal."
        else:
            return self.run_command(command)

    def type_text(self, text: str) -> str:
        """Types text onto the screen using wtype (Wayland) with fallback to ydotool."""
        try:
            # Escape single quotes for shell command safety
            escaped_text = text.replace("'", "'\\''")
            subprocess.run(f"wtype -d 50 '{escaped_text}'", shell=True, check=True, capture_output=True)
            return f"Typed via wtype: {text}"
        except Exception as e:
            # Fallback to ydotool
            escaped_text = text.replace("'", "'\\''")
            return self.run_command(f"YDOTOOL_SOCKET=/tmp/ydotoolsock ydotool type '{escaped_text}'")

    def mouse_click(self, button: str = "left") -> str:
        """Performs a mouse click using ydotool."""
        btn_code = "0xC0" if button == "left" else "0xC1"
        return self.run_command(f"YDOTOOL_SOCKET=/tmp/ydotoolsock ydotool click {btn_code}")

    def mouse_move(self, x: int, y: int) -> str:
        """Moves mouse to coordinates x, y."""
        return self.run_command(f"YDOTOOL_SOCKET=/tmp/ydotoolsock ydotool mousemove -a {x} {y}")

    def press_key(self, key_combo: str) -> str:
        """Presses a key using wtype or ydotool."""
        key_combo = key_combo.lower().strip()
        
        try:
            if "+" in key_combo:
                parts = key_combo.split("+")
                modifiers = parts[:-1]
                key = parts[-1]
                if key == "enter": key = "Return"
                elif len(key) > 1: key = key.capitalize()
                mod_on = " ".join([f"-M {m}" for m in modifiers])
                mod_off = " ".join([f"-m {m}" for m in reversed(modifiers)])
                subprocess.run(f"wtype {mod_on} -k {key} {mod_off}", shell=True, check=True, capture_output=True)
            else:
                wtype_key = "Return" if key_combo == "enter" else key_combo
                if len(wtype_key) > 1: wtype_key = wtype_key.capitalize()
                subprocess.run(f"wtype -k {wtype_key}", shell=True, check=True, capture_output=True)
            result = f"Pressed via wtype: {key_combo}"
        except:
            result = self.run_command(f"YDOTOOL_SOCKET=/tmp/ydotoolsock ydotool key {key_combo}")
        
        time.sleep(0.3)
        return result

    def power_mgmt(self, action: str) -> str:
        """Handles power actions (reboot, shutdown, logout)."""
        action = action.lower().strip()
        if action == "shutdown":
            return self.run_command("systemctl poweroff")
        elif action == "reboot":
            return self.run_command("systemctl reboot")
        elif action == "logout":
            return self.run_command("hyprctl dispatch exit")
        return "Unknown power action"

    def get_system_info(self) -> str:
        """Returns CPU and Memory usage summary."""
        cpu = self.run_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        mem = self.run_command("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'")
        return f"CPU Usage: {cpu}%, Memory Usage: {mem}"

    def close_window(self) -> str:
        """Closes the active window."""
        return self.run_command("hyprctl dispatch killactive")

    def check_for_updates(self) -> str:
        """Checks for available system updates."""
        # 1. Try checkupdates if available
        try:
            result = subprocess.run(["checkupdates"], capture_output=True, text=True)
            if result.returncode == 0:
                count = len(result.stdout.strip().splitlines())
                return f"There are {count} updates available."
            elif result.returncode == 2:
                return "Your system is fully up to date."
        except Exception:
            pass

        # 2. Try pacman -Qu
        try:
            result = subprocess.run(["pacman", "-Qu"], capture_output=True, text=True)
            if result.returncode == 0:
                count = len(result.stdout.strip().splitlines())
                return f"There are {count} updates pending."
            elif result.returncode == 1:
                return "Your system is fully up to date."
            else:
                return "I couldn't check for updates at the moment."
        except Exception as e:
            logger.debug(f"Error checking pacman updates: {e}")
            return "I couldn't check for updates at the moment."

    def get_active_windows(self) -> List[Dict]:
        """Gets currently open window clients from Hyprland."""
        try:
            output = self.run_command("hyprctl clients -j")
            return json.loads(output)
        except Exception as e:
            logger.error(f"Error getting clients: {e}")
            return []

# Global system executor instance
_system_executor: Optional[SystemExecutor] = None

def get_system_executor() -> SystemExecutor:
    global _system_executor
    if _system_executor is None:
        _system_executor = SystemExecutor()
    return _system_executor
