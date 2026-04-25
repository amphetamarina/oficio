# ofício

<img src="imagens/logo.png" width="100" />

`python · 0.0.1 · experimental`

Um ofício pede poucos instrumentos bem escolhidos e um único banco onde tudo está ao alcance da mão. Este repositório reúne uma camada fina sobre Obsidian, um lançador minimalista, um pequeno despachante de agentes e um conjunto de convenções de teclado, todos derivados da Humane Interface de Jef Raskin. Não pretende ser catedral nem sistema operacional. É a oficina onde se trabalha bem.


## raiz

Jef Raskin iniciou o projeto Macintosh em 1979, foi vencido pela interface gráfica vitoriana que se seguiu, e passou os vinte e cinco anos seguintes desenhando interfaces que respeitassem o tempo cognitivo de quem as usa, em máquinas como Swyft, Canon Cat e o ambiente Archy. A tese dele cabe em uma linha. A interface deve minimizar o intervalo entre intenção e execução sem cobrar tributo de atenção. O ofício toma essa tese como projeto e a aplica a um cotidiano comum, de quem escreve, lê e conversa com agentes ao longo do dia, em qualquer Unix moderno, sem reescrever o sistema operacional.


## princípios

Cada princípio entra com a definição raskiniana e a decisão de projeto correspondente. A ordem é a do impacto sentido no corpo, não a da hierarquia teórica.

### locus de atenção

<img src="imagens/locus_atencao.png" width="300" />

A interface deve respeitar o ponto onde o cuidado está pousado e nunca arrancá-lo de lá sem motivo digno.

Decisão: Obsidian em tela cheia, no espaço de trabalho zero, sem barra de ícones lateral, com cromia reduzida. Notificações de sistema desligadas. O painel do gerenciador de janelas carrega só bateria, rede e relógio. Tudo o mais que a usuária queira saber (carga, fila dos agentes, estado do disco) entra como nota viva, lida via Dataview a partir de um YAML que um pequeno daemon atualiza a cada poucos segundos. Nada pisca, nada balança, nada interrompe. Olha-se quando se quer.

### sem modos

<img src="imagens/sem_modos.png" width="300" />

A mesma tecla deve sempre fazer a mesma coisa, em qualquer estado do sistema. Modos persistentes (Caps Lock, vim normal e insert, layouts ocultos) são bugs disfarçados de recurso.

Decisão: o modo Vim do Obsidian permanece desligado por padrão. Caps Lock vira Esc no nível do teclado, antes mesmo do compositor saber que ele existe; o que era a tecla mais ofensiva do teclado, um modo persistente esperando ser apertado por engano, vira gesto de cancelar, que é momentâneo por natureza. A tabela completa de atalhos vive em `Hotkeys.md` no cofre, gerada a partir da configuração real, para que a previsibilidade seja auditável e legível como o resto do trabalho.

### quasimodos

<img src="imagens/quasimodos.png" width="300" />

Estados que existem somente enquanto a tecla está pressionada são aceitáveis. O corpo sente fisicamente que está num estado especial, então o estado não fica esquecido em segundo plano.

Decisão: a invocação dos agentes acontece por quasimodo. Mantém-se um modificador, surge um campo de prompt, solta-se a tecla e o campo desaparece junto com o estado. Nenhum modo dura mais que o gesto que o sustenta.

### monotonia

<img src="imagens/monotonia.png" width="300" />

Uma única maneira de fazer cada coisa. Reduz ruído de escolha, fortalece habituação, devolve para o dia o tempo que múltiplos caminhos consomem.

Decisão: um lançador, uma paleta de comandos, um campo de busca, um caminho para invocar agente. Quando há tentação de oferecer "também por menu, também por clique", o ofício recusa. Caminho duplicado é caminho a manter.

### LEAP

<img src="imagens/LEAP.png" width="300" />

Busca incremental como navegação primária, no lugar da rolagem e do clique: duas teclas dedicadas levam o cursor a qualquer ponto de qualquer documento, sem mudança de janela e sem modo.

Decisão: três camadas concêntricas de busca, todas vivas e imediatas. Dentro do Obsidian, Omnisearch indexa o cofre inteiro com correspondência aproximada incremental, e a busca local nativa cobre o documento atual. No sistema, um lançador qualquer que respeite teclado e indexe arquivos abre notas via `obsidian://open?vault=...&file=...`. Sobre links visíveis, Jump to Link expõe marcadores de atalho em quasimodo, no espírito do que o vimium fez para a web. Em qualquer ponto do ofício, três a cinco teclas chegam ao destino.

### desfazer universal

<img src="imagens/desfazer_universal.png" width="300" />

Toda ação é reversível. Nenhum diálogo modal pedindo confirmação.

