class StreamerInfoManager {
    static async fetchLiveInfo(roomId) {

        // const response = await fetch('/api/live/get_live_info', {
        //     method: 'GET',
        //     headers: {
        //         'Content-Type': 'application/json',
        //         'room_id': roomId  // 通过header或URL参数传递
        //     }
        // });
        //
        // if (!response.ok) throw new Error('Network error');
        // const data = await response.json();
        //
        // return data.code === 0 ? data.data.live_info : null;
        // 模拟数据
        const mockData = {
            code: 0,
            data: {
                live_info: {
                    room_id: roomId,
                    uid: "streamer_123",
                    username: "里斯",
                    live_num: Math.floor(Math.random() * 5000) + 100, // 随机100-5100人
                    character_name: "警官奥斯汀",
                    live_status: true,
                    avatar_url: "https://i.imgur.com/JQWUQZG.jpg"
                }
            }
        };
        return mockData.data.live_info;
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

    static async init(roomId) {
        // 初始化加载
        const liveInfo = await this.fetchLiveInfo(roomId);
        this.updateUI(liveInfo);

        // 模拟实时更新
        // this.interval = setInterval(async () => {
        //     const info = await this.fetchLiveInfo(roomId);
        //     this.updateViewerCount(info.live_num);
        // }, 5000); // 每5秒更新
    }

    static updateUI(data) {
        // 更新主播信息
        if (data) {
            // 头像
            const avatar = document.querySelector('.streamer-details img');
            if (avatar) avatar.src = data.avatar_url;

            // 名字
            const nameEl = document.getElementById('streamerName');
            if (nameEl) nameEl.textContent = data.character_name;

            // 观看人数
            this.updateViewerCount(data.live_num);

            // 直播状态
            const statusIndicator = document.querySelector('.streamer-details .bi-circle-fill');
            if (statusIndicator) {
                statusIndicator.classList.toggle('text-success', data.live_status);
                statusIndicator.classList.toggle('text-danger', !data.live_status);
            }
        }
    }

    static stop() {
        clearInterval(this.interval);
    }
}

export default StreamerInfoManager



