let pc = null;
let cameraDefaults = {};
let allPositions = [];
let currentPage = 0;
const itemsPerPage = 10;
let isTableView = false;

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show ' + type;
    
    // クリックで即座に消える
    toast.onclick = () => {
        toast.classList.remove('show');
        toast.onclick = null;
    };
    
    // 5秒後に自動で消える
    setTimeout(() => {
        toast.classList.remove('show');
        toast.onclick = null;
    }, 5000);
}

function togglePanel(panelId) {
    const body = document.getElementById(panelId + '-body');
    const icon = document.getElementById(panelId + '-toggle');
    body.classList.toggle('collapsed');
    icon.classList.toggle('collapsed');
}

function updateConnectionStatus(status) {
    const statusDiv = document.getElementById('connectionStatus');
    statusDiv.className = 'status ' + status;
    const messages = {
        'connecting': '🔄 接続中...',
        'connected': '✅ 接続完了',
        'disconnected': '❌ 切断'
    };
    statusDiv.textContent = messages[status] || status;
}

async function setupWebRTC() {
    updateConnectionStatus('connecting');
    
    try {
        pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });
        
        pc.ontrack = (event) => {
            const video = document.getElementById('videoElement');
            
            if (event.streams && event.streams[0]) {
                video.srcObject = event.streams[0];
            }
            
            video.onloadedmetadata = () => {
                updateConnectionStatus('connected');
            };
            
            video.play().catch(e => console.error('再生エラー:', e));
        };
        
        pc.oniceconnectionstatechange = () => {
            if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
                updateConnectionStatus('disconnected');
            }
        };
        
        pc.addTransceiver("video", { direction: "recvonly" });
        
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        const response = await fetch('/api/webrtc/offer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sdp: pc.localDescription.sdp,
                type: pc.localDescription.type,
                width: 640,
                height: 480
            })
        });
        
        if (!response.ok) {
            showToast('WebRTC接続エラー', 'error');
            updateConnectionStatus('disconnected');
            return;
        }
        
        const answer = await response.json();
        await pc.setRemoteDescription(new RTCSessionDescription(answer));
        
    } catch (error) {
        showToast('WebRTC接続失敗: ' + error.message, 'error');
        updateConnectionStatus('disconnected');
    }
}

async function loadCameraControls() {
    const response = await fetch('/api/camera/controls');
    const data = await response.json();
    
    if (data.status === 'ok') {
        const container = document.getElementById('cameraControls');
        container.innerHTML = '';
        cameraDefaults = {};
        
        for (const [name, ctrl] of Object.entries(data.controls)) {
            cameraDefaults[name] = ctrl.default;
            
            const group = document.createElement('div');
            group.className = 'control-group';
            
            if (ctrl.type === 'int') {
                // 既存のスライダー表示
                group.innerHTML = `
                    <label>${name}: <span id="${name}-value">${ctrl.value}</span></label>
                    <input type="range" 
                           id="${name}" 
                           min="${ctrl.min}" 
                           max="${ctrl.max}" 
                           value="${ctrl.value}"
                           oninput="updateCameraControl('${name}', this.value)">
                `;
            } else if (ctrl.type === 'bool') {
                // チェックボックス表示
                group.innerHTML = `
                    <label>
                        <input type="checkbox" 
                               id="${name}" 
                               ${ctrl.value ? 'checked' : ''}
                               onchange="updateCameraControl('${name}', this.checked ? 1 : 0)">
                        ${name}
                    </label>
                `;
            } else if (ctrl.type === 'menu') {
                // セレクトボックス表示
                let optionsHtml = '';
                for (const [optId, optLabel] of Object.entries(ctrl.options)) {
                    optionsHtml += `<option value="${optId}" ${parseInt(optId) === ctrl.value ? 'selected' : ''}>${optLabel}</option>`;
                }
                group.innerHTML = `
                    <label>${name}:</label>
                    <select id="${name}" onchange="updateCameraControl('${name}', this.value)">
                        ${optionsHtml}
                    </select>
                `;
            }
            
            container.appendChild(group);
        }
    }
}

async function updateCameraControl(name, value) {
    // int型の場合のみ-value要素を更新
    const valueElement = document.getElementById(name + '-value');
    if (valueElement) {
        valueElement.textContent = value;
    }
    await fetch(`/api/camera/control/${name}/${value}`, { method: 'POST' });
}

