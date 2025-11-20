/* global bootstrap: false */
(function () {
    'use strict'
    // 初始化 Tooltip
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 动态管理 active 类
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            console.log(`Clicked: ${this.textContent.trim()}`);
        });

        link.addEventListener('mouseover', function () {
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });


    });


})();