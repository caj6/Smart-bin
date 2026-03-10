// ===================== ESP32 Gateway: LoRa RX -> JSON -> MQTT Publish (QoS1 + Retain + Persistent + Sober) =====================
#include <WiFi.h>
#include <time.h>
#include <Ticker.h>

// AsyncMQTT_ESP32 is based on AsyncMqttClient
#include <AsyncMQTT_ESP32.h>

HardwareSerial LORA(2); // RX2=GPIO16, TX2=GPIO17

// ======= WIFI =======
const char* WIFI_SSID = "+++";
const char* WIFI_PASS = "neima123";

// ======= MQTT (Mosquitto on your PC) =======
const char* MQTT_HOST = "10.173.156.52";
const int   MQTT_PORT = 1883;

// ✅ MQTT credentials (required if allow_anonymous false)
const char* MQTT_USER = "esp32gw";
const char* MQTT_PASS = "waste2026";

// ======= MQTT Session =======
// IMPORTANT: stable client id for persistent session (cleanSession=false)
const char* MQTT_CLIENT_ID = "esp32-gw-01";

// Gateway status (LWT + online)
const char* GW_STATUS_TOPIC = "trash/gw/status";

// Publish options you want
const uint8_t MQTT_QOS = 1;
const bool    MQTT_RETAIN = true;

// ======= NTP (UTC time for ts_device) =======
bool ntpOk = false;

// Async MQTT client + reconnect timers
AsyncMqttClient mqtt;
Ticker mqttReconnectTimer;
Ticker wifiReconnectTimer;

// ---------------- HEX HELPERS ----------------
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

// ---------------- AT HELPERS ----------------
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

// ---------------- BIN STATES + GAS CACHE ----------------
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

// returns BIN1 or BIN2 if available, otherwise NONE
String pickOtherNotFull(const String& whoIsFull) {
  String other = (whoIsFull == "BIN1") ? "BIN2" : "BIN1";
  String st = getBinState(other);
  if (st == "EMPTY" || st == "HALF") return other;
  return "NONE";
}

// parse key -> int (ex: key="TVOC=")
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

// ---------------- WIFI + NTP ----------------
void connectWiFi() {
  Serial.println("WiFi connect...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void setupTimeUTC() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov", "time.google.com");

  ntpOk = false;
  Serial.print("NTP sync");
  for (int i = 0; i < 40; i++) { // ~12s max
    struct tm t;
    if (getLocalTime(&t, 300)) {
      if (t.tm_year > 120) { // > 2020
        ntpOk = true;
        break;
      }
    }
    Serial.print(".");
    delay(300);
  }
  Serial.println();

  if (ntpOk) Serial.println("✅ NTP synced");
  else       Serial.println("⚠️ NTP not synced (ts_device may be null)");
}

String iso8601UtcNow() {
  if (!ntpOk) return "";
  struct tm t;
  if (!getLocalTime(&t, 200)) return "";
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
  return String(buf);
}

// ---------------- MQTT ----------------
void connectMqtt() {
  Serial.println("MQTT connect...");
  mqtt.connect();
}

void onMqttConnect(bool sessionPresent) {
  Serial.print("✅ MQTT connected. sessionPresent=");
  Serial.println(sessionPresent ? "true" : "false");

  // publish gateway online retained (QoS1)
  mqtt.publish(GW_STATUS_TOPIC, MQTT_QOS, true, "online");
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
  Serial.print("❌ MQTT disconnected. reason=");
  Serial.println((int)reason);

  // reason=5 is typically "Not authorized"
  if (WiFi.isConnected()) {
    mqttReconnectTimer.once(2, connectMqtt);
  }
}

void onWiFiEvent(WiFiEvent_t event) {
  switch (event) {
    case ARDUINO_EVENT_WIFI_STA_GOT_IP:
      Serial.println("✅ WiFi connected");
      Serial.print("IP ESP32: ");
      Serial.println(WiFi.localIP());

      setupTimeUTC();
      connectMqtt();
      break;

    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
      Serial.println("❌ WiFi disconnected");
      mqttReconnectTimer.detach();
      wifiReconnectTimer.once(2, connectWiFi);
      break;

    default:
      break;
  }
}

