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

def get_platform():
    """获取当前平台信息"""
    import platform
    system = platform.system()
    machine = platform.machine()
    
    # 检测是否为安卓平台
    if system == 'Linux' and 'android' in platform.platform().lower():
        # 检测安卓架构
        if 'arm64' in machine.lower() or 'aarch64' in machine.lower():
            return 'android_arm64'
        elif 'arm' in machine.lower():
            return 'android_arm'
        elif 'x86_64' in machine.lower() or 'amd64' in machine.lower():
            return 'android_x86_64'
        else:
            return 'android_unknown'
    elif system == 'Linux':
        # 其他Linux系统（如CoreElec）
        if 'arm64' in machine.lower() or 'aarch64' in machine.lower():
            return 'linux_arm64'
        elif 'amd64' in machine.lower() or 'x86_64' in machine.lower():
            return 'linux_amd64'
        elif '386' in machine.lower() or 'x86' in machine.lower():
            return 'linux_386'
        else:
            return 'linux_other'

    else:
        return 'other'

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
    # 获取当前平台
    platform = get_platform()
    xbmc.log(f"[{ADDON_ID}] 当前平台: {platform}", xbmc.LOGINFO)
    
    # 根据平台确定二进制文件路径
    if platform.startswith('android'):
        # 安卓平台
        platform_dir = 'android'
    elif platform.startswith('linux'):
        # Linux平台
        platform_dir = 'linux'
    else:
        # 其他平台
        xbmcgui.Dialog().ok("错误", f"不支持的平台: {platform}")
        return
    
    # 构建openlist二进制文件路径（放在bin/[platform]子文件夹中）
    bin_dir = os.path.join(ADDON_PATH, 'bin')
    platform_bin_dir = os.path.join(bin_dir, platform_dir)
    openlist_filename = 'openlist'
    openlist_path = os.path.join(platform_bin_dir, openlist_filename)
    openlist_path = xbmcvfs.translatePath(openlist_path)
    
    # 确保目录存在
    if not xbmcvfs.exists(bin_dir):
        xbmcvfs.mkdirs(bin_dir)
    if not xbmcvfs.exists(platform_bin_dir):
        xbmcvfs.mkdirs(platform_bin_dir)
    
    if not xbmcvfs.exists(openlist_path):
        xbmcgui.Dialog().ok("错误", f"未找到openlist: {openlist_path}\n请手动添加对应平台的二进制文件到bin/{platform_dir}子文件夹中")
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
            # 先尝试重置登录失败次数（如果支持）
            try:
                reset_cmd = [
                    openlist_path, 
                    'admin', 'reset-failures',
                    '--data', data_dir
                ]
                subprocess.run(
                    reset_cmd,
                    capture_output=True,
                    text=True
                )
            except Exception:
                # 如果命令不支持，忽略错误
                pass
            
            # 设置默认密码为admin
            # 尝试不同的命令格式
            set_password_cmds = [
                # 格式1: admin set <password>
                [openlist_path, 'admin', 'set', 'admin', '--data', data_dir],
                # 格式2: admin password set <password>
                [openlist_path, 'admin', 'password', 'set', 'admin', '--data', data_dir],
                # 格式3: admin set-password <password>
                [openlist_path, 'admin', 'set-password', 'admin', '--data', data_dir]
            ]
            
            password_set = False
            for cmd in set_password_cmds:
                # 记录命令以便调试
                xbmc.log(f"[{ADDON_ID}] 尝试设置密码命令: {' '.join(cmd)}", xbmc.LOGINFO)
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True
                    )
                    xbmc.log(f"[{ADDON_ID}] 命令返回码: {result.returncode}", xbmc.LOGINFO)
                    xbmc.log(f"[{ADDON_ID}] 命令输出: {result.stdout}", xbmc.LOGINFO)
                    xbmc.log(f"[{ADDON_ID}] 命令错误: {result.stderr}", xbmc.LOGINFO)
                    
                    if result.returncode == 0:
                        xbmc.log(f"[{ADDON_ID}] 密码设置成功", xbmc.LOGINFO)
                        password_set = True
                        break
                    else:
                        xbmc.log(f"[{ADDON_ID}] 密码设置失败: {result.stderr}", xbmc.LOGERROR)
                except Exception as e:
                    xbmc.log(f"[{ADDON_ID}] 执行命令时出错: {str(e)}", xbmc.LOGERROR)
            
            if not password_set:
                xbmcgui.Dialog().ok("密码设置失败", "尝试多种命令格式均失败，请检查OpenList版本是否兼容")
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

