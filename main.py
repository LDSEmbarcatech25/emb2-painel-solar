# =============================================================================
# RASTREADOR SOLAR INTELIGENTE — KiiRA V2.0 / ESP32-S3
# Firmware: MicroPython v1.22.0
# Versão: 1.2 
# =============================================================================
# MAPA DE PINOS DA PLACA KIIRA V2.0:
#   GPIO 1  → LDR 1 Integrado (ADC Analógico Esquerdo)
#   GPIO 42 → LDR 2 Externo (Digital Direito — Conector "Sensors")
#   GPIO 43 → Servo 1 (Eixo Principal — Conector Superior)
#   GPIO 44 → Servo 2 (Eixo Espelhado — Conector Superior)
#   GPIO 14 → I²C SDA (OLED, MPU6050, HDC1080)
#   GPIO 21 → I²C SCL (OLED, MPU6050, HDC1080)
#   GPIO 48 → Relé 1 / MOSFET 1 (Ativação em Nível ALTO)
#   GPIO 45 → Botão 1 (Limpeza Manual)
#   GPIO 46 → Botão 2 (Reset / Modo Manutenção Cíclico)
#   GPIO 3  → Buzzer/LED Integrado (PWM 5kHz)
# =============================================================================

import math
import struct
import time
from machine import ADC, I2C, PWM, Pin

# ── Driver SSD1306 embutido para o OLED Integrado ───────────────────────────
class SSD1306:
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        self.init_display()
    def init_display(self):
        for cmd in (0xAE, 0xD5, 0x80, 0xA8, self.height - 1, 0xD3, 0x00, 0x40, 0x8D, 0x14 if not self.external_vcc else 0x10, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x12 if self.height == 64 else 0x02, 0x81, 0xCF if not self.external_vcc else 0x9F, 0xD9, 0xF1 if not self.external_vcc else 0x22, 0xDB, 0x40, 0xA4, 0xA6, 0xAF):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()
    def fill(self, col):
        self.buffer = bytearray([0xff if col else 0x00] * len(self.buffer))
    def pixel(self, x, y, col):
        if 0 <= x < self.width and 0 <= y < self.height:
            index = (y // 8) * self.width + x
            offset = y % 8
            if col: self.buffer[index] |= (1 << offset)
            else: self.buffer[index] &= ~(1 << offset)
    def text(self, string, x, y, col=1):
        import framebuf
        fbuf = framebuf.FrameBuffer(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        fbuf.text(string, x, y, col)
    def show(self):
        x0, x1 = 0, self.width - 1
        self.write_cmd(0x21); self.write_cmd(x0); self.write_cmd(x1)
        self.write_cmd(0x22); self.write_cmd(0); self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)

class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3c, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        super().__init__(width, height, external_vcc)
    def write_cmd(self, cmd):
        self.temp[0] = 0x00; self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)
    def write_data(self, buf):
        self.i2c.writeto(self.addr, b'\x40' + buf)

# =============================================================================
# PARÂMETROS CONFIGURÁVEIS
# =============================================================================
PASSO       = 2           
CICLO_MS    = 150         
ANGULO_MIN  = 10          
ANGULO_MAX  = 170         
ANGULO_CTR  = 90          
LAVAGEM_S   = 10          
ADC_AMOSTRAS  = 4         

# Limiar de escuridão total (Noite) para ativação do retorno automático
LDR_NOITE_CRITICO = 3800  

TEMPO_FILTRO_INCLINACAO = 2000  

SERVO_DUTY_MIN = 1638     
SERVO_DUTY_MAX = 8192     

OLED_ADDR   = 0x3C
MPU_ADDR    = 0x68
HDC_ADDR    = 0x40
MPU_PWR_REG = 0x6B        
MPU_ACCEL_REG = 0x3B     

# =============================================================================
# INICIALIZAÇÃO DO HARDWARE FIXO
# =============================================================================
i2c = I2C(0, sda=Pin(14), scl=Pin(21), freq=400_000)

try:
    oled = SSD1306_I2C(128, 64, i2c, addr=OLED_ADDR)
    oled.fill(0)
    oled.text("KiiRA Solar V1.2", 0, 0)
    oled.text("Iniciando...", 0, 16)
    oled.show()
    OLED_OK = True
except:
    OLED_OK = False

def mpu_leitura_accel():
    try:
        raw = i2c.readfrom_mem(MPU_ADDR, MPU_ACCEL_REG, 6)
        ax_raw, ay_raw, az_raw = struct.unpack('>hhh', raw)
        return ax_raw / 16384.0, ay_raw / 16384.0, az_raw / 16384.0
    except:
        return 0.0, 0.0, 1.0  

