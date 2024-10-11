"""
title: Get github repo code
author: Saltedfish
version: 0.1
"""

import os
import re
import requests
import zipfile
import tempfile
from typing import Tuple, List


class Tools:
    def __init__(self):
        pass

    def fetch_github_code(self, repo_url: str) -> str:
        """
        Fetches all code files from a GitHub repository and returns their contents formatted in Markdown.

        :param repo_url: The URL of the GitHub repository.
        :return: A string containing Markdown-formatted code files with filenames and paths.
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
            # 可以在此处添加更多扩展名及其对应的语言
        }

        supported_extensions = list(language_mapping.keys())

        def parse_github_url(url: str) -> Tuple[str, str]:
            """
            Parses the GitHub repository URL to extract the username and repository name.

            :param url: The GitHub repository URL.
            :return: A tuple containing the username and repository name.
            :raises ValueError: If the URL is not a valid GitHub repository URL.
            """
            pattern = re.compile(
                r"(?:https?://github\.com/|git@github\.com:)([^/]+)/([^/.]+?)(?:\.git)?/?$"
            )
            match = pattern.match(url)
            if not match:
                raise ValueError("Invalid GitHub repository URL.")
            user, repo = match.groups()
            return user, repo

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
                raise Exception(f"Failed to access GitHub API: {response.status_code}")
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
                raise Exception(
                    f"Failed to download repository ZIP: {response.status_code}"
                )
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

        def find_code_files(
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

        def generate_markdown(
            code_files: List[Tuple[str, str]], language_mapping: dict
        ) -> str:
            """
            将代码文件内容格式化为 Markdown 字符串。

            :param code_files: 包含相对路径和完整路径的代码文件列表。
            :param language_mapping: 文件扩展名到编程语言的映射字典，用于语法高亮。
            :return: 包含所有代码文件内容的 Markdown 格式字符串。
            """
            markdown_content = ""

            for rel_path, full_path in code_files:
                file_name = os.path.basename(rel_path)
                file_dir = os.path.dirname(rel_path)
                markdown_content += f"### {file_name}\n"
                markdown_content += f"**路径**: `{file_dir}`\n\n"

                # 确定语言类型，用于语法高亮
                ext = os.path.splitext(file_name)[1].lower()
                language = language_mapping.get(ext, "")

                markdown_content += f"```{language}\n"
                try:
                    with open(full_path, "r", encoding="utf-8") as code_file:
                        code_content = code_file.read()
                except UnicodeDecodeError:
                    # 如果utf-8解码失败，尝试使用latin1编码
                    with open(full_path, "r", encoding="latin1") as code_file:
                        code_content = code_file.read()
                markdown_content += f"{code_content}\n```\n\n"

            return markdown_content

        try:
            # 步骤1：解析GitHub URL
            user, repo = parse_github_url(repo_url)
        except ValueError as ve:
            return f"错误: {ve}"

        try:
            # 步骤2：获取默认分支
            default_branch = get_default_branch(user, repo)
            print(f"默认分支: {default_branch}")
        except Exception as e:
            return f"错误: {e}"

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, f"{repo}.zip")
            try:
                # 步骤3：下载仓库ZIP
                print("正在下载仓库...")
                download_repo_zip(user, repo, default_branch, zip_path)
                print("下载完成。")
            except Exception as e:
                return f"错误: {e}"

            try:
                # 步骤4：解压ZIP
                print("正在解压仓库...")
                extract_root = extract_zip(zip_path, tmpdir)
                print(f"解压完成。解压路径: {extract_root}")
            except Exception as e:
                return f"错误: {e}"

            # 步骤5：查找代码文件
            code_files = find_code_files(extract_root, supported_extensions)
            if not code_files:
                return "未找到指定的代码文件。"

            print(f"找到 {len(code_files)} 个代码文件。")

            # 步骤6：生成Markdown
            markdown_output = generate_markdown(code_files, language_mapping)
            return f"Give a brief description of the code:{markdown_output}, and ask user what to do next."
