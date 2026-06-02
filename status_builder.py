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
            "umidade": int(umidade),
            "temperatura": int(temperatura)
        }

        return self

    def set_luminosidade(self,ldr_esq,ldr_dir,delta):
        self.payload["luminosidade"] = {
            "LDR_Esq": ldr_esq,
            "LDR_Dir": ldr_dir,
            "delta": delta
        }
        return self

    def set_posicao_painel(self,x,y):

        self.payload["posicao_painel"] = {
            "x": int(x),
            "y": y
        }

        return self

    def build(self):
        return json.dumps(self.payload)