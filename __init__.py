from kivy_ios.toolchain import CythonRecipe
from os.path import join, exists, dirname
import subprocess
import shutil
import os

class QuicklzRecipe(CythonRecipe):
    """用于构建 iOS 平台的 QuickLZ 压缩库的配方。
    
    本配方负责编译 QuickLZ 压缩库及其 Python 绑定，支持 iOS 设备和模拟器平台。
    虽然继承自 CythonRecipe，但由于我们使用预生成的 C 文件，所以手动处理编译过程。
    
    属性说明：
        version: QuickLZ 版本号（1.0）
        url: 源代码压缩包路径（当前使用本地文件）
        library: 输出的静态库名称
        sources: 空列表，因为我们手动处理编译
        include_dir: 需要安装的头文件
        include_per_platform: 是否为每个平台单独安装头文件
        version_min: 最低 iOS 版本要求
        depends: 依赖项（hostpython3 和 python3）
        pre_build_ext: 跳过预构建扩展步骤
        cythonize: 跳过 Cython 编译，因为已有 C 文件
    """
    version='1.0'
    url = "file:///Users/makera/Desktop/pyquicklz.zip"
    library = "libquicklz.a"
    sources = []
    include_dir = "quicklz.h"
    include_per_platform = True
    version_min = "-miphoneos-version-min=13.0"
    depends = ["hostpython3", "python3"]
    pre_build_ext = False
    cythonize = False  # 已经有 C 文件，不需要 Cython 编译
    
    def build_platform(self, plat):
        """为特定平台构建 QuickLZ 库和 Python 模块。
        
        本方法处理手动编译过程：
        1. 将 quicklz.c 编译为目标文件
        2. 将 quicklzmodule.c 与 Python 包含文件一起编译为目标文件
        3. 将两个目标文件合并创建静态库（libquicklz.a）
        
        参数：
            plat: 平台对象，包含构建配置
                (可能是 iphoneos-arm64 或 iphonesimulator-arm64)
        """
        # 根据平台确定SDK
        if plat.name == "iphoneos-arm64":
            platform = "iphoneos"
        else:
            platform = "iphonesimulator"

        # Python 头文件和库文件路径
        python_include_path = "/Users/makera/Desktop/ios-controller/dist/hostpython3/include/python3.11"
        python_lib_path = "/Users/makera/Desktop/ios-controller/dist/hostpython3/lib"

        # 编译 quicklz.c - 核心压缩库
        cmd = ["xcrun", "-sdk", platform, "clang", "-arch", "arm64",
            "-c", "quicklz.c", "-o", "quicklz.o"]
        subprocess.run(cmd, check=True)

        # 编译 quicklzmodule.c - Python 绑定
        cmd = ["xcrun", "-sdk", platform, "clang", "-arch", "arm64",
            "-I", python_include_path,
            "-L", python_lib_path,
            "-c", "quicklzmodule.c", "-o", "quicklzmodule.o",
            "-lpython3.11"]  # 链接 Python 库
        subprocess.run(cmd, check=True)

        # 创建包含两个目标文件的静态库
        cmd = ["ar", "rcs", "libquicklz.a", "quicklz.o", "quicklzmodule.o"]
        subprocess.run(cmd, check=True)

recipe = QuicklzRecipe()
