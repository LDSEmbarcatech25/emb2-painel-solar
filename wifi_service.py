import network
import time

# https://docs.micropython.org/en/latest/esp8266/tutorial/network_basics.html
class WifiService:

    def __init__(self, nome_rede:str, senha_rede:str):
        self.nome_rede = nome_rede
        self.senha_rede = senha_rede
        self.sta_if = network.WLAN(network.STA_IF)

    def conectar_rede(self):

        if not self.esta_conectado():
            print("Conectando...")

            self.sta_if.active(True)
            self.sta_if.connect(self.nome_rede, self.senha_rede)

            while not self.esta_conectado():
                time.sleep(1)
                print("Tentando conectar...")

        print("Conectado!")
        print(f"wifi config {self.sta_if.ifconfig()}")

    def esta_conectado(self):
        return self.sta_if.isconnected()
