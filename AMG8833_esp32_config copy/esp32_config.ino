#include <TFT_eSPI.h>
#include <Adafruit_ILI9341.h>
#include <Adafruit_AMG88xx.h>

#define TFT_CS   5
#define TFT_DC   27
#define TFT_RST  33
#define PIN_INT 32

#define KEYPAD_TOP 15
#define KEYPAD_LEFT 50
#define BUTTON_W 60
#define BUTTON_H 30
#define BUTTON_SPACING_X 10
#define BUTTON_SPACING_Y 10
#define BUTTON_TEXTSIZE 2

TFT_eSPI Display = TFT_eSPI();

#define C_BLUE Display.color565(0,0,255)
#define C_RED Display.color565(255,0,0)
#define C_GREEN Display.color565(0,255,0)
#define C_WHITE Display.color565(255,255,255)
#define C_BLACK Display.color565(0,0,0)
#define C_LTGREY Display.color565(200,200,200)
#define C_DKGREY Display.color565(80,80,80)
#define C_GREY Display.color565(127,127,127)

boolean measure = true;
uint16_t centerTemp;
unsigned long tempTime = millis();

char KeyPadBtnText[12][5] = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "Done", "0", "Clr" };

uint16_t KeyPadBtnColor[12] = {C_BLUE, C_BLUE, C_BLUE, C_BLUE, C_BLUE, C_BLUE, C_BLUE, C_BLUE, C_BLUE, C_GREEN, C_BLUE, C_RED };

float MinTemp = 25;
float MaxTemp = 35;

byte red, green, blue;

byte i, j, k, row, col, incr;
float intPoint, val, a, b, c, d, ii;
byte aLow, aHigh;

byte BoxWidth = 3;
byte BoxHeight = 3;

int x, y;
char buf[20];

int ShowGrid = -1;
int DefaultTemp = -1;

float pixels[64];

float HDTemp[80][80];

Adafruit_GFX_Button KeyPadBtn[12];

Adafruit_AMG88xx ThermalSensor;

void UpdateThermalData();
void InterpolateRows();
void InterpolateCols();
void DisplayGradient();
uint16_t GetColor(float val);
void SetTempScale();
void Getabcd();
void DrawLegend();
void drawMeasurement();

void setup() {
  Serial.begin(115200);

  Display.begin();
  Display.fillScreen(C_BLACK);
  Display.setRotation(0);

  Display.setTextSize(2);
  Display.setCursor(62, 61);
  Display.setTextColor(C_WHITE, C_BLACK);
  Display.print("Thermal");

  Display.setCursor(60, 60);
  Display.setTextColor(C_BLUE);
  Display.print("Thermal");

  Display.setCursor(92, 101);
  Display.setTextColor(C_WHITE, C_BLACK);
  Display.print("Camera");

  Display.setCursor(90, 100);
  Display.setTextColor(C_RED);
  Display.print("Camera");

  bool status = ThermalSensor.begin();
  delay(100);

  if (!status) {
    while (1) {
      Display.setCursor(20, 180);
      Display.setTextColor(C_RED, C_BLACK);
      Display.print("Sensor: FAIL");
      delay(500);
      Display.setCursor(20, 180);
      Display.setTextColor(C_BLACK, C_BLACK);
      Display.print("Sensor: FAIL");
      delay(500);
    }
  } else {
    Display.setCursor(20, 180);
    Display.setTextColor(C_GREEN, C_BLACK);
    Display.print("Sensor: FOUND");
  }

  ThermalSensor.readPixels(pixels);

  if (pixels[0] < 0) {
    while (1) {
      Display.setCursor(20, 210);
      Display.setTextColor(C_RED, C_BLACK);
      Display.print("Readings: FAIL");
      delay(500);
      Display.setCursor(20, 210);
      Display.setTextColor(C_BLACK, C_BLACK);
      Display.print("Readings: FAIL");
      delay(500);
    }
  } else {
    Display.setCursor(20, 210);
    Display.setTextColor(C_GREEN, C_BLACK);
    Display.print("Readings: OK");
    delay(2000);
  }

  Display.fillScreen(C_BLACK);
  SetTempScale();
  DrawLegend();
  Display.fillRect(10, 10, 220, 220, C_WHITE);
}

void loop() {
  if (Serial.available()) {
    char command = Serial.read();
    if (command == 'T') {
      UpdateThermalData();
    }
  }
}

void UpdateThermalData() {
  ThermalSensor.readPixels(pixels);

  SetTempScale();

  InterpolateRows();

  InterpolateCols();

  DisplayGradient();

  Serial.println("START DATA");

  for (row = 0; row < 8; row++) {
    for (col = 0; col < 8; col++) {
      Serial.print(pixels[row * 8 + col], 2);
      if (col < 7) {
        Serial.print(",");
      }
    }
    Serial.println();
  }
  Serial.print("END DATA");
}

