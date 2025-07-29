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
    // // 在你的 JavaScript 文件中
    // document.querySelectorAll('.nav-link').forEach(link => {
    //     link.addEventListener('click', function(e) {
    //         // 移除所有 .nav-link 的 .active 类
    //         document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    //         // 移除聚焦
    //         this.blur();
    //     });
    // });

})();