// Variables globales
let mainChart, comboGauge, pressureBars, productionChart;
let pressureHistory = [];
let productionHistory = [];
const MAX_HISTORY_MAIN = 10;
const MAX_HISTORY_BAR = 6;
const MAX_HISTORY_PROD = 10;

const updateLock = {
    isLocked: false,
    queue: [],
    async acquire() {
        return new Promise(resolve => {
            if (!this.isLocked) {
                this.isLocked = true;
                resolve();
            } else {
                this.queue.push(resolve);
            }
        });
    },
    release() {
        if (this.queue.length > 0) {
            const next = this.queue.shift();
            next();
        } else {
            this.isLocked = false;
        }
    }
};

let currentPuitThresholds = null;
let activeAlerts = [];
const ALERT_EXPIRATION_HOURS = 24;
const MAX_ALERTS = 50;
let alertIconButton, alertCountBadge, alertListContainer, alertListUl;

const DASHBOARD_INTERVAL = 4000;
const PRODUCTION_INTERVAL = 60000;
let dashboardIntervalId, productionIntervalId;

// Affichage de l'heure en temps réel
function formatTime(date, includeSeconds = true) {
    if (!date) return '';
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
        second: includeSeconds ? '2-digit' : undefined,
        timeZone: 'Africa/Algiers'
    });
}
function updateTime() {
    const now = new Date();
    document.getElementById('current-time').textContent =
        `${formatTime(now)} - ${now.toLocaleDateString('fr-FR')}`;
}

// Calcul production journalière (exemple simplifié, adapte selon ton besoin)
function calculateDailyProduction(glr, pp, pt, diametre_duse) {
    if ([glr, pp, pt, diametre_duse].some(v => typeof v !== 'number' || isNaN(v))) {
        return 0;
    }
    const a = 0.1, b = 0.1, c = 0.546, k = 1000;
    const safeGlr = Math.max(glr, 1);
    const safeDeltaP = Math.max(pp - pt, 1);
    const safeDiam = Math.max(diametre_duse, 1);
    const production = k * Math.sqrt((a * safeDeltaP * Math.pow(safeDiam, b)) / Math.pow(safeGlr, c));
    return Math.max(100, Math.min(Math.round(production), 1500));
}

// Détruire un graphique Chart.js proprement
function destroyChart(chartInstance) {
    if (chartInstance) {
        try { chartInstance.destroy(); } catch (e) { }
    }
}

// Réinitialisation complète des graphiques et historiques
function resetCharts() {
    destroyChart(mainChart);        mainChart = null;
    destroyChart(comboGauge);       comboGauge = null;
    destroyChart(pressureBars);     pressureBars = null;
    destroyChart(productionChart);  productionChart = null;
    pressureHistory = [];
    productionHistory = [];
    const mainCtx = document.getElementById('mainChart')?.getContext('2d');
    const gaugeCtx = document.getElementById('comboGauge')?.getContext('2d');
    const pressureCtx = document.getElementById('pressureBars')?.getContext('2d');
    const productionCtx = document.getElementById('productionChart')?.getContext('2d');
    if (mainCtx)       initMainChart(mainCtx);
    if (gaugeCtx)      initComboGauge(gaugeCtx);
    if (pressureCtx)   initPressureBars(pressureCtx);
    if (productionCtx) initProductionChart(productionCtx);
    updateTime();
    updateAlertIconAndList();
}

// Nettoyage des anciennes alertes
function cleanupOldAlerts() {
    const now = new Date();
    activeAlerts = activeAlerts.filter(alert => {
        const hoursDiff = (now - alert.timestamp) / (1000 * 60 * 60);
        return hoursDiff < ALERT_EXPIRATION_HOURS;
    }).slice(0, MAX_ALERTS);
}

