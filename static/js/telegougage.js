// Données de télégougage (initialement vide, sera remplie par les données du serveur)
let telegougageData = [];
let puitsList = []; // Liste des puits disponibles
let currentDetailId = null;

// Éléments du DOM
const openFormButton = document.getElementById('openFormButton');
const formModal = document.getElementById('formModal');
const detailModal = document.getElementById('detailModal');
const telegougageForm = document.getElementById('telegougageForm');
const telegougageItems = document.getElementById('telegougageItems');
const detailContent = document.getElementById('detailContent');
const exportButton = document.getElementById('exportButton');
const deleteButton = document.getElementById('deleteButton');
const emptyState = document.getElementById('emptyState');
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const nomPuitsInput = document.getElementById('nomPuits');
const suggestionsBox = document.getElementById('suggestions');

// Boutons de fermeture
const closeButtons = document.querySelectorAll('.close-button');
const cancelButton = document.getElementById('cancelButton');
const closeDetailButton = document.getElementById('closeDetailButton');

// Charger les données initiales depuis le serveur
function loadInitialData() {
    fetch('/get_telegougage_data')
        .then(response => response.json())
        .then(data => {
            telegougageData = data;
            updateTelegougageList();
        })
        .catch(error => {
            console.error('Erreur lors du chargement des données:', error);
        });
}

// Charger la liste des puits disponibles
function loadPuitsList() {
    fetch('/api/puits')
        .then(response => response.json())
        .then(data => {
            puitsList = data;
        })
        .catch(error => {
            console.error('Erreur lors du chargement de la liste des puits:', error);
        });
}

// Fonction de recherche
function performSearch() {
    const searchTerm = searchInput.value.toLowerCase();
    
    if (!searchTerm) {
        updateTelegougageList();
        return;
    }
    
    const filteredData = telegougageData.filter(item => {
        return (
            item.nom_puits.toLowerCase().includes(searchTerm) ||
            formatDate(item.date_debut).toLowerCase().includes(searchTerm) ||
            formatDate(item.date_fin).toLowerCase().includes(searchTerm)
        );
    });
    
    displaySearchResults(filteredData);
}

// Afficher les résultats de recherche
function displaySearchResults(results) {
    if (results.length === 0) {
        telegougageItems.innerHTML = '';
        telegougageItems.appendChild(emptyState);
        emptyState.style.display = 'block';
        emptyState.innerHTML = `
            <h3>Aucun résultat trouvé</h3>
            <p>Aucun télégougage ne correspond à votre recherche</p>
        `;
        return;
    }
    
    emptyState.style.display = 'none';
    telegougageItems.innerHTML = '';
    
    results.forEach(item => {
        const itemElement = document.createElement('div');
        itemElement.className = 'telegougage-item';
        
        itemElement.innerHTML = `
            <div>${item.nom_puits}</div>
            <div>${formatDate(item.date_debut)}</div>
            <div>${formatDate(item.date_fin)}</div>
            <div class="action-buttons">
                <button class="btn btn-primary btn-sm" data-id="${item.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                    Ouvrir
                </button>
            </div>
        `;
        
        telegougageItems.appendChild(itemElement);
    });
    
    document.querySelectorAll('.btn-primary').forEach(button => {
        button.addEventListener('click', function() {
            const id = parseInt(this.getAttribute('data-id'));
            showDetails(id);
        });
    });
}

// Gestion des suggestions de puits
nomPuitsInput.addEventListener('input', function() {
    const inputVal = this.value.toLowerCase();
    suggestionsBox.innerHTML = '';

    if (inputVal === '') {
        suggestionsBox.style.display = 'none';
        return;
    }

    const matched = puitsList
        .filter(puit => puit.nom.toLowerCase().includes(inputVal))
        .slice(0, 5);

    if (matched.length > 0) {
        matched.forEach(puit => {
            const div = document.createElement('div');
            div.textContent = puit.nom;
            div.addEventListener('click', () => {
                nomPuitsInput.value = puit.nom;
                document.getElementById('puit_id').value = puit.id;
                suggestionsBox.innerHTML = '';
                suggestionsBox.style.display = 'none';
            });
            suggestionsBox.appendChild(div);
        });
        suggestionsBox.style.display = 'block';
    } else {
        suggestionsBox.style.display = 'none';
    }
});

