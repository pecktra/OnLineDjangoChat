import UserManager from './user.mjs';
import LiveManager from './lives.mjs';  // 注意：这里使用相对路径，不是模板标签
import ChatLiveManager from './chat_live.mjs';
import StreamerInfoManager from "./streamer.mjs";
import ChatUserManager from "./chat_user.mjs";
import WebSocketManager from "./WebSocketManager.mjs";


// 统一初始化函数
async  function initializeApp() {

    const room_name = window.GLOBAL_ROOM_NAME;
    const room_id = window.GLOBAL_ROOM_ID;


    // 1. 用户认证模块
    await UserManager.checkLogin();
    UserManager.bindLogoutEvent();
    
    

    //直播模块
    LiveManager.init();

    //主播历史聊天
    ChatLiveManager.init(room_name);

    //主播信息端
    StreamerInfoManager.init(room_name)
    //主播用户消息端
    ChatUserManager.init(room_name);




    // 3. 全局工具提示初始化（只需要初始化静态元素）
    initStaticTooltips();
    const userName = window.GLOBAL_USER_NAME;
    initWebSocket(room_id,room_name,userName);
}
//初始化websocket
function initWebSocket(room_id,room_name,userName) {
    console.log("initWebSocket")
    console.log(userName)
    const wsManager = new WebSocketManager(room_id,room_name,userName);
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