// Initialisation du système d'alertes
function initAlertSystem() {
    alertIconButton = document.getElementById('alert-icon-button');
    alertCountBadge = document.getElementById('alert-count-badge');
    alertListContainer = document.getElementById('alert-list-container');
    alertListUl = document.getElementById('alert-list-ul');
    if (!alertIconButton || !alertCountBadge || !alertListContainer || !alertListUl) return;
    function toggleAlertList(event) {
        event.stopPropagation();
        if (alertListContainer.style.display === 'none' || !alertListContainer.style.display) {
            renderAlertList();
            alertListContainer.style.display = 'block';
        } else {
            alertListContainer.style.display = 'none';
        }
    }
    function closeOnOutsideClick(event) {
        if (alertListContainer.style.display === 'block' &&
            !alertIconButton.contains(event.target) &&
            !alertListContainer.contains(event.target)) {
            alertListContainer.style.display = 'none';
        }
    }
    alertIconButton.addEventListener('click', toggleAlertList);
    document.addEventListener('click', closeOnOutsideClick);
    updateAlertIconAndList();
}

// Affichage de la liste des alertes
function renderAlertList() {
    if (!alertListUl) return;
    cleanupOldAlerts();
    alertListUl.innerHTML = '';
    if (activeAlerts.length === 0) {
        const li = document.createElement('li');
        li.textContent = "Aucune alerte active.";
        li.className = 'no-alerts';
        alertListUl.appendChild(li);
        return;
    }
    activeAlerts.forEach(alert => {
        const li = document.createElement('li');
        const time = formatTime(alert.timestamp);
        const date = alert.timestamp.toLocaleDateString('fr-FR');
        li.innerHTML = `
            <strong class="alert-puit">${alert.puitName || 'Système'}</strong>
            <span class="alert-time">${time} ${date}</span>
            <div class="alert-message">${alert.message}</div>
        `;
        alertListUl.appendChild(li);
    });
}

// Mise à jour de l'icône et de la liste d'alertes
function updateAlertIconAndList() {
    cleanupOldAlerts();
    if (alertCountBadge) {
        alertCountBadge.textContent = activeAlerts.length;
        alertCountBadge.style.display = activeAlerts.length > 0 ? 'inline-block' : 'none';
    }
    if (alertListContainer && alertListContainer.style.display === 'block') {
        renderAlertList();
    }
}

// Notification + ajout alerte si besoin
function showNotification(message, type = 'info') {
    const isErrorAlert = type === 'error' || message.toLowerCase().includes('alerte');
    if (isErrorAlert) {
        const puitName = currentPuitThresholds ? currentPuitThresholds.nom : 'Puits Inconnu';
        activeAlerts.unshift({
            message: message,
            timestamp: new Date(),
            puitName: puitName
        });
        cleanupOldAlerts();
        updateAlertIconAndList();
    }
    console.log("Notification:", message);
}

// Initialisation des graphiques
function initCharts() {
    const mainCtx = document.getElementById('mainChart')?.getContext('2d');
    const gaugeCtx = document.getElementById('comboGauge')?.getContext('2d');
    const pressureCtx = document.getElementById('pressureBars')?.getContext('2d');
    const productionCtx = document.getElementById('productionChart')?.getContext('2d');
    if (mainCtx) initMainChart(mainCtx);
    if (gaugeCtx) initComboGauge(gaugeCtx);
    if (pressureCtx) initPressureBars(pressureCtx);
    if (productionCtx) initProductionChart(productionCtx);
    updateTime();
}

// Initialisation du graphique principal
function initMainChart(ctx) {
    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'PRESSION (kg/cm²)',
                    data: [],
                    borderColor: '#FF2E63',
                    backgroundColor: 'rgba(255, 46, 99, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y',
                    pointBorderColor: [],
                    pointBackgroundColor: []
                },
                {
                    label: 'TEMPERATURE (°C)',
                    data: [],
                    borderColor: '#FFA500',
                    backgroundColor: 'rgba(255, 165, 0, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y1',
                    pointBorderColor: [],
                    pointBackgroundColor: []
                },
                {
                    label: 'DEBIT (m³/h)',
                    data: [],
                    borderColor: '#4BC0C0',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y2',
                    pointBorderColor: [],
                    pointBackgroundColor: []
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#2A2A3D',
                        font: { family: 'Montserrat', size: 12, weight: '600' },
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function (context) {
                            return formatTime(context[0].label);
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        callback: function (value) {
                            return formatTime(this.getLabelForValue(value));
                        },
                        color: '#6B7280',
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 10
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                },
                y: {
                    position: 'left',
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: { color: '#6B7280' },
                    title: { display: true, text: 'Pression (kg/cm²)', color: '#2A2A3D' }
                },
                y1: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#FFA500' },
                    title: { display: true, text: 'Température (°C)', color: '#FFA500' }
                },
                y2: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#4BC0C0' },
                    title: { display: true, text: 'Débit (m³/h)', color: '#4BC0C0' },
                    afterFit: scale => { scale.right += 50; }
                }
            }
        }
    });
}

