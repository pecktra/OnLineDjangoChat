
// WebSocketManager.mjs
export default class WebSocketManager {
    constructor(roomId,roomName,userName) {
        this.roomId = roomId;
        this.roomName = roomName;
        this.userName = userName;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;

        // 轮询配置
        this.pollingIntervalMs = 5000; // 10 秒
        this.pollingTimerId = null;

        // 已见消息去重集合
        this.seenMessageIds = new Set();
        this.lastFloor = 0;

        // 滚动控制
        this.isInitialLoad = true; // 标记是否首次加载

        // DOM 元素
        this.chatArea = document.querySelector('.chat-area');
        this.chatContent = document.querySelector('.chat-content');
        this.chatInput = document.querySelector('#chatMessageInput');
        this.sendButton = document.querySelector('#chatMessageSend');

        window.addEventListener('beforeunload', () => this.disconnect());
        window.addEventListener('unload', () => this.disconnect()); // 备用
    }

    init() {
        this.startPolling();
        this.connect();
        this.bindEvents();
    }

    // 检测是否滚动到底部
    isScrolledToBottom(element) {
        const threshold = 50; // 允许50px的误差范围
        return element.scrollHeight - element.scrollTop - element.clientHeight <= threshold;
    }

    // 条件滚动：只在用户在底部时滚动
    conditionalScroll(element) {
        // 如果是首次加载，不滚动
        if (this.isInitialLoad) {
            return;
        }
        // 如果用户滚动到底部，才自动滚动
        if (this.isScrolledToBottom(element)) {
            element.scrollTop = element.scrollHeight;
        }
    }

    // 新增方法：保存聊天记录到服务器
    async saveChatHistory(message) {
        // 检查登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('please log in first');
            const googleLoginLink = document.getElementById('googleLoginLink');
            if (googleLoginLink) {
                googleLoginLink.click()
            }
            return;
        }
        try {
            const response = await fetch('/api/live/save_user_chat_history/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    room_id:this.roomId,
                    room_name: this.roomName,
                    username: this.userName,
                    user_message: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

        } catch (error) {
            console.error('保存消息失败:', error);
            // 可选：重试逻辑或用户提示
        }
    }

    // 启动轮询
    startPolling() {
        // 立即拉取一次
        this.fetchAndAppendNewMessages().catch(console.error);

        // 定时轮询
        this.pollingTimerId = window.setInterval(() => {
            this.fetchAndAppendNewMessages()//.catch(console.error);
        }, this.pollingIntervalMs);
    }

    // 从后端拉取消息并仅追加新增项
    async fetchAndAppendNewMessages() {
        try {
            const url = `/api/chat/get_room_chat/?room_id=${encodeURIComponent(this.roomId)}&last_floor=${this.lastFloor}`;
            const resp = await fetch(url, { credentials: 'same-origin' });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const payload = await resp.json();
            document.querySelector('.chat-area .loading').hidden=true
            // 兼容多种返回形态：{messages: [...]} 或直接 [...]
            const items = payload.data
            if (!Array.isArray(items)) return;

            for (const item of items) {
                if (item.floor <= this.lastFloor) continue;
                this.lastFloor = item.floor
                // 提取唯一 ID；尽量使用后端提供的 id，其次 data.id；都没有则构造一个稳定 key
                // const rawId = item.id ?? item?.data?.id ?? `${item.type || 'msg'}-${item?.data?.username || ''}-${item?.data?.send_date || item?.data?.time || ''}-${item?.data?.message || item?.data?.live_message || ''}`;
                // if (this.seenMessageIds.has(rawId)) continue;

                // // 记录并渲染
                // this.seenMessageIds.add(rawId);

                const type = item.data_type
                if (type === 'ai') {
                    this.chatArea.insertAdjacentHTML('beforeend', this.appendLiveMessage(item));
                    this.conditionalScroll(this.chatArea);
                } else if (type === 'user') {
                    this.chatArea.insertAdjacentHTML('beforeend', this.appendLiveMessage(item));
                    this.conditionalScroll(this.chatArea);
                } else {
                    // 若后端未提供 type，则尝试通过字段推断
                    const hasLiveFields = (item.data || item)?.live_message || (item.data || item)?.live_message_html;
                    if (hasLiveFields) {
                        this.chatArea.insertAdjacentHTML('beforeend', this.appendLiveMessage(item));
                        this.conditionalScroll(this.chatArea);
                    } else {
                        this.chatContent.insertAdjacentHTML('beforeend', this.appendUserMessage(item));
                        this.conditionalScroll(this.chatContent);
                    }
                }
            }

            // 首次加载完成后，标记为非首次加载
            if (this.isInitialLoad && items.length > 0) {
                this.isInitialLoad = false;
            }
        } catch (err) {
            console.error('轮询获取聊天失败:', err);
        }
    }

