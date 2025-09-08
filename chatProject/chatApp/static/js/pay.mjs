/**
 * 支付模块管理
 */
class PayManager {
    static pollingIntervals = new Map(); // 存储每个订单的轮询定时器

    /**
     * 初始化支付模块
     * @param {string} payModalId 支付模态框ID
     * @param {string} payFormId 支付表单ID
     * @param {string} closeButtonId 关闭按钮ID
     */
    static init(payModalId, payFormId, closeButtonId) {
        const payModal = document.getElementById(payModalId);
        const payForm = document.getElementById(payFormId);
        const closeButton = document.getElementById(closeButtonId);
        const planCards = document.querySelectorAll('.plan-card');
        const selectedAmountInput = document.getElementById('selected-amount');
        let selectedDiamonds = 0;

        if (!payModal || !payForm || !closeButton) {
            console.error('初始化失败：缺少必要元素');
            return;
        }

        planCards.forEach(card => {
            card.addEventListener('click', () => {
                planCards.forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                const amount = card.querySelector('.price').textContent.replace(' USD', '');
                const diamonds = card.querySelector('.diamonds').textContent.replace(' 钻石', '');
                selectedAmountInput.value = amount;
                selectedDiamonds = diamonds;
                console.log(`选中: ${amount} USD, ${diamonds} 钻石`);
            });
        });

        payForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const amount = selectedAmountInput.value;
            if (!amount) {
                alert('请选择一个充值计划！');
                return;
            }

            if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
                alert('please log in');
                return;
            }

            const payload = {
                user_id: window.GLOBAL_USER_ID,
                crypto_amount: parseInt(amount)
            };

