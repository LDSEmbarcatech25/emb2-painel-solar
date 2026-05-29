# =============================================================================
# RASTREADOR SOLAR INTELIGENTE — KiiRA V2.1 / ESP32-S3
# Firmware: MicroPython v1.22.0
# Versão: 2.1 — PRODUTIVO / DOIS BARRAMENTOS INDEPENDENTES INTEGRADOS
# =============================================================================
# MAPEAMENTO DE PINOS OFICIAL (KiiRA V2.1):
#   GPIO 14 → I²C0 SDA (OLED, MPU6050, HDC1080, BH1750 Esquerdo)
#   GPIO 21 → I²C0 SCL (OLED, MPU6050, HDC1080, BH1750 Esquerdo)
#   GPIO 41 → I²C1 SDA (Exclusivo para BH1750 Direito)
#   GPIO 42 → I²C1 SCL (Exclusivo para BH1750 Direito)
#   GPIO 44 → Servo Único (Eixo Ativo — Conector Superior RX)
#   GPIO 48 → Relé 1 / MOSFET 1 (Ativação da Válvula em Nível ALTO)
#   GPIO 45 → Botão 1 (Limpeza Manual — 5 segundos)
#   GPIO 46 → Botão 2 (Reset / Modo Manutenção Cíclico)
#   GPIO 3  → Buzzer Integrado (PWM Sinais Acústicos)
#   GPIO 1  → Potenciômetro (Mantido eletricamente, ignorado no software)
# =============================================================================

import math
import struct
import time
from machine import I2C, PWM, Pin

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
# PARÂMETROS CONFIGURÁVEIS DO SISTEMA
# =============================================================================
PASSO           = 2           # Graus deslocados por ciclo de ajuste
CICLO_MS        = 150         # Intervalo entre leituras de rastreamento
ANGULO_MIN      = 10          # Limite físico esquerdo do painel
ANGULO_MAX      = 170         # Limite físico direito do painel
ANGULO_CTR      = 90          # Posição central / de repouso (Noturno)
LAVAGEM_S       = 5           # Tempo ativo da lavagem em segundos
HISTERESE_LUX   = 45          # Diferença de Lux mínima para mover o motor

# Limiar fotométrico do Modo Noturno (Baseado no datasheet BH1750)
LUX_NOITE_CRITICO = 12        # Abaixo disso em ambos os lados, entra em Modo Noturno

TEMPO_FILTRO_INCLINACAO = 2000 # Filtro anti-agitação contra ventos (ms)

SERVO_DUTY_MIN  = 1638        # PWM correspondente a 0 graus
SERVO_DUTY_MAX  = 8192        # PWM correspondente a 180 graus

OLED_ADDR       = 0x3C
MPU_ADDR        = 0x68
HDC_ADDR        = 0x40
BH1750_ADDR     = 0x23        # Ambos usam endereço padrão por estarem isolados por hardware [cite: 49]
MPU_PWR_REG     = 0x6B        
MPU_ACCEL_REG   = 0x3B     

# =============================================================================
# INICIALIZAÇÃO DOS BARRAMENTOS I2C DUPLOS
# =============================================================================
# Canal I2C 0: Componentes integrados da placa + Sensor Solar Esquerdo
i2c0 = I2C(0, sda=Pin(14), scl=Pin(21), freq=400_000)

# Canal I2C 1: Linha isolada (Soft-I2C) nos pinos livres para o Sensor Solar Direito
i2c1 = I2C(1, sda=Pin(41), scl=Pin(42), freq=400_000)

try:
    oled = SSD1306_I2C(128, 64, i2c0, addr=OLED_ADDR)
    OLED_OK = True
except:
    OLED_OK = False

# ── Funções de Comunicação Direta com o BH1750 (Sem Bibliotecas) ────────────
def bh1750_init(i2c_bus):
    try:
        i2c_bus.writeto(BH1750_ADDR, b'\x01')  # Comando: Power On
        i2c_bus.writeto(BH1750_ADDR, b'\x10')  # Comando: Continuos High Resolution (1 lx de precisão)
    except:
        pass

def bh1750_ler_lux(i2c_bus):
    try:
        dados = i2c_bus.readfrom(BH1750_ADDR, 2)
        lux = (dados[0] << 8) | dados[1]   # Concatena os 16-bits de leitura [cite: 15]
        return round(lux / 1.2)            # Fator oficial de conversão em Lux [cite: 19, 49]
    except:
        return 0

# Inicializa os sensores ópticos nos barramentos correspondentes
bh1750_init(i2c0)  
bh1750_init(i2c1)  

def mpu_leitura_accel():
    try:
        raw = i2c0.readfrom_mem(MPU_ADDR, MPU_ACCEL_REG, 6)
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

# ── ATUADOR DE POSICIONAMENTO (SERVO MOTOR) NO PINO 44 ───────────────────────
servo2_pwm = PWM(Pin(44), freq=50, duty_u16=0)   

buzzer_pin = Pin(3, Pin.OUT)
buzzer = PWM(buzzer_pin)
buzzer.init(freq=5000, duty_u16=0)

angulo_alvo_antigo = ANGULO_CTR

def mover_servo(graus):
    graus = max(0, min(180, graus))
    duty2 = int(SERVO_DUTY_MIN + ((180 - graus) / 180.0) * (SERVO_DUTY_MAX - SERVO_DUTY_MIN))
    servo2_pwm.duty_u16(duty2)

