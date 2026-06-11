#include <Arduino.h>
#include <Wire.h>
#include <Servo.h>
#include <math.h>

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#ifdef sensor_t
#undef sensor_t
#endif
#include "camera_service.h"


#include <BH1750.h>
#include "esp_timer.h"

#include "buzzer.h"

#include "ClosedCube_HDC1080.h"

#include "status_builder.h"
#include "buzzer.h"
#include "mqtt_service.h"
#include "relay.h"

#define ALTURA_TELA 128
#define LARGURA_TELA 64

#define OLED_ADDR 0x3C
#define HDR_ADDR 0x40
#define BH_ADDR 0x23

#define MPU_ADDR 0x68
#define MPU_PWR_REG 0x6B
#define MPU_ACCEL_REG 0x3B

#define PASSO 2           
#define CICLO_MS 150
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
#define SERVO 44

const char* TOPICOS_SUB[] = {
  "monitorador-solar/cmd/tirar-foto",
  "monitorador-solar/cmd/acionar-valvula"
};

int anguloAntigo = ANGULO_CTR;

int angulo_atual = ANGULO_CTR;
bool valvula_aberta = false;
uint t_lavagem_fim  = 0;
uint t_ultimo_rastreamento = 0;

int modo_manual = 0;  
int t_inicio_inclinacao = 0;  
bool estado_noturno = false;

String mqtt_topico = "";
String mqtt_msg = "";
bool tem_mensagem = false;

volatile bool pode_enviar_status = false;

esp_timer_handle_t status_timer;

struct MonitorSensores {
  int umidade;
  int temperatura;
  int LDR_Esq;
  int LDR_Dir;
  int angulo_painel;
};

MonitorSensores monitor_sensores = {
  0, // umidade
  0, // temperatura
  0, // LDR_Esq
  0, // LDR_Dir
  0  // angulo_painel
};

// TwoWire I2C_1 = TwoWire(0);
TwoWire I2C_2 = TwoWire(1);

Adafruit_SSD1306 oled(ALTURA_TELA, LARGURA_TELA, &Wire, -1);

ClosedCube_HDC1080 hdc;

Adafruit_MPU6050 mpu;

BH1750 LDR_Esq;
BH1750 LDR_Dir;

Servo servo;
Buzzer buzzer(BUZZER);

Relay relay(RELAY);

MqttService mqtt("broker.emqx.io","ESP32-S3");

CameraService camera;

float calcular_angulo(float ax, float az);
void oled_print(const char* texto ,u_int8_t tamanho_letra,int16_t x,int16_t y);
void mover_servo(int graus);
void mover_servo_suave(int graus);
void timer_handler(void* arg);

float calcular_angulo(float ax, float az) {
  return atan2(ax, az) * (180.0 / PI);
}

void mover_servo(int graus){
  constrain(graus,0,180);
  servo.write(graus);
}

void mover_servo_suave(int grausAlvo){
  grausAlvo = constrain(grausAlvo, 0, 180);
  mover_servo(grausAlvo);
  anguloAntigo = grausAlvo;
}

void oled_print(const char* texto ,u_int8_t tamanho_letra,int16_t x,int16_t y){
  oled.clearDisplay();

  oled.setTextSize(tamanho_letra);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(5,0);

  oled.println(texto);

  oled.display();
}

void timer_handler(void* arg){
  pode_enviar_status = true;
}

void enviar_status() {
  String json_status = StatusBuilder()
  .set_clima(monitor_sensores.umidade,monitor_sensores.temperatura)
  .set_luminosidade(monitor_sensores.LDR_Esq,monitor_sensores.LDR_Dir)
  .set_angulo_painel(monitor_sensores.angulo_painel)
  .build();

  Serial.println("ta mandando as info");
  // mqtt.pub("monitorador-solar/status/painel", json_status);
}

