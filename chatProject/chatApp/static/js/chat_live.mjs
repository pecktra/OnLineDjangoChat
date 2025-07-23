/**
 * 直播间历史消息管理模块 (增强版)
 */
class ChatLiveManager {
    /**
     * 获取并处理历史消息
     * @param {string} roomId 直播间ID
     * @returns {Promise<Array>} 处理后的消息数组
     */
    static async fetchChatHistory(roomId) {
        try {
            // 模拟数据 - 实际替换为真实API请求
            const mockResponse = {
                code: 0,
                data: {
                    chat_info: [
                        {
                            uid: "1",
                            name: "pride",
                            is_user: true,
                            is_system: false,
                            send_date: "July 11, 2025 5:51pm",
                            mes: "哈喽",
                            extra: { isSmallSys: false, reasoning: "" },
                            force_avatar: "User Avatars/user-default.png"
                        },
                        {
                            uid: "2",
                            name: "Seraphina",
                            is_user: false,
                            send_date: "July 11, 2025 6:13pm",
                            mes: "Um...thanks ? But what was that exactly?...", // 截短示例
                            extra: {
                                api: "koboldhorde",
                                model: "Skyfall-36B-v2",
                                reasoning: ""
                            }
                        }
                        ,
                        {
                            uid: "3",
                            name: "Seraphina",
                            is_user: false,
                            send_date: "July 11, 2025 6:13pm",
                            mes: "Um...thanks ? But what was that exactly?11111111111111111111111111111111111111112222222222222222222222222222222222222222222222222222222222222222222222222", // 截短示例
                            extra: {
                                api: "koboldhorde",
                                model: "Skyfall-36B-v2",
                                reasoning: ""
                            }
                        }
                        ,
                        {
                            uid: "4",
                            name: "Seraphina",
                            is_user: false,
                            send_date: "July 11, 2025 6:13pm",
                            mes: "Um...thanks ? But what was that exactly?...", // 截短示例
                            extra: {
                                api: "koboldhorde",
                                model: "Skyfall-36B-v2",
                                reasoning: ""
                            }
                        }
                    ]
                }
            };

            // 正式环境请取消注释以下代码 ▼
            // const response = await fetch('/api/live/get_live_chat_history', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ room_id: roomId })
            // });
            // if (!response.ok) throw new Error('Network error');
            // const mockResponse = await response.json();

            return mockResponse.code === 0
                ? this.processMessages(mockResponse.data.chat_info)
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
    static processMessages(rawMessages) {
        return rawMessages.map(msg => ({
            id: msg.uid + '_' + Date.now(), // 唯一ID
            sender: msg.name,
            isUser: msg.is_user,
            isSystem: msg.is_system || false,
            avatar: msg.force_avatar || this.getDefaultAvatar(msg),
            content: this.formatContent(msg.mes),
            timestamp: this.parseDate(msg.send_date),
            meta: {
                model: msg.extra?.model,
                reasoning: msg.extra?.reasoning
            }
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
    static parseDate(dateStr) {
        try {
            return new Date(dateStr).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });
        } catch {
            return '刚刚';
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
    static renderMessages(messages) {
        const chatArea = document.querySelector('.chat-area');
        if (!chatArea) return;

        chatArea.innerHTML = messages.map(msg => {
            const isShort = msg.content.length < 15;
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
        }).join('');

        chatArea.scrollTop = chatArea.scrollHeight;
    }


    /**
     * 初始化历史消息
     */
    static async init(roomId) {
        const messages = await this.fetchChatHistory(roomId);
        this.renderMessages(messages);
    }
}

export default ChatLiveManager;