    connect() {
        this.socket = new WebSocket(`wss://${window.location.host}/ws/chat/${this.roomId}/`);

        this.socket.onopen = (e) => {
            this.reconnectAttempts = 0; // 重置重连尝试次数
        };

        this.socket.onclose = (e) => {
            this.handleReconnect();
        };

        this.socket.onmessage = (e) => this.handleMessage(e);
        this.socket.onerror = (err) => {
            console.error('WebSocket错误:', err);
            this.socket.close();
        };
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            console.error('达到最大重连次数，停止尝试');
        }
    }

    handleMessage(e) {
        const data = JSON.parse(e.data);


        switch (data.type) {
            case 'chat_live_message':

                this.chatArea.insertAdjacentHTML('beforeend', this.appendLiveMessage(data.data));
                this.conditionalScroll(this.chatArea);
                break;
            case 'chat_user_message':
                this.chatContent.insertAdjacentHTML('beforeend', this.appendUserMessage(data.data));
                this.conditionalScroll(this.chatContent);


                break;

            default:
                console.warn('未知消息类型:', data.type);
        }
    }

    extractHtmlContent(content) {
        // 提取 ```html 代码块中的内容
        const htmlCodeBlockMatch = content.match(/```html\s*([\s\S]*?)```/i);
        if (htmlCodeBlockMatch) {
            return htmlCodeBlockMatch[1].trim();
        }

        // 提取 <pre><code> 标签中的内容
        const preCodeMatch = content.match(/<pre[^>]*><code[^>]*>([\s\S]*?)<\/code><\/pre>/i);
        if (preCodeMatch) {
            // 解码 HTML 实体
            const div = document.createElement('div');
            div.innerHTML = preCodeMatch[1];
            return div.textContent || div.innerText;
        }

        // 直接返回原内容
        return content;
    }

    isCompleteHtml(content) {
        // 检查是否包含完整的 HTML 结构标签
        const hasHtmlTag = /<html[^>]*>/i.test(content);
        const hasBodyTag = /<body[^>]*>/i.test(content);
        const hasHeadTag = /<head[^>]*>/i.test(content);

        // 如果包含 html/body/head 标签之一，认为是完整 HTML
        return hasHtmlTag || hasBodyTag || hasHeadTag;
    }

    // 自适应 iframe 高度
    autoResizeIframe(iframe) {
        try {
            // 等待 iframe 内容加载完成
            iframe.addEventListener('load', () => {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (iframeDoc && iframeDoc.body) {
                        // 获取内容的实际高度
                        const contentHeight = Math.max(
                            iframeDoc.body.scrollHeight,
                            iframeDoc.body.offsetHeight,
                            iframeDoc.documentElement.scrollHeight,
                            iframeDoc.documentElement.offsetHeight
                        );
                        // 设置 iframe 高度，增加一点缓冲空间
                        iframe.style.height = (contentHeight + 2) + 'px';
                    }
                } catch (error) {
                    console.error('无法访问 iframe 内容:', error);
                    // 如果无法访问，保持默认高度
                }
            });
        } catch (error) {
            console.error('设置 iframe 自适应失败:', error);
        }
    }

    appendLiveMessage(msg) {
        let messageContent = msg.data.is_user  ? msg.data.mes : msg.mes_html;

        // 提取可能包裹在代码块中的 HTML
        const extractedHtml = this.extractHtmlContent(messageContent);
        // 检查是否是完整的 HTML
        let contentHtml;
        let hasIframe = false;
        if (this.isCompleteHtml(extractedHtml)) {
            // 使用 iframe srcdoc 渲染完整 HTML
            const escapedHtml = extractedHtml
                .replace(/&/g, '&amp;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
            // 添加 auto-resize-iframe class 用于标识需要自适应的 iframe
            contentHtml = `<iframe loading="lazy" class="auto-resize-iframe" srcdoc="${escapedHtml}" style="width: 100%; min-height: 200px; border: 1px solid #ddd; border-radius: 4px;"></iframe>`;
            hasIframe = true;
        } else {
            contentHtml = messageContent;
        }

        const messageHtml = `
                <div class="chat-message ${msg.data.is_user ? 'user-message' : 'ai-message'} ">
                    <div class="message-content">
                        <div class="message-header">
                            <div><span class="sender-name">${msg.data.name}</span><span>#${msg.floor}</span><div>
                            <span class="message-time">${this.convertTo24Hour(msg.data.send_date)}</span>
                        </div>
                        <div class="mes_text">
                            ${contentHtml}
                        </div>

                    </div>
                </div>
            `;

        // 如果包含 iframe，需要在插入后设置自适应
        if (hasIframe) {
            // 使用 setTimeout 确保 DOM 已更新
            setTimeout(() => {
                const iframes = document.querySelectorAll('.auto-resize-iframe:not([data-resized])');
                iframes.forEach(iframe => {
                    iframe.setAttribute('data-resized', 'true');
                    this.autoResizeIframe(iframe);
                });
            }, 20);
        }

        return messageHtml;
    }

    convertTo24Hour(timeStr) {
        try {
            const dt = moment(timeStr, 'MMM DD, YYYY hh:mmA');
            if (!dt.isValid()) throw new Error('无效的时间格式');
            return dt.format('YYYY-MM-DD HH:mm');
        } catch (error) {
            console.error('时间转换错误:', error);
            return '无效的时间格式';
        }
    }


    appendUserMessage(data) {
        const isCurrentUser = data.data.username === window.GLOBAL_USER_NAME;
        return `
            <div class="message ${isCurrentUser ? 'my-message' : 'other-message'}">
                <div class="message-user-info">
                    <svg class="bi me-2 flex-shrink-0" width="16" height="16">  <!-- 禁止图标压缩 -->
                        <use xlink:href="#people-circle"/>
                    </svg>

                    <div><span class="message-username">${data.data.username }</span></div>
                    <div class="message-time">${ new Date().toLocaleString('en-CA', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                }).replace(/,/, '')}</div>
                </div>
                <div class="message-bubble">${data.data.msg}</div>

            </div>
        `;
    }




    removeOnlineUser(username) {
        const option = document.querySelector(`option[value="${username}"]`);
        if (option) option.remove();
    }

    sendMessage() {
        // 检查登录
        if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
            alert('please log in first');
            const googleLoginLink = document.getElementById('googleLoginLink');
            if (googleLoginLink) {
                googleLoginLink.click()
            }
            return;
        }
        const message = this.chatInput.value.trim();

        if (!message) return;

        // 2. 通过HTTP保存记录（不阻塞UI）
        this.saveChatHistory(message).catch(console.error);

        // 3. 前端乐观追加一条当前用户消息（等待下一次轮询与服务端对齐）
        try {
            const optimistic = {
                data: {
                    username: this.userName,
                    msg: message
                }
            };
            this.chatContent.insertAdjacentHTML('beforeend', this.appendUserMessage(optimistic));
            // 用户发送消息时，主动滚动到底部
            this.chatContent.scrollTop = this.chatContent.scrollHeight;
        } catch (_) {}
        this.chatInput.value = '';
    }

    bindEvents() {
        // 现有事件
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // 新增功能示例：
        // 1. 输入框获得焦点时清空提示文字
        this.chatInput.addEventListener('focus', () => {
            if (this.chatInput.placeholder) this.chatInput.placeholder = '';
        });

        // 2. 输入框失去焦点时恢复提示
        this.chatInput.addEventListener('blur', () => {
            if (!this.chatInput.value) {
                this.chatInput.placeholder = '输入消息...';
            }
        });
    }

    disconnect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.close(1000, "User left the chat"); // 1000 是正常关闭状态码
            console.log("WebSocket 连接已主动关闭");
        }
        if (this.pollingTimerId) {
            clearInterval(this.pollingTimerId);
            this.pollingTimerId = null;
        }
    }
}

