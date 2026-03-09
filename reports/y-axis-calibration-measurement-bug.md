# Y-Ekseni (Çap) Kalibrasyon vs Ölçüm Uyumsuzluk Analizi

## 🔴 KRİTİK SORUN TESPİT EDİLDİ

Kalibrasyon sırasında doğru ölçüm yapılıyor, ancak ölçüm aşamasında yanlış sonuç veriyor.

---

## Kod Karşılaştırması

### 1. Kalibrasyon (`app.py` - `detect_edges`)

```python
# Kenar Haritası Modu (satır 263-297):
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (mk, mk))
binary = cv2.dilate(gray, kernel, iterations=1)  # ⬅️ Dİlate KULLANILIYOR
_, binary = cv2.threshold(binary, 20, 255, cv2.THRESH_BINARY)

col = binary[:, click_x]
white_pixels = np.where(col > 0)[0]
top_y = int(white_pixels[0])
bottom_y = int(white_pixels[-1])
```

### 2. Ölçüm (`profile_extractor.py` - `extract_profile`)

```python
# Kenar Haritası Modu (satır 49-72):
binary_edges = cv2.GaussianBlur(gray, (3, 3), 0)  # ⬅️ Blur KULLANILIYOR
_, binary_edges = cv2.threshold(binary_edges, 20, 255, cv2.THRESH_BINARY)

# İçi dolduruluyor:
for x in range(w):
    col = binary_edges[:, x]
    white_idx = np.where(col > 0)[0]
    if len(white_idx) > 0:
        y1 = white_idx[0]
        y2 = white_idx[-1]
        if y2 - y1 > 5:
            solid_mask[y1:y2+1, x] = 255  # ⬅️ Farklı maske!

# Morfolojik işlem (DAHA AGRESİF):
mk = morph_ksize + 2  # ⬅️ Kalibrasyondan 2 fazla!
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (mk, mk))
binary = cv2.morphologyEx(solid_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

# Kenar bulma (satır 108-129):
for x in range(x_start, x_end):
    if is_edge_map and 'binary_edges' in locals():
        col = binary_edges[:, x]  # ⬅️ binary_edges kullanılıyor
    else:
        col = mask[:, x]
    white_pixels = np.where(col > 0)[0]
    top = int(white_pixels[0])
    bottom = int(white_pixels[-1])
    diameter_px.append(bottom - top)
```

---

## 🔴 TEMEL FARKLAR

| Özellik | Kalibrasyon (`detect_edges`) | Ölçüm (`extract_profile`) |
|---------|------------------------------|---------------------------|
| **Ön İşleme** | `cv2.dilate()` | `cv2.GaussianBlur()` |
| **Kernel Boyutu** | `morph_ksize` (varsayılan 5) | `morph_ksize + 2` (varsayılan 7) |
| **Morfoloji** | Yok (sadece dilate) | MORPH_CLOSE + MORPH_OPEN |
| **Maske Kaynağı** | Doğrudan `binary` | `binary_edges` → `solid_mask` → `binary` |
| **Kenar Çizgisi** | `binary[:, click_x]` | `binary_edges[:, x]` |

---

## ❌ SORUN: FARKLI ALGORİTMALAR KULLANILIYOR!

### Kalibrasyon:
1. Görüntü → **Dilate** → Threshold → **Tek bir kolondan** kenar bul

### Ölçüm:
1. Görüntü → **Blur** → Threshold → Solid mask oluştur → **Morfolojik işlemler** → Kenar bul

**Dilate** kenarları kalınlaştırır (daha içeri/alta çizer)
**Blur** kenarları yumuşatır (daha dışarı/üstte çizer)

Bu iki farklı yaklaşım **farklı piksel değerleri** üretir!

---

## 📊 Örnek Senaryo

```
Gerçek kenarlar:        Kalibrasyon (dilate):    Ölçüm (blur):
    |                        |                        |
    |  ← üst kenar           |  ← üst kenar           |
   _|_                      _|_                      _|_
  |   |                    |   |                    |   |
  |   |                    |   |                    |   |
  |   | ← alt kenar        |   | ← alt kenar        |   |
   -|-                      -|-                      -|-
    |                        |  ← alt kenar           |
    |                        |                        |
```

**Sonuç:**
- Kalibrasyon: `pixel_distance = 100 px`
- Ölçüm: `diameter_px = 120 px` (farklı!)

---

## ✅ ÇÖZÜM

### Seçenek 1: Ölçümü Kalibrasyonla Aynı Algoritmaya Getir

`profile_extractor.py` dosyasında kenar haritası modunu `detect_edges` ile aynı algoritmayı kullanacak şekilde güncelle:

```python
if is_edge_map:
    # Kalibrasyon ile AYNI algoritmayı kullan
    mk = morph_ksize  # +2 YAPMA!
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (mk, mk))
    binary = cv2.dilate(gray, kernel, iterations=1)  # BLUR yerine Dİlate
    _, binary = cv2.threshold(binary, 20, 255, cv2.THRESH_BINARY)
    
    # solid_mask yerine doğrudan binary kullan
    # ...
```

### Seçenek 2: Kalibrasyonu Ölçümle Aynı Algoritmaya Getir

`detect_edges` fonksiyonunu `profile_extractor` ile aynı algoritmayı kullanacak şekilde güncelle.

---

## 🛠️ ÖNERİLEN DÜZELTME

`profile_extractor.py` satır 49-72'yi şu şekilde değiştir:

```python
if is_edge_map:
    # KENAR HARİTASI MODU - Kalibrasyon ile tutarlı
    mk = morph_ksize  # +2 kaldırıldı - kalibrasyonla aynı
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (mk, mk))
    
    # Kalibrasyon ile AYNI ön işleme
    binary = cv2.dilate(gray, kernel, iterations=1)
    _, binary_edges = cv2.threshold(binary, 20, 255, cv2.THRESH_BINARY)
    
    # Solid mask oluştur
    h, w = binary_edges.shape
    solid_mask = np.zeros_like(binary_edges)
    for x in range(w):
        col = binary_edges[:, x]
        white_idx = np.where(col > 0)[0]
        if len(white_idx) > 0:
            y1 = white_idx[0]
            y2 = white_idx[-1]
            if y2 - y1 > 5:
                solid_mask[y1:y2+1, x] = 255
    
    # Morfolojik temizleme (isteğe bağlı - daha az agresif)
    kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (mk, mk))
    binary = cv2.morphologyEx(solid_mask, cv2.MORPH_CLOSE, kernel2, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel2, iterations=1)
```

---

## ⚠️ ÖNEMli NOT

Bu değişiklik sadece `is_edge_map = True` (kenar haritası modu) için geçerlidir. Normal görüntü modu için de benzer bir tutarsızlık olabilir, kontrol edilmeli.

Normal görüntü modunda:
- Kalibrasyon: Otsu threshold + MORPH_CLOSE + MORPH_OPEN
- Ölçüm: Aynı (tutarlı görünüyor)