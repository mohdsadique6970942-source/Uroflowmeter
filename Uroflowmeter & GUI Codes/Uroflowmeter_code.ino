#include <HX711_ADC.h>
#if defined(ESP8266)|| defined(ESP32) || defined(AVR)
#include <EEPROM.h>
#endif

const int HX711_dout = 2;
const int HX711_sck = 3;

HX711_ADC LoadCell(HX711_dout, HX711_sck);

const int calVal_eepromAdress = 0;

// ----------- UROFLOW VARIABLES -----------
float prevVolume = 0;
float flowRate = 0;
unsigned long prevTime = 0;
boolean uroStart = false;
boolean tareDone = false;
// ----------------------------------------

// ----------- FINAL REPORT VARIABLES -----------
float maxFlowRate = 0;
float totalVolume = 0;
unsigned long startTime = 0;
unsigned long endTime = 0;
boolean reportPrinted = false;
unsigned long lastFlowTime = 0;
const int stopDelay = 3000;
// ----------------------------------------------

void setup() {
  Serial.begin(115200); delay(10);
  Serial.println();
  Serial.println("Lets Start");

  LoadCell.begin();
  float calibrationValue;
  calibrationValue = 600.59;   // Set after Calibration  

  unsigned long stabilizingtime = 2000;
  boolean _tare = false;
  LoadCell.start(stabilizingtime, _tare);

  if (LoadCell.getTareTimeoutFlag()) {
    Serial.println("Timeout, check MCU>HX711 wiring");
    while (1);
  }
  else {
    LoadCell.setCalFactor(calibrationValue);
    Serial.println("Put the bucket and Send 'T' to tare and start");
  }
}

void loop() {

  if(reportPrinted == true){
    while(1);
  }

  static boolean newDataReady = 0;
  if (LoadCell.update()) newDataReady = true;

  // -------- WAIT FOR 't' TO TARE ----------
  if (Serial.available() > 0 && !tareDone) {
    char inChar = Serial.read();
    if (inChar == 'T') {
      Serial.println("Taring...");
      LoadCell.tareNoDelay();
      tareDone = true;
    }
  }

  if (LoadCell.getTareStatus() == true && tareDone && !uroStart) {
    Serial.println("Tare complete");
    Serial.println("START URINATING");
    delay(2000);
    uroStart = true;
    prevTime = millis();
  }
  // ----------------------------------------

  if (newDataReady && uroStart) {

    float volume = abs(LoadCell.getData());

    unsigned long currentTime = millis();
    float dt = (currentTime - prevTime) / 1000.0;

    if (dt > 0) {
      flowRate = abs((volume - prevVolume) / dt);
    }

    if (flowRate > 1 && startTime == 0) {
      startTime = millis();
    }

    if (flowRate > maxFlowRate) {
      maxFlowRate = flowRate;
    }

    if (flowRate > 1) {
      lastFlowTime = millis();
    }

    totalVolume = volume;

    float elapsedTime = 0;
    if(startTime > 0){
      elapsedTime = (millis() - startTime) / 1000.0;
    }

    Serial.print("Time (sec):");
    Serial.print(elapsedTime );
    Serial.print("  Volume (ml):");
    Serial.print(volume );
    Serial.print("  Flow Rate (ml/sec):");
    Serial.println(flowRate);

    prevVolume = volume;
    prevTime = currentTime;

    newDataReady = 0;
    delay(5);
  }

  if (!reportPrinted && startTime > 0 && millis() - lastFlowTime > stopDelay) {

    endTime = millis();
    float voidingTime = (endTime - startTime) / 1000.0;
    float avgFlowRate = totalVolume / voidingTime;

    Serial.println("\n----- FINAL UROFLOW REPORT -----");

    Serial.print("Total Volume (ml): ");
    Serial.println(totalVolume);

    Serial.print("Voiding Time (sec): ");
    Serial.println(voidingTime);

    Serial.print("Max Flow Rate Qmax (ml/sec): ");
    Serial.println(maxFlowRate);

    Serial.print("Average Flow Rate Qavg (ml/sec): ");
    Serial.println(avgFlowRate);

    Serial.println("--------------------------------");

    reportPrinted = true;
  }
}