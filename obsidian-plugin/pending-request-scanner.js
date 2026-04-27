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

module.exports = { HERMES_MARKER, PendingRequestScanner };
