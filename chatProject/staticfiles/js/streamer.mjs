import { generateSimpleAvatar } from './util.mjs';
class StreamerInfoManager {

    static async init(room_name) {
        // 初始化加载
        const data = await this.fetchLiveInfo(room_name);
        const vip_status = await this.vip_check(data.live_info,data.vip_info);
        if(!vip_status){
            window.location.href = '/';
        }
        this.updateUI(data.live_info);
        this.initSubscriptionButton(data.subscription_info); //初始化订阅按钮
        this.initFollowButton(data.live_info,data.follow_info); // 新增：初始化关注按钮
        // 模拟实时更新
        // this.interval = setInterval(async () => {
        //     const info = await this.fetchLiveInfo(roomId);
        //     this.updateViewerCount(info.live_num);
        // }, 5000); // 每5秒更新
    }


    static async fetchLiveInfo(room_name) {

        const response = await fetch(`/api/live/get_live_info/?room_name=${encodeURIComponent(room_name)}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }, // 如果后端不要求此头，可移除
        });
        
        if (!response.ok) throw new Error('Network error');
        const data = await response.json();
        window.GLOBAL_ANCHOR_ID = data?.data?.live_info?.uid

        window.GLOBAL_SUBSCRIPTRION_STATUS = data?.data?.subscription_info?.subscription_status
        return data.code === 0 ? data.data : null;
        // 模拟数据
        // const mockData = {
        //     code: 0,
        //     data: {
        //         live_info: {
        //             room_id: roomId,
        //             room_name:roomName
        //             uid: "streamer_123",
        //             username: "里斯",
        //             live_num: Math.floor(Math.random() * 5000) + 100, // 随机100-5100人
        //             character_name: "警官奥斯汀",
        //             live_status: true,
        //             avatar_url: "https://i.imgur.com/JQWUQZG.jpg"
        //         }
        //     }
        // };
        // return mockData.data.live_info;
    }

    static updateViewerCount(count) {
        const counter = document.getElementById('viewerCount');
        if (counter) {
            // 添加动画效果
            counter.classList.add('text-success');
            setTimeout(() => {
                counter.textContent = count.toLocaleString();
                counter.classList.remove('text-success');
            }, 300);
        }
    }

    static async vip_check(live_info,vip_info) {
        if(vip_info.amount === 0){
            return true
        }


        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('请登录');
            return false;
        }
        if(vip_info.vip_status){
            return true;
        }


        // 如果不是VIP，显示支付确认对话框
        const confirmed = confirm(`开通VIP需要支付${vip_info.amount}钻石，确认支付吗？`);
        if (!confirmed) {
            return false;
        }
        
        try {
            // 调用支付接口
            const response = await fetch('/api/live/pay_vip_coin/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    user_id: window.GLOBAL_USER_ID,
                    anchor_id:live_info.uid,
                    room_name: live_info.room_name,
                    amount: vip_info.amount
                })
            });
            
            const data = await response.json();
            if (data.code === 0) {
                alert('支付成功');
                return true;
            } else {
                // alert(`支付失败: ${data.message || '未知错误'}`);
                alert(`余额不足，请充值`);
                return false;
            }
        } catch (error) {
            console.error('VIP支付请求失败:', error);
            alert('支付请求失败，请稍后再试');
            return false;
        }

    }

    static updateUI(data) {


        // 更新主播信息
        if (data) {
            // 头像
            const avatar = document.querySelector('.streamer-details img');
            avatar.src = generateSimpleAvatar(data.username);

            const avatar1 = document.querySelector('.live-user-header img');
            avatar1.src = generateSimpleAvatar(data.username);

            // 名字
            const nameEl = document.getElementById('streamerName');
            if (nameEl) nameEl.textContent = data.username;

            // 名字
            const nameEl1 = document.getElementById('streamerName1');
            if (nameEl1) nameEl1.textContent = data.username;

            // 观看人数
            this.updateViewerCount(data.live_num);

            // 直播状态
            const statusIndicator = document.querySelector('.streamer-details .bi-circle-fill');
            if (statusIndicator) {
                statusIndicator.classList.toggle('text-success', data.live_status);
                statusIndicator.classList.toggle('text-danger', !data.live_status);
            }


        // 更新房间标题
        const titleEl = document.querySelector('.streamer-title');

                const title = data.title ;
                if (title) {
                    // 移除d-none类来显示标题
                    titleEl.classList.remove('d-none');
                    const titleBadge = titleEl.querySelector('span');
                    titleBadge.textContent = title;
                    
                    // 设置徽章样式
                    titleBadge.className = 'badge text-truncate d-inline-block';
                } else {
                    // 添加d-none类来隐藏标题
                    titleEl.classList.add('d-none');
                }

        


        }
    }






    // 新增方法：初始化订阅按钮状态和事件
    static initSubscriptionButton(subscription_info) {
        const subBtn = document.querySelector('.subscription-btn');
        if (!subBtn) return;

        // 根据订阅状态设置按钮
        if (window.GLOBAL_SUBSCRIPTRION_STATUS) {
            subBtn.disabled = true;
            subBtn.textContent = '已订阅';
            subBtn.classList.add('btn-secondary');
            subBtn.classList.remove('btn-primary');
        } else {
            subBtn.disabled = false;
            subBtn.textContent = '订阅';
            subBtn.classList.add('btn-primary');
            subBtn.classList.remove('btn-secondary');
            
            // 绑定点击事件
            subBtn.addEventListener('click', () => {
                this.handleSubscription(subscription_info);
            });
        }
    }

    // 新增方法：处理订阅逻辑
    static async handleSubscription(subscription_info) {
        // 检查登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('请先登录');
            return;
        }

        // 确认支付
        const confirmed = confirm(`订阅主播需要支付${subscription_info.amount}钻石，确认订阅吗？`);
        if (!confirmed) return;

        try {
            const response = await fetch('/api/subscription/subscribe_to_anchor/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    anchor_id: window.GLOBAL_ANCHOR_ID,
                    user_id: window.GLOBAL_USER_ID,
                    amount: subscription_info.amount
                })
            });

            const data = await response.json();
            if (data.code === 0) {
                alert('订阅成功！');
                window.GLOBAL_SUBSCRIPTRION_STATUS = true;
                this.initSubscriptionButton(subscription_info); // 刷新按钮状态
            } else {
                alert(`订阅失败: ${data.message || '未知错误'}`);
            }
        } catch (error) {
            console.error('订阅请求失败:', error);
            alert('订阅请求失败，请稍后再试');
        }
    }











    //初始化关注按钮状态和事件
    static initFollowButton(live_info,follow_info) {
        const followBtn = document.querySelector('.follow2-btn');
        if (!followBtn) return;


        // 根据关注状态设置按钮
        if (follow_info.follow_status) {
            followBtn.disabled = false;
            followBtn.textContent = '取消关注';

        } else {
            followBtn.disabled = false;
            followBtn.textContent = '关注';

        }
        // 添加防抖的点击处理
        let isProcessing = false;
        followBtn.onclick = async () => {
            if (isProcessing) return;
            isProcessing = true;
            try {
                await this.toggleFollow(live_info, follow_info);
            } finally {
                isProcessing = false;
            }
        };
    }

    // 新增方法：处理关注/取消关注
    static async toggleFollow(live_info,follow_info) {
        // 检查登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('请先登录');
            return;
        }

        const newStatus = !follow_info.follow_status;
        const confirmMsg = newStatus ? '确定要关注该主播吗？' : '确定要取消关注该主播吗？';
        
        if (!confirm(confirmMsg)) return;
        
        try {
            const response = await fetch('/api/follow_live/toggle_follow_room/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    user_id: window.GLOBAL_USER_ID,
                    room_name: live_info.room_name,
                    follow_status: newStatus
                })
            });

            const data = await response.json();
            if (data.code === 0) {
                alert(newStatus ? '关注成功！' : '已取消关注');
                follow_info.follow_status = newStatus; // 更新状态
                this.initFollowButton(live_info,follow_info); // 刷新按钮
            } else {
                alert(`操作失败: ${data.message || '未知错误'}`);
            }
        } catch (error) {
            console.error('关注操作失败:', error);
            alert('操作失败，请稍后再试');
        }
    }














    static stop() {
        clearInterval(this.interval);
    }

    static getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
}

export default StreamerInfoManager



