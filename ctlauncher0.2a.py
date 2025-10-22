import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import hashlib
import ssl
import time
import requests  # Added for dynamic Java version fetching

# Define constants for directories and URLs
CTLAUNCHER_DIR = os.path.expanduser("~/.ctlauncher")
VERSIONS_DIR = os.path.join(CTLAUNCHER_DIR, "versions")
JAVA_DIR = os.path.expanduser("~/.ctlauncher/java")
VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
ASSETS_DIR = os.path.join(CTLAUNCHER_DIR, "assets")

# Download settings
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds
DOWNLOAD_TIMEOUT = 60  # seconds
RATE_LIMIT_DELAY = 0.1  # seconds between downloads

# CTLauncher theme colors - Dark theme (original)
DARK_THEME = {
    'bg': '#121212',
    'sidebar': '#1f1f1f',
    'accent': '#2196f3',
    'accent_light': '#64b5f6',
    'text': '#ffffff',
    'text_secondary': '#bbbbbb',
    'button': '#2196f3',
    'button_hover': '#64b5f6',
    'input_bg': '#2f2f2f',
    'header_bg': '#0d0d0d',
    'tab_active': '#2196f3',
    'tab_inactive': '#121212'
}

# Light theme
LIGHT_THEME = {
    'bg': '#ffffff',
    'sidebar': '#f0f0f0',
    'accent': '#007bff',
    'accent_light': '#66aaff',
    'text': '#000000',
    'text_secondary': '#666666',
    'button': '#007bff',
    'button_hover': '#66aaff',
    'input_bg': '#e0e0e0',
    'header_bg': '#e9ecef',
    'tab_active': '#007bff',
    'tab_inactive': '#ffffff'
}

