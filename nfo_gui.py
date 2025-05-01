import sys
import traceback
import tkinter.font as tkfont
from tkinter import filedialog, scrolledtext, messagebox, simpledialog
import json
import os
import threading
import webbrowser
from discogs_oauth import oauth_login
import tkinter.ttk as ttk
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import tkinter as tk
import sys
from discogs2nfo_batch import search_discogs_release
from musicbrainz_search import get_release_by_id as mb_get_release_by_id
import shutil
import re
import cloudscraper
from nfo_backend import safe_join_path

try:
    import os
    import tkinter as tk
    import threading
    from nfo_backend import process_albums_gui
except Exception as e:
    print("Import failed:", e)
    traceback.print_exc()
    sys.exit(1)

SESSION_FILE = os.path.join(os.path.expanduser("~"), ".ripzbuddy_session.json")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".ripzbuddy_settings.json")

class RipzBuddyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RipzBuddy - GUI Edition [UPDATED]")
        self.settings = {}
        self.root_dir = tk.StringVar()
        self.ripper_name = tk.StringVar()
        self.release_group = tk.StringVar(value="TSH")
        self.ascii_art = tk.StringVar()
        self.add_presents = tk.BooleanVar()
        self.presents_group = tk.StringVar()
        self.geometry("1400x900")
        self.resizable(True, True)
        self.session = self.load_session()
        # --- Ensure Discogs token is loaded from settings at startup ---
        self.discogs_token = self.settings.get('discogs_token', '')
        if 'template_path' in self.settings:
            self.load_template(self.settings['template_path'])
        self.create_topbar(self)
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)
        main_frame = tk.Frame(notebook)
        notebook.add(main_frame, text="Main")
        main_hframe = tk.Frame(main_frame)
        main_hframe.pack(fill=tk.BOTH, expand=True)
        main_hframe.grid_rowconfigure(0, weight=1)
        main_hframe.grid_columnconfigure(0, weight=2)  
        main_hframe.grid_columnconfigure(1, weight=3)  
        left_vframe = tk.Frame(main_hframe)
        left_vframe.grid(row=0, column=0, sticky="nsew")
        left_vframe.grid_rowconfigure(0, weight=0)
        left_vframe.grid_rowconfigure(1, weight=1)
        left_vframe.grid_rowconfigure(2, weight=0)
        left_vframe.grid_columnconfigure(0, weight=1)
        content_frame = tk.Frame(left_vframe)
        content_frame.grid(row=0, column=0, sticky="ew")
        ascii_frame = tk.LabelFrame(content_frame, text="Custom ASCII Art (appears at top of NFO)", padx=5, pady=5)
        ascii_frame.pack(fill=tk.BOTH, padx=10, pady=10)
        ascii_font = ("Consolas", 10)
        try:
            tkfont.nametofont("TkFixedFont").configure(family="Consolas", size=10)
        except Exception:
            ascii_font = ("Courier New", 10)
        self.ascii_text = scrolledtext.ScrolledText(ascii_frame, height=10, width=80, font=ascii_font)
        self.ascii_text.pack(fill=tk.BOTH, expand=True)
        tk.Button(ascii_frame, text="Load ASCII Art from File", command=self.load_ascii_file).pack(anchor="e", pady=(5,0))
        meta_frame = tk.Frame(content_frame)
        meta_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        tk.Label(meta_frame, text="Ripper Name:").pack(side=tk.LEFT)
        tk.Entry(meta_frame, textvariable=self.ripper_name, width=20).pack(side=tk.LEFT, padx=(5, 15))
        tk.Label(meta_frame, text="Release Group:").pack(side=tk.LEFT)
        tk.Entry(meta_frame, textvariable=self.release_group, width=10).pack(side=tk.LEFT, padx=(5, 0))
        presents_frame = tk.Frame(content_frame)
        presents_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        tk.Checkbutton(presents_frame, text="Add 'Presents' line to NFO", variable=self.add_presents, command=self.toggle_presents).pack(side=tk.LEFT)
        tk.Label(presents_frame, text="Group Name:").pack(side=tk.LEFT, padx=(15,0))
        self.presents_entry = tk.Entry(presents_frame, textvariable=self.presents_group, width=20, state="disabled")
        self.presents_entry.pack(side=tk.LEFT, padx=(5,0))
        esw_frame = tk.LabelFrame(content_frame, text="Equipment Used & Software Used", padx=5, pady=5)
        esw_frame.pack(fill=tk.BOTH, padx=10, pady=(0,10))
        tk.Label(esw_frame, text="Equipment Used:").grid(row=0, column=0, sticky="nw")
        self.equipment_text = scrolledtext.ScrolledText(esw_frame, height=2, width=30, font=("Arial", 10))
        self.equipment_text.grid(row=0, column=1, padx=(5,15), pady=2)
        tk.Label(esw_frame, text="Software Used:").grid(row=0, column=2, sticky="nw")
        self.software_text = scrolledtext.ScrolledText(esw_frame, height=2, width=30, font=("Arial", 10))
        self.software_text.grid(row=0, column=3, padx=(5,0), pady=2)
        esw_frame.grid_columnconfigure(1, weight=1)
        esw_frame.grid_columnconfigure(3, weight=1)
        self.rip_mode = tk.StringVar(value="vinyl")
        mode_frame = tk.Frame(content_frame)
        mode_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        tk.Label(mode_frame, text="Processing Mode:").pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="Vinyl Rip (rename folders/tracks)", variable=self.rip_mode, value="vinyl").pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(mode_frame, text="CD FLAC Rip (keep names)", variable=self.rip_mode, value="cd").pack(side=tk.LEFT, padx=10)
        manual_frame = tk.LabelFrame(content_frame, text="Manual Release Search", padx=5, pady=5)
        manual_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Label(manual_frame, text="Artist:").pack(side=tk.LEFT)
        self.manual_artist = tk.StringVar()
        tk.Entry(manual_frame, textvariable=self.manual_artist, width=20).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(manual_frame, text="Album:").pack(side=tk.LEFT)
        self.manual_album = tk.StringVar()
        tk.Entry(manual_frame, textvariable=self.manual_album, width=25).pack(side=tk.LEFT, padx=(5, 10))
        tk.Button(manual_frame, text="Search", command=self.manual_release_search).pack(side=tk.LEFT, padx=(5, 0))
        browse_btn = tk.Button(content_frame, text="Manual Discogs/MusicBrainz Search", command=self.open_browser_window)
        browse_btn.pack(pady=5)
        paste_btn = tk.Button(content_frame, text="Paste Release URL to Fetch Metadata", command=self.paste_release_url)
        paste_btn.pack(pady=5)
        log_frame = tk.LabelFrame(left_vframe, text="Log / Progress", padx=5, pady=5)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, width=40, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        bottom_btn_frame = tk.Frame(left_vframe, bg="#f0f0f0")
        bottom_btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 10), padx=10)
        bottom_btn_frame.columnconfigure((0,1,2), weight=1)  # 3 columns now
        btn_font = ("Arial", 11)
        batch_btn = tk.Button(bottom_btn_frame, text="Start Batch Processing", command=self.start_batch_processing, font=btn_font, relief=tk.RAISED, bd=2, height=1, padx=10, pady=4)
        batch_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        save_btn = tk.Button(bottom_btn_frame, text="Save Template", command=self.save_template, font=btn_font, relief=tk.RAISED, bd=2, height=1, padx=10, pady=4)
        save_btn.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        load_btn = tk.Button(bottom_btn_frame, text="Load Template", command=self.load_template, font=btn_font, relief=tk.RAISED, bd=2, height=1, padx=10, pady=4)
        load_btn.grid(row=0, column=2, sticky="ew")
        right_nfo_frame = tk.Frame(main_hframe)
        right_nfo_frame.grid(row=0, column=1, sticky="nsew", padx=(10,10), pady=10)
        nfo_frame = tk.LabelFrame(right_nfo_frame, text="NFO Preview", padx=5, pady=5)
        nfo_frame.pack(fill=tk.BOTH, expand=True)
        self.nfo_preview_text = scrolledtext.ScrolledText(nfo_frame, height=40, width=120, state='disabled', font=("Consolas", 9))
        self.nfo_preview_text.pack(fill=tk.BOTH, expand=True)
        xscroll = tk.Scrollbar(nfo_frame, orient="horizontal", command=self.nfo_preview_text.xview)
        xscroll.pack(side="bottom", fill="x")
        yscroll = tk.Scrollbar(nfo_frame, orient="vertical", command=self.nfo_preview_text.yview)
        yscroll.pack(side="right", fill="y")
        self.nfo_preview_text.config(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        about_frame = tk.Frame(notebook)
        notebook.add(about_frame, text="About")
        about_title = tk.Label(about_frame, text="RipzBuddy Pro v1.0.0", font=("Segoe UI", 22, "bold"), fg="#1a237e", anchor="center", justify="center")
        about_title.pack(pady=(40, 10), anchor="center")
        about_subtitle = tk.Label(about_frame, text="Next-Gen NFO & Metadata Automation for Music Collectors", font=("Segoe UI", 13, "italic"), fg="#3949ab", anchor="center", justify="center")
        about_subtitle.pack(pady=(0, 20), anchor="center")
        about_text = tk.Label(
            about_frame,
            text=(
                "RipzBuddy Pro automates NFO, playlist, and checksum creation for your FLAC music collections.\n\n"
                "Key Features:\n"
                "• Smart NFO tracklist: VA/single-artist, multi-disc, proper numbering\n"
                "• Capitalized FLAC filenames\n"
                "• CUE, M3U, SFV, and log file support\n"
                "• Discogs metadata integration\n"
                "• Batch folder processing\n"
                "• Robust error handling & logs\n"
                "• Customizable ASCII art/release group template\n\n"
                "Developed by Cobus Galvin (Galvitech).\n"
                "Support: cobusgalvin@gmail.com | github.com/ElectronicPunkZA\n\n"
                "Powered by Python, Tkinter, and open music APIs.\n\n"
                "Version: 1.0.0  |  License: MIT"
            ),
            font=("Segoe UI", 11), fg="#222", justify="center", anchor="center"
        )
        about_text.pack(padx=30, pady=(0, 20), anchor="center")

        tutorial_frame = tk.Frame(notebook)
        notebook.add(tutorial_frame, text="Tutorial")
        tutorial_title = tk.Label(tutorial_frame, text="Quick Start Tutorial", font=("Segoe UI", 16, "bold"), fg="#2c3e50", anchor="center", justify="center")
        tutorial_title.pack(pady=(30, 10), anchor="center")
        tutorial_text = tk.Label(
            tutorial_frame,
            text=(
                "Step-by-step Quick Start:\n\n"
                "1. Create a start.bat file with the following content (in your app folder):\n"
                "   @echo off\n"
                "   python nfo_gui.py\n\n"
                "2. Run the start.bat file to launch the app.\n\n"
                "3. Fill in all relevant info:\n"
                "   • ASCII art for your release group\n"
                "   • Ripper name\n"
                "   • Release group name\n"
                "   • Group name\n"
                "   • Choose Vinyl or CD\n\n"
                "4. Go to your Discogs page, create a general use token, and copy it into the 'Discogs Token' field in the app.\n\n"
                "5. If happy with your settings, save your template anywhere on your system.\n\n"
                "6. To process a batch of releases:\n"
                "   • Click 'Start Batch Processing'\n"
                "   • Select your root folder containing all release folders\n"
                "   • Click Open\n\n"
                "7. The batch process will start, with a log showing all tasks being performed.\n\n"
                "That's it—enjoy your newly created releases!\n\n"
                "---\n"
                "Tips:\n"
                "• For CD rips, we recommend Exact Audio Copy (EAC) v1.8 or above for best results and log creation.\n"
                "• For multi-disc releases, keep all discs in the same folder (tracks 101, 201, etc.).\n"
                "• Create an id.tsh file with the Discogs release URL for best metadata.\n"
                "• Backup your results!\n"
                "• Need help? See About or contact support.\n\n"
                "Next Update: Even smarter auto id.tsh creation and more!"
            ),
            font=("Segoe UI", 11), fg="#222", justify="left", anchor="nw"
        )
        tutorial_text.pack(padx=30, pady=(0, 20), anchor="nw")
        self.bind_preview_updates()
        self.update_nfo_preview()

    def create_topbar(self, parent):
        topbar = tk.Frame(parent)
        topbar.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(topbar, text="Root Folder:").pack(side=tk.LEFT)
        root_entry = tk.Entry(topbar, textvariable=self.root_dir, width=40)
        root_entry.pack(side=tk.LEFT, padx=(5, 0))
        tk.Button(topbar, text="Browse Folder", command=self.browse_dir).pack(side=tk.LEFT, padx=(5, 15))
        tk.Label(topbar, text="Discogs Token:").pack(side=tk.LEFT)
        self.discogs_token_var = tk.StringVar(value=self.settings.get('discogs_token', ''))
        token_entry = tk.Entry(topbar, textvariable=self.discogs_token_var, width=35, show='*')
        token_entry.pack(side=tk.LEFT, padx=(5, 0))
        tk.Button(topbar, text="Save Token", command=self.save_discogs_token).pack(side=tk.LEFT, padx=(5, 0))
        tk.Button(topbar, text="Reset Template", command=self.reset_template).pack(side=tk.LEFT, padx=(15, 0))
        return topbar

    def save_discogs_token(self):
        """
        Save the Discogs token to settings and to disk.
        """
        token = self.discogs_token_var.get()
        self.settings['discogs_token'] = token
        self.discogs_token = token  # --- Keep in sync for runtime use ---
        try:
            import json
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            self.log("[OK] Discogs token saved.")
        except Exception as e:
            self.log(f"[ERROR] Failed to save token: {e}")

    def browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.root_dir.set(d)

    def load_ascii_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.ascii_text.delete("1.0", tk.END)
                    self.ascii_text.insert(tk.END, f.read())
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ASCII art: {e}")

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def toggle_presents(self):
        if self.add_presents.get():
            self.presents_entry.config(state="normal")
        else:
            self.presents_entry.config(state="disabled")
            self.presents_group.set("")

    def save_settings(self):
        import json
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f)

    def load_template(self):
        from tkinter import filedialog
        import json
        import os
        path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="Load Template")
        if not path or not os.path.exists(path):
            self.log(f"[ERROR] No template file selected or file does not exist: {path}")
            return
        with open(path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        self.apply_template(template_data)
        # --- Ensure Discogs token is refreshed from template/settings after loading a template ---
        self.discogs_token = self.settings.get('discogs_token', '')
        self.settings['template_path'] = path
        self.save_settings()
        self.log(f"[OK] Loaded template from {path}")

    def save_template(self):
        import json
        from tkinter import filedialog
        template_data = self.get_current_template()
        template_data['discogs_token'] = self.discogs_token_var.get()
        file_path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON Files', '*.json')])
        if not file_path:
            return
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2)
        self.settings['template_path'] = file_path
        self.save_settings()
        print(f"[DEBUG] Saved template to {file_path} and locked in.")

    def apply_template(self, template_data):
        if 'root_dir' in template_data:
            self.root_dir.set(template_data['root_dir'])
        if 'ripper_name' in template_data:
            self.ripper_name.set(template_data['ripper_name'])
        if 'release_group' in template_data:
            self.release_group.set(template_data['release_group'])
        if 'ascii_art' in template_data and hasattr(self, 'ascii_text'):
            self.ascii_text.delete("1.0", "end")
            self.ascii_text.insert("1.0", template_data['ascii_art'])
        if 'equipment' in template_data and hasattr(self, 'equipment_text'):
            self.equipment_text.delete("1.0", "end")
            self.equipment_text.insert("1.0", template_data['equipment'])
        if 'software' in template_data and hasattr(self, 'software_text'):
            self.software_text.delete("1.0", "end")
            self.software_text.insert("1.0", template_data['software'])
        if 'add_presents' in template_data:
            self.add_presents.set(template_data['add_presents'])
        if 'presents_group' in template_data:
            self.presents_group.set(template_data['presents_group'])
        if 'rip_mode' in template_data and hasattr(self, 'rip_mode'):
            self.rip_mode.set(template_data['rip_mode'])
        if 'discogs_token' in template_data:
            self.discogs_token_var.set(template_data['discogs_token'])
            self.settings['discogs_token'] = template_data['discogs_token']
            self.log("[OK] Discogs token loaded from template.")

    def start_single_processing(self):
        """
        Process the selected directory using the same logic as batch mode, but only for the current folder.
        """
        import os
        from nfo_backend import process_albums_gui
        folder = self.root_dir.get()
        if not folder:
            self.log("[ERROR] No root folder selected.")
            return
        # Use GUI field values for processing
        ascii_art = self.ascii_text.get("1.0", "end-1c") if hasattr(self, 'ascii_text') else ""
        ripper = self.ripper_name.get() if hasattr(self, 'ripper_name') else ""
        group = self.release_group.get() if hasattr(self, 'release_group') else ""
        equipment = self.equipment_text.get("1.0", "end-1c") if hasattr(self, 'equipment_text') else ""
        software = self.software_text.get("1.0", "end-1c") if hasattr(self, 'software_text') else ""
        presents_enabled = self.add_presents.get() if hasattr(self, 'add_presents') else False
        presents_group = self.presents_group.get() if hasattr(self, 'presents_group') else ""
        discogs_client = self.get_discogs_client()
        # Call the same backend as batch, but for just one folder
        process_albums_gui(
            folder, ascii_art, ripper, group, equipment, software,
            presents_enabled, presents_group, log_callback=self.log, cd_mode=False, discogs_client=discogs_client
        )

    def get_discogs_client(self):
        try:
            import discogs_client
            token = self.discogs_token_var.get() if hasattr(self, 'discogs_token_var') else self.settings.get('discogs_token', None)
            if token:
                return discogs_client.Client('RipzBuddy/1.0', user_token=token)
            else:
                return None
        except Exception as e:
            self.log(f"[ERROR] Could not initialize Discogs client: {e}")
            return None

    def start_batch_processing(self):
        """
        Batch mode: Process all album subfolders using robust, rule-compliant logic with detailed debug logging.
        """
        from tkinter import filedialog
        import threading
        batch_dir = filedialog.askdirectory(title="Select Batch Folder")
        if not batch_dir:
            self.log("[CANCELLED] No batch folder selected.")
            return
        def run_batch():
            try:
                template_json = self.get_current_template()
                group = self.release_group.get() if hasattr(self, 'release_group') else ""
                presents = self.presents_group.get() if hasattr(self, 'presents_group') else ""
                ascii_art = self.ascii_text.get("1.0", "end-1c") if hasattr(self, 'ascii_text') else ""
                ripper = self.ripper_name.get() if hasattr(self, 'ripper_name') else ""
                equipment = self.equipment_text.get("1.0", "end-1c") if hasattr(self, 'equipment_text') else ""
                software = self.software_text.get("1.0", "end-1c") if hasattr(self, 'software_text') else ""
                presents_enabled = self.add_presents.get() if hasattr(self, 'add_presents') else False
                # Discover all release folders in batch_dir
                folders = [os.path.join(batch_dir, f) for f in os.listdir(batch_dir) if os.path.isdir(os.path.join(batch_dir, f))]
                for folder in folders:
                    try:
                        self.log(f"[PROCESSING] {folder}")
                        # --- Begin robust, rule-compliant batch logic ---
                        import re
                        import shutil
                        from mutagen.flac import FLAC
                        def sanitize_filename(text):
                            return re.sub(r'[\\/:*?"<>|]', '', text)
                        def get_release_base_name(artist, album, year, group):
                            album_part = album.replace(' ', '_')
                            return f"{album_part}-FLAC-[{year}]-{group}"
                        def update_cue_file(cue_path, flac_files, encoding='utf-8'):
                            def read_cue_lines(cue_path):
                                try:
                                    with open(cue_path, encoding=encoding) as f:
                                        return f.readlines()
                                except UnicodeDecodeError:
                                    with open(cue_path, encoding='cp1252') as f:
                                        return f.readlines()
                            lines = read_cue_lines(cue_path)
                            new_lines = []
                            flac_idx = 0
                            for line in lines:
                                if line.strip().upper().startswith('FILE') and flac_idx < len(flac_files):
                                    new_file = flac_files[flac_idx]
                                    new_lines.append(f'FILE "{self.normalize_filename(new_file)}" WAVE\r\n')
                                    flac_idx += 1
                                else:
                                    new_lines.append(self.normalize_filename(line.rstrip('\r\n')) + '\r\n')
                            shutil.copy2(cue_path, cue_path + '.bak')
                            with open(cue_path, 'w', encoding='cp1252', newline='') as f:
                                f.writelines(new_lines)
                            self.log(f"[OK] Updated cue: {cue_path}")
                            # Validate CUE: check all FILE lines exist
                            missing_files = []
                            for l in new_lines:
                                if l.strip().upper().startswith('FILE'):
                                    fname = l.split('"')[1]
                                    if not os.path.exists(os.path.join(os.path.dirname(cue_path), fname)):
                                        missing_files.append(fname)
                            if missing_files:
                                self.log(f"[ERROR] CUE references missing files: {missing_files}")
                            else:
                                # Clean up .bak if all is well
                                if os.path.exists(cue_path + '.bak'):
                                    os.remove(cue_path + '.bak')
                        def generate_tracklist(flac_info, various=True):
                            lines = []
                            multidisc = any(entry[0] > 1 for entry in flac_info if len(entry) >= 2)
                            for entry in flac_info:
                                # Support both old (5-tuple) and new (7-tuple) formats
                                if len(entry) == 5:
                                    disc, track, artist, title, flac = entry
                                else:
                                    disc, track, track_str, artist, title, old_flac, new_flac = entry
                                if multidisc:
                                    track_num = disc * 100 + track
                                    num_str = f"{track_num:03d}"
                                else:
                                    num_str = f"{track:02d}"
                                if various:
                                    lines.append(f"{num_str}. {artist} - {title}")
                                else:
                                    lines.append(f"{num_str}. {title}")
                            return '\n'.join(lines)
                        # Gather FLAC info
                        flacs = sorted([f for f in os.listdir(folder) if f.lower().endswith('.flac')])
                        flac_info = []
                        year = None
                        album = None
                        album_artist = artist = "VA"
                        for flac in flacs:
                            src_path = os.path.join(folder, flac)
                            try:
                                audio = FLAC(src_path)
                                discnumber = int(audio.get('discnumber', [1])[0])
                                tracknumber = int(audio.get('tracknumber', [1])[0])
                                track_artist = audio.get('artist', ["Unknown Artist"])[0]
                                title = audio.get('title', ["Unknown Title"])[0]
                                if not year:
                                    year = audio.get('date', [None])[0]
                                if not album:
                                    album = audio.get('album', [None])[0]
                                flac_info.append((discnumber, tracknumber, track_artist, title, flac))
                            except Exception as e:
                                self.log(f"[WARN] Could not read tags for {flac}: {e}")
                        flac_info.sort()
                        # --- Detect if multi-disc by number of CUEs ---
                        cues = [f for f in os.listdir(folder) if f.lower().endswith('.cue')]
                        if len(cues) == 1:
                            is_multidisc = False
                        else:
                            is_multidisc = len(cues) > 1
                        # --- Build FLAC rename and CUE FILE logic ---
                        flac_info = []
                        year = None
                        album = None
                        album_artist = artist = "VA"
                        for flac in flacs:
                            src_path = os.path.join(folder, flac)
                            try:
                                audio = FLAC(src_path)
                                discnumber = int(audio.get('discnumber', [1])[0])
                                tracknumber = int(audio.get('tracknumber', [1])[0])
                                track_artist = audio.get('artist', ["Unknown Artist"])[0]
                                title = audio.get('title', ["Unknown Title"])[0]
                                if not year:
                                    year = audio.get('date', [None])[0]
                                if not album:
                                    album = audio.get('album', [None])[0]
                                # --- Track number logic ---
                                if is_multidisc:
                                    final_track_num = discnumber*100 + tracknumber
                                    track_str = f"{final_track_num:03d}"
                                else:
                                    track_str = f"{tracknumber:02d}"
                                new_flac = f"{track_str} - {track_artist.title()} - {title.title()}{os.path.splitext(flac)[1]}"
                                new_flac = self.normalize_filename(new_flac)
                                flac_info.append((discnumber, tracknumber, track_str, track_artist, title, flac, new_flac))
                            except Exception as e:
                                self.log(f"[WARN] Could not read tags for {flac}: {e}")
                        flac_info.sort()
                        # --- Two-Phase Rename: Phase 1, check for collisions and prepare temp names ---
                        dst_map = {}
                        temp_map = {}
                        temp_suffix = ".__tmp__"
                        for disc, track, track_str, track_artist, title, old_flac, new_flac in flac_info:
                            dst = os.path.join(folder, new_flac)
                            dst_map.setdefault(dst, []).append(old_flac)
                        # --- Detect and log collisions ---
                        collision_found = False
                        for dst, srcs in dst_map.items():
                            if len(srcs) > 1:
                                collision_found = True
                                self.log(f"[COLLISION] Destination '{dst}' would be created from multiple sources: {srcs}. Skipping all these renames!")
                        if collision_found:
                            self.log("[ABORT] Collisions detected. No files will be renamed. Fix metadata and retry.")
                            return
                        # --- Phase 1: Rename all sources to unique temp names ---
                        for disc, track, track_str, track_artist, title, old_flac, new_flac in flac_info:
                            src = os.path.join(folder, old_flac)
                            temp = src + temp_suffix
                            temp_map[src] = temp
                            if os.path.exists(src):
                                try:
                                    os.rename(src, temp)
                                    self.log(f"[TMP] Renamed {src} -> {temp}")
                                except Exception as e:
                                    self.log(f"[ERROR] Failed temp rename {src} -> {temp}: {e}")
                        # --- Phase 2: Rename all temp files to their final destination ---
                        for disc, track, track_str, track_artist, title, old_flac, new_flac in flac_info:
                            temp = os.path.join(folder, old_flac) + temp_suffix
                            dst = os.path.join(folder, new_flac)
                            if os.path.exists(temp):
                                if os.path.exists(dst):
                                    os.remove(dst)
                                try:
                                    os.rename(temp, dst)
                                    self.log(f"[OK] Renamed {temp} -> {dst}")
                                except Exception as e:
                                    self.log(f"[ERROR] Failed to finalize rename {temp} -> {dst}: {e}")
                        # --- Update CUE FILE lines with correct FLAC names ---
                        self.log(f"[DEBUG] is_multidisc: {is_multidisc}, cues: {cues}")
                        for i, entry in enumerate(flac_info):
                            if len(entry) == 7:
                                disc, track, track_str, artist, title, old_flac, new_flac = entry
                                self.log(f"[DEBUG] FLAC[{i}]: disc={disc}, track={track}, track_str={track_str}, file={new_flac}")
                            else:
                                disc, track, artist, title, flac = entry
                                self.log(f"[DEBUG] FLAC[{i}]: disc={disc}, track={track}, file={flac}")
                        for cue in cues:
                            cue_path = os.path.join(folder, cue)
                            cue_disc = self.get_disc_from_cue(cue)
                            self.log(f"[DEBUG] cue_disc for {cue}: {cue_disc}")
                            # Only FLACs for this disc (if multidisc)
                            if is_multidisc:
                                disc_flacs = [nflac for (d, t, ts, a, ti, ofl, nflac) in flac_info if d == cue_disc]
                            else:
                                disc_flacs = [nflac for (d, t, ts, a, ti, ofl, nflac) in flac_info]
                            # --- Sanitize and normalize all disc_flacs before CUE writing ---
                            disc_flacs = [self.normalize_filename(f) for f in disc_flacs]
                            self.log(f"[DEBUG] disc_flacs for {cue}: {disc_flacs}")
                            self.update_cue_file(cue_path, disc_flacs)
                            # After CUE update, validate existence using normalization
                            cue_dir = os.path.dirname(cue_path)
                            files_in_dir = os.listdir(cue_dir)
                            norm_files_in_dir = [self.normalize_filename(f) for f in files_in_dir]
                            missing_files = []
                            for f in disc_flacs:
                                if self.normalize_filename(f) not in norm_files_in_dir:
                                    missing_files.append(f)
                            if missing_files:
                                self.log(f"[ERROR] CUE references missing files after normalization: {missing_files}")
                                self.log(f"[DEBUG] Directory listing: {files_in_dir}")
                            else:
                                self.log(f"[OK] All CUE references found in directory after normalization.")
                        # --- PATCH: Improved VA detection: VA if multiple unique artists ---
                        detected_artists = set(entry[3] for entry in flac_info if len(entry) == 7)
                        is_va = len(detected_artists) > 1
                        self.log(f"[DEBUG] Detected artists: {detected_artists}")
                        self.log(f"[DEBUG] is_va: {is_va}")
                        self.log(f"[DEBUG] Album: {album}, Year: {year}, Group: {group}")
                        # --- Naming logic for base_name (folder and file prefix) ---
                        if is_va:
                            base_name = f"VA-{album.replace(' ', '_')}-FLAC-[{year}]-{group}"
                        else:
                            main_artist = next(iter(detected_artists)) if detected_artists else "Unknown_Artist"
                            base_name = f"{main_artist.replace(' ', '_')}-{album.replace(' ', '_')}-FLAC-[{year}]-{group}"
                        self.log(f"[DEBUG] base_name: {base_name}")
                        # --- FLAC filename logic ---
                        for idx, entry in enumerate(flac_info):
                            if len(entry) == 7:
                                disc, track, track_str, artist, title, old_flac, new_flac = entry
                                ext = os.path.splitext(old_flac)[1]
                                if is_va:
                                    correct_name = f"{track_str} - {artist.title()} - {title.title()}{ext}"
                                else:
                                    correct_name = f"{track_str} - {title.title()}{ext}"
                                correct_name = self.normalize_filename(correct_name)
                                flac_info[idx] = (disc, track, track_str, artist, title, old_flac, correct_name)
                        # --- END PATCH ---
                        # --- Compose base_name for NFO, M3U, etc. ---
                        # base_name = get_release_base_name(album_artist, album, year, group)
                        # --- VA/Single-Artist logic for NFO ---
                        va_names = ["various", "various artists", "va"]
                        is_va = str(album_artist).strip().lower() in va_names
                        # --- Generate tracklist before using it in NFO content ---
                        tracklist = generate_tracklist(flac_info, various=is_va)
                        # --- Generate NFO ---
                        for ext in ['.nfo', '.m3u', '.sfv', '.log']:
                            target = safe_join_path(folder, base_name, ext)
                            if ext == '.nfo':
                                # --- Always define discogs_info before use ---
                                discogs_info = ""
                                id_tsh_path = os.path.join(folder, "id.tsh")
                                if os.path.exists(id_tsh_path):
                                    try:
                                        with open(id_tsh_path, encoding="utf-8") as f:
                                            discogs_info = f.read().strip()
                                    except Exception:
                                        with open(id_tsh_path, encoding='cp1252') as f:
                                            discogs_info = f.read().strip()
                                self.log(f"[DEBUG] id.tsh found: {id_tsh_path}")
                                self.log(f"[DEBUG] id.tsh content: {discogs_info}")
                                # --- Prefer Discogs API over Selenium for speed and reliability ---
                                import re
                                import requests
                                discogs_token = getattr(self, 'discogs_token', None)
                                release_id_match = re.search(r'/release/(\d+)', discogs_info)
                                release_id = release_id_match.group(1) if release_id_match else None
                                print(f"[DEBUG] Discogs token: {discogs_token[:6] + '...' if discogs_token else None}, release_id: {release_id}")
                                if not discogs_token or not release_id:
                                    print("[WARN] Discogs token or release_id not found. Falling back to old logic.")
                                    # fallback logic here
                                else:
                                    # fetch Discogs release as before
                                    self.fetch_discogs_release(release_id)
                                discogs_fields = {}
                                if release_id:
                                    api_url = f"https://api.discogs.com/releases/{release_id}"
                                    headers = {"Authorization": f"Discogs token={discogs_token}"}
                                    resp = requests.get(api_url, headers=headers)
                                    if resp.status_code == 200:
                                        data = resp.json()
                                        discogs_fields = {
                                            'Artist': data['artists'][0]['name'] if data.get('artists') else '',
                                            'Album': data.get('title', ''),
                                            'Year': str(data.get('year', '')) or '',
                                            'Country': data.get('country', ''),
                                            'Label': ', '.join([l['name'] for l in data.get('labels', [])]),
                                            'CatNo': ', '.join([l['catno'] for l in data.get('labels', []) if l.get('catno', '')]),
                                            'Genre': ', '.join(data.get('genres', [])),
                                            'Style': ', '.join(data.get('styles', [])),
                                            'Format': ', '.join([f['name'] for f in data.get('formats', [])]),
                                            'Notes': data.get('notes', ''),
                                            'Tracks': [t['title'] for t in data.get('tracklist', [])]
                                        }
                                        print(f"[DEBUG] Discogs fields for NFO: {discogs_fields}")
                                    else:
                                        print(f"[ERROR] Discogs API fetch failed: HTTP {resp.status_code}")
                                else:
                                    print("[WARN] Discogs token or release_id not found. Falling back to old logic.")
                                # Compose discogs_fields for NFO output
                                discogs_fields = {
                                    'Artist': discogs_fields.get('Artist', album_artist),
                                    'Album': discogs_fields.get('Album', album),
                                    'Year': discogs_fields.get('Year', year or ''),
                                    'Country': discogs_fields.get('Country', ''),
                                    'Label': discogs_fields.get('Label', ''),
                                    'CatNo': discogs_fields.get('CatNo', ''),
                                    'Genre': discogs_fields.get('Genre', ''),
                                    'Style': discogs_fields.get('Style', ''),
                                    'Format': discogs_fields.get('Format', ''),
                                    'Notes': discogs_fields.get('Notes', ''),
                                    'Tracks': discogs_fields.get('Tracks', [])
                                }
                                # Compose extended info block, only include non-empty fields, with Notes as a separate section
                                info_lines = []
                                for key in ['Artist', 'Album', 'Year', 'Country', 'Label', 'CatNo', 'Genre', 'Style', 'Format']:
                                    value = discogs_fields.get(key, '')
                                    if value:
                                        info_lines.append(f"{key:10}: {value}")
                                # Add Notes as a separate section if present
                                notes = discogs_fields.get('Notes', '')
                                if notes:
                                    info_lines.append("\nNotes:")
                                    info_lines.append(notes)
                                # Add Tracklist section using generate_tracklist output
                                info_lines.append("\nTracklist:")
                                info_lines.append(tracklist)
                                info_block = '\n'.join(info_lines) + '\n'
                                # Center and space the presents line
                                presents_line = self.center_line("-- *The Sound House Presents* --")
                                ascii_lines = ascii_art.splitlines()
                                ascii_with_gap = "\n"*2 + "\n".join(ascii_lines) + "\n\n" + presents_line + "\n\n"
                                # Compose NFO content
                                nfo_content = ascii_with_gap + info_block + "\nRipper      : " + ripper + "\nGroup       : " + group + "\nEquipment   : " + equipment + "\nSoftware    : " + software + "\n"
                                # Clean up extra blank lines
                                nfo_content = self.clean_nfo_spacing(nfo_content)
                                with open(target, 'w', encoding='utf-8') as f:
                                    f.write(nfo_content)
                                self.log(f"[OK] NFO written: {target}")
                            else:
                                files = [f for f in os.listdir(folder) if f.lower().endswith(ext)]
                                for f in files:
                                    src = os.path.join(folder, f)
                                    if src != target:
                                        if os.path.exists(target):
                                            os.remove(target)
                                        os.rename(src, target)
                                        self.log(f"[OK] Renamed {src} -> {target}")
                                if not files:
                                    open(target, 'a').close()
                        # --- Folder renaming logic ---
                        new_folder_name = base_name
                        parent_dir = os.path.dirname(folder)
                        new_folder_path = os.path.join(parent_dir, new_folder_name)
                        if os.path.abspath(folder) != os.path.abspath(new_folder_path):
                            try:
                                if not os.path.exists(new_folder_path):
                                    os.rename(folder, new_folder_path)
                                    self.log(f"[OK] Renamed folder: {folder} -> {new_folder_path}")
                                    folder = new_folder_path  # UPDATE folder variable so all further ops use the correct path!
                                else:
                                    self.log(f"[WARN] Target folder already exists: {new_folder_path}")
                                    folder = new_folder_path  # Even if it exists, use the new name for further processing
                            except Exception as e:
                                self.log(f"[ERROR] Failed to rename folder: {e}")
                        # --- After all renaming and CUE logic, generate M3U/SFV using shared backend utility ---
                        from nfo_backend import generate_m3u_and_sfv
                        # Use the final, renamed FLAC files for playlist/checksum
                        renamed_flacs = [entry[6] for entry in flac_info if len(entry) == 7]
                        base_name = None
                        if not os.path.exists(folder):
                            self.log(f"[ERROR] Folder missing after rename: {folder}. Skipping M3U/SFV generation.")
                            continue
                        for f in os.listdir(folder):
                            if f.lower().endswith('.nfo'):
                                base_name = os.path.splitext(f)[0]
                                break
                        if not base_name:
                            base_name = os.path.basename(folder)
                        if renamed_flacs:
                            generate_m3u_and_sfv(folder, renamed_flacs, base_name, self.log)
                        else:
                            self.log(f"[WARN] No FLAC files found for M3U/SFV generation in {folder}")
                        self.log(f"[DONE] Release processed: {new_folder_path if os.path.exists(new_folder_path) else folder}")
                    except Exception as e:
                        import traceback
                        self.log(f"[ERROR] Exception processing {folder}: {e}\n{traceback.format_exc()}")
            except Exception as e:
                import traceback
                self.log(f"[ERROR] Batch processing failed: {e}\n{traceback.format_exc()}")
        threading.Thread(target=run_batch, daemon=True).start()

    def fetch_release_from_url(self, url):
        # This should mimic the logic of your Paste Release URL button
        # For example, detect Discogs/MusicBrainz and call fetch_discogs_release, etc.
        if "discogs.com" in url.lower():
            release_id = url.rstrip('/').split('/')[-1].split('-')[0]
            self.fetch_discogs_release(release_id)
        elif "musicbrainz.org" in url.lower():
            release_id = url.rstrip('/').split('/')[-1]
            self.fetch_musicbrainz_release(release_id)
        else:
            self.log(f"[ERROR] Unsupported URL: {url}")

    def manual_release_search(self):
        artist = self.manual_artist.get().strip()
        album = self.manual_album.get().strip()
        if not artist and not album:
            messagebox.showwarning("Input Required", "Please enter at least an artist or album name to search.")
            return
        threading.Thread(target=self._manual_release_search_thread, args=(artist, album), daemon=True).start()

    def _manual_release_search_thread(self, artist, album):
        from nfo_backend import search_discogs_and_musicbrainz
        self.log("[Manual Search] Searching for: Artist='{}', Album='{}'".format(artist, album))
        try:
            matches = search_discogs_and_musicbrainz(artist, album)
            if not matches:
                self.log("[Manual Search] No matches found.")
                messagebox.showinfo("No Results", "No releases found for your search.")
                return
            idx = self.choose_metadata_dialog(matches)
            if idx is not None and 0 <= idx < len(matches):
                match = matches[idx]
                self.log(f"[Manual Search] Selected: {match.get('artist','?')} - {match.get('album','?')} ({match.get('year','?')})")
                messagebox.showinfo("Release Selected", f"You selected:\n{match.get('artist','?')} - {match.get('album','?')} ({match.get('year','?')})")
            else:
                self.log("[Manual Search] No selection made.")
        except Exception as e:
            self.log(f"[Manual Search] Search failed: {e}")
            messagebox.showerror("Search Error", str(e))

    def save_template_as(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="Save Template As")
        if path:
            print(f"[DEBUG] Saving template to: {path}")
            self.save_settings_to_path(path)
            self.last_template_path = path
            messagebox.showinfo("Template Saved", f"Template saved to {path}")

    def load_settings_from_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            self.root_dir.set(settings.get("root_dir", ""))
            self.ripper_name.set(settings.get("ripper_name", ""))
            self.release_group.set(settings.get("release_group", "TSH"))
            self.ascii_text.delete("1.0", tk.END)
            self.ascii_text.insert(tk.END, settings.get("ascii_art", ""))
            self.equipment_text.delete("1.0", tk.END)
            self.equipment_text.insert(tk.END, settings.get("equipment", ""))
            self.software_text.delete("1.0", tk.END)
            self.software_text.insert(tk.END, settings.get("software", ""))
            self.add_presents.set(settings.get("add_presents", False))
            self.presents_group.set(settings.get("presents_group", ""))
            self.rip_mode.set(settings.get("rip_mode", "vinyl"))
            if 'discogs_token' in settings:
                self.discogs_token_var.set(settings['discogs_token'])
                self.settings['discogs_token'] = settings['discogs_token']
                self.log("[OK] Discogs token loaded from template.")
        except Exception as e:
            print(f"[DEBUG] Failed to load template: {e}")

    def open_browser_window(self):
        webbrowser.open("https://www.discogs.com/search/")

    def paste_release_url(self):
        url = simpledialog.askstring("Paste Release URL", "Paste the full Discogs or MusicBrainz release URL:")
        if url:
            self.handle_release_url(url)

    def handle_release_url(self, url):
        if "discogs.com" in url.lower():
            release_id = url.rstrip('/').split('/')[-1].split('-')[0]
            print(f"[DEBUG] Pasted Discogs release ID: {release_id}")
            self.fetch_discogs_release(release_id)
        elif "musicbrainz.org" in url.lower():
            mbid = url.split("/release/")[-1].split("/")[0]
            print(f"[DEBUG] Pasted MusicBrainz MBID: {mbid}")
            self.fetch_musicbrainz_release(mbid)
        else:
            print("[ERROR] Not a recognized Discogs or MusicBrainz release URL.")

    def fetch_discogs_release(self, release_id):
        import discogs_client
        import re
        import cloudscraper
        from bs4 import BeautifulSoup
        token = getattr(self, 'discogs_token', None)
        print(f"[DEBUG] Discogs token used: {token[:6]}..." if token else "[DEBUG] No Discogs token present!")
        numeric_id_match = re.match(r'^(\d+)', str(release_id))
        if numeric_id_match:
            numeric_id = int(numeric_id_match.group(1))
        else:
            print(f"[ERROR] Could not extract numeric Discogs ID from: {release_id}")
            return
        # Try API first
        if token:
            print("[DEBUG] Using Discogs API (token present)...")
            try:
                d = discogs_client.Client('NFO-GUI/1.0', user_token=token)
                release = d.release(numeric_id)
                print(f"[DEBUG] Discogs release fetched: {release.title} by {[a.name for a in release.artists]}")
                # Extract all needed fields from API object
                discogs_fields = {
                    'Artist': getattr(release, 'artists', [])[0].name if getattr(release, 'artists', None) and len(getattr(release, 'artists', [])) > 0 else '',
                    'Album': getattr(release, 'title', ''),
                    'Year': str(getattr(release, 'year', '')) or '',
                    'Country': getattr(release, 'country', ''),
                    'Label': ', '.join([l.name for l in getattr(release, 'labels', [])]) if getattr(release, 'labels', None) else '',
                    'CatNo': ', '.join([getattr(l, 'catno', '') for l in getattr(release, 'labels', []) if getattr(l, 'catno', '')]),
                    'Genre': ', '.join(getattr(release, 'genres', [])) if getattr(release, 'genres', None) else '',
                    'Style': ', '.join(getattr(release, 'styles', [])) if getattr(release, 'styles', None) else '',
                    'Format': ', '.join([f.get('name', '') for f in getattr(release, 'formats', [])]) if getattr(release, 'formats', None) else '',
                    'Notes': getattr(release, 'notes', ''),
                    'Tracks': [t.title for t in getattr(release, 'tracklist', [])]
                }
                print(f"[DEBUG] Discogs fields for NFO: {discogs_fields}")
                self.last_discogs_fields = discogs_fields
                self.update_nfo_preview()
                return
            except Exception as e:
                print(f"[ERROR] Failed to fetch Discogs release (API): {e}")
                # If API fails, fall back to scraping
        print("[DEBUG] No token found or API failed, using cloudscraper fallback...")
        try:
            import undetected_chromedriver as uc
        except ImportError:
            print("[ERROR] undetected-chromedriver is not installed. Please run: pip install undetected-chromedriver")
            return None
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        chromedriver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chromedriver.exe')
        if not os.path.exists(chromedriver_path):
            chromedriver_path = 'chromedriver'  # fallback to PATH

        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1200,900')
        options.add_argument('--no-sandbox')
        options.add_argument('--lang=en-US')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        driver = uc.Chrome(executable_path=chromedriver_path, options=options)
        driver.set_page_load_timeout(30)
        try:
            driver.get(f"https://www.discogs.com/release/{release_id}")
            time.sleep(2)
            # Handle cookie consent (iframe or not)
            try:
                # Switch to cookie iframe if present
                iframes = driver.find_elements(By.TAG_NAME, 'iframe')
                for iframe in iframes:
                    if 'cookie' in iframe.get_attribute('src') or 'consent' in iframe.get_attribute('src'):
                        driver.switch_to.frame(iframe)
                        break
                # Try multiple selectors for accept button
                for sel in [
                    '[id^="onetrust-accept-btn-handler"]',
                    'button[title*="Accept"]',
                    'button[aria-label*="Accept"]',
                    'button[class*="accept"]',
                    'button[data-testid*="accept"]',
                    'button[mode="primary"]',
                    'button.cookie-btn',
                    'button:contains("Accept All Cookies")',
                ]:
                    try:
                        btn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                        )
                        btn.click()
                        time.sleep(1)
                        break
                    except Exception:
                        continue
                driver.switch_to.default_content()
            except Exception:
                pass  # No cookie banner
            # Wait for real Discogs content
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.release-title, .profile, .tracklist, h1'))
                )
            except Exception:
                pass
            html = driver.page_source
            with open('discogs_debug_rendered.html', 'w', encoding='utf-8') as f:
                f.write(html)
            # Debug: check if <body> and Discogs content is present
            if '<body' not in html or 'release-title' not in html:
                ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                debug_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'discogs_selenium_debug_{ts}')
                driver.save_screenshot(debug_base + '.png')
                with open(debug_base + '.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"[DEBUG] Saved Selenium debug screenshot and HTML to {debug_base}.png/.html")
            return html
        except Exception as e:
            print(f"[ERROR] undetected-chromedriver failed: {e}")
            return None
        finally:
            driver.quit()

    def fetch_musicbrainz_release(self, mbid):
        from musicbrainz_search import get_release_by_id as mb_get_release_by_id
        try:
            release = mb_get_release_by_id(mbid)
            print(f"[DEBUG] MusicBrainz release fetched: {release['album']} by {release['artist']}")
            self.populate_from_release(release)
        except Exception as e:
            print(f"[ERROR] Failed to fetch MusicBrainz release: {e}")

    def populate_from_release(self, release):
        self.current_release = None
        discogs_fields = {}
        if release.get('source', '').startswith('Discogs') and release.get('release_obj'):
            self.current_release = release['release_obj']
            rel = self.current_release
            discogs_fields = {
                'Artist': rel.artists[0].name if getattr(rel, 'artists', None) and len(rel.artists) > 0 else '',
                'Album': getattr(rel, 'title', ''),
                'Year': str(getattr(rel, 'year', '')) or '',
                'Country': getattr(rel, 'country', ''),
                'Label': ', '.join([l.name for l in getattr(rel, 'labels', [])]) if getattr(rel, 'labels', None) else '',
                'CatNo': ', '.join([getattr(l, 'catno', '') for l in getattr(rel, 'labels', []) if getattr(l, 'catno', '')]),
                'Genre': ', '.join(rel.genres) if getattr(rel, 'genres', None) else '',
                'Style': ', '.join(rel.styles) if getattr(rel, 'styles', None) else '',
                'Format': ', '.join([f.get('name', '') for f in getattr(rel, 'formats', [])]) if getattr(rel, 'formats', None) else '',
                'Notes': getattr(rel, 'notes', ''),
                'Tracks': [t.title for t in getattr(rel, 'tracklist', [])],
            }
            print(f"[DEBUG] Discogs fields for NFO: {discogs_fields}")
            self.last_discogs_fields = discogs_fields
            self.update_nfo_preview()

    def render_full_nfo(self):
        lines = []
        ascii_art = self.ascii_text.get("1.0", "end-1c").rstrip()
        ascii_lines = ascii_art.splitlines() if ascii_art else []
        if ascii_art:
            lines.extend(ascii_lines)
        # Add three blank lines after ASCII art before presents
        lines.extend(['', '', ''])
        # Centered Presents line
        presents = f"-- *{self.presents_group.get()} Presents* --" if self.add_presents.get() and self.presents_group.get() else ""
        if presents:
            width = max([len(line) for line in ascii_lines] + [70])
            centered = self.center_line(presents, width)
            lines.append(centered)
        if lines:
            lines.append("")  # Only one blank line after ascii/presents
        d = getattr(self, 'last_discogs_fields', {})
        ripper = self.ripper_name.get()
        group = self.release_group.get()
        equipment = self.equipment_text.get("1.0", "end-1c")
        software = self.software_text.get("1.0", "end-1c")
        artist = d.get('Artist', ripper)
        album = d.get('Album', self.manual_album.get() if hasattr(self, 'manual_album') else '')
        year = d.get('Year', '')
        country = d.get('Country', '')
        label = d.get('Label', '')
        catno = d.get('CatNo', '')
        genre = d.get('Genre', '')
        style = d.get('Style', '')
        format_ = d.get('Format', '')
        notes = d.get('Notes', '')
        tracks = d.get('Tracks', [])
        discogs_lines = []
        for key in ['Artist', 'Album', 'Year', 'Country', 'Label', 'CatNo', 'Genre', 'Style', 'Format']:
            value = d.get(key, '')
            if value:
                discogs_lines.append(f"{key:10}: {value}")
        # Add Notes as a separate section if present
        if notes:
            discogs_lines.append("\nNotes:")
            discogs_lines.append(notes)
        # Add Tracklist section using generate_tracklist output
        if tracks and isinstance(tracks, list) and any(tracks):
            discogs_lines.append("\nTracklist:")
            for idx, track in enumerate(tracks, 1):
                discogs_lines.append(f"  {idx:02d}. {track}")
        lines.extend(discogs_lines)
        lines.append(f"Ripper      : {ripper}")
        lines.append(f"Group       : {group}")
        lines.append(f"Equipment   : {equipment}")
        lines.append(f"Software    : {software}")
        return '\n'.join([l.rstrip() for l in lines if l.strip() != '' or l == ''])

    def update_nfo_preview(self, *_):
        nfo_text = self.render_full_nfo()
        self.nfo_preview_text.config(state='normal', wrap='none')
        self.nfo_preview_text.delete('1.0', 'end')
        self.nfo_preview_text.insert('end', nfo_text)
        self.nfo_preview_text.config(state='disabled')

    def bind_preview_updates(self):
        self.ascii_text.bind("<KeyRelease>", self.update_nfo_preview)
        self.ripper_name.trace_add('write', self.update_nfo_preview)
        self.release_group.trace_add('write', self.update_nfo_preview)
        self.equipment_text.bind("<KeyRelease>", self.update_nfo_preview)
        self.software_text.bind("<KeyRelease>", self.update_nfo_preview)
        self.add_presents.trace_add('write', self.update_nfo_preview)
        self.presents_group.trace_add('write', self.update_nfo_preview)
        if hasattr(self, 'manual_artist'):
            self.manual_artist.trace_add('write', self.update_nfo_preview)
        if hasattr(self, 'manual_album'):
            self.manual_album.trace_add('write', self.update_nfo_preview)
        if hasattr(self, 'tracks_text'):
            self.tracks_text.bind("<KeyRelease>", self.update_nfo_preview)

    def save_session(self):
        session = {
            "user": "current",
            "settings_file": SETTINGS_FILE
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session, f)

    def load_session(self):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                session = json.load(f)
            return session
        except Exception:
            return None

    def get_current_template(self):
        return {
            "root_dir": self.root_dir.get(),
            "ripper_name": self.ripper_name.get(),
            "release_group": self.release_group.get(),
            "ascii_art": self.ascii_text.get("1.0", "end-1c"),
            "equipment": self.equipment_text.get("1.0", "end-1c"),
            "software": self.software_text.get("1.0", "end-1c"),
            "add_presents": self.add_presents.get(),
            "presents_group": self.presents_group.get(),
            "rip_mode": self.rip_mode.get() if hasattr(self, 'rip_mode') else ""
        }

    def reset_template(self):
        self.settings.pop('template_path', None)
        self.save_settings()
        print("[DEBUG] Template lock cleared.")
        self.root_dir.set("")
        self.ripper_name.set("")
        self.release_group.set("")
        if hasattr(self, 'ascii_text'):
            self.ascii_text.delete("1.0", "end")
        self.equipment_text.delete("1.0", "end")
        self.software_text.delete("1.0", "end")
        self.add_presents.set(False)
        self.presents_group.set("")
        self.rip_mode.set("vinyl")

    # --- Utility: Extract disc number from CUE filename ---
    def get_disc_from_cue(self, cue_name):
        import re
        m = re.search(r'(cd|disc)[ _-]?(\d+)', cue_name, re.IGNORECASE)
        if m:
            return int(m.group(2))
        return 1

    # --- Add cp1252 sanitization helper ---
    def cp1252_safe(self, s):
        replacements = {
            '\u2010': '-', '\u2011': '-', '\u2012': '-', '\u2013': '-', '\u2014': '-', '\u2015': '-',
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...'
        }
        for uni, ascii_ in replacements.items():
            s = s.replace(uni, ascii_)
        return s.encode('cp1252', errors='replace').decode('cp1252')

    # --- Add normalize_filename helper ---
    def normalize_filename(self, s):
        s = self.cp1252_safe(s)
        s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
        s = s.replace('–', '-').replace('—', '-').replace('‐', '-')
        s = s.replace('…', '...')
        s = self.sanitize_windows_filename(s)
        return s  # REMOVE .lower() to preserve capitalization

    def sanitize_windows_filename(self, s):
        # Remove forbidden characters for Windows
        return re.sub(r'[<>:"/\\|?*]', '_', s)

    # --- Utility: Center a line for NFO ---
    def center_line(self, line, width=80):
        return line.center(width)

    # --- Utility: Remove more than one blank line in a row from NFO ---
    def clean_nfo_spacing(self, text):
        import re
        return re.sub(r'\n{3,}', '\n\n', text)

    # --- Use cp1252_safe for all CUE output lines and filenames ---
    # In update_cue_file and any CUE/NFO writing, wrap all lines and filenames with cp1252_safe()
    def update_cue_file(self, cue_path, flac_files, encoding='utf-8'):
        def read_cue_lines(cue_path):
            try:
                with open(cue_path, encoding=encoding) as f:
                    return f.readlines()
            except UnicodeDecodeError:
                with open(cue_path, encoding='cp1252') as f:
                    return f.readlines()
        lines = read_cue_lines(cue_path)
        new_lines = []
        flac_idx = 0
        for line in lines:
            if line.strip().upper().startswith('FILE') and flac_idx < len(flac_files):
                new_file = flac_files[flac_idx]
                new_lines.append(f'FILE "{self.normalize_filename(new_file)}" WAVE\r\n')
                flac_idx += 1
            else:
                new_lines.append(self.normalize_filename(line.rstrip('\r\n')) + '\r\n')
        shutil.copy2(cue_path, cue_path + '.bak')
        with open(cue_path, 'w', encoding='cp1252', newline='') as f:
            f.writelines(new_lines)
        self.log(f"[OK] Updated cue: {cue_path}")
        # Validate CUE: check all FILE lines exist
        missing_files = []
        for l in new_lines:
            if l.strip().upper().startswith('FILE'):
                fname = l.split('"')[1]
                if not os.path.exists(os.path.join(os.path.dirname(cue_path), fname)):
                    missing_files.append(fname)
        if missing_files:
            self.log(f"[ERROR] CUE references missing files: {missing_files}")
        else:
            # Clean up .bak if all is well
            if os.path.exists(cue_path + '.bak'):
                os.remove(cue_path + '.bak')

if __name__ == "__main__":
    try:
        app = RipzBuddyGUI()
        app.mainloop()
    except Exception as e:
        print("Main loop failed:", e)
        traceback.print_exc()
        sys.exit(1)