// Masquer les suggestions si clic à l'extérieur
document.addEventListener('click', function(e) {
    if (!nomPuitsInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
        suggestionsBox.style.display = 'none';
    }
});

// Événements de recherche
searchButton.addEventListener('click', performSearch);
searchInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
        performSearch();
    }
});

// Gestion des modals
openFormButton.addEventListener('click', () => {
    formModal.style.display = 'block';
});

function closeModal(modal) {
    modal.style.display = 'none';
}

closeButtons.forEach(button => {
    button.addEventListener('click', function() {
        closeModal(this.closest('.modal'));
    });
});

cancelButton.addEventListener('click', () => closeModal(formModal));
closeDetailButton.addEventListener('click', () => closeModal(detailModal));

window.addEventListener('click', (e) => {
    if (e.target === formModal) closeModal(formModal);
    if (e.target === detailModal) closeModal(detailModal);
});

// Enregistrer un nouveau télégougage
telegougageForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const newEntry = {
        nom_puits: document.getElementById('nomPuits').value,
        date_debut: document.getElementById('dateDebut').value,
        date_fin: document.getElementById('dateFin').value,
        pression_pip: parseFloat(document.getElementById('pressionPip').value),
        pression_manifold: parseFloat(document.getElementById('pressionManifold').value),
        temperature_pipe: parseFloat(document.getElementById('temperaturePipe').value),
        temperature_tete: parseFloat(document.getElementById('temperatureTete').value),
        pression_tete: parseFloat(document.getElementById('pressionTete').value),
        debit_huile: parseFloat(document.getElementById('debitHuil').value),
        gor: parseFloat(document.getElementById('gor').value),
        glr: parseFloat(document.getElementById('glr').value),
        taux_eau: parseFloat(document.getElementById('eau').value),
        eau_inj: parseFloat(document.getElementById('eauinj').value),
        puit_id: document.getElementById('puit_id').value
    };

    fetch('/enregistrer_donnees', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(newEntry)
    })
    .then(response => {
        if (!response.ok) throw new Error('Erreur lors de l\'enregistrement');
        return response.json();
    })
    .then(data => {
        loadInitialData();
        telegougageForm.reset();
        closeModal(formModal);
    })
    .catch(error => {
        console.error('Erreur:', error);
        alert("Erreur lors de l'enregistrement");
    });
});