def mover_servo_suave(graus_alvo, emitir_som=False):
    global angulo_alvo_antigo
    graus_alvo = max(0, min(180, graus_alvo))
    
    if abs(graus_alvo - angulo_alvo_antigo) > 3:
        if emitir_som:
            buzzer.init(freq=5000)
            buzzer.duty_u16(32768) 
            
        passo_rampa = 1 if graus_alvo > angulo_alvo_antigo else -1
        while abs(angulo_alvo_antigo - graus_alvo) > 0:
            angulo_alvo_antigo += passo_rampa
            mover_servo(angulo_alvo_antigo)
            time.sleep_ms(15) 
            
        if emitir_som:
            buzzer.duty_u16(0) 
    else:
        mover_servo(graus_alvo)
        angulo_alvo_antigo = graus_alvo

# ── COMPONENTES INTEGRADOS DE CONTROLE ELÉTRICO ─────────────────────────────
relay1      = Pin(48, Pin.OUT, value=0)  
btn_limpeza = Pin(45, Pin.IN, Pin.PULL_UP)
btn_reset   = Pin(46, Pin.IN, Pin.PULL_UP)

def beep(duracao_ms=100):
    try:
        buzzer.init(freq=5000)
        buzzer.duty_u16(32768)
        time.sleep_ms(duracao_ms)
        buzzer.duty_u16(0)
    except:
        pass

# =============================================================================
# VARIÁVEIS DE ESTADO E INICIALIZAÇÃO DO LOOP
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

    print("Firmware KiiRA V2.1 Ativo — Rastreamento Ativo")
    time.sleep_ms(100)
    mover_servo_suave(ANGULO_CTR, emitir_som=False)
    beep(200)

    while True:
        agora = time.ticks_ms()

        # Execução periódica do bloco de rastreamento e telemetria
        if time.ticks_diff(agora, t_ultimo_rastreamento) >= CICLO_MS:
            t_ultimo_rastreamento = agora

            # Coleta física isolada por barramentos
            lux_esq = bh1750_ler_lux(i2c0)       # Coleta do sensor na linha principal
            lux_dir = bh1750_ler_lux(i2c1)       # Coleta do sensor nos pinos dedicados 41/42        
            ax, ay, az = mpu_leitura_accel()
            inclinacao  = calcular_angulo(ax, az)

            if modo_manual == 0:
                # ── ALGORITMO: GESTÃO DO MODO NOTURNO AUTO
                if lux_esq <= LUX_NOITE_CRITICO and lux_dir <= LUX_NOITE_CRITICO:
                    if not estado_noturno:
                        estado_noturno = True
                        print("[Modo Noturno] Escuridão detectada. Recolhendo painel para o centro (90 deg).")
                    angulo_atual = ANGULO_CTR
                    mover_servo_suave(angulo_atual, emitir_som=False) 
                else:
                    estado_noturno = False
                    
                    # Filtro mecânico do acelerômetro contra tempestades/rajadas de vento
                    if abs(inclinacao) > 80:
                        if t_inicio_inclinacao == 0:
                            t_inicio_inclinacao = agora
                        
                        if time.ticks_diff(agora, t_inicio_inclinacao) >= TEMPO_FILTRO_INCLINACAO:
                            angulo_atual = ANGULO_CTR
                            mover_servo_suave(angulo_atual, emitir_som=False)
                    else:
                        t_inicio_inclinacao = 0 
                        
                        # ALGORITMO DE RASTREAMENTO DIFERENCIAL DIGITAL COMPENSADO
                        if abs(lux_dir - lux_esq) > HISTERESE_LUX:
                            if lux_dir > lux_esq:
                                angulo_atual = min(ANGULO_MAX, angulo_atual + PASSO)
                            else:
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

            # Renderização de Telemetria no OLED Integrado da KiiRA
            temp, umid = hdc_ler()
            if OLED_OK:
                oled.fill(0)
                oled.text("KiiRA Solar V2.1", 0, 0)
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
                status_v = "LAVANDO" if valvula_aberta else "Fechada"
                oled.text(f"Valvula: {status_v}", 0, 52)
                oled.show()

        # ── DISPARADOR DA VÁLVULA DE ENXÁGUE AUTOMÁTICO/MANUAL
        if btn_limpeza.value() == 0:
            time.sleep_ms(20)
            if btn_limpeza.value() == 0 and not valvula_aberta:
                relay1.value(1) 
                valvula_aberta = True
                t_lavagem_fim = time.ticks_add(agora, LAVAGEM_S * 1000)
                beep(150)

        # ── INTERFACE ACÚSTICA OSCILANTE DA LAVAGEM ATIVA
        if valvula_aberta:
            if (agora // 200) % 2 == 0:
                buzzer.init(freq=4500)
                buzzer.duty_u16(32768)
            else:
                buzzer.init(freq=3500)
                buzzer.duty_u16(32768)

            if time.ticks_diff(agora, t_lavagem_fim) >= 0:
                relay1.value(0) 
                valvula_aberta = False
                buzzer.duty_u16(0) 
                beep(200)

        # ── INTERRUPÇÃO E TROCA CÍCLICA DE MODOS OPERACIONAIS
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
                    lux_esq = bh1750_ler_lux(i2c0)       
                    lux_dir = bh1750_ler_lux(i2c1)
                    if abs(lux_dir - lux_esq) > HISTERESE_LUX:
                        if lux_dir > lux_esq:
                            angulo_atual = min(ANGULO_MAX, angulo_atual + PASSO)
                        else:
                            angulo_atual = max(ANGULO_MIN, angulo_atual - PASSO)
                    mover_servo_suave(angulo_atual, emitir_som=True)
                    
                time.sleep_ms(300) 

        time.sleep_ms(20) 

loop()