            PayManager.submitPayment(payload, payModal, selectedDiamonds)
                .then(response => {
                    console.log('支付响应:', response);
                })
                .catch(error => {
                    alert('充值失败，请重试！');
                    console.error(error);
                });
        });

        closeButton.addEventListener('click', () => {
            PayManager.stopAllPolling(); // 关闭模态框时停止所有轮询
            payModal.style.display = 'none';
        });

        payModal.addEventListener('click', (e) => {
            if (e.target === payModal) {
                PayManager.stopAllPolling(); // 点击外部关闭时停止所有轮询
                payModal.style.display = 'none';
            }
        });
    }

    /**
     * 提交支付请求
     * @param {Object} payload 支付参数
     * @param {HTMLElement} payModal 支付模态框元素
     * @param {number} selectedDiamonds 选中钻石数
     * @returns {Promise<Object>} 服务器响应
     */
    static submitPayment(payload, payModal, selectedDiamonds) {
        return fetch('/api/payment/process_recharge/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) throw new Error('网络错误');
            return response.json();
        })
        .then(data => {
            if (data.code === 0) {
                PayManager.displayQrCode(data, payload, payModal, selectedDiamonds);
            } else {
                alert(`充值失败: ${data.message}`);
            }
            return data;
        });
    }

    /**
     * 获取 CSRF 令牌
     * @returns {string} CSRF 令牌
     */
    static getCsrfToken() {
        let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            return csrfToken.value;
        }
        const name = 'csrftoken';
        const cookieValue = document.cookie.split('; ').find(row => row.startsWith(name + '='));
        return cookieValue ? cookieValue.split('=')[1] : '';
    }

    /**
     * 展示二维码并轮询状态
     * @param {Object} result_data 返回参数
     * @param {Object} payload 接口输入参数
     * @param {HTMLElement} payModal 支付模态框元素
     * @param {number} selectedDiamonds 选中钻石数
     */
    static displayQrCode(result_data, payload, payModal, selectedDiamonds) {
        const paymentWrapper = payModal.querySelector('.payment-wrapper');
        let qrContainer = payModal.querySelector('.qr-container');
        
        if (!qrContainer) {
            qrContainer = document.createElement('div');
            qrContainer.className = 'qr-container';
            qrContainer.style.display = 'none';
            qrContainer.style.position = 'absolute';
            qrContainer.style.top = '0';
            qrContainer.style.left = '0';
            qrContainer.style.width = '100%';
            qrContainer.style.height = '100%';
            qrContainer.style.backgroundColor = '#2d2d2d';
            qrContainer.style.padding = '20px';
            qrContainer.style.boxSizing = 'border-box';
            qrContainer.style.display = 'flex';
            qrContainer.style.flexDirection = 'column';
            qrContainer.style.justifyContent = 'center';
            qrContainer.style.alignItems = 'center';
            payModal.appendChild(qrContainer);
        }

        paymentWrapper.style.display = 'none';
        qrContainer.style.display = 'flex';

        qrContainer.innerHTML = '';

        // const qrImg = document.createElement('img');
        // qrImg.style.maxWidth = '300px';
        // qrImg.style.borderRadius = '8px';

        // const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(
        //     `tron:${result_data.pay_address}?amount=${payload.crypto_amount}`
        // )}`;
        // qrImg.src = qrUrl;
        const qrImg = document.createElement('img');
        qrImg.style.maxWidth = '300px';
        qrImg.style.borderRadius = '8px';
        // 使用 API 返回的 Base64 编码二维码
        qrImg.src = `data:image/png;base64,${result_data.qr_code}`;
        // qrImg.alt = 'QR Code for TRON Payment';



        const networkInfo = document.createElement('p');
        networkInfo.textContent = '请使用 TRON 网络进行支付';
        networkInfo.style.color = '#fff';
        networkInfo.style.marginTop = '10px';

        const addressInfo = document.createElement('p');
        addressInfo.textContent = `接收地址: ${result_data.pay_address}`;
        addressInfo.style.color = '#fff';
        addressInfo.style.marginTop = '10px';
        addressInfo.style.wordBreak = 'break-all';

        const amountInfo = document.createElement('p');
        amountInfo.textContent = `支付金额: ${payload.crypto_amount} USD\n预计获得: ${selectedDiamonds} 钻石`;
        amountInfo.style.color = '#fff';
        amountInfo.style.marginTop = '10px';

        const closeBtn = document.createElement('button');
        closeBtn.textContent = '关闭';
        closeBtn.style.padding = '10px 20px';
        closeBtn.style.background = '#555';
        closeBtn.style.color = '#fff';
        closeBtn.style.border = 'none';
        closeBtn.style.borderRadius = '8px';
        closeBtn.style.cursor = 'pointer';
        closeBtn.style.marginTop = '20px';
        closeBtn.addEventListener('click', () => {
            PayManager.stopPolling(result_data.order_id);
            payModal.style.display = 'none';
        });

        const backBtn = document.createElement('button');
        backBtn.textContent = '返回';
        backBtn.style.padding = '10px 20px';
        backBtn.style.background = '#777';
        backBtn.style.color = '#fff';
        backBtn.style.border = 'none';
        backBtn.style.borderRadius = '8px';
        backBtn.style.cursor = 'pointer';
        backBtn.style.marginTop = '10px';
        backBtn.addEventListener('click', () => {
            qrContainer.style.display = 'none';
            paymentWrapper.style.display = 'block';
            PayManager.stopPolling(result_data.order_id); // 停止当前订单的轮询
        });

        qrContainer.appendChild(qrImg);
        qrContainer.appendChild(networkInfo);
        qrContainer.appendChild(addressInfo);
        qrContainer.appendChild(amountInfo);
        qrContainer.appendChild(closeBtn);
        qrContainer.appendChild(backBtn);

        // 启动轮询检查订单状态
        PayManager.startPolling(result_data.order_id, payModal, selectedDiamonds);
    }

    /**
     * 启动订单状态轮询
     * @param {string} orderId 订单ID
     * @param {HTMLElement} payModal 支付模态框元素
     * @param {number} selectedDiamonds 选中钻石数
     */
    static startPolling(orderId, payModal, selectedDiamonds) {
        if (PayManager.pollingIntervals.has(orderId)) {
            clearInterval(PayManager.pollingIntervals.get(orderId)); // 清除已有轮询
        }
        const intervalId = setInterval(() => {
            PayManager.checkPaymentStatus(orderId, payModal, selectedDiamonds);
        }, 5000); // 每 5 秒检查一次
        PayManager.pollingIntervals.set(orderId, intervalId);
    }

    /**
     * 检查支付状态
     * @param {string} orderId 订单ID
     * @param {HTMLElement} payModal 支付模态框元素
     * @param {number} selectedDiamonds 选中钻石数
     */
    static checkPaymentStatus(orderId, payModal, selectedDiamonds) {
        fetch(`/api/payment/check_payment_status/${orderId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('网络错误');
            return response.json();
        })
        .then(data => {
            if (data.code === 0) {
                console.log(data.status)
                if (data.status === 'completed') {
                    alert(`充值成功！\n订单ID: ${orderId}\n已增加 ${selectedDiamonds} 钻石`);
                    const diamondCount = document.getElementById('diamond');
                    if (diamondCount && !diamondCount.dataset.updated) {
                        diamondCount.textContent = parseInt(diamondCount.textContent) + selectedDiamonds;
                        diamondCount.dataset.updated = 'true'; // 标记已更新
                    }
                    PayManager.stopPolling(orderId);
                    payModal.style.display = 'none';
                } else if (data.status === 'waiting') {
                    console.log(`订单 ${orderId} 仍在等待支付...`);
                } else {
                    alert(`充值状态: ${data.status}`);
                    PayManager.stopPolling(orderId);
                }
            } else {
                alert('查询状态失败，请稍后重试');
                PayManager.stopPolling(orderId);
            }
        })
        .catch(error => {
            console.error('检查状态出错:', error);
            alert('网络错误，请稍后重试');
            PayManager.stopPolling(orderId);
        });
    }

    /**
     * 停止特定订单的轮询
     * @param {string} orderId 订单ID
     */
    static stopPolling(orderId) {
        if (PayManager.pollingIntervals.has(orderId)) {
            clearInterval(PayManager.pollingIntervals.get(orderId));
            PayManager.pollingIntervals.delete(orderId);
        }
    }

    /**
     * 停止所有订单的轮询
     */
    static stopAllPolling() {
        PayManager.pollingIntervals.forEach((intervalId, orderId) => {
            clearInterval(intervalId);
        });
        PayManager.pollingIntervals.clear();
    }
}

export default PayManager;