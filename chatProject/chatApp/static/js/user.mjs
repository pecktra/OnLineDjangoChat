
class UserManager {
    static async checkLogin() {
        try {
            // const response = await fetch('/api/users/is_login');
            // const data = await response.json();
            const data = {
                code: 0,
                data: {
                    user_info: {
                        uid: "张三",
                        status: false,  // 已登录
                        uname: "张三"
                    }
                }
            };
            if (data.code === 0) {
                this.updateUI(data.data.user_info);
            } else {
                this.showGuestUI();
            }
        } catch (error) {
            console.error('Auth error:', error);
            this.showGuestUI();
        }
    }

    static updateUI(userInfo) {
        document.getElementById('username').textContent = userInfo.uname;
        document.getElementById('loginLink').style.display = userInfo.status ? 'none' : 'block';
        document.getElementById('logoutLink').style.display = userInfo.status ? 'block' : 'none';
    }

    static showGuestUI() {
        document.getElementById('username').textContent = '游客';
        document.getElementById('loginLink').style.display = 'block';
        document.getElementById('logoutLink').style.display = 'none';
    }




    static async logout() {
        try {
            const response = await fetch('/api/users/login_out', {
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

}

// 导出模块
export default UserManager;