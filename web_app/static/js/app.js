let pc = null;
let cameraDefaults = {};
let allPositions = [];
let currentPage = 0;
const itemsPerPage = 10;
let isTableView = false;
let printerStatusInterval = null;
let printerStatusDisabled = false;
let robotConfig = null;
let activeJogAxis = null;

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
    updateMonitorViewUI();
    startPrinterMonitor();
    setInterval(updateGripperStatus, 2000);
    setupRobotControls();
};

async function setupRobotControls() {
    await loadRobotConfig();
    bindJogButton('robotJogNegative', 'negative');
    bindJogButton('robotJogPositive', 'positive');

    window.addEventListener('mouseup', robotJogStop);
    window.addEventListener('touchend', robotJogStop);
}

async function loadRobotConfig() {
    try {
        const response = await fetch('/api/robot/config');
        if (!response.ok) {
            return;
        }
        robotConfig = await response.json();
        const speedInput = document.getElementById('robotJogSpeed');
        if (speedInput && robotConfig) {
            speedInput.min = robotConfig.jog_speed_min_mm_s;
            speedInput.max = robotConfig.jog_speed_max_mm_s;
            speedInput.value = robotConfig.jog_speed_default_mm_s;
        }
    } catch (error) {
        console.error('ロボット設定取得エラー:', error);
    }
}

function bindJogButton(buttonId, direction) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    const startHandler = (event) => {
        event.preventDefault();
        robotJogStart(direction);
    };
    const stopHandler = (event) => {
        if (event) event.preventDefault();
        robotJogStop();
    };

    button.addEventListener('mousedown', startHandler);
    button.addEventListener('touchstart', startHandler, { passive: false });
    button.addEventListener('mouseup', stopHandler);
    button.addEventListener('mouseleave', stopHandler);
    button.addEventListener('touchend', stopHandler);
}

function getRobotJogAxis() {
    const axisSelect = document.getElementById('robotJogAxis');
    return axisSelect ? parseInt(axisSelect.value, 10) : 0;
}

function getRobotJogSpeed() {
    const speedInput = document.getElementById('robotJogSpeed');
    return speedInput ? parseFloat(speedInput.value) : 10.0;
}

