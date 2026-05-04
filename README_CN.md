# 小米动态照片转LIVP工具

[English](#english)

## 项目简介
将小米手机拍摄的动态照片（Motion Photo）转换为苹果iOS兼容的LIVP（Live Photo）格式，可被百度网盘正确识别。  
运行平台：**macOS / Linux / Windows**  
Python版本：**3.8+**

## 功能特性
- 小米动态照片 → LIVP 格式转换
- JPEG → HEIC 高效图像编码
- MP4 → MOV 容器格式转换
- 完整保留EXIF元数据
- 生成符合百度网盘识别标准的LIVP文件
- 支持批量处理

## 安装说明
1. 安装Python依赖：
   ```bash
   pip install pillow pillow-heif pyexiv2 mutagen
   ```
2. 安装外部工具：
   - [FFmpeg](https://ffmpeg.org/) → 用于MP4转MOV
   - [ExifTool](https://exiftool.org/) → 用于元数据处理

   macOS安装：
   ```bash
   brew install ffmpeg exiftool
   ```

## 使用教程
```bash
python3 convert_xiaomi_to_livp.py <输入目录> <输出目录>
```
**示例**：
```bash
python3 convert_xiaomi_to_livp.py ./source_photos ./output_livp
```

## 项目结构
```
├── convert_xiaomi_to_livp.py    # 核心转换脚本
├── README.md                    # 英文说明
└── README_CN.md                 # 中文说明（本文件）
```

---

## LIVP文件格式详细说明

### 1. 文件基本结构
LIVP文件本质上是一个**ZIP压缩包**，包含以下两个文件：
```
example.livp (ZIP)
├── IMG_XXXX.HEIC.heic    # HEIC格式的静态图片
└── IMG_XXXX.HEIC.mov     # MOV格式的视频片段
```

### 2. ZIP压缩格式要求

#### 2.1 压缩方法
- **必须使用`STORED`（无压缩）模式**
- 不能使用`DEFLATE`等压缩算法

#### 2.2 文件系统标识
- `create_system` 必须设置为 `0`（MS-DOS/FAT）
- 对应 `zipinfo` 输出中的 `file system or operating system of origin: MS-DOS, OS/2 or NT FAT`

#### 2.3 版本要求
- `version of encoding software`: 0.0
- `minimum software version required to extract`: 2.0

### 3. ZIP注释格式（关键）

LIVP文件**必须**包含56字节的ZIP注释，这是百度网盘识别的关键标识。

#### 3.1 注释结构
注释是一个56字节的**ASCII十六进制字符串**，结构如下：

| 偏移 | 长度 | 说明 | 示例值 |
|------|------|------|--------|
| 0 | 4字符 | 版本号 | `0002` |
| 4 | 8字符 | 固定标志 | `00000030` |
| 12 | 8字符 | HEIC文件大小（十六进制） | `0005eb7f` |
| 20 | 4字符 | 固定常量 | `0003` |
| 24 | 8字符 | HEIC文件大小+95（十六进制） | `0005ebde` |
| 32 | 8字符 | MOV文件大小（十六进制） | `0004a63a` |
| 40 | 16字符 | 魔术字符串 | `313030304c495650` |

#### 3.2 魔术字符串
- 最后16字符固定为 `313030304c495650`
- 这是字符串 `1000LIVP` 的ASCII十六进制表示

#### 3.3 计算公式
```python
# HEIC文件大小
heic_size = os.path.getsize(heic_path)

# MOV文件大小  
mov_size = os.path.getsize(mov_path)

# 构建注释
version = '0002'
flags = '00000030'
heic_size_hex = f'{heic_size:08x}'
constant = '0003'
heic_size_plus95_hex = f'{heic_size + 95:08x}'
mov_size_hex = f'{mov_size:08x}'
magic = '313030304c495650'  # "1000LIVP"

comment = (version + flags + heic_size_hex + constant + 
           heic_size_plus95_hex + mov_size_hex + magic).encode('ascii')
```

#### 3.4 注释示例
```
0002000000300005eb7f00030005ebde0004a63a313030304c495650
│    │    │    │    │    │    │
│    │    │    │    │    │    └── 魔术字符串 "1000LIVP"
│    │    │    │    │    └────── MOV文件大小
│    │    │    │    └─────────── HEIC文件大小+95
│    │    │    └──────────────── 固定常量 0003
│    │    └───────────────────── HEIC文件大小
│    └────────────────────────── 固定标志 00000030
└─────────────────────────────── 版本号 0002
```

### 4. 内部文件格式

#### 4.1 HEIC文件
- 格式：HEIF/HEVC（High Efficiency Image Format）
- 扩展名：`.heic`
- 文件名格式：`IMG_XXXX.HEIC.heic`（XXXX为4位数字）
- 必须包含完整的EXIF元数据

#### 4.2 MOV文件
- 格式：QuickTime MOV容器
- 编码：H.264视频 + AAC音频
- 扩展名：`.mov`
- 文件名格式：`IMG_XXXX.HEIC.mov`（与HEIC文件同名）

### 5. 时间戳要求
- ZIP内文件的修改时间应与原始文件一致
- 使用DOS日期时间格式（`date_time`元组）

### 6. 验证方法

#### 6.1 检查ZIP注释
```bash
zipinfo -v example.livp | grep -A 3 "zipfile comment"
```

#### 6.2 检查文件系统标识
```bash
zipinfo -v example.livp | grep "file system or operating system"
```

#### 6.3 检查压缩方法
```bash
zipinfo example.livp
# 应显示 "stor"（STORED模式）
```

---

## 常见问题

### Q: 为什么百度网盘不识别生成的LIVP文件？
A: 请检查以下几点：
1. ZIP注释是否为56字节
2. 注释格式是否正确（参考上方说明）
3. 文件系统标识是否为MS-DOS/FAT
4. 是否使用STORED压缩模式

### Q: HEIC文件大小+95是什么意思？
A: 这是LIVP格式的固定偏移量，可能是头部或元数据的大小。实际测试发现，HEIC文件大小加上95字节正好等于注释中的第二个大小值。

### Q: 可以保留JPEG格式不转换为HEIC吗？
A: 可以，但参考文件均使用HEIC格式。为保证兼容性，建议转换为HEIC。

## 鸣谢
参考了以下项目与文章：
- [AppleLIVP_to_XiaomiMotionPhoto](https://github.com/lft123454321/AppleLIVP_to_XiaomiMotionPhoto) - 本项目的逆向参考
- [iOS 实况照片 -> 小米动态照片 转换脚本](https://github.com/Serendo/LivePhoto2XiaomiPhoto)
- [小米实况图片提取](https://github.com/xiaotian2333/MI-Live-Photo-Transition)
- [MotionPhotoMuxer](https://github.com/mihir-io/MotionPhotoMuxer)
- [国内厂商动态照片/实况照片格式对比](https://blog.0to1.cf/posts/cn-motion-photo-format/)
- [关于 Android「动态照片」实现方式的探究](https://zhuanlan.zhihu.com/p/11126715794)

## 许可证
MIT License
