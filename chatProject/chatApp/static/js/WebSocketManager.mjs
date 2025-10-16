
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
                    this.attachMessageBranchEvents();
                    this.conditionalScroll(this.chatArea);
                } else if (type === 'user') {
                    this.chatArea.insertAdjacentHTML('beforeend', this.appendLiveMessage(item));
                    this.attachMessageBranchEvents();
                    this.conditionalScroll(this.chatArea);
                } else {
                    // 若后端未提供 type，则尝试通过字段推断
                    const hasLiveFields = (item.data || item)?.live_message || (item.data || item)?.live_message_html;
                    if (hasLiveFields) {
                        this.chatArea.insertAdjacentHTML('beforeend', this.appendLiveMessage(item));
                        this.attachMessageBranchEvents();
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
                this.attachMessageBranchEvents();
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
        // 存储所有需要替换的 <pre><code> 块及其对应的 iframe
        const replacements = [];
        let processedContent = content;

        // 1. 处理所有 <pre><code> 标签块
        const preCodeRegex = /<pre[^>]*><code[^>]*>([\s\S]*?)<\/code><\/pre>/gi;
        let match;
        let index = 0;

        while ((match = preCodeRegex.exec(content)) !== null) {
            const fullMatch = match[0]; // 完整的 <pre><code>...</code></pre>
            const codeContent = match[1]; // code 标签内的内容

            // 解码 HTML 实体
            const div = document.createElement('div');
            div.innerHTML = codeContent;
            const decodedHtml = div.textContent || div.innerText;

            // 检查解码后的内容是否是完整的 HTML
            if (this.isCompleteHtml(decodedHtml)) {
                // 创建一个占位符
                const placeholder = `__IFRAME_PLACEHOLDER_${index}__`;
                replacements.push({
                    placeholder: placeholder,
                    html: decodedHtml
                });

                // 在内容中替换为占位符
                processedContent = processedContent.replace(fullMatch, placeholder);
                index++;
            }
        }

        // 2. 处理 ```html 代码块（如果有的话）
        const htmlCodeBlockRegex = /```html\s*([\s\S]*?)```/gi;
        while ((match = htmlCodeBlockRegex.exec(content)) !== null) {
            const fullMatch = match[0];
            const htmlContent = match[1].trim();

            if (this.isCompleteHtml(htmlContent)) {
                const placeholder = `__IFRAME_PLACEHOLDER_${index}__`;
                replacements.push({
                    placeholder: placeholder,
                    html: htmlContent
                });

                processedContent = processedContent.replace(fullMatch, placeholder);
                index++;
            }
        }

        // 3. 如果没有找到任何需要转换为 iframe 的内容，直接返回原内容
        if (replacements.length === 0) {
            return content;
        }

        // 4. 将占位符替换为实际的 iframe
        replacements.forEach((replacement) => {
            const escapedHtml = replacement.html
                .replace(/&/g, '&amp;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');

            const iframeHtml = `<iframe loading="lazy" class="auto-resize-iframe" srcdoc="${escapedHtml}" style="width: 100%; min-height: 200px; border: 1px solid #ddd; border-radius: 4px; margin: 10px 0;"></iframe>`;

            processedContent = processedContent.replace(replacement.placeholder, iframeHtml);
        });

        return processedContent;
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

        // 提取并处理所有 HTML 内容（可能包含多个 iframe）
        const processedContent = this.extractHtmlContent(messageContent);

        // 检查处理后的内容是否包含 iframe
        const hasIframe = processedContent.includes('auto-resize-iframe');

        const messageHtml = `
                <div class="chat-message ${msg.data.is_user ? 'user-message' : 'ai-message'} ">
                    <div class="message-content">
                        <div class="message-header">
                            <div><span class="sender-name">${msg.data.name}</span><span>#${msg.floor}</span>
                                <span class="message-branch-btn" data-floor="${msg.floor}" data-tooltip="Branch" style="margin-left: 8px; cursor: pointer; display: inline-flex; align-items: center;">
                                    <svg viewBox="0 0 384 512" style="width: 14px; height: 14px; fill: currentColor;">
                                        <path d="M384 144c0-44.2-35.8-80-80-80s-80 35.8-80 80c0 36.4 24.3 67.1 57.5 76.8-.6 16.1-4.2 28.5-11 36.9-15.4 19.2-49.3 22.4-85.2 25.7-28.2 2.6-57.4 5.4-81.3 16.9v-144c32.5-10.2 56-40.5 56-76.3 0-44.2-35.8-80-80-80S0 35.8 0 80c0 35.8 23.5 66.1 56 76.3v199.3C23.5 365.9 0 396.2 0 432c0 44.2 35.8 80 80 80s80-35.8 80-80c0-34-21.2-63.1-51.2-74.6 3.1-5.2 7.8-9.8 14.9-13.4 16.2-8.2 40.4-10.4 66.1-12.8 42.2-3.9 90-8.4 118.2-43.4 14-17.4 21.1-39.8 21.6-67.9 31.6-10.8 54.4-40.7 54.4-75.9zM80 64c8.8 0 16 7.2 16 16s-7.2 16-16 16-16-7.2-16-16 7.2-16 16-16zm0 384c-8.8 0-16-7.2-16-16s7.2-16 16-16 16 7.2 16 16-7.2 16-16 16zm224-320c8.8 0 16 7.2 16 16s-7.2 16-16 16-16-7.2-16-16 7.2-16 16-16z"/>
                                    </svg>
                                </span>
                                <span class="message-copy-btn" data-tooltip="Copy" title="Copy" style="margin-left: 8px; cursor: pointer; display: inline-flex; align-items: center;">
                                    <svg viewBox="0 0 640 640" style="width: 14px; height: 14px; fill: currentColor;">
                                        <path d="M288 64C252.7 64 224 92.7 224 128L224 384C224 419.3 252.7 448 288 448L480 448C515.3 448 544 419.3 544 384L544 183.4C544 166 536.9 149.3 524.3 137.2L466.6 81.8C454.7 70.4 438.8 64 422.3 64L288 64zM160 192C124.7 192 96 220.7 96 256L96 512C96 547.3 124.7 576 160 576L352 576C387.3 576 416 547.3 416 512L416 496L352 496L352 512L160 512L160 256L176 256L176 192L160 192z"/>
                                    </svg>
                                </span>

                            </div>
                            <span class="message-time">${this.convertTo24Hour(msg.data.send_date)}</span>
                        </div>
                        <div class="mes_text">
                            ${processedContent}
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

    // 为消息中的 branch / copy 按钮绑定事件
    attachMessageBranchEvents() {
        // 使用 setTimeout 确保 DOM 已更新
        setTimeout(() => {
            const messageBranchBtns = document.querySelectorAll('.message-branch-btn:not([data-event-attached])');
            messageBranchBtns.forEach(btn => {
                btn.setAttribute('data-event-attached', 'true');
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const floor = btn.getAttribute('data-floor');
                    // 调用 StreamerInfoManager 的方法，传递 floor 参数
                    if (window.StreamerInfoManager) {
                        window.StreamerInfoManager.openForkDialog(floor);
                    } else {
                        console.error('StreamerInfoManager not available');
                    }
                });
            });

            const copyBtns = document.querySelectorAll('.message-copy-btn:not([data-event-attached])');
            copyBtns.forEach(btn => {
                btn.setAttribute('data-event-attached', 'true');
                btn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    try {
                        const messageContent = btn.closest('.message-content');
                        const mesText = messageContent ? messageContent.querySelector('.mes_text') : null;
                        const text = mesText ? mesText.textContent.trim() : '';

                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            await navigator.clipboard.writeText(text);
                        } else {
                            const textarea = document.createElement('textarea');
                            textarea.value = text;
                            textarea.style.position = 'fixed';
                            textarea.style.opacity = '0';
                            document.body.appendChild(textarea);
                            textarea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textarea);
                        }
                        // 使用 Toast 提示
                        this.showToast('Copied to clipboard');
                    } catch (err) {
                        console.error('复制失败:', err);
                        alert('复制失败');
                    }
                });
            });
        }, 10);
    }

    // 显示全局 Toast 提示（Bootstrap 5）
    showToast(message) {
        try {
            // 如果没有 Bootstrap，则回退到 alert
            if (typeof bootstrap === 'undefined') {
                alert(message);
                return;
            }

            // 容器（复用）
            let container = document.getElementById('global-toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'global-toast-container';
                container.style.position = 'fixed';
                container.style.right = '20px';
                container.style.bottom = '20px';
                container.style.zIndex = '1080';
                document.body.appendChild(container);
            }

            // 构建 toast 元素
            const toast = document.createElement('div');
            toast.className = 'toast align-items-center bg-white border';
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body" style="color:#333333;">${message}</div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            container.appendChild(toast);

            const bsToast = new bootstrap.Toast(toast, { delay: 1500 });
            toast.addEventListener('hidden.bs.toast', () => toast.remove());
            bsToast.show();
        } catch (e) {
            // 兜底
            alert(message);
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

