// gamificacao.js - Motor de Engajamento SAT
document.addEventListener("DOMContentLoaded", function() {
    
    // 1. Animação da Barra de XP (Módulo 2.3) [cite: 41, 43]
    const xpFill = document.querySelector(".xp-progress");
    if (xpFill) {
        // Pega o valor enviado pelo Django através do atributo data-width
        const targetWidth = xpFill.getAttribute("data-width") || 0;
        
        // Timeout para garantir que a animação ocorra após o carregamento [cite: 17]
        setTimeout(() => {
            xpFill.style.width = targetWidth + "%";
            xpFill.style.transition = "width 1.5s cubic-bezier(0.4, 0, 0.2, 1)";
        }, 300);
    }

    // 2. Sistema de Radar para Check-in GPS (Módulo 5.2) 
    const btnCheckin = document.querySelector(".btn-radar");
    if (btnCheckin) {
        btnCheckin.addEventListener("click", function() {
            if ("geolocation" in navigator) {
                btnCheckin.disabled = true;
                btnCheckin.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Validando GPS...`;
                
                // O App verifica o GPS conforme o escopo 
                navigator.geolocation.getCurrentPosition(onSuccess, onError, {
                    enableHighAccuracy: true,
                    timeout: 5000
                });
            } else {
                alert("GPS não suportado pelo seu navegador.");
            }
        });
    }
});

function onSuccess(position) {
    const lat = position.coords.latitude;
    const lon = position.coords.longitude;
    
    // Aqui faremos a chamada para o seu backend para validar se o torcedor está no estádio 
    console.log(`Localização: ${lat}, ${lon}`);
    // fetch('/api/checkin-georreferenciado/', { ... });
}

function onError(error) {
    const btnCheckin = document.querySelector(".btn-radar");
    btnCheckin.disabled = false;
    btnCheckin.innerHTML = `<i class="bi bi-pin-map-fill me-2"></i>FAZER CHECK-IN (GPS)`;
    alert("Erro ao capturar localização. Verifique as permissões de GPS.");
}