# Kalibrasyon + Ölçüm + Arayüz Derin Denetim Raporu

Tarih: 2026-03-09  
Kapsam: `backend` ve `frontend` tarafında kalibrasyon/ölçüm/zoom/X-kalibrasyon akışlarının kod incelemesi  
Amaç: Hataları kök neden seviyesinde çıkarıp adım adım düzeltme planı hazırlamak

---

## 1) Genel Sonuç

Sistemdeki sorunlar tek bir bug değil, birden fazla katmanda birikmiş durumda:

1. **Algoritma tutarlılığı kısmen iyileştirilmiş**, ancak kenar haritası ölçüm akışında hala kırılgan noktalar var.  
2. **Zoom + tıklama + overlay koordinat sistemi** birlikte çalışıyor gibi görünse de bazı koşullarda kayma üretebilecek tasarım riskleri mevcut.  
3. **Arayüzde doğrudan buglar var** (ör. yanlış tab ID kontrolü), bu da kullanıcıya hatalı durum/başlık gösterebiliyor.  
4. X/Y kalibrasyon durumu için **global state kullanımı** (backend) çoklu görsel senaryolarında yanlış ölçüm riskini artırıyor.

---

## 2) Kritik Bulgular (P1)

### P1-1) Edge-map ölçümünde profil çıkarma ile kalibrasyon hala birebir aynı değil

**Durum:**  
`profile_extractor.py` içinde edge-map dalı, geçmişe göre düzeltilmiş olsa da ölçümde kullanılan kolon kaynağı (`binary_edges`) sparse (seyrek) kalabiliyor. Bu, bazı x kolonlarında `white_pixels` boş gelmesine ve çapın `0` yazılmasına neden olabiliyor.

**Kod izi:**  
- `backend/profile_extractor.py` → `extract_profile()`  
  - edge-map dalında `binary_edges` üretiliyor  
  - sonra profil döngüsünde `if is_edge_map ... col = binary_edges[:, x]` kullanılıyor  
  - `white_pixels` boşsa `diameter_px=0` atanıyor

**Etkisi:**  
- Gradient tabanlı bölüm tespitinde (measurement engine) sahte geçişler oluşabilir.  
- Bölüm sınırları ve uzunluklar kayar, bazı durumlarda “yarım çizgi” veya “kısa bölüm” etkisi oluşabilir.

---

### P1-2) Kalibrasyon tıklaması yapılan panel ile backend’e gönderilen image_id ayrışabiliyor

**Durum:**  
Frontend’de tıklama koordinatı tıklanan görüntüden hesaplanıyor, ama Y-kalibrasyon için backend’e gönderilen `image_id` her zaman `processedImageId || imageId`.

**Kod izi:**  
- `frontend/js/app.js` → `handleAutoEdgeClick()`  
  - `clickX/clickY`: tıklanan panelin `refImg` üstünden hesaplanıyor  
  - `calImageId = state.processedImageId || state.imageId`

**Etkisi:**  
- Teoride orijinal/işlenmiş görseller arasında boyut/geometry farkı oluşursa yanlış kolona bakılabilir.  
- Şu an algoritmalar çoğunlukla boyutu koruyor, ama tasarım olarak kırılgan.

---

### P1-3) Backend kalibrasyonu global ve görselden bağımsız tutuluyor

**Durum:**  
`active_calibration` tek global state. Yeni görsele geçince otomatik sıfırlama/bağlama yok.

**Kod izi:**  
- `backend/app.py` global `active_calibration`  
- `/api/measure` doğrudan bu state’i kullanıyor

**Etkisi:**  
- Kullanıcı yeni parça/görsel yükleyip ölçerse eski kalibrasyonla ölçebilir.  
- Bu durum yanlış sonucu “algoritma hatası” gibi gösterebilir.

---

## 3) Orta Seviye Bulgular (P2)

### P2-1) Tab ID kontrol bugı: ölçüm sekmesinde başlık reset dalı çalışmıyor

**Durum:**  
HTML’de ölçüm tabı `tab-measure`, JS’de kontrol `tab-measurement`.

**Kod izi:**  
- `frontend/index.html` → `id="tab-measure"`  
- `frontend/js/app.js` → `resetOverlays()` içinde `activeTabId === 'tab-measurement'`

**Etkisi:**  
- Sekme geçişinde ölçüm başlık/temizlik akışının bir kısmı atlanır.  
- Kullanıcı “state karıştı” hissi yaşayabilir.

---

### P2-2) Zoom + transform tabanlı koordinat yaklaşımı hassas, sınır clamp yok

**Durum:**  
X1/X2 manuel input veya slider değerleri için hard clamp yok. Negatif veya aşırı değerler girilebilir.

**Kod izi:**  
- `frontend/js/app.js` → `setX1Value()`, `setX2Value()`

