# Roteiro do pitch, até 5 minutos

Tempo-alvo: 4 minutos e 45 segundos. Deixe o sistema aberto, com o replay autorizado cadastrado e pelo menos um alerta pendente.

## Slide 1, abertura (0:00 a 0:25)

> Esta câmera já existe no canteiro. O que faltava era transformar o vídeo em uma ação de segurança. O Vigilante.AI analisa capacete e colete, separa ocorrências por pessoa e envia uma evidência para revisão. O técnico continua decidindo. A IA reduz o tempo entre a situação de risco e a resposta.

## Slide 2, evolução do projeto (0:25 a 0:55)

> Na entrega anterior, o núcleo já funcionava localmente: Next.js, FastAPI, PostgreSQL e YOLO sobre streams RTSP. Desde então, implementamos WhatsApp bidirecional, alertas no Teams, blur da região da cabeça, assistente com base de conhecimento, replay de vídeo e uma avaliação mais exigente do modelo. Hoje, o back-end passa 128 testes, o front-end fecha o build de produção e o banco está no Amazon RDS.

## Slide 3, fluxo e demonstração ao vivo (0:55 a 1:50)

> Este é o hub de câmeras. Para a demonstração, usamos um vídeo replay autorizado, portanto o fluxo não depende de uma câmera externa. Vou iniciar o stream. O worker detecta a pessoa e procura evidência de capacete e colete. Quando encontra uma possível ausência, cria um alerta pendente. O recorte aparece anonimizado. Eu confirmo ou rejeito a ocorrência. Essa decisão entra no histórico e também pode virar amostra para o próximo treinamento. Depois da confirmação, o sistema pode avisar a equipe no WhatsApp ou no Teams. O painel continua como fonte de verdade, inclusive se uma integração externa falhar.

[Mostrar, sem narrar menus: login, câmera, detecção, alerta e decisão. Se o stream falhar, usar o replay e a evidência já capturada.]

## Slide 4, entrada no mercado (1:50 a 2:20)

> O primeiro cliente que buscamos é uma construtora pequena ou média, com até quatro câmeras IP e um técnico de segurança responsável. A venda começa por demonstração consultiva e por parceiros de SST ou CFTV. A proposta é aproveitar as câmeras instaladas, configurar acesso por VPN, executar um piloto curto e medir falsos alertas, tempo de revisão e uso por câmera.

## Slide 5, modelo em validação e oferta (2:20 a 3:05)

> Hoje ainda não é honesto cobrar como um produto validado. O resultado de mAP 0,944 veio de uma divisão com frames semelhantes em treino e validação. Na amostra de CCTV real, o modelo anterior cobriu apenas 4% dos trabalhadores e gerou 100% de falsos alarmes de capacete. Por isso, buscamos um parceiro de codesenvolvimento: piloto gratuito de noventa dias, até quatro câmeras, sem SLA e com uso autorizado de amostras para treinamento. Depois, oferecemos três meses assistidos por R$ 990. O plano de R$ 2.490 só entra após validação por câmera.

## Slide 6, fluxo de caixa (3:05 a 3:35)

> O estágio de validação consome R$ 15.630 em seis meses. Nos três primeiros meses não há receita. Nos três seguintes, a projeção assume apenas um plano fundador de R$ 990 por mês. Os fundadores mantêm seus empregos e não retiram pró-labore. Essa conta trata dados de canteiro como investimento necessário, não como um detalhe que o mercado resolverá depois.

## Slide 7, banco em nuvem na AWS (3:35 a 4:15)

> Para cumprir o requisito de banco em nuvem sem desperdiçar crédito, o PostgreSQL está no Amazon RDS, com TLS, criptografia e acesso restrito ao IP atual. O front-end, a API e o YOLO executam no k3s da máquina de demonstração. O Cloudflare Tunnel publica o sistema em vigilanteai.outis.com.br. As migrations chegaram à revisão 0005, o pgvector está ativo e o alerta permaneceu salvo depois do reinício do back-end. O RDS custa cerca de US$ 4,06 por sete dias, mas o desembolso previsto é zero enquanto os créditos elegíveis cobrirem a conta.

## Slide 8, fechamento (4:15 a 4:45)

> O MVP funcional está em aproximadamente 86% do escopo. O fluxo completo está validado com banco em nuvem, replay, alerta e persistência. Para o piloto comercial ainda faltam imagens representativas, medição por câmera real e os instrumentos de privacidade. O código está no GitHub, e a documentação inclui o Go to Market, seis meses de caixa, breakeven, CAC, LTV e os custos da AWS.

## Checklist de gravação

- Ocultar tokens, URLs privadas, telefones e dados pessoais.
- Fechar notificações do computador.
- Usar resolução 1080p e ampliar o navegador para o texto ficar legível.
- Antes de gravar, executar `scripts/k3s-fase5-aws.sh status` e confirmar que o login público e a câmera respondem.
- Se mostrar o console da AWS, enquadrar apenas o status `Available` e ocultar conta, endpoint e credenciais.
- Deixar o link do GitHub visível no último slide.
- Publicar no YouTube como não listado e testar o link em janela anônima.
- Executar `scripts/finalize-fase5.sh URL_DO_YOUTUBE` para substituir o marcador, reconstruir os PDFs e gerar o ZIP final.
