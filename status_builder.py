import json

class StatusBuilder:
    def __init__(self):
        self.payload = {
            "clima":{},
            "luminosidade": {},
            "posicao_painel": {},
        }

    def set_clima(self,umidade,temperatura):
        self.payload["clima"] = {
            "umidade": umidade,
            "temperatura": temperatura
        }

        return self

    def set_luminosidade(self,ldr_esq,ldr_dir,delta):
        self.payload["luminosidade"] = {
            "ldr_esq": ldr_esq,
            "ldr_dir": ldr_dir,
            "delta": delta,
        }
        return self

    def set_posicao_painel(self,x,y):

        self.payload["posicao_painel"] = {
            "x": x,
            "y": y
        }

        return self

    def build(self):
        return json.dumps(self.payload)