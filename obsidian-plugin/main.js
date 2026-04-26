const { Plugin, moment } = require('obsidian');
const { spawn } = require('child_process');
const path = require('path');

const DEBOUNCE_MS = 5 * 60 * 1000; // 5 minutes

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
        // Only watch daily notes and oficio inbox
        const dailyFolder = 'Daily';
        const inboxPath = 'agent/oficio/inbox.md';
        const filePath = file.path;

        const isDaily = filePath.startsWith(dailyFolder + '/') && filePath.endsWith('.md');
        const isInbox = filePath === inboxPath;

        if (!isDaily && !isInbox) {
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
        }, 2000);
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
        const scriptPath = path.join(
            this.app.vault.adapter.getBasePath(),
            'agent', 'oficio', 'bin', 'check-and-run-hermes'
        );

        const child = spawn('hermes', [
            '-z',
            `Scan the ofício vault for pending @hermes requests in ${filePath} and process them.`,
            '--yolo',
            '--accept-hooks'
        ], {
            detached: true,
            stdio: 'ignore',
            env: { ...process.env },
        });

        child.on('error', (err) => {
            console.error('Ofício Trigger: failed to spawn Hermes:', err.message);
        });

        child.unref();
        console.log(`Ofício Trigger: Hermes spawned (pid ${child.pid}) for ${filePath}`);
    }
};
