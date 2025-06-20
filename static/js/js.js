  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(() => {
        const flashMessages = document.querySelector('.flash-messages');
        if (flashMessages) {
            flashMessages.style.transition = "opacity 0.5s ease";
            flashMessages.style.opacity = '0';
            setTimeout(() => flashMessages.remove(), 500);
        }
    }, 3000);
        // Initialisation de la section active au chargement
        loadReports();
showSection('tableSection');

        showSection('formSection');

        // Gestion de la fermeture de la modale
        document.getElementById('overlay').addEventListener('click', closeRapportModal);
        const closeBtn = document.querySelector('.close-rapport');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeRapportModal);
        }
        
    });

    function showSection(sectionId) {
        // Mise à jour des boutons
        document.querySelectorAll('.nav-button').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('onclick')?.includes(sectionId)) {
                btn.classList.add('active');
            }
        });

        // Affichage des sections
        document.getElementById('formSection').style.display = sectionId === 'formSection' ? 'block' : 'none';
        document.getElementById('tableSection').style.display = sectionId === 'tableSection' ? 'block' : 'none';

        if (sectionId === 'tableSection') {
            loadReports();
        }
    }

    async function loadReports() {
        const tbody = document.querySelector('.rapports-table tbody');
        try {
            const response = await fetch('/get_all_reports');
            const data = await response.json();
            tbody.innerHTML = '';

            if (!data.length) {
                tbody.innerHTML = '<tr><td colspan="3">Aucun rapport disponible</td></tr>';
                return;
            }

            data.forEach(rapport => {
                const row = `
    <tr>
        <td class="nom-rapport">${rapport.nom_rapport}</td>
        <td class="date-rapport">${new Date(rapport.date_rapport).toLocaleDateString('fr-FR')}</td>
        <td>
            <button class="open-btn" onclick="openRapport('${rapport.id}')">Ouvrir</button>
            <button class="delete-btn" onclick="deleteRapport('${rapport.id}')">Supprimer</button>
        </td>
    </tr>`;

                tbody.innerHTML += row;
            });
        } catch (error) {
            console.error('Erreur de chargement :', error);
            tbody.innerHTML = '<tr><td colspan="3">Erreur de chargement</td></tr>';
        }
    }
