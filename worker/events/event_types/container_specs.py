from pprint import pprint
from .eventType import EventType
import psutil
import pynvml
import platform
import os

class ContainerSpecs(EventType):
    name = "container_specs"
    
    def __init__(self):        
        self.data = self.get_system_specs()
        
    def get_system_specs(self):
        specs: dict[str, object] = {}

        
        # 1. CPU - Get usage and core count
        specs['cpu_usage_pct'] = psutil.cpu_percent(interval=None)
        #pyrefly:ignore
        specs['cpu_cores'] = psutil.cpu_count(logical=True)

        #pyrefly:ignore
        specs['operating_system'] = get_os_details()

        # 2. RAM - Total and Available
        ram = psutil.virtual_memory()
        specs['ram_total_gb'] = round(ram.total / (1024**3), 2)
        specs['ram_available_gb'] = round(ram.available / (1024**3), 2)
    
        # 3. Storage - Based on the root directory
        disk = psutil.disk_usage('/')
        specs['storage_total_gb'] = round(disk.total / (1024**3), 2)
        specs['storage_free_gb'] = round(disk.free / (1024**3), 2)

        # 4. Get GPUS. Works on Nvidia and Intel (integrated). Other platforms needs testing.
        #pyrefly:ignore
        specs["gpus"] = get_all_gpus()
        specs["capabilities"] = {
            "terminal": True,
            "machine_logs": True,
        }
        
        return specs

def get_all_gpus():
    """
    Clean cross-platform GPU detection.
    Supports:
        - NVIDIA / AMD / Intel / Apple
        - Windows / Linux / macOS

    Returns:
        list[dict]
    """
    import platform
    import subprocess
    import re

    system = platform.system()
    gpus = []

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def normalize_name(name: str) -> str:
        if not name:
            return "Unknown GPU"

        name = re.sub(r"\(rev .*?\)", "", name)
        name = name.replace("Corporation", "")
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def detect_brand(name: str) -> str:
        u = name.upper()

        if "NVIDIA" in u:
            return "NVIDIA"
        if "INTEL" in u:
            return "Intel"
        if "AMD" in u or "RADEON" in u or "ATI" in u:
            return "AMD"
        if "APPLE" in u or "M1" in u or "M2" in u or "M3" in u:
            return "Apple"

        return "Unknown"

    def same_gpu(a: str, b: str) -> bool:
        a = a.upper()
        b = b.upper()

        # NVIDIA family matching
        if "3060" in a and "3060" in b:
            return True
        if "3070" in a and "3070" in b:
            return True
        if "3080" in a and "3080" in b:
            return True

        # Intel Iris Xe
        if "IRIS XE" in a and "IRIS XE" in b:
            return True

        return a == b

    def add_gpu(name, total=None, free=None, used=None):
        name = normalize_name(name)

        for gpu in gpus:
            if same_gpu(gpu["name"], name):
                # Keep richer stats if existing is empty
                if gpu["vram_total_mb"] is None and total is not None:
                    gpu["vram_total_mb"] = total
                if gpu["vram_free_mb"] is None and free is not None:
                    gpu["vram_free_mb"] = free
                if gpu["vram_used_mb"] is None and used is not None:
                    gpu["vram_used_mb"] = used
                return

        gpus.append({
            "brand": detect_brand(name),
            "name": name,
            "vram_total_mb": total,
            "vram_free_mb": free,
            "vram_used_mb": used
        })

    # -------------------------------------------------
    # NVIDIA via NVML (best source)
    # -------------------------------------------------
    try:
        import pynvml

        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()

        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)

            name = pynvml.nvmlDeviceGetName(h)
            if isinstance(name, bytes):
                name = name.decode()

            mem = pynvml.nvmlDeviceGetMemoryInfo(h)

            add_gpu(
                name=name,
                total=round(mem.total / 1024**2, 2),
                free=round(mem.free / 1024**2, 2),
                used=round(mem.used / 1024**2, 2)
            )

        pynvml.nvmlShutdown()

    except Exception:
        pass

    # -------------------------------------------------
    # Windows
    # -------------------------------------------------
    if system == "Windows":
        try:
            import wmi
            c = wmi.WMI()

            for gpu in c.Win32_VideoController():
                name = gpu.Name
                total = None

                try:
                    if gpu.AdapterRAM:
                        total = round(int(gpu.AdapterRAM) / 1024**2, 2)
                except Exception:
                    pass

                add_gpu(name=name, total=total)

        except Exception:
            pass

    # -------------------------------------------------
    # Linux
    # -------------------------------------------------
    elif system == "Linux":
        try:
            out = subprocess.check_output(
                ["lspci"],
                text=True,
                stderr=subprocess.DEVNULL
            )

            for line in out.splitlines():
                l = line.lower()

                if "vga compatible controller" in l or "3d controller" in l:
                    name = line.split(": ", 1)[-1]
                    add_gpu(name=name)

        except Exception:
            pass

    # -------------------------------------------------
    # macOS
    # -------------------------------------------------
    elif system == "Darwin":
        try:
            out = subprocess.check_output(
                ["system_profiler", "SPDisplaysDataType"],
                text=True
            )

            for line in out.splitlines():
                line = line.strip()

                if line.startswith("Chipset Model:"):
                    name = line.split(":", 1)[1].strip()
                    add_gpu(name=name)

                elif line.startswith("Graphics Processor:"):
                    name = line.split(":", 1)[1].strip()
                    add_gpu(name=name)

        except Exception:
            pass

    # -------------------------------------------------
    # Fallback
    # -------------------------------------------------
    if not gpus:
        return [{
            "brand": "None",
            "name": "No GPU detected",
            "vram_total_mb": 0,
            "vram_free_mb": 0,
            "vram_used_mb": 0
        }]

    return gpus

def get_os_details():
    system_name = platform.system()
    
    os_details = {
        "name": "",
        "version": "",
        "architecture": platform.architecture()[0]  # Architecture (e.g., '64bit' or '32bit')
    }
    
    if system_name == "Windows":
        os_details["name"] = "Windows"
        os_details["version"] = platform.version()  # Windows version, e.g., "10.0.18363"
    
    elif system_name == "Darwin":  # macOS
        os_details["name"] = "macOS"
        os_details["version"] = platform.mac_ver()[0]  # macOS version, e.g., "10.15.7"
    
    elif system_name == "Linux":
        os_details["name"] = "Linux"
        try:
            import distro
            os_details["version"] = distro.version()  # Get version from distro module
        except ImportError:
            # If 'distro' is not available, read /etc/os-release
            try:
                with open("/etc/os-release") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("VERSION="):
                            os_details["version"] = line.strip().split('=')[1].replace('"', '')
                        if line.startswith("NAME="):
                            os_details["name"] = line.strip().split('=')[1].replace('"', '')
            except FileNotFoundError:
                os_details["version"] = "Unknown Linux Distro"
    
    else:
        os_details["name"] = "Unknown"
        os_details["version"] = "Unknown"
    
    return os_details



__all__ = ["ContainerSpecs"]