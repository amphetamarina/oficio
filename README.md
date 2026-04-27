# ofício

<p align="center">
  <img src="imagens/logo.png" alt="ofício" width="620">
</p>

<p align="center"><code>0.2.0 · experimental</code></p>

ofício is a small cybernetic loop between an Obsidian daily note and Hermes.
You write a checkbox. The agent answers in the same place. The vault stays the
body, the memory, and the record.

The whole interface is:

> `- [ ] @hermes <some message>`

## requirements

[Obsidian](https://obsidian.md/) is the markdown vault. It gives ofício a daily
note to watch and a visible place to return status, answers, and links.

[Hermes Agent](https://hermes-agent.org/) is the agent runtime. It reads the
request, uses the ofício tools, and stores the session transcript under
`~/.hermes/sessions/`.

ofício is the bridge: a Hermes plugin plus a tiny Obsidian trigger plugin.

## getting started

### 1. clone

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

Replace `~/Documents/my-vault` with your vault path:

```bash
mkdir -p ~/Documents/my-vault/.obsidian/plugins
ln -s ~/git/oficio/obsidian-plugin ~/Documents/my-vault/.obsidian/plugins/oficio-trigger
```

Open Obsidian and enable **Ofício Trigger** in
**Settings -> Community plugins**.

The trigger expects `hermes` on your desktop `PATH`. It watches
`Daily/YYYY-MM-DD.md`.

### 4. ask

In today's daily note:

> `- [ ] @hermes write the weekly project summary from this vault.`

Obsidian notices the unchecked `@hermes` task and starts Hermes. ofício then
adds an `id:`, writes `Status: in progress`, and links the real Hermes session
log. When the agent finishes, it checks the box and writes the response below
the request.

## three concepts

### 1. the vault is the body

<p align="center">
  <img src="imagens/arquitetura.png" alt="Obsidian vault, Hermes plugin, and text conventions" width="840">
</p>

Requests, context, status, answers, and memory live in markdown. There is no
dashboard and no second inbox.

### 2. the checkbox is the signal

<p align="center">
  <img src="imagens/monotonia.png" alt="One repeated request shape" width="420">
</p>

One shape is enough: `- [ ] @hermes <some message>`. A checked box means the
cycle closed.

### 3. the trace stays visible

<p align="center">
  <img src="imagens/habituacao_visibilidade.png" alt="Visible inline status" width="420">
</p>

Each request keeps its status inline. `Session:` is the Hermes session ID.
`Log:` points to `~/.hermes/sessions/session_<id>.json`.

## development

Developer notes, tools, slash commands, and tests live in
[DEVELOPMENT.md](DEVELOPMENT.md).

## license

MIT.
