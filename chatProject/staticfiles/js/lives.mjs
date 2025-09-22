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

            const data = await response.json();
            return data.code === 0 ? data.data.lives_info : [];
        } catch (error) {
            console.error('获取直播列表失败:', error);
            return []; // 返回空数组避免前端报错
        }
    }


            static renderLiveList_sub(livesInfo) {
                const container = document.getElementById('liveListContainer');
                if (!container) {
                    console.warn('Live broadcast list container not found');
                    return;
                }

                // 清空容器
                container.innerHTML = '';

                if (livesInfo.length === 0) {
                    container.innerHTML = this.getEmptyTemplate();
                    return;
                }

                // 生成直播列表HTML
                livesInfo.forEach(liveInfo => {
                    const userCard = document.createElement('div');
                    userCard.className = 'live-card';
                    
                    // 用户头部信息（可点击展开）
                    const userHeader = document.createElement('div');
                    userHeader.className = 'user-header';
                    
                    const userInfoDiv = document.createElement('div');
                    userInfoDiv.className = 'user-info';
                    
                    userInfoDiv.innerHTML = `
                        <div class="user-avatar">${liveInfo.username ? liveInfo.username.charAt(0).toUpperCase() : 'U'}</div>
                        <div>
                            <div>${liveInfo.username}</div>
                            <div class="subscription-info">
                                subscription: ${liveInfo.subscription_date.split(' ')[0]} to ${liveInfo.subscription_end_date.split(' ')[0]}
                            </div>
                        </div>
                    `;
                    
                    const toggleIcon = document.createElement('div');
                    toggleIcon.className = 'toggle-icon';
                    toggleIcon.innerHTML = '<i class="fas fa-chevron-down"></i>';
                    
                    userHeader.appendChild(userInfoDiv);
                    userHeader.appendChild(toggleIcon);
                    
                    // 房间列表
                    const roomList = document.createElement('div');
                    roomList.className = 'room-list';
                    
                    liveInfo.anchor_room_infos.forEach(room => {
                        let roomInfo = null;
                        let diamondBadge = '';
                        
                        try {
                            roomInfo = room.room_info ? room.room_info : null;
                            
                            // 如果是VIP房间且钻石数量>0
                            if (roomInfo && roomInfo.room_type === 1 && roomInfo.coin_num > 0) {
                                diamondBadge = `
                                    <span class="badge bg-primary ms-2 flex-shrink-0">
                                        <i class="fas fa-gem me-1" style="font-size: 0.8em;"></i>
                                        vip ${roomInfo.coin_num}
                                    </span>
                                `;
                            }
                        } catch (e) {
                            console.error('room_info error:', e);
                        }
                        
                        const roomItem = document.createElement('a');
                        roomItem.href = `/live/${room.room_id}/`;

                        roomItem.target = '_blank';
                        roomItem.className = 'room-item';
                        roomItem.innerHTML = `
                            <div class="room-icon">
                                <i class="fas fa-video"></i>
                            </div>
                            <div class="room-info">
                                <div class="room-details">${room.character_name}</div>
                                <div class="room-details">${room.character_date}</div>
                            </div>
                            ${diamondBadge}
                        `;
                        
                        roomList.appendChild(roomItem);
                    });
                    
                    // 添加点击展开/收缩功能
                    userHeader.addEventListener('click', () => {
                        roomList.classList.toggle('expanded');
                        toggleIcon.classList.toggle('expanded');
                    });
                    
                    userCard.appendChild(userHeader);
                    userCard.appendChild(roomList);
                    container.appendChild(userCard);
                });
            }

    //<div class="room-details">${this.convertTo24Hour(room.character_date)}</div>
