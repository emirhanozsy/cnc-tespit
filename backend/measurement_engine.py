"""
CNC Parça Ölçüm Sistemi — Ölçüm Motoru
Çap profil verisinden bölüm tespiti, çap ve uzunluk hesaplama.
"""

import numpy as np
from typing import Dict, List, Optional
from calibration import CalibrationProfile


def detect_sections(profile: Dict, calibration: CalibrationProfile,
                    min_section_width_px: int = 20,
                    gradient_threshold: float = 2.0) -> List[Dict]:
    """
    Çap profilindeki bölümleri (sabit çap bölgeleri) tespit eder.

    Yöntem:
    1. Çap profilinin türevini al
    2. Türevdeki büyük sıçramalar = bölüm geçişleri
    3. Her düz bölge = bir bölüm
    4. Her bölümün ortalama çapını ve uzunluğunu hesapla

    Args:
        profile: profile_extractor.extract_profile() çıktısı
        calibration: Kalibrasyon profili
        min_section_width_px: Minimum bölüm genişliği (piksel)
        gradient_threshold: Bölüm geçiş eşiği (piksel/kolon)

    Returns:
        Bölüm listesi (her biri dict)
    """
    diameter_px = np.array(profile["diameter_px"], dtype=float)
    top_edge = profile["top_edge"]
    bottom_edge = profile["bottom_edge"]
    x_start = profile["x_start"]

    # None değerleri 0 ile değiştir
    diameter_px = np.nan_to_num(diameter_px, nan=0.0)

    # Kısa bir median filtre ile gürültüyü temizle
    if len(diameter_px) > 5:
        from scipy.ndimage import median_filter
        diameter_smooth = median_filter(diameter_px, size=7)
    else:
        diameter_smooth = diameter_px.copy()

    # Türev hesapla
    gradient = np.gradient(diameter_smooth)

    # Bölüm geçiş noktalarını bul
    transitions = []
    transitions.append(0)  # Başlangıç

    for i in range(1, len(gradient)):
        if abs(gradient[i]) > gradient_threshold:
            # Önceki geçişten yeterli uzaklıkta mı?
            if len(transitions) == 0 or (i - transitions[-1]) > min_section_width_px // 2:
                transitions.append(i)

    transitions.append(len(diameter_px))  # Bitiş

    # Geçişleri temizle — çok yakın olanları birleştir
    clean_transitions = [transitions[0]]
    for t in transitions[1:]:
        if t - clean_transitions[-1] >= min_section_width_px:
            clean_transitions.append(t)
        else:
            clean_transitions[-1] = t  # İleriyi al
    if clean_transitions[-1] != len(diameter_px):
        clean_transitions.append(len(diameter_px))

    # Bölüm bilgilerini hesapla
    sections = []
    section_num = 1

    for i in range(len(clean_transitions) - 1):
        s = clean_transitions[i]
        e = clean_transitions[i + 1]

        if e - s < min_section_width_px:
            continue

        # Bölüm çap değerleri
        seg_diameters = diameter_px[s:e]
        valid_diameters = seg_diameters[seg_diameters > 0]

        if len(valid_diameters) == 0:
            continue

        # İstatistikler
        avg_diameter_px = float(np.median(valid_diameters))
        std_diameter_px = float(np.std(valid_diameters))
        width_px = e - s

        # mm'ye çevir
        diameter_mm = calibration.pixels_to_mm(avg_diameter_px)
        length_mm = calibration.pixels_to_mm(width_px)

        # Orta noktadaki üst/alt kenar
        mid_idx = (s + e) // 2
        top_y_at_mid = top_edge[mid_idx] if mid_idx < len(top_edge) and top_edge[mid_idx] is not None else None
        bot_y_at_mid = bottom_edge[mid_idx] if mid_idx < len(bottom_edge) and bottom_edge[mid_idx] is not None else None

        # Merkez y
        center_y_values = [profile["center_y"][j] for j in range(s, e) if j < len(profile["center_y"]) and profile["center_y"][j] is not None]
        center_y = float(np.mean(center_y_values)) if center_y_values else None

        sections.append({
            "section_id": section_num,
            "x_start_rel": s,
            "x_end_rel": e,
            "x_start_abs": x_start + s,
            "x_end_abs": x_start + e,
            "width_px": width_px,
            "avg_diameter_px": round(avg_diameter_px, 2),
            "std_diameter_px": round(std_diameter_px, 2),
            "diameter_mm": round(diameter_mm, 4),
            "length_mm": round(length_mm, 4),
            "top_y_at_mid": top_y_at_mid,
            "bottom_y_at_mid": bot_y_at_mid,
            "center_y": center_y,
        })

        section_num += 1

    return sections


def generate_measurement_table(sections: List[Dict]) -> List[Dict]:
    """
    Bölüm verisinden VICIVISION benzeri ölçüm tablosu oluşturur.

    Returns:
        Tablo satırları listesi
    """
    rows = []
    for sec in sections:
        # Çap satırı
        rows.append({
            "id": f"D{sec['section_id']:02d}",
            "type": "Çap",
            "description": f"Ø Bölüm {sec['section_id']}",
            "nominal_mm": sec["diameter_mm"],
            "measured_mm": sec["diameter_mm"],
            "deviation_mm": 0.0,
            "section_id": sec["section_id"],
        })
        # Uzunluk satırı
        rows.append({
            "id": f"L{sec['section_id']:02d}",
            "type": "Uzunluk",
            "description": f"Boy Bölüm {sec['section_id']}",
            "nominal_mm": sec["length_mm"],
            "measured_mm": sec["length_mm"],
            "deviation_mm": 0.0,
            "section_id": sec["section_id"],
        })

    return rows


def get_measurement_summary(sections: List[Dict]) -> Dict:
    """Genel ölçüm özeti."""
    if not sections:
        return {"total_sections": 0}

    diameters = [s["diameter_mm"] for s in sections]
    lengths = [s["length_mm"] for s in sections]

    return {
        "total_sections": len(sections),
        "min_diameter_mm": round(min(diameters), 4),
        "max_diameter_mm": round(max(diameters), 4),
        "total_length_mm": round(sum(lengths), 4),
        "sections": sections,
    }
