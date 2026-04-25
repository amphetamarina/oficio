# ofício

<img src="imagens/logo.png" width="600" />

`0.0.3 · experimental`

um ofício pede poucos instrumentos bem escolhidos e um único banco onde tudo está ao alcance da mão. este repositório contém um plugin Hermes que dá a agentes mãos explícitas para ler, escanear, marcar e escrever notas num cofre do Obsidian. não é catedral nem sistema operacional — é a oficina onde se trabalha bem.

## raiz

Jef Raskin passou a vida desenhando interfaces que respeitassem o tempo cognitivo de quem as usa (Swyft, Canon Cat, Archy). a tese cabe numa linha: **a interface deve minimizar o intervalo entre intenção e execução sem cobrar tributo de atenção.**

o ofício aplica essa tese a um cotidiano comum: quem escreve, lê e conversa com agentes ao longo do dia. o ponto de partida é um cofre do Obsidian, sincronizado, disponível no desktop e no celular, onde o texto vive antes, durante e depois da ação.

## arquitetura

<img src="imagens/arquitetura.png" width="900" />

três camadas, todas leves:

1. **cofre Obsidian** — fonte de verdade, espaço de escrita e leitura.
2. **plugin Hermes** — ferramentas que deixam o agente ler pedidos, escrever respostas e registrar ações no cofre.
3. **convenções de texto** — formato dos pedidos, logs e metadados.

não há painel separado, banco oculto nem caixa de entrada paralela. o que a usuária escreve no Obsidian é o que o agente vê. o que o agente produz volta ao Obsidian como nota, alteração ou log.

## princípios e decisões

cada princípio raskiniano vira decisão concreta de projeto. a ordem é a do impacto no corpo, não a da hierarquia.

### locus de atenção

<img src="imagens/locus_atencao.png" width="500" />

_a interface respeita o foco e nunca o arranca sem motivo._

> Obsidian é o ponto de partida. agentes não disputam foco: leem o cofre quando há pedido, escrevem de volta quando a resposta pertence ao trabalho. **nada pisca, nada interrompe. olha-se quando se quer.**

### sem modos

<img src="imagens/sem_modos.png" width="400" />

_a mesma tecla faz sempre a mesma coisa._

> o cofre fica o mais próximo possível de texto direto. pedidos são notas ou trechos de notas, não estados escondidos. a tabela de atalhos vive em `Hotkeys.md`.

### quasimodos

<img src="imagens/quasimodos.png" width="400" />

_estados que existem só enquanto a tecla está pressionada são aceitáveis._

> a invocação de agentes pode ser um gesto curto, mas o resultado vira texto no cofre. o estado termina com o gesto.

### monotonia

<img src="imagens/monotonia.png" width="400" />

_uma única maneira de fazer cada coisa._

> um cofre, uma fonte de verdade, um lugar para pedir trabalho: `agent/oficio/inbox.md`. agentes podem ser muitos; o protocolo é o mesmo.

### LEAP

<img src="imagens/LEAP.png" width="400" />

_busca incremental como navegação primária._

> a navegação é a busca nativa do Obsidian. bons nomes e links explícitos valem mais que indexadores pesados.

### desfazer universal

<img src="imagens/desfazer_universal.png" width="400" />

_toda ação é reversível. sem diálogos de confirmação._

> o desfazer é o do Obsidian. ações de agentes são registradas como texto no cofre — logs diários, metadados de conclusão e marcas de falha tornam tudo auditável.

### texto eterno

<img src="imagens/texto_eterno.png" width="400" />

_salvar e carregar são vestígios de disquete._

> autossave ligado, sync assumido. agentes escrevem no cofre; não mantêm verdade própria esperando exportação.

### sem aplicativos, só documentos

<img src="imagens/apenas_documentos.png" width="400" />

_o sistema é um espaço contínuo de texto._

> o cofre é o sistema. um pedido a agente é documento. uma resposta de agente também é. a gravidade volta para o texto.

### CALC

<img src="imagens/CALC.png" width="400" />

_aplicação direta do princípio anterior: uma seleção contendo expressão vira resultado no mesmo lugar com uma única tecla, sem janela auxiliar._

> transformações pequenas acontecem no próprio texto. quando um agente resume, calcula, reescreve ou classifica, o resultado volta ao trecho de origem. sem painel auxiliar, sem conversa paralela quando o documento basta. **(ainda não implementado — ver "o que ainda não existe")**

### habituação e visibilidade

<img src="imagens/habituacao_visibilidade.png" width="400" />

_bons gestos viram automáticos. o efeito de cada ação deve ser visível antes e narrável depois._

