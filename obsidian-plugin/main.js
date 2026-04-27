const { Plugin, Notice } = require('obsidian');
const { spawn } = require('child_process');

const DEBOUNCE_MS = 5 * 60 * 1000; // 5 minutes
const SETTLE_MS = 2000;

module.exports = class OficioTriggerPlugin extends Plugin {
    async onload() {
        this.lastTrigger = {};
        this.pendingCheck = null;

        console.log('Ofício Trigger: loaded, watching vault modifications');

        this.registerEvent(
            this.app.vault.on('modify', (file) => {
                this._onFileModified(file);
            })
        );
    }

    onunload() {
        console.log('Ofício Trigger: unloaded');
        if (this.pendingCheck) {
            clearTimeout(this.pendingCheck);
        }
    }

    async _onFileModified(file) {
        // Only watch daily notes.
        const dailyFolder = 'Daily';
        const filePath = file.path;

        const isDaily = filePath.startsWith(dailyFolder + '/') && filePath.endsWith('.md');
        if (!isDaily) {
            return;
        }

        // 5-minute debounce per file
        const now = Date.now();
        const last = this.lastTrigger[filePath] || 0;
        if (now - last < DEBOUNCE_MS) {
            console.log(`Ofício Trigger: debounced ${filePath} (${Math.round((now - last) / 1000)}s since last trigger)`);
            return;
        }

        // Debounce rapid successive saves: wait 2s after last modify
        if (this.pendingCheck) {
            clearTimeout(this.pendingCheck);
        }

        this.pendingCheck = setTimeout(async () => {
            this.pendingCheck = null;
            await this._checkAndTrigger(file);
        }, SETTLE_MS);
    }

    async _checkAndTrigger(file) {
        const filePath = file.path;
        console.log(`Ofício Trigger: checking ${filePath}`);

        try {
            const content = await this.app.vault.read(file);

            // Check for unchecked @hermes without Status
            const hasPending = this._hasPendingWithoutStatus(content);

            if (hasPending) {
                this.lastTrigger[filePath] = Date.now();
                console.log(`Ofício Trigger: pending @hermes found in ${filePath}, triggering Hermes`);
                this._triggerHermes(filePath);
            } else {
                console.log(`Ofício Trigger: no pending @hermes in ${filePath}`);
            }
        } catch (err) {
            console.error(`Ofício Trigger: error reading ${filePath}:`, err);
        }
    }

    _hasPendingWithoutStatus(content) {
        const lines = content.split('\n');

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            // Standard format: - [ ] @hermes ...
            if (/^\s*-\s*\[\s*\]\s+.*@hermes\b/.test(line)) {
                if (!this._hasStatusInBlock(lines, i)) {
                    return true;
                }
                continue;
            }

            // Split-line format: @hermes ... on a standalone line followed by - [ ]
            if (/@hermes\b/.test(line) && !/^\s*-\s*\[/.test(line)) {
                // Find the next - [ ] line
                let j = i + 1;
                while (j < lines.length && !lines[j].trim()) {
                    j++;
                }
                if (j < lines.length && /^\s*-\s*\[\s*\]/.test(lines[j]) && !/@hermes/.test(lines[j])) {
                    if (!this._hasStatusInBlock(lines, j)) {
                        return true;
                    }
                }
            }
        }

        return false;
    }

    _hasStatusInBlock(lines, startIdx) {
        // Check within the next 15 lines for a Status: line
        const limit = Math.min(lines.length, startIdx + 15);
        for (let i = startIdx + 1; i < limit; i++) {
            if (/^\s*Status:/.test(lines[i])) {
                return true;
            }
            // Stop at next checkbox (end of block)
            if (/^\s*-\s*\[/.test(lines[i])) {
                return false;
            }
            // Stop at non-indented, non-heading, non-empty lines
            const line = lines[i];
            if (line && !/^\s/.test(line) && !/^#/.test(line)) {
                return false;
            }
        }
        return false;
    }

    _triggerHermes(filePath) {
        const vaultPath = this.app.vault.adapter.getBasePath();
        const prompt = [
            `Scan the ofício vault for pending @hermes requests in ${filePath} and process them.`,
            '',
            'Use the oficio tools. When you start a request, call oficio_start with the current Hermes Session ID from your system prompt.',
            'When you finish, call oficio_complete or oficio_fail with that same session_id.',
            'Unless the request explicitly asks for a different format, write the final answer back to the daily note through oficio_complete.response.',
            'The response should be concise markdown. oficio_complete will place it under the request as an Agent response code block.',
            'Do not create a separate log file; the Hermes transcript is the session log.'
        ].join('\n');

        const args = [
            'chat',
            '-q',
            prompt,
            '--quiet',
            '--pass-session-id',
            '--source',
            'obsidian',
            '--yolo',
            '--accept-hooks'
        ];

        const writeLog = (message) => {
            const line = `[${new Date().toISOString()}] ${message}\n`;
            log.write(line);
            console.log(`Ofício Trigger: ${message}`);
        };

        writeLog(`starting Hermes: hermes ${args.map((arg) => JSON.stringify(arg)).join(' ')}`);

        const child = spawn('hermes', args, {
            cwd: vaultPath,
            stdio: ['ignore', 'pipe', 'pipe'],
            env: { ...process.env },
        });

        writeLog(`Hermes spawned (pid ${child.pid}) for ${filePath}`);
        new Notice(`Ofício: Hermes started for ${filePath}`);

        child.stdout.on('data', (data) => {
            console.log(`Ofício Trigger stdout: ${data.toString().trimEnd()}`);
        });

        child.stderr.on('data', (data) => {
            console.error(`Ofício Trigger stderr: ${data.toString().trimEnd()}`);
        });

        child.on('error', (err) => {
            writeLog(`failed to spawn Hermes: ${err.message}`);
            new Notice(`Ofício: failed to spawn Hermes — ${err.message}`, 10000);
        });

        child.on('close', (code, signal) => {
            const ok = code === 0;
            const result = ok
                ? `Hermes completed successfully for ${filePath}`
                : `Hermes failed for ${filePath} (exit ${code}${signal ? `, signal ${signal}` : ''})`;
            writeLog(result);

            if (ok) {
                new Notice(`Ofício: Hermes completed for ${filePath}`, 8000);
            } else {
                new Notice(`Ofício: Hermes failed for ${filePath}`, 15000);
            }
        });
    }
};