async function robotHome() {
    try {
        const response = await fetch('/api/robot/home', { method: 'POST' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || '原点復帰に失敗しました');
        }
        showToast(payload.message || '原点復帰を開始しました', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function robotStopAll() {
    try {
        const response = await fetch('/api/robot/stop', { method: 'POST' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || '停止に失敗しました');
        }
        showToast(payload.message || '停止しました', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function robotJogStart(direction) {
    const axis = getRobotJogAxis();
    const speed = getRobotJogSpeed();
    activeJogAxis = axis;
    try {
        const response = await fetch('/api/robot/jog/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ axis, direction, speed_mm_s: speed })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || 'JOG開始に失敗しました');
        }
    } catch (error) {
        activeJogAxis = null;
        showToast(error.message, 'error');
    }
}

async function robotJogStop() {
    if (activeJogAxis === null) return;
    const axis = activeJogAxis;
    activeJogAxis = null;
    try {
        const response = await fetch('/api/robot/jog/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ axis })
        });
        await response.json().catch(() => ({}));
    } catch (error) {
        console.error('JOG停止エラー:', error);
    }
}

async function registerRobotPoint() {
    const pointNoInput = document.getElementById('robotPointNo');
    const commentInput = document.getElementById('robotPointComment');
    const pointNo = pointNoInput ? parseInt(pointNoInput.value, 10) : 0;
    const comment = commentInput ? commentInput.value : '';

    try {
        const response = await fetch('/api/robot/point/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ point_no: pointNo, comment })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || 'ポイント登録に失敗しました');
        }
        showToast('ポイントを登録しました', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function robotIoOutput(on) {
    const boardInput = document.getElementById('robotIoBoard');
    const portInput = document.getElementById('robotIoPort');
    const boardId = boardInput ? parseInt(boardInput.value, 10) : 0;
    const portNo = portInput ? parseInt(portInput.value, 10) : 0;

    try {
        const response = await fetch('/api/robot/io/output', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ board_id: boardId, port_no: portNo, on })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || 'IO出力に失敗しました');
        }
        showToast('IO出力を更新しました', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}


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

// ===== 把持状態判定の手動更新 =====
function fetchGripStatus(silent = false) {
    checkGripStatus(silent);
}

let activeMonitorView = 'grip';

function updateMonitorViewUI() {
    const isGrip = activeMonitorView === 'grip';
    const gripView = document.getElementById('gripMonitorView');
    const currentView = document.getElementById('currentMonitorView');
    if (gripView) {
        gripView.classList.toggle('active', isGrip);
        gripView.style.display = isGrip ? 'block' : 'none';
    }
    if (currentView) {
        currentView.classList.toggle('active', !isGrip);
        currentView.style.display = isGrip ? 'none' : 'block';
    }

    const statusLabel = document.getElementById('monitorStatusLabel');
    if (statusLabel) {
        statusLabel.textContent = isGrip ? '表示: 把持状態モニター' : '表示: 電流値モニター';
    }

    const toggleButton = document.getElementById('monitorToggleButton');
    if (toggleButton) {
        toggleButton.textContent = isGrip ? '⚡ 電流値モニターに切替' : '🤏 把持状態モニターに切替';
    }
}

function setMonitorView(view) {
    if (view !== 'grip' && view !== 'current') {
        return;
    }
    if (view === activeMonitorView) {
        updateMonitorViewUI();
        return;
    }
    activeMonitorView = view;
    if (view === 'grip') {
        stopCurrentMonitor();
    } else {
        startCurrentMonitor();
    }
    updateMonitorViewUI();
}

function toggleMonitorView(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const nextView = activeMonitorView === 'grip' ? 'current' : 'grip';
    setMonitorView(nextView);
}

// ===== 3Dプリンター =====
function startPrinterMonitor() {
    if (printerStatusDisabled || printerStatusInterval) {
        return;
    }
    setPrinterMessage('プリンター情報を取得中...', 'info');
    fetchPrinterStatus();
    printerStatusInterval = setInterval(fetchPrinterStatus, 5000);
}

function stopPrinterMonitor() {
    if (printerStatusInterval) {
        clearInterval(printerStatusInterval);
        printerStatusInterval = null;
    }
}

async function fetchPrinterStatus() {
    if (printerStatusDisabled) {
        return;
    }
    try {
        const response = await fetch('/api/printer/status');
        const payload = await response.json();

        if (payload.status === 'disabled') {
            handlePrinterDisabled(payload.message);
            return;
        }
        if (!response.ok) {
            throw new Error(payload.detail || payload.message || `HTTP ${response.status}`);
        }
        if (payload.status !== 'ok' || !payload.data) {
            throw new Error(payload.message || 'プリンター情報を取得できませんでした');
        }

        updatePrinterUI(payload.data);
    } catch (error) {
        console.error('プリンター状態取得エラー:', error);
        setPrinterMessage(error.message || 'プリンター情報の取得に失敗しました', 'error');
    }
}

function handlePrinterDisabled(message) {
    printerStatusDisabled = true;
    stopPrinterMonitor();
    updatePrinterButtons(null);
    setPrinterMessage(message || 'OctoPrintサービスが無効です', 'warning');
}

function setPrinterMessage(message, type = 'info') {
    const messageEl = document.getElementById('printerStatusMessage');
    if (!messageEl) {
        return;
    }
    messageEl.classList.remove('info', 'warning', 'error', 'hidden');
    if (!message) {
        messageEl.classList.add('hidden');
        messageEl.textContent = '';
        return;
    }
    messageEl.textContent = message;
    messageEl.classList.add(type);
}

function updatePrinterUI(status) {
    const stateEl = document.getElementById('printerState');
    if (stateEl) {
        stateEl.textContent = prettifyPrinterState(status.state);
    }

    updatePrinterProgress(status.progress);
    const etaEl = document.getElementById('printerEta');
    if (etaEl) {
        etaEl.textContent = formatEta(status.eta);
    }

    const temps = status.temperatures || {};
    const toolEl = document.getElementById('printerToolTemp');
    if (toolEl) {
        toolEl.textContent = formatTemperature(temps.tool0);
    }
    const bedEl = document.getElementById('printerBedTemp');
    if (bedEl) {
        bedEl.textContent = formatTemperature(temps.bed);
    }

    updatePrinterButtons(status.state);

    if (status.message) {
        setPrinterMessage(status.message, 'warning');
    } else if ((status.state || '').toLowerCase() === 'offline') {
        setPrinterMessage('プリンターがオフラインです。OctoPrintの接続を確認してください。', 'warning');
    } else {
        setPrinterMessage('');
    }
}

function updatePrinterProgress(progress) {
    const bar = document.getElementById('printerProgressBar');
    const text = document.getElementById('printerProgressText');
    if (!bar || !text) {
        return;
    }

    if (typeof progress === 'number' && !Number.isNaN(progress)) {
        const clamped = Math.max(0, Math.min(100, progress));
        bar.classList.remove('indeterminate');
        bar.style.width = clamped.toFixed(1) + '%';
        text.textContent = clamped.toFixed(1) + '%';
    } else {
        bar.classList.add('indeterminate');
        bar.style.width = '25%';
        text.textContent = '--%';
    }
}

function formatEta(seconds) {
    if (typeof seconds !== 'number' || Number.isNaN(seconds) || seconds <= 0) {
        return '--';
    }
    const totalMinutes = Math.round(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (hours > 0) {
        return `${hours}時間${minutes.toString().padStart(2, '0')}分`;
    }
    return `${Math.max(1, minutes)}分`;
}

function formatTemperature(temp) {
    if (!temp || (typeof temp.actual !== 'number' && typeof temp.temperature !== 'number')) {
        return '-- ℃';
    }
    const actual = typeof temp.actual === 'number' ? temp.actual : temp.temperature;
    const target = typeof temp.target === 'number' ? temp.target : undefined;
    if (typeof target === 'number') {
        return `${actual.toFixed(1)} / ${target.toFixed(1)} ℃`;
    }
    return `${actual.toFixed(1)} ℃`;
}

function prettifyPrinterState(state) {
    if (!state) {
        return '不明';
    }
    const normalized = state.toLowerCase();
    const labels = {
        operational: '待機中',
        printing: '造形中',
        paused: '一時停止',
        pausing: '停止処理中',
        resuming: '再開中',
        cancelling: 'キャンセル中',
        finishing: '完了処理中',
        offline: 'オフライン',
        error: 'エラー'
    };
    return labels[normalized] || state;
}

function updatePrinterButtons(state) {
    const pauseBtn = document.getElementById('pausePrinterButton');
    const resumeBtn = document.getElementById('resumePrinterButton');
    if (!pauseBtn || !resumeBtn) {
        return;
    }

    if (!state) {
        pauseBtn.disabled = true;
        resumeBtn.disabled = true;
        return;
    }

    const normalized = state.toLowerCase();
    const canPause = normalized.includes('print') && !normalized.includes('pause');
    const canResume = normalized.includes('pause');
    pauseBtn.disabled = !canPause;
    resumeBtn.disabled = !canResume;
}

async function pausePrinterJob() {
    if (printerStatusDisabled) {
        showToast('OctoPrintサービスが無効です', 'warning');
        return;
    }
    try {
        setPrinterMessage('プリンターへ一時停止を送信中...', 'info');
        const response = await fetch('/api/printer/pause', { method: 'POST' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || payload.message || '一時停止に失敗しました');
        }
        showToast(payload.message || 'プリントを一時停止しました', 'success');
        fetchPrinterStatus();
    } catch (error) {
        console.error('プリンター一時停止エラー:', error);
        showToast(error.message, 'error');
    }
}

async function resumePrinterJob() {
    if (printerStatusDisabled) {
        showToast('OctoPrintサービスが無効です', 'warning');
        return;
    }
    try {
        setPrinterMessage('プリンターへ再開を送信中...', 'info');
        const response = await fetch('/api/printer/resume', { method: 'POST' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || payload.message || '再開に失敗しました');
        }
        showToast(payload.message || 'プリントを再開しました', 'success');
        fetchPrinterStatus();
    } catch (error) {
        console.error('プリンター再開エラー:', error);
        showToast(error.message, 'error');
    }
}


async function presentPrinterBed() {
    if (printerStatusDisabled) {
        showToast('OctoPrintサービスが無効です', 'warning');
        return;
    }
    try {
        setPrinterMessage('ベッドを移動中...', 'info');
        const response = await fetch('/api/printer/present_bed', { method: 'POST' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || payload.message || '移動に失敗しました');
        }
        showToast(payload.message || 'ベッドを前に出しました', 'success');
    } catch (error) {
        console.error('ベッド移動エラー:', error);
        showToast(error.message, 'error');
    }
}

// Vision Detection Functions
async function detectFiber() {
    try {
        const response = await fetch('/api/vision/detect/fiber', { method: 'POST' });
        const result = await response.json();
        showVisionResult(result, 'Fiber Detection');
    } catch (error) {
        console.error('Error detecting fiber:', error);
        showToast('Error detecting fiber', 'error');
    }
}

async function detectBead() {
    try {
        const response = await fetch('/api/vision/detect/bead', { method: 'POST' });
        const result = await response.json();
        showVisionResult(result, 'Bead Detection');
    } catch (error) {
        console.error('Error detecting bead:', error);
        showToast('Error detecting bead', 'error');
    }
}

function showVisionResult(result, title) {
    const modal = new bootstrap.Modal(document.getElementById('visionModal'));
    const img = document.getElementById('visionResultImage');
    const dataDiv = document.getElementById('visionResultData');
    
    if (result.image_base64) {
        img.src = 'data:image/jpeg;base64,' + result.image_base64;
        img.style.display = 'block';
    } else {
        img.style.display = 'none';
    }
    
    let infoHtml = '<strong>Detected:</strong> ' + (result.detected ? 'Yes' : 'No') + '<br>';
    if (result.detected) {
        infoHtml += '<strong>Count:</strong> ' + result.count + '<br>';
        if (result.offset) {
            if (typeof result.offset === 'number') {
                infoHtml += '<strong>Offset:</strong> ' + result.offset.toFixed(2) + ' px<br>';
            } else {
                infoHtml += '<strong>Offset:</strong> X=' + result.offset.dx.toFixed(2) + ', Y=' + result.offset.dy.toFixed(2) + ' px<br>';
            }
        }
    }
    
    dataDiv.innerHTML = infoHtml;
    modal.show();
}

// Override showVisionResult to work with custom modal
function showVisionResult(result, title) {
    const modal = document.getElementById('visionModal');
    const img = document.getElementById('visionResultImage');
    const dataDiv = document.getElementById('visionResultData');
    
    modal.style.display = 'flex';
    
    if (result.image_base64) {
        img.src = 'data:image/jpeg;base64,' + result.image_base64;
        img.style.display = 'block';
    } else {
        img.style.display = 'none';
    }
    
    let infoHtml = '<strong>Detected:</strong> ' + (result.detected ? 'Yes' : 'No') + '<br>';
    if (result.detected) {
        infoHtml += '<strong>Count:</strong> ' + result.count + '<br>';
        if (result.offset) {
            if (typeof result.offset === 'number') {
                infoHtml += '<strong>Offset:</strong> ' + result.offset.toFixed(2) + ' px<br>';
            } else {
                infoHtml += '<strong>Offset:</strong> X=' + result.offset.dx.toFixed(2) + ', Y=' + result.offset.dy.toFixed(2) + ' px<br>';
            }
        }
    }
    
    dataDiv.innerHTML = infoHtml;
}
