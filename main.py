# =============================================================================
# RASTREADOR SOLAR INTELIGENTE — KiiRA V2.1 / ESP32-S3
# Firmware: MicroPython v1.22.0
# Versão: 1.2 
# 
# MAPEAMENTO DE HARDWARE E PINOS (PROCESSADOR ESP32-S3):
# ── BARRAMENTO I2C_0 (Sensores Principais e Display OLED)
#    - SDA: Pin(14)
#    - SCL: Pin(21)
#    - Dispositivos: OLED Integrado (0x3C), Sensor MPU6050 (0x68),
#                    Sensor HDC1080 (0x40), Sensor BH1750 Esquerdo (0x23)
#
# ── BARRAMENTO I2C_1 (Canal Isolado)
#    - SDA: Pin(41)
#    - SCL: Pin(42)
#    - Dispositivos: Sensor BH1750 Direito (0x23)
#
# ── ATUADORES E SAÍDAS (PWM / DIGITAL)
#    - Servo Motor (Eixo Principal): Pin(44) [PWM - Frequência: 50Hz]
#    - Buzzer Sonoro (Alertas): Pin(3)      [PWM - Frequência: 5000Hz]
#    - Relé 1 (Válvula de Limpeza): Pin(48)  [Saída Digital - Ativo em nível ALTO]
#
# ── ENTRADAS E INTERRUPÇÕES (BOTÕES)
#    - Botão de Limpeza Manual: Pin(45)     [Entrada Digital - Pull-Up Interno]
#    - Botão de Reset / Modos: Pin(46)      [Entrada Digital - Pull-Up Interno]
# =============================================================================
from machine import ADC, I2C, PWM, Pin, Timer

import math
import time
import json

import mqtt_service
import wifi_service
import camera_service
from servo import Servo
from relay import Relay
from hdc import Hdc1080
from mpu import Mpu6050
from status_builder import StatusBuilder

import ssd1306

topicos_sub = [
    "monitorador-solar/cmd/tirar-foto",
    "monitorador-solar/cmd/acionar-valvula",
]

wifi = wifi_service.WifiService("IFCE Alunos","")
wifi.conectar_rede()

mqtt = mqtt_service.MqttService()
mqtt.conectar_broker()

mqtt.sub_multiplos_topicos(topicos_sub)

# camera = camera_service.CameraService()

# =============================================================================
# PARÂMETROS CONFIGURÁVEIS DO SISTEMA
# =============================================================================
PASSO           = 2           
CICLO_MS        = 150         # Retornado para o tempo original rápido
ANGULO_MIN      = 10          
ANGULO_MAX      = 170         
ANGULO_CTR      = 90          
LAVAGEM_S       = 5           
HISTERESE_LUX   = 45          
LUX_NOITE_CRITICO = 12        
TEMPO_FILTRO_INCLINACAO = 2000 

SERVO_DUTY_MIN  = 1638        
SERVO_DUTY_MAX  = 8192        

OLED_ADDR       = 0x3C
MPU_ADDR        = 0x68
HDC_ADDR        = 0x40
BH1750_ADDR     = 0x23        
MPU_PWR_REG     = 0x6B        
MPU_ACCEL_REG   = 0x3B     

# =============================================================================
# INICIALIZAÇÃO DOS BARRAMENTOS I2C (DUPLO)
# =============================================================================
i2c0 = I2C(0, sda=Pin(14), scl=Pin(21), freq=400_000)
i2c1 = I2C(1, sda=Pin(41), scl=Pin(42), freq=400_000)

hdc = Hdc1080(i2c)
mpu = Mpu6050(i2c)

try:
    oled = ssd1306.SSD1306_I2C(128, 64, i2c0, addr=OLED_ADDR)
    oled.fill(0)
    oled.text("KiiRA Solar V1.2", 0, 0)
    oled.show()
    OLED_OK = True
except:
    OLED_OK = False

def bh1750_init(i2c_bus):
    try:
        i2c_bus.writeto(BH1750_ADDR, b'\x01')  
        i2c_bus.writeto(BH1750_ADDR, b'\x10')  
    except:
        pass

def bh1750_ler_lux(i2c_bus):
    try:
        dados = i2c_bus.readfrom(BH1750_ADDR, 2)
        lux = (dados[0] << 8) | dados[1]
        return round(lux / 1.2)     
    except:
        return 0

bh1750_init(i2c0)  
bh1750_init(i2c1)  

