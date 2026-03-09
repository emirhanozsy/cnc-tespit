# Kalibrasyon vs Ölçüm Uyumsuzluk Analizi

## Sorun Özeti
Kullanıcı X-ekseni kalibrasyonu sırasında doğru bir çizgi ölçüyor, ancak ölçüm aşamasında çizgiler "yarıya kadar" çekiyor - yani uzunluk ölçümleri yanlış çıkıyor.

---

## Kod Akış Analizi

### 1. X-Ekseni Kalibrasyon Süreci

**Frontend (`app.js` satır 493-509):**
```javascript
const scaleX = refImg.naturalWidth / rect.width;
const clickX = Math.round((e.clientX - rect.left) * scaleX);
```
- Tıklama koordinatı, görüntünün doğal boyutlarına dönüştürülüyor
- `handleXCalClick()` fonksiyonu `clickX` değerini saklıyor

**Backend (`calibration.py` satır 168-185):**
```python
def calculate_x_calibration(reference_length_mm: float, x1: float, x2: float) -> float:
    pixel_distance = abs(x2 - x1)
    return pixel_distance / reference_length_mm
```
- X1 ve X2 arasındaki piksel mesafesi / bilinen uzunluk = `pixels_per_mm_x`

### 2. Ölçüm Süreci

**Backend (`measurement_engine.py` satır 32-97):**
```python
diameter_px = np.array(profile["diameter_px"], dtype=float)
# ... gradient analizi ile bölüm tespiti ...
width_px = e - s  # Bölüm genişliği (piksel)
length_mm = calibration.pixels_to_mm_x(width_px)
```

**Profil Çıkarma (`profile_extractor.py` satır 98-129):**
```python
bbox = cv2.boundingRect(main_contour)
x_start, y_start, bbox_w, bbox_h = bbox
x_end = x_start + bbox_w

for x in range(x_start, x_end):
    col = mask[:, x]
    white_pixels = np.where(col > 0)[0]
    # ... üst/alt kenar bul ...
    diameter_px.append(bottom - top)
```

---

## 🔴 SORUN TESPİTİ

### Temel Sorun: Koordinat Sistemi Uyumsuzluğu

**Kalibrasyonda:**
- Kullanıcı **görüntü üzerinde** tıklıyor
- Tıklanan X koordinatları **orijinal görüntünün piksel koordinatları**
- Örnek: Kullanıcı x=100 ve x=600 noktalarına tıkladı → 500 piksel mesafe

**Ölçümde:**
- `profile_extractor.py` **kontur bounding box'ını** kullanıyor
- `x_start = bbox.x` (parçanın başladığı x koordinatı)
- `diameter_px` dizisi `x_start`'tan `x_end`'e kadar olan sütunları içeriyor
- **`diameter_px` dizisinin indeksleri 0'dan başlıyor!**

```python
# measurement_engine.py'de:
x_start = profile["x_start"]  # Örneğin 100

# Bölüm tespitinde:
transitions.append(0)  # Dizinin 0. indeksinden başlanıyor
# ...
"x_start_rel": s,           # 0-tabanlı indeks
"x_start_abs": x_start + s, # Gerçek x koordinatı
"width_px": e - s,          # ⚠️ Bu doğru!
```

**`width_px = e - s` hesaplaması DOĞRU** - bu piksel cinsinden genişlik.

---

### 🟡 İkincil Sorun: Bounding Box vs Gerçek Kenarlar

**Profil çıkarma sırasında:**
```python
bbox = cv2.boundingRect(main_contour)
```
- `cv2.boundingRect()` konturun **dikdörtgen sınırlayıcı kutusunu** verir
- Bu kutu, konturun en sol/sağ/üst/alt noktalarını içerir
- **Ancak** parçanın gerçek kenarları bounding box'tan farklı olabilir!

**Örnek:**
```
Gerçek parça:     Bounding Box:
   ████           ████████
  ██████          ████████
 ████████   →     ████████
  ██████          ████████
   ████           ████████
```

Eğimli bir parçada bounding box, gerçek kenarlardan daha geniş olabilir.

---

### 🟠 Üçüncül Sorun: Kenar Haritası Modu

