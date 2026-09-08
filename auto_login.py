import os
import sys
import requests
from playwright.sync_api import sync_playwright

def send_telegram_notification(token, chat_id, message):
    """通过 Telegram Bot 发送消息通知"""
    if not token or not chat_id:
        print("[提示] 未配置 Telegram Bot Token 或 Chat ID，已跳过 Telegram 通知。")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("Telegram 通知发送成功！")
        else:
            print(f"Telegram 通知发送失败，错误码: {res.status_code}, 内容: {res.text}")
    except Exception as e:
        print(f"发送 Telegram 通知时发生异常: {e}")

def run():
    email = os.getenv("WISP_EMAIL")
    password = os.getenv("WISP_PASSWORD")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not email or not password:
        print("[错误] 缺少环境变量 WISP_EMAIL 或 WISP_PASSWORD，请先配置 GitHub Secrets！")
        sys.exit(1)

    print("正在启动无头浏览器...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            target_url = "https://wispbyte.com/client/account"
            print(f"正在访问登录页面: {target_url}")
            page.goto(target_url, wait_until="networkidle", timeout=60000)

            # 匹配邮箱输入框
            email_input = page.locator('input[type="email"], input[name="email"], input[name="username"]').first
            email_input.wait_for(state="visible", timeout=15000)
            email_input.fill(email)

            # 匹配密码输入框
            password_input = page.locator('input[type="password"], input[name="password"]').first
            password_input.wait_for(state="visible", timeout=15000)
            password_input.fill(password)

            # 匹配登录按钮并点击
            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign In")').first
            submit_btn.click()

            print("已提交登录，等待页面刷新响应...")
            page.wait_for_load_state("networkidle", timeout=30000)

            # 获取页面信息进行状态验证
            current_url = page.url
            content = page.content().lower()

            # 判断是否登录成功 (不在登录页或包含控制台/退出特征词)
            is_success = "login" not in current_url or "logout" in content or "dashboard" in content or "sign out" in content

            if is_success:
                success_msg = (
                    f"<b>✅ WispByte 自动登录成功通知</b>\n\n"
                    f"<b>账号：</b> <code>{email}</code>\n"
                    f"<b>页面地址：</b> {current_url}\n"
                    f"<b>提示：</b> 您的 WispByte 免费服务已成功续期保活！"
                )
                print(success_msg)
                send_telegram_notification(telegram_token, telegram_chat_id, success_msg)
            else:
                raise Exception("登录提交后页面未改变，可能遇到了密码错误或验证码阻挡。")

        except Exception as e:
            error_msg = (
                f"<b>❌ WispByte 自动登录失败通知</b>\n\n"
                f"<b>账号：</b> <code>{email}</code>\n"
                f"<b>异常信息：</b> {str(e)}"
            )
            print(error_msg)
            send_telegram_notification(telegram_token, telegram_chat_id, error_msg)
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    run()