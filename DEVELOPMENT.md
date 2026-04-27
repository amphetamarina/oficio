# development

This file is for the moving parts. The README is only the front door.

## Hermes tools

| tool | what it does |
|---|---|
| `oficio_scan` | finds pending `@hermes` requests in the daily note |
| `oficio_read` | reads a vault note |
| `oficio_start` | writes `Status: in progress` without checking the box |
| `oficio_complete` | checks the box, writes `Status: completed`, and can add `Agent response:` |
| `oficio_fail` | checks the box and writes `Status: failed` |
| `oficio_replace` | replaces one exact string in one note |
| `oficio_today` | shows today's daily note path |
| `oficio_config_show` | shows the active configuration |

## slash command

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

## Obsidian trigger

The Obsidian plugin watches daily notes at `Daily/YYYY-MM-DD.md`. When it sees
an unchecked `@hermes` task without a `Status:` line, it starts:

```bash
hermes chat -q <prompt> --pass-session-id --source obsidian --yolo --accept-hooks
```

The trigger does not edit the vault. Hermes edits through the ofício tools, so
the session ID in the note matches the Hermes session log.

## tests

```bash
PYTHONPATH=. pytest -q
```