// Initialisation du combo gauge
function initComboGauge(ctx) {
    comboGauge = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['GOR (m³/m³)', 'GLR (m³/m³)', 'Taux Eau (m³/h)'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ['#00FFA3', '#9C27B0', '#00D4FF']
            }]
        },
        options: {
            cutout: '70%',
            animation: { duration: 0 }
        }
    });
}

// Initialisation des barres de pression
function initPressureBars(ctx) {
    pressureBars = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'PIPELINE (kg/cm²)',
                    backgroundColor: '#2962FF',
                    data: [],
                    barThickness: 30
                },
                {
                    label: 'TÊTE (kg/cm²)',
                    backgroundColor: '#00E5FF',
                    data: [],
                    barThickness: 30
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#2A2A3D',
                        font: { family: 'Montserrat', size: 12, weight: '600' },
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function (context) {
                            return formatTime(context[0].label);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        color: '#6B7280',
                        callback: function (value) {
                            return formatTime(this.getLabelForValue(value));
                        },
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 6
                    }
                },
                y: {
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: { color: '#6B7280' },
                    title: { display: true, text: 'Pression (kg/cm²)', color: '#2A2A3D' }
                }
            }
        }
    });
}

// Initialisation du graphique de production
function initProductionChart(ctx) {
    productionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'PRODUCTION (m³/j)',
                data: [],
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#2A2A3D',
                        font: { family: 'Montserrat', size: 12, weight: '600' },
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function (context) {
                            const date = new Date(context[0].label);
                            return date.toLocaleString('fr-FR', {
                                weekday: 'short',
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit'
                            });
                        },
                        label: function (context) {
                            return `Production : ${context.formattedValue} m³/j`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        callback: function (value) {
                            const date = new Date(this.getLabelForValue(value));
                            return date.toLocaleDateString('fr-FR') + ' ' + date.toLocaleTimeString('fr-FR', {
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                        },
                        color: '#6B7280',
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 10
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                },
                y: {
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: { color: '#6B7280' },
                    title: { display: true, text: 'Production (m³/jour)', color: '#2A2A3D' }
                }
            }
        }
    });
}