// Supprimer un télégougage
deleteButton.addEventListener('click', () => {
    if (currentDetailId && confirm("Voulez-vous vraiment supprimer ce télégougage ?")) {
        fetch(`/supprimer_telegougage/${currentDetailId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) throw new Error('Erreur lors de la suppression');
            return response.json();
        })
        .then(data => {
            loadInitialData();
            closeModal(detailModal);
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert("Erreur lors de la suppression");
        });
    }
});

// Mettre à jour la liste des télégougage
function updateTelegougageList() {
    if (telegougageData.length === 0) {
        telegougageItems.innerHTML = '';
        telegougageItems.appendChild(emptyState);
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    telegougageItems.innerHTML = '';
    
    telegougageData.forEach(item => {
        const itemElement = document.createElement('div');
        itemElement.className = 'telegougage-item';
        
        itemElement.innerHTML = `
            <div>${item.nom_puits}</div>
            <div>${formatDate(item.date_debut)}</div>
            <div>${formatDate(item.date_fin)}</div>
            <div class="action-buttons">
                <button class="btn btn-primary btn-sm" data-id="${item.id}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                    Ouvrir
                </button>
            </div>
        `;
        
        telegougageItems.appendChild(itemElement);
    });
    
    document.querySelectorAll('.btn-primary').forEach(button => {
        button.addEventListener('click', function() {
            const id = parseInt(this.getAttribute('data-id'));
            showDetails(id);
        });
    });
}

// Afficher les détails d'un télégougage
function showDetails(id) {
    currentDetailId = id;
    const item = telegougageData.find(item => item.id === id);
    
    if (item) {
        detailContent.innerHTML = `
            <div class="detail-item"><span class="detail-label">Nom du Puits:</span> ${item.nom_puits}</div>
            <div class="detail-item"><span class="detail-label">Date de Début:</span> ${formatDateTime(item.date_debut)}</div>
            <div class="detail-item"><span class="detail-label">Date de Fin:</span> ${formatDateTime(item.date_fin)}</div>
            <div class="detail-item"><span class="detail-label">Pression PIP (kg/cm²):</span> ${item.pression_pip}</div>
            <div class="detail-item"><span class="detail-label">Pression Manifold (kg/cm²):</span> ${item.pression_manifold}</div>
            <div class="detail-item"><span class="detail-label">Pression Tête (kg/cm²):</span> ${item.pression_tete}</div>
            <div class="detail-item"><span class="detail-label">Température Pipe (°C):</span> ${item.temperature_pipe}</div>
            <div class="detail-item"><span class="detail-label">Température Tête (°C):</span> ${item.temperature_tete}</div>
            <div class="detail-item"><span class="detail-label">Débit Huile (m³/h):</span> ${item.debit_huile}</div>
            <div class="detail-item"><span class="detail-label">GOR (m³/m³):</span> ${item.gor}</div>
            <div class="detail-item"><span class="detail-label">GLR (m³/m³):</span> ${item.glr}</div>
            <div class="detail-item"><span class="detail-label">Eau (m³/h):</span> ${item.taux_eau}</div>
            <div class="detail-item"><span class="detail-label">Eau_inj (m³/h):</span> ${item.eau_inj}</div>
        `;
        
        detailModal.style.display = 'block';
    }
}

// Exporter en Excel
exportButton.addEventListener('click', () => {
    if (currentDetailId) {
        const item = telegougageData.find(item => item.id === currentDetailId);
        if (item) {
            exportToExcel(item);
        }
    }
});

function exportToExcel(data) {
    const wb = XLSX.utils.book_new();
    const excelData = [
        ["Nom du Puits", data.nom_puits],
        ["Date de Début", formatDateTime(data.date_debut)],
        ["Date de Fin", formatDateTime(data.date_fin)],
        ["Pression PIP", data.pression_pip],
        ["Pression Manifold", data.pression_manifold],
        ["Température Pipe", data.temperature_pipe],
        ["Température Tête", data.temperature_tete],
        ["Pression Tête", data.pression_tete],
        ["Débit Huile", data.debit_huile],
        ["GOR", data.gor],
        ["GLR", data.glr],
        ["Taux d'eau", data.taux_eau],
        ["Eau_Inj", data.eau_inj]
    ];
    
    const ws = XLSX.utils.aoa_to_sheet(excelData);
    XLSX.utils.book_append_sheet(wb, ws, "Télégougage");
    XLSX.writeFile(wb, `telegougage_${data.nom_puits}_${formatDateForExport(data.date_debut)}.xlsx`);
}

// Fonctions utilitaires
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('fr-FR');
}

function formatDateForExport(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().split('T')[0].replace(/-/g, '');
}

// Export global des données
document.getElementById('exportAllButton').addEventListener('click', function() {
    if (telegougageData.length === 0) {
        alert("Aucune donnée à exporter !");
        return;
    }

    const data = telegougageData.map(item => ({
        "Nom du Puits": item.nom_puits,
        "Date de Début": formatDateTime(item.date_debut),
        "Date de Fin": formatDateTime(item.date_fin),
        "P_PIP": item.pression_pip,
        "P_MANIFOLD": item.pression_manifold,
        "T_Pipe": item.temperature_pipe,
        "T_Tête": item.temperature_tete,
        "P_Tete": item.pression_tete,
        "D_HUILE": item.debit_huile,
        "GOR": item.gor,
        "GLR": item.glr,
        "EAU": item.taux_eau,
        "EAU_INJ": item.eau_inj
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, "Télégougage Data");
    const exportDate = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    XLSX.writeFile(wb, `export_telegougage_${exportDate}.xlsx`);
});

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    loadInitialData();
    loadPuitsList(); // Charger la liste des puits disponibles
});