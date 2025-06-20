// Variables globales
let mainChart, comboGauge, pressureBars, productionChart;
let pressureHistory = [];
let productionHistory = [];
const MAX_HISTORY_MAIN = 10;
const MAX_HISTORY_BAR = 6;
const MAX_HISTORY_PROD = 10;
const NBR_CHANGEUR_STATUS = 5; // Nombre de changeurs de statut


async function updatePuitStatus(puitId, newStatus) {
    try {
        const response = await fetch(`/api/update_puit_status/${puitId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // 1. Rafraîchir le dashboard admin si disponible
        if (typeof refreshWellStats === 'function') {
            refreshWellStats();
        }
        
        // 2. Alternative pour les iframes/onglets ouverts
        if (window.opener && typeof window.opener.refreshWellStats === 'function') {
            window.opener.refreshWellStats();
        }
        
        
        
        return result;
        
    } catch (error) {
        console.error("Erreur lors de la mise à jour du statut du puits:", error);
        showNotification(`Erreur technique: ${error.message}`, 'error');
        return {
            success: false,
            message: error.message
        };
    }
}

// Fonction helper pour les notifications (à adapter à votre système existant)
function showNotification(message, type = 'info') {
    // Utilisez votre système de notification existant ou cette implémentation de base
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}


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
    // Si le puits est inactif ou en maintenance, retourner 0
    if (
        currentPuitThresholds &&
        (currentPuitThresholds.status === 'inactif' || currentPuitThresholds.status === 'en maintenance')
    ) {
        return 0;
    }
    // Sinon, calculer normalement
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

// Initialisation de la recherche de puits
async function initPuitSearch() {
    const searchInput = document.getElementById('puit-search');
    const resultsContainer = document.getElementById('puit-results');
    if (!searchInput || !resultsContainer) return;
    try {
        const puitsData = await fetchPuitsData();
        if (!puitsData || puitsData.length === 0) {
            //showNotification("Aucun puits disponible dans la base de données", "warning");
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
    const uniqueAlerts = [];
    const seenMessages = new Set();
    
    activeAlerts.forEach(alert => {
        const hoursDiff = (now - alert.timestamp) / (1000 * 60 * 60);
        if (hoursDiff < ALERT_EXPIRATION_HOURS && !seenMessages.has(alert.message)) {
            seenMessages.add(alert.message);
            uniqueAlerts.push(alert);
        }
    });
    
    activeAlerts = uniqueAlerts.slice(0, MAX_ALERTS);
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
    // Ignorer les notifications si le puits est inactif ou en maintenance
    if (currentPuitThresholds && 
        (currentPuitThresholds.status === 'inactif' || currentPuitThresholds.status === 'en maintenance') &&
        type === 'error') {
        return;
    } 
    // Ignorer les notifications d'erreur pendant les premières 5 secondes après le chargement
    if (performance.now() < 5000 && type === 'error') {
        console.log("Notification ignorée pendant l'initialisation:", message);
        return;
    }
    
    const isErrorAlert = type === 'error' || message.toLowerCase().includes('alerte');
    if (isErrorAlert) {
        const puitName = currentPuitThresholds ? currentPuitThresholds.nom : 'Puits Inconnu';
        
        // Vérifier si une alerte identique existe déjà
        const now = new Date();
        const existingAlert = activeAlerts.find(alert => 
            alert.message === message && 
            ((now - alert.timestamp) / (1000 * 60)) < 5 // Moins de 5 minutes
        );
        
        if (!existingAlert) {
            activeAlerts.unshift({
                message: message,
                timestamp: now,
                puitName: puitName,
                puitId: currentPuitThresholds ? currentPuitThresholds.id : null
            });
            cleanupOldAlerts();
            updateAlertIconAndList();
            
            // Vérifier si nous avons plus de 5 alertes pour le puits actuel
            if (currentPuitThresholds && currentPuitThresholds.id) {
                const puitAlerts = activeAlerts.filter(alert => 
                    alert.puitId === currentPuitThresholds.id
                );

                if (puitAlerts.length >= NBR_CHANGEUR_STATUS && currentPuitThresholds.status !== 'en urgence') {
                    // Mettre à jour le statut du puits
                    updatePuitStatus(currentPuitThresholds.id, 'en urgence')
                        .then(updatedPuit => {
                            if (updatedPuit) {
                                currentPuitThresholds.status = 'en urgence';
                                showNotification(`Le statut du puits ${currentPuitThresholds.nom} a été changé en EN URGENCE en raison de multiples alertes`, 'error');
                                
                            }
                        });
                }
            }
        }
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
        }        });
}

// Initialisation du graphique de production
function initProductionChart(ctx) {
    productionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'PRODUCTION JOURNALIÈRE (m³/j)',
                    data: [],
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'DÉBIT HUILE (m³/h) -jaugeage-',
                    data: [],
                    borderColor: '#FF9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y1'
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
                    position: 'left',
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: { color: '#6B7280' },
                    title: { 
                        display: true, 
                        text: 'Production (m³/jour)', 
                        color: '#4CAF50' 
                    }
                },
                y1: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#FF9800' },
                    title: { 
                        display: true, 
                        text: 'Débit Huile (m³/h)', 
                        color: '#FF9800' 
                    }
                }
            }
        }
    });
}

// Mise à jour du graphique principal
async function updateMainChart(data) {
    await updateLock.acquire();
    try {
        if (!mainChart || !data || data.length === 0) return;

        const isInitialData = data.length <= 3; // Ajustez selon vos critères

        // Réinitialiser les données du graphique
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

        // Mise à jour : vérification des seuils uniquement si le puits est actif
        if (currentPuitThresholds && !isInitialData && limitedData.length > 0) {
            const latestPuitData = limitedData[limitedData.length - 1];
            const puitName = currentPuitThresholds.nom || "Puits Actuel";
            const puitStatus = currentPuitThresholds.status;

            if (puitStatus !== 'inactif' && puitStatus !== 'en maintenance') {
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
        
        // Tri des données par timestamp
        const sortedData = [...data].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
        
        if (sortedData.length === 0) return;
        
        // Récupération des données les plus récentes
        const lastData = sortedData[sortedData.length - 1];
        const now = new Date(lastData.timestamp || new Date());
        
        // Calcul de la production journalière
        const productionValue = calculateDailyProduction(
            lastData.glr || 0,
            lastData.pression_pip || 0,
            lastData.pression_tete || 0,
            lastData.diametre_duse || 0
        );
        
        // Vérification si les données sont nouvelles
        const lastTimestamp = productionHistory.length > 0 ? 
            productionHistory[productionHistory.length-1].timestamp.getTime() : null;
        const currentTimestamp = now.getTime();
        
        if (!lastTimestamp || currentTimestamp !== lastTimestamp) {
            // Ajout des nouvelles données à l'historique
            productionHistory.push({ 
                timestamp: now, 
                value: productionValue,
                debit_huile: lastData.debit_huile || 0
            });
            
            // Limite de l'historique
            if (productionHistory.length > MAX_HISTORY_PROD) {
                productionHistory.shift();
            }
            
            // Mise à jour des labels et données
            productionChart.data.labels = productionHistory.map(d => d.timestamp);
            productionChart.data.datasets[0].data = productionHistory.map(d => d.value);
            productionChart.data.datasets[1].data = productionHistory.map(d => d.debit_huile);
            
            // Mise à jour du graphique
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
        //showNotification("Erreur de connexion au serveur de données", "error");
    }
}


// Mise à jour des données de production
async function updateProduction() {
    if (updateLock.isLocked) return;
    try {
        // Récupérer les données de télégaugeage
        let telejaugeageUrl = "/get_telegougage_data";
        if (currentPuitThresholds && currentPuitThresholds.id) {
            telejaugeageUrl += `?puit_id=${currentPuitThresholds.id}`;
        }
        const telejaugeageRes = await fetch(telejaugeageUrl);
        if (!telejaugeageRes.ok) throw new Error(`HTTP error! status: ${telejaugeageRes.status}`);
        const telejaugeageData = await telejaugeageRes.json();

        // Récupérer les données modbus
        let modbusUrl = "/api/modbus_data";
        if (currentPuitThresholds && currentPuitThresholds.id) {
            modbusUrl += `?puit_id=${currentPuitThresholds.id}`;
        }
        const modbusRes = await fetch(modbusUrl);
        if (!modbusRes.ok) throw new Error(`HTTP error! status: ${modbusRes.status}`);
        const modbusData = await modbusRes.json();

        // Fusionner les données - prendre tout de Modbus sauf debit_huile de jaugeage
        let combinedData = [...modbusData];
        
        if (telejaugeageData && telejaugeageData.length > 0) {
            // Trouver le jaugeage le plus récent
            const latestJaugeage = telejaugeageData.reduce((latest, current) => {
                const currentDate = new Date(current.date_debut);
                const latestDate = latest ? new Date(latest.date_debut) : 0;
                return currentDate > latestDate ? current : latest;
            }, null);

            if (latestJaugeage) {
                // Mettre à jour le debit_huile dans toutes les entrées Modbus
                combinedData = combinedData.map(modbusItem => ({
                    ...modbusItem,
                    debit_huile: latestJaugeage.debit_huile
                }));
            }
        }

        console.log("Données combinées:", combinedData);

        if (combinedData.length > 0) {
            await updateProductionChart(combinedData);
        }
    } catch (error) {
        console.error("Erreur lors de la mise à jour des données de production:", error);
    }
}

// Récupération des données des puits
async function fetchPuitsData() {
    try {
        const response = await fetch('/api/puits');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        //showNotification("Erreur de chargement de la liste des puits", "error");
        return [];
    }
}

// Récupération des détails d'un puits et RESET complet du dashboard
async function fetchPuitDetails(puitId) {
    await updateLock.acquire();
    try {
        document.getElementById('mainChart').style.opacity = '0.5';
        destroyChart(mainChart); mainChart = null;
        destroyChart(comboGauge); comboGauge = null;
        destroyChart(pressureBars); pressureBars = null;
        destroyChart(productionChart); productionChart = null;
        pressureHistory = [];
        productionHistory = [];
        activeAlerts = [];
        updateAlertIconAndList();

        const mainCtx = document.getElementById('mainChart')?.getContext('2d');
        const gaugeCtx = document.getElementById('comboGauge')?.getContext('2d');
        const pressureCtx = document.getElementById('pressureBars')?.getContext('2d');
        const productionCtx = document.getElementById('productionChart')?.getContext('2d');

        if (mainCtx) initMainChart(mainCtx);
        if (gaugeCtx) initComboGauge(gaugeCtx);
        if (pressureCtx) initPressureBars(pressureCtx);
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

        await fetch(`/api/set_current_puit/${puitId}`, { method: 'POST' });

        // 🔄 Attente avant de lancer les updates pour laisser le backend simuler
        await new Promise(resolve => setTimeout(resolve, 1200)); // 1.2 seconde

        // Affichage selon le statut
        const dashTitle = document.querySelector('.dashboard-title');
        dashTitle.textContent = `SURVEILLANCE DES PARAMÈTRES - ${currentPuitThresholds.nom.toUpperCase()}`;

        if (currentPuitThresholds.status === 'inactif') {
            document.getElementById('inactive-message').style.display = 'block';
            document.getElementById('maintenance-message').style.display = 'none';
            resetCharts();
            document.getElementById('mainChart').style.opacity = '1';
            return;
        }
        if (currentPuitThresholds.status === 'en maintenance') {
            document.getElementById('inactive-message').style.display = 'none';
            document.getElementById('maintenance-message').style.display = 'block';
            resetCharts();
            document.getElementById('mainChart').style.opacity = '1';
            return;
        }

        document.getElementById('inactive-message').style.display = 'none';
        document.getElementById('maintenance-message').style.display = 'none';

        // ✅ Mise à jour du dashboard (données + production)
        await Promise.all([
            updateDashboard(),
            updateProduction()
        ]);

        document.getElementById('mainChart').style.opacity = '1';

    } catch (error) {
        currentPuitThresholds = null;
        document.getElementById('mainChart').style.opacity = '1';
        console.error("Erreur dans fetchPuitDetails:", error);
    } finally {
        updateLock.release();
    }
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
        dateFormat: "d/m/Y",
        time_24hr: true,
        enableTime: false,
        "locale": {
            "firstDayOfWeek": 0, // dimanche premier jour
            "weekdays": {
                "shorthand": ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"],
                "longhand": ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
            },
            "months": {
                "shorthand": ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"],
                "longhand": ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
            }
        }
    });
}
    } catch (error) {
        //showNotification("Erreur d'initialisation de l'application", "error");
    }
});