#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from helper_md_doc.helper_html_doc import embed_images_as_base64
from playwright.async_api import async_playwright
import argparse
import asyncio
import concurrent.futures
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

spec = importlib.util.spec_from_file_location(
    "requirements_rnac", os.path.join(
        os.path.dirname(__file__), "requirements_rnac.py")
)
requirements_rnac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(requirements_rnac)
requirements_rnac.check_and_install_dependencies()


logging.basicConfig(level=logging.INFO, format="%(message)s")


async def _wait_until_assets_ready(page) -> None:
    await page.evaluate(
        """async () => {
            await document.fonts.ready;
            await Promise.all(
                Array.from(document.images).map((image) => {
                    if (image.complete) {
                        return Promise.resolve();
                    }
                    return new Promise((resolve) => {
                        image.addEventListener('load', resolve, { once: true });
                        image.addEventListener('error', resolve, { once: true });
                    });
                })
            );
        }"""
    )


def _html_text_to_pdf(html_text: str, output_path: str, base_dir: Optional[str] = None) -> str:
    resolved_base_dir = os.path.abspath(base_dir) if base_dir else os.getcwd()
    rendered_html = embed_images_as_base64(html_text, resolved_base_dir)

    async def _run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(rendered_html, wait_until="networkidle")
            await _wait_until_assets_ready(page)
            await page.emulate_media(media="screen")
            await page.pdf(path=output_path, format="A4", print_background=True)
            await page.close()
            await browser.close()

    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())
        loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(_run_in_thread).result()

    logging.info(f"변환 완료: {output_path}")
    return output_path


def html_to_pdf(html_path: str, output_path: Optional[str] = None) -> str:
    logging.info(f"HTML 읽기: {html_path}")
    with open(html_path, "r", encoding="utf-8") as file:
        html_text = file.read()

    resolved_output_path = output_path or os.path.splitext(html_path)[
        0] + ".pdf"
    base_dir = os.path.dirname(os.path.abspath(html_path))
    return _html_text_to_pdf(html_text, resolved_output_path, base_dir=base_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="HTML(.html)을 PDF로 변환합니다.")
    parser.add_argument("input", help="입력 HTML 파일 경로 (.html)")
    parser.add_argument("-o", "--output", help="출력 PDF 파일 경로 (.pdf)")
    args = parser.parse_args()

    in_path = args.input
    if not os.path.isfile(in_path):
        print(f"파일을 찾을 수 없습니다: {in_path}", file=sys.stderr)
        sys.exit(1)

    html_to_pdf(in_path, args.output)


if __name__ == "__main__":
    main()
