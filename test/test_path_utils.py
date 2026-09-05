import sys
import os
import tempfile
from pathlib import Path
import numpy as np
import cv2
import pytest

from core.path_utils import (
    get_project_root,
    get_resource_path,
    get_app_data_dir,
    safe_read_image,
)


def test_get_project_root():
    root = get_project_root()
    assert root.exists()
    assert (root / "main.py").exists()


def test_get_resource_path_existing_relative():
    # Test resolving known files
    model_path = get_resource_path("models/sam2.1_hiera_small.pt")
    assert model_path.exists()
    assert model_path.name == "sam2.1_hiera_small.pt"

    img_path = get_resource_path("imgs/logo_DEMO.ico")
    assert img_path.exists()

    qss_path = get_resource_path("styles/style.qss")
    assert qss_path.exists()


def test_get_resource_path_absolute():
    root = get_project_root()
    abs_model = root / "models" / "sam2.1_hiera_small.pt"
    resolved = get_resource_path(abs_model)
    assert resolved == abs_model


def test_get_resource_path_frozen_simulation(monkeypatch, tmp_path):
    # Simulate PyInstaller frozen environment
    fake_meipass = tmp_path / "_internal"
    fake_meipass.mkdir()
    fake_model_dir = fake_meipass / "models"
    fake_model_dir.mkdir()
    fake_model_file = fake_model_dir / "sam2.1_hiera_small.pt"
    fake_model_file.write_text("dummy model data")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)

    resolved = get_resource_path("models/sam2.1_hiera_small.pt")
    assert resolved == fake_model_file
    assert resolved.exists()


def test_get_app_data_dir():
    app_dir = get_app_data_dir("LocalKnotTest")
    assert app_dir.exists()
    assert app_dir.is_dir()
    # Cleanup test dir
    try:
        app_dir.rmdir()
    except Exception:
        pass


def test_safe_read_image(tmp_path):
    # Non-existent file
    assert safe_read_image(tmp_path / "non_existent.png") is None

    # Create a small valid test image with unicode characters in filename
    unicode_img_path = tmp_path / "tèst_ìmmagine_legnò.png"
    dummy_img = np.zeros((50, 50, 3), dtype=np.uint8)
    dummy_img[:, :] = (120, 150, 200)
    
    # Save image
    success, encoded = cv2.imencode(".png", dummy_img)
    assert success
    with open(unicode_img_path, "wb") as f:
        f.write(encoded.tobytes())

    loaded = safe_read_image(unicode_img_path)
    assert loaded is not None
    assert loaded.shape == (50, 50, 3)
