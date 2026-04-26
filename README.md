# ofício

<img src="imagens/logo.png" width="600" />

`0.2.0 · experimental`

an ofício asks for few well-chosen instruments and a single bench where everything is within reach. this repository holds a Hermes plugin that gives agents explicit hands to read, scan, mark, and write notes inside an Obsidian vault. it is not a cathedral nor an operating system — it is the workshop where work gets done well.

## root

Jef Raskin spent his life designing interfaces that respect the user's cognitive time (Swyft, Canon Cat, Archy). the thesis fits in one line: **the interface should minimize the gap between intention and execution without charging an attention tax.**

ofício applies that thesis to a common daily rhythm: someone who writes, reads, and talks to agents throughout the day. the starting point is an Obsidian vault — synced, available on desktop and phone — where text lives before, during, and after action.

## architecture

<img src="imagens/arquitetura.png" width="900" />

three layers, all lightweight:

1. **Obsidian vault** — source of truth, space for reading and writing.
2. **Hermes plugin** — tools that let the agent read requests, write responses, and record actions in the vault.
3. **text conventions** — format for requests and inline metadata.

there is no separate dashboard, hidden database, parallel inbox, or log folder. what the user writes in their Obsidian daily note is what the agent sees. what the agent produces returns to that same daily note as inline status. Hermes sessions are the logs — inspectable via `session_search`.

## principles and decisions

every principle becomes a concrete project decision. the order follows impact on the body, not hierarchy.

### locus of attention

<img src="imagens/locus_atencao.png" width="500" />

_the interface respects focus and never yanks it without reason._

> Obsidian is the starting point. agents do not compete for focus: they read the daily note when there is a request, write the status back into the same note. **nothing blinks, nothing interrupts. you look when you want.**

### monotony

<img src="imagens/monotonia.png" width="400" />

_a single way to do each thing._

> one vault, one source of truth, one place to ask for work: the daily note of the day (`Daily/YYYY-MM-DD.md`). agents can be many; the protocol is the same.

### habituation and visibility

<img src="imagens/habituacao_visibilidade.png" width="400" />

_good gestures become automatic. the effect of every action must be visible before and narratable after._

> every `@hermes` request in the daily note gets a `Status:` line inline. glancing at the daily note is seeing what was done and what is pending. auditing a decision is opening the day's note or using `session_search` in Hermes.

### no apps, only documents

<img src="imagens/apenas_documentos.png" width="400" />

_the system is a continuous space of text._

> the vault is the system. a request to an agent is a document. an agent's response is also a document — inline in the daily note. gravity returns to text.

## what exists today

the Hermes plugin `oficio` exposes eight tools, a session hook, and a slash command.

### tools

| tool | what it does |
|---|---|
| `oficio_scan` | finds `- [ ] @hermes ...` requests in the daily note |
| `oficio_read` | reads any note in the vault |
| `oficio_start` | marks a request as `Status: in progress` without changing the checkbox |
| `oficio_complete` | marks request as `[x]` and writes `Status: completed` inline |
| `oficio_fail` | marks request as `[x]` and writes `Status: failed` inline |
| `oficio_replace` | swaps one exact string for another (safe, no regex) |
| `oficio_today` | shows the path to today's daily note |
| `oficio_config_show` | shows the active configuration |

### session hook

`on_session_start`: when a session starts, the plugin scans the daily note and informs the agent about pending requests — without executing, without marking, without writing to the vault.

### where to write requests

the daily note is the only place. write `- [ ] @hermes` directly in your daily:

```markdown
- [ ] @hermes describe what the agent should do.
```

### request format

```markdown
- [ ] @hermes describe what the agent should do.
```

the `id:` is optional. if omitted in hand-written requests inside Obsidian, the scan generates an auto-ID in the format `YYYYMMDD-N` for temporary reference.

```markdown
- [ ] @hermes id:my-request
  describe what the agent should do.
```

### inline status

every `@hermes` request in the daily note gains a `Status:` line right below it. the agent updates this status directly:

```markdown
- [ ] @hermes id:my-request
  Status: in progress | Session: 20260426_164315_8da571
  request description.
```

```markdown
- [x] @hermes id:my-request
  Status: completed - summary of what was done | Session: 20260426_164315_8da571
  request description.
```

```markdown
- [x] @hermes id:another-request
  Status: failed - reason for failure | Session: 20260426_164315_8da571
  request description.
```

### sessions

Hermes sessions are the logs. use `session_search` to inspect execution history. there is no separate log folder — each Hermes session already records what was done. the session ID is embedded in the `Status:` line for traceability.

### Obsidian plugin

the repository includes an Obsidian plugin at `obsidian-plugin/` that watches daily note modifications (with a 5-minute debounce) and automatically triggers a Hermes session when it finds `- [ ] @hermes` without a `Status:` line. the plugin does not write to the vault — it only spawns Hermes. the agent sets `in progress` status via `oficio_start` when it begins work.

to install:

```bash
cp -r ~/git/oficio/obsidian-plugin ~/Documents/amphetamarina/.obsidian/plugins/oficio-trigger/
```

and enable "Ofício Trigger" in Settings → Community plugins.

### quick template

to insert an `@hermes` block with a shortcut in Obsidian, use the `hermes-request` template (in `Templates/`). with the Templates plugin enabled:

1. place the cursor where you want the request.
2. `Cmd/Ctrl+T` → choose `hermes-request`.
3. fill in the id and description.

### slash commands

```
/oficio scan [path]
/oficio config
/oficio today
/oficio start <id> [line]
/oficio complete <id> <note...>
/oficio fail <id> <error...>
```

## usage

```bash
# clone and link
git clone https://codeberg.org/agentescognitivos/oficio ~/git/oficio
ln -s ~/git/oficio ~/.hermes/plugins/oficio
hermes plugins enable oficio

# test
cd ~/git/oficio
nix shell nixpkgs#python312 nixpkgs#python312Packages.pytest -c sh -lc 'PYTHONPATH=. pytest -q'
```

real workflow:

1. write a request in the daily note.
2. in Hermes, use `/oficio scan` or ask the agent to scan.
3. the agent calls `oficio_start` when it begins working (sets `Status: in progress`).
4. after executing, the agent calls `oficio_complete` (or `oficio_fail`).
5. check Obsidian: the task is `[x]` with `Status:` inline.

## state

version 0.2.0. in personal use, still exploratory. the daily note is the starting point and the destination. status lives inline. Hermes sessions are the logs. **Obsidian is the desk, the vault is the memory, agents are helping hands.** contributions welcome. before proposing a feature, ask whether it respects one of the principles above. if it exists only for catalog comfort, it probably won't go in.

## license

MIT.
