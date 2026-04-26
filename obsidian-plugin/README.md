# Ofício Trigger — Obsidian Plugin

Watches vault modifications and automatically triggers Hermes agent sessions
when a daily note or the ofício inbox is modified and contains unchecked
`@hermes` requests without a Status line.

## How it works

1. Listens to `vault.on('modify')` events
2. Filters for daily notes (`Daily/YYYY-MM-DD.md`) and the ofício inbox
3. 5-minute debounce: won't trigger more than once per 5 minutes per file
4. 2-second debounce: waits for rapid successive saves to settle
5. Checks content for unchecked `- [ ] @hermes` without `Status:` line
6. Spawns `hermes -z "Scan the ofício vault..." --yolo --accept-hooks`

## Installation

```bash
# From the ofício repo
cp -r obsidian-plugin/ ~/Documents/amphetamarina/.obsidian/plugins/oficio-trigger/

# Or symlink
ln -s ~/git/oficio/obsidian-plugin ~/Documents/amphetamarina/.obsidian/plugins/oficio-trigger
```

Then enable "Ofício Trigger" in Obsidian → Settings → Community plugins.

## Requirements

- Obsidian desktop (uses `child_process.spawn`)
- `hermes` on PATH

## Architecture

```
obsidian-plugin/
├── manifest.json    # Obsidian plugin manifest
├── main.js          # Plugin code
└── README.md        # This file
```

The plugin lives in the ofício repo (`~/git/oficio/obsidian-plugin/`) and is
copied or symlinked into the Obsidian vault's plugins directory.

The plugin source should stay in the repo; the vault copy is just the
deployment target.
