"""
CNC Parça Ölçüm Sistemi — Kalibrasyon Modülü
Piksel/mm oranı hesaplama ve kalibrasyon profili yönetimi.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


class CalibrationProfile:
    """Kalibrasyon profili — piksel/mm oranını saklar."""

    def __init__(self, pixels_per_mm: float = 1.0, reference_diameter_mm: float = 0.0,
                 reference_pixels: float = 0.0, name: str = "default"):
        self.name = name
        self.pixels_per_mm = pixels_per_mm
        self.reference_diameter_mm = reference_diameter_mm
        self.reference_pixels = reference_pixels

    def pixels_to_mm(self, pixels: float) -> float:
        """Piksel değerini mm'ye çevir."""
        if self.pixels_per_mm <= 0:
            return 0.0
        return pixels / self.pixels_per_mm

    def mm_to_pixels(self, mm: float) -> float:
        """mm değerini piksele çevir."""
        return mm * self.pixels_per_mm

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pixels_per_mm": self.pixels_per_mm,
            "reference_diameter_mm": self.reference_diameter_mm,
            "reference_pixels": self.reference_pixels,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationProfile":
        return cls(
            pixels_per_mm=data.get("pixels_per_mm", 1.0),
            reference_diameter_mm=data.get("reference_diameter_mm", 0.0),
            reference_pixels=data.get("reference_pixels", 0.0),
            name=data.get("name", "default"),
        )


def calculate_calibration(reference_diameter_mm: float, point1_y: float, point2_y: float) -> CalibrationProfile:
    """
    İki nokta arasındaki piksel mesafesi ve bilinen çap değerinden kalibrasyon hesapla.

    Args:
        reference_diameter_mm: Referans çap değeri (mm)
        point1_y: Birinci nokta y koordinatı (piksel) — üst kenar
        point2_y: İkinci nokta y koordinatı (piksel) — alt kenar

    Returns:
        CalibrationProfile: Hesaplanan kalibrasyon profili
    """
    pixel_distance = abs(point2_y - point1_y)
    if pixel_distance == 0 or reference_diameter_mm <= 0:
        raise ValueError("Geçersiz kalibrasyon değerleri: piksel mesafesi ve çap sıfırdan büyük olmalı")

    pixels_per_mm = pixel_distance / reference_diameter_mm

    return CalibrationProfile(
        pixels_per_mm=pixels_per_mm,
        reference_diameter_mm=reference_diameter_mm,
        reference_pixels=pixel_distance,
        name="custom",
    )


def calculate_calibration_from_line(reference_length_mm: float, x1: float, y1: float,
                                     x2: float, y2: float) -> CalibrationProfile:
    """
    Herhangi iki nokta arası piksel mesafesi ve bilinen uzunluktan kalibrasyon hesapla.
    Hem yatay hem dikey ölçüm için kullanılabilir.
    """
    import math
    pixel_distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if pixel_distance == 0 or reference_length_mm <= 0:
        raise ValueError("Geçersiz kalibrasyon değerleri")

    pixels_per_mm = pixel_distance / reference_length_mm
    return CalibrationProfile(
        pixels_per_mm=pixels_per_mm,
        reference_diameter_mm=reference_length_mm,
        reference_pixels=pixel_distance,
        name="custom",
    )


# ---------------------------------------------------------------------------
# Profil Kayıt/Yükleme
# ---------------------------------------------------------------------------

PROFILES_DIR = Path(__file__).resolve().parent.parent / "calibration_profiles"


def save_profile(profile: CalibrationProfile, name: Optional[str] = None) -> str:
    """Kalibrasyon profilini JSON dosyası olarak kaydet."""
    PROFILES_DIR.mkdir(exist_ok=True)
    profile_name = name or profile.name
    filepath = PROFILES_DIR / f"{profile_name}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
    return str(filepath)


def load_profile(name: str) -> CalibrationProfile:
    """Kaydedilmiş kalibrasyon profilini yükle."""
    filepath = PROFILES_DIR / f"{name}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Profil bulunamadı: {name}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return CalibrationProfile.from_dict(data)


def list_profiles() -> list:
    """Kaydedilmiş profillerin listesini döndür."""
    PROFILES_DIR.mkdir(exist_ok=True)
    profiles = []
    for fp in PROFILES_DIR.glob("*.json"):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            profiles.append(data)
        except Exception:
            continue
    return profiles
