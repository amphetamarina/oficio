const { Plugin, PluginSettingTab, Setting, Notice } = require('obsidian');
const { spawn } = require('child_process');

const STATUS_LOOKAHEAD_LINES = 15;
const OPEN_TASK = /^\s*-\s*\[\s*\]/;
const ANY_TASK = /^\s*-\s*\[/;
const STATUS = /^\s*Status:/;

const DAILY_FOLDER = 'Daily';
const TRIGGER_DEBOUNCE_MS = 5 * 60 * 1000;
const SAVE_SETTLE_MS = 2000;

const DEFAULT_PROMPT = [
    'Scan the ofício vault for pending {marker} requests in {filePath} and process them.',
    '',
    'Use the oficio MCP tools.',
    'When you start a request, call oficio_start with your session id.',
    'When you finish, call oficio_complete or oficio_fail with that same session_id.',
    'Unless the request asks for another format, write the final answer through oficio_complete.response',
    'as concise native markdown for insertion under the request. Do not wrap the whole response in a code',
    'fence unless the request specifically asks for a code block.',
].join('\n');

const DEFAULT_SETTINGS = {
    agentMarker: '@agent',
    agentCommand: '',
    agentArgs: '',
    promptTemplate: DEFAULT_PROMPT,
    dailyFolder: DAILY_FOLDER,
};

class PendingRequestScanner {
    constructor(marker) {
        this.marker = marker;
    }

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
        return OPEN_TASK.test(line) && line.includes(this.marker);
    }

    _splitTaskIndex(lines, markerIndex) {
        const marker = lines[markerIndex];
        if (!marker.includes(this.marker) || ANY_TASK.test(marker)) {
            return null;
        }
        const taskIndex = this._nextContentLine(lines, markerIndex + 1);
        if (taskIndex >= lines.length) {
            return null;
        }
        const task = lines[taskIndex];
        return OPEN_TASK.test(task) && !task.includes(this.marker) ? taskIndex : null;
    }

    _hasStatus(lines, taskIndex) {
        const end = Math.min(lines.length, taskIndex + STATUS_LOOKAHEAD_LINES);
        for (let index = taskIndex + 1; index < end; index++) {
            if (STATUS.test(lines[index])) return true;
            if (this._endsBlock(lines[index])) return false;
        }
        return false;
    }

    _endsBlock(line) {
        return ANY_TASK.test(line) || Boolean(line && !/^\s/.test(line) && !/^#/.test(line));
    }

    _nextContentLine(lines, startIndex) {
        let index = startIndex;
        while (index < lines.length && !lines[index].trim()) index++;
        return index;
    }
}

class AgentRunner {
    constructor(plugin) {
        this.plugin = plugin;
    }

    run(filePath) {
        const { agentCommand, agentArgs } = this.plugin.settings;
        if (!agentCommand) {
            new Notice('Ofício: configure an agent command in plugin settings.', 8000);
            return;
        }

        const prompt = this._renderPrompt(filePath);
        const args = this._parseArgs(agentArgs, prompt, filePath);
        this.plugin.log(`starting agent: ${agentCommand} ${args.map((a) => JSON.stringify(a)).join(' ')}`);

        const child = spawn(agentCommand, args, {
            cwd: this.plugin.vaultPath(),
            stdio: ['ignore', 'pipe', 'pipe'],
            env: { ...process.env, OFICIO_SESSION_ID: this._sessionId() },
        });

        this.plugin.log(`agent spawned (pid ${child.pid}) for ${filePath}`);
        new Notice(`Ofício: agent started for ${filePath}`);

        child.stdout.on('data', (data) => console.log(`Ofício stdout: ${data.toString().trimEnd()}`));
        child.stderr.on('data', (data) => console.error(`Ofício stderr: ${data.toString().trimEnd()}`));
        child.on('error', (error) => {
            this.plugin.log(`failed to spawn agent: ${error.message}`);
            new Notice(`Ofício: failed to spawn agent — ${error.message}`, 10000);
        });
        child.on('close', (code, signal) => {
            const signalText = signal ? `, signal ${signal}` : '';
            const ok = code === 0;
            this.plugin.log(`agent ${ok ? 'completed' : 'failed'} for ${filePath} (exit ${code}${signalText})`);
            new Notice(`Ofício: agent ${ok ? 'completed' : 'failed'} for ${filePath}`, ok ? 8000 : 15000);
        });
    }

    _renderPrompt(filePath) {
        const { promptTemplate, agentMarker } = this.plugin.settings;
        return (promptTemplate || DEFAULT_PROMPT)
            .replaceAll('{filePath}', filePath)
            .replaceAll('{marker}', agentMarker);
    }

    _parseArgs(template, prompt, filePath) {
        const raw = (template || '').trim();
        if (!raw) return [prompt];
        const tokens = raw.match(/(?:[^\s"']+|"(?:\\"|[^"])*"|'(?:\\'|[^'])*')+/g) || [];
        return tokens.map((token) =>
            token
                .replace(/^"|"$/g, '')
                .replace(/^'|'$/g, '')
                .replaceAll('{prompt}', prompt)
                .replaceAll('{filePath}', filePath)
                .replaceAll('{sessionId}', this._sessionId())
        );
    }

    _sessionId() {
        return `obsidian_${Date.now().toString(36)}`;
    }
}

class OficioSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();
        containerEl.createEl('h2', { text: 'Ofício Trigger' });

        new Setting(containerEl)
            .setName('Agent marker')
            .setDesc('Text that marks a task as an agent request. Default: @agent')
            .addText((text) =>
                text
                    .setPlaceholder('@agent')
                    .setValue(this.plugin.settings.agentMarker)
                    .onChange(async (value) => {
                        this.plugin.settings.agentMarker = value.trim() || '@agent';
                        await this.plugin.saveSettings();
                    })
            );

        new Setting(containerEl)
            .setName('Agent command')
            .setDesc('Executable to run when a pending request is detected (e.g. claude, codex, opencode, hermes).')
            .addText((text) =>
                text
                    .setPlaceholder('claude')
                    .setValue(this.plugin.settings.agentCommand)
                    .onChange(async (value) => {
                        this.plugin.settings.agentCommand = value.trim();
                        await this.plugin.saveSettings();
                    })
            );

        new Setting(containerEl)
            .setName('Agent arguments')
            .setDesc(
                'Space-separated argv. Placeholders: {prompt}, {filePath}, {sessionId}. ' +
                'If empty, the prompt is passed as a single positional argument.'
            )
            .addTextArea((text) =>
                text
                    .setPlaceholder('-p "{prompt}"')
                    .setValue(this.plugin.settings.agentArgs)
                    .onChange(async (value) => {
                        this.plugin.settings.agentArgs = value;
                        await this.plugin.saveSettings();
                    })
            );

        new Setting(containerEl)
            .setName('Prompt template')
            .setDesc('Sent to the agent. Placeholders: {filePath}, {marker}.')
            .addTextArea((text) => {
                text
                    .setValue(this.plugin.settings.promptTemplate)
                    .onChange(async (value) => {
                        this.plugin.settings.promptTemplate = value;
                        await this.plugin.saveSettings();
                    });
                text.inputEl.rows = 8;
                text.inputEl.style.width = '100%';
            });

        new Setting(containerEl)
            .setName('Daily folder')
            .setDesc("Vault-relative folder where the trigger watches notes. Default: Daily")
            .addText((text) =>
                text
                    .setPlaceholder('Daily')
                    .setValue(this.plugin.settings.dailyFolder)
                    .onChange(async (value) => {
                        this.plugin.settings.dailyFolder = value.trim() || 'Daily';
                        await this.plugin.saveSettings();
                    })
            );
    }
}

module.exports = class OficioTriggerPlugin extends Plugin {
    async onload() {
        await this.loadSettings();
        this.runner = new AgentRunner(this);
        this.lastTriggerByPath = {};
        this.pendingTimer = null;

        this.addSettingTab(new OficioSettingTab(this.app, this));
        this.log('loaded, watching daily notes');
        this.registerEvent(this.app.vault.on('modify', (file) => this._fileChanged(file)));
    }

    onunload() {
        this.log('unloaded');
        clearTimeout(this.pendingTimer);
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
    }

    vaultPath() {
        return this.app.vault.adapter.getBasePath();
    }

    log(message) {
        console.log(`Ofício Trigger: ${message}`);
    }

    _scanner() {
        return new PendingRequestScanner(this.settings.agentMarker);
    }

    _fileChanged(file) {
        if (!this._isDailyNote(file.path) || this._recentlyTriggered(file.path)) return;
        this._checkSoon(file);
    }

    _isDailyNote(filePath) {
        const folder = `${this.settings.dailyFolder}/`;
        return filePath.startsWith(folder) && filePath.endsWith('.md');
    }

    _recentlyTriggered(filePath) {
        const elapsed = Date.now() - (this.lastTriggerByPath[filePath] || 0);
        if (elapsed >= TRIGGER_DEBOUNCE_MS) return false;
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
            if (!this._scanner().hasRunnableRequest(content)) {
                this.log(`no pending ${this.settings.agentMarker} in ${file.path}`);
                return;
            }
            this.lastTriggerByPath[file.path] = Date.now();
            this.runner.run(file.path);
        } catch (error) {
            console.error(`Ofício Trigger: error reading ${file.path}:`, error);
        }
    }
};
