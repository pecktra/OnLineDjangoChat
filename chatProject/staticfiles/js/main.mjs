import UserManager from './user.mjs';
import LiveManager from './lives.mjs';  // 注意：这里使用相对路径，不是模板标签
import ChatLiveManager from './chat_live.mjs';
import StreamerInfoManager from "./streamer.mjs";
import ChatUserManager from "./chat_user.mjs";
import WebSocketManager from "./WebSocketManager.mjs";
import RewardManager from "./reward_manager.mjs";
import PayManager from "./pay.mjs";



// 统一初始化函数
async  function initializeApp() {
    vhCheck({
        cssVarName: '--vh'  // 可选，默认就是 --vh
    });

    const room_id = window.GLOBAL_ROOM_ID;


    // 1. 用户认证模块
    await UserManager.checkLogin(room_id);
    UserManager.bindLogoutEvent();
    // await UserManager.initGoogleLogin()




    //直播模块
    LiveManager.init();
    LiveManager.initFollowsButton();
    LiveManager.initSubscriptionsButton();
    LiveManager.initRoomButton()
    let is_home = false; // Use let instead of const

    if (room_id == "None") {
        is_home = true; // Reassign to true inside the block
        await LiveManager.loadHome(is_home);
        // LiveManager.initHomeButton(is_home)
        LiveManager.initRedirectHomeButton()
        return;
    }
    // LiveManager.initHomeButton(is_home)

    LiveManager.initRedirectHomeButton()


    // 根据 room_id 控制显示
    // const homepageContainer = document.getElementById('homepageContainer');
    // const totalChat = document.querySelector('.total-chat');
    // if (!room_id) {
    //     if (homepageContainer) homepageContainer.style.display = 'flex';
    //     if (totalChat) totalChat.style.display = 'none';
    //     await LiveManager.loadHome();
    //     return;
    // } else {
    //     if (totalChat) totalChat.style.display = 'flex';
    //     if (homepageContainer) homepageContainer.style.display = 'none';
    // }





    //主播历史聊天
    // ChatLiveManager.init(room_id);

    //主播信息端
    await StreamerInfoManager.init(room_id)
    // 分支按钮
    // StreamerInfoManager.initBranchButton()

    // 在 get_live_info 执行完成后初始化 fork chat inline
    if (typeof window.initForkChatInline === 'function') {
        window.initForkChatInline();
    }



    //主播用户消息端
    ChatUserManager.init(room_id);

    //打赏
    RewardManager.init()

    //支付
    PayManager.init('pay-modal', 'pay-form', 'close-pay-modal')




    // 3. 全局工具提示初始化（只需要初始化静态元素）
    initStaticTooltips();
    const userName = window.GLOBAL_USER_NAME;
    const room_name = window.GLOBAL_ROOM_NAME;

    initWebSocket(room_id,room_name,userName);
}
// 初始化聊天（已改为 HTTP 轮询实现，但保留函数名以兼容）
function initWebSocket(room_id,room_name,userName) {
    console.log(userName)
    const wsManager = new WebSocketManager(room_id,room_name,userName);
    wsManager.init();
    window.wsManager = wsManager; // 可用于调试
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


