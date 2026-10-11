<div align="center">

# 🧵 Garment Defect Detection System

### A Deep Learning-Based Computer Vision System for Garment Quality Inspection

*Detecting broken stitches, missing/misaligned buttons, missing or defective labels, and color imbalance — with a live dashboard for results and reporting.*

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?logo=tensorflow&logoColor=white)
![YOLO11](https://img.shields.io/badge/YOLO11-Ultralytics-111F68?logo=ultralytics&logoColor=00FFF0)
![ResNet](https://img.shields.io/badge/ResNet-50-EE4C2C?logo=pytorch&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?logo=opencv&logoColor=white)
![Tesseract OCR](https://img.shields.io/badge/OCR-Tesseract-4285F4?logo=google&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![XAMPP](https://img.shields.io/badge/XAMPP-FB7A24?logo=xampp&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/status-in%20development-orange)

**🎓 Team Aurors** — Faculty of Applied Sciences, Rajarata University of Sri Lanka (2021/2022 Batch)  
Supervised by **Mr. E.A.C.I. Senaratne**

</div>

<br>

| 👤 Name | 🆔 Registration No. | 🔢 Index No. |
|---|:---:|:---:|
| M.A.I.A. Ranathunga | ICT/2022/082 | 5686 |
| C. Ashini Kumarawadu | ICT/2022/033 | 5639 |
| M.F.F. Fazeena | ICT/2022/024 | 5631 |
| G.C.P.A. Hemasiri | ICT/2022/067 | 5671 |
| I.O. Subasinghe | ICT/2022/002 | 5610 |

---

## 📑 Table of Contents

- [🎯 Problem Statement](#-problem-statement)
- [🚀 Objectives](#-objectives)
- [✨ Key Features](#-key-features)
- [🏗️ System Architecture](#️-system-architecture)
- [🔍 Detection Modules](#-detection-modules)
- [🛠️ Technology Stack](#️-technology-stack)
- [📁 Repository Structure](#-repository-structure)
- [⚡ Getting Started](#-getting-started)
- [🗄️ Database Setup](#️-database-setup)
- [📊 Dataset](#-dataset)
- [🧠 Model Training](#-model-training)
- [📚 Documentation](#-documentation)
- [📈 Non-Functional Targets](#-non-functional-targets)
- [📄 License](#-license)

---

## 🎯 Problem Statement

> 🧑‍🏭 Manual visual inspection accuracy in garment factories typically ranges between **60–75%**, leaving a large share of defects undetected.

Critical defects — broken or skipped stitches, missing/misaligned buttons, absent or incorrect labels, and color imbalance — often escape detection until later production stages, increasing rework costs and damaging brand reputation. Most existing computer-vision inspection tools address only a **single** defect type and are too costly for small/medium-scale factories.

This project delivers a **low-cost, integrated inspection platform** that detects all four defect categories in one system and generates structured inspection reports for operational decision-making.

## 🚀 Objectives

**🎯 Main Objective**
> Develop a low-cost garment defect detection system using image processing techniques, capable of detecting broken stitches, missing buttons and button alignment defects, missing garment labels and label defects, and color imbalances — with a dashboard for result visualization and report generation.

**✅ Sub-Objectives**

| # | Objective |
|:---:|---|
| 1 | 🧵 Detect broken stitches using image processing techniques |
| 2 | 🔘 Detect missing buttons and button alignment defects via presence, shape, and spatial-arrangement analysis |
| 3 | 🎨 Identify color imbalance using color space analysis |
| 4 | 🏷️ Detect missing garment labels and label defects (fading, misprinting) using region-based, texture, and color feature analysis |
| 5 | 📊 Design and develop a dashboard for visualizing results and generating inspection reports |

## ✨ Key Features

- 📷 Real-time image capture (USB/industrial camera) or batch image upload
- 🤖 Four independent AI defect-detection modules running per inspection
- ⚖️ Rule-based decision engine aggregating module outputs into a **PASS / FAIL** result
- 🔐 Operator authentication with PIN-based login and email-based recovery
- 🕒 Inspection history tracking and PDF/CSV report generation
- 🖥️ Web dashboard for operators with minimal technical background

## 🏗️ System Architecture

The system follows a layered, modular architecture (see SDS §2.1) built on **Scrum** (process model) and **MVC** (architectural pattern):

Each detection module handles its own preprocessing (resizing, normalization, ROI extraction), so no separate shared preprocessing layer is required.

## 🔍 Detection Modules

| Module | Approach | Primary Technologies | Status |
|---|---|---|---|
| 🧵 **Broken Stitches Detection** | CNN texture analysis + Canny edge detection | ![TensorFlow](https://img.shields.io/badge/-TensorFlow-FF6F00?logo=tensorflow&logoColor=white) ![OpenCV](https://img.shields.io/badge/-OpenCV-5C3EE8?logo=opencv&logoColor=white) | 🟡 In Progress |
| 🔘 **Missing Buttons & Alignment** | Object detection + template comparison | ![TensorFlow](https://img.shields.io/badge/-YOLO%2FSSD-FF6F00?logo=tensorflow&logoColor=white) | 🟡 In Progress |
| 🏷️ **Missing Labels Detection** | Object detection (label presence) + OCR verification | ![YOLO11](https://img.shields.io/badge/-YOLO11-111F68?logo=ultralytics&logoColor=00FFF0) ![Tesseract](https://img.shields.io/badge/-Tesseract%20OCR-4285F4?logo=google&logoColor=white) | 🟡 In Progress |
| 🎨 **Color Imbalance Detection** | **ResNet-based** deep classifier on LAB/HSV color space features | ![ResNet](https://img.shields.io/badge/-ResNet-EE4C2C?logo=pytorch&logoColor=white) ![OpenCV](https://img.shields.io/badge/-OpenCV-5C3EE8?logo=opencv&logoColor=white) ![NumPy](https://img.shields.io/badge/-NumPy-013243?logo=numpy&logoColor=white) | ✅ **Integrated** |

> 💡 **Note on Label Detection:** The SDS specifies a CNN classifier + OCR for label detection. The implemented version uses **YOLO11** as an object detector instead of a plain classifier — this additionally localizes the label region, which makes the OCR verification step (Tesseract, run on the cropped region) significantly more accurate than running OCR on the full image.

> 💡 **Note on Color Imbalance Detection:** The SDS specified a statistical LAB/HSV analysis approach. The implemented version uses a **ResNet-based deep classifier** trained on color distribution features — this achieves higher accuracy and robustness to lighting variation than pure statistical methods, while still leveraging LAB/HSV preprocessing for input normalization. The module is **fully integrated** into the Flask web dashboard and its verdict (Balanced / Imbalanced) is displayed live on the inspection result screen and stored in every inspection record.

## 🛠️ Technology Stack

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![Keras](https://img.shields.io/badge/Keras-D00000?style=for-the-badge&logo=keras&logoColor=white)
![ResNet](https://img.shields.io/badge/ResNet-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Ultralytics](https://img.shields.io/badge/YOLO11-111F68?style=for-the-badge&logo=ultralytics&logoColor=00FFF0)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Tesseract](https://img.shields.io/badge/Tesseract_OCR-4285F4?style=for-the-badge&logo=google&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![XAMPP](https://img.shields.io/badge/XAMPP-FB7A24?style=for-the-badge&logo=xampp&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![GoogleColab](https://img.shields.io/badge/Google_Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)

</div>

| Category | Technologies |
|---|---|
| 🐍 Language | Python |
| 🧠 Deep Learning | TensorFlow / Keras, Ultralytics YOLO11, **ResNet** |
| 👁️ Computer Vision | OpenCV, NumPy |
| 🔤 OCR | Tesseract OCR (pytesseract) |
| 🔄 Data Augmentation | Albumentations, TensorFlow `ImageDataGenerator` |
| 📈 Supplementary ML | scikit-learn |
| 🖥️ Web Framework | Flask (Jinja2 templates, Flask-Login, Flask-WTF, Flask-Mail) |
| 🗄️ Database | **MySQL via XAMPP** (Apache + MySQL + phpMyAdmin stack) |
| 🔗 ORM | Flask-SQLAlchemy + PyMySQL driver |
| 📄 Reporting | pandas, ReportLab / fpdf |
| 📧 Email | Flask-Mail (Gmail SMTP for PIN recovery) |
| ☁️ Model Training | Google Colab (free GPU access) |
| 🔀 Version Control | Git / GitHub |
| 📐 Diagramming | Draw.io / Lucidchart |
| 🎨 UI Mockups | Canva |

## 📁 Repository Structure

## ⚡ Getting Started

### ✅ Prerequisites

- 🐍 Python 3.9+
- 📦 pip
- 🗄️ **XAMPP** (for MySQL — see [Database Setup](#️-database-setup))
- 🎮 (Optional) NVIDIA GPU + CUDA for local training; otherwise use Google Colab
- 🔤 Tesseract OCR engine installed on the host system (for the label-defect module)

### 📥 Installation

```bash
git clone https://github.com/<your-org>/<your-repo>.git
cd garment_defect_system
python -m pip install -r requirements.txt
