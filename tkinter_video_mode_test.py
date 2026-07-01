"""
Standalone Tkinter video-mode DLP test.

Flow:
1) Open fullscreen Tk window on secondary display (black).
2) Arm DLP asynchronously into standard video mode (0x00), LED power=50.
3) Display exactly 5 frames at 1 second each: White, Black, White, Black, White.
4) Teardown asynchronously: power(0), changemode(0x00).
5) Exit Tk app once teardown is confirmed complete.
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
import glob
import time

import cv2
import numpy as np
from PIL import Image, ImageTk

# Optional Windows DPI awareness for multi-monitor stability.
if os.name == "nt":
    try:
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware()
    except Exception as exc:
        print(f"[WARN] Could not set DPI awareness: {exc}")

# Enforce project-local interpreter to avoid dependency mismatches.
_REQUIRED_PYTHON = os.path.normcase(
    os.path.normpath(os.path.join(os.path.dirname(__file__), ".conda", "python.exe"))
)
_ACTIVE_PYTHON = os.path.normcase(os.path.normpath(sys.executable))
if _ACTIVE_PYTHON != _REQUIRED_PYTHON:
    print(f"[FATAL] Wrong Python interpreter detected: {_ACTIVE_PYTHON}")
    print(f"[FATAL] Required interpreter: {_REQUIRED_PYTHON}")
    print("Please run using: .\\.conda\\python.exe tkinter_video_mode_test.py")
    sys.exit(1)

try:
    import screeninfo
except Exception as exc:
    print(f"[FATAL] screeninfo import failed: {exc}")
    sys.exit(1)


class TkinterVideoModeTest:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Tkinter Video Mode Test")

        # Tk image widget for projector output updates.
        self.image_label = tk.Label(self.root, bg="black", borderwidth=0, highlightthickness=0)
        self.image_label.pack(fill="both", expand=True)

        self.controller = None
        self.arm_done = threading.Event()
        self.arm_failed = threading.Event()
        self.teardown_done = threading.Event()
        self.teardown_started = False

        # Runtime display geometry and image assets.
        self.target_width = 0
        self.target_height = 0
        self.loaded_photos: list[ImageTk.PhotoImage] = []

        # Image sequence index 0..4
        self.frame_index = 0

        self._place_on_secondary_display()
        self._load_test_images()

    def _place_on_secondary_display(self) -> None:
        monitors = screeninfo.get_monitors()
        if len(monitors) > 1:
            target = monitors[1]
            print(
                f"Using secondary display: index=1, "
                f"size={target.width}x{target.height}, origin=({target.x},{target.y})"
            )
        else:
            target = monitors[0]
            print("Secondary display not found. Falling back to primary display (index=0).")

        # Fullscreen-style placement on the selected monitor.
        self.root.geometry(f"{target.width}x{target.height}+{target.x}+{target.y}")
        self.root.overrideredirect(True)
        self.root.configure(bg="black")
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.focus_force()

        self.target_width = int(target.width)
        self.target_height = int(target.height)

    def _load_test_images(self) -> None:
        """Load first 5 images from ./test_images using Prince-style file loading semantics."""
        images_dir = os.path.join(os.path.dirname(__file__), "test_images")
        patterns = ("*.png", "*.tif", "*.tiff", "*.bmp", "*.jpg", "*.jpeg", "*.npy")

        file_list: list[str] = []
        for pat in patterns:
            file_list.extend(glob.glob(os.path.join(images_dir, pat)))

        file_list = sorted(file_list)[:5]
        if len(file_list) < 5:
            raise RuntimeError(
                f"Expected at least 5 images in {images_dir}, found {len(file_list)}"
            )

        self.loaded_photos.clear()

        for path in file_list:
            ext = os.path.splitext(path)[1].lower()

            if ext == ".npy":
                arr = np.load(path, allow_pickle=False)
            else:
                # Match Prince_Segmented image loading strategy.
                arr = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

            if arr is None:
                raise RuntimeError(f"Failed to load image: {path}")

            photo = self._array_to_photoimage(arr)
            self.loaded_photos.append(photo)

        print(f"Loaded {len(self.loaded_photos)} test images from {images_dir}")

    def _array_to_photoimage(self, arr: np.ndarray) -> ImageTk.PhotoImage:
        """Convert image array to Tk PhotoImage, resized to projector resolution."""
        if arr.ndim == 2:
            rgb = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_GRAY2RGB)
        elif arr.ndim == 3 and arr.shape[2] == 4:
            rgb = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_BGRA2RGB)
        elif arr.ndim == 3 and arr.shape[2] == 3:
            # OpenCV loads color as BGR; convert to RGB for PIL/Tk.
            rgb = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_BGR2RGB)
        else:
            raise RuntimeError(f"Unsupported image shape for display: {arr.shape}")

        if rgb.shape[1] != self.target_width or rgb.shape[0] != self.target_height:
            rgb = cv2.resize(
                rgb,
                (self.target_width, self.target_height),
                interpolation=cv2.INTER_NEAREST,
            )

        pil_img = Image.fromarray(rgb)
        return ImageTk.PhotoImage(image=pil_img)

    def _show_image(self, index: int) -> None:
        photo = self.loaded_photos[index]
        self.image_label.configure(image=photo)
        self.image_label.image = photo

    def _initialize_controller(self) -> None:
        if self.controller is not None:
            return

        support_modules_path = os.path.join(os.path.dirname(__file__), "support_modules")
        if support_modules_path not in sys.path:
            sys.path.append(support_modules_path)

        import pycrafter9000  # type: ignore

        self.controller = pycrafter9000.dmd()

    def _arm_hardware_worker(self) -> None:
        try:
            print("Arming thread started...")
            self._initialize_controller()

            from support_modules.USBCoordinator import usb_coordinator

            with usb_coordinator.dlp_operation("tkinter_video_mode_arm"):
                # 1) Safety reset: stop sequence, LEDs off, baseline video mode.
                self.controller.stopsequence()
                self.controller.power(current=0)
                self.controller.changemode(0x00)

                # 2) HDMI handshake in the dark.
                self.controller.hdmi()

                # 3) Long wait for OS/display receiver sync.
                time.sleep(1.5)

                # 4) Pivot to pattern mode while still dark.
                self.controller.changemode(0x02)

                # 5) Configure single 8-bit blue/UV pattern and start sequence.
                self.controller.configurelut(1, 0xFFFFFFFF)
                self.controller.definepattern(
                    index=0,
                    exposure=33333,
                    bitdepth=8,
                    color="100",
                    triggerin=False,
                    darktime=0,
                    triggerout=0,
                    patind=0,
                    bitpos=0,
                )
                self.controller.startsequence()

                # 6) Reveal: wait briefly, then enable LEDs.
                time.sleep(0.5)
                self.controller.power(current=50)

            print("[PASS] DLP armed in silent pattern-mode wakeup sequence, power=50")
            self.arm_done.set()
        except Exception as exc:
            print(f"[FAIL] DLP arming failed: {exc}")
            self.arm_failed.set()

    def _start_arm_async(self) -> None:
        threading.Thread(target=self._arm_hardware_worker, daemon=True).start()

    def _wait_for_arm_and_start_exposure(self) -> None:
        if self.arm_failed.is_set():
            self._exit_now()
            return

        if not self.arm_done.is_set():
            self.root.after(50, self._wait_for_arm_and_start_exposure)
            return

        self.frame_index = 0
        self._show_next_frame()

    def _show_next_frame(self) -> None:
        if self.frame_index >= 5:
            # Mirror Prince behavior: force black frame before teardown commands.
            self.image_label.configure(image="", bg="black")
            self.image_label.image = None
            self.root.configure(bg="black")
            self.root.update_idletasks()
            self._start_teardown_async()
            self._wait_for_teardown_and_exit()
            return

        print(f"Frame {self.frame_index + 1}/5: test image {self.frame_index + 1} (1000 ms)")
        self._show_image(self.frame_index)
        self.frame_index += 1

        # Hold each frame for exactly 1000 ms.
        self.root.after(1000, self._show_next_frame)

    def _teardown_hardware_worker(self) -> None:
        try:
            print("Teardown thread started...")
            if self.controller is not None:
                from support_modules.USBCoordinator import usb_coordinator

                with usb_coordinator.dlp_operation("tkinter_video_mode_teardown"):
                    self.controller.stopsequence()
                    self.controller.power(current=0)
                    self.controller.changemode(0x00)

            print("[PASS] DLP teardown complete (power=0, mode=0x00)")
            self.teardown_done.set()
        except Exception as exc:
            print(f"[WARN] DLP teardown warning: {exc}")
            self.teardown_done.set()

    def _start_teardown_async(self) -> None:
        if self.teardown_started:
            return
        self.teardown_started = True
        threading.Thread(target=self._teardown_hardware_worker, daemon=True).start()

    def _wait_for_teardown_and_exit(self) -> None:
        if not self.teardown_done.is_set():
            self.root.after(50, self._wait_for_teardown_and_exit)
            return
        self._exit_now()

    def _exit_now(self) -> None:
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> None:
        # Start on black.
        self.image_label.configure(image="", bg="black")
        self.image_label.image = None
        self.root.configure(bg="black")
        self.root.update_idletasks()
        self.root.update()

        self._start_arm_async()
        self._wait_for_arm_and_start_exposure()

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt received. Teardown and exit...")
            self._start_teardown_async()
            self._wait_for_teardown_and_exit()


def main() -> int:
    app = TkinterVideoModeTest()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
