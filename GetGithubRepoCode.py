"""
title: Get github repo code
author: Saltedfish
version: 0.1.2
"""

import os
import re
import requests
import zipfile
import tempfile
from typing import Tuple, List, Union
from urllib.parse import urlparse, unquote


class Tools:
    def __init__(self):
        pass

    def fetch_github_code(self, repo_url: str) -> str:
        """
        Fetches code files from a GitHub repository URL (repository root, directory, or single file)
        and returns their contents formatted in Markdown.

        :param repo_url: The URL of the GitHub repository, directory, or single file.
        :return: A Markdown-formatted string containing the code files.
        """
        # 定义支持的文件扩展名及其对应的语言
        language_mapping = {
            ".py": "python",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".java": "java",
            ".js": "javascript",
            ".ts": "typescript",
            ".rb": "ruby",
            ".go": "go",
            ".cs": "csharp",
            ".swift": "swift",
            ".kt": "kotlin",
            ".php": "php",
            ".rs": "rust",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".yaml": "yaml",
            ".json": "json",
            # 可以在此处添加更多扩展名及其对应的语言
        }

        supported_extensions = list(language_mapping.keys())

        def parse_github_url(url: str) -> Tuple[str, str, str, str]:
            """
            Parses the GitHub URL to extract the username, repository name, type ('repo', 'dir', 'file'),
            branch, and path within the repository.

            :param url: The GitHub URL.
            :return: A tuple containing (user, repo, type, path).
            :raises ValueError: If the URL is invalid.
            """
            # Handle SSH URLs separately
            ssh_pattern = re.compile(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?$")
            ssh_match = ssh_pattern.match(url)
            if ssh_match:
                user, repo = ssh_match.groups()
                return user, repo, "repo", ""

            # Parse standard URLs
            parsed_url = urlparse(url)
            if parsed_url.netloc != "github.com":
                raise ValueError("URL 必须是 GitHub.com 的地址。")

            path = unquote(parsed_url.path)
            path_parts = path.strip("/").split("/")

            if len(path_parts) < 2:
                raise ValueError("无效的 GitHub 仓库 URL。")

            user, repo = path_parts[0], path_parts[1]
            repo = repo[:-4] if repo.endswith(".git") else repo  # 去除 .git

            if len(path_parts) == 2:
                return user, repo, "repo", ""
            elif len(path_parts) >= 4:
                indicator = path_parts[2]
                branch = path_parts[3]
                sub_path = "/".join(path_parts[4:]) if len(path_parts) > 4 else ""
                if indicator == "tree":
                    return user, repo, "dir", {"branch": branch, "path": sub_path}
                elif indicator == "blob":
                    return user, repo, "file", {"branch": branch, "path": sub_path}
                else:
                    raise ValueError("未知的 GitHub URL 类型。")
            else:
                raise ValueError("无法解析的 GitHub URL 结构。")

        def get_default_branch(user: str, repo: str) -> str:
            """
            Retrieves the default branch of the GitHub repository using the GitHub API.

            :param user: GitHub username.
            :param repo: GitHub repository name.
            :return: The name of the default branch.
            :raises Exception: If the GitHub API request fails.
            """
            api_url = f"https://api.github.com/repos/{user}/{repo}"
            response = requests.get(api_url)
            if response.status_code != 200:
                raise Exception(f"访问 GitHub API 失败: {response.status_code}")
            data = response.json()
            return data.get("default_branch", "master")

        def download_repo_zip(
            user: str, repo: str, branch: str, dest_path: str
        ) -> None:
            """
            Downloads the ZIP archive of the specified repository and branch.

            :param user: GitHub username.
            :param repo: GitHub repository name.
            :param branch: Branch name.
            :param dest_path: Destination file path for the downloaded ZIP.
            :raises Exception: If the download fails.
            """
            zip_url = (
                f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
            )
            response = requests.get(zip_url, stream=True)
            if response.status_code != 200:
                raise Exception(f"下载仓库 ZIP 失败: {response.status_code}")
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        def extract_zip(zip_path: str, extract_to: str) -> str:
            """
            Extracts the ZIP archive to the specified directory.

            :param zip_path: Path to the ZIP file.
            :param extract_to: Directory where the ZIP will be extracted.
            :return: Path to the root directory of the extracted repository.
            """
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_to)
                # Identify the root directory (usually <repo>-<branch>/)
                root_dirs = [name for name in zip_ref.namelist() if name.endswith("/")]
                if root_dirs:
                    return os.path.join(extract_to, root_dirs[0].strip("/"))
                else:
                    return extract_to

        def find_code_files_repo(
            root_dir: str, extensions: List[str]
        ) -> List[Tuple[str, str]]:
            """
            Searches for code files with the specified extensions within the repository.

            :param root_dir: Root directory of the extracted repository.
            :param extensions: List of file extensions to search for.
            :return: A list of tuples containing the relative path and full path of each code file.
            """
            code_files = []
            for dirpath, _, filenames in os.walk(root_dir):
                for filename in filenames:
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext in extensions:
                        full_path = os.path.join(dirpath, filename)
                        rel_path = os.path.relpath(full_path, root_dir)
                        code_files.append((rel_path, full_path))
            return code_files

        def fetch_code_from_directory(
            user: str,
            repo: str,
            branch: str,
            directory_path: str,
            extensions: List[str],
        ) -> List[Tuple[str, str]]:
            """
            Fetches code files from a specific directory in the repository using GitHub API.

            :param user: GitHub username.
            :param repo: GitHub repository name.
            :param branch: Branch name.
            :param directory_path: Path to the directory within the repository.
            :param extensions: List of file extensions to search for.
            :return: A list of tuples containing the relative path and content URL of each code file.
            """
            api_url = (
                f"https://api.github.com/repos/{user}/{repo}/contents/{directory_path}"
            )
            params = {"ref": branch}
            response = requests.get(api_url, params=params)
            if response.status_code != 200:
                raise Exception(f"获取目录内容失败: {response.status_code}")
            data = response.json()
            if isinstance(data, dict) and data.get("type") == "file":
                # The path points to a single file, not a directory
                return []
            code_files = []
            for item in data:
                if (
                    item["type"] == "file"
                    and os.path.splitext(item["name"])[1].lower() in extensions
                ):
                    rel_path = os.path.relpath(item["path"], directory_path)
                    code_files.append((rel_path, item["download_url"]))
                elif item["type"] == "dir":
                    # 递归子目录
                    sub_dir_files = fetch_code_from_directory(
                        user, repo, branch, item["path"], extensions
                    )
                    code_files.extend(sub_dir_files)
            return code_files

        def fetch_single_file(
            user: str, repo: str, branch: str, file_path: str
        ) -> List[Tuple[str, str]]:
            """
            Fetches a single code file from the repository using GitHub API.

            :param user: GitHub username.
            :param repo: GitHub repository name.
            :param branch: Branch name.
            :param file_path: Path to the file within the repository.
            :return: A list containing a single tuple with the file name and its content URL.
            """
            api_url = f"https://api.github.com/repos/{user}/{repo}/contents/{file_path}"
            params = {"ref": branch}
            response = requests.get(api_url, params=params)
            if response.status_code != 200:
                raise Exception(f"获取文件内容失败: {response.status_code}")
            data = response.json()
            if data.get("type") != "file":
                raise ValueError("指定的路径并不是一个文件。")
            file_ext = os.path.splitext(data["name"])[1].lower()
            if file_ext not in language_mapping:
                return []
            return [(data["name"], data["download_url"])]

        def generate_markdown(
            code_files: List[Tuple[str, str]],
            language_mapping: dict,
            base_path: str = "",
        ) -> str:
            """
            将代码文件内容格式化为 Markdown 字符串。

            :param code_files: 包含相对路径和下载 URL 或本地路径的代码文件列表。
            :param language_mapping: 文件扩展名到编程语言的映射字典，用于语法高亮。
            :param base_path: 基本路径，用于显示文件的相对路径。
            :return: 包含所有代码文件内容的 Markdown 格式字符串。
            """
            markdown_content = ""

            for rel_path, download_url in code_files:
                file_name = os.path.basename(rel_path)
                file_dir = os.path.dirname(rel_path)
                markdown_content += f"### {file_name}\n"
                markdown_content += (
                    f"**路径**: `{os.path.join(base_path, file_dir)}`\n\n"
                )

                # 确定语言类型，用于语法高亮
                ext = os.path.splitext(file_name)[1].lower()
                language = language_mapping.get(ext, "")

                markdown_content += f"```{language}\n"

                try:
                    parsed = urlparse(download_url)
                    if parsed.scheme in ("http", "https"):
                        # 如果 download_url 是一个有效的 URL，则通过 HTTP 请求获取内容
                        response = requests.get(download_url)
                        if response.status_code == 200:
                            code_content = response.text
                        else:
                            code_content = (
                                f"无法下载该文件内容: HTTP {response.status_code}"
                            )
                    else:
                        # 否则，假定 download_url 是一个本地文件路径，直接读取文件内容
                        with open(download_url, "r", encoding="utf-8") as f:
                            code_content = f.read()
                except Exception as e:
                    code_content = f"请求文件时出错: {e}"

                markdown_content += f"{code_content}\n```\n\n"

            return markdown_content

        try:
            # 步骤1：解析GitHub URL
            parsed = parse_github_url(repo_url)
            user, repo, url_type, path_info = parsed
        except ValueError as ve:
            return f"错误: {ve}"

        try:
            if url_type == "repo":
                # 步骤2a：获取默认分支
                default_branch = get_default_branch(user, repo)
                print(f"默认分支: {default_branch}")

                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, f"{repo}.zip")
                    try:
                        # 步骤3a：下载仓库ZIP
                        print("正在下载仓库...")
                        download_repo_zip(user, repo, default_branch, zip_path)
                        print("下载完成。")
                    except Exception as e:
                        return f"错误: {e}"

                    try:
                        # 步骤4a：解压ZIP
                        print("正在解压仓库...")
                        extract_root = extract_zip(zip_path, tmpdir)
                        print(f"解压完成。解压路径: {extract_root}")
                    except Exception as e:
                        return f"错误: {e}"

                    # 步骤5a：查找代码文件
                    code_files = find_code_files_repo(
                        extract_root, supported_extensions
                    )
                    if not code_files:
                        return "未找到指定的代码文件。"

                    print(f"找到 {len(code_files)} 个代码文件。")

                    # 步骤6a：生成Markdown
                    markdown_output = generate_markdown(code_files, language_mapping)
                    return markdown_output

            elif url_type == "dir":
                # 步骤2b：处理目录URL
                branch = path_info["branch"]
                directory_path = path_info["path"]
                print(f"目录路径: {directory_path}, 分支: {branch}")

                try:
                    # 步骤3b：查找目录中的代码文件
                    code_files = fetch_code_from_directory(
                        user, repo, branch, directory_path, supported_extensions
                    )
                    if not code_files:
                        return "未找到指定的代码文件。"
                    print(f"找到 {len(code_files)} 个代码文件。")
                except Exception as e:
                    return f"错误: {e}"

                # 步骤4b：生成Markdown
                # base_path用于在Markdown中显示相对于指定目录的路径
                base_path = directory_path
                markdown_output = generate_markdown(
                    code_files, language_mapping, base_path=base_path
                )
                return markdown_output

            elif url_type == "file":
                # 步骤2c：处理单个文件URL
                branch = path_info["branch"]
                file_path = path_info["path"]
                print(f"文件路径: {file_path}, 分支: {branch}")

                try:
                    # 步骤3c：获取单个文件
                    code_files = fetch_single_file(user, repo, branch, file_path)
                    if not code_files:
                        return "该文件的扩展名不在支持的列表中。"
                    print(f"找到 {len(code_files)} 个代码文件。")
                except Exception as e:
                    return f"错误: {e}"

                # 步骤4c：生成Markdown
                # base_path用于在Markdown中显示相对于指定路径的路径
                base_path = os.path.dirname(file_path)
                markdown_output = generate_markdown(
                    code_files, language_mapping, base_path=base_path
                )
                return markdown_output

            else:
                return "未知的 URL 类型。"

        except Exception as e:
            return f"发生错误: {e}"
