#include "klima_model_yeni.h" 
#include <tflm_esp32.h>
#include <eloquent_tinyml.h>
#include <DHT.h>
#include <time.h>  
#include "secrets.h"
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>
#include "WiFi.h"

#define DHTTYPE DHT22  
#define DHTPIN 4
#define TF_NUM_OPS 3
#define ARENA_SIZE 8 * 1024  // Klima modeli biraz daha büyük olabilir
#define AWS_IOT_PUBLISH_TOPIC "esp32/esp32-to-aws"
#define AWS_IOT_SUBSCRIBE_TOPIC "esp32/aws-to-esp32"
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 3 * 3600;  // Türkiye için UTC+3
const int daylightOffset_sec = 0;
#define PUBLISH_INTERVAL 4000  // 4 seconds

DHT dht(DHTPIN, DHTTYPE);

Eloquent::TF::Sequential<TF_NUM_OPS, ARENA_SIZE> tf;

WiFiClientSecure net = WiFiClientSecure();
MQTTClient client = MQTTClient(256);

unsigned long lastPublishTime = 0;

void setup() {
    delay(3000);
    Serial.begin(115200);
    

    Serial.println("KLIMA TINYML TEST");

    tf.setNumInputs(2);
    tf.setNumOutputs(4);

    // Gerekli operasyonları ekleyin
    tf.resolver.AddFullyConnected();
    tf.resolver.AddRelu();
    tf.resolver.AddLogistic();

    while (!tf.begin(klima_model).isOk()) {
        Serial.println(tf.exception.toString());
        delay(1000);
    }

    dht.begin();  // DHT22 başlat
      analogSetAttenuation(ADC_11db);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.println("ESP32 connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  connectToAWS();
  initTime(); 
}

void loop() {
    client.loop();
    // DHT22 sensöründen sıcaklık ve nem verilerini oku
    float humidity = dht.readHumidity(); // Nem yüzdesi
    float temperature = dht.readTemperature(); // Sıcaklık (Celsius cinsinden)

    // Sensör verisi okunamazsa hata mesajı yazdır
    if (isnan(humidity) || isnan(temperature)) {
        Serial.println("Failed to read from DHT sensor!");
        return;
    }

      

  if (millis() - lastPublishTime > PUBLISH_INTERVAL) {
    sendToAWS("humidity", humidity, "cm3");
    sendToAWS("temperature", temperature, "celsius");
    lastPublishTime = millis();
  }

    // Sıcaklık ve nem verilerini yazdır
    Serial.print("Humidity: ");
    Serial.println(humidity);
    Serial.print("Temperature: ");
    Serial.println(temperature);

    // Eğitimde kullandığımız MinMaxScaler'a göre verileri ölçeklendir
    float scaledHumidity = humidity / 100.0; // Nem 0-100 arası, 0-1 aralığına ölçeklendir
    float scaledTemperature = temperature / 50.0; // Sıcaklık 0-50 arası, 0-1 aralığına ölçeklendir (örnek, ihtimale göre 50°C'yi sınırladık)

    // Giriş verisi olarak ölçeklendirilmiş sıcaklık ve nem verilerini hazırla
    float inputs[2] = {scaledTemperature, scaledHumidity};

    // Tahmin yap
    if (!tf.predict(inputs).isOk()) {
        Serial.println(tf.exception.toString());
        return;
    }

    // Modelin çıktılarından tahmin edilen dört değeri al
    float temp_up = tf.output(0);        // Sıcaklık artırma durumu
    float temp_down = tf.output(1);      // Sıcaklık azaltma durumu
    float humidity_up = tf.output(2);    // Nem artırma durumu
    float humidity_down = tf.output(3);  // Nem azaltma durumu

    // Çıktıları yazdır
    Serial.print("Sıcaklık artırma: ");
    Serial.println(temp_up > 0.5 ? "Açık" : "Kapalı");

    Serial.print("Sıcaklık azaltma: ");
    Serial.println(temp_down > 0.5 ? "Açık" : "Kapalı");

    Serial.print("Nem artırma: ");
    Serial.println(humidity_up > 0.5 ? "Açık" : "Kapalı");

    Serial.print("Nem azaltma: ");
    Serial.println(humidity_down > 0.5 ? "Açık" : "Kapalı");

    // Ayırıcı çizgi
    Serial.println("********************************");

    delay(2000); // 2 saniye bekle
}


void connectToAWS() {
  // Configure WiFiClientSecure to use the AWS IoT device credentials
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  // Connect to the MQTT broker on the AWS endpoint we defined earlier
  client.begin(AWS_IOT_ENDPOINT, 8883, net);

  // Create a handler for incoming messages
  client.onMessage(messageHandler);

  Serial.print("ESP32 connecting to AWS IOT");

  while (!client.connect(THINGNAME)) {
    Serial.print(".");
    delay(100);
  }
  Serial.println();

  if (!client.connected()) {
    Serial.println("ESP32 - AWS IoT Timeout!");
    return;
  }

  // Subscribe to a topic, the incoming messages are processed by messageHandler() function
  client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC);

  Serial.println("ESP32  - AWS IoT Connected!");
}


void initTime() {
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.print("Zaman eşitleniyor");
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.println("Zaman eşitlendi!");
}

void sendToAWS(String type, float value, String unit){
  StaticJsonDocument<200> message;
  message["type"] = type;
  message["value"] = value;
  message["unit"] = unit;

  time_t now;
  time(&now);
  message["timestamp"] = now;

  char messageBuffer[512];
  serializeJson(message, messageBuffer);

  client.publish(AWS_IOT_PUBLISH_TOPIC, messageBuffer);

  Serial.println("sent:");
  Serial.print("- topic: ");
  Serial.println(AWS_IOT_PUBLISH_TOPIC);
  Serial.print("- payload:");
  Serial.println(messageBuffer);
}


void messageHandler(String &topic, String &payload) {
  Serial.println("received:");
  Serial.println("- topic: " + topic);
  Serial.println("- payload:");
  Serial.println(payload);

  // You can process the incoming data as json object, then control something
  /*
  StaticJsonDocument<200> doc;
  deserializeJson(doc, payload);
  const char* message = doc["message"];
  */
}
