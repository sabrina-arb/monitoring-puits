document.addEventListener("DOMContentLoaded", function () {
    // Vérifie si le formulaire a été soumis pour afficher la modal
    if (document.getElementById("rapportModal")) {
        document.getElementById("overlay").style.display = "block";
        document.getElementById("rapportModal").style.display = "block";
    }
    
    // Gestion de la fermeture de la modal
    const overlay = document.getElementById("overlay");
    if (overlay) {
        overlay.addEventListener("click", function() {
            document.getElementById("overlay").style.display = "none";
            document.getElementById("rapportModal").style.display = "none";
        });
    }
});
function closeRapportModal() {
    document.getElementById('rapportModal').style.display = 'none';
    document.getElementById('overlay').style.display = 'none';
}