function openRapport(rapportId) {
    fetch(`/get_rapport/${rapportId}`)
    .then(response => response.json())
    .then(data => {
        // Récupérer le formulaire email via fetch
        fetch('/get_email_form_partial')
        .then(res => res.text())
        .then(emailFormHtml => {
            const content = `
                <h2 class="rapport-title">📋 Rapport Technique du Puits</h2>
                <div class="rapport-details">

                    <p><strong>📅 Date du rapport :</strong> ${new Date(data.date_rapport).toLocaleDateString('fr-FR')}</p>

                    <h3>🛢️ Informations de base</h3>
                    <p><strong>Nom du puits :</strong> ${data.nom_puits}</p>
                    <p><strong>ID du puits :</strong> ${data.id_puits}</p>
                    <p><strong>Région :</strong> ${data.region}</p>
                    <p><strong>Localisation GPS :</strong> Latitude ${data.latitude}, Longitude ${data.longitude}</p>
                    <p><strong>Date de mise en service :</strong> ${data.date_mise_en_service}</p>

                    <h3>📈 Paramètres de surveillance</h3>
                    <p><strong>Pression :</strong> ${data.pression} kg/cm³</p>
                    <p><strong>Température :</strong> ${data.temperature} °C</p>
                    <p><strong>Débit :</strong> ${data.debit} m³/h</p>
                    <p><strong>État du puits :</strong> ${data.etat_puits}</p>
                    <p><strong>Nombre d'alertes :</strong> ${data.alertes}</p>

                    <h3>👤 Opérateur</h3>
                    <p><strong>Nom :</strong> ${data.operateur}</p>

                    <h3>📝 Compte-rendu technique</h3>
                    <div class="description-static">
                        ${data.description ? data.description.replace(/\n/g, '<br>') : 'Aucune description fournie.'}
                    </div>
                </div>

                <div class="rapport-actions">
        <a href="/download_pdf/${rapportId}" class="download-link" target="_blank">Télécharger le PDF</a>
    </div>

                ${emailFormHtml}
            `;

            // Injecter contenu dans modal
            document.getElementById('modalContent').innerHTML = content;

            // Afficher modal + overlay
            document.getElementById('overlay').style.display = 'block';
            document.getElementById('rapportModal').style.display = 'block';

            // Injecter les données dans les champs cachés du formulaire email (si les inputs ont des data-field)
            const form = document.querySelector('.email-form');
            if (form) {
                for (const key in data) {
                    const input = form.querySelector(`[data-field="${key}"]`);
                    if (input) input.value = data[key];
                }
            }
        });
    })
    .catch(error => {
        console.error('Erreur de chargement du rapport :', error);
    });
}


    function closeRapportModal() {
        document.getElementById('rapportModal').style.display = 'none';
        document.getElementById('overlay').style.display = 'none';
    }

    function toggleTable() {
        const tableSection = document.getElementById('tableSection');
        tableSection.style.display = tableSection.style.display === 'none' ? 'block' : 'none';
    }
    document.addEventListener('submit', function(e) {
    if (e.target && e.target.classList.contains('email-form')) {
        e.preventDefault();
        const formData = new FormData(e.target);
        fetch(e.target.action, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(result => alert(result.message || 'Email envoyé.'))
        .catch(err => alert('Erreur d\'envoi de l\'email.'));
    }
});

function showSection(section) {
  const formSection = document.getElementById('formSection');
  const tableSection = document.getElementById('tableSection');
  const navSearch = document.getElementById('navSearch');

  if (section === 'formSection') {
    formSection.style.display = 'block';
    tableSection.style.display = 'none';
    navSearch.style.display = 'none';  // cacher barre de recherche
  } else if (section === 'tableSection') {
    formSection.style.display = 'none';
    tableSection.style.display = 'block';
    navSearch.style.display = 'flex';  // afficher barre de recherche (flex pour garder l’alignement)
  }

  // Gestion des boutons actifs
  document.querySelectorAll('.nav-button').forEach(btn => btn.classList.remove('active'));
  if (section === 'formSection') {
    document.querySelector('.nav-button:nth-child(1)').classList.add('active');
  } else {
    document.querySelector('.nav-button:nth-child(2)').classList.add('active');
  }
}
function filterRapports() {
  const input = document.getElementById('searchInput');
  const filter = input.value.trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const rows = document.querySelectorAll('.rapports-table tbody tr');
  let visibleCount = 0;

  rows.forEach(row => {
    // Ignorer la ligne spéciale "aucun rapport trouvé"
    if (row.id === 'noResultRow') return;

    const nom = (row.querySelector('.nom-rapport')?.textContent || '')
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

    const date = (row.querySelector('.date-rapport')?.textContent || '')
      .toLowerCase().trim();

    // Convertir la date en format ISO (aaaa-mm-jj)
    const dateParts = date.split('/');
    const isoDate = dateParts.length === 3 
      ? `${dateParts[2]}-${dateParts[1]}-${dateParts[0]}` 
      : null;

    // Vérifie si la recherche correspond au nom ou à la date
    const match = nom.includes(filter) || 
                  date.includes(filter) || 
                  (isoDate && isoDate.includes(filter));

    row.style.display = match ? 'table-row' : 'none';
    if (match) visibleCount++;
  });

  // Affiche ou cache la ligne "Aucun rapport trouvé"
  const noResultRow = document.getElementById('noResultRow');
  if (noResultRow) {
    noResultRow.style.display = (visibleCount === 0) ? 'table-row' : 'none';
  }
}



function deleteRapport(rapportId) {
    if (confirm("Êtes-vous sûr de vouloir supprimer ce rapport ?")) {
        fetch(`/supprimer_rapport/${rapportId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                // Supprime la ligne du tableau
                const row = document.querySelector(`button.delete-btn[onclick="deleteRapport('${rapportId}')"]`).closest('tr');
                row.remove();

                // Affiche le message de succès
                const messageDiv = document.getElementById('success-message');
                messageDiv.style.display = 'block';

                // Cache le message après 3 secondes
                setTimeout(() => {
                    messageDiv.style.display = 'none';
                }, 3000);
            } else {
                alert("Échec de la suppression du rapport.");
            }
        })
        .catch(error => {
            console.error("Erreur :", error);
            alert("Une erreur est survenue lors de la suppression.");
        });
    }
}
function openPdf(rapportId) {
    const url = `/download_pdf/${rapportId}`;
    window.open(url, '_blank');
}