> documentação de atalhos e convenções vive como nota do cofre. logs diários registram o que cada agente fez. auditar uma decisão é abrir uma nota.

## o que existe hoje

o plugin Hermes `oficio` (~300 linhas) expõe oito ferramentas e um gancho de sessão.

### ferramentas

| ferramenta | o que faz |
|---|---|
| `oficio_scan` | encontra pedidos `- [ ] @hermes id:...` no inbox |
| `oficio_read` | lê qualquer nota do cofre |
| `oficio_append` | acrescenta texto a uma nota |
| `oficio_replace` | troca uma string exata por outra (seguro, sem regex) |
| `oficio_complete` | marca pedido como `[x]` e escreve entrada no log diário |
| `oficio_fail` | marca falha com erro e registra no log diário |
| `oficio_today` | mostra os caminhos de inbox e log do dia |
| `oficio_config_show` | mostra a configuração ativa |

### gancho de sessão

`on_session_start`: ao iniciar uma sessão, o plugin escaneia o inbox e informa o agente sobre pedidos pendentes — sem executar, sem marcar, sem escrever no cofre. o agente decide se oferece execução.

### formato dos pedidos

```markdown
- [ ] @hermes id:meu-pedido
  descreva o que o agente deve fazer.
```

### formato dos logs

logs diários vivem em `agent/oficio/log/daily/YYYY-MM-DD.md`. cada entrada é uma seção:

```markdown
## meu-pedido

- status: completed
- at: 2026-04-25T20:00:00-03:00
- source: agent/oficio/inbox.md

resultado ou erro registrado aqui.
```

### propriedades (novo em 0.0.3)

inbox e logs têm frontmatter YAML (compatível com Obsidian Properties):

```yaml
---
tags: [oficio/inbox]
type: inbox
---
```

```yaml
---
tags: [oficio/log]
type: log
date: 2026-04-25
---
```

### comandos slash

```
/oficio scan [path]
/oficio config
/oficio today
/oficio complete <id> <nota...>
/oficio fail <id> <erro...>
```

## o que ainda não existe

a lista abaixo registra o que os princípios pedem mas a implementação atual ainda não cobre. cada item é uma decisão pendente, não uma promessa.

- **sincronização como gatilho**: um gancho que reage a mudanças de sync e aciona o agente quando um novo pedido aparece. a arquitetura prevê isso, mas a versão atual depende de scan manual ou do gancho `on_session_start`.
- **watcher de filesystem**: escuta contínua do inbox. o lugar natural é um cron visível do Hermes, não um daemon oculto. ainda não implementado.
- **CALC / transformações inline**: selecionar texto no cofre, aplicar transformação (resumo, cálculo, reescrita) e ver o resultado no mesmo lugar. conceito documentado, implementação futura.
- **plugins auxiliares no Obsidian**: a filosofia prefere poucos plugins, mas templates, dataview ou quick-add podem reduzir atrito sem violar princípios. a decisão de quais entram ainda está aberta.
- **agentes múltiplos simultâneos**: o protocolo suporta múltiplos agentes (cada um com seu marcador), mas o plugin atual só escaneia `@hermes`. generalização futura.
- **inbox diário opcional**: a configuração prevê `use_daily_inbox`, mas o fluxo canônico usa um inbox único. a rota diária existe como possibilidade, não como padrão testado.

## uso

```bash
# clonar e linkar
git clone https://github.com/agentescognitivos/oficio ~/git/oficio
ln -s ~/git/oficio ~/.hermes/plugins/oficio
hermes plugins enable oficio

# testar
cd ~/git/oficio
nix shell nixpkgs#python312 nixpkgs#python312Packages.pytest -c sh -lc 'PYTHONPATH=. pytest -q'
```

fluxo real:

1. escreva no Obsidian, em `agent/oficio/inbox.md`:
   ```markdown
   - [ ] @hermes id:teste-001
     leia este pedido e registre uma confirmação no log diário.
   ```
2. no Hermes, use `/oficio scan` ou peça ao agente para escanear.
3. depois de executar, o agente chama `oficio_complete` (ou `oficio_fail` se der erro).
4. confira no Obsidian: a tarefa virou `[x]` e o log diário tem a entrada.

## estado

versão 0.0.3. em uso pessoal, ainda exploratório. as convenções estabilizam em torno de uma tese: **Obsidian é a mesa, o cofre é a memória, agentes são mãos auxiliares.** contribuições bem-vindas. antes de propor recurso, pergunte se ele respeita um dos princípios acima. se existe só para conforto de catálogo, provavelmente não vai entrar.

## licença

MIT.