async function resetCameraDefaults() {
    for (const [name, defaultValue] of Object.entries(cameraDefaults)) {
        const control = document.getElementById(name);
        if (control && defaultValue !== null) {
            // 型に応じて値を設定
            if (control.type === 'checkbox') {
                control.checked = (defaultValue === 1);
            } else if (control.type === 'select-one') {
                control.value = defaultValue;
            } else {
                control.value = defaultValue;
            }
            await updateCameraControl(name, defaultValue);
        }
    }
    showToast('カメラパラメータをデフォルトに戻しました', 'success');
}

async function changeResolution() {
    const resolution = document.getElementById('resolutionSelect').value;
    const [width, height] = resolution.split('x').map(Number);
    
    const response = await fetch('/api/camera/resolution', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ width, height })
    });
    
    const data = await response.json();
    if (data.status === 'ok') {
        showToast(data.message, 'success');
        if (pc) pc.close();
        setTimeout(setupWebRTC, 1000);
    }
}

async function changeCodec() {
    const codec = document.getElementById('codecSelect').value;
    
    const response = await fetch('/api/camera/codec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codec: codec })
    });
    
    const data = await response.json();
    if (data.status === 'ok') {
        showToast(data.message, 'success');
        if (pc) pc.close();
        setTimeout(setupWebRTC, 1000);
    }
}

async function takeSnapshot() {
    const response = await fetch('/api/camera/snapshot', { method: 'POST' });
    const data = await response.json();
    
    if (data.status === 'ok') {
        showToast(data.message, 'success');
        loadSnapshots();
    } else {
        showToast('スナップショット失敗: ' + data.message, 'error');
    }
}

async function loadSnapshots() {
    const response = await fetch('/api/camera/snapshots');
    const data = await response.json();
    
    if (data.status === 'ok') {
        const grid = document.getElementById('snapshotsGrid');
        grid.innerHTML = '';
        
        data.snapshots.forEach(snap => {
            const item = document.createElement('div');
            item.className = 'snapshot-item';
            item.onclick = () => window.open(`/api/camera/snapshots/${snap.filename}`, '_blank');
            item.innerHTML = `
                <img src="/api/camera/snapshots/${snap.filename}" alt="${snap.filename}">
                <div class="snapshot-info">
                    ${(snap.size / 1024).toFixed(0)} KB
                </div>
            `;
            grid.appendChild(item);
        });
        
        showToast(`${data.snapshots.length}件のスナップショット`, 'success');
    }
}

async function updateGripperStatus() {
    try {
        const response = await fetch('/api/gripper/status');
        const data = await response.json();
        
        if (data.status === 'ok') {
            document.getElementById('gripperStatus').textContent = 
                `位置: ${data.position_mm.toFixed(2)}mm | サーボ: ${data.servo_on ? 'ON' : 'OFF'}`;
        }
    } catch (e) {
        console.error('Gripper status update error:', e);
    }
}

async function gripperServo(action) {
    await fetch(`/api/gripper/servo/${action}`, { method: 'POST' });
    updateGripperStatus();
}

async function gripperHome() {
    await fetch('/api/gripper/home', { method: 'POST' });
    updateGripperStatus();
}

async function gripperMove() {
    const position = document.getElementById('positionInput').value;
    await fetch(`/api/gripper/move/${position}`, { method: 'POST' });
    updateGripperStatus();
}

// ポジションテーブル: 個別読み込み
async function loadPositionTable() {
    const position = document.getElementById('posTableSelect').value;
    const response = await fetch(`/api/gripper/position_table/${position}`);
    const data = await response.json();
    
    if (data.status === 'ok') {
        document.getElementById('pt_position_mm').value = data.data.position_mm || 0;
        document.getElementById('pt_width_mm').value = data.data.width_mm || 0.1;
        document.getElementById('pt_speed_mm_s').value = data.data.speed_mm_s || 50;
        document.getElementById('pt_accel_g').value = data.data.accel_g || 0.3;
        document.getElementById('pt_decel_g').value = data.data.decel_g || 0.3;
        document.getElementById('pt_push_current').value = data.data.push_current_percent || 0;
        document.getElementById('posTableData').style.display = 'flex';
        showToast(`ポジション${position}のデータを読み込みました`, 'success');
    } else {
        showToast('読み込み失敗: ' + data.message, 'error');
    }
}

