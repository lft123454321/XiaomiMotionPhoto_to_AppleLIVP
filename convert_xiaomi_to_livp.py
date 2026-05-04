#!/usr/bin/env python3
"""
Convert Xiaomi Motion Photo (JPEG with embedded MP4) to Apple Live Photo (LIVP) format.
"""

import os
import sys
import zipfile
import shutil
import subprocess
import tempfile
import json
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

def get_micro_video_offset(jpg_path: str) -> int:
    """Extract MicroVideoOffset from JPEG using exiftool."""
    cmd = ['exiftool', '-json', '-MicroVideoOffset', jpg_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"exiftool failed: {result.stderr}")
    data = json.loads(result.stdout)
    if not data or 'MicroVideoOffset' not in data[0]:
        raise ValueError("MicroVideoOffset not found")
    return int(data[0]['MicroVideoOffset'])

def split_motion_photo(jpg_path: str, output_dir: str):
    """Split motion photo into JPEG and MP4 files.
    Returns (jpeg_path, mp4_path)."""
    offset = get_micro_video_offset(jpg_path)
    file_size = os.path.getsize(jpg_path)
    jpeg_size = file_size - offset
    
    # Read binary data
    with open(jpg_path, 'rb') as f:
        jpeg_data = f.read(jpeg_size)
        mp4_data = f.read(offset)  # offset is size of MP4
    
    # Write JPEG
    jpeg_path = os.path.join(output_dir, 'temp.jpg')
    with open(jpeg_path, 'wb') as f:
        f.write(jpeg_data)
    
    # Write MP4
    mp4_path = os.path.join(output_dir, 'temp.mp4')
    with open(mp4_path, 'wb') as f:
        f.write(mp4_data)
    
    return jpeg_path, mp4_path

def convert_jpeg_to_heic(jpeg_path: str, heic_path: str, quality: int = 90):
    """Convert JPEG to HEIC using pillow-heif."""
    from PIL import Image
    import pillow_heif
    pillow_heif.register_heif_opener()
    
    with Image.open(jpeg_path) as img:
        img.save(heic_path, "HEIF", quality=quality)
    logging.info(f"Converted JPEG to HEIC: {heic_path}")

def copy_exif_data(source_jpeg: str, target_heic: str):
    """Copy EXIF metadata from source JPEG to target HEIC using exiftool."""
    cmd = [
        'exiftool',
        '-TagsFromFile', source_jpeg,
        '-All:All',
        '-overwrite_original',
        target_heic
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.warning(f"Failed to copy EXIF data: {result.stderr}")
    else:
        logging.info(f"Copied EXIF data from {source_jpeg} to {target_heic}")

def convert_mp4_to_mov(mp4_path: str, mov_path: str):
    """Convert MP4 to MOV using ffmpeg (copy streams)."""
    cmd = [
        'ffmpeg', '-i', mp4_path,
        '-c', 'copy',
        '-movflags', '+faststart',
        mov_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    logging.info(f"Converted MP4 to MOV: {mov_path}")

def create_livp(heic_path: str, mov_path: str, output_livp_path: str, img_filename: str, vid_filename: str, timestamp: float = None):
    """Create a LIVP (ZIP) file containing HEIC and MOV."""
    heic_size = os.path.getsize(heic_path)
    mov_size = os.path.getsize(mov_path)
    
    # Build comment: 56-byte ASCII string
    # Format: version(4) + flags(8) + heic_size(8) + constant(4) + heic_size+95(8) + mov_size(8) + magic(16)
    version = '0002'
    flags = '00000030'
    heic_size_hex = f'{heic_size:08x}'
    constant = '0003'
    heic_size_plus95_hex = f'{heic_size + 95:08x}'
    mov_size_hex = f'{mov_size:08x}'
    magic = '313030304c495650'  # "1000LIVP" in ASCII hex
    
    comment = (version + flags + heic_size_hex + constant + heic_size_plus95_hex + mov_size_hex + magic).encode('ascii')
    
    with zipfile.ZipFile(output_livp_path, 'w', zipfile.ZIP_STORED) as zf:
        zf.comment = comment
        
        # Set modification time for each file
        if timestamp is not None:
            time_tuple = time.localtime(timestamp)
            date_time = time_tuple[:6]
        else:
            date_time = None
        
        # Add HEIC file
        info = zipfile.ZipInfo(img_filename, date_time=date_time)
        info.create_system = 0  # MS-DOS/FAT
        info.extra = b''  # No extra field
        with open(heic_path, 'rb') as f:
            zf.writestr(info, f.read())
        
        # Add MOV file
        info = zipfile.ZipInfo(vid_filename, date_time=date_time)
        info.create_system = 0  # MS-DOS/FAT
        info.extra = b''  # No extra field
        with open(mov_path, 'rb') as f:
            zf.writestr(info, f.read())
    logging.info(f"Created LIVP: {output_livp_path}")

def convert_single(input_jpg: str, output_dir: str, index: int):
    """Convert a single Xiaomi motion photo to LIVP."""
    # Prepare output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filenames
    base_name = Path(input_jpg).stem
    # Try to extract date from filename (e.g., 微信图片_20260504222502_6540_120)
    # Format: 微信图片_YYYYMMDDHHMMSS_...
    parts = base_name.split('_')
    if len(parts) >= 2 and len(parts[1]) >= 14:
        date_str = parts[1][:14]  # YYYYMMDDHHMMSS
        # Convert to YYYY-MM-DD HHMMSS
        formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}{date_str[10:12]}{date_str[12:14]}"
        livp_name = f"{formatted}.livp"
    else:
        livp_name = f"{base_name}.livp"
    
    livp_path = os.path.join(output_dir, livp_name)
    
    # Internal filenames (similar to reference)
    img_filename = f"IMG_{index:04d}.HEIC.heic"
    vid_filename = f"IMG_{index:04d}.HEIC.mov"
    
    # Get original file modification time
    mtime = os.path.getmtime(input_jpg)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Split motion photo
        jpeg_path, mp4_path = split_motion_photo(input_jpg, temp_dir)
        
        # Convert JPEG to HEIC
        heic_path = os.path.join(temp_dir, 'temp.heic')
        convert_jpeg_to_heic(jpeg_path, heic_path)
        
        # Copy EXIF data from original JPEG to HEIC
        copy_exif_data(jpeg_path, heic_path)
        
        # Convert MP4 to MOV
        mov_path = os.path.join(temp_dir, 'temp.mov')
        convert_mp4_to_mov(mp4_path, mov_path)
        
        # Create LIVP with original modification time
        create_livp(heic_path, mov_path, livp_path, img_filename, vid_filename, timestamp=mtime)
    
    logging.info(f"Successfully converted {input_jpg} -> {livp_path}")
    return livp_path

def batch_convert(input_dir: str, output_dir: str):
    """Convert all Xiaomi motion photos in input_dir."""
    # Find all JPEG files (could be .jpg or .jpeg)
    input_files = []
    for ext in ('*.jpg', '*.jpeg', '*.JPG', '*.JPEG'):
        input_files.extend(Path(input_dir).glob(ext))
    
    if not input_files:
        logging.warning(f"No JPEG files found in {input_dir}")
        return
    
    logging.info(f"Found {len(input_files)} JPEG files")
    
    # Process each file
    for idx, input_file in enumerate(input_files, start=1):
        try:
            convert_single(str(input_file), output_dir, idx)
        except Exception as e:
            logging.error(f"Failed to convert {input_file}: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_directory> <output_directory>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    batch_convert(input_dir, output_dir)