from umqtt.simple import MQTTClient

class MqttService:
    def __init__(self, mqtt_broker:str="broker.emqx.io", mqtt_client_id="ESP32", mqtt_user=None, mqtt_password=None):
        self.mqtt = MQTTClient(
            mqtt_client_id,
            mqtt_broker,
            user=mqtt_user,
            password=mqtt_password
        )

        self.topico = None
        self.msg = None
        self.tem_mensagem = None

        self.mqtt.set_callback(self.msg_log)

    def conectar_broker(self):
        self.mqtt.connect()
        print("foi")

    def sub(self, topico):
        self.mqtt.subscribe(topico)

    def pub(self, topico, msg):
        self.mqtt.publish(topico, msg)

    def check(self):
        self.mqtt.check_msg()

    def msg_log(self, topico, msg):
        self.topico = topico
        self.msg = msg
        self.tem_mensagem = True

        print("Topico:", topico.decode())
        print("Mensagem:", msg.decode())

    def sub_multiplos_topicos(self, topicos:list[str]) -> None:
        for topico in topicos:
            self.sub(topico)
            print(f"inscrito no topico: {topico}")

    def chegou_msg(self):
        self.mqtt.check_msg()

    def reset(self):
        self.tem_mensagem = False
        self.msg = None
        self.topico = None