// ポジションテーブル: 個別保存
async function savePositionTable() {
    const position = parseInt(document.getElementById('posTableSelect').value);
    const data = {
        position_mm: parseFloat(document.getElementById('pt_position_mm').value),
        width_mm: parseFloat(document.getElementById('pt_width_mm').value),
        speed_mm_s: parseFloat(document.getElementById('pt_speed_mm_s').value),
        accel_g: parseFloat(document.getElementById('pt_accel_g').value),
        decel_g: parseFloat(document.getElementById('pt_decel_g').value),
        push_current_percent: parseInt(document.getElementById('pt_push_current').value)
    };
    
    const response = await fetch(`/api/gripper/position_table/${position}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    const result = await response.json();
    if (result.status === 'ok') {
        showToast(result.message, 'success');
        
        // デバッグログ
        console.log('=== Save Debug ===');
        console.log('position:', position);
        console.log('data:', data);
        console.log('allPositions.length:', allPositions.length);
        console.log('isTableView:', isTableView);
        
        // allPositions配列が存在すれば常に更新（表示モードに関わらず）
        if (allPositions.length > 0) {
            const index = allPositions.findIndex(pos => pos.position === position);
            console.log('Found index:', index);
            if (index !== -1) {
                // 保存したデータをそのまま反映
                console.log('Before update:', allPositions[index]);
                allPositions[index] = { 
                    position: position, 
                    ...data 
                };
                console.log('After update:', allPositions[index]);
                console.log('allPositions updated successfully');
                
                // テーブル表示中なら即座に再描画
                if (isTableView) {
                    console.log('Table view is active - calling displayPositionTable()');
                    displayPositionTable();
                } else {
                    console.log('Table view is NOT active - data updated but not displayed');
                }
            } else {
                console.log('ERROR: Position not found in allPositions array');
            }
        } else {
            console.log('WARNING: allPositions is empty - please load data first');
        }
    } else {
        showToast('保存失敗: ' + result.message, 'error');
    }
}

// ポジションテーブル: 全件読み込み
async function loadAllPositions() {
    showToast('全ポジションデータを読み込み中...', 'info');
    allPositions = [];
    
    for (let i = 0; i < 64; i++) {
        try {
            const response = await fetch(`/api/gripper/position_table/${i}`);
            const data = await response.json();
            if (data.status === 'ok') {
                allPositions.push({ position: i, ...data.data });
            }
        } catch (e) {
            console.error(`Position ${i} load error:`, e);
        }
    }
    
    showToast(`${allPositions.length}件のデータを読み込みました`, 'success');
    currentPage = 0;
    displayPositionTable();
    
    // テーブル表示に切り替え
    if (!isTableView) {
        toggleTableView();
    }
}

// ポジションテーブル: 表示切替
function toggleTableView() {
    isTableView = !isTableView;
    console.log('toggleTableView() - isTableView:', isTableView);
    document.getElementById('posTableList').style.display = isTableView ? 'block' : 'none';
    document.getElementById('posTableEdit').style.display = isTableView ? 'none' : 'block';
    
    // テーブル表示に切り替えた時、データがあれば再描画
    if (isTableView && allPositions.length > 0) {
        console.log('Switching to table view - redrawing table');
        displayPositionTable();
    }
}

// ポジションテーブル: ページ表示
function displayPositionTable() {
    console.log('=== displayPositionTable() called ===');
    console.log('currentPage:', currentPage);
    console.log('itemsPerPage:', itemsPerPage);
    console.log('allPositions.length:', allPositions.length);
    
    const tbody = document.getElementById('posTableBody');
    tbody.innerHTML = '';
    
    const start = currentPage * itemsPerPage;
    const end = Math.min(start + itemsPerPage, allPositions.length);
    console.log('Displaying positions from', start, 'to', end-1);
    
    for (let i = start; i < end; i++) {
        const pos = allPositions[i];
        const row = tbody.insertRow();
        row.onclick = () => editPositionFromTable(pos.position);
        
        row.innerHTML = `
            <td>${pos.position}</td>
            <td>${(pos.position_mm || 0).toFixed(2)}</td>
            <td>${(pos.width_mm || 0).toFixed(3)}</td>
            <td>${(pos.speed_mm_s || 0).toFixed(1)}</td>
            <td>${(pos.accel_g || 0).toFixed(2)}</td>
            <td>${(pos.decel_g || 0).toFixed(2)}</td>
            <td>${pos.push_current_percent || 0}</td>
        `;
    }
    
    // ページネーション
    const totalPages = Math.ceil(allPositions.length / itemsPerPage);
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    for (let i = 0; i < totalPages; i++) {
        const btn = document.createElement('button');
        btn.textContent = i + 1;
        btn.className = i === currentPage ? 'active' : '';
        btn.onclick = () => {
            currentPage = i;
            displayPositionTable();
        };
        pagination.appendChild(btn);
    }
}

// ポジションテーブル: テーブルから編集
function editPositionFromTable(position) {
    // 編集モードに切り替え
    toggleTableView();
    
    // ポジション番号をセット
    document.getElementById('posTableSelect').value = position;
    
    // データをロード
    loadPositionTable();
}

window.onload = () => {
    setupWebRTC();
    loadCameraControls();
    setInterval(updateGripperStatus, 2000);
};


// ===== 電流値モニター =====
let currentChart = null;
let currentMonitorInterval = null;

function initCurrentChart() {
    const ctx = document.getElementById('currentChart').getContext('2d');
    currentChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '電流値 (mA)',
                data: [],
                borderColor: 'rgb(0, 212, 255)',
                backgroundColor: 'rgba(0, 212, 255, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    display: true,
                    ticks: { 
                        color: '#aaa',
                        maxTicksLimit: 6,  // 最大6個のラベル表示（10秒間隔）
                        autoSkip: true,  // 自動的にラベルを間引く
                        callback: function(value, index, ticks) {
                            // 10秒（20ポイント）ごとにラベル表示
                            const label = this.getLabelForValue(value);
                            const seconds = parseFloat(label);
                            if (seconds % 10 === 0) {
                                return label;
                            }
                            return '';
                        }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    display: true,
                    beginAtZero: true,
                    min: 0,
                    max: 500,  // 電流値の縦軸を0-500mAに固定
                    ticks: { 
                        color: '#aaa',
                        stepSize: 100  // 100mA刻みで表示
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            },
            plugins: {
                legend: { labels: { color: '#fff' } }
            }
        }
    });
}

function startCurrentMonitor() {
    if (currentMonitorInterval) return;
    
    // グラフが未初期化の場合のみ初期化
    if (!currentChart) {
        initCurrentChart();
    }
    
    let dataPointIndex = 0;
    
    currentMonitorInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/gripper/current');
            const data = await response.json();
            
            if (data.status === 'ok') {
                document.getElementById('currentValue').textContent = data.current;
                
                // ラベルは相対時間（秒）を使用
                const timeLabel = (dataPointIndex * 0.5).toFixed(1) + 's';
                
                // グラフ更新
                currentChart.data.labels.push(timeLabel);
                currentChart.data.datasets[0].data.push(data.current);
                
                // 最大120データポイント（60秒分、500ms間隔）
                if (currentChart.data.labels.length > 120) {
                    currentChart.data.labels.shift();
                    currentChart.data.datasets[0].data.shift();
                }
                
                dataPointIndex++;
                currentChart.update('none'); // アニメーションなしで更新
            }
        } catch (error) {
            console.error('電流値取得エラー:', error);
        }
    }, 500); // 500ms間隔で取得
}

function stopCurrentMonitor() {
    if (currentMonitorInterval) {
        clearInterval(currentMonitorInterval);
        currentMonitorInterval = null;
    }
}

// ===== 把持状態判定 =====
async function checkGripStatus(silent = false) {
    try {
        const response = await fetch('/api/gripper/grip_status');
        const data = await response.json();
        
        const led = document.getElementById('statusLed');
        const text = document.getElementById('statusText');
        
        // LEDとテキストの更新
        led.className = 'status-led ' + data.status;
        
        const statusTexts = {
            'success': '✅ 把持成功',
            'failure': '❌ 把持失敗',
            'warning': '⚠️ 警告',
            'moving': '🔄 移動中'
        };
        text.textContent = statusTexts[data.status] || '待機中';
        
        // 詳細情報の更新
        document.getElementById('gripCurrent').textContent = data.current || '--';
        document.getElementById('gripPosition').textContent = 
            data.position_mm ? data.position_mm.toFixed(2) : '--';
        document.getElementById('gripPsfl').textContent = data.psfl ? 'あり' : 'なし';
        
        const reasonTexts = {
            'empty_grip': '空振り検出',
            'normal': '正常',
            'low_current': '電流値低',
            'positioning': '位置決め中'
        };
        document.getElementById('gripReason').textContent = 
            reasonTexts[data.reason] || data.reason || '--';
        
        // トースト通知（silentモードでない場合のみ）
        if (!silent) {
            if (data.status === 'success') {
                showToast('把持成功', 'success');
            } else if (data.status === 'failure') {
                showToast('把持失敗: ' + (reasonTexts[data.reason] || data.reason), 'error');
            } else if (data.status === 'warning') {
                showToast('警告: ' + (reasonTexts[data.reason] || data.reason), 'warning');
            }
        }
        
    } catch (error) {
        console.error('把持状態取得エラー:', error);
        showToast('把持状態の取得に失敗しました', 'error');
    }
}

// ===== 把持状態判定の自動更新 =====
let gripStatusInterval = null;

function startGripStatusMonitor() {
    if (gripStatusInterval) return;
    
    // 初回実行
    checkGripStatus(true);  // silent=true
    
    // 3秒間隔で自動更新（silent=trueでトースト通知を抑制）
    gripStatusInterval = setInterval(async () => {
        await checkGripStatus(true);
    }, 3000);  // 3秒間隔
}

function stopGripStatusMonitor() {
    if (gripStatusInterval) {
        clearInterval(gripStatusInterval);
        gripStatusInterval = null;
    }
}

// パネル展開時に電流値モニター・把持状態判定の自動更新開始
const originalTogglePanel = togglePanel;
togglePanel = function(panelId) {
    // 元の関数を実行
    originalTogglePanel(panelId);
    
    setTimeout(() => {
        // 電流値モニターパネルの場合
        if (panelId === 'current') {
            const body = document.getElementById('current-body');
            if (body && !body.classList.contains('collapsed')) {
                startCurrentMonitor();
            } else {
                stopCurrentMonitor();
            }
        }
        
        // 把持状態判定パネルの場合
        if (panelId === 'grip') {
            const body = document.getElementById('grip-body');
            if (body && !body.classList.contains('collapsed')) {
                startGripStatusMonitor();
            } else {
                stopGripStatusMonitor();
            }
        }
    }, 100);
};

// ==================== プリンター制御 ====================
let printerStatusInterval = null;
let macrosData = [];

// プリンター状態のポーリング
async function updatePrinterStatus() {
    try {
        const resp = await fetch('/api/printer/status');
        const data = await resp.json();
        
        if (data.status === 'ok') {
            const state = data.state || 'unknown';
            const temps = data.temperatures || {};
            const progress = data.progress || {};
            
            document.getElementById('printerState').textContent = state;
            document.getElementById('nozzleTemp').textContent = 
                temps.tool0?.actual?.toFixed(1) || '--';
            document.getElementById('bedTemp').textContent = 
                temps.bed?.actual?.toFixed(1) || '--';
            
            const percent = progress.completion || 0;
            document.getElementById('printerProgress').style.width = percent + '%';
            document.getElementById('progressPercent').textContent = percent.toFixed(1) + '%';
            
            if (progress.printTimeLeft) {
                const mins = Math.floor(progress.printTimeLeft / 60);
                document.getElementById('progressTime').textContent = `残り ${mins} 分`;
            } else {
                document.getElementById('progressTime').textContent = '--';
            }
        }
    } catch (err) {
        console.error('プリンター状態取得エラー:', err);
    }
}

function startPrinterMonitor() {
    if (!printerStatusInterval) {
        updatePrinterStatus();
        printerStatusInterval = setInterval(updatePrinterStatus, 3000);
    }
}

function stopPrinterMonitor() {
    if (printerStatusInterval) {
        clearInterval(printerStatusInterval);
        printerStatusInterval = null;
    }
}

// ファイル一覧を取得
async function refreshFiles() {
    try {
        const resp = await fetch('/api/printer/files');
        const data = await resp.json();
        const select = document.getElementById('gcodeFileSelect');
        select.innerHTML = '<option value="">-- ファイルを選択 --</option>';
        
        if (data.status === 'ok' && data.files) {
            data.files.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f.name;
                opt.textContent = f.name;
                select.appendChild(opt);
            });
        }
    } catch (err) {
        showToast('ファイル一覧取得エラー', 'error');
    }
}

// 印刷開始
async function startPrint() {
    const select = document.getElementById('gcodeFileSelect');
    const filename = select.value;
    if (!filename) {
        showToast('ファイルを選択してください', 'error');
        return;
    }
    
    try {
        const resp = await fetch('/api/printer/print', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename})
        });
        const data = await resp.json();
        showToast(data.message || '印刷開始', data.status === 'ok' ? 'success' : 'error');
    } catch (err) {
        showToast('印刷開始エラー', 'error');
    }
}

// 一時停止
async function pausePrint() {
    try {
        const resp = await fetch('/api/printer/pause', {method: 'POST'});
        const data = await resp.json();
        showToast(data.message || '一時停止', data.status === 'ok' ? 'success' : 'error');
    } catch (err) {
        showToast('一時停止エラー', 'error');
    }
}

// 中止
async function cancelPrint() {
    if (!confirm('印刷を中止しますか?')) return;
    
    try {
        const resp = await fetch('/api/printer/cancel', {method: 'POST'});
        const data = await resp.json();
        showToast(data.message || '印刷中止', data.status === 'ok' ? 'success' : 'error');
    } catch (err) {
        showToast('中止エラー', 'error');
    }
}

// マクロ一覧を取得
async function loadMacros() {
    try {
        const resp = await fetch('/api/printer/macros');
        const data = await resp.json();
        
        if (data.status === 'ok') {
            macrosData = data.macros || [];
            renderMacros();
        }
    } catch (err) {
        console.error('マクロ読み込みエラー:', err);
    }
}

function renderMacros() {
    const list = document.getElementById('macroList');
    list.innerHTML = '';
    
    macrosData.forEach(macro => {
        const item = document.createElement('div');
        item.className = 'macro-item';
        item.innerHTML = `
            <div class="macro-item-header">
                <span>${macro.name}</span>
            </div>
            <div class="macro-commands">${macro.commands.join('\n')}</div>
            <div class="macro-item-buttons">
                <button class="success" onclick="runMacro('${macro.name}')">▶️ 実行</button>
                <button class="danger" onclick="deleteMacro('${macro.name}')">🗑️ 削除</button>
            </div>
        `;
        list.appendChild(item);
    });
}

// マクロ実行
async function runMacro(name) {
    try {
        const resp = await fetch('/api/printer/macro/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name})
        });
        const data = await resp.json();
        showToast(data.message || `マクロ「${name}」実行`, data.status === 'ok' ? 'success' : 'error');
    } catch (err) {
        showToast('マクロ実行エラー', 'error');
    }
}

// マクロ削除
async function deleteMacro(name) {
    if (!confirm(`マクロ「${name}」を削除しますか?`)) return;
    
    try {
        const resp = await fetch(`/api/printer/macro/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        const data = await resp.json();
        showToast(data.message || 'マクロ削除', data.status === 'ok' ? 'success' : 'error');
        if (data.status === 'ok') loadMacros();
    } catch (err) {
        showToast('マクロ削除エラー', 'error');
    }
}

