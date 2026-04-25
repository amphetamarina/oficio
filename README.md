# ofício

<img src="imagens/logo.png" width="600" />

`0.0.2 · experimental`

um ofício pede poucos instrumentos bem escolhidos e um único banco onde tudo está ao alcance da mão. este repositório descreve uma camada fina sobre um cofre do Obsidian, alguns ganchos para agentes e um conjunto de convenções de trabalho, todos derivados da Humane Interface de Jef Raskin. não pretende ser catedral nem sistema operacional. é a oficina onde se trabalha bem.


## raiz

Jef Raskin iniciou o projeto Macintosh em 1979, foi vencido pela interface gráfica vitoriana que se seguiu, e passou os vinte e cinco anos seguintes desenhando interfaces que respeitassem o tempo cognitivo de quem as usa, em máquinas como Swyft, Canon Cat e o ambiente Archy.

a tese dele cabe em uma linha: a interface deve minimizar o intervalo entre intenção e execução sem cobrar tributo de atenção.

o ofício toma essa tese como projeto e a aplica a um cotidiano comum, de quem escreve, lê e conversa com agentes ao longo do dia. o ponto de partida não é uma pilha de ferramentas: é um cofre do Obsidian, sincronizado, disponível no desktop e no celular, onde o texto vive antes, durante e depois da ação.


## arquitetura

<img src="imagens/arquitetura.png" width="900" />

três peças, todas leves. no centro, o cofre do Obsidian: espaço de escrita, leitura, comando e memória. de um lado, agentes como Codex e Pi, que leem notas, respondem a intenções registradas no cofre e escrevem de volta quando precisam produzir texto, registrar andamento ou deixar rastro. do outro, a camada mínima que observa mudanças de sincronização e aciona os ganchos correspondentes.

o cofre permanece a única fonte de verdade. não há caixa de entrada paralela, painel de controle separado nem banco oculto. o que a usuária escreve no Obsidian é o que os agentes veem. o que os agentes fazem volta ao Obsidian como nota, alteração ou log. assume-se que persistência, salvamento e sincronização já pertencem ao próprio Obsidian: autossave e sync fecham o ciclo.

os únicos scripts necessários são ganchos pequenos: um jeito de um agente reconhecer pedidos no cofre, um jeito de reagir quando uma sincronização traz mudança nova, e um jeito de escrever respostas ou registros no lugar combinado. o resto é convenção de texto.


## princípios

cada princípio entra com a definição raskiniana e a decisão de projeto correspondente. a ordem é a do impacto sentido no corpo, não a da hierarquia teórica.

### locus de atenção

<img src="imagens/locus_atencao.png" width="500" />

_a interface deve respeitar o ponto onde o cuidado está pousado e nunca arrancá-lo de lá sem motivo digno._

#### decisão
- Obsidian é o ponto de partida da interface.
- o cofre concentra escrita, leitura, pedidos a agentes, respostas e registros.
- agentes não disputam foco com janelas próprias. eles leem o cofre, reagem quando há algo a fazer e escrevem de volta quando a resposta pertence ao trabalho.
- **nada pisca, nada balança, nada interrompe. olha-se quando se quer.**

### sem modos

<img src="imagens/sem_modos.png" width="400" />

_a mesma tecla deve sempre fazer a mesma coisa, em qualquer estado do sistema._


#### decisão
- o Obsidian fica o mais próximo possível de texto direto.
- menos plugins é melhor. só entra extensão quando ela reduz atrito real sem criar outro lugar para lembrar.
- pedidos a agentes são notas ou trechos de notas, não estados escondidos de uma interface auxiliar.
- a tabela de atalhos vive no próprio cofre, em `Hotkeys.md`, para que a previsibilidade seja auditável e legível como o resto do trabalho.

### quasimodos

<img src="imagens/quasimodos.png" width="400" />

_estados que existem somente enquanto a tecla está pressionada são aceitáveis. o corpo sente fisicamente que está num estado especial, então o estado não fica esquecido em segundo plano._

#### decisão
- a invocação explícita de agentes pode acontecer por gesto curto, mas o pedido resultante vira texto no cofre.
- o estado especial termina no gesto. o acompanhamento depois disso é nota, log ou resposta escrita.
- nenhum modo dura mais que o gesto que o sustenta.

### monotonia

<img src="imagens/monotonia.png" width="400" />

_uma única maneira de fazer cada coisa. reduz ruído de escolha, fortalece habituação, devolve para o dia o tempo que múltiplos caminhos consomem._

#### decisão
- um cofre, uma fonte de verdade, um lugar para pedir trabalho.
- agentes podem ser muitos, mas o protocolo é o mesmo: ler Obsidian, reagir, escrever Obsidian.
- quando há tentação de oferecer "também por painel, também por aplicativo, também por chat separado", o ofício recusa. caminho duplicado é caminho a manter.

