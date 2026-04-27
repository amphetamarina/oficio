# ofício

<p align="center">
  <img src="imagens/logo.png" alt="ofício" width="620">
</p>

<p align="center"><code>0.2.0 · experimental</code></p>

ofício is a calm interface between an Obsidian daily note and Hermes Agent.
It lets a markdown checkbox become a small cycle of attention: you write a
request where you are already working, Hermes processes it, and the answer
returns to the same note with status, session, and log links.

There is no separate inbox to remember, no dashboard to check, and no new place
for work to drift away. The vault remains the locus of attention.

The basic gesture is:

> `- [ ] @hermes <your request>`

## Why

ofício is for a quieter kind of automation. It keeps the agent inside the
texture of daily notes, where context, memory, and unfinished work already
live. A single repeated shape reduces monotony instead of adding another mode:
unchecked means open, checked means closed, and the trace stays visible.

It is designed around three simple constraints:

- **Local attention:** requests stay beside the work that caused them.
- **Visible state:** progress, completion, session ID, and log path are written inline.
- **Markdown first:** answers are plain markdown, nested under the request, so they remain editable and part of the note.

## Architecture

<p align="center">
  <img src="imagens/arquitetura.png" alt="Obsidian vault, Hermes plugin, and text conventions" width="840">
</p>

ofício has two parts:

- A Hermes plugin that exposes tools such as `oficio_scan`, `oficio_start`, and `oficio_complete`.
- A small Obsidian plugin that watches daily notes and starts Hermes when it sees a pending `@hermes` checkbox.

Hermes writes through the ofício tools. The Obsidian trigger only starts the
session; it does not edit your notes directly.

## Requirements

- Obsidian desktop
- Hermes Agent installed and available as `hermes`
- A daily note path shaped like `Daily/YYYY-MM-DD.md`

## Install

Clone the repository:

```bash
git clone https://codeberg.org/agentescognitivos/oficio ~/git/oficio
cd ~/git/oficio
```

Install the Hermes plugin:

```bash
mkdir -p ~/.hermes/plugins
ln -sfn ~/git/oficio ~/.hermes/plugins/oficio
hermes plugins enable oficio
```

Check that Hermes can see it:

```bash
hermes -z "/oficio config"
```

Install the Obsidian trigger plugin. Replace `/path/to/vault` with your vault
directory:

```bash
mkdir -p /path/to/vault/.obsidian/plugins
rm -rf /path/to/vault/.obsidian/plugins/oficio-trigger
ln -s ~/git/oficio/obsidian-plugin /path/to/vault/.obsidian/plugins/oficio-trigger
```

Then open Obsidian and enable **Ofício Trigger** in **Settings -> Community
plugins**.

## Use

Write an unchecked request in today's daily note:

```markdown
- [ ] @hermes summarize the notes from this meeting.
```

When Obsidian saves the note, the trigger starts Hermes. ofício adds an `id:`,
marks the request as in progress, then completes it in place:

```markdown
- [x] @hermes id:20260427-1 summarize the notes from this meeting.
  Status: completed - summary written | Session: 20260427_150511_4b969e | Log:
  /home/you/.hermes/sessions/session_20260427_150511_4b969e.json
  Agent response:
  ## Summary

  - The main decision was...
  - The next step is...
```

The exact response depends on the request, but it should stay as normal
markdown under `Agent response:`.

## Development

Developer notes, tools, slash commands, and tests live in
[DEVELOPMENT.md](DEVELOPMENT.md).

## License

MIT.
