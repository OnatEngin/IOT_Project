## 🚀 Kurulum

### 1. ESP32 Firmware Yükleme

- Arduino IDE veya PlatformIO ile `arduino/esp2aws.ino` dosyasını aç.
- `WiFi` bilgilerini ve `MQTT` ayarlarını `.ino` dosyasındaki ilgili alanlara gir.
- AWS IoT sertifikalarını `cert/` klasörüne yerleştir ve `cert.h` içinde referansla.
- ESP32'yi bağla ve yüklemeyi yap.

### 2. Python Arayüzü Çalıştırma

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
cp arayuz/.env.example arayuz/.env
# .env içindeki AWS anahtarlarını doldur

# Uygulamayı çalıştır
python arayuz/cloudwatch_fetcher.py
