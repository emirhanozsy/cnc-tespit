"""
CNC Parça Ölçüm Sistemi — Görüntü İşleme Modülü
Tüm kenar tespit ve görüntü işleme algoritmalarını içerir.
"""

import cv2
import numpy as np
from typing import Dict, Any


# ---------------------------------------------------------------------------
# Algoritma Kayıt Sistemi
# ---------------------------------------------------------------------------

ALGORITHMS: Dict[str, Dict[str, Any]] = {}


def register(name: str, display_name: str, description: str, params: list):
    """Algoritma dekoratörü — fonksiyonu ALGORITHMS sözlüğüne kaydeder."""
    def decorator(func):
        ALGORITHMS[name] = {
            "function": func,
            "display_name": display_name,
            "description": description,
            "params": params,
        }
        return func
    return decorator


def get_algorithm_list() -> list:
    """Tüm kayıtlı algoritmaların listesini döndürür (fonksiyon olmadan)."""
    result = []
    for key, val in ALGORITHMS.items():
        result.append({
            "name": key,
            "display_name": val["display_name"],
            "description": val["description"],
            "params": val["params"],
        })
    return result


def apply_algorithm(name: str, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    """Belirtilen algoritmayı görüntüye uygular."""
    if name not in ALGORITHMS:
        raise ValueError(f"Bilinmeyen algoritma: {name}")
    func = ALGORITHMS[name]["function"]
    return func(image, params)


# ---------------------------------------------------------------------------
# Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------

def _ensure_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image


def _odd(val: int) -> int:
    val = max(1, int(val))
    return val if val % 2 == 1 else val + 1


# ---------------------------------------------------------------------------
# 1. Grayscale
# ---------------------------------------------------------------------------
@register("grayscale", "Grayscale (Gri Tonlama)",
          "Renkli görüntüyü gri tonlamaya çevirir.", [])
def grayscale(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    return cv2.cvtColor(_ensure_gray(image), cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 2. Gaussian Blur
# ---------------------------------------------------------------------------
@register("gaussian_blur", "Gaussian Blur (Bulanıklaştırma)",
          "Gürültüyü azaltmak için Gaussian bulanıklaştırma uygular.",
          [{"name": "kernel_size", "display_name": "Kernel Boyutu", "type": "int", "min": 1, "max": 31, "default": 5, "step": 2}])
def gaussian_blur(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    k = _odd(params.get("kernel_size", 5))
    return cv2.GaussianBlur(image, (k, k), 0)


# ---------------------------------------------------------------------------
# 3. Canny Edge Detection
# ---------------------------------------------------------------------------
@register("canny", "Canny Kenar Tespiti",
          "En yaygın kenar tespit algoritması. İki eşik değeri ile güçlü kenarları bulur.",
          [{"name": "threshold1", "display_name": "Alt Eşik", "type": "int", "min": 0, "max": 500, "default": 50, "step": 1},
           {"name": "threshold2", "display_name": "Üst Eşik", "type": "int", "min": 0, "max": 500, "default": 150, "step": 1},
           {"name": "aperture_size", "display_name": "Aperture", "type": "int", "min": 3, "max": 7, "default": 3, "step": 2}])
def canny_edge(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    gray = _ensure_gray(image)
    t1 = int(params.get("threshold1", 50))
    t2 = int(params.get("threshold2", 150))
    aperture = max(3, min(7, _odd(params.get("aperture_size", 3))))
    edges = cv2.Canny(gray, t1, t2, apertureSize=aperture)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 4. Sobel Edge Detection
# ---------------------------------------------------------------------------
@register("sobel", "Sobel Kenar Tespiti",
          "Gradyan tabanlı kenar tespiti. X ve Y yönünde türev alır.",
          [{"name": "kernel_size", "display_name": "Kernel Boyutu", "type": "int", "min": 1, "max": 7, "default": 3, "step": 2},
           {"name": "direction", "display_name": "Yön", "type": "select", "options": ["both", "x", "y"], "default": "both"}])
def sobel_edge(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    gray = _ensure_gray(image)
    k = max(1, min(7, _odd(params.get("kernel_size", 3))))
    direction = params.get("direction", "both")
    if direction == "x":
        sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)
    elif direction == "y":
        sobel = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)
    else:
        sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)
        sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)
        sobel = np.sqrt(sx ** 2 + sy ** 2)
    mx = sobel.max()
    sobel = np.uint8(np.clip(sobel / mx * 255, 0, 255)) if mx > 0 else np.zeros_like(gray)
    return cv2.cvtColor(sobel, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 5. Laplacian Edge Detection
# ---------------------------------------------------------------------------
@register("laplacian", "Laplacian Kenar Tespiti",
          "İkinci türev tabanlı kenar tespiti. Tüm yönlerdeki kenarları yakalar.",
          [{"name": "kernel_size", "display_name": "Kernel Boyutu", "type": "int", "min": 1, "max": 31, "default": 3, "step": 2}])
def laplacian_edge(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    gray = _ensure_gray(image)
    k = _odd(params.get("kernel_size", 3))
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=k)
    mx = np.abs(lap).max()
    lap = np.uint8(np.clip(np.abs(lap) / mx * 255, 0, 255)) if mx > 0 else np.zeros_like(gray)
    return cv2.cvtColor(lap, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 6. Adaptive Threshold
# ---------------------------------------------------------------------------
@register("adaptive_threshold", "Adaptive Threshold (Uyarlanabilir Eşikleme)",
          "Her piksel için yerel eşik hesaplar. Değişken aydınlatmada etkilidir.",
          [{"name": "block_size", "display_name": "Blok Boyutu", "type": "int", "min": 3, "max": 99, "default": 11, "step": 2},
           {"name": "c_value", "display_name": "C Değeri", "type": "int", "min": -20, "max": 20, "default": 2, "step": 1},
           {"name": "method", "display_name": "Metot", "type": "select", "options": ["mean", "gaussian"], "default": "gaussian"}])
def adaptive_threshold(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    gray = _ensure_gray(image)
    block = max(3, _odd(params.get("block_size", 11)))
    c = int(params.get("c_value", 2))
    method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C if params.get("method", "gaussian") == "gaussian" else cv2.ADAPTIVE_THRESH_MEAN_C
    result = cv2.adaptiveThreshold(gray, 255, method, cv2.THRESH_BINARY, block, c)
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 7. Otsu Threshold
# ---------------------------------------------------------------------------
@register("otsu_threshold", "Otsu Threshold (Otomatik Eşikleme)",
          "Histogram analizi ile optimum eşik değerini otomatik belirler.", [])
def otsu_threshold(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    gray = _ensure_gray(image)
    _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 8. Morphological Operations
# ---------------------------------------------------------------------------
@register("morphological", "Morfolojik İşlemler",
          "Erozyon, genişletme, açma ve kapama. Gürültü temizleme ve şekil düzeltme.",
          [{"name": "operation", "display_name": "İşlem", "type": "select", "options": ["erode", "dilate", "open", "close"], "default": "close"},
           {"name": "kernel_size", "display_name": "Kernel Boyutu", "type": "int", "min": 1, "max": 21, "default": 5, "step": 2},
           {"name": "iterations", "display_name": "Tekrar Sayısı", "type": "int", "min": 1, "max": 10, "default": 1, "step": 1}])
def morphological(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    k = _odd(params.get("kernel_size", 5))
    iterations = max(1, int(params.get("iterations", 1)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    gray = _ensure_gray(image)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    op = params.get("operation", "close")
    ops = {"erode": lambda: cv2.erode(binary, kernel, iterations=iterations),
           "dilate": lambda: cv2.dilate(binary, kernel, iterations=iterations),
           "open": lambda: cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=iterations),
           "close": lambda: cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=iterations)}
    result = ops.get(op, ops["close"])()
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 9. Contour Detection
# ---------------------------------------------------------------------------
@register("contour_detection", "Kontur Tespiti",
          "Nesnelerin dış hatlarını bulur ve çizer. Parça profilini görmek için kullanışlı.",
          [{"name": "threshold", "display_name": "Eşik Değeri", "type": "int", "min": 0, "max": 255, "default": 127, "step": 1},
           {"name": "min_area", "display_name": "Min Alan (px²)", "type": "int", "min": 0, "max": 50000, "default": 500, "step": 100},
           {"name": "thickness", "display_name": "Çizgi Kalınlığı", "type": "int", "min": 1, "max": 10, "default": 2, "step": 1}])
def contour_detection(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    gray = _ensure_gray(image)
    thresh_val = int(params.get("threshold", 127))
    min_area = int(params.get("min_area", 500))
    thickness = int(params.get("thickness", 2))
    _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = _ensure_bgr(image).copy()
    colors = [(0, 255, 0), (0, 200, 255), (255, 100, 0), (0, 255, 255), (255, 0, 255)]
    for i, c in enumerate(c for c in contours if cv2.contourArea(c) >= min_area):
        cv2.drawContours(result, [c], -1, colors[i % len(colors)], thickness)
    return result


# ---------------------------------------------------------------------------
# 10. Hough Line Transform
# ---------------------------------------------------------------------------
@register("hough_lines", "Hough Doğru Tespiti",
          "Görüntüdeki doğru çizgileri tespit eder.",
          [{"name": "canny_thresh1", "display_name": "Canny Alt Eşik", "type": "int", "min": 0, "max": 500, "default": 50, "step": 1},
           {"name": "canny_thresh2", "display_name": "Canny Üst Eşik", "type": "int", "min": 0, "max": 500, "default": 150, "step": 1},
           {"name": "min_line_length", "display_name": "Min Çizgi Uzunluğu", "type": "int", "min": 10, "max": 500, "default": 100, "step": 10},
           {"name": "max_line_gap", "display_name": "Max Boşluk", "type": "int", "min": 1, "max": 100, "default": 10, "step": 1},
           {"name": "threshold", "display_name": "Oylama Eşiği", "type": "int", "min": 10, "max": 500, "default": 100, "step": 10}])
def hough_lines(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    gray = _ensure_gray(image)
    edges = cv2.Canny(gray, int(params.get("canny_thresh1", 50)), int(params.get("canny_thresh2", 150)))
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, int(params.get("threshold", 100)),
                            minLineLength=int(params.get("min_line_length", 100)),
                            maxLineGap=int(params.get("max_line_gap", 10)))
    result = _ensure_bgr(image).copy()
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
    return result


# ---------------------------------------------------------------------------
# 11. CLAHE
# ---------------------------------------------------------------------------
@register("clahe", "CLAHE (Kontrast İyileştirme)",
          "Yerel kontrast iyileştirme. Düşük kontrastlı görüntülerde detayları ortaya çıkarır.",
          [{"name": "clip_limit", "display_name": "Clip Limit", "type": "float", "min": 1.0, "max": 20.0, "default": 2.0, "step": 0.5},
           {"name": "grid_size", "display_name": "Grid Boyutu", "type": "int", "min": 2, "max": 16, "default": 8, "step": 1}])
def clahe_enhance(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    clip = float(params.get("clip_limit", 2.0))
    grid = int(params.get("grid_size", 8))
    if len(image.shape) == 3 and image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        gray = _ensure_gray(image)
        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
        return cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# 12. Bilateral Filter
# ---------------------------------------------------------------------------
@register("bilateral_filter", "Bilateral Filtre",
          "Kenarları koruyarak gürültüyü azaltır. Kenar tespit öncesi idealdir.",
          [{"name": "d", "display_name": "Komşuluk Çapı", "type": "int", "min": 1, "max": 15, "default": 9, "step": 2},
           {"name": "sigma_color", "display_name": "Sigma Color", "type": "int", "min": 10, "max": 200, "default": 75, "step": 5},
           {"name": "sigma_space", "display_name": "Sigma Space", "type": "int", "min": 10, "max": 200, "default": 75, "step": 5}])
def bilateral_filter(image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    return cv2.bilateralFilter(_ensure_bgr(image), int(params.get("d", 9)),
                               int(params.get("sigma_color", 75)), int(params.get("sigma_space", 75)))
