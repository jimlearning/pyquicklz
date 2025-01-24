# Kivy iOS Python 调用 C 语言库 Quicklz 总结 - 静态库方案

## 预期目标

kivy 是 Python 编写的开源用户界面框架，在 Windows、Linux、macOS、Android 和 iOS 上运行。本文的目标是在 iOS 上运行 kivy，且可以使用 kivy 调用第三方 c 语言库。具体来说，就是在 `main.py` 里，调用 c 库 `quicklz` 的 `compress` & `decompress` 方法。

## 基本原理

### 必须使用动态库

**Python 不能直接加载静态库 (.a 文件)**。这是因为静态库只是一个目标文件的集合，在编译时由链接器合并到最终的可执行文件或动态库中。Python 使用的 `ctypes` 或其他类似工具只支持加载动态库 (`.so` 文件，Linux/macOS 上) 或 `DLL` 文件 (Windows 上)。

## 关键流程

### 安装依赖项

```shell
$ brew install autoconf automake libtool pkg-config
$ brew link libtool
$ pip install Cython==3.0.11
```

### 安装 kivy-ios

```shell
$ pip install kivy-ios
```

`kivy-ios` 的源码安装在了 `python` `site-packages` 目录下，我的默认目录为 `/opt/miniconda3/lib/python3.12/site-packages`。


### 编译 kivy-ios

```
$ toolchain build kivy 
```

请注意，编译结果输出在命令当前环境路径下，结构如下：

```shell
.
├── build
│ ├── hostopenssl
│ ├── hostpython3
│ ├── ios
│ ├── kivy
│ ├── libffi
│ ├── libpng
│ ├── openssl
│ ├── pyobjus
│ ├── python3
│ ├── sdl2
│ ├── sdl2_image
│ ├── sdl2_mixer
│ └── sdl2_ttf
└── dist
    ├── frameworks
    ├── hostopenssl
    ├── hostpython3
    ├── include
    ├── lib
    ├── root
    ├── state.db
    └── xcframework
```

> 请谨慎选择当前路径，后期不要随意更改，因为编译结果中，很多地方使用的是绝对路径。

### 接着使用内置工具新建 iOS 工程

```shell
$ toolchain create kivy-quicklz ~/Projects/kivy-build-output
```

我的工程新建在 ~/Projects 目录下，工程名字为 kivy-quicklz，脚本会自动新建目录 kivy-quicklz-ios，并把工程放在该目录下。
请注意，`toolchain create`所处路径必须与上一步 `toolchain build kivy` 是同一路径，否则会报错：

```shell
[ERROR   ] No python recipe compiled!
[ERROR   ] You must have compiled at least python3
[ERROR   ] recipe to be able to create a project.
```

> 此处工程命名也请谨慎，后期不要随意更改，因为工程配置中，也有很多地方使用的是绝对路径。

### 打开工程

- 找到 `kivy-build-output/kivy-quicklz-ios/kivy-quicklz.xcodeproj`，双击在 Xcode 打开
- 选择工程文件 `kivy-quicklz -> Targets -> kivy-quicklz`
	- `General -> Minimum Deployment -> 13.0`
	- `Signing & Capabilities -> Team -> Apple Account Team`
- 然后运行，不出意外的话会 `Build Failed`，`Run custom shell script 'Run Script'`，这是因为 `toolchain create`生成工程中，自定义了三个 `Run Script`，每运行一次 YourApp 就会重新生成，但脚本有问题，每运行一次就会嵌套生成一层，结构如下：

```shell
├── kivy-quicklz-ios
    ├── YourApp
    │ ├── build
    │ ├── dist
    │ └── kivy-quicklz-ios
			├── YourApp
```

- 找到工程文件 `kivy-quicklz -> Targets -> kivy-quicklz`
	- `Build Phases -> 第一个 Run Script`，全选改为以下脚本：
	
