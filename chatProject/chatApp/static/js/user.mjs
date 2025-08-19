

class UserManager {
    static async checkLogin() {
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
            this.updateUI(data.data.user_info);


        } catch (error) {
            console.error('Auth error:', error);
            this.showGuestUI();
        }
    }

    static updateUI(userInfo) {
        document.getElementById('username').textContent = userInfo.uname;
        document.getElementById('googleLoginLink').style.display = userInfo.status ? 'none' : 'block';
        document.getElementById('logoutLink').style.display = userInfo.status ? 'block' : 'none';
        document.getElementById('diamond').textContent = userInfo.coin_num;
    }

    static async logout() {
        try {
            const response = await fetch('/api/users/login_out/', {
                method: 'get',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'  // 确保携带cookie
            });

            const data = await response.json();

            if (data.code === 0) {
                this.showGuestUI();
                // 可以添加登出成功后的回调或页面跳转
                window.location.reload(); // 刷新页面更新状态
            } else {
                console.error('Logout failed:', data.message);
            }
        } catch (error) {
            console.error('Logout error:', error);
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
        document.getElementById('username').textContent = 'Guest';
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
            // 1. 获取 Google 登录 URL
            const response = await fetch('/api/users/google_login_url/');
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


}
// 直接绑定点击事件
document.addEventListener('DOMContentLoaded', () => {
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