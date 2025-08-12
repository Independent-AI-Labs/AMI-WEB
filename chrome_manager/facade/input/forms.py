"""Form interaction and input controls."""

import asyncio
from pathlib import Path

from loguru import logger
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.ui import Select, WebDriverWait

from ...utils.exceptions import InputError
from ..base import BaseController


class FormsController(BaseController):
    """Handles form interactions and input controls."""

    async def select_option(self, selector: str, value: str | None = None, text: str | None = None, index: int | None = None) -> None:
        """Select an option from a dropdown.

        Args:
            selector: CSS selector for the select element
            value: Option value to select
            text: Visible text to select
            index: Index of option to select
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            loop = asyncio.get_event_loop()
            select = Select(element)

            if value is not None:
                await loop.run_in_executor(None, select.select_by_value, value)
            elif text is not None:
                await loop.run_in_executor(None, select.select_by_visible_text, text)
            elif index is not None:
                await loop.run_in_executor(None, select.select_by_index, index)
            else:
                raise InputError("Must specify value, text, or index")

            self.instance.update_activity()
            logger.debug(f"Selected option in: {selector}")

        except Exception as e:
            logger.error(f"Select option failed for {selector}: {e}")
            raise InputError(f"Failed to select option in {selector}: {e}") from e

    async def upload_file(self, selector: str, file_path: str) -> None:
        """Upload a file to a file input.

        Args:
            selector: CSS selector for the file input
            file_path: Path to the file to upload
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        # Validate file path
        path = Path(file_path)
        if not path.exists():
            raise InputError(f"File not found: {file_path}")
        if not path.is_file():
            raise InputError(f"Path is not a file: {file_path}")

        # Convert to absolute path for browser
        absolute_path = str(path.absolute())

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, element.send_keys, absolute_path)

            self.instance.update_activity()
            logger.debug(f"Uploaded file to: {selector}")

        except Exception as e:
            logger.error(f"File upload failed for {selector}: {e}")
            raise InputError(f"Failed to upload file to {selector}: {e}") from e

    async def check_checkbox(self, selector: str) -> None:
        """Check a checkbox if it's not already checked.

        Args:
            selector: CSS selector for the checkbox
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                if not element.is_selected():
                    element.click()
            else:
                loop = asyncio.get_event_loop()
                is_selected = await loop.run_in_executor(None, element.is_selected)
                if not is_selected:
                    await loop.run_in_executor(None, element.click)

            self.instance.update_activity()
            logger.debug(f"Checked checkbox: {selector}")

        except Exception as e:
            logger.error(f"Check checkbox failed for {selector}: {e}")
            raise InputError(f"Failed to check {selector}: {e}") from e

    async def uncheck_checkbox(self, selector: str) -> None:
        """Uncheck a checkbox if it's checked.

        Args:
            selector: CSS selector for the checkbox
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                if element.is_selected():
                    element.click()
            else:
                loop = asyncio.get_event_loop()
                is_selected = await loop.run_in_executor(None, element.is_selected)
                if is_selected:
                    await loop.run_in_executor(None, element.click)

            self.instance.update_activity()
            logger.debug(f"Unchecked checkbox: {selector}")

        except Exception as e:
            logger.error(f"Uncheck checkbox failed for {selector}: {e}")
            raise InputError(f"Failed to uncheck {selector}: {e}") from e

    async def select_radio(self, selector: str) -> None:
        """Select a radio button.

        Args:
            selector: CSS selector for the radio button
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                if not element.is_selected():
                    element.click()
            else:
                loop = asyncio.get_event_loop()
                is_selected = await loop.run_in_executor(None, element.is_selected)
                if not is_selected:
                    await loop.run_in_executor(None, element.click)

            self.instance.update_activity()
            logger.debug(f"Selected radio button: {selector}")

        except Exception as e:
            logger.error(f"Select radio failed for {selector}: {e}")
            raise InputError(f"Failed to select radio {selector}: {e}") from e

    async def get_form_values(self, form_selector: str) -> dict[str, str]:
        """Get all values from a form.

        Args:
            form_selector: CSS selector for the form

        Returns:
            Dictionary of field names/IDs to values
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        script = f"""
        const form = document.querySelector('{form_selector}');
        if (!form) return null;

        const values = {{}};
        const inputs = form.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {{
            const key = input.name || input.id || input.className;
            if (input.type === 'checkbox' || input.type === 'radio') {{
                values[key] = input.checked;
            }} else {{
                values[key] = input.value;
            }}
        }});

        return values;
        """

        try:
            if self._is_in_thread_context():
                return self.driver.execute_script(script)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.driver.execute_script, script)

        except Exception as e:
            logger.error(f"Get form values failed: {e}")
            raise InputError(f"Failed to get form values: {e}") from e

    async def submit_form(self, selector: str) -> None:
        """Submit a form.

        Args:
            selector: CSS selector for the form or submit button
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            element = await self._find_element(selector)
            if not element:
                raise InputError(f"Element not found: {selector}")

            if self._is_in_thread_context():
                element.submit()
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, element.submit)

            self.instance.update_activity()
            logger.debug(f"Submitted form: {selector}")

        except Exception as e:
            logger.error(f"Form submit failed for {selector}: {e}")
            raise InputError(f"Failed to submit form {selector}: {e}") from e

    async def fill_form(self, form_data: dict[str, str | bool], submit: bool = False) -> None:  # noqa: C901
        """Fill a form with provided data.

        Args:
            form_data: Dictionary mapping selectors to values
            submit: Whether to submit the form after filling
        """
        if not self.driver:
            raise InputError("Browser not initialized")

        try:
            for selector, value in form_data.items():
                element = await self._find_element(selector)
                if not element:
                    logger.warning(f"Form field not found: {selector}")
                    continue

                tag_name = element.tag_name.lower()
                input_type = element.get_attribute("type")

                if tag_name == "select":
                    await self.select_option(selector, text=str(value))
                elif input_type == "checkbox":
                    if value:
                        await self.check_checkbox(selector)
                    else:
                        await self.uncheck_checkbox(selector)
                elif input_type == "radio":
                    if value:
                        await self.select_radio(selector)
                elif input_type == "file":
                    await self.upload_file(selector, str(value))
                else:
                    # Text input, textarea, etc.
                    from .keyboard import KeyboardController

                    keyboard = KeyboardController(self.instance)
                    await keyboard.type_text(selector, str(value), clear=True)

            if submit:
                submit_button = await self._find_element("button[type='submit'], input[type='submit']")
                if submit_button:
                    from .mouse import MouseController

                    mouse = MouseController(self.instance)
                    await mouse.click("button[type='submit'], input[type='submit']")

            self.instance.update_activity()
            logger.debug("Form filled successfully")

        except Exception as e:
            logger.error(f"Fill form failed: {e}")
            raise InputError(f"Failed to fill form: {e}") from e

    async def _find_element(self, selector: str, wait: bool = True, timeout: int = 10) -> WebElement | None:
        """Find an element on the page."""
        try:
            by, value = self._parse_selector(selector)

            if wait:
                wait_obj = WebDriverWait(self.driver, timeout)
                if self._is_in_thread_context():
                    return wait_obj.until(EC.presence_of_element_located((by, value)))
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, wait_obj.until, EC.presence_of_element_located((by, value)))
            return self.driver.find_element(by, value)

        except Exception as e:
            logger.warning(f"Element not found: {selector}: {e}")
            return None