class CTLauncher(tk.Tk):
    def __init__(self):
        """Initialize the CTLauncher window and UI."""
        super().__init__()
        self.title("CTLauncher v1.0")
        self.geometry("900x550")
        self.minsize(800, 500)
        self.themes = {'Dark': DARK_THEME, 'Light': LIGHT_THEME}
        self.current_theme_mode = 'Dark'
        self.theme = self.themes[self.current_theme_mode]
        self.configure(bg=self.theme['bg'])
        self.versions = {}  # Dictionary to store version IDs and their URLs
        self.version_categories = {
            "Latest Release": [],
            "Latest Snapshot": [],
            "Release": [],
            "Snapshot": [],
            "Old Beta": [],
            "Old Alpha": []
        }
        
        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.apply_theme_styles()
        self.init_ui()

    def apply_theme_styles(self):
        """Apply theme to ttk styles."""
        self.style.configure("TFrame", background=self.theme['bg'])
        self.style.configure("TLabel", background=self.theme['bg'], foreground=self.theme['text'])
        self.style.configure("TButton",
                             background=self.theme['button'],
                             foreground=self.theme['text'],
                             borderwidth=0,
                             focuscolor='none')
        self.style.map("TButton",
                       background=[('active', self.theme['button_hover']),
                                   ('pressed', self.theme['accent'])])
        
        self.style.configure("TCombobox",
                             fieldbackground=self.theme['input_bg'],
                             background=self.theme['input_bg'],
                             foreground=self.theme['text'],
                             arrowcolor=self.theme['text'],
                             borderwidth=0)
        
        self.style.configure("TScale",
                             background=self.theme['bg'],
                             troughcolor=self.theme['input_bg'])
        
        self.style.configure("TNotebook",
                             background=self.theme['header_bg'],
                             borderwidth=0)
        self.style.configure("TNotebook.Tab",
                             background=self.theme['tab_inactive'],
                             foreground=self.theme['text_secondary'],
                             padding=[15, 5],
                             borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[('selected', self.theme['tab_active'])],
                       foreground=[('selected', self.theme['text'])])

    def init_ui(self):
        """Set up the graphical user interface with CTLauncher styling."""
        # Header
        self.header = tk.Frame(self, bg=self.theme['header_bg'], height=40)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)
        
        # Header title
        self.title_label = tk.Label(self.header, text="CTLauncher", font=("Arial", 14, "bold"),
                         bg=self.theme['header_bg'], fg=self.theme['accent'])
        self.title_label.pack(side="left", padx=15, pady=10)
        
        # Header version
        self.version_label = tk.Label(self.header, text="v1.0", font=("Arial", 10),
                           bg=self.theme['header_bg'], fg=self.theme['text_secondary'])
        self.version_label.pack(side="right", padx=15, pady=10)
        
        # Theme toggler
        theme_frame = tk.Frame(self.header, bg=self.theme['header_bg'])
        theme_frame.pack(side="right", padx=10, pady=10)
        theme_label = tk.Label(theme_frame, text="Theme:", font=("Arial", 10),
                               bg=self.theme['header_bg'], fg=self.theme['text_secondary'])
        theme_label.pack(side="left")
        self.theme_combo = ttk.Combobox(theme_frame, values=['Dark', 'Light', 'System'],
                                        state="readonly", width=8, font=("Arial", 10))
        self.theme_combo.pack(side="left")
        self.theme_combo.set(self.current_theme_mode)
        self.theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # Main container
        self.main_container = tk.Frame(self, bg=self.theme['bg'])
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - Game settings
        self.left_panel = tk.Frame(self.main_container, bg=self.theme['sidebar'], width=300)
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))
        self.left_panel.pack_propagate(False)
        
        # Game version selection
        self.version_frame = tk.Frame(self.left_panel, bg=self.theme['sidebar'])
        self.version_frame.pack(fill="x", padx=15, pady=15)
        
        tk.Label(self.version_frame, text="VERSION", font=("Arial", 9, "bold"),
                 bg=self.theme['sidebar'], fg=self.theme['text_secondary']).pack(anchor="w")
        
        self.category_combo = ttk.Combobox(self.version_frame, values=list(self.version_categories.keys()),
                                           state="readonly", font=("Arial", 10))
        self.category_combo.pack(fill="x", pady=(5, 0))
        self.category_combo.set("Latest Release")
        self.category_combo.bind("<<ComboboxSelected>>", self.update_version_list)
        
        self.version_combo = ttk.Combobox(self.version_frame, state="readonly", font=("Arial", 10))
        self.version_combo.pack(fill="x", pady=5)
        
        # Account settings
        self.account_frame = tk.Frame(self.left_panel, bg=self.theme['sidebar'])
        self.account_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(self.account_frame, text="ACCOUNT", font=("Arial", 9, "bold"),
                 bg=self.theme['sidebar'], fg=self.theme['text_secondary']).pack(anchor="w")
        
        self.username_input = tk.Entry(self.account_frame, font=("Arial", 10), bg=self.theme['input_bg'],
                                       fg=self.theme['text'], insertbackground=self.theme['text'], bd=0, relief="flat")
        self.username_input.pack(fill="x", pady=(5, 0))
        self.username_input.insert(0, "Player")
        self.username_input.bind("<FocusIn>", lambda e: self.username_input.delete(0, tk.END)
                                 if self.username_input.get() == "Player" else None)
        
        # RAM settings
        self.ram_frame = tk.Frame(self.left_panel, bg=self.theme['sidebar'])
        self.ram_frame.pack(fill="x", padx=15, pady=10)
        
        self.ram_header = tk.Frame(self.ram_frame, bg=self.theme['sidebar'])
        self.ram_header.pack(fill="x")
        
        tk.Label(self.ram_header, text="RAM", font=("Arial", 9, "bold"),
                 bg=self.theme['sidebar'], fg=self.theme['text_secondary']).pack(side="left")
        
        self.ram_value_label = tk.Label(self.ram_header, text="4 GB", font=("Arial", 9),
                                        bg=self.theme['sidebar'], fg=self.theme['text'])
        self.ram_value_label.pack(side="right")
        
        self.ram_scale = tk.Scale(self.ram_frame, from_=1, to=16, orient="horizontal",
                                  bg=self.theme['sidebar'], fg=self.theme['text'],
                                  activebackground=self.theme['accent'],
                                  highlightthickness=0, bd=0,
                                  troughcolor=self.theme['input_bg'],
                                  sliderrelief="flat",
                                  command=lambda v: self.ram_value_label.config(text=f"{int(float(v))} GB"))
        self.ram_scale.set(4)
        self.ram_scale.pack(fill="x")
        
        # Skin button
        skin_button = tk.Button(self.left_panel, text="Change Skin", font=("Arial", 10),
                                bg=self.theme['button'], fg=self.theme['text'],
                                bd=0, padx=20, pady=8, command=self.select_skin)
        skin_button.pack(padx=15, pady=10, fill="x")
        
        # Launch button
        launch_button = tk.Button(self.left_panel, text="PLAY NOW", font=("Arial", 12, "bold"),
                                  bg=self.theme['accent'], fg=self.theme['text'],
                                  bd=0, padx=20, pady=12, command=self.prepare_and_launch)
        launch_button.pack(side="bottom", padx=15, pady=15, fill="x")
        
        # Right panel - Tabs and content
        self.right_panel = tk.Frame(self.main_container, bg=self.theme['bg'])
        self.right_panel.pack(side="left", fill="both", expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.right_panel)
        notebook.pack(fill="both", expand=True)
        
        # News tab
        news_tab = ttk.Frame(notebook)
        notebook.add(news_tab, text="News")
        
        # Versions tab
        versions_tab = ttk.Frame(notebook)
        notebook.add(versions_tab, text="Versions")
        
        # Settings tab
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")
        
        # Populate news tab with CTLauncher content
        news_content = tk.Frame(news_tab, bg=self.theme['bg'])
        news_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # News title
        news_title = tk.Label(news_content, text="CTLauncher News",
                              font=("Arial", 16, "bold"), bg=self.theme['bg'], fg=self.theme['accent'])
        news_title.pack(anchor="w", pady=(0, 15))
        
        # News items
        news_items = [
            "Custom Minecraft Launcher with modern interface",
            "Support for all Minecraft versions",
            "Automatic Java installation",
            "Easy skin changing",
            "Optimized performance settings",
            "Lightweight and fast",
            "Regular updates and improvements",
            "Advanced technology powered",
            "NEW: Enhanced download stability with retry logic!",
            "FIXED: Full asset downloading and natives resolution for stable launches"
        ]
        for item in news_items:
            item_frame = tk.Frame(news_content, bg=self.theme['bg'])
            item_frame.pack(fill="x", pady=2)
            tk.Label(item_frame, text=item, font=("Arial", 10),
                     bg=self.theme['bg'], fg=self.theme['text'], justify="left", anchor="w").pack(fill='x')
        
        # Version list in versions tab
        versions_content = tk.Frame(versions_tab, bg=self.theme['bg'])
        versions_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        versions_title = tk.Label(versions_content, text="AVAILABLE VERSIONS",
                                  font=("Arial", 12, "bold"), bg=self.theme['bg'], fg=self.theme['text'])
        versions_title.pack(anchor="w", pady=(0, 10))
        
        # Version listbox
        version_list_frame = tk.Frame(versions_content, bg=self.theme['bg'])
        version_list_frame.pack(fill="both", expand=True)
        
        # Scrollbar for version list
        scrollbar = ttk.Scrollbar(version_list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.version_listbox = tk.Listbox(version_list_frame, bg=self.theme['input_bg'], fg=self.theme['text'],
                                          selectbackground=self.theme['accent'], selectforeground=self.theme['text'],
                                          yscrollcommand=scrollbar.set, font=("Arial", 10), bd=0)
        self.version_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.version_listbox.yview)
        
        # Settings tab content
        settings_content = tk.Frame(settings_tab, bg=self.theme['bg'])
        settings_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        settings_title = tk.Label(settings_content, text="CTLAUNCHER SETTINGS",
                                  font=("Arial", 12, "bold"), bg=self.theme['bg'], fg=self.theme['text'])
        settings_title.pack(anchor="w", pady=(0, 10))
        
        # Settings options
        settings_options = [
            ("Auto-update CTLauncher", tk.BooleanVar(value=True)),
            ("Close launcher when game starts", tk.BooleanVar(value=False)),
            ("Keep launcher open (recommended)", tk.BooleanVar(value=True)),
            ("Check for Java updates", tk.BooleanVar(value=True))
        ]
        for text, var in settings_options:
            cb = tk.Checkbutton(settings_content, text=text, variable=var,
                                bg=self.theme['bg'], fg=self.theme['text'], selectcolor=self.theme['sidebar'],
                                activebackground=self.theme['bg'], activeforeground=self.theme['text'])
            cb.pack(anchor="w", pady=5)
        
        # Game directory setting
        dir_frame = tk.Frame(settings_content, bg=self.theme['bg'])
        dir_frame.pack(fill="x", pady=10)
        
        tk.Label(dir_frame, text="Game Directory:", bg=self.theme['bg'], fg=self.theme['text']).pack(anchor="w")
        
        dir_entry = tk.Entry(dir_frame, bg=self.theme['input_bg'], fg=self.theme['text'],
                             insertbackground=self.theme['text'], bd=0)
        dir_entry.insert(0, CTLAUNCHER_DIR)
        dir_entry.pack(fill="x", pady=(5, 0))
        
        # Load versions after UI is initialized
        self.load_version_manifest()

    def change_theme(self, event=None):
        """Handle theme change from combobox."""
        mode = self.theme_combo.get()
        if mode == 'System':
            detected = self.detect_system_mode()
            self.theme = self.themes[detected]
            self.current_theme_mode = detected
        else:
            self.theme = self.themes[mode]
            self.current_theme_mode = mode
        self.apply_theme()

    def detect_system_mode(self):
        """Detect system theme preference."""
        system = platform.system()
        if system == 'Windows':
            try:
                from winreg import OpenKey, QueryValueEx, CloseKey, HKEY_CURRENT_USER
                key = OpenKey(HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = QueryValueEx(key, "AppsUseLightTheme")
                CloseKey(key)
                return 'Light' if value == 1 else 'Dark'
            except:
                return 'Light'
        elif system == 'Darwin':
            try:
                output = subprocess.check_output(["defaults", "read", "-g", "AppleInterfaceStyle"])
                return 'Dark' if b'Dark' in output else 'Light'
            except:
                return 'Light'
        elif system == 'Linux':
            try:
                output = subprocess.check_output(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"])
                return 'Dark' if b'prefer-dark' in output else 'Light'
            except:
                return 'Light'
        return 'Light'

    def apply_theme(self):
        """Apply the current theme to all widgets and styles."""
        self.configure(bg=self.theme['bg'])
        self.apply_theme_styles()
        
        def update_widgets(widget, depth=0, max_depth=10):
            if depth > max_depth:  # Prevent recursion depth issues
                return
            try:
                wtype = type(widget)
                if wtype in (tk.Frame, ttk.Frame):
                    widget.configure(bg=self.theme['bg'] if 'header' not in str(widget.winfo_name()) and 'sidebar' not in str(widget.winfo_name()) else self.theme.get('header_bg', self.theme['bg']) if 'header' in str(widget.winfo_name()) else self.theme['sidebar'])
                elif wtype == tk.Label:
                    bg = self.theme['bg'] if 'header' not in str(widget.master.winfo_name()) else self.theme['header_bg']
                    fg = self.theme['text'] if 'secondary' not in str(widget['text']) else self.theme['text_secondary']
                    if 'CTLauncher News' in str(widget['text']):
                        fg = self.theme['accent']
                    widget.configure(bg=bg, fg=fg)
                elif wtype == tk.Button:
                    widget.configure(bg=self.theme['button'] if 'PLAY' not in str(widget['text']) else self.theme['accent'], fg=self.theme['text'])
                elif wtype == tk.Entry:
                    widget.configure(bg=self.theme['input_bg'], fg=self.theme['text'], insertbackground=self.theme['text'])
                elif wtype == tk.Listbox:
                    widget.configure(bg=self.theme['input_bg'], fg=self.theme['text'], selectbackground=self.theme['accent'], selectforeground=self.theme['text'])
                elif wtype == tk.Checkbutton:
                    widget.configure(bg=self.theme['bg'], fg=self.theme['text'], activebackground=self.theme['bg'], activeforeground=self.theme['text'], selectcolor=self.theme['sidebar'])
                elif wtype == tk.Scale:
                    widget.configure(bg=self.theme['sidebar'], fg=self.theme['text'], activebackground=self.theme['accent'], troughcolor=self.theme['input_bg'])
            except:
                pass
            for child in widget.winfo_children():
                update_widgets(child, depth + 1, max_depth)
        
        update_widgets(self)
        self.header.configure(bg=self.theme['header_bg'])
        self.title_label.configure(bg=self.theme['header_bg'], fg=self.theme['accent'])
        self.version_label.configure(bg=self.theme['header_bg'], fg=self.theme['text_secondary'])
        self.left_panel.configure(bg=self.theme['sidebar'])
        self.version_frame.configure(bg=self.theme['sidebar'])
        self.account_frame.configure(bg=self.theme['sidebar'])
        self.ram_frame.configure(bg=self.theme['sidebar'])
        self.ram_header.configure(bg=self.theme['sidebar'])
        self.ram_value_label.configure(bg=self.theme['sidebar'], fg=self.theme['text'])
        self.main_container.configure(bg=self.theme['bg'])
        self.right_panel.configure(bg=self.theme['bg'])

    def update_version_list(self, event=None):
        """Update the version list based on the selected category."""
        category = self.category_combo.get()
        if self.version_categories[category]:
            self.version_combo['values'] = self.version_categories[category]
            self.version_combo.current(0)
        else:
            self.version_combo['values'] = []
            self.version_combo.set("")  # Clear selection if category is empty
            self.category_combo.set("Latest Release")  # Fallback to Latest Release
            if self.version_categories["Latest Release"]:
                self.version_combo['values'] = self.version_categories["Latest Release"]
                self.version_combo.current(0)
        
        # Update the listbox in versions tab
        self.version_listbox.delete(0, tk.END)
        for version in self.version_categories[category]:
            self.version_listbox.insert(tk.END, version)

    def download_with_retry(self, url, output_path, description="file", expected_sha1=None):
        """Download a file with retry logic and checksum verification."""
        for attempt in range(MAX_RETRIES):
            try:
                print(f"📥 Downloading {description} (attempt {attempt + 1}/{MAX_RETRIES})...")
                
                # Create SSL context
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                req = urllib.request.Request(url, headers={'User-Agent': 'CTLauncher/1.0'})
                
                with urllib.request.urlopen(req, context=ssl_context, timeout=DOWNLOAD_TIMEOUT) as response:
                    with open(output_path, 'wb') as out_file:
                        out_file.write(response.read())
                
                # Verify checksum if provided
                if expected_sha1 and not self.verify_file(output_path, expected_sha1):
                    print(f"⚠️ Checksum mismatch for {description}, retrying...")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    else:
                        return False
                
                print(f"✅ Downloaded {description} successfully!")
                time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
                return True
                
            except (urllib.error.URLError, ssl.SSLError, ConnectionError, TimeoutError) as e:
                print(f"⚠️ Network error downloading {description}: {e}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    print(f"🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Failed to download {description} after {MAX_RETRIES} attempts")
                    return False
                    
            except Exception as e:
                print(f"❌ Unexpected error downloading {description}: {e}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False
        
        return False

    def load_version_manifest(self):
        """Load the list of available Minecraft versions from Mojang's servers."""
        try:
            # Create SSL context that handles certificate verification issues
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                VERSION_MANIFEST_URL,
                headers={
                    'User-Agent': 'CTLauncher/1.0 (Minecraft Launcher)',
                    'Accept': 'application/json'
                }
            )
            
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as url:
                manifest = json.loads(url.read().decode())
                
                # Clear existing categories
                for category in self.version_categories:
                    self.version_categories[category] = []
                
                # Categorize versions
                latest_release = None
                latest_snapshot = None
                
                for v in manifest["versions"]:
                    self.versions[v["id"]] = v["url"]
                    
                    # Track latest versions
                    if v["id"] == manifest["latest"]["release"]:
                        latest_release = v["id"]
                        self.version_categories["Latest Release"].append(v["id"])
                    elif v["id"] == manifest["latest"]["snapshot"]:
                        latest_snapshot = v["id"]
                        self.version_categories["Latest Snapshot"].append(v["id"])
                    
                    # Categorize by type
                    if v["type"] == "release":
                        if v["id"] != latest_release:
                            self.version_categories["Release"].append(v["id"])
                    elif v["type"] == "snapshot":
                        if v["id"] != latest_snapshot:
                            self.version_categories["Snapshot"].append(v["id"])
                    elif v["type"] == "old_beta":
                        self.version_categories["Old Beta"].append(v["id"])
                    elif v["type"] == "old_alpha":
                        self.version_categories["Old Alpha"].append(v["id"])
                
                # Update the version combo box
                self.update_version_list()
                print("✅ Version manifest loaded successfully!")
                
        except urllib.error.URLError as e:
            print(f"❌ Network error loading version manifest: {e}")
            messagebox.showerror("CTLauncher Error",
                                 f"Failed to load version manifest.\n\nNetwork Error: {str(e)}\n\nPlease check your internet connection and firewall settings.")
        except ssl.SSLError as e:
            print(f"❌ SSL error loading version manifest: {e}")
            messagebox.showerror("CTLauncher Error",
                                 f"SSL verification failed.\n\nError: {str(e)}\n\nPlease check your internet connection.")
        except Exception as e:
            print(f"❌ Error loading version manifest: {e}")
            messagebox.showerror("CTLauncher Error",
                                 f"Failed to load version manifest.\n\nError: {str(e)}\n\nPlease check your internet connection.")

    def get_latest_java_url(self):
        """Fetch the latest OpenJDK 21 release URL from Adoptium API."""
        try:
            response = requests.get("https://api.adoptium.net/v3/assets/latest/21/hotspot", timeout=10)
            response.raise_for_status()
            releases = response.json()
            system = platform.system()
            arch = "x64"
            os_map = {"Windows": "windows", "Linux": "linux", "Darwin": "mac"}
            os_name = os_map.get(system, None)
            if not os_name:
                return None, None
            for release in releases:
                if release["binary"]["os"] == os_name and release["binary"]["architecture"] == arch:
                    return release["binary"]["package"]["link"], release["version"]["openjdk_version"]
            return None, None
        except Exception as e:
            print(f"❌ Failed to fetch latest Java version: {e}")
            return None, None

    def is_java_installed(self, required_version="21"):
        """Check if a compatible Java version (21 or higher) is installed."""
        try:
            # First check system Java
            result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stderr
            match = re.search(r'version "(\d+)', output)
            if match:
                major_version = int(match.group(1))
                return major_version >= int(required_version)
        except Exception:
            pass
        
        # Check local Java installation
        try:
            java_bin = os.path.join(JAVA_DIR, self.get_local_java_dir(), "bin", "java.exe" if platform.system() == "Windows" else "java")
            if os.path.exists(java_bin):
                result = subprocess.run([java_bin, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                output = result.stderr
                match = re.search(r'version "(\d+)', output)
                if match:
                    major_version = int(match.group(1))
                    return major_version >= int(required_version)
            return False
        except Exception:
            return False

    def get_local_java_dir(self):
        """Find the extracted Java directory dynamically."""
        if not os.path.exists(JAVA_DIR):
            return "jdk-21.0.5+11"
        for dir_name in os.listdir(JAVA_DIR):
            if dir_name.startswith("jdk-") and os.path.isdir(os.path.join(JAVA_DIR, dir_name)):
                return dir_name
        return "jdk-21.0.5+11"  # Fallback to default if not found

    def install_java_if_needed(self):
        """Install the latest OpenJDK 21 if a compatible Java version is not found."""
        if self.is_java_installed():
            print("✅ Java is already installed!")
            return
        print("Installing OpenJDK 21...")
        java_url, java_version = self.get_latest_java_url()
        if not java_url:
            messagebox.showerror("CTLauncher Error", "Unsupported OS or failed to fetch Java URL!")
            return
        archive_ext = "zip" if platform.system() == "Windows" else "tar.gz"
        archive_path = os.path.join(JAVA_DIR, f"openjdk.{archive_ext}")
        os.makedirs(JAVA_DIR, exist_ok=True)
        # Use download_with_retry for Java installation
        if not self.download_with_retry(java_url, archive_path, "Java 21"):
            messagebox.showerror("CTLauncher Error",
                                 "Failed to download Java 21. Please check your internet connection or install Java manually.")
            return
        try:
            if platform.system() == "Windows":
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(JAVA_DIR)
            else:
                import tarfile
                with tarfile.open(archive_path, "r:gz") as tar_ref:
                    tar_ref.extractall(JAVA_DIR)
                java_bin = os.path.join(JAVA_DIR, self.get_local_java_dir(), "bin", "java")
                if os.path.exists(java_bin):
                    os.chmod(java_bin, 0o755)  # Make Java executable
        except Exception as e:
            print(f"❌ Failed to extract Java: {e}")
            messagebox.showerror("CTLauncher Error",
                                 f"Failed to extract Java 21: {str(e)}.\n\nPlease try again or install Java manually.")
            return
        finally:
            if os.path.exists(archive_path):
                os.remove(archive_path)  # Cleanup archive
        print("✅ Java 21 installed locally!")

    def select_skin(self):
        """Allow the user to select and apply a custom skin PNG file."""
        file_path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
        if file_path:
            skin_dest = os.path.join(CTLAUNCHER_DIR, "skins")
            os.makedirs(skin_dest, exist_ok=True)
            try:
                shutil.copy(file_path, os.path.join(skin_dest, "custom_skin.png"))
                messagebox.showinfo("CTLauncher", "Skin applied successfully! Note: This may require a mod to apply in-game.")
            except Exception as e:
                print(f"❌ Failed to apply skin: {e}")
                messagebox.showerror("CTLauncher Error", f"Failed to apply skin: {str(e)}.\n\nPlease check file permissions or try another file.")

    @staticmethod
    def verify_file(file_path, expected_sha1):
        """Verify the SHA1 checksum of a file."""
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha1(f.read()).hexdigest()
            return file_hash == expected_sha1
        except Exception as e:
            print(f"❌ Failed to verify file {file_path}: {e}")
            return False

    def download_assets(self, version_data):
        """Download asset index and missing asset objects."""
        try:
            asset_index = version_data.get("assetIndex", {})
            if not asset_index:
                print("⚠️ No asset index found, skipping assets.")
                return True

            index_url = asset_index["url"]
            index_hash = asset_index["sha1"]
            index_path = os.path.join(ASSETS_DIR, "indexes", f"{asset_index['id']}.json")
            os.makedirs(os.path.dirname(index_path), exist_ok=True)

            if not os.path.exists(index_path) or not self.verify_file(index_path, index_hash):
                if not self.download_with_retry(index_url, index_path, "asset index", index_hash):
                    return False

            with open(index_path, "r") as f:
                assets = json.load(f)

            objects_dir = os.path.join(ASSETS_DIR, "objects")
            os.makedirs(objects_dir, exist_ok=True)

            total_objects = len(assets["objects"])
            downloaded = 0
            for obj_name, obj_info in assets["objects"].items():
                obj_hash = obj_info["hash"]
                obj_path = os.path.join(objects_dir, obj_hash[:2], obj_hash)
                os.makedirs(os.path.dirname(obj_path), exist_ok=True)

                if not os.path.exists(obj_path) or not self.verify_file(obj_path, obj_hash):
                    obj_url = f"https://resources.download.minecraft.net/{obj_hash[:2]}/{obj_hash}"
                    if not self.download_with_retry(obj_url, obj_path, f"asset {obj_name}", obj_hash):
                        print(f"⚠️ Failed to download asset {obj_name}, continuing...")
                        continue
                    downloaded += 1
                    print(f"📥 Assets: {downloaded}/{total_objects} downloaded")

            print(f"✅ Assets downloaded: {downloaded}/{total_objects}")
            return True
        except Exception as e:
            print(f"❌ Failed to download assets: {e}")
            return False

    def download_version_files(self, version_id, version_url):
        """Download the version JSON, JAR, libraries, natives, and assets with checksum verification."""
        print(f"⬇️ Downloading version files for {version_id}...")
        version_dir = os.path.join(VERSIONS_DIR, version_id)
        os.makedirs(version_dir, exist_ok=True)
        
        # Download version JSON
        version_json_path = os.path.join(version_dir, f"{version_id}.json")
        if not self.download_with_retry(version_url, version_json_path, f"{version_id} JSON"):
            messagebox.showerror("CTLauncher Error", f"Failed to download version {version_id} JSON.")
            return False
        
        try:
            with open(version_json_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to read version JSON: {e}")
            messagebox.showerror("CTLauncher Error", f"Cannot read version {version_id} JSON.")
            return False
        
        # Download assets
        if not self.download_assets(data):
            messagebox.showwarning("CTLauncher Warning", "Failed to download some assets. Game may have missing textures/sounds.")
        
        # Download client JAR
        try:
            jar_url = data["downloads"]["client"]["url"]
            jar_path = os.path.join(version_dir, f"{version_id}.jar")
            expected_sha1 = data["downloads"]["client"]["sha1"]
            
            if not os.path.exists(jar_path) or not CTLauncher.verify_file(jar_path, expected_sha1):
                if not self.download_with_retry(jar_url, jar_path, f"{version_id} JAR", expected_sha1):
                    messagebox.showerror("CTLauncher Error", f"Failed to download version {version_id} JAR.")
                    return False
        except KeyError as e:
            print(f"❌ Missing client JAR info in JSON: {e}")
            messagebox.showerror("CTLauncher Error", f"Version {version_id} is missing client JAR information.")
            return False
        
        current_os = platform.system().lower()
        if current_os == "darwin":
            current_os = "osx"
        
        libraries_dir = os.path.join(CTLAUNCHER_DIR, "libraries")
        os.makedirs(libraries_dir, exist_ok=True)
        
        natives_dir = os.path.join(version_dir, "natives")
        os.makedirs(natives_dir, exist_ok=True)
        
        # Download libraries with improved error handling
        for lib in data.get("libraries", []):
            if self.is_library_allowed(lib, current_os):
                # Download artifact
                if "downloads" in lib and "artifact" in lib["downloads"]:
                    lib_url = lib["downloads"]["artifact"]["url"]
                    lib_path = os.path.join(libraries_dir, lib["downloads"]["artifact"]["path"])
                    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
                    expected_sha1 = lib["downloads"]["artifact"]["sha1"]
                    
                    if not os.path.exists(lib_path) or not CTLauncher.verify_file(lib_path, expected_sha1):
                        lib_name = lib.get('name', 'unknown')
                        if not self.download_with_retry(lib_url, lib_path, f"library {lib_name}", expected_sha1):
                            print(f"⚠️ Warning: Failed to download library {lib_name}, continuing...")
                            continue
                
                # Download natives
                if "natives" in lib and current_os in lib["natives"]:
                    classifier = lib["natives"][current_os]
                    if "downloads" in lib and "classifiers" in lib["downloads"] and classifier in lib["downloads"]["classifiers"]:
                        native_url = lib["downloads"]["classifiers"][classifier]["url"]
                        native_path = os.path.join(natives_dir, f"{classifier}.jar")
                        expected_sha1 = lib["downloads"]["classifiers"][classifier]["sha1"]
                        
                        if not os.path.exists(native_path) or not CTLauncher.verify_file(native_path, expected_sha1):
                            lib_name = lib.get('name', 'unknown')
                            if not self.download_with_retry(native_url, native_path, f"native {lib_name}", expected_sha1):
                                print(f"⚠️ Warning: Failed to download native {lib_name}, continuing...")
                                continue
                        
                        # Extract natives
                        try:
                            with zipfile.ZipFile(native_path, "r") as zip_ref:
                                zip_ref.extractall(natives_dir)
                            os.remove(native_path)
                        except Exception as e:
                            print(f"⚠️ Warning: Failed to extract native {lib.get('name', 'unknown')}: {e}")
        
        print("✅ Download complete! Ready to play!")
        return True

    def create_game_directories(self):
        """Create all necessary game directories and initialize logs."""
        os.makedirs(os.path.join(CTLAUNCHER_DIR, "logs"), exist_ok=True)
        os.makedirs(os.path.join(CTLAUNCHER_DIR, "crash-reports"), exist_ok=True)
        os.makedirs(ASSETS_DIR, exist_ok=True)
        os.makedirs(os.path.join(ASSETS_DIR, "indexes"), exist_ok=True)
        os.makedirs(os.path.join(ASSETS_DIR, "objects"), exist_ok=True)
        os.makedirs(os.path.join(CTLAUNCHER_DIR, "saves"), exist_ok=True)
        os.makedirs(os.path.join(CTLAUNCHER_DIR, "resourcepacks"), exist_ok=True)
        os.makedirs(os.path.join(CTLAUNCHER_DIR, "skins"), exist_ok=True)

        # Initialize logs/latest.log to avoid access denied
        log_path = os.path.join(CTLAUNCHER_DIR, "logs", "latest.log")
        if not os.path.exists(log_path):
            with open(log_path, "w") as f:
                f.write("")  # Empty file
        print("📁 Game directories and logs initialized.")

    def modify_options_txt(self, target_fps=60):
        """Modify options.txt to set maxFps and disable vsync, preserving other settings."""
        options_path = os.path.join(CTLAUNCHER_DIR, "options.txt")
        options = {}
        if os.path.exists(options_path):
            try:
                with open(options_path, "r") as f:
                    for line in f:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            options[parts[0]] = parts[1]
            except Exception as e:
                print(f"⚠️ Could not read options.txt: {e}")
        
        options['maxFps'] = str(target_fps)
        options['enableVsync'] = 'false'
        
        try:
            os.makedirs(os.path.dirname(options_path), exist_ok=True)
            with open(options_path, "w") as f:
                for key, value in options.items():
                    f.write(f"{key}:{value}\n")
            print(f"⚙️ Set maxFps to {target_fps} and disabled vsync!")
        except Exception as e:
            print(f"❌ Failed to write options.txt: {e}")

    def is_library_allowed(self, lib, current_os):
        """Check if a library is allowed on the current OS based on its rules."""
        if "rules" not in lib:
            return True
        allowed = False
        for rule in lib["rules"]:
            if rule["action"] == "allow":
                if "os" not in rule or (isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os):
                    allowed = True
            elif rule["action"] == "disallow":
                if "os" in rule and isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os:
                    allowed = False
        return allowed

    def evaluate_rules(self, rules, current_os):
        """Evaluate argument rules based on the current OS, ignoring feature-based rules."""
        if not rules:
            return True
        allowed = False
        for rule in rules:
            if "features" in rule:
                continue
            if rule["action"] == "allow":
                if "os" not in rule or (isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os):
                    allowed = True
            elif rule["action"] == "disallow":
                if "os" in rule and isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os:
                    allowed = False
        return allowed

    def generate_offline_uuid(self, username):
        """Generate a UUID for offline mode based on the username."""
        offline_prefix = "OfflinePlayer:"
        hash_value = hashlib.md5((offline_prefix + username).encode('utf-8')).hexdigest()
        uuid_str = f"{hash_value[:8]}-{hash_value[8:12]}-{hash_value[12:16]}-{hash_value[16:20]}-{hash_value[20:32]}"
        return uuid_str

    def build_launch_command(self, version, username, ram, natives_dir):
        """Construct the command to launch Minecraft."""
        version_dir = os.path.join(VERSIONS_DIR, version)
        json_path = os.path.join(version_dir, f"{version}.json")
        try:
            with open(json_path, "r") as f:
                version_data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to read version JSON: {e}")
            messagebox.showerror("CTLauncher Error", f"Cannot read version {version} JSON.")
            return []
        
        current_os = platform.system().lower()
        if current_os == "darwin":
            current_os = "osx"
        
        main_class = version_data.get("mainClass", "net.minecraft.client.main.Main")
        libraries_dir = os.path.join(CTLAUNCHER_DIR, "libraries")
        jar_path = os.path.join(version_dir, f"{version}.jar")
        
        classpath = [jar_path]
        for lib in version_data.get("libraries", []):
            if "downloads" in lib and "artifact" in lib["downloads"]:
                lib_path = os.path.join(libraries_dir, lib["downloads"]["artifact"]["path"])
                if os.path.exists(lib_path):
                    classpath.append(lib_path)
        
        classpath_str = ";".join(classpath) if platform.system() == "Windows" else ":".join(classpath)
        
        java_bin = "java"
        if not self.is_java_installed():
            java_bin = os.path.join(JAVA_DIR, self.get_local_java_dir(), "bin", "java.exe" if platform.system() == "Windows" else "java")
            if not os.path.exists(java_bin):
                print(f"❌ Java binary not found at {java_bin}")
                messagebox.showerror("CTLauncher Error", "Java binary not found. Please install Java manually.")
                return []
        
        command = [java_bin, f"-Xmx{ram}G"]
        
        jvm_args = []
        if "arguments" in version_data and "jvm" in version_data["arguments"]:
            for arg in version_data["arguments"]["jvm"]:
                if isinstance(arg, str):
                    jvm_args.append(arg)
                elif isinstance(arg, dict) and "rules" in arg and "value" in arg:
                    if self.evaluate_rules(arg["rules"], current_os):
                        if isinstance(arg["value"], list):
                            jvm_args.extend(arg["value"])
                        else:
                            jvm_args.append(arg["value"])
        
        if platform.system() == "Darwin" and "-XstartOnFirstThread" not in jvm_args:
            jvm_args.append("-XstartOnFirstThread")
        
        if not any("-Djava.library.path=" in arg for arg in jvm_args):
            jvm_args.append(f"-Djava.library.path={natives_dir}")
        
        command.extend(jvm_args)
        
        game_args = []
        if "arguments" in version_data and "game" in version_data["arguments"]:
            for arg in version_data["arguments"]["game"]:
                if isinstance(arg, str):
                    game_args.append(arg)
                elif isinstance(arg, dict) and "rules" in arg and "value" in arg:
                    if self.evaluate_rules(arg["rules"], current_os):
                        if isinstance(arg["value"], list):
                            game_args.extend(arg["value"])
                        else:
                            game_args.append(arg["value"])
        elif "minecraftArguments" in version_data:
            game_args = version_data["minecraftArguments"].split()
        
        uuid = self.generate_offline_uuid(username)
        replacements = {
            "${auth_player_name}": username,
            "${version_name}": version,
            "${game_directory}": CTLAUNCHER_DIR,
            "${assets_root}": ASSETS_DIR,
            "${assets_index_name}": version_data.get("assetIndex", {}).get("id", "legacy"),
            "${auth_uuid}": uuid,
            "${auth_access_token}": "0",
            "${user_type}": "legacy",
            "${version_type}": version_data.get("type", "release"),
            "${user_properties}": "{}",
            "${quickPlayRealms}": "",
            "${natives_directory}": natives_dir,  # FIXED: Add natives_directory replacement
            "${launcher_name}": "CTLauncher",  # FIXED: Resolve launcher placeholders
            "${launcher_version}": "1.0",
            "${clientid}": "ctlauncher-offline"  # FIXED: Dummy client ID for offline
        }
        
        def replace_placeholders(arg):
            for key, value in replacements.items():
                arg = arg.replace(key, value)
            return arg
        
        game_args = [replace_placeholders(arg) for arg in game_args]
        jvm_args = [replace_placeholders(arg) for arg in jvm_args]
        
        command.extend(["-cp", classpath_str, main_class] + game_args)
        return command

    def validate_username(self, username):
        """Validate the username to ensure it's non-empty and alphanumeric."""
        if not username or not re.match(r'^[a-zA-Z0-9_]+$', username):
            return "Player"
        return username

    def prepare_and_launch(self):
        """Wrapper function to handle setup before launching."""
        self.create_game_directories()  # FIXED: Create dirs and init logs
        self.install_java_if_needed()
        self.modify_options_txt(target_fps=60)
        self.download_and_launch()

    def download_and_launch(self):
        """Handle the download and launch process."""
        version = self.version_combo.get()
        if not version:
            messagebox.showerror("CTLauncher Error", "No version selected.")
            return
        username = self.validate_username(self.username_input.get())
        ram = int(self.ram_scale.get())
        version_url = self.versions.get(version)
        if not version_url:
            messagebox.showerror("CTLauncher Error", f"Version {version} URL not found.")
            return
        version_dir = os.path.join(VERSIONS_DIR, version)
        natives_dir = os.path.join(version_dir, "natives")
        if not self.download_version_files(version, version_url):
            return
        launch_cmd = self.build_launch_command(version, username, ram, natives_dir)  # FIXED: Pass natives_dir
        if not launch_cmd:
            return
        print("🚀 Launching Minecraft with:", " ".join(launch_cmd))
        print("Have fun gaming!")
        try:
            subprocess.Popen(launch_cmd)
        except Exception as e:
            print(f"❌ Failed to launch Minecraft: {e}")
            messagebox.showerror("CTLauncher Error", f"Failed to launch Minecraft: {str(e)}.\n\nPlease check your settings or Java installation.")

if __name__ == "__main__":
    print("CTLauncher v1.0 - Initializing...")
    app = CTLauncher()
    app.mainloop()