void setup() {
  Serial.begin(115200);

  pinMode(BTN_LIMPEZA, INPUT_PULLUP);
  pinMode(BTN_RESET, INPUT_PULLUP);

  Wire.begin(14,21,400000);
  I2C_2.begin(41,42,400000);

  hdc.begin(HDR_ADDR);
  
  mpu.begin(MPU_ADDR,&Wire);

  LDR_Esq.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,BH_ADDR,&Wire);
  LDR_Dir.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,BH_ADDR,&I2C_2);

  oled.begin(SSD1306_SWITCHCAPVCC,OLED_ADDR);

  oled.clearDisplay();

  oled_print("resenha",2,0,0);

  servo.attach(SERVO,SERVO_DUTY_MIN,SERVO_DUTY_MAX);

  const esp_timer_create_args_t timer_args = {
    .callback = &timer_handler,
    .arg = nullptr,
    .dispatch_method = ESP_TIMER_TASK,
    .name = "status_timer"
  };
  esp_timer_create(&timer_args, &status_timer);

  // 10_000 ms = 10 segundos → convertido para microssegundos
  esp_timer_start_periodic(status_timer, 10ULL * 1000ULL * 1000ULL);

  Serial.println("Firmware KiiRA V1.2 Ativo — Sistema Rodando Limpo");
  delay(100);
  mover_servo_suave(ANGULO_CTR);
  buzzer.beep(200);
  
  mqtt.getClient().setCallback(
    [](char* topic, byte* payload, unsigned int length) {
    
      String msg = "";
    
      for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
      }
    
      Serial.print("Topico: ");
      Serial.println(topic);
    
      Serial.print("Mensagem: ");
      Serial.println(msg);
    }
  );

  mqtt.getClient().setCallback([] (char* topic, byte* payload, unsigned int length) {
      mqtt_topico = String(topic);

      mqtt_msg = "";
      for (unsigned int i = 0; i < length; i++) {
        mqtt_msg += (char)payload[i];
      }

      Serial.print("Topico: ");
      Serial.println(mqtt_topico);

      Serial.print("Mensagem: ");
      Serial.println(mqtt_msg);
      tem_mensagem = true;
    }
  );

  camera.begin();
}

