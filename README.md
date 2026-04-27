# ofício

<p align="center">
  <img src="imagens/logo.png" alt="ofício" width="620">
</p>

<p align="center"><code>0.2.0 · experimental</code></p>

ofício connects an Obsidian vault to Hermes. You write one checkbox task in
today's daily note, Obsidian sees it, Hermes runs, and the result returns to the
same note.

The only request syntax you need is `- [ ] @hermes <some message>`.

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

Check that Hermes can see it:

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
**Settings -> Community plugins**.

The Obsidian plugin needs `hermes` on your desktop `PATH`. It watches daily
notes at `Daily/YYYY-MM-DD.md`.

### 4. ask from your daily note

In today's daily note, add one task line:

> `- [ ] @hermes write the weekly project summary from the notes in this vault.`

Obsidian starts Hermes automatically. The trigger only starts the session; it
does not edit the vault itself.

When Hermes starts work, ofício adds an `id:`, keeps the checkbox open, and
writes `Status: in progress` under the task. When Hermes finishes, it checks the
box and changes the status to `completed` or `failed`.

The status line also contains:

| field | meaning |
|---|---|
| `Session:` | the real Hermes session ID |
| `Log:` | a link to `~/.hermes/sessions/session_<id>.json` |

Unless the request asks for another format, the final answer is written below
the task under `Agent response:`.

## three concepts

### 1. the vault is the workspace

<p align="center">
  <img src="imagens/arquitetura.png" alt="Obsidian vault, Hermes plugin, and text conventions" width="840">
</p>

Your Obsidian vault is the source of truth. Requests, context, results, and
status all live in markdown files you already read and edit.

There is no dashboard, hidden database, parallel inbox, or ofício-owned log
folder. Hermes owns session transcripts in `~/.hermes/sessions/`.

### 2. a checkbox is the command surface

<p align="center">
  <img src="imagens/monotonia.png" alt="One repeated request shape" width="420">
</p>

The command surface is one markdown shape: `- [ ] @hermes <some message>`.

Use it directly in the daily note. The Obsidian plugin watches for unchecked
`@hermes` tasks without a `Status:` line and starts a Hermes session.

### 3. status stays inline

<p align="center">
  <img src="imagens/habituacao_visibilidade.png" alt="Visible inline status" width="420">
</p>

Every request gets its status directly under the checkbox. The daily note is the
place to ask, inspect progress, read the answer, and find the Hermes transcript.

## what exists today

The Hermes plugin exposes these tools:

| tool | what it does |
|---|---|
| `oficio_scan` | finds pending `@hermes` requests in the daily note |
| `oficio_read` | reads any note in the vault |
| `oficio_start` | writes `Status: in progress` without changing the checkbox |
| `oficio_complete` | checks the box, writes `Status: completed`, and can add `Agent response:` |
| `oficio_fail` | checks the box and writes `Status: failed` |
| `oficio_replace` | replaces one exact string in one note |
| `oficio_today` | shows today's daily note path |
| `oficio_config_show` | shows the active configuration |

Slash commands:

| command | purpose |
|---|---|
| `/oficio scan [path]` | scan for pending requests |
| `/oficio config` | show configuration |
| `/oficio today` | show today's daily note path |
| `/oficio start <id> [line]` | mark a request in progress |
| `/oficio complete <id> <note...>` | mark a request complete |
| `/oficio fail <id> <error...>` | mark a request failed |

There is no session-start hook. Automatic execution belongs to the Obsidian
trigger plugin.

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