def calcular_angulo(ax, az):
    try:
        return math.atan2(ax, az) * (180 / math.pi)
    except:
        return 0.0

def hdc_ler():
    try:
        i2c.writeto(HDC_ADDR, b'\x00')
        time.sleep_ms(15)
        dados = i2c.readfrom(HDC_ADDR, 4)
        t_raw = (dados[0] << 8) | dados[1]
        h_raw = (dados[2] << 8) | dados[3]
        return round(((t_raw / 65536.0) * 165.0 - 40.0), 1), round(((h_raw / 65536.0) * 100.0), 1)
    except:
        return 0.0, 0.0

try:
    i2c.writeto_mem(MPU_ADDR, MPU_PWR_REG, b'\x00')
except:
    pass

# ── CONFIGURAÇÃO DOS SENSORES ────────────────────────────────────────────────
adc_ldr1 = ADC(Pin(1), atten=ADC.ATTN_11DB)        
pin_ldr2 = Pin(42, Pin.IN)                         

def ler_ldr1_estavel():
    try:
        soma = sum(adc_ldr1.read_u16() >> 4 for _ in range(ADC_AMOSTRAS))
        return soma // ADC_AMOSTRAS
    except:
        return 0

# ── INICIALIZAÇÃO DOS SERVOS (GPIO 43 e 44) ──────────────────────────────────
servo1_pwm = PWM(Pin(43), freq=50, duty_u16=0)   
servo2_pwm = PWM(Pin(44), freq=50, duty_u16=0)   

# Correção física do Buzzer para ESP32-S3 real
buzzer_pin = Pin(3, Pin.OUT)
buzzer = PWM(buzzer_pin)
buzzer.init(freq=5000, duty_u16=0)

# Controle interno para suavizar movimentos bruscos
angulo_alvo_antigo = ANGULO_CTR

def mover_servo(graus):
    """Aplica o pulso PWM diretamente nos pinos do servo"""
    graus = max(0, min(180, graus))
    duty1 = int(SERVO_DUTY_MIN + (graus / 180.0) * (SERVO_DUTY_MAX - SERVO_DUTY_MIN))
    duty2 = int(SERVO_DUTY_MIN + ((180 - graus) / 180.0) * (SERVO_DUTY_MAX - SERVO_DUTY_MIN))
    servo1_pwm.duty_u16(duty1)
    servo2_pwm.duty_u16(duty2)

def mover_servo_suave(graus_alvo, emitir_som=False):
    """Muda o ângulo dividindo em pequenos passos. Toca buzzer se emitir_som for True"""
    global angulo_alvo_antigo
    graus_alvo = max(0, min(180, graus_alvo))
    
    # Se a diferença for considerável, faz rampa de aproximação suave
    if abs(graus_alvo - angulo_alvo_antigo) > 3:
        if emitir_som:
            buzzer.duty_u16(32768) # 50% de duty cycle real no ESP32 para som ideal
            
        passo_rampa = 1 if graus_alvo > angulo_alvo_antigo else -1
        while abs(angulo_alvo_antigo - graus_alvo) > 0:
            angulo_alvo_antigo += passo_rampa
            mover_servo(angulo_alvo_antigo)
            time.sleep_ms(15) # Tempo sutil entre incrementos da rampa
            
        if emitir_som:
            buzzer.duty_u16(0) 
    else:
        mover_servo(graus_alvo)
        angulo_alvo_antigo = graus_alvo

# ── ATUADORES DE FÁBRICA (NÍVEL LÓGICO ALTO) ─────────────────────────────────
relay1      = Pin(48, Pin.OUT, value=0)  
btn_limpeza = Pin(45, Pin.IN, Pin.PULL_UP)
btn_reset   = Pin(46, Pin.IN, Pin.PULL_UP)

def beep(duracao_ms=100):
    try:
        buzzer.duty_u16(32768)
        time.sleep_ms(duracao_ms)
        buzzer.duty_u16(0)
    except:
        pass

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================
angulo_atual   = ANGULO_CTR
valvula_aberta = False
t_lavagem_fim  = 0
t_ultimo_rastreamento = 0

modo_manual = 0  
t_inicio_inclinacao = 0  
estado_noturno = False

