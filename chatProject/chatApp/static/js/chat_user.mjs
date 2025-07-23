export default class ChatUserManager {
    static async fetchChatHistory(roomId) {
        // 模拟数据
        const mockData = {
            code: 0,
            data: {
                chat_info: [
                    {
                        uid: "user_123",
                        username: "观众A",
                        send_date: new Date().toISOString(),
                        user_message: "主播今天播什么内容？"
                    },
                    {
                        uid: "user_456",
                        username: "观众B",
                        send_date: new Date().toISOString(),
                        user_message: "昨天的直播很精彩！"
                    },
                    {
                        uid: "user_789",
                        username: "我",
                        send_date: new Date().toISOString(),
                        user_message: "今天主要讲解JavaScript高级技巧"
                    }
                ]
            }
        };
        return mockData.data.chat_info;
    }

    static async init(roomId) {
        try {
            const messages = await this.fetchChatHistory(roomId);
            this.renderMessages(messages);

            // // 模拟实时消息更新
            // this.interval = setInterval(async () => {
            //     const newMessages = await this.fetchNewMessages(roomId);
            //     this.appendNewMessages(newMessages);
            // }, 3000);

        } catch (error) {
            console.error('初始化聊天失败:', error);
        }
    }

    static renderMessages(messages) {
        const chatContainer = document.querySelector('.chat-content');
        if (!chatContainer) return;

        chatContainer.innerHTML = messages.map(msg =>
            this.createMessageElement(msg)
        ).join('');
    }

    static createMessageElement(message) {
        const isCurrentUser = message.username === '我';
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

    static async fetchNewMessages(roomId) {
        // 模拟获取新消息
        const mockNewMessages = {
            code: 0,
            data: {
                chat_info: [
                    {
                        uid: `user_${Math.floor(Math.random() * 1000)}`,
                        username: `观众${String.fromCharCode(65 + Math.floor(Math.random() * 26))}`,
                        send_date: new Date().toISOString(),
                        user_message: `新消息${Math.floor(Math.random() * 100)}`
                    }
                ]
            }
        };
        return mockNewMessages.data.chat_info;
    }

    static appendNewMessages(messages) {
        const chatContainer = document.querySelector('.chat-content');
        if (!chatContainer) return;

        messages.forEach(msg => {
            const msgElement = this.createMessageElement(msg);
            chatContainer.insertAdjacentHTML('beforeend', msgElement);
        });

        this.scrollToBottom();
    }

    static formatTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    static scrollToBottom() {
        const chatContainer = document.querySelector('.chat-content');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    static stop() {
        clearInterval(this.interval);
    }
}