void InterpolateRows() {
  for (row = 0; row < 8; row ++) {
    for (col = 0; col < 70; col ++) {
      aLow = col / 10 + (row * 8);
      aHigh = (col / 10) + 1 + (row * 8);
      intPoint = (( pixels[aHigh] - pixels[aLow] ) / 10.0 );
      incr = col % 10;
      val = (intPoint * incr ) + pixels[aLow];
      HDTemp[ (7 - row) * 10][col] = val;
    }
  }
}

void InterpolateCols() {
  for (col = 0; col < 70; col ++) {
    for (row = 0; row < 70; row ++) {
      aLow = (row / 10 ) * 10;
      aHigh = aLow + 10;
      intPoint = (( HDTemp[aHigh][col] - HDTemp[aLow][col] ) / 10.0 );
      incr = row % 10;
      val = (intPoint * incr ) + HDTemp[aLow][col];
      HDTemp[ row ][col] = val;
    }
  }
}

void DisplayGradient() {
  for (row = 0; row < 70; row ++) {
    if (ShowGrid < 0) {
      BoxWidth = 3;
    } else {
      if ((row % 10 == 9) ) {
        BoxWidth = 2;
      } else {
        BoxWidth = 3;
      }
    }
    for (col = 0; col < 70; col++) {
      if (ShowGrid < 0) {
        BoxHeight = 3;
      } else {
        if ((col % 10 == 9)) {
          BoxHeight = 2;
        } else {
          BoxHeight = 3;
        }
      }
      Display.fillRect((row * 3) + 15, (col * 3) + 15, BoxWidth, BoxHeight, GetColor(HDTemp[row][col]));
      if (measure == true && row == 36 && col == 36) {
        drawMeasurement();
      }
    }
  }
}

uint16_t GetColor(float val) {
  red = constrain(255.0 / (c - b) * val - ((b * 255.0) / (c - b)), 0, 255);

  if ((val > MinTemp) & (val < a)) {
    green = constrain(255.0 / (a - MinTemp) * val - (255.0 * MinTemp) / (a - MinTemp), 0, 255);
  } else if ((val >= a) & (val <= c)) {
    green = 255;
  } else if (val > c) {
    green = constrain(255.0 / (c - d) * val - (d * 255.0) / (c - d), 0, 255);
  } else if ((val > d) | (val < a)) {
    green = 0;
  }

  if (val <= b) {
    blue = constrain(255.0 / (a - b) * val - (255.0 * b) / (a - b), 0, 255);
  } else if ((val > b) & (val <= d)) {
    blue = 0;
  } else if (val > d) {
    blue = constrain(240.0 / (MaxTemp - d) * val - (d * 240.0) / (MaxTemp - d), 0, 240);
  }

  return Display.color565(red, green, blue);
}

void SetTempScale() {
  MinTemp = 255;
  MaxTemp = 0;

  for (i = 0; i < 64; i++) {
    if (pixels[i] < MinTemp) {
      MinTemp = pixels[i];
    }
    if (pixels[i] > MaxTemp) {
      MaxTemp = pixels[i];
    }
  }

  MaxTemp = MaxTemp + 2.0;
  MinTemp = MinTemp - 2.0;

  if (MinTemp >= MaxTemp) {
    MinTemp = MaxTemp - 5;
    if (MinTemp < 0) MinTemp = 0;
  }

  Getabcd();
  DrawLegend();
}

void Getabcd() {
  a = MinTemp + (MaxTemp - MinTemp) * 0.2121;
  b = MinTemp + (MaxTemp - MinTemp) * 0.3182;
  c = MinTemp + (MaxTemp - MinTemp) * 0.4242;
  d = MinTemp + (MaxTemp - MinTemp) * 0.8182;
}

void DrawLegend() {
  j = 0;
  float inc = (MaxTemp - MinTemp ) / 220.0;

  for (ii = MinTemp; ii < MaxTemp; ii += inc) {
    Display.drawFastVLine(10 + j++, 255, 30, GetColor(ii));
  }

  int xpos;
  if (MaxTemp > 99) {
    xpos = 184;
  } else {
    xpos = 196;
  }

  Display.setTextSize(2);
  Display.setCursor(10, 235);
  Display.setTextColor(C_WHITE, C_BLACK);
  sprintf(buf, "%2d", (int)MinTemp);
  Display.print(buf);

  Display.setTextSize(2);
  Display.setCursor(xpos, 235);
  Display.setTextColor(C_WHITE, C_BLACK);
  sprintf(buf, " %2d", (int)MaxTemp);
  Display.print(buf);
}

void drawMeasurement() {
  Display.drawCircle(120, 120, 3, ILI9341_WHITE);

  centerTemp = pixels[27];

  Display.setCursor(10, 300);
  Display.setTextColor(ILI9341_WHITE, ILI9341_BLACK);
  Display.setTextSize(2);
  sprintf(buf, "%s:%2d", "Temp", centerTemp);
  Display.print(buf);
}