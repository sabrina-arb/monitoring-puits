// Variables globales
let mainChart, comboGauge, pressureBars;
let pressureHistory = [];
const MAX_HISTORY = 5; // Nombre maximum de points à afficher

// Formatage du temps
function formatTime(date) {
    if (!date) return '';
    const d = new Date(date);
    return isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
}

// Mise à jour de l'heure
function updateTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = 
        `${formatTime(now)} - ${now.toLocaleDateString()}`;
}

// Initialisation des graphiques
function initCharts() {
    initMainChart();
    initComboGauge();
    initPressureBars();
    setupPuitSearch();
    setInterval(updateTime, 2000);
    updateTime();
}

// 1. Graphique principal (Pression uniquement)
function initMainChart() {
    const ctx = document.getElementById('mainChart').getContext('2d');
    
    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'PRESSION (bar)',
                    data: [],
                    borderColor: '#FF2E63',
                    backgroundColor: 'rgba(255, 46, 99, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'TEMPERATURE (°C)',
                    data: [],
                    borderColor: '#FFA500',
                    backgroundColor: 'rgba(255, 165, 0, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y1'
                },
                {
                    label: 'DEBIT (m³/h)',
                    data: [],
                    borderColor: '#4BC0C0',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#2A2A3D',
                        font: {
                            family: 'Montserrat',
                            size: 12,
                            weight: '600'
                        },
                        padding: 20
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        callback: function(value) {
                            return formatTime(this.getLabelForValue(value));
                        },
                        color: '#6B7280',
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 10
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: '#6B7280'
                    },
                    title: {
                        display: true,
                        text: 'Pression (bar)',
                        color: '#2A2A3D'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        color: '#FFA500'
                    },
                    title: {
                        display: true,
                        text: 'Température (°C)',
                        color: '#FFA500'
                    }
                },
                y2: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        color: '#4BC0C0'
                    },
                    title: {
                        display: true,
                        text: 'Débit (m³/h)',
                        color: '#4BC0C0'
                    },
                    // Positionne cet axe après y1
                    afterFit: function(scale) {
                        scale.right += 50;
                    }
                }
            }
        }
    });
}


// 2. Jauge circulaire (GOR, GLR, Taux d'eau)
function initComboGauge() {
    const ctx = document.getElementById('comboGauge')?.getContext('2d');
    if (!ctx) return;

    comboGauge = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['GOR', 'GLR', 'Taux Eau'],
            datasets: [{
                data: [30, 30, 40], // Valeurs par défaut
                backgroundColor: ['#00FFA3', '#9C27B0', '#00D4FF']
            }]
        },
        options: {
            cutout: '70%'
        }
    });
}

// 3. Barres groupées (Pression Pip/Tête)
function initPressureBars() {
    const ctx = document.getElementById('pressureBars').getContext('2d');
    
    pressureBars = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'PIPELINE',
                    backgroundColor: '#2962FF',
                    data: [],
                    barThickness: 30
                },
                {
                    label: 'TÊTE',
                    backgroundColor: '#00E5FF',
                    data: [],
                    barThickness: 30
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    position: 'top',
                    labels: {
                        color: '#2A2A3D',
                        font: {
                            family: 'Montserrat',
                            size: 12,
                            weight: '600'
                        },
                        padding: 20
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return formatTime(context[0].label);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6B7280',
                        callback: function(value) {
                            return formatTime(this.getLabelForValue(value));
                        },
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 6
                    }
                },
                y: { 
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: '#6B7280'
                    },
                    title: {
                        display: true,
                        text: 'Pression (bar)',
                        color: '#2A2A3D'
                    }
                }
            }
        }
    });
}

// Mise à jour des données
async function updateDashboard() {
    try {
        const res = await fetch("/api/modbus_data");
        const data = await res.json();
        const lastData = data[data.length - 1] || {};
        
        updateMainChart(data);
        updateComboGauge(lastData);
        updatePressureBars(lastData);
        
    } catch (error) {
        console.error("Erreur de mise à jour:", error);
        // Fallback avec des données de test
        const testData = [{
            timestamp: new Date().toISOString(),
            pression: 10 + Math.random() * 5,
            pression_pip: 15 + Math.random() * 3,
            pression_tete: 10 + Math.random() * 2,
            gor: 30,
            glr: 30,
            taux_eau: 40
        }];
        updateMainChart(testData);
        updateComboGauge(testData[0]);
        updatePressureBars(testData[0]);
    }
}

