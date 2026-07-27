// app/static/js/main.js
console.log("SahabatMart System Initialized.");

// Contoh: Validasi form sederhana atau interaksi UI bisa ditambahkan di sini
document.addEventListener('DOMContentLoaded', function() {
    // Inisialisasi tooltip Bootstrap jika ada
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
});