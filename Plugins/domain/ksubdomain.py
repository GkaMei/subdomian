import subprocess
import json
import re
import os
import logging
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(level=logging.INFO)

TOOLS_DIR = os.path.abspath("tools")

def is_root_user():
    """检查是否是 root 用户运行"""
    return os.geteuid() == 0

def execute_command(command: List[str]) -> Optional[str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{' '.join(command)}' failed with error: {e}")
        return None

def extract_useful_info(output: str) -> List[str]:
    # 提取域名解析路径
    domain_pattern = re.compile(r"(\S+ => \S+)")
    domain_matches = domain_pattern.findall(output)
    
    if domain_matches:
        return [match.split(" => ")[0] for match in domain_matches]  # 返回提取的子域名
    else:
        logging.warning("No useful information found in the output.")
        return []  # 返回空列表表示未找到

def get_subdomains_tools(domain: str) -> List[str]:
    logging.info(f"Starting subdomain discovery by Tools for domain : {domain}")

    commands = {
        'subfinder': [os.path.join(TOOLS_DIR, 'subfinder', 'subfinder'), '-d', domain, '-silent'],
        'assetfinder': [os.path.join(TOOLS_DIR, 'assetfinder', 'assetfinder'), '--subs-only', domain],
        'findomain': [os.path.join(TOOLS_DIR, 'findomain', 'findomain'), '-t', domain, '-q']
    }

    all_subdomains = set()

    with ThreadPoolExecutor() as executor:
        future_to_tool = {executor.submit(execute_command, command): tool for tool, command in commands.items()}
        
        for future in as_completed(future_to_tool):
            tool = future_to_tool[future]
            try:
                output = future.result()
                if output:
                    logging.info(f"{tool.capitalize()} output:\n{output}")
                    all_subdomains.update(output.splitlines())
            except Exception as e:
                logging.error(f"{tool.capitalize()} generated an exception: {e}")

    return list(all_subdomains)

def get_subdomains_dict(domain: str, dict_file: Optional[str] = None) -> List[str]:
    """
    使用 ksubdomain 进行主动子域名发现。
    
    :param domain: 要检查的域名
    :param dict_file: 字典文件路径，如果为 None 则使用默认字典
    :return: 子域名列表
    """
    # 检查 root 权限
    if not is_root_user():
        logging.error("root or sudo try again")
        exit(1)
    
    logging.info(f"使用{dict_file}字典扫描")
    ksubdomain_command = [
        os.path.join(TOOLS_DIR, 'ksubdomain', 'ksubdomain'),
        '-d', domain,
        '-f', dict_file,
        '-full'
    ]
    
    output = execute_command(ksubdomain_command)    
    ksubdomain_output = extract_useful_info(output)
    return list(ksubdomain_output)