function updateMainChart(data) {
    if (!mainChart) return;
    
    mainChart.data.labels = data.map(d => d.timestamp);
    mainChart.data.datasets[0].data = data.map(d => d.pression || 0);
    mainChart.data.datasets[1].data = data.map(d => d.temperature || 0);
    mainChart.data.datasets[2].data = data.map(d => d.debit || 0);
    mainChart.update();
}  


function updateComboGauge(data) {
    if (!comboGauge) return;
    
    comboGauge.data.datasets[0].data = [
        data.gor || 0,
        data.glr || 0, 
        data.taux_eau || 0
    ];
    comboGauge.update();
}

function updatePressureBars(data) {
    if (!pressureBars) return;
    
    const now = new Date();
    pressureHistory.push({
        timestamp: now,
        pip: data.pression_pip || 0,
        tete: data.pression_tete || 0
    });
    
    if (pressureHistory.length > MAX_HISTORY) {
        pressureHistory.shift();
    }
    
    pressureBars.data.labels = pressureHistory.map(d => d.timestamp);
    pressureBars.data.datasets[0].data = pressureHistory.map(d => d.pip);
    pressureBars.data.datasets[1].data = pressureHistory.map(d => d.tete);
    pressureBars.update();
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    updateDashboard();
    setInterval(updateDashboard, 2000);
    
    // Initialisation du calendrier s'il existe
    if (document.getElementById("calendar")) {
        flatpickr("#calendar", {
            inline: true,
            locale: "fr",
            dateFormat: "Y-m-d"
        });
    }
});


function setupPuitSearch() {
    const searchInput = document.getElementById('puit-search');
    const resultsContainer = document.getElementById('puit-results');

    searchInput.addEventListener('input', async function() {
        const query = this.value.trim();
        
        if (query.length < 2) {
            resultsContainer.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/api/search_puits?q=${encodeURIComponent(query)}`);
            const puits = await response.json();
            
            resultsContainer.innerHTML = puits.map(puit => `
                <div class="puit-result" data-id="${puit.id}">
                    ${puit.nom} (${puit.region || 'N/A'})
                </div>
            `).join('');

            // Ajoutez les écouteurs d'événements aux résultats
            document.querySelectorAll('.puit-result').forEach(item => {
                item.addEventListener('click', function() {
                    searchInput.value = this.textContent.trim();
                    resultsContainer.innerHTML = '';
                    loadPuitData(this.dataset.id);
                });
            });
        } catch (error) {
            console.error("Erreur de recherche:", error);
        }
    });
}

// Fonction pour charger les données d'un puits spécifique
async function loadPuitData(puitId) {
    try {
        // Récupérer les seuils du puits
        const res = await fetch(`/api/puit_seuils/${puitId}`);
        const seuils = await res.json();
        
        // Mettre à jour le dashboard avec les seuils
        updateDashboardWithSeuils(seuils);
    } catch (error) {
        console.error("Erreur de chargement des seuils:", error);
    }
}

// Modifiez updateDashboard pour inclure les seuils
async function updateDashboard(seuils = null) {
    try {
        const res = await fetch("/api/modbus_data");
        const data = await res.json();
        const lastData = data[data.length - 1] || {};
        
        updateMainChart(data, seuils);
        updateComboGauge(lastData, seuils);
        updatePressureBars(lastData);
        
    } catch (error) {
        console.error("Erreur de mise à jour:", error);
        // Fallback avec des données de test
        const testData = [{
            timestamp: new Date().toISOString(),
            pression: 10 + Math.random() * 5,
            pression_pip: 15 + Math.random() * 3,
            pression_tete: 10 + Math.random() * 2,
            gor: 30,
            glr: 30,
            taux_eau: 40
        }];
        updateMainChart(testData, seuils);
        updateComboGauge(testData[0], seuils);
        updatePressureBars(testData[0]);
    }
}


