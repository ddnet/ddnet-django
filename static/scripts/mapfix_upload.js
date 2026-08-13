/* Card-grid UI for the mapfix upload page.
 *
 * Files are collected client-side; each file becomes a card showing the
 * mapname it was fuzzy-matched to, which can be corrected via a search
 * field. The whole batch is submitted in one multipart POST where the
 * n-th entry of "mapnames" belongs to the n-th entry of "mapfiles".
 */
(function () {
    'use strict';

    var grid = document.getElementById('mapfix-grid');
    var addTile = document.getElementById('mapfix-add');
    var fileInput = document.getElementById('mapfix-file-input');
    var replaceInput = document.getElementById('mapfix-replace-input');
    var csrfInput = document.getElementById('mapfix-csrf');
    var errorsEl = document.getElementById('mapfix-errors');
    var startQueuedBtn = document.getElementById('mapfix-start-queued');

    var cards = [];
    var replaceTarget = null;

    function basename(filename) {
        return filename.replace(/\.[^.]*$/, '');
    }

    function searchMaps(query) {
        var url = MAPFIX_SEARCH_URL + '?q=' + encodeURIComponent(query);
        return fetch(url, {credentials: 'same-origin'})
            .then(function (r) { return r.json(); })
            .then(function (d) { return d.results; });
    }

    function setStatus(card, cls, text) {
        card.el.classList.remove('ok', 'weak', 'bad');
        if (cls) {
            card.el.classList.add(cls);
        }
        card.statusEl.textContent = text || '';
    }

    function clearDiff(card) {
        card.diffSeq++;
        card.diffEl.innerHTML = '';
    }

    function renderDiff(card, lines) {
        card.diffEl.innerHTML = '';
        var ul = document.createElement('ul');
        lines.forEach(function (line) {
            var li = document.createElement('li');
            li.textContent = line;
            ul.appendChild(li);
        });
        card.diffEl.appendChild(ul);
    }

    // Diff the card's file against the released version of its chosen map.
    function requestDiff(card) {
        var seq = ++card.diffSeq;
        var mapname = card.input.value.trim();
        card.diffEl.innerHTML = '';
        if (!mapname) {
            return;
        }
        card.diffEl.textContent = 'diffing against released version…';

        var data = new FormData();
        data.append('csrfmiddlewaretoken', csrfInput.value);
        data.append('mapname', mapname);
        data.append('mapfile', card.file, card.file.name);
        fetch(MAPFIX_DIFF_URL, {
            method: 'POST',
            body: data,
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function (r) {
            return r.json();
        }).then(function (d) {
            if (seq !== card.diffSeq) {
                return; // superseded by a newer request
            }
            renderDiff(card, d.lines || [d.error || 'Diff failed.']);
        }).catch(function () {
            if (seq === card.diffSeq) {
                renderDiff(card, ['Diff unavailable.']);
            }
        });
    }

    function autoMatch(card) {
        setStatus(card, null, 'matching…');
        searchMaps(basename(card.file.name)).then(function (results) {
            if (card.manual) {
                return; // the user chose a map in the meantime
            }
            if (results.length) {
                card.input.value = results[0].name;
                if (results[0].score >= 0.6) {
                    setStatus(card, 'ok', '✓ matched');
                } else {
                    setStatus(card, 'weak', '⚠ uncertain match, please check');
                }
                requestDiff(card);
            } else {
                card.input.value = '';
                setStatus(card, 'bad', '✗ no match found');
                clearDiff(card);
            }
        });
    }

    function verify(card) {
        var value = card.input.value.trim();
        if (!value) {
            setStatus(card, 'bad', '✗ choose a map');
            return;
        }
        searchMaps(value).then(function (results) {
            for (var i = 0; i < results.length; i++) {
                if (results[i].name.toLowerCase() === value.toLowerCase()) {
                    card.input.value = results[i].name; // canonical spelling
                    setStatus(card, 'ok', '✓ matched');
                    requestDiff(card);
                    return;
                }
            }
            setStatus(card, 'bad', '✗ no such map');
            clearDiff(card);
        });
    }

    function clearSuggestions(card) {
        var ul = card.maprow.querySelector('.suggestions');
        if (ul) {
            ul.parentNode.removeChild(ul);
        }
    }

    function renderSuggestions(card, results) {
        clearSuggestions(card);
        if (!results.length) {
            return;
        }
        var ul = document.createElement('ul');
        ul.className = 'suggestions';
        results.forEach(function (r) {
            var li = document.createElement('li');
            li.textContent = r.name;
            li.addEventListener('mousedown', function (e) {
                e.preventDefault(); // keep the input from blurring first
                card.manual = true;
                card.input.value = r.name;
                clearSuggestions(card);
                setStatus(card, 'ok', '✓ matched');
                requestDiff(card);
            });
            ul.appendChild(li);
        });
        card.maprow.appendChild(ul);
    }

    // Upload a single card and start its fix right away.
    function uploadCard(card) {
        var mapname = card.input.value.trim();
        if (!mapname) {
            setStatus(card, 'bad', '✗ choose a map');
            return;
        }

        card.fixBtn.disabled = true;
        card.fixBtn.textContent = '…';

        var data = new FormData();
        data.append('csrfmiddlewaretoken', csrfInput.value);
        data.append('start', 'on');
        data.append('mapfiles', card.file, card.file.name);
        data.append('mapnames', mapname);

        fetch(window.location.href, {
            method: 'POST',
            body: data,
            credentials: 'same-origin',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function (r) {
            return r.json();
        }).then(function (d) {
            if (d.errors || !d.redirect) {
                showErrors(d.errors || ['Upload failed.']);
                resetFixButton(card);
                return;
            }
            markUploaded(card, d);
        }).catch(function () {
            showErrors(['Upload failed.']);
            resetFixButton(card);
        });
    }

    function resetFixButton(card) {
        card.fixBtn.disabled = false;
        card.fixBtn.classList.remove('armed');
        card.fixBtn.textContent = 'Fix';
    }

    // The card stays visible as a receipt; the × merely dismisses it. The fix
    // itself shows up in the fixes table right away.
    function markUploaded(card, response) {
        card.done = true;
        var i = cards.indexOf(card);
        if (i !== -1) {
            cards.splice(i, 1);
        }

        card.el.classList.remove('ok', 'weak', 'bad');
        card.el.classList.add('done');
        card.input.disabled = true;
        card.fixBtn.textContent = '✓';
        card.statusEl.textContent = response.started
            ? '✓ fix started'
            : '✓ uploaded — starts when the running fix finishes';

        refreshStatus();
    }

    var ARM_TIMEOUT = 3000;

    function createCard(file) {
        var card = {file: file, manual: false, done: false};

        var el = document.createElement('div');
        el.className = 'mapfix-card';

        var head = document.createElement('div');
        head.className = 'cardhead';

        var name = document.createElement('span');
        name.className = 'filename';
        name.title = 'Click to replace this file';
        name.textContent = file.name;
        name.addEventListener('click', function () {
            if (card.done) {
                return;
            }
            replaceTarget = card;
            replaceInput.click();
        });

        // needs a second click within ARM_TIMEOUT to actually kick off the fix
        var fixBtn = document.createElement('button');
        fixBtn.type = 'button';
        fixBtn.className = 'fixbtn';
        fixBtn.title = 'Upload this file and start the fix';
        fixBtn.textContent = 'Fix';
        var armTimer = null;
        fixBtn.addEventListener('click', function () {
            if (card.done || fixBtn.disabled) {
                return;
            }
            if (fixBtn.classList.contains('armed')) {
                clearTimeout(armTimer);
                uploadCard(card);
                return;
            }
            fixBtn.classList.add('armed');
            fixBtn.textContent = 'Sure?';
            armTimer = setTimeout(function () {
                resetFixButton(card);
            }, ARM_TIMEOUT);
        });

        var remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'remove';
        remove.title = 'Remove';
        remove.textContent = '×';
        remove.addEventListener('click', function () {
            var i = cards.indexOf(card);
            if (i !== -1) {
                cards.splice(i, 1);
            }
            el.parentNode.removeChild(el);
        });

        head.appendChild(name);
        head.appendChild(fixBtn);
        head.appendChild(remove);

        var maprow = document.createElement('div');
        maprow.className = 'maprow';

        var input = document.createElement('input');
        input.type = 'text';
        input.className = 'map-input';
        input.placeholder = 'Search map…';
        input.autocomplete = 'off';
        var timer = null;
        input.addEventListener('input', function () {
            card.manual = true;
            setStatus(card, null, '');
            clearDiff(card);
            clearTimeout(timer);
            timer = setTimeout(function () {
                var q = input.value.trim();
                if (q) {
                    searchMaps(q).then(function (results) {
                        renderSuggestions(card, results);
                    });
                } else {
                    clearSuggestions(card);
                }
            }, 150);
        });
        input.addEventListener('blur', function () {
            setTimeout(function () { clearSuggestions(card); }, 150);
            if (card.manual) {
                verify(card);
            }
        });
        maprow.appendChild(input);

        var status = document.createElement('span');
        status.className = 'status';

        var diff = document.createElement('div');
        diff.className = 'diff';

        el.appendChild(head);
        el.appendChild(maprow);
        el.appendChild(status);
        el.appendChild(diff);

        card.el = el;
        card.input = input;
        card.maprow = maprow;
        card.statusEl = status;
        card.diffEl = diff;
        card.diffSeq = 0;
        card.fixBtn = fixBtn;

        grid.insertBefore(el, addTile);
        cards.push(card);
        autoMatch(card);
    }

    function addFiles(fileList) {
        Array.prototype.forEach.call(fileList, createCard);
    }

    function showErrors(errors) {
        errorsEl.innerHTML = '';
        errors.forEach(function (e) {
            var li = document.createElement('li');
            li.textContent = e;
            errorsEl.appendChild(li);
        });
        errorsEl.style.display = errors.length ? '' : 'none';
    }

    addTile.addEventListener('click', function () {
        fileInput.click();
    });

    fileInput.addEventListener('change', function () {
        addFiles(fileInput.files);
        fileInput.value = '';
    });

    replaceInput.addEventListener('change', function () {
        if (replaceTarget && replaceInput.files.length) {
            replaceTarget.file = replaceInput.files[0];
            replaceTarget.el.querySelector('.filename').textContent =
                replaceTarget.file.name;
            if (!replaceTarget.manual) {
                autoMatch(replaceTarget);
            } else {
                requestDiff(replaceTarget);
            }
        }
        replaceTarget = null;
        replaceInput.value = '';
    });

    grid.addEventListener('dragover', function (e) {
        e.preventDefault();
        grid.classList.add('dragover');
    });
    grid.addEventListener('dragleave', function () {
        grid.classList.remove('dragover');
    });
    grid.addEventListener('drop', function (e) {
        e.preventDefault();
        grid.classList.remove('dragover');
        addFiles(e.dataTransfer.files);
    });

    // --- the fixes table: status polling and expandable per-row logs ---

    var fixesSection = document.getElementById('mapfix-fixes');
    var statusBody = document.getElementById('mapfix-table-body');
    var expanded = {};   // fix id -> bool
    var logCache = {};   // fixlog id -> text
    var latestStatus = null;
    var pollTimer = null;

    function rowIsExpandable(r) {
        return !!(r.log_id || r.state === 'running' || r.changelog);
    }

    function makeLogRow(r, liveLog) {
        var tr = document.createElement('tr');
        tr.className = 'logrow';
        var td = document.createElement('td');
        td.colSpan = 4;

        if (r.changelog) {
            var clLabel = document.createElement('div');
            clLabel.className = 'loglabel';
            clLabel.textContent = 'Changes vs released version';
            td.appendChild(clLabel);
            var clPre = document.createElement('pre');
            clPre.className = 'fixlog';
            clPre.textContent = r.changelog;
            td.appendChild(clPre);
        }

        if (r.log_id || r.state === 'running') {
            if (r.changelog) {
                var logLabel = document.createElement('div');
                logLabel.className = 'loglabel';
                logLabel.textContent = 'Fix log';
                td.appendChild(logLabel);
            }
            var pre = document.createElement('pre');
            pre.className = 'fixlog';
            if (r.state === 'running') {
                pre.textContent = liveLog || '…';
            } else if (logCache[r.log_id] !== undefined) {
                pre.textContent = logCache[r.log_id];
            } else {
                pre.textContent = 'loading…';
                fetch(MAPFIX_STATUS_URL + '?log=' + r.log_id, {credentials: 'same-origin'})
                    .then(function (resp) { return resp.json(); })
                    .then(function (d) {
                        logCache[r.log_id] = d.log || '';
                        pre.textContent = logCache[r.log_id];
                    });
            }
            td.appendChild(pre);
            if (r.state === 'running') {
                pre.scrollTop = pre.scrollHeight;
            }
        }

        tr.appendChild(td);
        return tr;
    }

    function makeStatusRow(r) {
        var tr = document.createElement('tr');
        tr.className = 'fixrow state-' + r.state;

        var toggle = document.createElement('td');
        toggle.className = 'toggle';
        if (rowIsExpandable(r)) {
            toggle.textContent = expanded[r.id] ? '▾' : '▸';
            tr.classList.add('haslog');
            tr.title = 'Show log';
            tr.addEventListener('click', function () {
                expanded[r.id] = !expanded[r.id];
                renderStatus(latestStatus);
            });
        }
        tr.appendChild(toggle);

        var name = document.createElement('td');
        name.textContent = r.name;
        tr.appendChild(name);

        var status = document.createElement('td');
        status.textContent = r.status;
        if (r.state === 'running') {
            var bar = document.createElement('span');
            bar.className = 'mapfix-progress';
            bar.appendChild(document.createElement('span'));
            status.appendChild(bar);
        }
        tr.appendChild(status);

        var when = document.createElement('td');
        when.textContent = r.when;
        tr.appendChild(when);

        return tr;
    }

    function renderStatus(data) {
        if (!statusBody || !data) {
            return;
        }
        latestStatus = data;

        fixesSection.style.display = data.rows.length ? '' : 'none';
        if (startQueuedBtn) {
            startQueuedBtn.style.display = data.queued_ids ? '' : 'none';
            startQueuedBtn.disabled = data.running;
            startQueuedBtn.title = data.running ? 'Another fix is currently running.' : '';
            startQueuedBtn.setAttribute('data-ids', data.queued_ids);
        }

        statusBody.innerHTML = '';
        data.rows.forEach(function (r) {
            statusBody.appendChild(makeStatusRow(r));
            if (expanded[r.id] && rowIsExpandable(r)) {
                statusBody.appendChild(makeLogRow(r, data.live_log));
            }
        });

        clearTimeout(pollTimer);
        if (data.running) {
            pollTimer = setTimeout(refreshStatus, 2000);
        }
    }

    function refreshStatus() {
        fetch(MAPFIX_STATUS_URL, {credentials: 'same-origin'})
            .then(function (r) { return r.json(); })
            .then(renderStatus)
            .catch(function () {
                clearTimeout(pollTimer);
                if (latestStatus && latestStatus.running) {
                    pollTimer = setTimeout(refreshStatus, 2000);
                }
            });
    }

    if (startQueuedBtn) {
        startQueuedBtn.addEventListener('click', function () {
            if (startQueuedBtn.disabled) {
                return;
            }
            startQueuedBtn.disabled = true;

            var data = new FormData();
            data.append('csrfmiddlewaretoken', csrfInput.value);
            data.append('ids', startQueuedBtn.getAttribute('data-ids'));
            fetch(MAPFIX_START_URL, {
                method: 'POST',
                body: data,
                credentials: 'same-origin'
            }).then(function () {
                refreshStatus();
            }).catch(function () {
                showErrors(['Starting the queued fixes failed.']);
                startQueuedBtn.disabled = false;
            });
        });
    }

    refreshStatus();
})();
