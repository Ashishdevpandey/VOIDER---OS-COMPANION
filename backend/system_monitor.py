"""
System Monitor for VOIDER - OS Companion
Monitors CPU, RAM, and Disk space, and builds local system RAG context.
"""

import psutil
import platform
import subprocess
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitors system performance metrics and updates the local system properties list."""

    def __init__(self, context_path: str = "./system_context.txt"):
        self.context_path = context_path

    def get_stats(self) -> Dict[str, float]:
        """Gets CPU, RAM, and Disk percent usage."""
        try:
            return {
                "cpu": psutil.cpu_percent(interval=None),
                "ram": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent
            }
        except Exception as e:
            logger.error(f"Error obtaining stats: {e}")
            return {"cpu": 0.0, "ram": 0.0, "disk": 0.0}

    def get_system_info(self) -> Dict:
        """Collects details about hardware, operating system, and installed applications."""
        info = {
            "os": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "node": platform.node(),
            "processor": platform.processor(),
        }
        
        try:
            mem = psutil.virtual_memory()
            info["memory"] = [f"{mem.total / (1024**3):.1f}GB", f"{mem.used / (1024**3):.1f}GB"]
        except Exception as e:
            logger.debug(f"Memory read error: {e}")
            
        try:
            # List installed desktop apps
            apps = subprocess.check_output(
                "ls /usr/share/applications/*.desktop ~/.local/share/applications/*.desktop 2>/dev/null | xargs -n 1 basename | sed 's/\\.desktop//'",
                shell=True
            ).decode().split('\n')
            info["desktop_apps"] = [a.strip() for a in apps if a.strip()]
        except Exception as e:
            info["desktop_apps"] = []
            
        try:
            # List installed flatpaks
            flatpaks = subprocess.check_output(
                "flatpak list --columns=application,name 2>/dev/null | tail -n +1",
                shell=True
            ).decode().split('\n')
            info["flatpaks"] = [f.strip() for f in flatpaks if f.strip() and "Application" not in f]
        except Exception as e:
            info["flatpaks"] = []

        return info

    def update_system_context(self) -> str:
        """Generates/updates a readable text summary of the system specifications for the LLM."""
        try:
            info = self.get_system_info()
            lines = [
                "--- SYSTEM CONTEXT FOR VOIDER ---",
                f"OS: {info['os']} {info['release']} ({info['architecture']})",
                f"Node Name: {info['node']}",
            ]
            if 'memory' in info and len(info['memory']) == 2:
                lines.append(f"Memory: Total {info['memory'][0]}, Used {info['memory'][1]}")
            
            lines.append("\n--- INSTALLED APPLICATIONS ---")
            all_apps = list(set(info.get('desktop_apps', []) + info.get('flatpaks', [])))
            all_apps.sort()
            lines.append(", ".join(all_apps[:150])) # Limit to keep context readable and prompt token size low

            content = "\n".join(lines)
            with open(self.context_path, "w") as f:
                f.write(content)
            
            logger.info(f"System Monitor: Updated {self.context_path}")
            return content
        except Exception as e:
            logger.error(f"Error updating system context: {e}")
            return ""

# Global instance
_monitor = None

def get_system_monitor(context_path: str = "./system_context.txt") -> SystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor(context_path=context_path)
    return _monitor
