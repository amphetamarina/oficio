const { Plugin, Notice } = require('obsidian');
const { spawn } = require('child_process');

const HERMES_MARKER = '@hermes';
const STATUS_LOOKAHEAD_LINES = 15;

const OPEN_TASK = /^\s*-\s*\[\s*\]/;
const ANY_TASK = /^\s*-\s*\[/;
const STATUS = /^\s*Status:/;

class PendingRequestScanner {
    hasRunnableRequest(content) {
        const lines = content.split('\n');
        return lines.some((_, index) => {
            const taskIndex = this._taskIndex(lines, index);
            return taskIndex !== null && !this._hasStatus(lines, taskIndex);
        });
    }

    _taskIndex(lines, index) {
        if (this._isInlineRequest(lines[index])) {
            return index;
        }
        return this._splitTaskIndex(lines, index);
    }

    _isInlineRequest(line) {
        return OPEN_TASK.test(line) && line.includes(HERMES_MARKER);
    }

    _splitTaskIndex(lines, markerIndex) {
        const marker = lines[markerIndex];
        if (!marker.includes(HERMES_MARKER) || ANY_TASK.test(marker)) {
            return null;
        }

        const taskIndex = this._nextContentLine(lines, markerIndex + 1);
        if (taskIndex >= lines.length) {
            return null;
        }

        const task = lines[taskIndex];
        return OPEN_TASK.test(task) && !task.includes(HERMES_MARKER) ? taskIndex : null;
    }

    _hasStatus(lines, taskIndex) {
        const end = Math.min(lines.length, taskIndex + STATUS_LOOKAHEAD_LINES);
        for (let index = taskIndex + 1; index < end; index++) {
            if (STATUS.test(lines[index])) {
                return true;
            }
            if (this._endsBlock(lines[index])) {
                return false;
            }
        }
        return false;
    }

    _endsBlock(line) {
        return ANY_TASK.test(line) || Boolean(line && !/^\s/.test(line) && !/^#/.test(line));
    }

    _nextContentLine(lines, startIndex) {
        let index = startIndex;
        while (index < lines.length && !lines[index].trim()) {
            index++;
        }
        return index;
    }
}

class HermesRunner {
    constructor(plugin) {
        this.plugin = plugin;
        this._stderrBuffer = '';
    }

    run(filePath) {
        const args = this._args(filePath);
        this.plugin.log(`starting Hermes: hermes ${this._quoted(args)}`);
        this._stderrBuffer = '';

        const child = spawn('hermes', args, {
            cwd: this.plugin.vaultPath(),
            stdio: ['ignore', 'pipe', 'pipe'],
            env: { ...process.env },
        });

        this.plugin.log(`Hermes spawned (pid ${child.pid}) for ${filePath}`);
        new Notice(`Ofício: Hermes started for ${filePath}`);

        child.stdout.on('data', (data) => this._stdout(data));
        child.stderr.on('data', (data) => this._stderr(data));
        child.on('error', (error) => this._spawnFailed(error));
        child.on('close', (code, signal) => this._finished(filePath, code, signal));
    }

    _stderr(data) {
        const text = data.toString();
        this._stderrBuffer += text;
        console.error(`Ofício Trigger stderr: ${text.trimEnd()}`);
    }

    _finished(filePath, code, signal) {
        const sessionId = this._extractSessionId(this._stderrBuffer);
        const signalText = signal ? `, signal ${signal}` : '';

        if (code === 0 || sessionId) {
            const status = code === 0 ? 'completed successfully' : `completed with warnings (exit ${code}${signalText})`;
            this.plugin.log(`Hermes ${status} for ${filePath} (session ${sessionId || 'unknown'})`);
            new Notice(`Ofício: Hermes ${status === 'completed successfully' ? 'completed' : 'completed with warnings'} for ${filePath}`, 8000);
            return;
        }

        this.plugin.log(`Hermes failed for ${filePath} (exit ${code}${signalText})`);
        new Notice(`Ofício: Hermes failed for ${filePath}`, 15000);
    }

    _extractSessionId(stderr) {
        const match = stderr.match(/session_id:\s*(\S+)/);
        return match ? match[1] : null;
    }

    _args(filePath) {
        return [
            'chat',
            '-q',
            this._prompt(filePath),
            '--quiet',
            '--pass-session-id',
            '--source',
            'obsidian',
            '--yolo',
            '--accept-hooks',
        ];
    }

    _prompt(filePath) {
        return [
            `Scan the ofício vault for pending ${HERMES_MARKER} requests in ${filePath} and process them.`,
            '',
            'Use the oficio tools.',
            'When you start a request, call oficio_start with the Hermes Session ID from your system prompt.',
            'When you finish, call oficio_complete or oficio_fail with that same session_id.',
            'Unless the request asks for another format, write the final answer back through oficio_complete.response.',
            'Keep the response concise markdown; oficio_complete will place it under the request.',
            'Do not create a separate log file; the Hermes transcript is the session log.',
        ].join('\n');
    }

    _stdout(data) {
        console.log(`Ofício Trigger stdout: ${data.toString().trimEnd()}`);
    }

    _spawnFailed(error) {
        this.plugin.log(`failed to spawn Hermes: ${error.message}`);
        new Notice(`Ofício: failed to spawn Hermes - ${error.message}`, 10000);
    }

    _quoted(args) {
        return args.map((arg) => JSON.stringify(arg)).join(' ');
    }
}

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