Decisão: o cofre inteiro vive sob jj, escolhido por tratar o desfazer como cidadão de primeira classe. A cópia de trabalho é versionada a cada operação, e o log de operações preserva não apenas o conteúdo dos arquivos como também os movimentos do próprio sistema de versão; `jj undo` reverte o último movimento, qualquer que tenha sido. `oficio undo` é uma camada fina sobre `jj op log` que apresenta as operações recentes no lançador para reversão interativa. O sistema confia que a usuária vai querer desfazer, então não pergunta antes.

### texto eterno

<img src="imagens/texto_eterno.png" width="300" />

Salvar e Carregar são vestígios de disquete. O documento existe e persiste sempre.

Decisão: o autossave do Obsidian permanece ligado, os agentes escrevem direto em arquivos do cofre sem buffer próprio, e o jj acima fecha o ciclo. Em nenhum lugar há "deseja salvar antes de sair?". O texto está sempre salvo; o que pode mudar é apenas qual versão se está enxergando.

### sem aplicativos, só documentos

<img src="imagens/apenas_documentos.png" width="300" />

O sistema é um espaço contínuo de texto onde comandos agem sobre seleção.

Decisão: o cofre é o sistema. Ferramentas externas (terminal, navegador) entram em modo retrátil, fazem o que precisam fazer e somem sem ocupar tela. xfwm4, sway, kwin e Hyprland em Linux ou BSD, yabai ou o próprio Aqua em macOS, qualquer compositor decente faz o trabalho com uma única regra: Obsidian sempre maximizado, retráteis sempre voláteis. A gravidade volta para o texto.

### CALC

<img src="imagens/CALC.png" width="300" />

Aplicação direta do princípio anterior. Uma seleção contendo expressão matemática vira número no mesmo lugar com uma única tecla, sem janela auxiliar e sem mudança de contexto, porque ferramenta separada para calcular já é aplicativo distinto, contra a regra.

Decisão: um pequeno script de usuária (Templater no Obsidian, ou gancho de shell no editor de escolha) recebe a seleção, manda para uma calculadora simbólica (qalc é um bom padrão) e troca o trecho pelo resultado. Cobre matemática, conversões de unidade e datas. Sem painel auxiliar, sem barra lateral.

### habituação e visibilidade

<img src="imagens/habituacao_visibilidade.png" width="300" />

Bons gestos viram automáticos. O efeito de cada ação deve ser visível antes do gesto, e narrável depois.

Decisão: a documentação dos atalhos não vive em interface gráfica escondida, vive como nota do cofre, lida e editada como qualquer outra. Cada agente registra o que fez num `entrada.md` datado. O sistema é narrável de cima a baixo, e auditar uma decisão é abrir um arquivo, não arqueologia em log binário.


## arquitetura

Quatro peças, todas leves. Obsidian como espaço de trabalho persistente, único processo gráfico que importa. Um lançador minimalista para LEAP de sistema, escolhido pela usuária. Um despachante de agentes em Python que recebe prompts via socket Unix, roteia por prefixo (`/code`, `/pesquisa`, `/livre`) para qualquer agente externo configurável, escreve respostas em arquivos do cofre, e mantém o snapshot do cofre em jj via um monitor de arquivos. E um conjunto de convenções de teclado mais alguns plugins do Obsidian (Omnisearch, Templater, Dataview, Jump to Link) que costuram o resto. O cofre permanece a única fonte de verdade. Os agentes não abrem janelas próprias, não pedem permissão por janela flutuante, não disputam foco.


## requisitos

Qualquer Unix moderno: macOS, Linux, FreeBSD, OpenBSD. Um gerenciador de janelas que aceite atalhos globais (XFCE, KDE, GNOME, sway, Hyprland, i3 em Linux ou BSD; yabai com skhd ou o próprio Aqua em macOS). Obsidian. jj. Um lançador minimalista que respeite teclado (rofi, tofi, wofi, anyrun em Linux ou BSD; Raycast ou Alfred em macOS; fzf em terminal serve em qualquer Unix). Um terminal com aparição e sumiço por atalho (foot, kitty ou alacritty mais tdrop em X11; scratchpad de sway no Wayland; janela de atalho do iTerm2 ou Hammerspoon em macOS). Python 3.11 ou superior para o despachante. fswatch para o snapshot contínuo. Caps Lock remapeado para Esc no nível do teclado, via xkb em Linux ou BSD, via Karabiner-Elements em macOS. Roda em hardware antigo sem reclamar.


## estado

Versão 0.0.1. Em uso pessoal, ainda em estado exploratório. As convenções estão estabilizadas; o despachante de agentes está em forma cedo. Contribuições bem-vindas, com a ressalva de que este repositório existe para servir um modo de trabalhar, não para virar produto. Antes de abrir chamado propondo recurso, pergunte se o recurso respeita um dos princípios acima. Se ele existe para conforto de catálogo, provavelmente não vai entrar.


## licença

MIT.