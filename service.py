import os
import subprocess
import signal
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

# 获取插件信息
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = ADDON.getAddonInfo('path')

def set_directory_permissions(path):
    """为目录及其子文件设置可执行权限"""
    if not xbmcvfs.exists(path):
        # 若目录不存在则创建
        xbmcvfs.mkdirs(path)
    # 设置目录本身权限
    try:
        os.chmod(path, 0o755)
    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] 设置目录权限失败 {path}: {str(e)}", xbmc.LOGERROR)
    # 递归设置子文件权限
    dirs, files = xbmcvfs.listdir(path)
    for file in files:
        file_path = os.path.join(path, file)
        try:
            os.chmod(file_path, 0o755)
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] 设置文件权限失败 {file_path}: {str(e)}", xbmc.LOGERROR)
    for dir in dirs:
        dir_path = os.path.join(path, dir)
        set_directory_permissions(dir_path)

def main():
    openlist_filename = 'openlist'
    
    # 构建openlist二进制文件路径
    openlist_path = os.path.join(ADDON_PATH, openlist_filename)
    openlist_path = xbmcvfs.translatePath(openlist_path)
    
    if not xbmcvfs.exists(openlist_path):
        xbmcgui.Dialog().ok("错误", f"未找到{openlist_filename}: {openlist_path}")
        return
    
    # 设置二进制文件权限
    try:
        os.chmod(openlist_path, 0o755)
    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] 设置openlist权限失败: {str(e)}", xbmc.LOGERROR)
    
    # 定义目标数据目录（addon_data/service.openlist）
    data_dir = xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}/")
    # 确保数据目录存在并设置权限
    set_directory_permissions(data_dir)
    
    # 检查是否为初次启动（通过判断关键配置文件是否存在）
    # 假设openlist的配置文件为data.db，可根据实际情况修改
    config_file = os.path.join(data_dir, "data.db")
    is_first_launch = not xbmcvfs.exists(config_file)
    
    # 仅在初次启动时设置密码
    if is_first_launch:
        try:
            set_password_cmd = [
                openlist_path, 
                'admin', 'set', 'coreelec',
                '--data', data_dir  # 密码设置也指定数据目录
            ]
            result = subprocess.run(
                set_password_cmd,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                xbmcgui.Dialog().ok("密码设置失败", f"错误: {result.stderr}")
                return
        except Exception as e:
            xbmcgui.Dialog().ok("错误", f"设置密码时出错: {str(e)}")
            return
    
    # 启动服务（通过--data指定数据目录）
    process = None
    try:
        start_cmd = [
            openlist_path, 
            'server',
            '--data', data_dir  # 核心修改：指定数据存储路径
        ]
        process = subprocess.Popen(start_cmd)
        xbmc.log(f"[{ADDON_ID}] {openlist_filename} 已启动 (PID: {process.pid})，数据路径: {data_dir}", xbmc.LOGINFO)
    except Exception as e:
        xbmcgui.Dialog().ok("启动失败", f"无法启动{openlist_filename}: {str(e)}")
        return
    
    # 等待Kodi退出后停止服务
    xbmc.Monitor().waitForAbort()
    if process and process.poll() is None:
        try:
            os.kill(process.pid, signal.SIGTERM)
            xbmc.log(f"[{ADDON_ID}] {openlist_filename} 已停止", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] 停止失败: {str(e)}", xbmc.LOGERROR)

if __name__ == '__main__':
    main()
