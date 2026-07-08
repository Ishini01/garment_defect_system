# 👕 Garment Defect Detection System

A Deep Learning-Based Computer Vision System for Automated Garment Quality Control

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Development-orange.svg)

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation Guide](#installation-guide)
- [Running the Application](#running-the-application)
- [Usage Guide](#usage-guide)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Team Members](#team-members)
- [License](#license)

---

## 🎯 Project Overview

The Garment Defect Detection System is an intelligent quality control solution designed for the garment manufacturing industry. It uses computer vision and deep learning techniques to automatically detect defects in shirts, specifically focusing on **button-related defects**.

### Problem Statement
Manual visual inspection in garment factories is:
- ❌ Slow and time-consuming
- ❌ Prone to human error and fatigue
- ❌ Inconsistent (60-75% accuracy rate)
- ❌ Costly for small and medium factories

### Our Solution
- ✅ Automated defect detection using AI
- ✅ Real-time image capture and analysis
- ✅ Instant PASS/FAIL classification
- ✅ Comprehensive reporting and history tracking
- ✅ Low-cost and accessible for any factory

---

## ✨ Features

### 🔐 Authentication System
- User Registration with Operator ID, Operator Name, NIC, and PIN
- Secure Login with PIN hashing (bcrypt)
- Forgot Password recovery using Operator ID + NIC verification
- Session Management

### 📊 Dashboard
- Real-time statistics dashboard
- Total inspections count
- Pass/Fail rate visualization
- Quick action buttons
- Operator details display

### 📷 Inspection Module
- Live camera capture (Webcam/Industrial Camera)
- Image upload from file system
- Automatic button detection using Circle Hough Transform
- Button count verification (expected: 7 buttons)
- Button alignment analysis
- Button spacing analysis
- Instant defect identification with alarm

### 📋 History & Reporting
- Complete inspection history
- Detailed view of past inspections
- PASS/FAIL status tracking
- Defect type categorization
- Report generation (Weekly/Monthly/Annual)

### 🔔 Alarm System
- Audio alert when defects are detected
- Visual notification on dashboard
- Defect type specific alerts

---

## 🛠️ Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.8+ | Programming Language |
| Flask | 2.3.3 | Web Framework |
| Flask-Login | 0.6.2 | User Authentication |
| Flask-WTF | 1.1.1 | Form Handling |
| Flask-SQLAlchemy | 3.0.5 | Database ORM |
| MySQL | 8.0 | Database |
| bcrypt | 4.1.1 | PIN Hashing |

### AI/Computer Vision
| Technology | Version | Purpose |
|------------|---------|---------|
| OpenCV | 4.8.1.78 | Image Processing |
| NumPy | 1.24.3 | Numerical Computing |
| Pillow | 10.1.0 | Image Manipulation |

### Frontend
| Technology | Purpose |
|------------|---------|
| HTML5 | Structure |
| CSS3 | Styling |
| Bootstrap 5 | UI Framework |
| JavaScript | Interactivity |
| Font Awesome | Icons |

---

## 📁 Project Structure
garment_defect_system/
│
├── backend/
│   ├── __init__.py                    # Makes backend a Python package
│   ├── app.py                         # Main Flask application (routes, config)
│   ├── models.py                      # Database models (User, InspectionSession, Defect)
│   ├── forms.py                       # WTForms for validation
│   │
│   ├── templates/                     # HTML Templates
│   │   ├── base.html                 # Base template with navigation
│   │   ├── login.html                # User login page
│   │   ├── register.html             # User registration page
│   │   ├── forgot_password.html      # Password reset request page
│   │   ├── reset_password.html       # Reset PIN with token
│   │   ├── dashboard.html            # Main dashboard with statistics
│   │   ├── inspect.html              # Inspection with camera and upload
│   │   ├── history.html              # Inspection history list
│   │   ├── reports.html              # Report generation page
│   │   └── profile.html              # User profile display
│   │
│   ├── static/                        # Static assets
│   │   ├── css/
│   │   │   └── style.css            # Custom CSS styles
│   │   ├── js/
│   │   │   └── main.js              # Custom JavaScript
│   │   ├── uploads/                  # Uploaded images directory
│   │   └── sounds/                   # Alarm sound files
│   │       └── alarm.wav            # Alarm sound
│   │
│   ├── routes/                        # Route handlers
│   │   ├── __init__.py               # Makes routes a package
│   │   ├── auth.py                   # Authentication routes (login, register, logout)
│   │   └── main.py                   # Main routes (dashboard, inspect, history)
│   │
│   └── utils/                         # Utility functions
│       ├── __init__.py               # Makes utils a package
│       ├── button_detector.py        # Button detection and analysis logic
│       ├── alarm.py                  # Audio alarm system
│       └── report_generator.py       # PDF report generation
│
├── models/                            # AI Models (YOLO models)
│   └── (button_model.pt will be placed here)
│
├── reports/                           # Generated PDF reports
│   └── (reports will be saved here)
│
├── data/                              # Dataset (training images)
│   └── (dataset will be placed here)
│
├── venv/                              # Virtual environment (ignored by git)
│
├── requirements.txt                   # Python package dependencies
├── .gitignore                         # Git ignore rules
├── README.md                          # Project documentation
├── run.py                             # Application entry point
└── .env                               # Environment variables (optional)