// マクロフォーム表示切替
function toggleMacroForm() {
    const wrapper = document.getElementById('macroFormWrapper');
    if (wrapper.style.display === 'none') {
        wrapper.style.display = 'block';
        document.getElementById('macroName').value = '';
        document.getElementById('macroCommands').value = '';
    } else {
        wrapper.style.display = 'none';
    }
}

// マクロ保存
async function saveMacro() {
    const name = document.getElementById('macroName').value.trim();
    const commandsText = document.getElementById('macroCommands').value.trim();
    
    if (!name || !commandsText) {
        showToast('マクロ名とコマンドを入力してください', 'error');
        return;
    }
    
    const commands = commandsText.split('\n').map(c => c.trim()).filter(c => c);
    
    try {
        const resp = await fetch('/api/printer/macro', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, commands})
        });
        const data = await resp.json();
        showToast(data.message || 'マクロ保存', data.status === 'ok' ? 'success' : 'error');
        
        if (data.status === 'ok') {
            toggleMacroForm();
            loadMacros();
        }
    } catch (err) {
        showToast('マクロ保存エラー', 'error');
    }
}

// 初期化処理の拡張
const originalOnload = window.onload;
window.onload = function() {
    if (originalOnload) originalOnload();
    
    // プリンター関連の初期化
    startPrinterMonitor();
    refreshFiles();
    loadMacros();
};
