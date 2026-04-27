# Ofício Trigger — Obsidian Plugin

Watches vault modifications and automatically triggers Hermes agent sessions
when a daily note contains unchecked `@hermes` requests without a Status line.

## How it works

1. Listens to `vault.on('modify')` events
2. Filters for daily notes (`Daily/YYYY-MM-DD.md`)
3. 5-minute debounce: won't trigger more than once per 5 minutes per file
4. 2-second debounce: waits for rapid successive saves to settle
5. Checks content for unchecked `- [ ] @hermes` without `Status:` line
6. Spawns `hermes chat -q ... --pass-session-id --source obsidian`

The trigger does not write to the vault. Hermes writes status and responses
through the ofício tools. Because the trigger uses `--pass-session-id`, the
agent can pass the real Hermes session ID to `oficio_start` and
`oficio_complete`, which makes the inline `Log:` link point at
`~/.hermes/sessions/session_<id>.json`.

## Installation

```bash
# From the ofício repo
rm -rf ~/Documents/amphetamarina/.obsidian/plugins/oficio-trigger
cp -r obsidian-plugin/ ~/Documents/amphetamarina/.obsidian/plugins/oficio-trigger

# Or symlink (replaces any existing copy)
rm -rf ~/Documents/amphetamarina/.obsidian/plugins/oficio-trigger
ln -s ~/git/oficio/obsidian-plugin ~/Documents/amphetamarina/.obsidian/plugins/oficio-trigger
```

Then enable "Ofício Trigger" in Obsidian → Settings → Community plugins.

## Requirements

- Obsidian desktop (uses `child_process.spawn`)
- `hermes` on PATH

## Architecture

```
obsidian-plugin/
├── manifest.json   # Obsidian plugin manifest
├── main.js         # Plugin logic (scanner + runner + lifecycle)
└── README.md       # This file
```

The plugin lives in the ofício repo (`~/git/oficio/obsidian-plugin/`) and is
copied or symlinked into the Obsidian vault's plugins directory.

The plugin source should stay in the repo; the vault copy is just the
deployment target.
