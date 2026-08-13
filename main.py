#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
tchmaterial-parser-kiss 是 tchMaterial-parser (4e53a3b5fa12584d0d5b2189792bb5576529e3fd) 的 fork
原项目 URL: https://github.com/happycola233/tchMaterial-parser
原项目贡献者: 晨叶梦春(https://github.com/wuziqian211)
              肥宅水水呀(https://github.com/happycola233)
              以及 https://github.com/happycola233/tchMaterial-parser/graphs/contributors 中的用户
"""
import os, sys, platform
import base64, json, re, requests
import traceback
from urllib.parse import urlparse, parse_qs
from pypdf import PdfReader, PdfWriter
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from rich.prompt import Confirm
from rich.progress import Progress
from rich import print as rprint
from rich.console import Console
from rich.syntax import Syntax
from rich.rule import Rule

texts = {
    'add_item': '在输入区内，你可以\n 1. 直接写下需要解析的 URL; \n 2. 按 Tab 键搜索资源(Enter 键选中)\n 3. 输入 set 来设置 Access Token\n 4. 输入 erase 清除保存的 Access Token\n 5. 输入 exit 退出\n> ',
    'wrong_url_or_res': '输入的不是正确的 URL/资源项, 请重新输入',
    'is_bookmark': '本资源需要添加书签吗？',
    'adding_bookmark': '正在添加书签...',
    'file_path_is': '文件已下载到',
    'following_failure': '以下文件下载失败',
    'copy_code_guide': '请在用浏览器在 [link=https://auth.smartedu.cn/uias/login]https://auth.smartedu.cn/uias/login[/link] 登录，在控制台输入上面代码得到 Access Token，粘贴到这里',
    'get_res_list_failure': '获取资源列表失败，请重新打开本程序',
    'ready_to_erase': '确定删除 Access Token 吗？',
    'erase_success': '已成功删除 Access Token',
}
texts_en = {
    'add_item': 'In the input field, you can\n 1. Directly type the URL to be parsed;\n 2. Press Tab to search for resources (press Enter to select);\n 3. Type "set" to set the Access Token;\n 4. Type "erase" to remove the saved Access Token;\n 5. Type "exit" to exit the program\n> ',
    'wrong_url_or_res': 'The URL/Resources Item you inputted is wrong, please input again',
    'is_bookmark': 'Need you add bookmarks to this resources?',
    'adding_bookmark': 'Adding bookmarks...',
    'file_path_is': 'File has been downloaded in',
    'following_failure': 'The following files failed to be download',
    'copy_code_guide': 'Login in [link=https://auth.smartedu.cn/uias/login]https://auth.smartedu.cn/uias/login[/link] in your browser, input the above code to your browser Console, and paste the Access Token you got here.',
    'get_res_list_failure': 'Failed to get the resources list, please restart this program.',
    'ready_to_erase': 'Are you sure that you want to remove the Access Token? ',
    'erase_success': 'Removed Access Token successfully.',
}
os_name = platform.system()
task = None
is_debug = False
progress = Progress()

try:
    import winreg
except Exception as e:
    winreg = None

def print_error(e: Exception) -> None: # 打印错误信息到控制台
    if sys.stderr and is_debug: # 无控制台运行时 sys.stderr 可能为 None，仅 debug 模式显示
        traceback.print_exception(e)
def print_error_info(info: str) -> None:
    rprint(f"[red]{info}[/red]")
def print_info(info: str) -> None:
    rprint(f"[green]{info}[/green]")

def parse(url: str, bookmarks: bool) -> list[tuple[str, str, str, list[dict]]] | None: # 解析资源，获取资源下载链接
    try:
        resources_info: list[tuple[str, str, str, list[dict]]] = []

        # 1. 提取 URL 中的 contentId 与 contentType
        content_id: str | None = None
        content_type: str | None = None

        params = parse_qs(urlparse(url, "https").query)

        if "contentId" in params:
            content_id = params["contentId"][0]
        elif re.search(r"^https?://([^/]+)/syncClassroom/classActivity", url): # 课程资源
            content_type = "national_lesson"
            if "activityId" in params:
                content_id = params["activityId"][0]
            else:
                return None
        elif re.search(r"^https?://([^/]+)/syncClassroom/prepare/detail", url): # 备课资源（课件、教学设计等）
            content_type = "prepare_sub_type"
            if "resourceId" in params:
                content_id = params["resourceId"][0]
            else:
                return None
        elif re.search(r"^https?://([^/]+)/syncClassroom/detail", url): # 知识点微课等课程资源
            if "resourceId" in params and "resourceType" in params:
                content_id = params["resourceId"][0]
                content_type = params["resourceType"][0]
            else:
                return None
        elif re.search(r"^https?://([^/]+)/qualityCourse", url): # 精品课
            content_type = "quality_course"
            if "courseId" in params:
                content_id = params["courseId"][0]
            else:
                return None
        else:
            return None

        if not content_type:
            if "contentType" in params:
                content_type = params["contentType"][0]
            else:
                content_type = "assets_document"

        # 2. 获取资源的信息
        # 返回数据示例：
        """
        {
            "id": "4f64356a-8df7-4579-9400-e32c9a7f6718",
            // ...
            "ti_items": [
                {
                    "ti_md5": "497110473b106d28651c41c14aa6d942",
                    "ti_size": 13075391,
                    "ti_storage": "cs_path:${ref-path}/edu_product/esp/assets/4f64356a-8df7-4579-9400-e32c9a7f6718.pkg/义务教育教科书 语文 八年级 上册_1756191813436.pdf", // 资源文件地址
                    "ti_storages": [
                        "https://r1-ndr-private.ykt.cbern.com.cn/edu_product/esp/assets/4f64356a-8df7-4579-9400-e32c9a7f6718.pkg/义务教育教科书 语文 八年级 上册_1756191813436.pdf",
                        "https://r2-ndr-private.ykt.cbern.com.cn/edu_product/esp/assets/4f64356a-8df7-4579-9400-e32c9a7f6718.pkg/义务教育教科书 语文 八年级 上册_1756191813436.pdf",
                        "https://r3-ndr-private.ykt.cbern.com.cn/edu_product/esp/assets/4f64356a-8df7-4579-9400-e32c9a7f6718.pkg/义务教育教科书 语文 八年级 上册_1756191813436.pdf"
                    ],
                    "ti_file_flag": "source",
                    "ti_is_source_file": true,
                    // ...
                    "ti_format": "pdf",
                    // ...
                },
                {
                    // ...（和上一个元素组成一样）
                }
            ],
            // ...
            "title": "（根据2022年版课程标准修订）义务教育教科书·语文八年级上册",
            // ...
        }
        """
        # 其中 $.ti_items 的每一项对应一个资源

        if re.search(r"^https?://([^/]+)/tchMaterial/detail", url) and content_type == "assets_document": # 对普通电子课本的解析
            response = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrv2/resources/tch_material/details/{content_id}.json")
        elif content_type == "national_lesson": # 对课程资源的解析
            response = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrv2/national_lesson/resources/details/{content_id}.json")
        elif content_type == "quality_course": # 对精品课的解析
            response = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrv2/resources/{content_id}.json")
        elif content_type == "prepare_sub_type": # 对备课资源的解析
            response = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrv2/prepare_sub_type/resources/details/{content_id}.json")
        elif re.search(r"^https?://([^/]+)/syncClassroom/detail", url): # 知识点微课等
            response = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrv2/{content_type}/resources/details/{content_id}.json")
        else: # 对专题课程（含电子课本、视频等）、其他类型资源的解析
            response = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/special_edu/resources/details/{content_id}.json")

        data: dict = response.json()

        # 3. 获取资源标题、下载链接及章节目录
        def get_resource_info(resource_data: dict, root_title: str | None = None) -> tuple[str, str, str, list[dict]] | None:
            title_data = resource_data.get("global_title")
            resource_title: str = title_data.get("zh-CN") or title_data.get("en") if isinstance(title_data, dict) else title_data or resource_data.get("title") or resource_data.get("id")
            title = f"{root_title} - {resource_title}" if root_title else resource_title
            resource_url: str | None = None
            resource_format = "pdf"

            for item in resource_data["ti_items"]: # 寻找存有资源链接列表的项
                if not item["ti_is_source_file"]:
                    continue

                resource_format = item.get("ti_format") or "pdf"
                if resource_format == "folder":
                   continue

                resource_url = item.get("ti_storage") # 获取并构造资源的 URL
                if resource_url:
                    resource_url = resource_url.replace("cs_path:${ref-path}", "https://r1-ndr-private.ykt.cbern.com.cn")
                else:
                    resource_url = next((url for url in item["ti_storages"] if url), None)
                    if not resource_url:
                        continue
                break

            if not resource_url: # 使用不同的判断条件寻找源文件
                for item in resource_data["ti_items"]:
                    if item["ti_file_flag"] not in ("source", "pdf", "ppt", "pptx", "doc", "docx"):
                        continue

                    resource_format = item.get("ti_format") or "pdf"
                    if resource_format == "folder":
                      continue

                    resource_url = item.get("ti_storage")
                    if resource_url:
                        resource_url = resource_url.replace("cs_path:${ref-path}", "https://r1-ndr-private.ykt.cbern.com.cn")
                    else:
                        resource_url = next((url for url in item["ti_storages"] if url), None)
                        if not resource_url:
                            continue
                    break

            if not resource_url:
                return None

            # 通过 ebook_mapping + tree 接口组合获取章节目录
            chapters: list[dict] = []
            if bookmarks and resource_format == "pdf":
                try:
                    mapping_url: str | None = None
                    for item in resource_data["ti_items"]:
                        if item["ti_file_flag"] == "ebook_mapping":
                            mapping_url = item.get("ti_storage") # 形如 https://r1-ndr-private.ykt.cbern.com.cn/edu_product/esp/assets/*.pkg/ebook_mapping.txt
                            if mapping_url:
                                mapping_url = mapping_url.replace("cs_path:${ref-path}", "https://r1-ndr-private.ykt.cbern.com.cn")
                            else:
                                mapping_url = next((url for url in item["ti_storages"] if url), None)
                            break

                    if mapping_url:
                        # a. 下载 mapping 文件获取页码和 ebook_id
                        map_resp = session.get(mapping_url)
                        map_data: dict = map_resp.json()
                        ebook_id: str = map_data.get("ebook_id")

                        # 构建 node_id 到 page_number 的映射字典
                        # 格式: [{ "node_id": "...", "page_number": 1 }, ...]
                        page_map: list[dict] = []
                        if map_data.get("mappings"):
                            for m in map_data["mappings"]:
                                page_map.append({ "node_id": m["node_id"], "page_number": m.get("page_number", 1) })

                        # b. 如果有 ebook_id，在课程接口下载完整的目录树（tree API）
                        if ebook_id:
                            tree_resp = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrv2/national_lesson/trees/{ebook_id}.json", headers=headers)
                            tree_data: list[dict] | dict = tree_resp.json()

                            # 递归函数：合并 tree 的标题和 mapping 的页码
                            def process_tree_nodes(nodes: list[dict]) -> list[dict]:
                                result: list[dict] = []
                                for node in nodes:
                                    # 从 page_map 中找页码，找不到为 None
                                    page_num: int | None = next((m["page_number"] for m in page_map if m["node_id"] == node["id"]), None)
                                    chapter_item = {
                                        "title": node["title"],
                                        "page_index": page_num,
                                    }

                                    # 如果有子节点，递归处理
                                    if node.get("child_nodes"):
                                        chapter_item["children"] = process_tree_nodes(node["child_nodes"])

                                    result.append(chapter_item)
                                return result

                            # 开始解析
                            if isinstance(tree_data, list):
                                chapters = process_tree_nodes(tree_data)
                            elif isinstance(tree_data, dict) and tree_data.get("child_nodes"):
                                chapters = process_tree_nodes(tree_data["child_nodes"])

                        # c. 兜底方案：如果获取 tree 失败，仅使用 mapping 生成纯页码索引
                        if not chapters:
                            page_map.sort(key=lambda x: x["page_number"])
                            for i, m in enumerate(page_map):
                                chapters.append({
                                    "title": f"第 {i+1} 节 (P{m['page_number']})",
                                    "page_index": m["page_number"],
                                })

                except Exception as e:
                    print_error(e)
                    chapters = []

            return title, resource_url, resource_format, chapters

        def get_audio_info(audio_data: dict, root_title: str | None = None) -> tuple[str, str, str, list[dict]] | None: # 解析教材关联的音频资源（如英语教材听力）
            # 音频资源的标题存放在 global_title 字典中（键为语言代码，如 zh-CN）
            title_data = audio_data.get("global_title")
            audio_title: str = title_data.get("zh-CN") or title_data.get("en") if isinstance(title_data, dict) else title_data or audio_data.get("title") or audio_data.get("id")
            title = f"{root_title} - {audio_title}" if root_title else audio_title
            resource_url: str | None = None
            resource_format = "mp3"

            # 优先选择转码后的 MP3 文件（ti_file_flag 为 href），否则回退到源文件
            for item in audio_data["ti_items"]:
                if item.get("ti_file_flag") not in ("href", "source") or item.get("ti_format") != "mp3":
                    continue

                resource_url = item.get("ti_storage") # 获取并构造资源的 URL
                if resource_url:
                    resource_url = resource_url.replace("cs_path:${ref-path}", "https://r1-ndr-private.ykt.cbern.com.cn")
                else:
                    resource_url = next((url for url in item.get("ti_storages") or [] if url), None)
                if resource_url:
                    resource_format = item.get("ti_format") or "mp3"
                    break

            if not resource_url:
                return None

            return title, resource_url, resource_format, []

        if content_type == "thematic_course": # 专题课程
            resources_resp = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/special_edu/thematic_course/{content_id}/resources/list.json")
            resources_data: list[dict] = resources_resp.json()
            for resource in resources_data:
                resource_info = get_resource_info(resource, data["title"])
                if resource_info:
                    resources_info.append(resource_info)
        elif data.get("relations"): # 课程包等多资源页面（含导学案、课件、PPT 等）
            for resources in data["relations"].values():
                if not isinstance(resources, list):
                    continue
                for resource in resources:
                    resource_info = get_resource_info(resource, data.get("title"))
                    if resource_info:
                        resources_info.append(resource_info)
        else: # 其他类型资源
            resource_info = get_resource_info(data)
            if resource_info:
                resources_info.append(resource_info)

            if content_type == "assets_document": # 教材可能带有配套的音频资源（如英语教材听力）
                try:
                    audios_resp = session.get(f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/resources/{content_id}/relation_audios.json")
                    audios_data: list[dict] = audios_resp.json()
                    for audio in audios_data:
                        audio_info = get_audio_info(audio, data.get("title"))
                        if audio_info:
                            resources_info.append(audio_info)
                except Exception: # 音频资源不是必需的，获取失败时直接跳过
                    pass

        return resources_info

    except Exception as e:
        print_error(e)
        return None

def download_file(url: str, save_path: str, chapters: list[dict] | None = None) -> None: # 下载文件
    global task # 进度条
    current_state = { "download_url": url, "save_path": save_path, "downloaded_size": 0, "total_size": 0, "finished": False, "failed_reason": None }
    download_states.append(current_state)

    try:
        response = session.get(url, headers=headers, stream=True)

        if not response.ok: # 服务器返回表示错误的 HTTP 状态码
            current_state["finished"] = True
            current_state["failed_reason"] = f"服务器返回 HTTP 状态码 {response.status_code}" + ("，Access Token 可能已过期或无效，请重新设置" if response.status_code in (401, 403) else "")
        else:
            temp_path = f"{save_path}.tmp"
            current_state["total_size"] = int(response.headers.get("Content-Length", 0))

            with open(temp_path, "wb") as file:
                for chunk in response.iter_content( # 分块下载
                    chunk_size=131072 if current_state["total_size"] < 20971520 else 262144 if current_state["total_size"] < 52428800 else 524288
                ):
                    if chunk: # 过滤掉 Keep-Alive 块
                        file.write(chunk)
                        current_state["downloaded_size"] += len(chunk)
                        all_downloaded_size = sum(state["downloaded_size"] for state in download_states)
                        all_total_size = sum(state["total_size"] for state in download_states)
                        downloaded_number = len([state for state in download_states if state["finished"]])
                        total_number = len(download_states)

                        if all_total_size > 0: # 防止下面一行代码除以 0 而报错
                            download_progress = (all_downloaded_size / all_total_size) * 100
                            progress.update(task, completed=download_progress) # 更新进度条

            if current_state["total_size"] > 0 and current_state["downloaded_size"] != current_state["total_size"]: # 文件下载不完整
                current_state["failed_reason"] = f"文件下载不完整，需下载 {current_state["total_size"]} 字节，实际下载 {current_state["downloaded_size"]} 字节"
                current_state["downloaded_size"], current_state["total_size"] = 0, 0
                current_state["finished"] = True
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            else:
                if chapters: # 添加书签
                    print_info(texts['adding_bookmark'])
                    add_bookmarks(temp_path, chapters)

                os.replace(temp_path, save_path) # 重命名临时文件为目标文件
                current_state["finished"] = True

    except Exception as e:
        print_error(e)
        current_state["downloaded_size"], current_state["total_size"] = 0, 0
        current_state["finished"] = True
        current_state["failed_reason"] = traceback.format_exc().rstrip()

    if all(state["finished"] for state in download_states): # 所有文件下载完成
        failed_states = [state for state in download_states if state["failed_reason"]]
        if failed_states: # 存在下载失败的文件
            failed_message = "\n\n".join(
                f"{state['download_url']}\n{state['failed_reason']}"
                for state in failed_states
            )
            print_error_info(f"{texts['file_path_is']}: {os.path.dirname(save_path)}\n{texts['following_failure']}: \n{failed_message}")
        else:
            print_info(f"{texts['file_path_is']}: {os.path.dirname(save_path)}")

def add_bookmarks(pdf_path: str, chapters: list[dict]) -> None: # 给 PDF 添加书签
    try:
        if not chapters:
            return
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        def add_chapter(chapter_list: list[dict], parent=None): # 递归添加书签的内部函数
            for chapter in chapter_list:
                title: str = chapter.get("title", "未知章节")
                p_index: int | None = chapter.get("page_index")
                if p_index is None: # 如果值为 None 或者不存在，跳过这个书签
                    print_error(ValueError(f"章节 “{title}” 的页码索引无效，已跳过此处书签添加"))
                    continue

                try: # 尝试将其转为整数并减 1（pypdf 页码从 0 开始)
                    page_num: int = int(p_index) - 1
                except (ValueError, TypeError) as e: # 如果转换失败，跳过这个书签
                    print_error(e)
                    continue

                if page_num < 0 or page_num >= len(writer.pages):
                    continue

                # 添加书签，其中 parent 是父级书签对象，用于处理多级目录
                bookmark = writer.add_outline_item(title, page_num, parent=parent)

                # 如果有子章节（children），递归添加
                if chapter.get("children"):
                    add_chapter(chapter["children"], parent=bookmark)

        # 开始处理章节数据
        add_chapter(chapters)

        # 保存修改后的文件
        with open(pdf_path, "wb") as f:
            writer.write(f)

    except Exception as e:
        print_error(e)

def load_access_token() -> None: # 读取本地存储的 Access Token
    global access_token
    try:
        if os_name == "Windows": # 在 Windows 上，从注册表读取
            if not winreg:
                return
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\tchmaterial-parser-kiss", 0, winreg.KEY_READ) as key:
                token, _ = winreg.QueryValueEx(key, "AccessToken")
                if token:
                    access_token = token
                    # 更新请求头
                    headers["Authorization"] = f"Bearer {access_token}"
                    headers["X-ND-AUTH"] = f'MAC id="{access_token}",nonce="0",mac="0"'
        elif os_name == "Linux": # 在 Linux 上，从 ~/.config/tchmaterial-parser-kiss/data.json 文件读取
            # 构建文件路径
            target_file = os.path.join(
                os.path.expanduser("~"), # 获取当前用户主目录
                ".config",
                "tchmaterial-parser-kiss",
                "data.json"
            )
            if not os.path.exists(target_file): # 文件不存在则不做处理
                return

            # 读取 JSON 文件
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 提取 access_token 字段
            token = data["access_token"]
        elif os_name == "Darwin": # 在 macOS 上，从 ~/Library/Application Support/tchmaterial-parser-kiss/data.json 文件读取
            target_file = os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Application Support",
                "tchmaterial-parser-kiss",
                "data.json"
            )
            if not os.path.exists(target_file):
                return

            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            token = data["access_token"]

        if token and isinstance(token, str):
            access_token = token
            headers["Authorization"] = f"Bearer {access_token}"
            headers["X-ND-AUTH"] = f'MAC id="{access_token}",nonce="0",mac="0"'

    except Exception as e:
        print_error(e)

def set_access_token(token: str) -> str: # 设置并更新 Access Token
    global access_token
    access_token = token
    headers["Authorization"] = f"Bearer {access_token or '0'}"
    headers["X-ND-AUTH"] = f'MAC id="{access_token or '0'}",nonce="0",mac="0"'

    try:
        if os_name == "Windows": # 在 Windows 上，将 Access Token 写入注册表
            if not winreg:
                return "Access Token 已保存！"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\tchmaterial-parser-kiss") as key:
                winreg.SetValueEx(key, "AccessToken", 0, winreg.REG_SZ, token)
            return "Access Token 已保存！\n已写入注册表：HKEY_CURRENT_USER\\Software\\tchmaterial-parser-kiss\\AccessToken"
        elif os_name == "Linux": # 在 Linux 上，将 Access Token 保存至 ~/.config/tchmaterial-parser-kiss/data.json 文件中
            # 构建目标目录和文件路径
            target_dir = os.path.join(
                os.path.expanduser("~"),
                ".config",
                "tchmaterial-parser-kiss"
            )
            target_file = os.path.join(target_dir, "data.json")
            # 创建目录（如果不存在）
            os.makedirs(target_dir, exist_ok=True)

            # 构建要保存的数据字典
            data = { "access_token": token }
            # 写入 JSON 文件
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            return "Access Token 已保存！\n已写入文件：~/.config/tchmaterial-parser-kiss/data.json"
        elif os_name == "Darwin": # 在 macOS 上，将 Access Token 保存至 ~/Library/Application Support/tchmaterial-parser-kiss/data.json 文件中
            target_dir = os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Application Support",
                "tchmaterial-parser-kiss"
            )
            target_file = os.path.join(target_dir, "data.json")
            os.makedirs(target_dir, exist_ok=True)

            data = { "access_token": token }
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            return "Access Token 已保存！\n已写入文件：~/Library/Application Support/tchmaterial-parser-kiss/data.json"
        else:
            return "Access Token 已保存！\n本工具尚未支持该操作系统下 Access Token 的持久化，下次启动时仍需手动输入 Access Token。"

    except Exception as e:
        print_error(e)
        return "Access Token 已保存！\n因出现错误而无法持久化，下次启动时仍需手动输入 Access Token。"

class ResourceHelper: # 获取网站上资源的数据
    def parse_hierarchy(self, hierarchy: list) -> dict: # 解析层级数据
        if not hierarchy: # 如果没有层级数据，返回空字典
            return {}

        parsed = {}
        for h in hierarchy:
            for ch in h["children"]:
                parsed[ch["tag_id"]] = { "display_name": ch["tag_name"], "children": self.parse_hierarchy(ch["hierarchies"]) }
        return parsed

    def fetch_book_list(self) -> dict: # 获取课本列表
        # 获取电子课本层级数据
        tags_resp = session.get("https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/tags/tch_material_tag.json")
        tags_data: dict = tags_resp.json()
        parsed_hier = self.parse_hierarchy(tags_data["hierarchies"])

        # 获取电子课本 URL 列表
        list_resp = session.get("https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/resources/tch_material/version/data_version.json")
        list_data: list[str] = list_resp.json()["urls"].split(",")

        # 获取电子课本列表
        for url in list_data:
            book_resp = session.get(url)
            book_data: list[dict] = book_resp.json()
            for book in book_data:
                if book.get("tag_paths"): # 某些非课本资料的 tag_paths 属性为空数组
                    # 解析课本层级数据
                    tag_paths: list[str] = book["tag_paths"][0].split("/")

                    # 分别解析课本层级
                    temp_hier = parsed_hier[tag_paths[1]]

                    for p in tag_paths[2:]: # 电子课本 tag_paths 的前两项为 “教材”、“电子教材”
                        if temp_hier.get("children") and temp_hier["children"].get(p):
                            temp_hier = temp_hier["children"][p]
                    if not temp_hier.get("children"):
                        temp_hier["children"] = {}

                    book["display_name"] = book["title"] if "title" in book else book["name"] if "name" in book else f"(未知电子课本 {book['id']})"

                    temp_hier["children"][book["id"]] = book

        return parsed_hier

def fetch_national_lesson_list(self) -> dict: # 获取自学课件列表
        # 获取课件层级数据
        tags_resp = session.get("https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/tags/national_lesson_tag.json")
        tags_data: dict = tags_resp.json()
        parsed_hier = self.parse_hierarchy([{ "children": [{ "tag_id": "__internal_national_lesson", "hierarchies": tags_data["hierarchies"], "tag_name": "学生自主学习课件" }] }])

        # 获取课件 URL 列表
        list_resp = session.get("https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/national_lesson/teachingmaterials/version/data_version.json")
        list_data: list[str] = list_resp.json()["urls"]

        # 获取课件列表
        for url in list_data:
            lesson_resp = session.get(url)
            lesson_data: list[dict] = lesson_resp.json()
            for lesson in lesson_data:
                if lesson.get("tag_list"):
                    # 解析课件层级数据
                    tag_paths: list[str] = [tag["tag_id"] for tag in sorted(lesson["tag_list"], key=lambda tag: tag["order_num"])]

                    # 分别解析课件层级（tag_paths 为乱序）
                    def parse_tag_path(hier: dict) -> dict:
                        for p in tag_paths:
                            if hier.get("children") and hier["children"].get(p):
                                return parse_tag_path(hier["children"][p])
                        return hier

                    hier = parse_tag_path(parsed_hier["__internal_national_lesson"])
                    if not hier.get("children"):
                        hier["children"] = {}

                    lesson["display_name"] = lesson["title"] if "title" in lesson else lesson["name"] if "name" in lesson else f"(未知课件 {lesson['id']})"

                    hier["children"][lesson["id"]] = lesson

        return parsed_hier

    def fetch_prepare_lesson_list(self) -> dict: # 获取备课课件列表
        # 获取课件层级数据
        tags_resp = session.get("https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/tags/k12.json")
        tags_data: dict = tags_resp.json()
        parsed_hier = self.parse_hierarchy([{ "children": [{ "tag_id": "__internal_prepare_lesson", "hierarchies": tags_data["hierarchies"], "tag_name": "教师备课授课课件" }] }])

        # 获取课件 URL 列表
        list_resp = session.get("https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/prepare_lesson/teachingmaterials/parts.json")
        list_data: list[str] = list_resp.json()

        # 获取课件列表
        for url in list_data:
            lesson_resp = session.get(url)
            lesson_data: list[dict] = lesson_resp.json()
            for lesson in lesson_data:
                if lesson.get("tag_list"):
                    # 解析课件层级数据
                    tag_paths: list[str] = [tag["tag_id"] for tag in sorted(lesson["tag_list"], key=lambda tag: tag["order_num"])]

                    # 分别解析课件层级（tag_paths 为乱序）
                    def parse_tag_path(hier: dict) -> dict:
                        for p in tag_paths:
                            if hier.get("children") and hier["children"].get(p):
                                return parse_tag_path(hier["children"][p])
                        return hier

                    hier = parse_tag_path(parsed_hier["__internal_prepare_lesson"])
                    if not hier.get("children"):
                        hier["children"] = {}

                    lesson["display_name"] = lesson["title"] if "title" in lesson else lesson["name"] if "name" in lesson else f"(未知课件 {lesson['id']})"

                    hier["children"][lesson["id"]] = lesson

        return parsed_hier

    def fetch_resource_list(self) -> dict: # 获取资源列表
        book_hier = self.fetch_book_list()
        # national_lesson_hier = self.fetch_national_lesson_list()
        # prepare_lesson_hier = self.fetch_prepare_lesson_list()
        return { **book_hier }

session = requests.Session() # 初始化请求
download_states: list[dict] = [] # 初始化下载状态
access_token: str | None = None
headers = { # 设置请求头部，包含认证信息，其中 “MAC id” 即为 Access Token，“nonce” 和 “mac” 不可缺省但可为任意非空值
    "Authorization": "Bearer 0",
    "Origin": "https://basic.smartedu.cn",
    "Referer": "https://basic.smartedu.cn/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "X-ND-AUTH": 'MAC id="0",nonce="0",mac="0"'
}
session.proxies = {} # 全局忽略代理

# 尝试加载已保存的 Access Token
load_access_token()


# 
if '--ensure-en' in sys.argv:
    texts = texts_en
if '--debug' in sys.argv:
    is_debug = True

is_ran_exit_effection = False
def exit_effection():
    global is_ran_exit_effection
    if not is_ran_exit_effection:
        rprint(Rule(style='white')) # 分界线
    is_ran_exit_effection = True
    sys.exit(0)

def set_token_guide() -> None:
    js_code = """
    (function() {
        const authKey = Object.keys(localStorage).find(key => key.startsWith("ND_UC_AUTH"));
        if (!authKey) {
            console.error("未找到 Access Token，请确保已登录！");
            return;
        }
        const tokenData = JSON.parse(localStorage.getItem(authKey));
        const accessToken = JSON.parse(tokenData.value).access_token;
        console.log("%cAccess Token:", "color: green; font-weight: bold", accessToken);
    })();
    """
    syntax = Syntax(js_code, "javascript", theme="monokai", line_numbers=False)
    rprint(syntax)
    rprint(texts['copy_code_guide'])
    token = input().strip()
    while token == '':
        token = input('> ').strip()
    print_info(set_access_token(token))

def clean_token_guide() -> None:
    is_clean = Confirm.ask(texts['ready_to_erase'], default=False)
    if is_clean:
        set_access_token('')
        print(texts['erase_success'])


# 获取资源列表
try:
    resource_dict = ResourceHelper().fetch_resource_list()
except Exception as e:
    print_error(e)
    resource_dict = {}
    print_error_info(texts['get_res_list_failure'])

def get_parse_result_from_input() -> tuple[str, str, str] | tuple[None, None, None]:
    chosen_dict = {'children': resource_dict}
    is_first_input = True
    url = ''
    rprint(Rule(style='white')) # 分界线
    items = [] # 选择的 option_id 的累计
    while True:
        if 'children' in chosen_dict: # 不是末端节点
            options_dict = {option_data.get('display_name').strip(): option_id for option_id, option_data in chosen_dict['children'].items()}
        else:   # 是末端节点
            resource_data = chosen_dict
            resource_type = resource_data.get("resource_type_code") or "assets_document"
            content_id = resource_data.get("id")
            root_id = items[0]
            if resource_type == "teachingmaterials":
                url = f"https://basic.smartedu.cn/syncClassroom{'/prepare' if root_id == '__internal_prepare_lesson' else ''}?defaultTag={'%2F'.join(items[1:])}"
            else:
                url = f"https://basic.smartedu.cn/tchMaterial/detail?contentType={resource_type}&contentId={content_id}&catalogType=tchMaterial&subCatalog=tchMaterial"
            break
        completer = WordCompleter(options_dict.keys(), ignore_case=True)
        result = prompt(texts['add_item'] if is_first_input else ' > ', completer=completer, complete_style=CompleteStyle.MULTI_COLUMN)
        result = result.strip()
        if result in options_dict:
            chosen_dict = chosen_dict['children'][options_dict[result]]
            items.append(options_dict[result])
        else:
            if 'basic.smartedu.cn' in result: # 可能是正确的 URL
                url = result
                break
            elif result == 'exit':
                exit_effection()
            elif result == 'set':
                set_token_guide() 
                return get_parse_result_from_input()
            elif result == 'erase':
                clean_token_guide()
                return get_parse_result_from_input()
            elif is_first_input:
                print_error_info(texts['wrong_url_or_res'])
                continue
            else: # 前几次选择了资源，而这一次输入错误，静默重输
                continue
        is_first_input = False
    is_bookmark = Confirm.ask(texts['is_bookmark'], default=True)
    return parse(url, is_bookmark)

try:
    while True:
        res_data_list = get_parse_result_from_input()
        for res_data in res_data_list:
            title = res_data[0]
            res_url = res_data[1]
            fmt = res_data[2]
            chapters = res_data[3]
            progress.start()
            task = progress.add_task("[green]Downloading...", total=100)
            download_file(url=res_url, save_path=f'{os.path.expanduser("~")}/Downloads/{title}.{fmt}', chapters=chapters)
            progress.stop()
except BaseException as e:
    print_error(e)
    exit_effection()
