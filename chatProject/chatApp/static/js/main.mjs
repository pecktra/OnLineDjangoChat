import UserManager from './user.mjs';
import LiveManager from './lives.mjs';  // 注意：这里使用相对路径，不是模板标签
import ChatLiveManager from './chat_live.mjs';
import StreamerInfoManager from "./streamer.mjs";
import ChatUserManager from "./chat_user.mjs";
import WebSocketManager from "./WebSocketManager.mjs";


// 统一初始化函数
function initializeApp() {
    // 1. 用户认证模块
    UserManager.checkLogin();
    UserManager.bindLogoutEvent();

    //直播模块
    LiveManager.init();

    //主播历史聊天
    ChatLiveManager.init('room_123');

    //主播信息端
    StreamerInfoManager.init('room_123')
    //主播用户消息端
    ChatUserManager.init('room_123');


    // 3. 全局工具提示初始化（只需要初始化静态元素）
    initStaticTooltips();

    initWebSocket('room_123');
}
//初始化websocket
function initWebSocket(roomId) {
    const wsManager = new WebSocketManager(roomId);
    wsManager.init();

    // 暴露给全局以便调试（可选）
    window.wsManager = wsManager;
}
// 专门处理静态元素的工具提示
function initStaticTooltips() {
    // 只选择不是由LiveManager动态生成的元素
    const staticTooltips = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]:not(.live-room)'
    );

    staticTooltips.forEach(el => new bootstrap.Tooltip(el));
}

// 单一DOMContentLoaded监听
document.addEventListener('DOMContentLoaded', initializeApp);