static renderLiveList_home(livesInfo) {
    const homeContainer = document.getElementById('homeLiveListContainer');
    if (!homeContainer) {
        console.warn('首页直播容器未找到');
        return;
    }

    const mediaUrl = window.MEDIA_URL || '/media/';

    homeContainer.innerHTML = livesInfo.length === 0
        ? this.getEmptyTemplate()
        : '';

    livesInfo.forEach((live, index) => {
        // 创建卡片 - 171px宽 x 342px高
        const liveCard = document.createElement('a');
        liveCard.className = 'home-live-card';
        liveCard.href = `/live/${live.room_id}/`;
        liveCard.target = '_blank';
        liveCard.setAttribute('data-room-id', live.room_id);
        liveCard.setAttribute('data-room-name', live.room_name);
        liveCard.style.cssText = `
            animation-delay: ${index * 0.1}s;
            width: 171px !important;
            height: 342px !important;
            max-width: 171px !important;
            max-height: 342px !important;
            display: flex !important;
            flex-direction: column !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 0 !important;
        `;

        // === 第1部分：图片区域 - 宽度占满171px，高度占一半171px ===
        const imageContainer = document.createElement('div');
        imageContainer.className = 'home-live-image-container';
        imageContainer.style.cssText = `
            width: 171px !important;
            height: 171px !important;
            position: relative !important;
            overflow: hidden !important;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%) !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            display: block !important;
            box-sizing: border-box !important;
            line-height: 0 !important;
            font-size: 0 !important;
            border-radius: 12px 12px 0 0 !important;
        `;
        
        const image = document.createElement('img');
        image.className = 'home-live-image';
        image.style.cssText = `
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
            object-position: center !important;
            display: block !important;
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            outline: none !important;
            border-radius: 12px 12px 0 0 !important;
            background: transparent !important;
            box-sizing: border-box !important;
            line-height: 0 !important;
            vertical-align: top !important;
            font-size: 0 !important;
        `;
        
        // 图片URL处理
        let imageUrl = '/media/headimage/default_image1.png';
        if (live.image_path) {
            const cleanPath = live.image_path.replace(/^\/+/, '');
            imageUrl = `${mediaUrl}${cleanPath}`;
        }
        
        image.src = imageUrl;
        image.alt = live.character_name || '直播图片';
        image.loading = 'lazy';
        
        // 加载成功后强制样式
        image.onload = function() {
            console.log(`图片加载成功: ${this.src}，尺寸: ${this.naturalWidth}x${this.naturalHeight}`);
            console.log(`容器尺寸: 171x171`);
            
            // 添加 loaded 类
            this.classList.add('loaded');
            
            // 强制设置尺寸
            this.style.width = '171px';
            this.style.height = '171px';
            this.style.maxWidth = '171px';
            this.style.maxHeight = '171px';
            this.style.minWidth = '171px';
            this.style.minHeight = '171px';
            this.style.objectFit = 'cover';
            this.style.objectPosition = 'center';
            
            // 调试：检查实际显示尺寸
            setTimeout(() => {
                const rect = this.getBoundingClientRect();
                console.log(`实际显示尺寸: ${rect.width}x${rect.height}`);
            }, 100);
        };
        
        // 错误处理
        image.onerror = function() {
            console.warn(`图片加载失败: ${this.src}`);
            this.src = '/media/headimage/default_image1.png';
        };
        
        image.addEventListener('error', function() {
            console.warn(`默认图片也加载失败`);
            imageContainer.innerHTML = `
                <div class="image-placeholder" style="
                    width: 171px !important;
                    height: 171px !important;
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                    right: 0 !important;
                    bottom: 0 !important;
                    border-radius: 12px 12px 0 0 !important;
                    line-height: 0 !important;
                ">
                    <i class="fas fa-image" style="font-size: 2rem;"></i>
                </div>
            `;
        });
        
        imageContainer.appendChild(image);

        // === 第2部分：角色名称 ===
        const cardNameContainer = document.createElement('div');
        cardNameContainer.className = 'home-card-name';
        cardNameContainer.style.cssText = `
            height: 45px !important;
            width: 171px !important;
            padding: 8px !important;
            margin: 0 !important;
            box-sizing: border-box !important;
        `;
        cardNameContainer.innerHTML = `
            <div class="character-name" style="
                height: 29px !important;
                font-size: 0.85rem !important;
                line-height: 1.1 !important;
                margin: 0 !important;
                padding: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-sizing: border-box !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
            ">${live.character_name || '未知角色'}</div>
        `;

        // === 第3部分：标题 ===
        const titleContainer = document.createElement('div');
        titleContainer.className = 'home-card-title-container';
        titleContainer.style.cssText = `
            height: 45px !important;
            width: 171px !important;
            padding: 8px !important;
            margin: 0 !important;
            box-sizing: border-box !important;
        `;
        
        const fullTitle = live.room_info?.title ;
        const truncatedTitle = fullTitle.length > 30 ? fullTitle.substring(0, 30) + '...' : fullTitle; // 窄卡片缩短标题
        
        const titleDiv = document.createElement('div');
        titleDiv.className = 'home-card-title';
        titleDiv.style.cssText = `
            height: 29px !important;
            font-size: 0.75rem !important;
            line-height: 1.2 !important;
            margin: 0 !important;
            padding: 0 !important;
            box-sizing: border-box !important;
            display: -webkit-box !important;
            -webkit-line-clamp: 2 !important;
            -webkit-box-orient: vertical !important;
            overflow: hidden !important;
        `;
        titleDiv.textContent = truncatedTitle;
        
        const tooltip = document.createElement('div');
        tooltip.className = 'home-title-tooltip';
        tooltip.textContent = fullTitle;
        tooltip.style.display = 'none';
        
        titleContainer.appendChild(titleDiv);
        titleContainer.appendChild(tooltip);

        // === 第4部分：标签 ===
        const tagsContainer = document.createElement('div');
        tagsContainer.className = 'home-tags-container';
        tagsContainer.style.cssText = `
            height: 45px !important;
            width: 171px !important;
            padding: 4px 8px !important;
            margin: 0 !important;
            box-sizing: border-box !important;
            gap: 3px !important;
            overflow: hidden !important;
        `;
        
        if (live.tags && live.tags.length > 0) {
            const maxTags = live.tags.slice(0, 3); // 窄卡片只显示3个标签
            maxTags.forEach(tag => {
                const tagSpan = document.createElement('span');
                tagSpan.className = 'home-tag';
                tagSpan.style.cssText = `
                    height: 20px !important;
                    font-size: 0.6rem !important;
                    padding: 2px 6px !important;
                    margin: 0 !important;
                    box-sizing: border-box !important;
                    display: flex !important;
                    align-items: center !important;
                    line-height: 1 !important;
                    white-space: nowrap !important;
                    overflow: hidden !important;
                `;
                tagSpan.textContent = `#${tag}`;
                tagsContainer.appendChild(tagSpan);
            });
        } 

        // === 第5部分：用户名 - 底部横向占满 ===
        const usernameContainer = document.createElement('div');
        usernameContainer.className = 'home-username-container';
        usernameContainer.innerHTML = `
            <div class="home-username" style="
                font-size: 0.7rem !important;
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                line-height: 1 !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
                display: block !important;
            ">${live.username}</div>
        `;

        // VIP徽章
        const roomInfo = live.room_info || {};
        if (roomInfo.room_type === 1 && roomInfo.coin_num > 0) {
            const diamondBadge = document.createElement('span');
            diamondBadge.className = 'badge vip-badge';
            diamondBadge.innerHTML = `<i class="fas fa-gem me-1"></i>VIP ${roomInfo.coin_num}`;
            diamondBadge.style.cssText = `
                position: absolute !important;
                top: 6px !important;
                right: 6px !important;
                z-index: 10 !important;
                font-size: 0.65rem !important;
                padding: 3px 6px !important;
                line-height: 1 !important;
                box-sizing: border-box !important;
            `;
            imageContainer.appendChild(diamondBadge);
        }

        // 标题悬停事件
        titleDiv.addEventListener('mouseenter', () => {
            if (fullTitle.length > 30) {
                tooltip.style.display = 'block';
            }
        });
        titleDiv.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
        });

        // 组装卡片
        liveCard.appendChild(imageContainer);        // 1. 图片 - 171×171 (宽度占满，高度占一半)
        liveCard.appendChild(cardNameContainer);     // 2. 角色名 - 45px
        liveCard.appendChild(titleContainer);        // 3. 标题 - 45px
        liveCard.appendChild(tagsContainer);         // 4. 标签 - 45px
        liveCard.appendChild(usernameContainer);     // 5. 用户名 - 底部横向
        
        homeContainer.appendChild(liveCard);
    });
}

