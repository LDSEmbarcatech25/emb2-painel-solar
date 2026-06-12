# PROJETO DE ENCERRAMENTO DE RESIDÊNCIA
### DISPOSITIVO IoT PARA RASTREAMENTO SOLAR ATIVO E MANUTENÇÃO DE PAINÉIS 

## 1. O Problema

Sou Diretor de Operações em uma usina de geração de energia solar fotovoltaica. Um dos nossos maiores desafios é a perda de eficiência dos painéis ao longo do dia por dois motivos principais: o primeiro é o posicionamento estático do painel, que deixa de captar o ápice da radiação conforme o sol se move; o segundo é o acúmulo de poeira, folhas e sujeira na superfície do vidro (*soiling*), o que bloqueia a luz e derruba a geração de energia. Deslocar equipes de limpeza para checar os painéis em grandes extensões de terra gera um custo operacional altíssimo.

Precisamos de uma solução embarcada para otimização e manutenção de painéis solares (*Smart Solar Tracker*). O dispositivo controlará a inclinação mecânica do painel utilizando um servo motor baseado na leitura diferencial de dois sensores de luminosidade (LDRs) posicionados nas extremidades (direita e esquerda), buscando sempre o ponto de maior intensidade de luz. O sistema também monitorará continuamente a temperatura, a umidade do ar e a angulação física real do painel (usando um acelerômetro). Todas as informações devem ser enviadas para uma Dashboard de monitoramento remoto e exibidas localmente em um display.

O sistema operará com três eixos críticos de manutenção e supervisão:

* **Rastreamento Solar Ativo:** O firmware lerá os dois LDRs. Se houver uma diferença de luminosidade entre eles, o servo motor deve ser acionado para rotacionar o painel em direção ao lado mais claro, maximizando a captação de energia em tempo real.
* **Auditoria Visual de Sujeira:** Através da Dashboard, o operador poderá enviar um comando para que a câmera integrada registre uma imagem da superfície do painel solar. Isso permitirá que um analista humano verifique remotamente o nível de poeira ou obstrução antes de tomar uma decisão de manutenção.
* **Sistema de Lavagem Automatizado:** O dispositivo controlará um relé conectado a uma válvula de água. A limpeza pode ser disparada de duas formas: manualmente através de um comando direto na Dashboard (após a análise da foto) ou de forma autônoma pela lógica local (ex: ao final do dia se as condições de umidade permitirem).

## 2. Recomendações de Firmware e Conectividade

* **Algoritmo de Rastreamento Diferencial:** O firmware deve calcular a diferença absoluta entre as leituras analógicas (ADC) do LDR Direito e do LDR Esquerdo. Para evitar oscilações contínuas e desgaste do servo motor, implemente uma zona morta (*deadband*): o motor só deve se mover se a diferença entre os sensores ultrapassar um limite mínimo configurado.
* **Cálculo de Inclinação via Acelerômetro:** Use os dados de aceleração dos eixos do acelerômetro para calcular o ângulo real de inclinação do painel e cruzar essa informação com a posição do servo, garantindo que o painel não force os limites mecânicos da estrutura.
* **Comunicação IoT Assíncrona (MQTT):** O protocolo MQTT é altamente recomendado para enviar os pacotes textuais de telemetria de ângulo, clima e luz. O dispositivo deve se inscrever nos tópicos de comando para acionar instantaneamente a válvula de água (Relé) e a captura e envio da foto.
* **Temporização Não-Bloqueante:** O processo de rastreamento dos LDRs e ajuste do servo motor deve rodar em paralelo com as requisições de rede. Evite o uso de funções bloqueantes para que o envio de imagens da câmera não congele os motores ou a leitura do acelerômetro.

## 3. Requisitos de Modelagem 3D 

Este projeto envolve componentes expostos ao tempo (sol direto, chuva e vento), exigindo um design mecânico focado em robustez e vedação externa:

* **Vedação e Proteção Intempéries:** O gabinete principal que protege o ESP32-S3 e o módulo de relés deve ser hermético, prevenindo a entrada de água da chuva ou da própria água do sistema de limpeza.
* **Posicionamento Estratégico dos LDRs e Câmera:**
    * Os dois LDRs devem ser fixados externamente no case, preferencialmente separados por uma pequena barreira ou "septo" centralizador de sombra, o que acentua a diferença de leitura quando o sol se move.
    * A câmera deve ser posicionada em um suporte elevado ou inclinado apontando diretamente para a face superior do painel solar para conseguir capturar com clareza o estado de limpeza do vidro.
* **Acoplamento Mecânico do Servo:** O modelo 3D deve prever o chassi de suporte estrutural onde o servo motor se acoplará fisicamente para girar o eixo de fixação do modelo do painel solar.
* **Isolamento do Sensor de Clima:** O sensor de temperatura/umidade do ar deve ser instalado em um abrigo ventilado na parte inferior ou traseira do case (protegido da luz solar direta), evitando que a radiação sobre o plástico distorça a medição real do clima local.

## 4. Entregável Inicial: Documento de Arquitetura e Viabilidade Técnica

Antes de iniciar o desenvolvimento prático do firmware ou a modelagem 3D do gabinete, a equipe deverá entregar um relatório técnico de arquitetura contendo obrigatoriamente os seguintes tópicos:

* **4.1. Mapeamento de Hardware e Componentes:** A equipe deve identificar e documentar os componentes ativados:
    * **Identificação:** Modelos exatos dos sensores LDR, sensor de temperatura/umidade, acelerômetro, display, servo motor, módulo de relé e câmera.
    * **Pinout (Tabela de GPIOs):** Tabela detalhada especificando quais pinos analógicos (ADC) lerão os LDRs, qual pino gerará o sinal PWM para o controle de posição do servo motor e as conexões digitais do display e relé.
    * **Barramentos Internos:** Indicação das interfaces configuradas no microcontrolador (ex: I2C para display e acelerômetro).

* **4.2. Diagrama de Blocos do Sistema:** Apresentar um esquema gráfico modular do hardware. No centro deve figurar o microcontrolador ESP32-S3 e, ao redor, blocos conectados por setas indicando o fluxo de sinal:
    * **Setas de entrada (In):** LDR Direito, LDR Esquerdo, Sensores de Clima, Acelerômetro e Câmera apontando para o ESP32-S3.
    * **Setas de saída (Out):** ESP32-S3 apontando para o Display, Servo Motor (via PWM) e Relé (Válvula de água).
    * **Fluxo de rede:** Seta indicando a transmissão Wi-Fi bidirecional com a Dashboard de supervisão da usina.

* **4.3. Especificação do Protocolo de Comunicação e Lógica IoT:**
    * **Lógica do Algoritmo de Rastreamento:** Explicação textual ou por fluxograma de como o programa decide mover o servo motor com base no delta ($\Delta$) de leitura dos LDRs.
    * **Protocolo de Aplicação de Rede:** Escolha do protocolo de comunicação de rede para tráfego simultâneo de telemetria leve e blocos de imagem sob demanda.
    * **Modelagem de Dados (Payload JSON):** Exemplo de estrutura JSON contendo os dados enviados à nuvem (incluindo o ângulo lido pelo acelerômetro) e as mensagens de acionamento manual da limpeza.