### LEAP

<img src="imagens/LEAP.png" width="400" />

_busca incremental como navegação primária, no lugar da rolagem e do clique: poucas teclas levam o cursor a qualquer ponto de qualquer documento, sem mudança de janela e sem modo._

#### decisão
- a navegação primária é a busca do próprio Obsidian: título, arquivo, link e texto.
- o cofre deve ser organizado para ser encontrado, não decorado. bons nomes, links explícitos e notas pequenas valem mais que indexadores pesados.
- não há dependência de plugin de busca adicional. se a busca nativa e a estrutura do cofre bastam, nada mais entra.
- em qualquer ponto do ofício, poucas teclas chegam ao destino.

### desfazer universal

<img src="imagens/desfazer_universal.png" width="400" />

_toda ação é reversível. nenhum diálogo modal pedindo confirmação._

#### decisão
- o primeiro desfazer é o do próprio Obsidian.
- mudanças de agentes são registradas como texto no cofre: antes de alterar, durante a execução ou depois, conforme o tipo de tarefa exigir.
- a reversibilidade nasce de notas legíveis, histórico de sincronização e logs simples, não de confirmação preventiva.
- o sistema confia que a usuária vai querer desfazer, então evita perguntar antes.

### texto eterno

<img src="imagens/texto_eterno.png" width="400" />

_salvar e carregar são vestígios de disquete. o documento existe e persiste sempre._

#### decisão
- o autossave do Obsidian permanece ligado.
- o sync do cofre é assumido como parte do ambiente, inclusive entre desktop e mobile.
- agentes escrevem no cofre quando precisam persistir resultado ou registrar ação. não mantêm uma verdade própria esperando exportação.
- em nenhum lugar há "deseja salvar antes de sair?". o texto está sempre salvo; o que pode mudar é apenas qual versão se está enxergando.

### sem aplicativos, só documentos

<img src="imagens/apenas_documentos.png" width="400" />

_o sistema é um espaço contínuo de texto onde comandos agem sobre seleção._

#### decisão
- o cofre é o sistema.
- um pedido a agente é documento: uma seção, uma nota, uma tarefa marcada, um bloco com contexto suficiente.
- uma resposta de agente também é documento: texto revisável, linkável, apagável, movível.
- a gravidade volta para o texto.

### CALC

<img src="imagens/CALC.png" width="400" />

_aplicação direta do princípio anterior. uma seleção contendo expressão matemática vira número no mesmo lugar com uma única tecla, sem janela auxiliar e sem mudança de contexto, porque ferramenta separada para calcular já é aplicativo distinto, contra a regra._

#### decisão
- transformações pequenas acontecem no próprio texto.
- quando um agente ou gancho calcula, resume, reescreve ou classifica, o resultado volta para o trecho ou nota de origem quando isso for o gesto mais simples.
- sem painel auxiliar, sem barra lateral obrigatória, sem conversa paralela quando o documento basta.

### habituação e visibilidade

<img src="imagens/habituacao_visibilidade.png" width="400" />

_bons gestos viram automáticos. o efeito de cada ação deve ser visível antes do gesto, e narrável depois._

#### decisão
- a documentação dos atalhos e convenções vive como nota do cofre, lida e editada como qualquer outra.
- cada agente registra o que fez em notas de log quando a ação precisa de memória.
- pedidos, respostas, erros e decisões devem ser narráveis por arquivos Markdown, não por arqueologia em estado oculto.
- auditar uma decisão é abrir uma nota.


## convenções

o ofício não exige muitos plugins. quanto menos peças entre a intenção e o texto, melhor. o Obsidian precisa abrir o cofre, salvar continuamente, sincronizar e permitir busca suficiente. todo o resto deve justificar sua existência.

agentes são convidados, não centros de comando. Codex pode cuidar de código, Pi pode conversar e amadurecer ideias, outros podem entrar depois. o contrato não muda: ler o cofre, reagir ao que foi pedido, escrever de volta quando houver algo útil a preservar.

sincronização é evento de trabalho. quando uma mudança chega ao cofre, um gancho pode identificar notas pendentes, tarefas marcadas ou blocos destinados a agentes e encaminhar a reação adequada. a arquitetura não depende de presença contínua diante da tela: uma nota escrita no celular deve poder virar trabalho no desktop, e uma resposta produzida depois deve voltar ao mesmo cofre.


## estado

versão 0.0.2. em uso pessoal, ainda em estado exploratório. as convenções estão estabilizando em torno de uma tese simples: Obsidian é a mesa, o cofre é a memória, agentes são mãos auxiliares. contribuições bem-vindas, com a ressalva de que este repositório existe para servir um modo de trabalhar, não para virar produto. antes de abrir chamado propondo recurso, pergunte se o recurso respeita um dos princípios acima. se ele existe para conforto de catálogo, provavelmente não vai entrar.


## licença

MIT.
