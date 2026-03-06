#include <WiFi.h>
#include <time.h>
#include <Ticker.h>
#include <WiFiClientSecure.h>
#include <AsyncMQTT_ESP32.h>

HardwareSerial LORA(2); // RX2=GPIO16, TX2=GPIO17

const char* WIFI_SSID = "must be chaged";
const char* WIFI_PASS = "same";

// ======= MQTT =======
const char* MQTT_HOST = "ip add";
const int MQTT_PORT = 8883;
const char* MQTT_CLIENT_ID = "esp32-gw-01";

const char* GW_STATUS_TOPIC = "trash/gw/status";

const uint8_t MQTT_QOS = 1;
const bool MQTT_RETAIN = true;

// ======= TLS CA CERTIFICATE =======
const char* mqtt_ca = \
"-----BEGIN CERTIFICATE-----\n"
"PASTE_YOUR_CA_CERTIFICATE_HERE\n"
"-----END CERTIFICATE-----\n";

bool ntpOk = false;

// ======= NETWORK =======
WiFiClientSecure secureClient;
AsyncMqttClient mqtt;

Ticker mqttReconnectTimer;
Ticker wifiReconnectTimer;

// ======= LoRa Serial =======
HardwareSerial LORA(2);

String hexToText(const String& hex) {
  String out = "";
  for (int i = 0; i + 1 < (int)hex.length(); i += 2) {
    String byteStr = hex.substring(i, i + 2);
    char c = (char)strtol(byteStr.c_str(), nullptr, 16);
    out += c;
  }
  return out;
}

String textToHex(const String& txt) {
  String hex = "";
  for (int i = 0; i < (int)txt.length(); i++) {
    byte b = (byte)txt[i];
    if (b < 16) hex += "0";
    hex += String(b, HEX);
  }
  hex.toUpperCase();
  return hex;
}

void sendAT(const String& cmd, int waitMs = 250) {
  LORA.println(cmd);
  delay(waitMs);
}

void loraStopRX() {
  sendAT("AT+TEST=STOPRX", 250);
  delay(150);
}

void loraEnterRX() {
  sendAT("AT+TEST=RXLRPKT", 250);
}

void loraSendText(const String& text) {
  String hex = textToHex(text);
  loraStopRX();
  delay(200);
  sendAT("AT+TEST=TXLRPKT,\"" + hex + "\"", 900);
  delay(150);
  loraEnterRX();
}

String bin1State = "UNKNOWN";
String bin2State = "UNKNOWN";

int bin1TVOC = -1, bin1ECO2 = -1;
int bin2TVOC = -1, bin2ECO2 = -1;

void setBinState(const String& binId, const String& st) {
  if (binId == "BIN1") bin1State = st;
  if (binId == "BIN2") bin2State = st;
}

String getBinState(const String& binId) {
  if (binId == "BIN1") return bin1State;
  if (binId == "BIN2") return bin2State;
  return "UNKNOWN";
}

bool isValidState(const String& st) {
  return (st == "EMPTY" || st == "HALF" || st == "FULL");
}

String pickOtherNotFull(const String& whoIsFull) {
  String other = (whoIsFull == "BIN1") ? "BIN2" : "BIN1";
  String st = getBinState(other);
  if (st == "EMPTY" || st == "HALF") return other;
  return "NONE";
}

int parseKeyInt(const String& msg, const String& key) {
  int p = msg.indexOf(key);
  if (p < 0) return -1;
  p += key.length();
  int end = msg.indexOf(':', p);
  String num = (end < 0) ? msg.substring(p) : msg.substring(p, end);
  num.trim();
  return num.toInt();
}

String jsonIntOrNull(int v) {
  return (v >= 0) ? String(v) : "null";
}

void connectWiFi() {
  Serial.println("WiFi connect...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void setupTimeUTC() {

  configTime(0, 0, "pool.ntp.org", "time.nist.gov", "time.google.com");

  ntpOk = false;

  Serial.print("NTP sync");

  for (int i = 0; i < 40; i++) {
    struct tm t;
    if (getLocalTime(&t, 300)) {
      if (t.tm_year > 120) {
        ntpOk = true;
        break;
      }
    }
    Serial.print(".");
    delay(300);
  }

  Serial.println();

  if (ntpOk)
    Serial.println("NTP synced");
  else
    Serial.println("NTP failed");
}

String iso8601UtcNow() {

  if (!ntpOk) return "";

  struct tm t;

  if (!getLocalTime(&t, 200)) return "";

  char buf[25];

  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);

  return String(buf);
}

