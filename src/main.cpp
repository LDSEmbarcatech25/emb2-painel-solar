#include <Arduino.h>
#include <Wire.h>
#include <Servo.h>
#include <math.h>

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <BH1750.h>

#include "ClosedCube_HDC1080.h"

#define ALTURA_TELA 128
#define LARGURA_TELA 64

#define OLED_ADDR 0x3C
#define HDR_ADDR 0x40
#define BH_ADDR 0x23

#define MPU_ADDR 0x68
#define MPU_PWR_REG 0x6B
#define MPU_ACCEL_REG 0x3B

#define PASSO 2           
#define CICLO_MS 150         # Retornado para o tempo original rápido
#define ANGULO_MIN 10          
#define ANGULO_MAX 170         
#define ANGULO_CTR 90          
#define LAVAGEM_S 5           
#define HISTERESE_LUX 45          
#define LUX_NOITE_CRITICO 12        
#define TEMPO_FILTRO_INCLINACAO 2000 

#define SERVO_DUTY_MIN 1638        
#define SERVO_DUTY_MAX 8192 

#define BUZZER 3
#define RELAY 48
#define BTN_LIMPEZA 45
#define BTN_RESET 46

const char* TOPICOS_SUB[] = {
  "monitorador-solar/cmd/tirar-foto",
  "monitorador-solar/cmd/acionar-valvula"
};

// TwoWire I2C_1 = TwoWire(0);
TwoWire I2C_2 = TwoWire(1);

Adafruit_SSD1306 oled(ALTURA_TELA, LARGURA_TELA, &Wire, -1);

ClosedCube_HDC1080 hdc;

Adafruit_MPU6050 mpu;

BH1750 LDR_Esq;
BH1750 LDR_Dir;

Servo servo;

float calcular_angulo(float ax, float az);
void oled_print(const char* texto ,u_int8_t tamanho_letra,int16_t x,int16_t y);

float calcular_angulo(float ax, float az) {
  return atan2(ax, az) * (180.0 / PI);
}

void oled_print(const char* texto ,u_int8_t tamanho_letra,int16_t x,int16_t y){
  oled.clearDisplay();

  oled.setTextSize(tamanho_letra);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(5,0);

  oled.println(texto);

  oled.display();
}

void setup() {
  Serial.begin(115200);

  Wire.begin(14,21,400000);
  I2C_2.begin(41,42,400000);

  hdc.begin(HDR_ADDR);
  
  mpu.begin(MPU_ADDR,&Wire);

  LDR_Esq.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,BH_ADDR,&Wire);
  LDR_Dir.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,BH_ADDR,&I2C_2);

  oled.begin(SSD1306_SWITCHCAPVCC,OLED_ADDR);

  oled.clearDisplay();

  oled_print("resenha",2,0,0);

}

void loop() {
  sensors_event_t a, g, t;

  mpu.getEvent(&a, &g, &t);

  float ax = a.acceleration.x;
  float ay = a.acceleration.y;
  float az = a.acceleration.z;

  float temperatura = hdc.readTemperature();
  float umidade = hdc.readHumidity();
  
  float luz_esq = LDR_Esq.readLightLevel();
  float luz_dir = LDR_Dir.readLightLevel();
  
  Serial.println(umidade);
  Serial.println(temperatura);
  Serial.println(luz_dir);
  Serial.println(luz_esq);

}