def loop():
    global angulo_atual, valvula_aberta, t_lavagem_fim, t_ultimo_rastreamento, modo_manual, t_inicio_inclinacao, estado_noturno

    print("Firmware KiiRA V1.2 Ativo - Sistema operando!")
    mover_servo_suave(ANGULO_CTR, emitir_som=False)
    beep(200)

    while True:
        agora = time.ticks_ms()

        if time.ticks_diff(agora, t_ultimo_rastreamento) >= CICLO_MS:
            t_ultimo_rastreamento = agora

            ldr1_val = ler_ldr1_estavel()       
            ldr2_sat = pin_ldr2.value()         

            ax, ay, az = mpu_leitura_accel()
            inclinacao  = calcular_angulo(ax, az)

            if modo_manual == 0:
                # ── SEGURANÇA 1: RETORNO AUTOMÁTICO SE COMPLETAMENTE ESCURO (PÔR DO SOL)
                if ldr1_val >= LDR_NOITE_CRITICO:
                    if not estado_noturno:
                        estado_noturno = True
                        print("[Modo Noturno] Luminosidade zerada. Retornando ao ponto de descanso de forma suave.")
                    angulo_atual = ANGULO_CTR
                    mover_servo_suave(angulo_atual, emitir_som=False) 
                else:
                    estado_noturno = False
                    
                    # Verificação de inclinação crítica do acelerômetro
                    if abs(inclinacao) > 80:
                        if t_inicio_inclinacao == 0:
                            t_inicio_inclinacao = agora
                        
                        if time.ticks_diff(agora, t_inicio_inclinacao) >= TEMPO_FILTRO_INCLINACAO:
                            angulo_atual = ANGULO_CTR
                            mover_servo_suave(angulo_atual, emitir_som=False)
                    else:
                        t_inicio_inclinacao = 0 
                        
                        # Rastreamento convencional diurno pelos LDRs
                        if ldr2_sat == 1:
                            angulo_atual = min(ANGULO_MAX, angulo_atual + PASSO)
                            mover_servo_suave(angulo_atual, emitir_som=False)
                        elif ldr1_val > 2500:
                            angulo_atual = max(ANGULO_MIN, angulo_atual - PASSO)
                            mover_servo_suave(angulo_atual, emitir_som=False)
            
            elif modo_manual == 1:
                t_inicio_inclinacao = 0
                angulo_atual = ANGULO_CTR
                mover_servo_suave(angulo_atual, emitir_som=True) 
                
            elif modo_manual == 2:
                t_inicio_inclinacao = 0
                angulo_atual = 0  
                mover_servo_suave(angulo_atual, emitir_som=True) 

            temp, umid = hdc_ler()
            if OLED_OK:
                oled.fill(0)
                oled.text("KiiRA Solar V1.2", 0, 0)
                oled.text(f"L1:{ldr1_val} L2:{ldr2_sat}", 0, 13) 
                
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
                status_v = "LAVANDO" if valvula_aberta else "Fechada"
                oled.text(f"Valvula: {status_v}", 0, 52)
                oled.show()

        if btn_limpeza.value() == 0:
            time.sleep_ms(20)
            if btn_limpeza.value() == 0 and not valvula_aberta:
                relay1.value(1) 
                valvula_aberta = True
                t_lavagem_fim = time.ticks_add(agora, LAVAGEM_S * 1000)
                beep(150)

        if btn_reset.value() == 0:
            time.sleep_ms(20)
            if btn_reset.value() == 0:
                modo_manual = (modo_manual + 1) % 3  
                beep(50) 
                
                if OLED_OK:
                    oled.fill(0)
                    if modo_manual == 0:
                        oled.text("MODO AUTOMATICO", 0, 26)
                    elif modo_manual == 1:
                        oled.text("RESET POSICAO 90", 0, 26)
                    elif modo_manual == 2:
                        oled.text("MODO MANUTENCAO", 0, 26)
                    oled.show()
                
                if modo_manual == 0:
                    ldr1_val = ler_ldr1_estavel()
                    ldr2_sat = pin_ldr2.value()
                    if ldr2_sat == 1:
                        angulo_atual = min(ANGULO_MAX, angulo_atual + PASSO)
                    elif ldr1_val > 2500:
                        angulo_atual = max(ANGULO_MIN, angulo_atual - PASSO)
                    
                    mover_servo_suave(angulo_atual, emitir_som=True)
                    
                time.sleep_ms(300) 

        if valvula_aberta and time.ticks_diff(agora, t_lavagem_fim) >= 0:
            relay1.value(0) 
            valvula_aberta = False

        time.sleep_ms(10)

loop()
