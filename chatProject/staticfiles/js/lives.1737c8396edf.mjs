/**
 * 直播列表管理模块
 * 功能：获取直播列表、渲染列表、处理直播间点击事件
 */
class LiveManager {
    /**
     * 从API获取直播列表数据
     * @returns {Promise<Array>} 直播列表数据
     */
    static async fetchLiveList() {
        try {
            const response = await fetch('/api/live/get_all_lives/');
            if (!response.ok) throw new Error('Network response was not ok');
            
            // const data = {
            //     code: 0,
            //     data: {
            //         lives_info: [
            //             {
            //                 room_id: "live_001",
            //                 uid: "user_789",
            //                 username: "游戏主播小王",
            //                 live_num: 1250,
            //                 character_name: "王者荣耀-韩信"
            //             },
            //             {
            //                 room_id: "live_002",
            //                 uid: "user_456",
            //                 username: "聊天主播小美",
            //                 live_num: 892,
            //                 character_name: "情感电台"
            //             },
            //             {
            //                 room_id: "live_003",
            //                 uid: "user_123",
            //                 username: "才艺主播阿杰",
            //                 live_num: 1560,
            //                 character_name: "吉他弹唱"
            //             },
            //             {
            //                 room_id: "live_004",
            //                 uid: "user_321",
            //                 username: "户外探险老李",
            //                 live_num: 2300,
            //                 character_name: "西藏徒步"
            //             },
            //             {
            //                 room_id: "live_005",
            //                 uid: "user_654",
            //                 username: "美食博主娜娜",
            //                 live_num: 1800,
            //                 character_name: "深夜厨房"
            //             }
            //         ]
            //     }
            // };
            const data = await response.json();
            return data.code === 0 ? data.data.lives_info : [];
        } catch (error) {
            console.error('获取直播列表失败:', error);
            return []; // 返回空数组避免前端报错
        }
    }

    /**
     * 渲染直播列表到DOM
     * @param {Array} lives 直播列表数据
     */
    static renderLiveList(lives) {
        const container = document.getElementById('liveListContainer');
        if (!container) {
            console.warn('直播列表容器未找到');
            return;
        }

        // 清空加载状态
        container.innerHTML = '';

        if (lives.length === 0) {
            container.innerHTML = this.getEmptyTemplate();
            return;
        }

        
        // 生成直播列表HTML
        container.innerHTML = lives.map(live => `

    <a href="/live/${live.room_name}/${live.room_id}/" 
       class="nav-link text-white d-flex align-items-center live-room text-nowrap" 
       data-bs-toggle="tooltip" 
       data-bs-placement="right" 
       title="进入${live.username}的直播间"
       data-room-id="${live.room_id}"
       data-room-name="${live.room_name}"
       style="min-width: 0;">  <!-- 添加这行防止flex溢出 -->
        <svg class="bi me-2 flex-shrink-0" width="16" height="16">  <!-- 禁止图标压缩 -->
            <use xlink:href="#people-circle"/>
        </svg>
        <span class="text-truncate flex-grow-1">  <!-- 文字超出显示省略号 -->
            ${live.username} ${live.character_name}
        </span>

    </a>
`).join('');
        // <span class="badge bg-primary ms-2 flex-shrink-0">  <!-- 禁止数字压缩 -->
        //     ${live.live_num}人
        // </span>
        // 初始化动态生成的工具提示
        this.initDynamicTooltips();
        // 绑定点击事件
        this.bindLiveRoomEvents();



    }

    /**
     * 空状态模板
     */
    static getEmptyTemplate() {
        return `
            <div class="text-center py-4 text-white">
                <i class="bi bi-exclamation-circle fs-4"></i>
                <p class="mt-2 mb-0">当前没有直播</p>
            </div>
        `;
    }

    /**
     * 初始化动态生成的Bootstrap工具提示
     */
    static initDynamicTooltips() {
        document.querySelectorAll('.live-room[data-bs-toggle="tooltip"]')
            .forEach(el => new bootstrap.Tooltip(el));
    }

    /**
     * 绑定直播间点击事件
     */
    static bindLiveRoomEvents() {
        document.querySelectorAll('.live-room').forEach(room => {
            room.addEventListener('click', (e) => {
                e.preventDefault();
                const roomId = room.dataset.roomId;
                const roomName = room.dataset.roomName
                this.enterLiveRoom(roomName,roomId);
            });
        });
    }

    /**
     * 进入直播间处理
     * @param {string} roomId 直播间ID
     */
    static enterLiveRoom(roomName,roomId) {
        // 实际项目中这里应该是跳转或打开直播间
        // console.log(`进入直播间: ${roomId}`);
        window.location.href = `/live/${roomName}/${roomId}`;
    }

    /**
     * 模块初始化入口
     */
    static async init() {
        const lives = await this.fetchLiveList();
        this.renderLiveList(lives);

        // 如果需要轮询更新可以在这里添加
        // this.startPolling();
    }

    /**
     * 轮询更新直播列表（可选）
     */
    static startPolling() {
        // 每30秒刷新一次
        this.pollingTimer = setInterval(async () => {
            const lives = await this.fetchLiveList();
            this.renderLiveList(lives);
        }, 30000);
    }
}

// 自动注册初始化（如果直接使用该模块）
if (import.meta.url === document.currentScript?.src) {
    document.addEventListener('DOMContentLoaded', () => LiveManager.init());
}

export default LiveManager;