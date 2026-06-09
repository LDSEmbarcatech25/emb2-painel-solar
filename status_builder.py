import json

class StatusBuilder:
    def __init__(self):
        self.payload = {
            "clima":{},
            "luminosidade": {},
            "angulo_painel": None,
        }

    def set_clima(self,umidade,temperatura):
        self.payload["clima"] = {
            "umidade": int(umidade),
            "temperatura": int(temperatura)
        }

        return self

    def set_luminosidade(self,ldr_esq,ldr_dir):
        self.payload["luminosidade"] = {
            "LDR_Esq": ldr_esq,
            "LDR_Dir": ldr_dir
        }
        return self

    def set_angulo_painel(self,angulo_painel):

        self.payload["angulo_painel"] = angulo_painel

        return self

    def build(self):
        return json.dumps(self.payload)