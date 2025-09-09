import { generateSimpleAvatar } from './util.mjs';

class StreamerInfoManager {

    static async init(room_id) {
        // 初始化加载
        const data = await this.fetchLiveInfo(room_id);
        const vip_status = await this.vip_check(data.live_info,data.vip_info,data.subscription_info);
        if(!vip_status){
            window.location.href = '/';
        }
        this.updateUI(data.live_info);
        this.initSubscriptionButton(data.subscription_info); //初始化订阅按钮
        this.initFollowButton(data.live_info,data.follow_info); // 新增：初始化关注按钮
        return data.live_info?.room_name
        // 模拟实时更新
        // this.interval = setInterval(async () => {
        //     const info = await this.fetchLiveInfo(roomId);
        //     this.updateViewerCount(info.live_num);
        // }, 5000); // 每5秒更新
    }


    static async fetchLiveInfo(room_id) {

        const response = await fetch(`/api/live/get_live_info/?room_id=${encodeURIComponent(room_id)}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }, // 如果后端不要求此头，可移除
        });
        
        if (!response.ok) throw new Error('Network error');
        const data = await response.json();
        window.GLOBAL_ANCHOR_ID = data?.data?.live_info?.uid


        window.GLOBAL_ROOM_NAME = data?.data?.live_info?.room_name

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

    static async vip_check(live_info,vip_info,subscription_info) {

        if (subscription_info.subscription_status){
            return true
        }


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
                    room_id: live_info.room_id,
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



        // 更新房间描述
        const describeEl = document.querySelector('.streamer-describe');

                const describe = data.describe ;
                if (describe) {
                    // 移除d-none类来显示标题
                    describeEl.classList.remove('d-none');
                    const describeBadge = describeEl.querySelector('span');
                    describeBadge.textContent = describe;
                    
                    // 设置徽章样式
                    describeBadge.className = 'badge text-truncate d-inline-block';
                } else {
                    // 添加d-none类来隐藏标题
                    describeEl.classList.add('d-none');
                }

        }
    }









    // 新增方法：初始化订阅按钮状态和事件
    // static initSubscriptionButton(subscription_info) {
    //     const subBtn = document.querySelector('.subscription-btn');
    //     if (!subBtn) return;

    //     // 根据订阅状态设置按钮
    //     if (window.GLOBAL_SUBSCRIPTRION_STATUS) {
    //         subBtn.disabled = true;
    //         subBtn.textContent = 'subscribed';
    //         subBtn.classList.add('btn-secondary');
    //         subBtn.classList.remove('btn-primary');
    //     } else {
    //         subBtn.disabled = false;
    //         subBtn.textContent = 'subscription';
    //         subBtn.classList.add('btn-primary');
    //         subBtn.classList.remove('btn-secondary');
            
    //         // 绑定点击事件
    //         subBtn.addEventListener('click', () => {
    //             this.handleSubscription(subscription_info);
    //         });
    //     }
    // }


static initSubscriptionButton(subscription_info) {
    const subBtn = document.querySelector('.subscription-btn');
    if (!subBtn) {
        console.error('Subscription button not found');
        return;
    }

    // 设置状态和图标
    const svg = subBtn.querySelector('svg');
    if (window.GLOBAL_SUBSCRIPTRION_STATUS) {
        subBtn.classList.add('subscribed');
        svg.innerHTML = '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill-rule="evenodd" />'; // 实心心
        subBtn.style.pointerEvents = 'none'; // 已订阅禁用点击
        subBtn.onclick = null; // 清除点击事件
    } else {
        subBtn.classList.remove('subscribed');
        svg.innerHTML = '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />'; // 空心心
        subBtn.style.pointerEvents = 'auto'; // 确保可点击
        // 绑定点击事件
        subBtn.onclick = null; // 清除已有事件
        subBtn.onclick = async () => {
            await this.handleSubscription(subscription_info);
            // 订阅成功后重新初始化按钮状态
            this.initSubscriptionButton(subscription_info);
        };
    }
}


    // 新增方法：处理订阅逻辑
    static async handleSubscription(subscription_info) {
        // 检查登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('please log in');
            return;
        }

        // 确认支付
        const confirmed = confirm(`The live-streamer subscription requires you to pay ${subscription_info.amount} diamonds. Are you sure you want to subscribe?`);
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
    // static initFollowButton(live_info,follow_info) {
    //     const followBtn = document.querySelector('.follow2-btn');
    //     if (!followBtn) return;


    //     // 根据关注状态设置按钮
    //     if (follow_info.follow_status) {
    //         followBtn.disabled = false;
    //         followBtn.textContent = 'unfavourite';

    //     } else {
    //         followBtn.disabled = false;
    //         followBtn.textContent = 'favourite';

    //     }
    //     // 添加防抖的点击处理
    //     let isProcessing = false;
    //     followBtn.onclick = async () => {
    //         if (isProcessing) return;
    //         isProcessing = true;
    //         try {
    //             await this.toggleFollow(live_info, follow_info);
    //         } finally {
    //             isProcessing = false;
    //         }
    //     };
    // }
static initFollowButton(live_info, follow_info) {
    const followBtn = document.querySelector('.follow2-btn');
    if (!followBtn) {
        console.error('Follow button not found');
        return;
    }

    // 设置状态和图标
    const svg = followBtn.querySelector('svg');
    if (follow_info.follow_status) {
        followBtn.classList.add('favourited');
        svg.innerHTML = '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill-rule="evenodd" />'; // 实心星
    } else {
        followBtn.classList.remove('favourited');
        svg.innerHTML = '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />'; // 空心星
    }

    // 确保可点击
    followBtn.style.pointerEvents = 'auto';

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
            alert('please log in');
            return;
        }

        const newStatus = !follow_info.follow_status;
        const confirmMsg = newStatus ? 'Are you sure you want to follow this streamer?' : 'Are you sure you want to unfollow this streamer?';
        
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
                    room_id: live_info.room_id,
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