// Mise à jour du graphique principal
async function updateMainChart(data) {
    await updateLock.acquire();
    try {
        if (!mainChart) return;
        // Reset complet du chart avant update
        mainChart.data.labels = [];
        mainChart.data.datasets.forEach(dataset => {
            dataset.data = [];
            if (dataset.pointBorderColor) dataset.pointBorderColor = [];
            if (dataset.pointBackgroundColor) dataset.pointBackgroundColor = [];
        });

        const sortedData = [...data].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
        if (sortedData.length === 0) {
            mainChart.update();
            return;
        }
        // Unicité par timestamp
        const uniqueData = [];
        const seenTimestamps = new Set();
        for (const item of sortedData) {
            const timestamp = new Date(item.timestamp).getTime();
            if (!seenTimestamps.has(timestamp)) {
                seenTimestamps.add(timestamp);
                uniqueData.push(item);
            }
        }
        const limitedData = uniqueData.slice(-MAX_HISTORY_MAIN);
        mainChart.data.labels = limitedData.map(d => new Date(d.timestamp));

        const alertColor = '#FF0000';
        const defaultPressureColors = { border: '#FF2E63', background: 'rgba(255, 46, 99, 0.8)' };
        const defaultTempColors = { border: '#FFA500', background: 'rgba(255, 165, 0, 0.8)' };
        const defaultDebitColors = { border: '#4BC0C0', background: 'rgba(75, 192, 192, 0.8)' };

        // Pression
        mainChart.data.datasets[0].data = limitedData.map(d => d.pression || 0);
        mainChart.data.datasets[0].pointBorderColor = limitedData.map(d =>
            currentPuitThresholds && (d.pression < currentPuitThresholds.p_min || d.pression > currentPuitThresholds.p_max)
                ? alertColor : defaultPressureColors.border);
        mainChart.data.datasets[0].pointBackgroundColor = limitedData.map(d =>
            currentPuitThresholds && (d.pression < currentPuitThresholds.p_min || d.pression > currentPuitThresholds.p_max)
                ? alertColor : defaultPressureColors.background);

        // Température
        mainChart.data.datasets[1].data = limitedData.map(d => d.temperature || 0);
        mainChart.data.datasets[1].pointBorderColor = limitedData.map(d =>
            currentPuitThresholds && (d.temperature < currentPuitThresholds.t_min || d.temperature > currentPuitThresholds.t_max)
                ? alertColor : defaultTempColors.border);
        mainChart.data.datasets[1].pointBackgroundColor = limitedData.map(d =>
            currentPuitThresholds && (d.temperature < currentPuitThresholds.t_min || d.temperature > currentPuitThresholds.t_max)
                ? alertColor : defaultTempColors.background);

        // Débit
        mainChart.data.datasets[2].data = limitedData.map(d => d.debit || 0);
        mainChart.data.datasets[2].pointBorderColor = limitedData.map(d =>
            currentPuitThresholds && (d.debit < currentPuitThresholds.d_min || d.debit > currentPuitThresholds.d_max)
                ? alertColor : defaultDebitColors.border);
        mainChart.data.datasets[2].pointBackgroundColor = limitedData.map(d =>
            currentPuitThresholds && (d.debit < currentPuitThresholds.d_min || d.debit > currentPuitThresholds.d_max)
                ? alertColor : defaultDebitColors.background);

        mainChart.update();

        // Vérification des seuils et alertes
        if (currentPuitThresholds && limitedData.length > 0) {
            const latestPuitData = limitedData[limitedData.length - 1];
            const puitName = currentPuitThresholds.nom || "Puits Actuel";
            if (latestPuitData.pression < currentPuitThresholds.p_min) {
                showNotification(`ALERTE ${puitName}: Pression (${latestPuitData.pression} kg/cm²) en dessous du seuil min (${currentPuitThresholds.p_min} kg/cm²)!`, 'error');
            } else if (latestPuitData.pression > currentPuitThresholds.p_max) {
                showNotification(`ALERTE ${puitName}: Pression (${latestPuitData.pression} kg/cm²) au dessus du seuil max (${currentPuitThresholds.p_max} kg/cm²)!`, 'error');
            }
            if (latestPuitData.temperature < currentPuitThresholds.t_min) {
                showNotification(`ALERTE ${puitName}: Température (${latestPuitData.temperature} °C) en dessous du seuil min (${currentPuitThresholds.t_min} °C)!`, 'error');
            } else if (latestPuitData.temperature > currentPuitThresholds.t_max) {
                showNotification(`ALERTE ${puitName}: Température (${latestPuitData.temperature} °C) au dessus du seuil max (${currentPuitThresholds.t_max} °C)!`, 'error');
            }
            if (latestPuitData.debit < currentPuitThresholds.d_min) {
                showNotification(`ALERTE ${puitName}: Débit (${latestPuitData.debit} m³/h) en dessous du seuil min (${currentPuitThresholds.d_min} m³/h)!`, 'error');
            } else if (latestPuitData.debit > currentPuitThresholds.d_max) {
                showNotification(`ALERTE ${puitName}: Débit (${latestPuitData.debit} m³/h) au dessus du seuil max (${currentPuitThresholds.d_max} m³/h)!`, 'error');
            }
        }
    } catch (error) {
        console.error("Erreur lors de la mise à jour du graphique principal:", error);
    } finally {
        updateLock.release();
    }
}

// Mise à jour du combo gauge
async function updateComboGauge(data) {
    await updateLock.acquire();
    try {
        if (!comboGauge) return;
        comboGauge.data.datasets[0].data = [data.gor || 0, data.glr || 0, data.taux_eau || 0];
        comboGauge.update();
    } catch (error) {
        console.error("Erreur lors de la mise à jour du combo gauge:", error);
    } finally {
        updateLock.release();
    }
}