void connectMqtt() {
  Serial.println("MQTT connect...");
  mqtt.connect();
}

void onMqttConnect(bool sessionPresent) {

  Serial.print("MQTT connected sessionPresent=");
  Serial.println(sessionPresent);

  mqtt.publish(GW_STATUS_TOPIC, MQTT_QOS, true, "online");
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {

  Serial.print("MQTT disconnected reason=");
  Serial.println((int)reason);

  if (WiFi.isConnected()) {
    mqttReconnectTimer.once(2, connectMqtt);
  }
}

void onWiFiEvent(WiFiEvent_t event) {

  switch (event) {

    case ARDUINO_EVENT_WIFI_STA_GOT_IP:

      Serial.println("WiFi connected");
      Serial.println(WiFi.localIP());

      setupTimeUTC();
      connectMqtt();

      break;

    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:

      Serial.println("WiFi lost");

      mqttReconnectTimer.detach();
      wifiReconnectTimer.once(2, connectWiFi);

      break;

    default:
      break;
  }
}

void publishJson(const String& binId, const String& state) {

  int tvoc = -1;
  int eco2 = -1;

  if (binId == "BIN1") { tvoc = bin1TVOC; eco2 = bin1ECO2; }
  if (binId == "BIN2") { tvoc = bin2TVOC; eco2 = bin2ECO2; }

  String ts = iso8601UtcNow();
  String tsJson = (ts.length() > 0) ? ("\"" + ts + "\"") : "null";

  String json =
    "{"
      "\"bin_id\":\"" + binId + "\","
      "\"ts_device\":" + tsJson + ","
      "\"state\":\"" + state + "\","
      "\"tvoc_ppb\":" + jsonIntOrNull(tvoc) + ","
      "\"eco2_ppm\":" + jsonIntOrNull(eco2) +
    "}";

  String topic = "trash/bins/" + binId + "/telemetry";

  Serial.println(json);

  if (!mqtt.connected()) return;

  mqtt.publish(topic.c_str(), MQTT_QOS, MQTT_RETAIN, json.c_str(), json.length());
}

void setup() {

  Serial.begin(115200);
  delay(500);

  Serial.printf("ESP SDK: %s\n", ESP.getSdkVersion());

  secureClient.setCACert(mqtt_ca);
  mqtt.setSecure(true);

  WiFi.onEvent(onWiFiEvent);

  mqtt.onConnect(onMqttConnect);
  mqtt.onDisconnect(onMqttDisconnect);

  mqtt.setServer(MQTT_HOST, MQTT_PORT);

  mqtt.setClientId(MQTT_CLIENT_ID);
  mqtt.setCleanSession(false);

  mqtt.setWill(GW_STATUS_TOPIC, MQTT_QOS, true, "offline");

  mqtt.setCredentials("esp32gw","waste2026");

  connectWiFi();

  // LoRa init
  LORA.begin(9600, SERIAL_8N1, 16, 17);

  delay(1500);

  sendAT("AT");
  sendAT("AT+MODE=TEST");
  sendAT("AT+TEST=RFCFG,868000000,SF7,125,4,8,14,ON,OFF");

  loraEnterRX();

  Serial.println("LoRa listening...");
}

void loop() {

  while (LORA.available()) {

    String line = LORA.readStringUntil('\n');
    line.trim();

    if (!line.length()) continue;

    int q1 = line.indexOf('"');
    int q2 = line.lastIndexOf('"');

    if (q1 < 0 || q2 <= q1) continue;

    String hex = line.substring(q1 + 1, q2);

    String msg = hexToText(hex);
    msg.trim();

    if (!msg.length()) continue;

    Serial.print("RECV: ");
    Serial.println(msg);

    int sep = msg.indexOf(':');

    if (sep < 0) continue;

    String binId = msg.substring(0, sep);
    String rest = msg.substring(sep + 1);

    binId.trim();
    rest.trim();

    if (rest.startsWith("GAS")) {

      int tv = parseKeyInt(msg, "TVOC=");
      int ec = parseKeyInt(msg, "eCO2=");

      if (binId == "BIN1") { bin1TVOC = tv; bin1ECO2 = ec; }
      if (binId == "BIN2") { bin2TVOC = tv; bin2ECO2 = ec; }

      continue;
    }

    String st = rest;

    if (!isValidState(st)) continue;

    String prev = getBinState(binId);

    setBinState(binId, st);

    if (prev != st) {

      publishJson(binId, st);

      if (st == "FULL") {

        String chosen = pickOtherNotFull(binId);
        String reply = "NEAREST:" + chosen;

        loraSendText(reply);
      }
    }
  }
}