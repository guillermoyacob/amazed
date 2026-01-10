import customtkinter as ctk
import threading
import subprocess
import os
import sys
import pyperclip

class AmazedApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Configuración de Rutas Portables
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.download_path = os.path.join(self.base_path, "downloads")
        self.ytdlp_path = os.path.join(self.base_path, "yt-dlp.exe")
        self.ffmpeg_path = os.path.join(self.base_path, "ffmpeg.exe")
        self.ffprobe_path = os.path.join(self.base_path, "ffprobe.exe")
        

        if getattr(sys, 'frozen', False):
            # En el ejecutable (.exe), PyInstaller pone el icono en la raíz temporal
            self.icon_path = os.path.join(sys._MEIPASS, "icono.ico") if hasattr(sys, '_MEIPASS') else os.path.join(self.base_path, "icono.ico")
        else:
            # En modo desarrollo (.py), lo busca dentro de la carpeta assets
            self.icon_path = os.path.join(self.base_path, "assets", "icono.ico")
        
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        # 2. Configuración de Ventana e Icono
        self.title("Amazed v1.2") # Versión agregada al título
        self.geometry("620x240")

        # Bloquea el redimensionamiento: (Ancho, Alto)
        self.resizable(False, False)
        
        if os.path.exists(self.icon_path):
            self.iconbitmap(self.icon_path)
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('guillermoyacob.amazed.v1.2')

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        # --- FILA 0: Input y Paste ---
        self.url_entry = ctk.CTkEntry(self, placeholder_text="Paste YouTube URL here...")
        self.url_entry.grid(row=0, column=0, padx=(20, 10), pady=(20, 10), sticky="ew")

        self.paste_button = ctk.CTkButton(self, text="Paste", width=100, command=self.paste_from_clipboard)
        self.paste_button.grid(row=0, column=1, padx=(10, 20), pady=(20, 10), sticky="e")

        # --- FILA 1: Opciones y Download ---
        self.options = ["Audio Standard MP3", "Audio Best Quality", "Video MP4 Full HD", "Video Best Quality"]
        self.option_menu = ctk.CTkOptionMenu(self, values=self.options, width=200)
        self.option_menu.grid(row=1, column=0, padx=20, pady=10, sticky="w")

        self.download_button = ctk.CTkButton(self, text="Download", width=100, command=self.run_thread)
        self.download_button.grid(row=1, column=1, padx=20, pady=10, sticky="e")

        # --- FILA 2: Créditos y Status ---
        # Créditos Guillermo Yacob
        self.credits_label = ctk.CTkLabel(self, text="Desarrollado por Guillermo Yacob v1.2", font=("Arial", 10), text_color="gray50")
        self.credits_label.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="sw")

        self.status_label = ctk.CTkLabel(self, text="Checking files...", text_color="gray")
        self.status_label.grid(row=2, column=1, padx=20, pady=(10, 20), sticky="se")

        self.check_required_files()

    def check_required_files(self):
        missing = []
        if not os.path.exists(self.ytdlp_path): missing.append("yt-dlp.exe")
        if not os.path.exists(self.ffmpeg_path): missing.append("ffmpeg.exe")
        if not os.path.exists(self.ffprobe_path): missing.append("ffprobe.exe")

        if missing:
            self.status_label.configure(text=f"Missing: {', '.join(missing)}", text_color="red")
            self.download_button.configure(state="disabled")
        else:
            self.status_label.configure(text="Ready", text_color="gray")

    def paste_from_clipboard(self):
        try:
            self.url_entry.delete(0, 'end')
            self.url_entry.insert(0, pyperclip.paste())
        except: pass

    def run_thread(self):
        threading.Thread(target=self.start_download, daemon=True).start()

    def start_download(self):
        url = self.url_entry.get()
        choice = self.option_menu.get()
        if not url: 
            self.status_label.configure(text="Insert URL", text_color="red")
            return

        output = os.path.join(self.download_path, "%(title)s.%(ext)s")
        cmd_base = [self.ytdlp_path, "--ffmpeg-location", self.base_path, "-o", output]
        
        commands = {
            "Audio Standard MP3": cmd_base + [
                "-x", "--audio-format", "mp3", 
                "--embed-metadata", "--embed-thumbnail", "--embed-chapters",
                url
            ],

            "Audio Best Quality": cmd_base + [
                "-x", "--audio-format", "m4a",
                "--audio-quality", "0",
                "--embed-metadata", "--embed-thumbnail", "--embed-chapters",
                url
            ],

            "Video MP4 Full HD": cmd_base + [
                "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", 
                "--embed-metadata", "--embed-thumbnail",
                url
            ],

            "Video Best Quality": cmd_base + [
                "--embed-metadata", "--embed-thumbnail", "--embed-chapters", "--embed-subs",
                url
            ]
        }

        try:
            self.download_button.configure(state="disabled")
            self.status_label.configure(text="Downloading...", text_color="orange")
            subprocess.run(commands[choice], check=True, creationflags=subprocess.CREATE_NO_WINDOW, shell=False)
            self.status_label.configure(text="Finished!", text_color="green")
        except:
            self.status_label.configure(text="Error", text_color="red")
        finally:
            self.download_button.configure(state="normal")

if __name__ == "__main__":
    app = AmazedApp()
    app.mainloop()