static getEmptyTemplate() {
    return `
    <div class="text-center py-5 text-white empty-state">
        <div class="mb-4">
            <i class="fas fa-video-slash fa-4x text-muted mb-3"></i>
            <h4 class="text-light">暂无直播</h4>
        </div>
        <p class="text-muted">稍后回来查看精彩直播</p>
        <div class="mt-3">
            <i class="fas fa-clock text-primary"></i>
            <small class="text-muted ms-1">每小时更新</small>
        </div>
    </div>
    `;
}

    /**
     * 渲染直播列表到DOM
     * @param {Array} lives 直播列表数据
     */
    // static renderLiveList(lives) {
    //     const container = document.getElementById('liveListContainer');
    //     if (!container) {
    //         console.warn('Live broadcast list container not found');
    //         return;
    //     }

    //     // 清空加载状态
    //     container.innerHTML = '';

    //     if (lives.length === 0) {
    //         container.innerHTML = this.getEmptyTemplate();
    //         return;
    //     }

        
    //     // 生成直播列表HTML
    //     container.innerHTML = lives.map(live => {
    //         // 解析room_info
    //         let roomInfo = null;
    //         let diamondBadge = '';
            
    //         try {
    //             roomInfo = live.room_info ? live.room_info : null;
                
    //             // 如果是VIP房间且钻石数量>0
    //             if (roomInfo && roomInfo.room_type === 1 && roomInfo.coin_num > 0) {
    //                 diamondBadge = `
    //                     <span class="badge bg-primary ms-2 flex-shrink-0" 
    //                         style="background-color: #3498db !important; min-width: 30px;">
    //                         <i class="fas fa-gem me-1" style="font-size: 0.8em;"></i>
    //                         vip ${roomInfo.coin_num}
    //                     </span>
    //                 `;
    //             }
    //         } catch (e) {
    //             console.error('Failed to parse room_info:', e);
    //         }

    //         return `
    //         <a href="/live/${live.room_id}/" 
    //         class="nav-link text-white d-flex align-items-center live-room text-nowrap" 
    //         data-bs-toggle="tooltip" 
    //         data-bs-placement="right" 
    //         title="Join ${live.username} Livestream"
    //         data-room-id="${live.room_id}"
    //         data-room-name="${live.room_name}"
    //         style="min-width: 0;">
    //             <svg class="bi me-2 flex-shrink-0" width="16" height="16">
    //                 <use xlink:href="#people-circle"/>
    //             </svg>
    //             <span class="text-truncate flex-grow-1">
    //                 ${live.username} ${live.character_name}
    //             </span>
    //             ${diamondBadge}
    //         </a>
    //         `;
    //     }).join('');


    //     // <span class="badge bg-primary ms-2 flex-shrink-0">  <!-- 禁止数字压缩 -->
    //     //     ${live.live_num}人
    //     // </span>
    //     // 初始化动态生成的工具提示
    //     this.initDynamicTooltips();
    //     // 绑定点击事件
    //     this.bindLiveRoomEvents();
    // }


