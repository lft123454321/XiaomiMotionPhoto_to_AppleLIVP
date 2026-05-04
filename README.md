# Xiaomi Motion Photo to Apple LIVP Converter

[中文说明](README_CN.md)

## Overview
Convert Xiaomi Motion Photos to Apple iOS compatible LIVP (Live Photo) format that can be recognized by Baidu Netdisk.  
Platform: **macOS / Linux / Windows**  
Python: **3.8+**

## Features
- Xiaomi Motion Photo → LIVP conversion
- JPEG → HEIC high-efficiency image encoding
- MP4 → MOV container format conversion
- Complete EXIF metadata preservation
- Generates LIVP files compatible with Baidu Netdisk
- Batch processing support

## Installation
1. Install Python dependencies:
   ```bash
   pip install pillow pillow-heif pyexiv2
   ```
2. Install external tools:
   - [FFmpeg](https://ffmpeg.org/) - for MP4 to MOV conversion
   - [ExifTool](https://exiftool.org/) - for metadata processing

   macOS installation:
   ```bash
   brew install ffmpeg exiftool
   ```

## Usage
```bash
python3 convert_xiaomi_to_livp.py <input_directory> <output_directory>
```

**Example**:
```bash
python3 convert_xiaomi_to_livp.py ./source_photos ./output_livp
```

## Project Structure
```
├── convert_xiaomi_to_livp.py    # Core conversion script
├── README.md                    # English documentation (this file)
└── README_CN.md                 # Chinese documentation
```

---

## LIVP File Format Specification

### 1. Basic Structure
An LIVP file is essentially a **ZIP archive** containing two files:
```
example.livp (ZIP)
├── IMG_XXXX.HEIC.heic    # Static image in HEIC format
└── IMG_XXXX.HEIC.mov     # Video clip in MOV format
```

### 2. ZIP Archive Requirements

#### 2.1 Compression Method
- **MUST use `STORED` (no compression) mode**
- Do NOT use `DEFLATE` or other compression algorithms

#### 2.2 File System Identifier
- `create_system` must be set to `0` (MS-DOS/FAT)
- Corresponds to `file system or operating system of origin: MS-DOS, OS/2 or NT FAT` in `zipinfo` output

#### 2.3 Version Requirements
- `version of encoding software`: 0.0
- `minimum software version required to extract`: 2.0

### 3. ZIP Comment Format (Critical)

LIVP files **MUST** contain a 56-byte ZIP comment, which is the key identifier for Baidu Netdisk recognition.

#### 3.1 Comment Structure
The comment is a 56-byte **ASCII hexadecimal string** with the following structure:

| Offset | Length | Description | Example |
|--------|--------|-------------|---------|
| 0 | 4 chars | Version | `0002` |
| 4 | 8 chars | Fixed flags | `00000030` |
| 12 | 8 chars | HEIC file size (hex) | `0005eb7f` |
| 20 | 4 chars | Fixed constant | `0003` |
| 24 | 8 chars | HEIC size + 95 (hex) | `0005ebde` |
| 32 | 8 chars | MOV file size (hex) | `0004a63a` |
| 40 | 16 chars | Magic string | `313030304c495650` |

#### 3.2 Magic String
- The last 16 characters are always `313030304c495650`
- This is the ASCII hexadecimal representation of `1000LIVP`

#### 3.3 Calculation Formula
```python
# Get file sizes
heic_size = os.path.getsize(heic_path)
mov_size = os.path.getsize(mov_path)

# Build comment
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

#### 3.4 Comment Example
```
0002000000300005eb7f00030005ebde0004a63a313030304c495650
│    │    │    │    │    │    │
│    │    │    │    │    │    └── Magic string "1000LIVP"
│    │    │    │    │    └────── MOV file size
│    │    │    │    └─────────── HEIC size + 95
│    │    │    └──────────────── Fixed constant 0003
│    │    └───────────────────── HEIC file size
│    └────────────────────────── Fixed flags 00000030
└─────────────────────────────── Version 0002
```

### 4. Internal File Formats

#### 4.1 HEIC File
- Format: HEIF/HEVC (High Efficiency Image Format)
- Extension: `.heic`
- Filename pattern: `IMG_XXXX.HEIC.heic` (XXXX is 4-digit number)
- Must contain complete EXIF metadata

#### 4.2 MOV File
- Format: QuickTime MOV container
- Codec: H.264 video + AAC audio
- Extension: `.mov`
- Filename pattern: `IMG_XXXX.HEIC.mov` (same name as HEIC file)

### 5. Timestamp Requirements
- Modification time of files in ZIP should match original files
- Use DOS date/time format (`date_time` tuple)

### 6. Verification Methods

#### 6.1 Check ZIP Comment
```bash
zipinfo -v example.livp | grep -A 3 "zipfile comment"
```

#### 6.2 Check File System Identifier
```bash
zipinfo -v example.livp | grep "file system or operating system"
```

#### 6.3 Check Compression Method
```bash
zipinfo example.livp
# Should show "stor" (STORED mode)
```

---

## FAQ

### Q: Why doesn't Baidu Netdisk recognize the generated LIVP file?
A: Please check the following:
1. Is the ZIP comment exactly 56 bytes?
2. Is the comment format correct (refer to specification above)?
3. Is the file system identifier MS-DOS/FAT?
4. Is STORED compression mode used?

### Q: What does "HEIC size + 95" mean?
A: This is a fixed offset in the LIVP format, possibly for header or metadata size. Testing shows that adding 95 bytes to the HEIC file size equals the second size value in the comment.

### Q: Can I keep JPEG format instead of converting to HEIC?
A: Yes, but all reference files use HEIC format. For best compatibility, conversion to HEIC is recommended.

## Acknowledgments
References and inspirations:
- [AppleLIVP_to_XiaomiMotionPhoto](https://github.com/lft123454321/AppleLIVP_to_XiaomiMotionPhoto) - Reverse engineering reference
- [iOS Live Photo to Xiaomi Motion Photo Script](https://github.com/Serendo/LivePhoto2XiaomiPhoto)
- [Xiaomi Motion Photo Extraction](https://github.com/xiaotian2333/MI-Live-Photo-Transition)
- [MotionPhotoMuxer](https://github.com/mihir-io/MotionPhotoMuxer)
- [Comparison of Dynamic/Motion Photo Formats Among Domestic Manufacturers](https://blog.0to1.cf/posts/cn-motion-photo-format/)
- [Exploring Android Motion Photo Implementations](https://zhuanlan.zhihu.com/p/11126715794)

## License
MIT License