// Mise à jour des barres de pression
async function updatePressureBars(data) {
    await updateLock.acquire();
    try {
        if (!pressureBars) return;
        const timestamp = data.timestamp ? new Date(data.timestamp) : new Date();
        const lastTimestamp = pressureHistory.length > 0 ? pressureHistory[pressureHistory.length-1].timestamp.getTime() : null;
        const currentTimestamp = timestamp.getTime();
        if (!lastTimestamp || currentTimestamp !== lastTimestamp) {
            pressureHistory.push({
                timestamp: timestamp,
                pip: data.pression_pip || 0,
                tete: data.pression_tete || 0
            });
            if (pressureHistory.length > MAX_HISTORY_BAR) pressureHistory.shift();
            pressureBars.data.labels = pressureHistory.map(d => d.timestamp);
            pressureBars.data.datasets[0].data = pressureHistory.map(d => d.pip);
            pressureBars.data.datasets[1].data = pressureHistory.map(d => d.tete);
            pressureBars.update();
        }
    } catch (error) {
        console.error("Erreur lors de la mise à jour des barres de pression:", error);
    } finally {
        updateLock.release();
    }
}

// Mise à jour du graphique de production
async function updateProductionChart(data) {
    await updateLock.acquire();
    try {
        if (!productionChart) return;
        const minuteGroups = {};
        const sortedData = [...data].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
        for (const item of sortedData) {
            const date = new Date(item.timestamp);
            const minuteKey = `${date.getHours()}:${date.getMinutes()}`;
            minuteGroups[minuteKey] = item;
        }
        const filteredData = Object.values(minuteGroups);
        if (filteredData.length === 0) return;
        const last = filteredData[filteredData.length - 1];
        const productionValue = calculateDailyProduction(
            last.glr || 0,
            last.pression_pip || 0,
            last.pression_tete || 0,
            last.diametre_duse || 0
        );
        const now = new Date(last.timestamp || new Date());
        const lastTimestamp = productionHistory.length > 0 ? productionHistory[productionHistory.length-1].timestamp.getTime() : null;
        const currentTimestamp = now.getTime();
        if (!lastTimestamp || currentTimestamp !== lastTimestamp) {
            productionHistory.push({ timestamp: now, value: productionValue });
            if (productionHistory.length > MAX_HISTORY_PROD) productionHistory.shift();
            productionChart.data.labels = productionHistory.map(d => d.timestamp);
            productionChart.data.datasets[0].data = productionHistory.map(d => d.value);
            productionChart.update();
        }
    } catch (error) {
        console.error("Erreur lors de la mise à jour du graphique de production:", error);
    } finally {
        updateLock.release();
    }
}

// Mise à jour du tableau de bord
async function updateDashboard() {
    if (updateLock.isLocked) return;
    try {
        let url = "/api/modbus_data";
        if (currentPuitThresholds && currentPuitThresholds.id) {
            url += `?puit_id=${currentPuitThresholds.id}`;
        }
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();
        const lastData = data[data.length - 1] || {};
        if (data.length > 0) {
            await Promise.all([
                updateMainChart(data),
                updateComboGauge(lastData),
                updatePressureBars(lastData)
            ]);
        }
    } catch (error) {
        showNotification("Erreur de connexion au serveur de données", "error");
    }
}

// Mise à jour des données de production
async function updateProduction() {
    if (updateLock.isLocked) return;
    try {
        let url = "/api/modbus_data";
        if (currentPuitThresholds && currentPuitThresholds.id) {
            url += `?puit_id=${currentPuitThresholds.id}`;
        }
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();
        if (data.length > 0) {
            await updateProductionChart(data);
        }
    } catch (error) {}
}

// Récupération des données des puits
async function fetchPuitsData() {
    try {
        const response = await fetch('/api/puits');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        showNotification("Erreur de chargement de la liste des puits", "error");
        return [];
    }
}