```shell 
# 1. 先将整个 kivy-quicklz-ios 目录（包含 YourApp 子目录）同步到 YourApp 目录；
# 2. 再将嵌套的 YourApp 目录内容移动到正确位置；
# 3. 最后删除多余的 YourApp 目录。
# 4. "/Users/jim/Projects/kivy-ios-output/kivy-quicklz-ios/" 不能改为 "$PROJECT_DIR"，不然会有问题，替换为自己的工程所在位置。
rsync -av --delete "/Users/jim/Projects/kivy-ios-output/kivy-quicklz-ios/" "$PROJECT_DIR"/YourApp
mv "$PROJECT_DIR"/YourApp/YourApp/* "$PROJECT_DIR"/YourApp
rm -rf "$PROJECT_DIR"/YourApp/YourApp
```

- 重新运行，此时继续报错

```shell
Running main.py: (null)
Unable to open main.py, abort.
Leaving
```

- 接下来就可以写 `main.py` 了。在 iOS 工程根目录下，即 `~/Projects/kivy-build-output/kivy-quicklz-ios/`，新建 `main.py`，粘贴如下测试代码：

```python
import kivy
kivy.require('1.0.7')

from kivy.app import App
from kivy.uix.button import Button

import quicklz

class TestApp(App):

    def build(self):
        self.button = Button(text='hello QuickLZ!',
                        on_press=self.quicklz)
        return self.button

    def quicklz(self, instance):
        compressed = quicklz.compress(b'hello QuickLZ!')
        decompressed = quicklz.decompress(compressed)
        
        decompressedDesc = decompressed.decode("utf-8")
        instance.text = "compressed and decompressed: " + decompressedDesc

if __name__ == '__main__':
    TestApp().run()
```

- 运行，不出意外，报错为 `ModuleNotFoundError: No module named 'quicklz'`。接下来，就可以准备 `quicklz` 动态库。

### 编译 `quicklz` 静态库
- 在第 2 步 `kivy-ios` 源码所安装的 `/opt/miniconda3/lib/python3.12/site-packages/kivy-ios` 目录，找到 `recipes` 目录，新建 `quicklz` 文件夹，新建 `__init__.py` 文件，粘贴如下代码：

```python
from kivy_ios.toolchain import Recipe
import subprocess

class QuickLZRecipe(Recipe):
    version = "1.0"
    url = "https://github.com/jimlearning/quicklz/archive/refs/tags/1.0.zip"
    library = "libquicklz.a"
    include_dir = "quicklz.h"
    include_per_platform = True
    version_min = "-miphoneos-version-min=13.0"
    depends = []

    def build_platform(self, plat):
        if plat.name == "iphoneos-arm64":
            platform = "iphoneos"
        else:
            platform = "iphonesimulator"

        # xcrun -sdk iphoneos clang -arch arm64 quicklz.c -o quicklz.o
        # xcrun -sdk iphonesimulator clang -arch arm64 quicklz.c -o quicklz.o
        cmd = ["xcrun", "-sdk", platform, "clang", "-arch", "arm64", "quicklz.c", "-o", "quicklz.o"]
        subprocess.run(cmd, check=True)

        # ar rcs libquicklz.a quicklz.o
        cmd = ["ar", "rcs", "libquicklz.a", "quicklz.o"]
        subprocess.run(cmd, check=True)

recipe = QuickLZRecipe()
```

- 成功生成 `libquicklz.a` & `libquicklz.xcframework`，且同时支持真机与模拟器。
- 可以正常 `import quicklz`，但找不到任何接口方法
    
```shell
AttributeError: module 'quicklz' has no attribute 'qlz_size_compressed'
```

- 继续尝试

```python
lib_path = os.path.abspath("./dist/lib/iphoneos/libquicklz.dylib") 
quicklz_lib = ctypes.CDLL(lib_path)
```
仍然报错

```
'/private/var/containers/Bundle/Application/9E719999-EF14-4F60-8545-29CD7D5EE77C/kivy-quicklz.app/YourApp/dist/lib/iphoneos/libquicklz.a' (not a mach-o file)
```

表明静态库无法被动态加载使用。所以此路不通。

### Python C 扩展模块

#### 新建 quicklzmodule.c

这是一个 Python C 扩展模块，它的主要作用是将 QuickLZ 压缩库的 C 函数包装成 Python 可以调用的接口。具体内容请参看源码。