// Publish JSON to topic trash/bins/<BINID>/telemetry
void publishJson(const String& binId, const String& state) {
  int tvoc = -1, eco2 = -1;
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

  Serial.print("JSON => ");
  Serial.println(json);

  if (!mqtt.connected()) {
    Serial.println("MQTT not connected -> skip publish");
    return;
  }

  uint16_t pktId = mqtt.publish(topic.c_str(), MQTT_QOS, MQTT_RETAIN, json.c_str(), json.length());
  Serial.print("MQTT publish QoS1 retain ");
  Serial.print(topic);
  Serial.print(" pktId=");
  Serial.println(pktId);
}

// ---------------- SETUP / LOOP ----------------
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.printf("ESP SDK: %s\n", ESP.getSdkVersion());

  WiFi.onEvent(onWiFiEvent);

  // MQTT config
  mqtt.onConnect(onMqttConnect);
  mqtt.onDisconnect(onMqttDisconnect);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);

  // Persistent session
  mqtt.setClientId(MQTT_CLIENT_ID);
  mqtt.setCleanSession(false);

  // ✅ Credentials (THIS FIXES reason=5 when broker requires auth)
  mqtt.setCredentials(MQTT_USER, MQTT_PASS);

  // LWT (retained QoS1)
  mqtt.setWill(GW_STATUS_TOPIC, MQTT_QOS, true, "offline");

  connectWiFi();

  // Init LoRa (LoRa-E5 via UART2)
  LORA.begin(9600, SERIAL_8N1, 16, 17);
  delay(1500);

  Serial.println("ESP32 LoRa E5 ready");

  sendAT("AT");
  sendAT("AT+MODE=TEST");
  sendAT("AT+TEST=RFCFG,868000000,SF7,125,4,8,14,ON,OFF");

  loraEnterRX();
  Serial.println("Listening...");
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

    // anti-duplicate (ignore same msg too fast)
    static String lastMsg = "";
    static unsigned long lastMsgMs = 0;
    unsigned long nowMs = millis();
    if (msg == lastMsg && (nowMs - lastMsgMs) < 1200) {
      continue;
    }
    lastMsg = msg;
    lastMsgMs = nowMs;

    Serial.print("RECV TEXT: ");
    Serial.println(msg);

    int sep = msg.indexOf(':');
    if (sep < 0) continue;

    String binId = msg.substring(0, sep);
    String rest  = msg.substring(sep + 1);
    binId.trim(); rest.trim();

    // GAS message: BIN1:GAS:TVOC=0:eCO2=400
    if (rest.startsWith("GAS")) {
      int tv = parseKeyInt(msg, "TVOC=");
      int ec = parseKeyInt(msg, "eCO2=");

      if (binId == "BIN1") {
        if (tv >= 0) bin1TVOC = tv;
        if (ec >= 0) bin1ECO2 = ec;
        Serial.print("BIN1 GAS => TVOC="); Serial.print(bin1TVOC);
        Serial.print(" eCO2="); Serial.println(bin1ECO2);
      } else if (binId == "BIN2") {
        if (tv >= 0) bin2TVOC = tv;
        if (ec >= 0) bin2ECO2 = ec;
        Serial.print("BIN2 GAS => TVOC="); Serial.print(bin2TVOC);
        Serial.print(" eCO2="); Serial.println(bin2ECO2);
      }
      continue;
    }

    // STATE message: BIN1:FULL / BIN2:HALF / BIN1:EMPTY
    String st = rest; st.trim();
    if (!isValidState(st)) {
      Serial.println("Ignored (unknown message type)");
      continue;
    }

    // only publish on state change
    String prev = getBinState(binId);
    setBinState(binId, st);

    Serial.print(binId);
    Serial.print(" => ");
    Serial.println(st);

    if (prev != st) {
      publishJson(binId, st);

      // If FULL -> reply NEAREST:<BIN>
      if (st == "FULL") {
        String chosen = pickOtherNotFull(binId);
        String reply = "NEAREST:" + chosen;

        Serial.print("SEND REPLY: ");
        Serial.println(reply);

        loraSendText(reply);
      }
    } else {
      Serial.println("No state change -> no MQTT publish");
    }
  }
}