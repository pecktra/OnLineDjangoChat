/**
 * 直播间历史消息管理模块 (增强版)
 */
class ChatLiveManager {
    /**
     * 获取并处理历史消息
     * @param {string} room_name 直播间ID
     * @returns {Promise<Array>} 处理后的消息数组
     */
    static async fetchChatHistory(room_name) {
        try {
            // 模拟数据 - 实际替换为真实API请求
            // const mockResponse = {
            //     code: 0,
            //     data: {
            //         chat_info: [
            //             {
            //                 uid: "1",
            //                 name: "pride",
            //                 is_user: true,
            //                 is_system: false,
            //                 send_date: "July 11, 2025 5:51pm",
            //                 mes: "哈喽",
            //                 extra: { isSmallSys: false, reasoning: "" },
            //                 force_avatar: "User Avatars/user-default.png"
            //             },
            //             {
            //                 uid: "2",
            //                 name: "Seraphina",
            //                 is_user: false,
            //                 send_date: "July 11, 2025 6:13pm",
            //                 mes: "Um...thanks ? But what was that exactly?...", // 截短示例
            //                 extra: {
            //                     api: "koboldhorde",
            //                     model: "Skyfall-36B-v2",
            //                     reasoning: ""
            //                 }
            //             }
            //             ,
            //             {
            //                 uid: "3",
            //                 name: "Seraphina",
            //                 is_user: false,
            //                 send_date: "July 11, 2025 6:13pm",
            //                 mes: "Um...thanks ? But what was that exactly?11111111111111111111111111111111111111112222222222222222222222222222222222222222222222222222222222222222222222222", // 截短示例
            //                 extra: {
            //                     api: "koboldhorde",
            //                     model: "Skyfall-36B-v2",
            //                     reasoning: ""
            //                 }
            //             }
            //             ,
            //             {
            //                 uid: "4",
            //                 name: "Seraphina",
            //                 is_user: false,
            //                 send_date: "July 11, 2025 6:13pm",
            //                 mes: "Um...thanks ? But what was that exactly?...", // 截短示例
            //                 extra: {
            //                     api: "koboldhorde",
            //                     model: "Skyfall-36B-v2",
            //                     reasoning: ""
            //                 }
            //             }
            //         ]
            //     }
            // };

            // 正式环境请取消注释以下代码 ▼
            const response = await fetch(`/api/live/get_live_chat_history/?room_name=${encodeURIComponent(room_name)}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }, // 如果后端不要求此头，可移除
            });
            if (!response.ok) throw new Error('Network error');
            const mockResponse = await response.json();

            return mockResponse.code === 0
                ? this.processMessages(mockResponse)
                : [];
        } catch (error) {
            console.error('获取历史消息失败:', error);
            return [];
        }
    }

    /**
     * 处理原始消息数据
     * @param {Array} rawMessages 原始消息数组
     * @returns {Array} 处理后的消息
     */
static processMessages(messages) {
    // 从 API 响应中获取 chat_info 数组
    const chatInfo = messages.data?.chat_info || [];
    
    // 提取需要的字段
    return chatInfo.map(message => ({
        is_user: message.is_user,
        live_message: message.live_message,
        live_message_html: message.live_message_html,
        sender_name: message.sender_name,
        send_date: this.convertTo24Hour(message.send_date)
    }));
}

    /**
     * 格式化消息内容
     */
    static formatContent(content) {
        // 移除AI消息中的技术信息
        return content.split('\nToday\'s Wisdom:')[0]
            .replace(/_+\n/g, '')
            .trim();
    }

    /**
     * 解析日期
     */
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
     * 获取默认头像
     */
    static getDefaultAvatar(msg) {
        return msg.is_user
            ? 'static/images/user-avatar.png'
            : 'static/images/ai-avatar.png';
    }

    /**
     * 渲染消息到聊天区域
     */
    // static renderMessages(messages) {

    //     const chatArea = document.querySelector('.chat-area');
    //     if (!chatArea) return;

    //     chatArea.innerHTML = messages.map(msg => {

    //         return `
    //             <div class="chat-message ${msg.is_user ? 'user-message' : 'ai-message'} ">
    //                 <div class="message-content">
    //                     <div class="message-header">
    //                         <span class="sender-name">${msg.sender_name}</span>
    //                         <span class="message-time">${msg.send_date}</span>
    //                     </div>
    //                     <p>${msg.is_user ? msg.live_message : marked.parse(msg.live_message)}</p>
    //                 </div>
    //             </div>
    //         `;
    //     }).join('');

    //     chatArea.scrollTop = chatArea.scrollHeight;
    // }
    static renderMessages(messages) {

        const chatArea = document.querySelector('.chat-area');
        if (!chatArea) return;

        chatArea.innerHTML = messages.map(msg => {
            const messageContent = msg.live_message_html === "" ? msg.live_message : msg.live_message_html;
            return `
                <div class="chat-message ${msg.is_user ? 'user-message' : 'ai-message'} ">
                    <div class="message-content">
                        <div class="message-header">
                            <span class="sender-name">${msg.sender_name}</span>
                            <span class="message-time">${msg.send_date}</span>
                        </div>
                        <div class="mes_text">
                            ${messageContent}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        chatArea.scrollTop = chatArea.scrollHeight;
    }

    /**
     * 初始化历史消息
     */
    static async init(room_name) {
        const messages = await this.fetchChatHistory(room_name);
        this.renderMessages(messages);
    }
}

export default ChatLiveManager;