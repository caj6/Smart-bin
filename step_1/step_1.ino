#include <Servo.h>

Servo myServo;

const int trigPin = 7;
const int echoPin = 6;
const int servoPin = 9;

long duration;
int distance;

const int THRESHOLD_CM = 15;      // distance pour ouvrir (à ajuster)
bool isOpen = false;

void setup() {
  Serial.begin(9600);

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  myServo.attach(servoPin);
  myServo.write(0);  // fermé au départ
}

int readDistanceCm() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(5);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration = pulseIn(echoPin, HIGH, 30000UL); // timeout 30ms
  if (duration == 0) return 999;              // rien détecté

  return (int)(duration * 0.017);             // cm
}

void loop() {
  distance = readDistanceCm();

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  // Si une main est proche -> ouvrir
  if (distance <= THRESHOLD_CM && !isOpen) {
    myServo.write(90);      // ouvre
    isOpen = true;
    delay(1500);            // reste ouvert 3s
  }

  // Refermer quand la main s’éloigne
  if (distance > THRESHOLD_CM + 5 && isOpen) {
    myServo.write(0);       // ferme
    isOpen = false;
  }

  delay(100);
}