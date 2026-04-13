import os
import types
import pathlib
import importlib.util

ROOT = pathlib.Path(__file__).resolve().parent
os.chdir(ROOT)

spec = importlib.util.spec_from_file_location("rush_app", ROOT / "Rush_Segmented_VideoPattern.py")
rush = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rush)


class DummyDMD:
    def stopsequence(self):
        pass

    def power(self, current=0):
        pass

    def changemode(self, mode=0):
        pass

    def hdmi(self):
        pass

    def configurelut(self, *args, **kwargs):
        pass

    def definepattern(self, *args, **kwargs):
        pass

    def startsequence(self):
        pass

    def standby(self):
        pass


class DummyAxis:
    def __init__(self, *args, **kwargs):
        self._pos_mm = 0.0

    def connect(self):
        pass

    def disconnect(self):
        pass

    def stop(self):
        pass

    def wait_until_idle(self):
        pass

    def get_position(self, unit=None):
        return self._pos_mm

    def move_absolute(
        self,
        position,
        unit=None,
        wait_until_idle=False,
        velocity=None,
        velocity_unit=None,
        acceleration=None,
        acceleration_unit=None,
    ):
        self._pos_mm = float(position)

    def move_relative(
        self,
        position,
        unit=None,
        wait_until_idle=False,
        velocity=None,
        velocity_unit=None,
        acceleration=None,
        acceleration_unit=None,
    ):
        self._pos_mm += float(position)


rush.pycrafter9000 = types.SimpleNamespace(dmd=lambda: DummyDMD())
rush.A3200StageAdapter = DummyAxis

window = rush.Tk()
mywin = rush.MyWindow(window)
window.title("Rush - Main Window (No Hardware Preview)")
if hasattr(mywin, "default_window_geometry"):
    window.geometry(mywin.default_window_geometry)
window.protocol("WM_DELETE_WINDOW", mywin.on_closing)
window.mainloop()
