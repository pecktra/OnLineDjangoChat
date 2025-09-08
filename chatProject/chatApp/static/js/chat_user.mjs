
export default class ChatUserManager {
    static async fetchChatHistory(room_id) {
        // 模拟数据
        // const mockData = {
        //     code: 0,
        //     data: {
        //         chat_info: [
        //             {
        //                 uid: "user_123",
        //                 username: "观众A",
        //                 send_date: new Date().toISOString(),
        //                 user_message: "主播今天播什么内容？"
        //             },
        //             {
        //                 uid: "user_456",
        //                 username: "观众B",
        //                 send_date: new Date().toISOString(),
        //                 user_message: "昨天的直播很精彩！"
        //             },
        //             {
        //                 uid: "user_789",
        //                 username: "我",
        //                 send_date: new Date().toISOString(),
        //                 user_message: "今天主要讲解JavaScript高级技巧"
        //             }
        //         ]
        //     }
        // };
        const response = await fetch(`/api/live/get_user_chat_history/?room_id=${encodeURIComponent(room_id)}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }, // 如果后端不要求此头，可移除
        });
        if (!response.ok) throw new Error('Network error');
        const mockData = await response.json();
        return mockData.data.chat_info;
    }

    static async init(room_id) {
        try {
            const messages = await this.fetchChatHistory(room_id);
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

    static renderMessages(messages) {
        const chatContainer = document.querySelector('.chat-content');
        if (!chatContainer) return;

        chatContainer.innerHTML = messages.map(msg =>
            this.createMessageElement(msg)
        ).join('');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    static createMessageElement(message) {

        const isCurrentUser = message.username === window.GLOBAL_USER_NAME;
        return `
            <div class="message ${isCurrentUser ? 'my-message' : 'other-message'}">
                <div class="message-user-info">
                    <svg class="bi me-2 flex-shrink-0" width="16" height="16">  <!-- 禁止图标压缩 -->
                        <use xlink:href="#people-circle"/>
                    </svg>
                     
                    <span class="message-username">${message.username}</span>
                    <div class="message-time">${this.convertTo24Hour(message.send_date)}</div>
                </div>
                <div class="message-bubble">${message.user_message}</div>
                
            </div>
        `;
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