void loop() {
    
  unsigned long agora = millis();

  mqtt.loop();

  if (pode_enviar_status) {
    enviar_status();
    pode_enviar_status = false;
  }

  if (tem_mensagem && mqtt_topico.length() > 0 && mqtt_msg.length() > 0) {

    String msg_agora = mqtt_msg;
    String topico_agora = mqtt_topico;

    if (topico_agora == "monitorador-solar/cmd/tirar-foto" && msg_agora == "foto") {

      camera_fb_t* img = camera.capture();
      
      mqtt.begin_pub("monitorador-solar/receber-foto",img->len,false);
    
      mqtt.write_pub(img->buf, img->len);
      mqtt.end_pub();
    
      camera.release();
    }

    else if (topico_agora == "monitorador-solar/cmd/acionar-valvula") {

      oled.clearDisplay();
      oled.setTextSize(1);
      oled.setTextColor(SSD1306_WHITE);
      
      oled.setCursor(0,0);
      oled.println("KiiRA Solar V1.2");

      oled.setCursor(0,26);
      oled.println(">> LAVANDO <<");

      oled.setCursor(0,45);
      oled.println("PAINEL TRAVADO");

      oled.display();

      StaticJsonDocument<128> doc;
      DeserializationError error = deserializeJson(doc, msg_agora);

      if (!error) {
        int tempo_segundos = doc["tempo_segundos"];

        relay.ligar();
        delay(tempo_segundos * 1000);
        relay.desligar();

        Serial.println("ligou a valvula");
      }
    }

    // reset equivalente ao mqtt.reset()
    mqtt_msg = "";
    mqtt_topico = "";
    tem_mensagem = false;
  }

  if (!valvula_aberta){
    if (agora - t_ultimo_rastreamento >= CICLO_MS) {
      t_ultimo_rastreamento = agora;

      float lux_esq = LDR_Esq.readLightLevel();
      float lux_dir = LDR_Dir.readLightLevel();

      sensors_event_t a, g, t;
      mpu.getEvent(&a, &g, &t);
        
      float ax = a.acceleration.x;
      float ay = a.acceleration.y;
      float az = a.acceleration.z;

      monitor_sensores.LDR_Esq = (int)lux_esq;
      monitor_sensores.LDR_Dir = (int)lux_dir;

      float inclinacao = calcular_angulo(ax,az);


      if(modo_manual == 0){
        if (lux_esq <= LUX_NOITE_CRITICO && lux_dir <= LUX_NOITE_CRITICO){
          if (!estado_noturno){
            estado_noturno = true;
          }

          angulo_atual = ANGULO_CTR;
          mover_servo_suave(angulo_atual);
        } else {
          estado_noturno = false;

          if (fabs(inclinacao) > 80){
            if (t_inicio_inclinacao == 0){
              t_inicio_inclinacao = agora;

              if((agora - t_inicio_inclinacao) >= TEMPO_FILTRO_INCLINACAO){
                angulo_atual = ANGULO_CTR;
                mover_servo_suave(angulo_atual);
              }
            }
          } else {
            t_inicio_inclinacao = 0;

            if (fabs(lux_dir - lux_esq) > HISTERESE_LUX){
              if (lux_dir > lux_esq){
                angulo_atual = min(ANGULO_MAX, angulo_atual + PASSO);
              } else {
                angulo_atual = min(ANGULO_MAX, angulo_atual - PASSO);
              }

              mover_servo_suave(angulo_atual);
            }
          }
          
        }
      } else if (modo_manual == 1){
        t_inicio_inclinacao = 0;
        angulo_atual = ANGULO_CTR;
        mover_servo_suave(angulo_atual);

      } else if (modo_manual == 2){
        t_inicio_inclinacao = 0;
        angulo_atual = 0;
        mover_servo_suave(angulo_atual);
      }

      float temperatura = hdc.readTemperature();
      float umidade = hdc.readHumidity();

      monitor_sensores.temperatura = (int) temperatura;
      monitor_sensores.umidade = (int) umidade;

      oled.clearDisplay();
      oled.setTextSize(1);
      oled.setTextColor(SSD1306_WHITE);
      
      oled.setCursor(0,0);
      oled.println("KiiRA Solar V1.2");

      oled.setCursor(0,13);
      oled.printf("E:{%d}lx D:{%d}lx\n",lux_esq,lux_esq);


      if (estado_noturno && modo_manual == 0) {
        oled.setCursor(0,13);
        oled.printf("MODO: NOTURNO (90)\n");
      
      } else if (modo_manual == 0) {
      
        if (t_inicio_inclinacao != 0 && (millis() - t_inicio_inclinacao) < TEMPO_FILTRO_INCLINACAO) {
          oled.setCursor(0,26);
          oled.printf("FILTRANDO AGIT.\n");
        } else {
          oled.setCursor(0,26);
          oled.printf("Angulo: %ddeg\n", (int)angulo_atual);
        }

      } else if (modo_manual == 1) {
        oled.setCursor(0,26);
        oled.println("Modo: RESET (90)");
      
      } else if (modo_manual == 2) {
        oled.setCursor(0,26);
        oled.println("Modo: MANUT (0)");
      }

      oled.setCursor(0,39);
      oled.printf("T:{%d}C H:{%d}%",temperatura,umidade);
      oled.setCursor(0,52);
      oled.println("Valvula: Fechada");
      oled.display();

      monitor_sensores.angulo_painel = angulo_atual;
    }

  }

  if (digitalRead(BTN_LIMPEZA) == LOW){
    delay(20);

    if (digitalRead(BTN_LIMPEZA) == LOW && !valvula_aberta){
      servo.write(0);

      relay.ligar();
      valvula_aberta = true;

      unsigned long t_lavagem_fim = agora + (LAVAGEM_S * 1000);
      buzzer.beep(150);

      oled.clearDisplay();
      oled.setTextSize(1);
      oled.setTextColor(SSD1306_WHITE);
      
      oled.setCursor(0,0);
      oled.println("KiiRA Solar V1.2");

      oled.setCursor(0,26);
      oled.println(">> LAVANDO <<");

      oled.setCursor(0,45);
      oled.println("PAINEL TRAVADO");

      oled.display();
    }
  }

  if (valvula_aberta) {
    if ((millis() - t_lavagem_fim) >= 0) {

      relay.desligar(); // Fecha a válvula d'água
      valvula_aberta = false;

      mover_servo(angulo_atual);

      buzzer.beep(200);
    }
  }

  if (digitalRead(BTN_RESET) == LOW) {
    delay(20);

    if (digitalRead(BTN_RESET) == LOW) {
      modo_manual = (modo_manual + 1) % 3;

      buzzer.beep(50);

      delay(300);
    }
  }

  delay(20);
}