- 主要提供了两个函数：
    - py_quicklz_compress: 将 Python 字符串压缩成二进制数据。
    - py_quicklz_decompress: 将压缩后的二进制数据解压缩回原始数据。
- 它通过 Python C API 实现了：
    - 参数解析（PyArg_ParseTuple）
    - 内存管理（malloc/free）
    - Python 对象创建（Py_BuildValue）
- 这样 Python 代码就可以直接调用 quicklz.compress() 和 quicklz.decompress() 函数。

#### 新建 setup.py

- 这是 Python 的构建配置文件，用于定义如何编译和安装 QuickLZ 模块
- 主要功能：
    - 定义了一个名为 'quicklz' 的 Extension（扩展模块）。
    - 指定源文件为 'quicklzmodule.c'。
    - 设置模块的版本号和描述信息。
    - 配置编译选项和依赖关系。
- quicklzmodule.c 与 setup.py 两个文件共同工作，使得 QuickLZ 压缩库能够在 iOS 平台上被 Python 代码调用。

#### 修改 __init__.py

修改手动编译的方法：
1. 将 quicklz.c 编译为目标文件
2. 将 quicklzmodule.c 与 Python 包含文件一起编译为目标文件
3. 将两个目标文件合并创建静态库（libquicklz.a）

```python
from kivy_ios.toolchain import CythonRecipe
from os.path import join, exists, dirname
import subprocess
import shutil
import os

class QuicklzRecipe(CythonRecipe):
    version='1.0' # QuickLZ 版本号
    url = "https://github.com/jimlearning/pyquicklz/archive/refs/tags/1.0.zip" # 源代码压缩包路径
    library = "libquicklz.a" # 输出的静态库名称
    sources = [] # 空列表，因为我们手动处理编译
    include_dir = "quicklz.h" # 需要安装的头文件
    include_per_platform = True # 是否为每个平台单独安装头文件
    version_min = "-miphoneos-version-min=13.0" # 最低 iOS 版本要求
    depends = ["hostpython3", "python3"] # 依赖项（hostpython3 和 python3）
    pre_build_ext = False # 跳过预构建扩展步骤
    cythonize = False  # 已经有 C 文件，不需要 Cython 编译
    
    def build_platform(self, plat):
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
```

#### 快捷方式

下载 https://github.com/jimlearning/pyquicklz 源码，然后将其中的 __init__.py 和 setup.py 文件放在 `/Users/jim/Projects/kivy-build-output/dist/root/python3/lib/python3.11/site-packages/quicklz/` 路径下即可。

### 运行

在 .py 文件中引入与调用，可正常运行。

```python
import quicklz

compressed = quicklz.compress(b'hello QuickLZ!')
decompressed = quicklz.decompress(compressed)
```

> 因为我们所有的实现文件和生成的动态库都位于 `dist` 下的 `lib` 目录下，kivy iOS 工程创建时已经做了相应的路径配置，所以不用做任何配置，免去了很多麻烦。可以参看 `Build Setting` 目录下的 `Search Paths` 配置：

```shell
FRAMEWORK_SEARCH_PATHS = /Users/jim/Projects/kivy-build-output/dist/frameworks $(SRCROOT)/../dist/xcframework $(inherited)
HEADER_SEARCH_PATHS = /Users/jim/Projects/kivy-build-output/dist/root/python3/include/python3.11/** /Users/jim/Projects/kivy-build-output/dist/include/common/sdl2
LIBRARY_SEARCH_PATHS = $(inherited) /Users/jim/Projects/kivy-build-output/dist/lib
```

## 总结

整个尝试过程中，大部分时间都在 kivy 给定的语境下打转，后来发现 Python 脚本只能使用动态库，把问题解耦为 kivy 支持 iOS 下调用 Python，Python 通过动态库调用第三方库，彻底摆脱了 kivy 的干扰，问题才得以顺利解决。

但 kivy 是如何基于静态库完成框架搭建，以及库之间的相互调用，还没看明白，有机会再继续研究。