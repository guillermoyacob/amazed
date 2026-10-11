import customtkinter as ctk

import threading

import subprocess

import os

import sys

import pyperclip

import tkinter.filedialog as filedialog

from tkinter import messagebox

import ctypes
import psutil

class AmazedApp(ctk.CTk):

    def __init__(self):

        super().__init__()

        # ============================================================

        # 1. CONFIGURACIÓN DE RUTAS PORTABLES

        # ============================================================

        if getattr(sys, 'frozen', False):

            self.base_path = os.path.dirname(sys.executable)

        else:

            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.download_path = os.path.join(self.base_path, "downloads")

        self.ytdlp_path = os.path.join(self.base_path, "yt-dlp.exe")

        self.ffmpeg_path = os.path.join(self.base_path, "ffmpeg.exe")

        self.ffprobe_path = os.path.join(self.base_path, "ffprobe.exe")

        if getattr(sys, 'frozen', False):

            self.icon_path = (

                os.path.join(sys._MEIPASS, "icono.ico")

                if hasattr(sys, "_MEIPASS")

                else os.path.join(self.base_path, "icono.ico")

            )

        else:

            self.icon_path = os.path.join(

                self.base_path, "assets", "icono.ico"

            )

        if not os.path.exists(self.download_path):

            os.makedirs(self.download_path)

        # ============================================================

        # 2. VARIABLES DE DESCARGA

        # ============================================================

        self.download_process = None

        self.downloading = False

        self.cancel_requested = False

        # Sincronización entre el hilo de descarga y la interfaz

        self.process_lock = threading.Lock()

        # Control de la advertencia

        self.warning_shown = False

        self.warning_event = threading.Event()

        self.warning_decision = None

        self.warning_window = None
        self.suspended_processes = []

        # Permite interrumpir la espera del temporizador

        # cuando la descarga termina o se cancela.

        self.monitor_stop_event = threading.Event()

        # ============================================================

        # 3. CONFIGURACIÓN DE VENTANA

        # ============================================================

        self.title("Amazed v2.0")

        self.geometry("620x260")

        self.resizable(False, False)

        if os.path.exists(self.icon_path):

            self.iconbitmap(self.icon_path)

            if sys.platform == "win32":

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(

                    "amazed"

                )

        self.grid_columnconfigure(0, weight=1)

        self.grid_columnconfigure(1, weight=0)

        # ============================================================

        # FILA 0: URL + PASTE

        # ============================================================

        self.url_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.url_frame.grid(

            row=0,

            column=0,

            columnspan=2,

            padx=20,

            pady=(20, 10),

            sticky="ew"

        )

        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_frame.grid_columnconfigure(1, weight=0)

        self.url_entry = ctk.CTkEntry(

            self.url_frame,

            placeholder_text="Paste media URL here..."

        )

        self.url_entry.grid(

            row=0,

            column=0,

            padx=(0, 25),

            sticky="ew"

        )

        self.paste_button = ctk.CTkButton(

            self.url_frame,

            text="Paste",

            width=100,

            command=self.paste_from_clipboard

        )

        self.paste_button.grid(

            row=0,

            column=1

        )

        # ============================================================

        # FILA 1: OPCIONES + DOWNLOAD/CANCEL

        # ============================================================

        self.options = [

            "Audio Standard MP3",

            "Audio Best Quality",

            "Video MP4 Full HD",

            "Video Best Quality"

        ]

        self.option_menu = ctk.CTkOptionMenu(

            self,

            values=self.options,

            width=200

        )

        self.option_menu.grid(

            row=1,

            column=0,

            padx=20,

            pady=10,

            sticky="w"

        )

        self.download_button = ctk.CTkButton(

            self,

            text="Download",

            width=100,

            command=self.run_thread

        )

        self.download_button.grid(

            row=1,

            column=1,

            padx=20,

            pady=10,

            sticky="e"

        )

        # ============================================================

        # FILA 2: RUTA DE DESCARGA

        # ============================================================

        self.folder_button = ctk.CTkButton(

            self,

            text="Choose folder",

            width=130,

            command=self.choose_download_folder

        )

        self.folder_button.grid(

            row=2,

            column=0,

            padx=20,

            pady=10,

            sticky="w"

        )

        self.download_path_label = ctk.CTkLabel(

            self,

            text=self.download_path,

            text_color="gray"

        )

        self.download_path_label.grid(

            row=2,

            column=1,

            padx=20,

            pady=10,

            sticky="e"

        )

        # ============================================================

        # FILA 3: ACTUALIZACIÓN Y VERSIÓN

        # ============================================================

        self.update_button = ctk.CTkButton(

            self,

            text="Update yt-dlp",

            width=130,

            command=self.update_ytdlp

        )

        self.update_button.grid(

            row=3,

            column=0,

            padx=20,

            pady=10,

            sticky="w"

        )

        self.version_label = ctk.CTkLabel(

            self,

            text="yt-dlp: checking...",

            text_color="gray"

        )

        self.version_label.grid(

            row=3,

            column=1,

            padx=20,

            pady=10,

            sticky="e"

        )

        # ============================================================

        # FILA 4: CRÉDITOS + STATUS

        # ============================================================

        self.credits_label = ctk.CTkLabel(

            self,

            text="Desarrollado por Guillermo Yacob",

            font=("Arial", 10),

            text_color="gray50"

        )

        self.credits_label.grid(

            row=4,

            column=0,

            padx=20,

            pady=(10, 5),

            sticky="sw"

        )

        self.status_label = ctk.CTkLabel(

            self,

            text="Checking files...",

            text_color="gray"

        )

        self.status_label.grid(

            row=4,

            column=1,

            padx=20,

            pady=(10, 5),

            sticky="se"

        )

        # ============================================================

        # COMPROBACIONES INICIALES

        # ============================================================

        self.check_required_files()

        self.get_ytdlp_version()

    # ================================================================

    # COMPROBAR ARCHIVOS

    # ================================================================

    def check_required_files(self):

        missing = []

        if not os.path.exists(self.ytdlp_path):

            missing.append("yt-dlp.exe")

        if not os.path.exists(self.ffmpeg_path):

            missing.append("ffmpeg.exe")

        if not os.path.exists(self.ffprobe_path):

            missing.append("ffprobe.exe")

        if missing:

            self.status_label.configure(

                text=f"Missing: {', '.join(missing)}",

                text_color="red"

            )

            self.download_button.configure(state="disabled")

            self.update_button.configure(

                state="disabled"

                if "yt-dlp.exe" in missing

                else "normal"

            )

        else:

            self.status_label.configure(

                text="Ready",

                text_color="gray"

            )

    # ================================================================

    # OBTENER VERSIÓN DE YT-DLP

    # ================================================================

    def get_ytdlp_version(self):

        if not os.path.exists(self.ytdlp_path):

            self.version_label.configure(

                text="yt-dlp: not found",

                text_color="red"

            )

            return

        def process():

            try:

                result = subprocess.run(

                    [self.ytdlp_path, "--version"],

                    capture_output=True,

                    text=True,

                    creationflags=subprocess.CREATE_NO_WINDOW,

                    shell=False

                )

                version = result.stdout.strip()

                if version:

                    self.after(

                        0,

                        lambda: self.version_label.configure(

                            text=f"yt-dlp: {version}",

                            text_color="gray"

                        )

                    )

                else:

                    self.after(

                        0,

                        lambda: self.version_label.configure(

                            text="yt-dlp: unknown",

                            text_color="orange"

                        )

                    )

            except Exception:

                self.after(

                    0,

                    lambda: self.version_label.configure(

                        text="yt-dlp: error",

                        text_color="red"

                    )

                )

        threading.Thread(

            target=process,

            daemon=True

        ).start()

    # ================================================================

    # ACTUALIZAR YT-DLP

    # ================================================================

    def update_ytdlp(self):

        if self.downloading:

            messagebox.showwarning(

                "Download in progress",

                "Please wait until the current download has finished."

            )

            return

        if not os.path.exists(self.ytdlp_path):

            messagebox.showerror(

                "Error",

                "yt-dlp.exe was not found."

            )

            return

        self.update_button.configure(

            state="disabled",

            text="Updating..."

        )

        def process():

            try:

                # Obtener versión anterior

                old_result = subprocess.run(

                    [self.ytdlp_path, "--version"],

                    capture_output=True,

                    text=True,

                    creationflags=subprocess.CREATE_NO_WINDOW,

                    shell=False

                )

                old_version = old_result.stdout.strip()

                # Ejecutar actualización nativa de yt-dlp

                update_result = subprocess.run(

                    [self.ytdlp_path, "-U"],

                    capture_output=True,

                    text=True,

                    creationflags=subprocess.CREATE_NO_WINDOW,

                    shell=False

                )

                # Obtener versión actual después de -U

                new_result = subprocess.run(

                    [self.ytdlp_path, "--version"],

                    capture_output=True,

                    text=True,

                    creationflags=subprocess.CREATE_NO_WINDOW,

                    shell=False

                )

                new_version = new_result.stdout.strip()

                if not new_version:

                    raise Exception(

                        "Could not determine the new yt-dlp version."

                    )

                # Actualizar etiqueta

                self.after(

                    0,

                    lambda: self.version_label.configure(

                        text=f"yt-dlp: {new_version}",

                        text_color="gray"

                    )

                )

                if old_version == new_version:

                    message = (

                        f"yt-dlp is already up to date.\n\n"

                        f"Version: {new_version}"

                    )

                else:

                    message = (

                        f"yt-dlp was updated successfully.\n\n"

                        f"Previous version: {old_version}\n"

                        f"New version: {new_version}"

                    )

                self.after(

                    0,

                    lambda: messagebox.showinfo(

                        "yt-dlp update",

                        message

                    )

                )

            except Exception as e:

                self.after(

                    0,

                    lambda: messagebox.showerror(

                        "Update error",

                        f"Could not update yt-dlp.\n\n{e}"

                    )

                )

            finally:

                self.after(

                    0,

                    lambda: self.update_button.configure(

                        state="normal",

                        text="Update yt-dlp"

                    )

                )

        threading.Thread(

            target=process,

            daemon=True

        ).start()

    # ================================================================

    # PORTAPAPELES

    # ================================================================

    def paste_from_clipboard(self):

        try:

            self.url_entry.delete(0, "end")

            self.url_entry.insert(0, pyperclip.paste())

        except Exception:

            pass

    # ================================================================

    # ELEGIR CARPETA DE DESCARGA

    # ================================================================

    def choose_download_folder(self):

        folder = filedialog.askdirectory(

            initialdir=self.download_path,

            title="Choose download folder"

        )

        if folder:

            self.download_path = folder

            self.download_path_label.configure(

                text=self.download_path

            )

    # ================================================================

    # CAMBIAR DOWNLOAD -> CANCEL

    # ================================================================

    def set_download_button_cancel(self):

        self.download_button.configure(

            text="Cancel",

            fg_color="orange",

            hover_color="#CC8400",

            command=self.cancel_download

        )

    # ================================================================

    # CAMBIAR CANCEL -> DOWNLOAD

    # ================================================================

    def set_download_button_download(self):

        self.download_button.configure(

            text="Download",

            fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],

            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],

            command=self.run_thread,

            state="normal"

        )

    # ================================================================

    # INICIAR DESCARGA

    # ================================================================

    def run_thread(self):

        if self.downloading:

            return

        url = self.url_entry.get().strip()

        if not url:

            self.status_label.configure(

                text="Insert URL",

                text_color="red"

            )

            return

        choice = self.option_menu.get()

        download_path = self.download_path

        self.downloading = True

        self.cancel_requested = False

        self.warning_shown = False

        self.warning_event.clear()

        self.monitor_stop_event.clear()

        self.warning_decision = None

        self.set_download_button_cancel()

        threading.Thread(

            target=self.start_download,

            args=(url, choice, download_path),

            daemon=True

        ).start()

    # ================================================================

    # DESCARGA

    # ================================================================

    def start_download(self, url, choice, download_path):

        process = None

        return_code = None

        error = None

        output = os.path.join(

            download_path,

            "%(title)s.%(ext)s"

        )

        cmd_base = [

            self.ytdlp_path,

            "--ffmpeg-location",

            self.base_path,

            "-o",

            output

        ]

        commands = {

            "Audio Standard MP3": cmd_base + [

                "-x",

                "--audio-format", "mp3",

                "--embed-metadata",

                "--embed-thumbnail",

                "--embed-chapters",

                "--sleep-interval", "5",

                "--max-sleep-interval", "15",

                url

            ],

            "Audio Best Quality": cmd_base + [

                "-x",

                "--audio-format", "m4a",

                "--audio-quality", "0",

                "--embed-metadata",

                "--embed-thumbnail",

                "--embed-chapters",

                "--sleep-interval", "5",

                "--max-sleep-interval", "15",

                url

            ],

            "Video MP4 Full HD": cmd_base + [

                "-f",

                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",

                "--embed-metadata",

                "--embed-thumbnail",

                "--embed-chapters",

                "--embed-subs",

                "--sub-langs", "es.*,en",

                "--sleep-interval", "5",

                "--max-sleep-interval", "15",

                url

            ],

            "Video Best Quality": cmd_base + [

                "--embed-metadata",

                "--embed-thumbnail",

                "--embed-chapters",

                "--embed-subs",

                "--sub-langs", "es.*,en",

                "--sleep-interval", "5",

                "--max-sleep-interval", "15",

                url

            ]

        }

        try:

            self.after(

                0,

                lambda: self.status_label.configure(

                    text="Downloading...",

                    text_color="orange"

                )

            )

            # Iniciar el proceso bajo protección del bloqueo.

            # Así no puede iniciarse una descarga nueva si

            # el usuario ya solicitó cancelarla.

            with self.process_lock:

                if not self.cancel_requested:

                    process = subprocess.Popen(

                        commands[choice],

                        creationflags=subprocess.CREATE_NO_WINDOW,

                        shell=False

                    )

                    self.download_process = process

            if process is not None:

                # Iniciar el control de tiempo

                threading.Thread(

                    target=self.monitor_download_time,

                    daemon=True

                ).start()

                return_code = process.wait()

        except Exception as e:

            error = e

        finally:

            with self.process_lock:

                was_cancelled = self.cancel_requested

                if self.download_process is process:

                    self.download_process = None

                self.downloading = False

                self.monitor_stop_event.set()

                self.warning_event.set()

                self.warning_shown = False

            # Actualizar la interfaz desde el hilo principal

            def finish_download():

                self.close_warning_window()

                if return_code == 0:

                    self.status_label.configure(

                        text="Finished!",

                        text_color="green"

                    )

                elif was_cancelled:

                    self.status_label.configure(

                        text="Cancelled",

                        text_color="gray"

                    )

                else:

                    self.status_label.configure(

                        text="Error",

                        text_color="red"

                    )

                self.set_download_button_download()

            self.after(0, finish_download)

    # ================================================================

    # CONTROL DEL TIEMPO DE DESCARGA

    # ================================================================

    def monitor_download_time(self):
        interval = 120

        while not self.monitor_stop_event.wait(interval):
            if not self.downloading:
                return

            with self.process_lock:
                process = self.download_process

            if process is None or process.poll() is not None:
                return

            decision = self.show_long_download_warning()

            if decision == "pause_failed":
                # La descarga sigue, pero no se vuelve a intentar inmediatamente.
                interval = 60
                continue

            if decision != "continue":
                return

            # Después de cada confirmación, esperar 5 minutos.
            interval = 300

    # ================================================================
    # PAUSAR / REANUDAR EL ÁRBOL DE PROCESOS
    # ================================================================

    def suspend_process_tree(self, pid):
        """Pausa yt-dlp y sus procesos secundarios, incluido FFmpeg."""
        suspended = []

        try:
            root = psutil.Process(pid)
            # Pausar primero el proceso principal para que no cree nuevos hijos.
            root.suspend()
            suspended.append(root)

            # Con yt-dlp pausado, identificar y pausar los procesos secundarios.
            for child in root.children(recursive=True):
                try:
                    child.suspend()
                    suspended.append(child)
                except psutil.NoSuchProcess:
                    # Un proceso secundario puede terminar durante la enumeración.
                    continue

            self.suspended_processes = suspended
            return True

        except (psutil.Error, OSError):
            # Si la pausa queda incompleta, intentar reanudar lo ya pausado.
            for proc in reversed(suspended):
                try:
                    proc.resume()
                except psutil.Error:
                    pass

            self.suspended_processes = []
            return False

    def resume_process_tree(self):
        """Reanuda primero los procesos secundarios y por último yt-dlp."""
        success = True

        for proc in reversed(self.suspended_processes):
            try:
                proc.resume()
            except psutil.NoSuchProcess:
                continue
            except psutil.Error:
                success = False

        if success:
            self.suspended_processes = []

        return success

    def show_long_download_warning(self):
        if self.warning_shown or not self.downloading:
            return None

        with self.process_lock:
            process = self.download_process

        if process is None or process.poll() is not None:
            return None

        # No mostrar la advertencia si no se pudo pausar el árbol completo.
        if not self.suspend_process_tree(process.pid):
            self.warning_shown = False
            self.after(
                0,
                lambda: messagebox.showerror(
                    "Pause error",
                    "Amazed could not pause the download processes. "
                    "The download will continue."
                )
            )
            return "pause_failed"

        self.warning_shown = True
        self.warning_event.clear()
        self.warning_decision = None

        def create_warning_window():
            # Comprobar que la descarga siga activa antes de abrir el diálogo.
            if (
                not self.downloading
                or self.monitor_stop_event.is_set()
            ):
                if not self.resume_process_tree():
                    self.cancel_download()
                self.warning_event.set()
                return

            warning = ctk.CTkToplevel(self)
            self.warning_window = warning

            warning.title("Amazed - Long download")
            warning.geometry("430x200")
            warning.resizable(False, False)
            warning.transient(self)
            warning.grab_set()

            label = ctk.CTkLabel(
                warning,
                text=(
                    "The download is still running.\n\n"
                    "Do you want to continue?"
                ),
                justify="center"
            )
            label.pack(padx=20, pady=(25, 15))

            button_frame = ctk.CTkFrame(
                warning,
                fg_color="transparent"
            )
            button_frame.pack(pady=(15, 20))

            def continue_download():
                if not self.resume_process_tree():
                    self.warning_decision = "stop"
                    self.close_warning_window()
                    self.cancel_download()
                    self.warning_event.set()
                    messagebox.showerror(
                        "Resume error",
                        "Amazed could not resume all download processes. "
                        "The download will be cancelled."
                    )
                    return

                self.warning_decision = "continue"
                self.close_warning_window()
                self.warning_event.set()

            def stop_download():
                self.warning_decision = "stop"
                self.close_warning_window()
                self.cancel_download()

            continue_button = ctk.CTkButton(
                button_frame,
                text="Continue",
                width=120,
                command=continue_download
            )
            continue_button.grid(row=0, column=0, padx=10)

            stop_button = ctk.CTkButton(
                button_frame,
                text="Stop downloads",
                width=120,
                fg_color="orange",
                hover_color="#CC8400",
                command=stop_download
            )
            stop_button.grid(row=0, column=1, padx=10)

            # Se exige una decisión mediante los botones.
            warning.protocol("WM_DELETE_WINDOW", lambda: None)

        self.after(0, create_warning_window)

        # Esperar la decisión o la finalización del proceso.
        self.warning_event.wait()

        decision = self.warning_decision
        self.warning_shown = False
        return decision

    def close_warning_window(self):
        warning = self.warning_window

        if warning is None:
            return

        self.warning_window = None

        try:
            warning.grab_release()
        except Exception:
            pass

        try:
            warning.destroy()
        except Exception:
            pass

    def cancel_download(self):

        with self.process_lock:

            if not self.downloading:

                return

            self.cancel_requested = True

            process = self.download_process

        self.status_label.configure(

            text="Cancelling...",

            text_color="orange"

        )

        if process is not None:

            try:

                result = subprocess.run(

                    [

                        "taskkill",

                        "/PID",

                        str(process.pid),

                        "/T",

                        "/F"

                    ],

                    capture_output=True,

                    creationflags=subprocess.CREATE_NO_WINDOW,

                    shell=False

                )

                # Si taskkill falla y yt-dlp sigue activo,

                # intentar terminar al menos el proceso principal.

                if result.returncode != 0 and process.poll() is None:

                    process.kill()

            except Exception:

                try:

                    if process.poll() is None:

                        process.kill()

                except Exception:

                    pass

        # Despertar al monitor si estaba esperando

        # la decisión de la ventana de advertencia.

        self.warning_event.set()

# ====================================================================

# MAIN

# ====================================================================

if __name__ == "__main__":

    app = AmazedApp()

    app.mainloop()