def calcular_angulo(ax, az):
    try:
        return math.atan2(ax, az) * (180 / math.pi)
    except:
        return 0.0

def hdc_ler():
    try:
        i2c0.writeto(HDC_ADDR, b'\x00')
        time.sleep_ms(15)
        dados = i2c0.readfrom(HDC_ADDR, 4)
        t_raw = (dados[0] << 8) | dados[1]
        h_raw = (dados[2] << 8) | dados[3]
        return round(((t_raw / 65536.0) * 165.0 - 40.0), 1), round(((h_raw / 65536.0) * 100.0), 1)
    except:
        return 0.0, 0.0

try:
    i2c0.writeto_mem(MPU_ADDR, MPU_PWR_REG, b'\x00')
except:
    pass

# ── CONFIGURAÇÃO DOS ATUADORES ──────────────────────────────────────────────
servo2_pwm = PWM(Pin(44), freq=50, duty_u16=0)   

buzzer_pin = Pin(3, Pin.OUT)
buzzer = PWM(buzzer_pin)
buzzer.init(freq=5000, duty_u16=0)

angulo_alvo_antigo = ANGULO_CTR

def mover_servo(graus):
    graus = max(0, min(180, graus))
    duty2 = int(SERVO_DUTY_MIN + ((180 - graus) / 180.0) * (SERVO_DUTY_MAX - SERVO_DUTY_MIN))
    servo2_pwm.duty_u16(duty2)

# Movimento direto e sem trancos (Mantém o sinal ativo para estabilidade contínua)
def mover_servo_suave(graus_alvo):
    global angulo_alvo_antigo
    graus_alvo = max(0, min(180, graus_alvo))
    mover_servo(graus_alvo)
    angulo_alvo_antigo = graus_alvo

# ── ATUADORES NATIVOS KIIRA (NÍVEL LÓGICO ALTO) ─────────────────────────────────
relay1 = Relay(48)
btn_limpeza = Pin(45, Pin.IN, Pin.PULL_UP)
btn_reset   = Pin(46, Pin.IN, Pin.PULL_UP)

def beep(duracao_ms=100):
    try:
        buzzer.init(freq=5000)
        buzzer.duty_u16(32768) 
        time.sleep_ms(duracao_ms)
        buzzer.duty_u16(0)
    except Exception as e:
        print(e)

# =============================================================================
# LOOP PRINCIPAL DO SISTEMA
# =============================================================================
angulo_atual   = ANGULO_CTR
valvula_aberta = False
t_lavagem_fim  = 0
t_ultimo_rastreamento = 0

modo_manual = 0  
t_inicio_inclinacao = 0  
estado_noturno = False

pode_enviar_status = False

monitor_sensores = {
    "umidade":0,
    "temperatura": 0,
    "posicao-x": 0,
    "posicao-y": 0,
    "LDR_Esq": 0,
    "LDR_Dir": 0,
    "delta": 0
}

def timer_handler(timer=None):
    global pode_enviar_status
    pode_enviar_status = True

def enviar_status():
    json_status = (StatusBuilder()
                   .set_clima(monitor_sensores["umidade"],monitor_sensores["temperatura"])
                   .set_luminosidade(monitor_sensores["LDR_Esq"],monitor_sensores["LDR_Dir"],monitor_sensores["delta"])
                   .set_posicao_painel(monitor_sensores["posicao-x"],monitor_sensores["posicao-y"])
                   .build())

    print("ta mandando as info")
    mqtt.pub(b"monitorador-solar/status/painel", json_status)

timer = Timer(0)
timer.init(period=10_000, mode=Timer.PERIODIC, callback=timer_handler)
# timer.init(period=3_600_000, mode=Timer.PERIODIC, callback=timer_handler) # 1 hora