static renderLiveList(livesInfo) {
    const container = document.getElementById('liveListContainer');
    if (!container) {
        console.warn('Live broadcast list container not found');
        return;
    }

    // 清空容器
    container.innerHTML = '';

    if (livesInfo.length === 0) {
        container.innerHTML = this.getEmptyTemplate();
        return;
    }

    // 生成直播列表HTML
    livesInfo.forEach(liveInfo => {
        const userCard = document.createElement('div');
        userCard.className = 'live-card';

        // 用户头部信息
        const userHeader = document.createElement('div');
        userHeader.className = 'user-header';

        const userInfoDiv = document.createElement('div');
        userInfoDiv.className = 'user-info';

        // 钻石徽章逻辑
        let diamondBadge = '';
        try {
            if (liveInfo.room_type === 1 && liveInfo.coin_num > 0) {
                diamondBadge = `
                    <span class="badge bg-primary ms-2 flex-shrink-0">
                        <i class="fas fa-gem me-1" style="font-size: 0.8em;"></i>
                        vip ${liveInfo.coin_num}
                    </span>
                `;
            }
        } catch (e) {
            console.error('room_info error:', e);
        }

        // 包裹在链接中
        userInfoDiv.innerHTML = `
            <a href="/live/${liveInfo.room_id}/" 
               class="nav-link text-white d-flex align-items-center live-room text-nowrap" 
               data-bs-toggle="tooltip" 
               data-bs-placement="right" 
               title="Join ${liveInfo.username} Livestream"
               data-room-id="${liveInfo.room_id}"
               data-room-name="${liveInfo.room_name}"
               target="_blank"  
               style="min-width: 0;">
                <div class="user-avatar">${liveInfo.username ? liveInfo.username.charAt(0).toUpperCase() : 'U'}</div>
                <div class="text-truncate flex-grow-1">
                    ${liveInfo.username} ${liveInfo.character_name}
                </div>
                ${diamondBadge}
            </a>
        `;

        userHeader.appendChild(userInfoDiv);
        userCard.appendChild(userHeader);
        container.appendChild(userCard);
    });
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
        window.location.href = `/live/${roomId}`;
    }

    /**
     * 模块初始化入口
     */
    static async init() {
        const lives = await this.fetchLiveList();
        this.renderLiveList(lives);


        // 设置变量
        sessionStorage.setItem('but_value', 'live');

        // 如果需要轮询更新可以在这里添加
        this.startPolling();
    }



    static initFollowsButton() {
        const followsLink = document.querySelector('.follows-link');
        if (followsLink) {
            followsLink.addEventListener('click', async () => {
                await this.loadFollows();
            });
        }
    }


    static async loadFollows() {
        // 设置变量
        sessionStorage.setItem('but_value', 'follow');
        // 获取变量
        let but_value = sessionStorage.getItem('but_value');

        // 检查用户是否登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('please log in first');
            
            const googleLoginLink = document.getElementById('googleLoginLink');
            if (googleLoginLink) {
                googleLoginLink.click()
            }

            return
        }

        try {
            const response = await fetch('/api/follow_live/get_followed_rooms/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            const lives = data.code === 0 ? data.data.lives_info : [];
            this.renderLiveList(lives)

        } catch (error) {
            console.error('Failed to load the follow list:', error);
            alert('Failed to load the follow list');
        }
    }







    static async loadSubscriptions() {
        // 检查用户是否登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('please log in first');
            
            const googleLoginLink = document.getElementById('googleLoginLink');
            if (googleLoginLink) {
                googleLoginLink.click()
            }

            return
        }
        sessionStorage.setItem('but_value', 'subscription');


        try {
            const response = await fetch('/api/subscription/get_subscriptions/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            const lives = data.code === 0 ? data.data.lives_info : [];
            this.renderLiveList_sub(lives)
        } catch (error) {
            console.error('加载订阅列表失败:', error);
            alert('无法加载订阅列表');
        }
    }

    static initSubscriptionsButton() {
        const subscriptionsLink = document.querySelector('.subscriptions-link');
        if (subscriptionsLink) {
            subscriptionsLink.addEventListener('click', async () => {
                await this.loadSubscriptions();
            });
        }
    }

    static initHomeButton(is_home) {
        const homeLink = document.querySelector('.home-link');
        if (homeLink) {
            homeLink.addEventListener('click', async () => {
                await this.loadHome(is_home);
            });
        }
    }
    static initRoomButton() {
        const roomLink = document.querySelector('.room-link');
        if (roomLink) {
            roomLink.addEventListener('click', async () => {
                await this.loadRoom();
            });
        }
    }


    static initRedirectHomeButton() {
        // 检查当前路径是否为根路径

        const titleLink = document.querySelector('.title-link');
        if (titleLink) {
            titleLink.addEventListener('click', async () => {
                await this.redirectHome();
            });
        }
    }



    static async loadHome(is_home) {
        sessionStorage.setItem('but_value', 'live');
        const lives = await this.fetchLiveList();
        this.renderLiveList(lives);
        if(is_home){
            this.renderLiveList_home(lives);
        }
    }
    static async loadRoom(is_home) {
        sessionStorage.setItem('but_value', 'live');
        const lives = await this.fetchLiveList();
        this.renderLiveList(lives);
    }
    static async redirectHome() {
        sessionStorage.setItem('but_value', 'live');
        const lives = await this.fetchLiveList();
        this.renderLiveList_home(lives)
        this.renderLiveList(lives);
    }


    static convertTo24Hour(timeStr) {
        try {
            const dt = moment(timeStr, 'MMM DD, YYYY hh:mmA');
            if (!dt.isValid()) throw new Error('无效的时间格式');
            return dt.format('YYYY-MM-DD HH:mm');
        } catch (error) {
            console.error('时间转换错误:', error);
            return '无效的时间格式';
        }
    }


    /**
     * 轮询更新直播列表（可选）
     */
    static startPolling() {
        // 每30秒刷新一次
        this.pollingTimer = setInterval(async () => {
            if(sessionStorage.getItem('but_value') == "live"){
                const lives = await this.fetchLiveList();

                this.renderLiveList(lives);
            }

        }, 10000);
    }
}

// 自动注册初始化（如果直接使用该模块）
if (import.meta.url === document.currentScript?.src) {
    document.addEventListener('DOMContentLoaded', () => LiveManager.init());
}

export default LiveManager;