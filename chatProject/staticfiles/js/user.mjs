

class UserManager {
    static async checkLogin(room_id) {
        try {
            const response = await fetch('/api/users/is_google_logged_in/');
            const data = await response.json();
            // const data = {
            //     code: 0,
            //     data: {
            //         user_info: {
            //             uid: "张三",
            //             status: false,  // 已登录
            //             uname: "张三"
            //         }
            //     }
            // };
            window.GLOBAL_USER_NAME = data?.data?.user_info?.uname
            window.GLOBAL_USER_ID = data?.data?.user_info?.uid

            this.updateUI(room_id,data.data.user_info);


        } catch (error) {
            console.error('Auth error:', error);
            this.showGuestUI();
        }
    }

    static updateUI(room_id,userInfo) {
        // document.getElementById('username').textContent = userInfo.uname;
        document.getElementById('googleLoginLink').style.display = userInfo.status ? 'none' : 'block';
        document.getElementById('logoutLink').style.display = userInfo.status ? 'block' : 'none';
        if(room_id != "None"){
            document.getElementById('diamond').textContent = userInfo.coin_num;
        }

    }

    static async logout() {
        try {

            const response = await fetch('/api/users/google_logout/');
            window.location.href = '/';

        } catch (error) {
            console.log('Logout failed:', error);

        }
    }
    //退出登录
    static bindLogoutEvent() {
        const logoutLink = document.getElementById('logoutLink');
        if (logoutLink) {
            logoutLink.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.logout();
            });
        }
    }

    static showGuestUI() {
        // document.getElementById('username').textContent = 'Guest';
        document.getElementById('logoutLink').style.display = 'none';
        document.getElementById('googleLoginLink').style.display = 'block';
    }

    // 新增的 Google 登录方法
    static async initGoogleLogin() {
        const googleLoginLink = document.getElementById('googleLoginLink');
        if (googleLoginLink) {
            googleLoginLink.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.handleGoogleLogin();
            });
        }
    }

    static async handleGoogleLogin() {

        try {
            // 1. 获取 Google 登录 URL，添加 ref 参数
            const refFromWindow = window.REF_DATA || '';
            let url = '/api/users/google_login_url/';
            if (refFromWindow) {
                const urlObj = new URL(url, window.location.origin);
                urlObj.searchParams.set('ref', refFromWindow);
                url = urlObj.pathname + urlObj.search;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.data.authorization_url) {
                // 2. 重定向到 Google 登录页面
                window.location.href = data.data.authorization_url;
            } else {
                console.error('No authorization URL received');
            }
        } catch (error) {
            console.error('Google login error:', error);
        }
    }


    // static async loadFollows() {
    //     // 检查用户是否登录
    //     if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
    //         alert('please log in first');
    //         return
    //     }

    //     // Manually show the modal
    //     const modalElement = document.getElementById('followsModal');
    //     const modal = new bootstrap.Modal(modalElement);
    //     modal.show();

    //     try {
    //         const response = await fetch('/api/follow_live/get_followed_rooms/', {
    //             method: 'GET',
    //             headers: {
    //                 'Content-Type': 'application/json'
    //             }
    //         });
    //         const result = await response.json();
    //         const tableBody = document.getElementById('followsTable');
    //         if (result.code === 0) {

    //             tableBody.innerHTML = ''; // Clear existing content

    //             if (result.data.length === 0) {
    //                 tableBody.innerHTML = '<tr><td colspan="2">暂无关注房间</td></tr>';
    //             } else {
    //                 result.data.forEach(room => {
    //                     const row = document.createElement('tr');
    //                     row.innerHTML = `
    //                         <td>${room.room_name}</td>
    //                         <td>${new Date(room.followed_at).toLocaleString('zh-CN')}</td>

    //                     `;
    //                     tableBody.appendChild(row);
    //                 });
    //             }
    //         } else {
    //             tableBody.innerHTML = '<tr><td colspan="2">暂无关注房间</td></tr>';
    //         }
    //     } catch (error) {
    //         console.error('加载关注列表失败:', error);
    //         alert('无法加载关注列表');
    //     }
    // }





    // static async loadSubscriptions() {
    //     // 检查用户是否登录
    //     if (!window.GLOBAL_USER_ID || window.GLOBAL_USER_ID === 'null') {
    //         alert('please log in first');
    //         return
    //     }
    //     // Manually show the modal
    //     const modalElement = document.getElementById('subscriptionsModal');
    //     const modal = new bootstrap.Modal(modalElement, { backdrop: 'static' });
    //     modal.show();

    //     try {
    //         const response = await fetch('/api/subscription/get_subscriptions/', {
    //             method: 'GET',
    //             headers: {
    //                 'Content-Type': 'application/json'
    //             }
    //         });
    //         const result = await response.json();
    //         const tableBody = document.getElementById('subscriptionsTable');
    //         if (result.code === 0) {

    //             tableBody.innerHTML = ''; // Clear existing content

    //             if (result.data.subscriptions.length === 0) {
    //                 tableBody.innerHTML = '<tr><td colspan="5">暂无订阅</td></tr>';
    //             } else {
    //                 result.data.subscriptions.forEach(sub => {
    //                     const row = document.createElement('tr');
    //                     row.innerHTML = `
    //                         <td>${sub.anchor_id}</td>
    //                         <td>${sub.anchor_name}</td>
    //                         <td>${sub.diamonds_paid}</td>
    //                         <td>${new Date(sub.subscription_date).toLocaleString('zh-CN')}</td>
    //                         <td>${new Date(sub.subscription_end_date).toLocaleString('zh-CN')}</td>
    //                     `;
    //                     tableBody.appendChild(row);
    //                 });
    //             }
    //         } else {
    //             tableBody.innerHTML = '<tr><td colspan="5">暂无订阅</td></tr>';
    //         }
    //     } catch (error) {
    //         console.error('加载订阅列表失败:', error);
    //         alert('无法加载订阅列表');
    //     }
    // }






}
// 直接绑定点击事件
document.addEventListener('DOMContentLoaded', () => {
    console.log("333")
    // 从当前页面 URL 解析 ref 并写入 window.REF_DATA
    try {
        const currentUrl = new URL(window.location.href);
        const refParam = currentUrl.searchParams.get('ref');
        if (refParam) {
            window.REF_DATA = refParam;
        }
    } catch (e) {
        console.warn('Failed to parse ref from current URL:', e);
    }
    const googleLoginLink = document.getElementById('googleLoginLink');
    if (googleLoginLink) {
        googleLoginLink.addEventListener('click', async (e) => {
            e.preventDefault();
            await UserManager.handleGoogleLogin();
        });
    } else {
        console.warn('Google login link element not found');
    }
});
// 导出模块
export default UserManager;