**`profile_extractor.py` satır 46-72:**
```python
mean_brightness = float(np.mean(gray))
is_edge_map = mean_brightness < 40

if is_edge_map:
    # KENAR HARİTASI MODU
    binary_edges = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary_edges = cv2.threshold(binary_edges, 20, 255, cv2.THRESH_BINARY)
    
    # İçi boş haritadan solid maske üret
    for x in range(w):
        col = binary_edges[:, x]
        white_idx = np.where(col > 0)[0]
        if len(white_idx) > 0:
            y1 = white_idx[0]
            y2 = white_idx[-1]
            if y2 - y1 > 5:
                solid_mask[y1:y2+1, x] = 255
```

**Sorun:** Kenar haritası modunda, her sütunda ilk ve son beyaz piksel arası dolduruluyor. Bu, **gerçek parça genişliğinden farklı** olabilir!

---

## 🔵 Olası Senaryolar

### Senaryo 1: Kalibrasyon ve Ölçüm Farklı Görüntülerde
- Kullanıcı **orijinal görüntüde** kalibrasyon yapıyor
- Kullanıcı **işlenmiş görüntüde** (Canny vb.) ölçüm yapıyor
- İşlenmiş görüntünün boyutları veya içeriği farklı olabilir

### Senaryo 2: Kontur Tespiti Farklı Bölge Buluyor
- Kalibrasyonda kullanıcı belirli bir bölgeyi seçiyor
- Ölçümde `findContours()` farklı bir bölge buluyor
- Bounding box, kullanıcının kalibre ettiği bölgeden farklı olabilir

### Senaryo 3: Bölüm Tespiti Yanlış Noktaları Buluyor
- Gradient tabanlı bölüm tespiti, yanlış geçiş noktaları buluyor
- `width_px = e - s` yanlış hesaplanıyor

---

## 📊 Test Önerileri

### Test 1: Koordinat Karşılaştırması
```python
# Kalibrasyonda:
print(f"X1: {x1}, X2: {x2}, Mesafe: {x2-x1} px")

# Ölçümde (profile_extractor.py'de):
print(f"Bounding Box: x_start={x_start}, x_end={x_end}, width={bbox_w}")
print(f"Kontur alanı: {cv2.contourArea(main_contour)}")
```

### Test 2: Görsel Doğrulama
```python
# Ölçüm overlay'ine bounding box çiz
cv2.rectangle(overlay, (x_start, y_start), (x_end, y_start + bbox_h), (255, 0, 0), 2)
```

### Test 3: Kalibrasyon Noktalarını Göster
```python
# X kalibrasyon noktalarını overlay'de göster
cv2.line(overlay, (x1, 0), (x1, h), (0, 255, 255), 2)  # Sarı dikey çizgi
cv2.line(overlay, (x2, 0), (x2, h), (0, 255, 255), 2)
```

---

## 🛠️ Önerilen Çözümler

### Çözüm 1: Debug Overlay Ekle
`draw_profile_overlay()` fonksiyonuna bounding box ve kalibrasyon noktalarını çizen debug modu ekle.

### Çözüm 2: Kalibrasyon ve Ölçüm Aynı Görüntüde Zorla
Kullanıcının kalibrasyon yaptığı görüntü ile ölçüm yaptığı görüntünün aynı olduğunu garanti et.

### Çözüm 3: Kontur Tespitini İyileştir
- Daha agresif morfolojik operatörler kullan
- ROI (Region of Interest) ile kalibrasyon bölgesini sınırla

### Çözüm 4: Piksel/mm Doğrulaması Ekle
```python
# Ölçüm sonucunda:
print(f"pixels_per_mm_x: {calibration.pixels_per_mm_x}")
print(f"pixels_per_mm_y: {calibration.pixels_per_mm_y}")
print(f"width_px: {width_px}")
print(f"length_mm: {length_mm}")
# Beklenen: length_mm = width_px / pixels_per_mm_x
```

---

## Sonuç

**En olası neden:** Kalibrasyon sırasında kullanıcı belirli bir bölgeyi işaretlerken, ölçüm sırasında `profile_extractor` farklı bir bölgeyi (bounding box üzerinden) hesaplıyor. Bu iki bölge arasında uyumsuzluk var.

**Hızlı doğrulama için:**
1. Kalibrasyon sırasında seçilen X1 ve X2 koordinatlarını kaydet
2. Ölçüm sırasında bulunan bounding box'ın x_start ve x_end değerleriyle karşılaştır
3. Eğer farklıysa, sorun koordinat uyumsuzluğudur