// Récupération des détails d'un puits et RESET complet du dashboard
async function fetchPuitDetails(puitId) {
    await updateLock.acquire();
    try {
        document.getElementById('mainChart').style.opacity = '0.5';
        destroyChart(mainChart);        mainChart = null;
        destroyChart(comboGauge);       comboGauge = null;
        destroyChart(pressureBars);     pressureBars = null;
        destroyChart(productionChart);  productionChart = null;
        pressureHistory = [];
        productionHistory = [];
        activeAlerts = [];
        updateAlertIconAndList();
        const mainCtx = document.getElementById('mainChart')?.getContext('2d');
        const gaugeCtx = document.getElementById('comboGauge')?.getContext('2d');
        const pressureCtx = document.getElementById('pressureBars')?.getContext('2d');
        const productionCtx = document.getElementById('productionChart')?.getContext('2d');
        if (mainCtx)       initMainChart(mainCtx);
        if (gaugeCtx)      initComboGauge(gaugeCtx);
        if (pressureCtx)   initPressureBars(pressureCtx);
        if (productionCtx) initProductionChart(productionCtx);
        if (!puitId) {
            currentPuitThresholds = null;
            document.querySelector('.dashboard-title').textContent = 'SURVEILLANCE DES PARAMÈTRES DE PRODUCTION';
            document.getElementById('mainChart').style.opacity = '1';
            return;
        }
        const response = await fetch(`/api/puit_details/${puitId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        currentPuitThresholds = await response.json();
        document.querySelector('.dashboard-title').textContent =
            `SURVEILLANCE DES PARAMÈTRES - ${currentPuitThresholds.nom.toUpperCase()}`;
        document.getElementById('mainChart').style.opacity = '1';
        await Promise.all([updateDashboard(), updateProduction()]);
    } catch (error) {
        currentPuitThresholds = null;
        showNotification(`Impossible de charger les seuils pour le puits ID ${puitId}`, "error");
        document.getElementById('mainChart').style.opacity = '1';
    } finally {
        updateLock.release();
    }
}

// Initialisation de la recherche de puits
async function initPuitSearch() {
    const searchInput = document.getElementById('puit-search');
    const resultsContainer = document.getElementById('puit-results');
    if (!searchInput || !resultsContainer) return;
    try {
        const puitsData = await fetchPuitsData();
        if (!puitsData || puitsData.length === 0) {
            showNotification("Aucun puits disponible dans la base de données", "warning");
            return;
        }
        if (puitsData.length > 0) {
            searchInput.value = puitsData[0].nom;
            await fetchPuitDetails(puitsData[0].id);
        }
        searchInput.addEventListener('input', function () {
            const searchTerm = this.value.toLowerCase();
            resultsContainer.innerHTML = '';
            if (searchTerm.length === 0) {
                resultsContainer.style.display = 'none';
                return;
            }
            const filteredPuits = puitsData.filter(puit =>
                puit.nom.toLowerCase().includes(searchTerm)
            );
            if (filteredPuits.length > 0) {
                filteredPuits.forEach(puit => {
                    const div = document.createElement('div');
                    div.textContent = puit.nom;
                    div.addEventListener('click', async function () {
                        searchInput.value = puit.nom;
                        resultsContainer.innerHTML = '';
                        resultsContainer.style.display = 'none';
                        await fetchPuitDetails(puit.id);
                    });
                    resultsContainer.appendChild(div);
                });
                resultsContainer.style.display = 'block';
            } else {
                resultsContainer.style.display = 'none';
            }
        });
        document.addEventListener('click', function (event) {
            if (!searchInput.contains(event.target) && !resultsContainer.contains(event.target)) {
                resultsContainer.style.display = 'none';
            }
        });
    } catch (error) {}
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', async function () {
    try {
        initCharts();
        initAlertSystem();
        await initPuitSearch();
        dashboardIntervalId = setInterval(updateDashboard, DASHBOARD_INTERVAL);
        productionIntervalId = setInterval(updateProduction, PRODUCTION_INTERVAL);
        setInterval(updateTime, 1000);
        if (document.getElementById("calendar")) {
            flatpickr("#calendar", {
                inline: true,
                locale: "fr",
                dateFormat: "Y-m-d",
                time_24hr: true,
                enableTime: false
            });
        }
    } catch (error) {
        showNotification("Erreur d'initialisation de l'application", "error");
    }
});