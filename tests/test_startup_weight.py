"""Opening Lock In must not load big libraries it doesn't need yet.

OpenCV (for the optional camera switch, off by default) and the web
request code (for the update check, which runs a moment later on a
background helper) used to load the instant the app opened. That made
startup slower and used tens of MB of memory for nothing. Each check
runs in a fresh Python, so nothing another test imported can hide a
problem."""

import subprocess
import sys


def modules_loaded_by(import_line: str) -> set:
    code = f"import sys\n{import_line}\nprint(','.join(sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True, cwd=".")
    return set(out.stdout.strip().split(","))


def test_opening_the_app_code_does_not_load_opencv_or_web_requests():
    loaded = modules_loaded_by("import lock_in.ui")
    assert "cv2" not in loaded
    assert "numpy" not in loaded
    assert "lock_in.update_fetch" not in loaded
    assert "urllib.request" not in loaded


def test_camera_feature_check_does_not_load_opencv():
    loaded = modules_loaded_by(
        "import lock_in.camera_enforcer as c; print(c.CAMERA_BACKEND_AVAILABLE)")
    assert "cv2" not in loaded
