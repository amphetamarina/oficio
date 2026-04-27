const { Notice } = require('obsidian');
const { spawn } = require('child_process');
const { HERMES_MARKER } = require('./pending-request-scanner');

class HermesRunner {
    constructor(plugin) {
        this.plugin = plugin;
    }

    run(filePath) {
        const args = this._args(filePath);
        this.plugin.log(`starting Hermes: hermes ${this._quoted(args)}`);

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

    _stderr(data) {
        console.error(`Ofício Trigger stderr: ${data.toString().trimEnd()}`);
    }

    _spawnFailed(error) {
        this.plugin.log(`failed to spawn Hermes: ${error.message}`);
        new Notice(`Ofício: failed to spawn Hermes - ${error.message}`, 10000);
    }

    _finished(filePath, code, signal) {
        if (code === 0) {
            this.plugin.log(`Hermes completed successfully for ${filePath}`);
            new Notice(`Ofício: Hermes completed for ${filePath}`, 8000);
            return;
        }

        const signalText = signal ? `, signal ${signal}` : '';
        this.plugin.log(`Hermes failed for ${filePath} (exit ${code}${signalText})`);
        new Notice(`Ofício: Hermes failed for ${filePath}`, 15000);
    }

    _quoted(args) {
        return args.map((arg) => JSON.stringify(arg)).join(' ');
    }
}

module.exports = { HermesRunner };
