<div align="center">

# 🧵 Garment Defect Detection System

### A Deep Learning-Based Computer Vision System for Garment Quality Inspection

*Detecting broken stitches, missing/misaligned buttons, missing or defective labels, and color imbalance — with a live dashboard for results and reporting.*

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?logo=tensorflow&logoColor=white)
![YOLO11](https://img.shields.io/badge/YOLO11-Ultralytics-111F68?logo=ultralytics&logoColor=00FFF0)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?logo=opencv&logoColor=white)
![Tesseract OCR](https://img.shields.io/badge/OCR-Tesseract-4285F4?logo=google&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
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
- 🔐 Operator authentication with PIN-based login and recovery
- 🕒 Inspection history tracking and PDF/CSV report generation
- 🖥️ Desktop dashboard for operators with minimal technical background

## 🏗️ System Architecture

The system follows a layered, modular architecture (see SDS §2.1) built on **Scrum** (process model) and **MVC** (architectural pattern):

```
🖥️  Presentation Layer   → Dashboard, image capture/upload UI, result viewer, report generator
⚙️  Application Layer    → Orchestrates modules, aggregates results, manages workflow & errors
🧠  Defect Detection Layer (AI Core)
      ├─ 🧵 Broken Stitches Detection      (CNN + Canny edge detection)
      ├─ 🔘 Missing Buttons & Alignment    (YOLO/SSD object detection)
      ├─ 🏷️ Missing Labels & Label Defects (CNN / YOLO detector + Tesseract OCR)
      └─ 🎨 Color Imbalance Detection      (LAB/HSV color space analysis)
🗄️  Database Layer        → Operator credentials, inspection sessions, defect records
📥  Image Input Layer     → USB/industrial camera or file upload
```

Each detection module handles its own preprocessing (resizing, normalization, ROI extraction), so no separate shared preprocessing layer is required.

## 🔍 Detection Modules

| Module | Approach | Primary Technologies |
|---|---|---|
| 🧵 **Broken Stitches Detection** | CNN texture analysis + Canny edge detection | ![TensorFlow](https://img.shields.io/badge/-TensorFlow-FF6F00?logo=tensorflow&logoColor=white) ![OpenCV](https://img.shields.io/badge/-OpenCV-5C3EE8?logo=opencv&logoColor=white) |
| 🔘 **Missing Buttons & Alignment** | Object detection + template comparison | ![TensorFlow](https://img.shields.io/badge/-YOLO%2FSSD-FF6F00?logo=tensorflow&logoColor=white) |
| 🏷️ **Missing Labels Detection** | Object detection (label presence) + OCR verification | ![YOLO11](https://img.shields.io/badge/-YOLO11-111F68?logo=ultralytics&logoColor=00FFF0) ![Tesseract](https://img.shields.io/badge/-Tesseract%20OCR-4285F4?logo=google&logoColor=white) |
| 🎨 **Color Imbalance Detection** | LAB/HSV color space variance analysis | ![OpenCV](https://img.shields.io/badge/-OpenCV-5C3EE8?logo=opencv&logoColor=white) ![NumPy](https://img.shields.io/badge/-NumPy-013243?logo=numpy&logoColor=white) |

> 💡 **Note:** The SDS specifies a CNN classifier + OCR for label detection. The implemented version uses **YOLO11** as an object detector instead of a plain classifier — this additionally localizes the label region, which makes the OCR verification step (Tesseract, run on the cropped region) significantly more accurate than running OCR on the full image.

## 🛠️ Technology Stack

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![Keras](https://img.shields.io/badge/Keras-D00000?style=for-the-badge&logo=keras&logoColor=white)
![Ultralytics](https://img.shields.io/badge/YOLO11-111F68?style=for-the-badge&logo=ultralytics&logoColor=00FFF0)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Tesseract](https://img.shields.io/badge/Tesseract_OCR-4285F4?style=for-the-badge&logo=google&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Qt](https://img.shields.io/badge/PyQt-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![GoogleColab](https://img.shields.io/badge/Google_Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)

</div>

| Category | Technologies |
|---|---|
| 🐍 Language | Python |
| 🧠 Deep Learning | TensorFlow / Keras, Ultralytics YOLO11 |
| 👁️ Computer Vision | OpenCV, NumPy |
| 🔤 OCR | Tesseract OCR (pytesseract) |
| 🔄 Data Augmentation | Albumentations, TensorFlow `ImageDataGenerator` |
| 📈 Supplementary ML | scikit-learn |
| 🖼️ UI Framework | Tkinter / PyQt (desktop), Flask (web dashboard alternative) |
| 🗄️ Database | MySQL (design), SQLite (lightweight local deployment) |
| 📄 Reporting | pandas, ReportLab / fpdf |
| ☁️ Model Training | Google Colab (free GPU access) |
| 🔀 Version Control | Git / GitHub |
| 📐 Diagramming | Draw.io / Lucidchart |
| 🎨 UI Mockups | Canva |

## 📁 Repository Structure

```
├── 📊 data/                       # Dataset (raw images, annotations) — see Dataset section
├── 🧠 models/
│   ├── 🧵 broken_stitches/        # Stitch defect detection model + training notebook
│   ├── 🔘 missing_buttons/        # Button detection model + training notebook
│   ├── 🏷️ missing_labels/         # Missing label detection (YOLO11 + OCR) model + notebook
│   └── 🎨 color_imbalance/        # Color imbalance analysis module
├── 🖥️ app/
│   ├── model/                     # Business logic, detection orchestration
│   ├── view/                      # UI screens (dashboard, capture, history, reports)
│   └── controller/                # Request handling, session management
├── 🗄️ database/                   # Schema, migrations, MySQL/SQLite setup
├── 📚 docs/                       # SRS, SDS, user manual, diagrams
└── 📄 README.md
```

*(Adjust this to match your actual folder layout as the codebase grows.)*

## ⚡ Getting Started

### ✅ Prerequisites

- 🐍 Python 3.9+
- 📦 pip
- 🎮 (Optional) NVIDIA GPU + CUDA for local training; otherwise use Google Colab
- 🔤 Tesseract OCR engine installed on the host system (for the label-defect module)

### 📥 Installation

```bash
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
```

### ▶️ Running the Application

```bash
python app/main.py
```

*(Update this once the entry point / packaging is finalized.)*

## 📊 Dataset

- 🎯 Target: 2,000–2,500 base images across all defect categories plus defect-free images (~450–500 images per defect type), collected via stratified sampling.
- ✂️ Split: **80%** training / **10%** validation / **10%** testing.
- 🔄 Augmentation (rotation, brightness, zoom, noise) is applied to improve robustness and generalization — see each module's training notebook for the exact augmentation pipeline used.
- 🏷️ Raw images and YOLO-format annotations for the Missing Labels module live under `data/raw_images/MissingLabels/{Images,Labels}`.

## 🧠 Model Training

Each detection model is trained in **☁️ Google Colab** (free GPU access) using the corresponding notebook under `models/<module>/`. General workflow:

1. 📂 Open the module's notebook in Colab and mount Google Drive.
2. ⚙️ Configure dataset paths and hyperparameters in the config cell.
3. ▶️ Run data loading/validation → (optional augmentation) → training → evaluation cells in order.
4. 💾 Trained weights are saved back to Google Drive for reuse in the desktop application.

Evaluation is reported using **accuracy, precision, recall, F1 score, false positive/negative rates, and inference time** — with training/validation loss and accuracy curves plotted to monitor convergence and overfitting.

## 📚 Documentation

- 📋 Software Requirements Specification (SRS)
- 📐 Software Design Specification (SDS) — this repository implements the design described there
- 📖 User Manual / Installation Guide
- 🗺️ UML diagrams (Class, Sequence, State Machine) — see `docs/`

## 📈 Non-Functional Targets

| Aspect | Target |
|---|---|
| ⚡ Performance | Process each image within 5 seconds; support 4 images per inspection cycle |
| 🎯 Accuracy | ≥ 95% overall classification accuracy |
| 🛡️ Reliability | ≥ 95% successful defect-storage and report-generation rate |
| 📈 Scalability | Modular architecture supports adding new defect types |
| 🖱️ Usability | Simple graphical interface for non-technical factory operators |

## 📄 License

*(Add your chosen license here, e.g. MIT.)*

<div align="center">

---

Made with 💙 by **Team Aurors**

</div>

