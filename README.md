# ofício

<p align="center">
  <img src="imagens/logo.png" alt="ofício" width="620">
</p>

<p align="center"><code>0.2.0 · experimental</code></p>

ofício connects an Obsidian vault to Hermes. You write a normal markdown task in
your daily note, Obsidian notices it, Hermes runs, and the answer comes back to
the same note as inline status.

```markdown
- [ ] @hermes summarize yesterday's meeting notes and draft follow-ups.
```

That is the interface. No dashboard, no inbox to check, no separate workflow to
learn.

## getting started

### 1. clone the repository

```bash
git clone https://codeberg.org/agentescognitivos/oficio ~/git/oficio
cd ~/git/oficio
```

### 2. install the Hermes plugin

```bash
mkdir -p ~/.hermes/plugins
ln -s ~/git/oficio ~/.hermes/plugins/oficio
hermes plugins enable oficio
```

To verify the plugin:

```bash
hermes -z "/oficio config"
```

### 3. install the Obsidian plugin

Replace `~/Documents/my-vault` with the path to your Obsidian vault:

```bash
mkdir -p ~/Documents/my-vault/.obsidian/plugins
ln -s ~/git/oficio/obsidian-plugin ~/Documents/my-vault/.obsidian/plugins/oficio-trigger
```

Then open Obsidian and enable **Ofício Trigger** in
**Settings → Community plugins**.

The Obsidian plugin needs the `hermes` command available on your desktop
`PATH`. It watches daily notes at `Daily/YYYY-MM-DD.md`.

### 4. ask for work from your daily note

In today's daily note, write:

```markdown
- [ ] @hermes write the weekly project summary from the notes in this vault.
```

Obsidian picks it up automatically. The trigger plugin only starts Hermes; it
does not edit your vault. Hermes writes the status through the ofício tools when
it starts and finishes:

```markdown
- [ ] @hermes id:20260427-1 write the weekly project summary from the notes in this vault.
  Status: in progress | Session: 20260427_091500_8da571 | Log: [/home/you/.hermes/sessions/session_20260427_091500_8da571.json](file:///home/you/.hermes/sessions/session_20260427_091500_8da571.json)
```

```markdown
- [x] @hermes id:20260427-1 write the weekly project summary from the notes in this vault.
  Status: completed - drafted the weekly summary | Session: 20260427_091500_8da571 | Log: [/home/you/.hermes/sessions/session_20260427_091500_8da571.json](file:///home/you/.hermes/sessions/session_20260427_091500_8da571.json)
  Agent response:
  ````markdown
  Drafted the weekly summary and added follow-up bullets.
  ````
```

`id:` is optional. If you omit it, ofício generates one when the request is
scanned.

## three concepts

### 1. the vault is the workspace

<p align="center">
  <img src="imagens/arquitetura.png" alt="Obsidian vault, Hermes plugin, and text conventions" width="840">
</p>

Your Obsidian vault is the source of truth. Requests, context, results, and
status all live in markdown files you already read and edit.

There is no separate dashboard, hidden database, parallel inbox, or ofício log
folder. Hermes sessions remain available in `~/.hermes/sessions/`, and each
status line links to the matching session transcript.

### 2. a checkbox is the command surface

<p align="center">
  <img src="imagens/monotonia.png" alt="One repeated request shape" width="420">
</p>

The command surface is one markdown shape:

```markdown
- [ ] @hermes <some message>
```

Use it directly in the daily note. The Obsidian plugin watches for unchecked
`@hermes` tasks without a `Status:` line and starts a Hermes session.

### 3. status stays inline

<p align="center">
  <img src="imagens/habituacao_visibilidade.png" alt="Visible inline status" width="420">
</p>

Every request gets a `Status:` line under it. While the agent works, the checkbox
stays open and the status says `in progress`. When the task finishes, the
checkbox is checked and the status says `completed` or `failed`. Obsidian
sessions launched by the trigger pass the real Hermes session ID to the agent,
so `Session:` and `Log:` point at the same transcript Hermes stores.

Unless the request says otherwise, the final answer is written back under the
request as an `Agent response` code block. That makes the daily note both the
place to ask and the place to audit.

## what exists today

The Hermes plugin exposes these tools:

| tool | what it does |
|---|---|
| `oficio_scan` | finds `- [ ] @hermes ...` requests in the daily note |
| `oficio_read` | reads any note in the vault |
| `oficio_start` | marks a request as `Status: in progress` without changing the checkbox, with optional Hermes `session_id` |
| `oficio_complete` | marks request as `[x]`, writes `Status: completed`, and can add an `Agent response` block |
| `oficio_fail` | marks request as `[x]` and writes `Status: failed` inline |
| `oficio_replace` | swaps one exact string for another, with no regex |
| `oficio_today` | shows the path to today's daily note |
| `oficio_config_show` | shows the active configuration |

It also provides:

- `on_session_start`, which scans the daily note and tells the agent about
  pending requests without executing them.
- slash commands:

```text
/oficio scan [path]
/oficio config
/oficio today
/oficio start <id> [line]
/oficio complete <id> <note...>
/oficio fail <id> <error...>
```

## development

```bash
nix shell nixpkgs#python312 nixpkgs#python312Packages.pytest -c sh -lc 'PYTHONPATH=. pytest -q'
```

## state

Version 0.2.0. In personal use, still exploratory. The daily note is the
starting point and the destination; status lives inline; Hermes sessions are the
logs.

## license

MIT.
