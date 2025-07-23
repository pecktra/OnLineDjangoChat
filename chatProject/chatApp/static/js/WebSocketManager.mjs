// WebSocketManager.mjs
export default class WebSocketManager {
    constructor(roomId) {
        this.roomId = roomId;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;

        // DOM 元素
        //获取
        this.chatArea = document.querySelector('.chat-area');
        this.chatContent = document.querySelector('.chat-content');

        this.chatInput = document.querySelector('#chatMessageInput');
        this.sendButton = document.querySelector('#chatMessageSend');
    }

    init() {
        this.connect();
        this.bindEvents();
    }

    connect() {
        this.socket = new WebSocket(`ws://${window.location.host}/ws/chat/${this.roomId}/`);

        this.socket.onopen = (e) => {
            console.log('WebSocket连接成功');
            this.reconnectAttempts = 0; // 重置重连尝试次数
        };

        this.socket.onclose = (e) => {
            console.log('WebSocket连接断开');
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
        console.log('收到消息:', data);

        switch (data.type) {
            case 'chat_live_message':

                this.chatArea.insertAdjacentHTML('beforeend', this.appendLiveMessage(data.message));
                this.chatArea.scrollTop = this.chatArea.scrollHeight;
                break;
            case 'chat_user_message':

                this.chatContent.insertAdjacentHTML('beforeend', this.appendUserMessage(data.message));
                this.chatContent.scrollTop = this.chatContent.scrollHeight;


                break;

            default:
                console.warn('未知消息类型:', data.type);
        }
    }

    appendLiveMessage(msg) {
        return `
                <div class="chat-message ${msg.isUser ? 'user-message' : 'ai-message'} ">
                    <div class="message-content">
                        <div class="message-header">
                            <span class="sender-name">${msg.sender}</span>
                            <span class="message-time">${msg.timestamp}</span>
                        </div>
                        <p>${msg.content}</p>
                    </div>
                </div>
            `;
    }


    appendUserMessage(message) {
        return `
            <div class="message ${isCurrentUser ? 'my-message' : 'other-message'}">
                <div class="message-user-info">
                    <img src="${isCurrentUser ? 'my-avatar.jpg' : 'default-avatar.jpg'}" 
                         class="message-avatar" >
                     
                    <span class="message-username">${message.username}</span>
                    <div class="message-time">${this.formatTime(message.send_date)}</div>
                </div>
                <div class="message-bubble">${message.user_message}</div>
                
            </div>
        `;
    }



    removeOnlineUser(username) {
        const option = document.querySelector(`option[value="${username}"]`);
        if (option) option.remove();
    }

    sendMessage() {
        const message = this.chatInput.value.trim();
        if (message && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ message }));
            this.chatInput.value = '';
        }
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
        if (this.socket) {
            this.socket.close();
        }
    }
}