def loop():
    global angulo_atual, valvula_aberta, t_lavagem_fim, t_ultimo_rastreamento, modo_manual, t_inicio_inclinacao, estado_noturno, pode_enviar_status

    print("Firmware KiiRA V1.2 Ativo — Sistema Rodando Limpo")
    time.sleep_ms(100)
    mover_servo_suave(ANGULO_CTR)
    beep(200)

    while True:
        agora = time.ticks_ms()

        # O rastreamento funciona normalmente, a não ser que a lavagem seja ativada
        if not valvula_aberta:
            if time.ticks_diff(agora, t_ultimo_rastreamento) >= CICLO_MS:
                t_ultimo_rastreamento = agora

                lux_esq = bh1750_ler_lux(i2c0)       
                lux_dir = bh1750_ler_lux(i2c1)       
                ax, ay, az = mpu_leitura_accel()
                inclinacao  = calcular_angulo(ax, az)

                if modo_manual == 0:
                    if lux_esq <= LUX_NOITE_CRITICO and lux_dir <= LUX_NOITE_CRITICO:
                        if not estado_noturno:
                            estado_noturno = True
                        angulo_atual = ANGULO_CTR
                        mover_servo_suave(angulo_atual) 
                    else:
                        estado_noturno = False
                        
                        if abs(inclinacao) > 80:
                            if t_inicio_inclinacao == 0:
                                t_inicio_inclinacao = agora
                            
                            if time.ticks_diff(agora, t_inicio_inclinacao) >= TEMPO_FILTRO_INCLINACAO:
                                angulo_atual = ANGULO_CTR
                                mover_servo_suave(angulo_atual)
                        else:
                            t_inicio_inclinacao = 0 
                            
                            if abs(lux_dir - lux_esq) > HISTERESE_LUX:
                                if lux_dir > lux_esq:
                                    angulo_atual = min(ANGULO_MAX, angulo_atual + PASSO)
                                else:
                                    angulo_atual = max(ANGULO_MIN, angulo_atual - PASSO)
                                mover_servo_suave(angulo_atual)
                
                elif modo_manual == 1:
                    t_inicio_inclinacao = 0
                    angulo_atual = ANGULO_CTR
                    mover_servo_suave(angulo_atual) 
                    
                elif modo_manual == 2:
                    t_inicio_inclinacao = 0
                    angulo_atual = 0  
                    mover_servo_suave(angulo_atual) 

                temp, umid = hdc_ler()
                if OLED_OK:
                    oled.fill(0)
                    oled.text("KiiRA Solar V1.2", 0, 0)
                    oled.text(f"E:{lux_esq}lx D:{lux_dir}lx", 0, 13) 
                    
                    if estado_noturno and modo_manual == 0:
                        oled.text("MODO: NOTURNO (90)", 0, 26)
                    elif modo_manual == 0:
                        if t_inicio_inclinacao != 0 and time.ticks_diff(agora, t_inicio_inclinacao) < TEMPO_FILTRO_INCLINACAO:
                            oled.text("FILTRANDO AGIT.", 0, 26)
                        else:
                            oled.text(f"Angulo: {angulo_atual}deg", 0, 26)
                    elif modo_manual == 1:
                        oled.text("Modo: RESET (90)", 0, 26)
                    elif modo_manual == 2:
                        oled.text("Modo: MANUT (0)", 0, 26)
                        
                    oled.text(f"T:{temp}C H:{umid}%", 0, 39)
                    oled.text("Valvula: Fechada", 0, 52)
                    oled.show()

        # ── DISPARADOR DA VÁLVULA DE ENXÁGUE MANUAL (FORÇA O MOTOR A PARAR IMEDIATAMENTE)
        if btn_limpeza.value() == 0:
            time.sleep_ms(20)
            if btn_limpeza.value() == 0 and not valvula_aberta:
                # Corta o sinal do servo para ele estancar o movimento no lugar atual
                servo2_pwm.duty_u16(0) 
                
                relay1.value(1) # Abre a válvula d'água
                valvula_aberta = True
                t_lavagem_fim = time.ticks_add(agora, LAVAGEM_S * 1000)
                beep(150)
                
                if OLED_OK:
                    oled.fill(0)
                    oled.text("KiiRA Solar V1.2", 0, 0)
                    oled.text(">> LAVANDO <<", 0, 26)
                    oled.text("PAINEL TRAVADO", 0, 45)
                    oled.show()

        # Monitor do tempo da lavagem ativa
        if valvula_aberta:
            if time.ticks_diff(agora, t_lavagem_fim) >= 0:
                relay1.value(0) # Fecha a válvula d'água
                valvula_aberta = False
                
                # Reativa o sinal do servo devolvendo ele para a posição guardada
                mover_servo(angulo_atual) 
                beep(200)

        # ── BOTÃO DE TROCA DE MODOS
        if btn_reset.value() == 0:
            time.sleep_ms(20)
            if btn_reset.value() == 0:
                modo_manual = (modo_manual + 1) % 3  
                beep(50) 
                time.sleep_ms(300) 

        time.sleep_ms(20)

loop()