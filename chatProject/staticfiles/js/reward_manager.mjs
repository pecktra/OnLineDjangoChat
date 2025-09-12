class RewardManager {
    static init() {
        // 初始化模态框
        this.rewardModal = new bootstrap.Modal(document.getElementById('rewardModal'));
        
        // 绑定打赏按钮点击事件
        document.querySelector('.reward-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.checkLoginBeforeReward();
        });
        


        // 绑定表单提交事件
        document.getElementById('rewardForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRewardSubmit();
        });

    }

    static checkLoginBeforeReward() {
        // 检查用户是否登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('please log in first');
            const googleLoginLink = document.getElementById('googleLoginLink');
            if (googleLoginLink) {
                googleLoginLink.click()
            }
            setTimeout(() => {
                document.activeElement?.blur(); // 强制移除当前焦点元素
            }, 0);
            return;
        }
        this.showRewardDialog();
    }

    static showRewardDialog() {
        // 重置表单
        document.getElementById('rewardForm')?.reset();
        this.rewardModal.show();
    }

    static async handleRewardSubmit() {
        // 再次检查登录状态（防止提交时状态变化）
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('登录状态已失效，请重新登录');
            this.rewardModal.hide();
            setTimeout(() => {
                document.activeElement?.blur(); // 强制移除当前焦点元素
            }, 0);
            return;
        }

        const amount = document.getElementById('rewardAmount').value;
        
        if (!amount || amount <= 0) {
            alert('请输入有效的打赏金额');
            setTimeout(() => {
                document.activeElement?.blur(); // 强制移除当前焦点元素
            }, 0);
            return;
        }

        try {
            const response = await fetch('/api/balance/make_donation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    user_id: window.GLOBAL_USER_ID,  // 使用全局用户ID
                    anchor_id: window.GLOBAL_ANCHOR_ID,
                    amount: amount
                })
            });

            const data = await response.json();
            if (data.code === 0) {
                alert('打赏成功！');
                this.rewardModal.hide();
                
                // 更新钻石总数显示
                const diamondElement = document.getElementById('diamond');
                if (diamondElement) {
                    const currentDiamonds = parseInt(diamondElement.textContent) || 0;
                    const rewardAmount = amount;
                    const newDiamondCount = currentDiamonds - rewardAmount;
                    
                    // 确保不会显示负数
                    diamondElement.textContent = Math.max(0, newDiamondCount);
                    
                    // 如果余额很低，可以添加视觉提示
                    // if (newDiamondCount < 10) {
                    //     diamondElement.style.color = '#ff6b6b'; // 变为红色警告
                    //     diamondElement.style.animation = 'pulse 0.5s 2'; // 添加闪烁动画
                    // }
                }
            } else {
                alert(`余额不足`);
            }
        } catch (error) {
            console.error('打赏请求失败:', error);
            alert('打赏请求失败，请稍后再试');
        }
    }

    static getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}
export default RewardManager