**Etkisi:**  
- Negatif/taşan koordinatlar backend’e gidebilir.  
- Çizgi kayması ve anlamsız X kalibrasyon oranı çıkabilir.

---

### P2-3) CSS’de `.image-canvas-wrapper` iki kez tanımlanmış

**Durum:**  
Aynı selector farklı bloklarda tekrar tanımlanmış; zoom sonrası son blok baskın oluyor.

**Kod izi:**  
- `frontend/css/style.css` (erken blok + dosya sonu zoom bloğu)

**Etkisi:**  
- Tasarım değiştikçe beklenmeyen layout/overlay hizası sorunları üretme riski.  
- Bakımı zorlaştırıyor.

---

## 4) Düşük Seviye Bulgular (P3)

### P3-1) `click_y` backend edge detect’te alınmış ama kullanılmıyor

**Kod izi:**  
- `backend/app.py` → `detect_edges()` içinde `click_y` okunuyor, algoritmada etkisiz.

**Etkisi:**  
- Doğrudan bug değil; ama yanlış beklenti yaratıyor.

---

### P3-2) `ASPECT_CORRECTION_FACTOR` fallback yaklaşımı görüntü/kamera bağımlı

**Kod izi:**  
- `backend/calibration.py` → `ASPECT_CORRECTION_FACTOR = 1.2762`

**Etkisi:**  
- X kalibrasyon yapılmayan durumlarda sistematik sapma riski.

---

## 5) Doğrulanmış / Kısmen Çözülmüş Noktalar

1. Geçmişte raporlanan “kalibrasyon vs ölçüm farklı preprocessing” sorunu için önemli düzeltme yapılmış.  
2. `profile_extractor.py` edge-map dalında `dilate` ve kernel tutarlılığı iyileştirilmiş.  
3. X-kalibrasyon UI, slider ve overlay çizimi aktif çalışacak şekilde eklenmiş.

Not: Buna rağmen P1/P2 bulguları nedeniyle sistem tamamen stabil sayılmaz.

---

## 6) Adım Adım Fix Planı (Önerilen Sıra)

### Faz A (Hızlı güvenlik düzeltmeleri)

1. `tab-measurement` → `tab-measure` bug fix  
2. `setX1Value/setX2Value` için min/max clamp eklenmesi  
3. X/Y kalibrasyon state reset kuralı: yeni görsel yüklenince kullanıcıya net uyarı + opsiyonel otomatik reset

### Faz B (Koordinat ve veri tutarlılığı)

4. `handleAutoEdgeClick()` içinde tıklanan panel ile gönderilen `image_id` bağını netleştirme  
5. “Bu kalibrasyon hangi image_id üzerinde alındı?” bilgisini state’e kaydetme  
6. Ölçüm çağrısında bu bilgi ile doğrulama (uyuşmazsa uyarı veya bloklama)

### Faz C (Edge-map ölçüm stabilizasyonu)

7. `extract_profile()` edge-map akışında profil ölçümü için sparse `binary_edges` yerine daha stabil kolon kaynağı stratejisi  
8. `diameter_px=0` kolonları için boşluk doldurma/interpolasyon kuralı  
9. `measurement_engine` geçiş tespitinde outlier baskılama (0-dip filtreleme)

### Faz D (Zoom/overlay teknik borç temizliği)

10. CSS’de tekil `.image-canvas-wrapper` tanımı  
11. Zoom transform + marker çizimi için net tek koordinat sistemi (dokümante)  
12. Regression test checklist: zoom seviyeleri %25/%100/%200/%400 + pan durumları

---

## 7) Test Matrisi (Fix Sonrası Kullanılacak)

1. **Y kalibrasyon testi**: aynı görselde 3 farklı noktada tekrar ölçüm  
2. **X kalibrasyon testi**: zoom yok / zoom var / pan var, aynı referans üzerinde fark <= 1 px  
3. **Sekme geçiş testi**: Algorithms ↔ Calibration ↔ Measurement geçişlerinde başlık/overlay reset doğrulama  
4. **Görsel değişim testi**: yeni upload sonrası eski kalibrasyonla ölçüm bloklama/uyarı  
5. **Edge-map testi**: Canny/Sobel/Laplacian ile bölüm sayısı ve boy toplamı karşılaştırması

---

## 8) Son Not

Kod tabanı önceki sürümlere göre daha iyi durumda, ancak özellikle koordinat yönetimi ve edge-map profil kararlılığı tarafında kalan teknik borçlar kullanıcıya “ölçüm bazen kayıyor” şeklinde yansıyor.  
Öneri: Önce Faz A + Faz B hızlıca uygulanıp stabilite artırılsın, sonra Faz C ile ölçüm kalitesi sıkılaştırılsın.
