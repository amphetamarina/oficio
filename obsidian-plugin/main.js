const { Plugin } = require('obsidian');
const { HermesRunner } = require('./hermes-runner');
const { HERMES_MARKER, PendingRequestScanner } = require('./pending-request-scanner');

const DAILY_FOLDER = 'Daily';
const TRIGGER_DEBOUNCE_MS = 5 * 60 * 1000;
const SAVE_SETTLE_MS = 2000;

module.exports = class OficioTriggerPlugin extends Plugin {
    async onload() {
        this.scanner = new PendingRequestScanner();
        this.runner = new HermesRunner(this);
        this.lastTriggerByPath = {};
        this.pendingTimer = null;

        this.log('loaded, watching daily notes');
        this.registerEvent(this.app.vault.on('modify', (file) => this._fileChanged(file)));
    }

    onunload() {
        this.log('unloaded');
        clearTimeout(this.pendingTimer);
    }

    vaultPath() {
        return this.app.vault.adapter.getBasePath();
    }

    log(message) {
        console.log(`Ofício Trigger: ${message}`);
    }

    _fileChanged(file) {
        if (!this._isDailyNote(file.path) || this._recentlyTriggered(file.path)) {
            return;
        }
        this._checkSoon(file);
    }

    _isDailyNote(filePath) {
        return filePath.startsWith(`${DAILY_FOLDER}/`) && filePath.endsWith('.md');
    }

    _recentlyTriggered(filePath) {
        const elapsed = Date.now() - (this.lastTriggerByPath[filePath] || 0);
        if (elapsed >= TRIGGER_DEBOUNCE_MS) {
            return false;
        }
        this.log(`debounced ${filePath} (${Math.round(elapsed / 1000)}s since last trigger)`);
        return true;
    }

    _checkSoon(file) {
        clearTimeout(this.pendingTimer);
        this.pendingTimer = setTimeout(() => this._check(file), SAVE_SETTLE_MS);
    }

    async _check(file) {
        this.pendingTimer = null;
        this.log(`checking ${file.path}`);

        try {
            const content = await this.app.vault.read(file);
            if (!this.scanner.hasRunnableRequest(content)) {
                this.log(`no pending ${HERMES_MARKER} in ${file.path}`);
                return;
            }
            this.lastTriggerByPath[file.path] = Date.now();
            this.runner.run(file.path);
        } catch (error) {
            console.error(`Ofício Trigger: error reading ${file.path}:`, error);
        }
    }
};
