#include <HX711_ADC.h>
#if defined(ESP8266) || defined(ESP32) || defined(AVR)
  #include <EEPROM.h>
#endif

const int HX711_dout = 2;
const int HX711_sck  = 3;

HX711_ADC LoadCell(HX711_dout, HX711_sck);

const float calibrationValue = 600.59;  

boolean tareDone   = false;
boolean measuring  = false;
float   prevVolume = 0;

void setup() {
  Serial.begin(9600);   
  delay(10);

  LoadCell.begin();

  unsigned long stabilizingtime = 2000;
  boolean _tare = false;                
  LoadCell.start(stabilizingtime, _tare);

  if (LoadCell.getTareTimeoutFlag()) {
    while (1) { Serial.println("0.0"); delay(500); }
  }

  LoadCell.setCalFactor(calibrationValue);
}

void loop() {

  static boolean newDataReady = false;
  if (LoadCell.update()) newDataReady = true;

  if (Serial.available() > 0 && !tareDone) {
    String incoming = Serial.readStringUntil('\n');
    incoming.trim();
    if (incoming.length() > 0 && incoming[0] == 'T') {
      LoadCell.tareNoDelay();
      tareDone = true;
    }
  }

  if (tareDone && !measuring && LoadCell.getTareStatus()) {
    measuring  = true;
    prevVolume = 0;
    LoadCell.update();
  }

  if (newDataReady && measuring) {
    float volume = abs(LoadCell.getData());
    unsigned long current_ms = millis(); 
    Serial.print(current_ms);
    Serial.print(",");
    Serial.println(volume, 1);

    prevVolume   = volume;
    newDataReady = false;
    delay(5);
  }
}