# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/login.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import asyncio
import functools
import os
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from cache.cache_factory import CacheFactory
from tools import utils
from tools.login_state import (
    clear_file,
    take_screenshot,
    wait_for_sms_code,
    write_state,
)


class XiaoHongShuLogin(AbstractLogin):

    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
        self._state_file = os.getenv("XHS_LOGIN_STATE_FILE", "")
        self._screenshot_file = os.getenv("XHS_SCREENSHOT_FILE", "")
        self._sms_code_file = os.getenv("XHS_SMS_CODE_FILE", "")
        self._remote_browser_url = os.getenv("XHS_REMOTE_BROWSER_URL", "")
        self._use_remote_login = bool(self._state_file)

    def _write_state(self, state: str, message: str, **kwargs) -> None:
        if self._state_file:
            if state in {"sms_needed", "captcha", "manual_required", "waiting_for_scan"}:
                kwargs.setdefault("remote_browser_url", self._remote_browser_url)
                kwargs.setdefault("remote_browser_hint", "可打开远程浏览器完成小红书页面上的验证操作。")
            write_state(self._state_file, state, message, **kwargs)

    async def _take_screenshot(self, element_selector: str | None = None) -> None:
        if self._screenshot_file:
            await take_screenshot(self._screenshot_file, self.context_page, element_selector)


    async def _is_logged_in(self) -> bool:
        """Check if already logged in via UI element or cookie change."""
        try:
            user_profile_selector = "xpath=//a[contains(@href, '/user/profile/')]//span[text()='我']"
            is_visible = await self.context_page.is_visible(user_profile_selector, timeout=500)
            if is_visible:
                return True
        except Exception:
            pass
        return False

    async def _needs_sms_verification(self) -> bool:
        """Check if the page is showing SMS verification or phone input prompt."""
        try:
            page_content = await self.context_page.content()
            keywords = ["短信验证码", "安全验证", "验证码", "手机号验证", "请输入验证码"]
            if any(kw in page_content for kw in keywords):
                return True
            # Check for verification input fields
            for sel in [
                "input[placeholder*='验证码']",
                "input[placeholder*='手机号']",
                "input[type='tel']",
                "input[name*='code']",
                "input[name*='captcha']",
                "input[name*='phone']",
            ]:
                if await self.context_page.is_visible(sel, timeout=200):
                    return True
        except Exception:
            pass
        return False

    async def _has_captcha(self) -> bool:
        """Check if a CAPTCHA challenge is showing."""
        try:
            page_content = await self.context_page.content()
            return "请通过验证" in page_content
        except Exception:
            return False

    async def _is_showing_qrcode(self) -> bool:
        """Check if QR code is still visible (waiting for scan)."""
        try:
            qr = await self.context_page.is_visible("xpath=//img[@class='qrcode-img']", timeout=500)
            return qr
        except Exception:
            return False

    async def _handle_sms_verification(self, no_logged_in_session: str) -> bool:
        """Handle SMS verification with retry support. Returns True if login succeeded."""
        max_attempts = 3

        for attempt in range(max_attempts):
            await self._take_screenshot()
            self._write_state(
                "sms_needed",
                f"请输入短信验证码（第{attempt + 1}次）",
                sms_attempts=attempt,
                max_sms_attempts=max_attempts,
            )
            utils.logger.info(f"[SMS] Waiting for verification code (attempt {attempt + 1}/{max_attempts})...")

            code = None
            initial_mtime = os.path.getmtime(self._sms_code_file) if os.path.exists(self._sms_code_file) else 0.0
            for _ in range(120):
                if await self._is_logged_in():
                    self._write_state("logged_in", "登录成功！")
                    utils.logger.info("[SMS] Login successful via remote browser.")
                    return True

                current_cookie = await self.browser_context.cookies()
                _, cookie_dict = utils.convert_cookies(current_cookie)
                current_web_session = cookie_dict.get("web_session")
                if current_web_session and current_web_session != no_logged_in_session:
                    self._write_state("logged_in", "登录成功！")
                    utils.logger.info("[SMS] Login confirmed by cookie change during remote verification.")
                    return True

                if os.path.exists(self._sms_code_file):
                    current_mtime = os.path.getmtime(self._sms_code_file)
                    if current_mtime != initial_mtime:
                        try:
                            code = open(self._sms_code_file, encoding="utf-8").read().strip()
                        except Exception:
                            code = None
                        if code:
                            break
                await asyncio.sleep(1)

            if not code:
                self._write_state("login_failed", "验证码等待超时")
                utils.logger.info("[SMS] Timed out waiting for verification code.")
                return False

            # Enter the code
            try:
                input_el = await self.context_page.query_selector(
                    "input[placeholder*='验证码'], input[type='tel'], "
                    "input[name*='code'], input[name*='captcha']"
                )
                if input_el:
                    await input_el.fill(code)
                    await asyncio.sleep(0.5)
                    btn = await self.context_page.query_selector(
                        "button[type='submit'], button:has-text('验证'), "
                        "button:has-text('确定'), button:has-text('登录')"
                    )
                    if btn:
                        await btn.click()
                        utils.logger.info("[SMS] Code submitted, waiting for result...")
            except Exception as e:
                utils.logger.error(f"[SMS] Failed to enter code: {e}")

            clear_file(self._sms_code_file)
            await asyncio.sleep(3)

            # Check if logged in after submitting
            if await self._is_logged_in():
                self._write_state("logged_in", "登录成功！")
                utils.logger.info("[SMS] Login successful after verification.")
                return True

            # Check cookie-based login
            current_cookie = await self.browser_context.cookies()
            _, cookie_dict = utils.convert_cookies(current_cookie)
            current_web_session = cookie_dict.get("web_session")
            if current_web_session and current_web_session != no_logged_in_session:
                self._write_state("logged_in", "登录成功！")
                utils.logger.info("[SMS] Login confirmed by cookie change.")
                return True

            # Code was wrong
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                self._write_state(
                    "sms_needed",
                    f"验证码错误，请重新输入（剩余{remaining}次）",
                    sms_attempts=attempt + 1,
                    max_sms_attempts=max_attempts,
                )
                utils.logger.info(f"[SMS] Wrong code, {remaining} attempts remaining.")
            else:
                self._write_state("login_failed", "验证码错误次数过多")
                utils.logger.info("[SMS] Max attempts reached.")
                return False

        return False

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """
        Verify login status using dual-check: UI elements and Cookies.
        With remote login support via structured state files.
        """
        # Take periodic screenshot for remote viewing
        if self._use_remote_login:
            # Screenshot only the QR code element (sharp PNG) during scan phase
            if await self._is_showing_qrcode():
                await self._take_screenshot("xpath=//img[@class='qrcode-img']")
            else:
                await self._take_screenshot()

        # Debug: log page state
        is_logged = await self._is_logged_in()
        needs_sms = await self._needs_sms_verification()
        has_captcha = await self._has_captcha()
        has_qr = await self._is_showing_qrcode()
        url = self.context_page.url
        utils.logger.info(f"[check_login_state] logged_in={is_logged} sms={needs_sms} captcha={has_captcha} qr={has_qr} url={url}")

        # 1. Check UI element
        try:
            user_profile_selector = "xpath=//a[contains(@href, '/user/profile/')]//span[text()='我']"
            is_visible = await self.context_page.is_visible(user_profile_selector, timeout=500)
            if is_visible:
                utils.logger.info("[XiaoHongShuLogin.check_login_state] Login confirmed by UI element.")
                if self._use_remote_login:
                    self._write_state("logged_in", "登录成功！")
                return True
        except Exception:
            pass

        # 2. Check for SMS verification
        if await self._needs_sms_verification():
            if self._use_remote_login:
                utils.logger.info("[check_login_state] SMS verification detected.")
                success = await self._handle_sms_verification(no_logged_in_session)
                if success:
                    return True
                # If failed, the retry decorator will keep trying
            else:
                utils.logger.info("[check_login_state] SMS verification detected (no remote handler).")

        # 3. Check for CAPTCHA
        if await self._has_captcha():
            if self._use_remote_login:
                await self._take_screenshot()
                self._write_state("captcha", "遇到验证码，请在浏览器中手动完成验证")
            utils.logger.info("[check_login_state] CAPTCHA detected.")

        # 4. Update state for waiting-for-scan (no screenshot needed — QR code is served separately)
        if self._use_remote_login and await self._is_showing_qrcode():
            self._write_state("waiting_for_scan", "请使用小红书 App 扫描二维码")

        # 5. Cookie-based fallback
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        current_web_session = cookie_dict.get("web_session")

        if current_web_session and current_web_session != no_logged_in_session:
            utils.logger.info("[XiaoHongShuLogin.check_login_state] Login confirmed by cookie change.")
            if self._use_remote_login:
                self._write_state("logged_in", "登录成功！")
            return True

        return False

    async def begin(self):
        """Start login xiaohongshu"""
        utils.logger.info("[XiaoHongShuLogin.begin] Begin login xiaohongshu ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[XiaoHongShuLogin.begin] Invalid Login Type Currently only supported qrcode or phone or cookies ...")

    async def login_by_mobile(self):
        """Login xiaohongshu by mobile"""
        utils.logger.info("[XiaoHongShuLogin.login_by_mobile] Begin login xiaohongshu by mobile ...")
        await asyncio.sleep(1)
        try:
            login_button_ele = await self.context_page.wait_for_selector(
                selector="xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button",
                timeout=5000
            )
            await login_button_ele.click()
            element = await self.context_page.wait_for_selector(
                selector='xpath=//div[@class="login-container"]//div[@class="other-method"]/div[1]',
                timeout=5000
            )
            await element.click()
        except Exception as e:
            utils.logger.info("[XiaoHongShuLogin.login_by_mobile] have not found mobile button icon and keep going ...")

        await asyncio.sleep(1)
        login_container_ele = await self.context_page.wait_for_selector("div.login-container")
        input_ele = await login_container_ele.query_selector("label.phone > input")
        await input_ele.fill(self.login_phone)
        await asyncio.sleep(0.5)

        send_btn_ele = await login_container_ele.query_selector("label.auth-code > span")
        await send_btn_ele.click()
        sms_code_input_ele = await login_container_ele.query_selector("label.auth-code > input")
        submit_btn_ele = await login_container_ele.query_selector("div.input-container > button")
        cache_client = CacheFactory.create_cache(config.CACHE_TYPE_MEMORY)
        max_get_sms_code_time = 60 * 2
        no_logged_in_session = ""
        while max_get_sms_code_time > 0:
            utils.logger.info(f"[XiaoHongShuLogin.login_by_mobile] get sms code from redis remaining time {max_get_sms_code_time}s ...")
            await asyncio.sleep(1)
            sms_code_key = f"xhs_{self.login_phone}"
            sms_code_value = cache_client.get(sms_code_key)
            if not sms_code_value:
                max_get_sms_code_time -= 1
                continue

            current_cookie = await self.browser_context.cookies()
            _, cookie_dict = utils.convert_cookies(current_cookie)
            no_logged_in_session = cookie_dict.get("web_session")

            await sms_code_input_ele.fill(value=sms_code_value.decode())
            await asyncio.sleep(0.5)
            agree_privacy_ele = self.context_page.locator("xpath=//div[@class='agreements']//*[local-name()='svg']")
            await agree_privacy_ele.click()
            await asyncio.sleep(0.5)

            await submit_btn_ele.click()
            break

        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.info("[XiaoHongShuLogin.login_by_mobile] Login xiaohongshu failed by mobile login method ...")
            if self._use_remote_login:
                self._write_state("login_failed", "手机号登录失败")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(f"[XiaoHongShuLogin.login_by_mobile] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_qrcode(self):
        """login xiaohongshu website and keep webdriver login state"""
        utils.logger.info("[XiaoHongShuLogin.login_by_qrcode] Begin login xiaohongshu by qrcode ...")
        qrcode_img_selector = "xpath=//img[@class='qrcode-img']"

        # find login qrcode
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector=qrcode_img_selector
        )
        if not base64_qrcode_img:
            utils.logger.info("[XiaoHongShuLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
            await asyncio.sleep(0.5)
            login_button_ele = self.context_page.locator("xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button")
            await login_button_ele.click()
            base64_qrcode_img = await utils.find_login_qrcode(
                self.context_page,
                selector=qrcode_img_selector
            )
            if not base64_qrcode_img:
                if self._use_remote_login:
                    self._write_state("login_failed", "无法找到登录二维码")
                sys.exit()

        # get not logged session
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("web_session")

        # show login qrcode
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        # Update state for remote login
        if self._use_remote_login:
            self._write_state("waiting_for_scan", "请使用小红书 App 扫描二维码")

        utils.logger.info(f"[XiaoHongShuLogin.login_by_qrcode] waiting for scan code login, remaining time is 120s")
        utils.logger.info(f"[XiaoHongShuLogin.login_by_qrcode] remote_login={self._use_remote_login}, screenshot_file={self._screenshot_file}")
        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            utils.logger.info("[XiaoHongShuLogin.login_by_qrcode] Login xiaohongshu failed by qrcode login method ...")
            if self._use_remote_login:
                self._write_state("login_failed", "扫码登录超时，请重新尝试")
            sys.exit()

        utils.logger.info("[XiaoHongShuLogin.login_by_qrcode] 扫码登录成功!")
        wait_redirect_seconds = 5
        utils.logger.info(f"[XiaoHongShuLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_cookies(self):
        """login xiaohongshu website by cookies"""
        utils.logger.info("[XiaoHongShuLogin.login_by_cookies] Begin login xiaohongshu by cookie ...")
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            if key != "web_session":
                continue
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".rednote.com" if config.XHS_INTERNATIONAL else ".xiaohongshu.com",
                'path': "/"
            }])
