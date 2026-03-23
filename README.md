# 🔓 Deep File Unblocker & Permission Fixer

Compatibility: Windows Only (Requires NTFS file system).
A powerful, multithreaded Windows utility designed to instantly fix restricted file permissions...

[![Latest Release](https://img.shields.io/github/v/release/Vova1975vn/Deep_File_Unblocker?label=version)](https://github.com/Vova1975vn/Deep_File_Unblocker/releases)
[![Downloads](https://img.shields.io/github/downloads/Vova1975vn/Deep_File_Unblocker/total?label=downloads)](https://github.com/Vova1975vn/Deep_File_Unblocker/releases)

A fast, multithreaded Windows utility to remove file security blocks and repair broken permissions across entire folders—instantly and safely.

---

## 🚀 Overview

Windows often restricts files downloaded from the internet or transferred between systems by:

- Adding a `Zone.Identifier` (Protected View warning)
- Breaking file permissions (ACL issues)

These restrictions can prevent you from opening, editing, or even accessing your own files.

**Deep File Unblocker** solves both problems in one click:
- Removes security blocks
- Takes ownership of files
- Restores full administrator access

All through a clean, responsive interface.

---

## ✨ Features

- 🔍 **Deep Directory Scanning**  
  Scan a single file or recursively process entire folders and drives  

- ⚡ **Dual-Action Engine**  
  - Removes `Zone.Identifier` (unblocks files)  
  - Repairs permissions using native Windows tools  

- 💽 **Smart Drive Detection**  
  Automatically handles FAT32/exFAT drives that don’t support Windows ACLs  

- 🧪 **Dry Run Mode**  
  Preview all changes before applying them  

- 🧵 **Multithreaded Processing**  
  Smooth UI with real-time progress—even on large directories  

- ⏯️ **Full Process Control**  
  Pause, resume, or cancel operations anytime  

- 📋 **Detailed Logging**  
  View, copy, or export logs for auditing and troubleshooting  

---

## 📥 Installation & Usage

You **do not need Python installed** to use this tool.

### Option 1: Download Prebuilt Version (Recommended)

1. Go to the [Releases](https://github.com/Vova1975vn/Deep_File_Unblocker/releases) page  
2. Download one of the following:

   - **Portable (`UnblockerApp_v2.exe`)**  
     → Run instantly (no installation required)

   - **Installer (`DeepUnblocker_Setup_v2.5.exe`)**  
     → Installs to Program Files and adds Start Menu shortcuts  

3. Run the application  
   - Administrator privileges will be requested automatically (required)

---

## ⚙️ Requirements

- Windows OS  
- Administrator privileges  

*(Python is only required if building from source)*

---

## 🛠️ How It Works (Technical Details)

This tool uses **native Windows commands** for maximum reliability:

- **Remove Protected View (ADS):**  
  ```
  cmd /c del /q /a "filename:Zone.Identifier"
  ```

- **Take Ownership:**  
  ```
  takeown /F "filename" /A
  ```

- **Reset Permissions:**  
  ```
  icacls "filename" /grant Administrators:F /C /Q
  ```

---

## 💻 Building From Source

### Requirements
- Python 3.8+
- Windows OS

### 1. Clone the repository
```bash
git clone https://github.com/Vova1975vn/Deep_File_Unblocker.git
cd Deep_File_Unblocker
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python main.py
```

---

## ⚠️ Important Notes

- This tool modifies **file ownership and permissions**
- Always use **Dry Run mode first** if unsure
- Administrator rights are required for full functionality

---

## 🙌 Credits

Created by **Dr. Vova**  
With assistance from **Google Gemini**

---

## ⭐ Support the Project

If you find this tool useful:
- Star ⭐ the repository  
- Share it with others  
- Report issues or suggest features  
