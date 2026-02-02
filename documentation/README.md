# Documentation Index

This directory contains comprehensive guides, technical references, and process documentation for the Prince 3D printing system. Documentation is organized by topic and user experience level.

## Table of Contents

- [Getting Started](#getting-started)
- [Setup Guides](#setup-guides)
- [Process Guides](#process-guides)
- [Technical References](#technical-references)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### For New Users

**Start here:**
1. **`UNDERGRADUATE_TEAM_GUIDE.md`** - Beginner-friendly introduction
   - Basic concepts and terminology
   - Hardware overview
   - Simple printing workflow
   - Safety and best practices

2. **`PRE_PRINT_SETUP_GUIDE.md`** - Step-by-step setup procedures
   - Hardware connections
   - Software configuration
   - Calibration procedures
   - First print walkthrough

3. **`PRINTING_PROCESS_GUIDE.md`** - Normal printing operations
   - Print flow overview
   - Monitoring prints
   - Data logging
   - Common issues

### For Experienced Users

**Quick references:**
- **`QUICK_REFERENCE.md`** (if exists) - Common commands and parameters
- **`DEPLOYMENT_GUIDE.md`** - System deployment and updates
- **`technical/`** - Detailed technical specifications

---

## Setup Guides

### `PRE_PRINT_SETUP_GUIDE.md`
**Complete setup procedures from hardware to first print**

**When to use:** First time setup, after hardware changes, system troubleshooting, training new users

**Key Sections:**
- System Overview
- Hardware Setup
- Software Launch
- Force Gauge Calibration
- Camera Calibration
- Stage Homing
- DLP Verification
- First Print
- Quick Reference Summary

---

### `DEPLOYMENT_GUIDE.md`
**Deploy system updates and maintain installations**

**When to use:** Deploying to new printer, updating existing installation, system migration, backup/restore

**Key Sections:**
- Critical Files
- Update Procedures
- Testing & Verification
- Backup Procedures
- Folder Structure
- Version Control

---

## Process Guides

### `PRINTING_PROCESS_GUIDE.md`
**Complete reference for print operations and troubleshooting**

**When to use:** Normal printing operations, understanding print behavior, diagnosing issues, optimizing parameters

**Key Sections:**
- Print Flow Overview
- Layer Sequencing
- 2-Stage Smooth Motion Profiles
- Three-Tier Data Logging System
- Phase Detection
- Adhesion Analysis
- Monitoring & Troubleshooting

---

### `UNDERGRADUATE_TEAM_GUIDE.md`
**Accessible introduction for undergraduate researchers**

**When to use:** Onboarding new team members, training undergraduate researchers, reviewing basic concepts

**Key Features:**
- Simple language
- Annotated diagrams
- Practical examples
- Safety reminders

**Key Sections:**
- What is Prince?
- How DLP Printing Works
- The Printing Process
- Force Measurement
- Data Analysis
- Running Experiments
- Best Practices

---

## Technical References

### `technical/` Directory

**Contains detailed technical specifications and algorithm documentation:**

#### Scientific Methodology
- **`WORK_OF_ADHESION_METRICS_DEFINITIONS.md`** - Detailed definitions and calculations for adhesion metrics
- **`ANALYSIS_RESULTS_COMPARISON.md`** - Methodology for comparing and validating analysis results

#### Implementation Details
- **`UNIFIED_CALCULATOR_IMPLEMENTATION.md`** - Technical details of the calculator implementation
- **`POST_PRINT_ANALYSIS_INTEGRATION.md`** - Integration documentation for post-print analysis
- **`LAYER_BOUNDARY_DETECTION.md`** - Algorithm for detecting layer boundaries in print data

#### Architecture & Algorithms
- System component interactions
- Data flow diagrams
- API references
- Class hierarchies

**When to use:** Developing new features, understanding algorithms, debugging complex issues, extending functionality

---

### `project_status/` Directory

**Contains project updates and historical documentation:**

- **`PROJECT_UPDATE_HYBRID_SYSTEM.md`** - Latest system updates and changes
- **`HYBRID_SYSTEM_SUCCESS_REPORT.md`** - Complete project documentation with results
- **`HYBRID_SYSTEM_BACKUP_MANIFEST.md`** - System backup information and organization

---

## Troubleshooting

### Issue-Specific Guides

Most guides include dedicated troubleshooting sections:

**Setup Issues:** → `PRE_PRINT_SETUP_GUIDE.md` § Common Setup Issues  
**Print Problems:** → `PRINTING_PROCESS_GUIDE.md` § Troubleshooting  
**Data Issues:** → `../post-processing/README.md` § Troubleshooting  
**Hardware Issues:** → `PRE_PRINT_SETUP_GUIDE.md` § Hardware Connections

### Common Issue Categories

1. **Hardware Connection Issues** - Force gauge, DLP, stage, camera
2. **Print Quality Issues** - High forces, failures, poor adhesion
3. **Data Logging Issues** - Missing files, incorrect labels, plot failures
4. **Software Issues** - Crashes, slow performance, import errors

---

## Reading Path by Role

### Undergraduate Researcher
```
1. UNDERGRADUATE_TEAM_GUIDE.md       (understand system)
2. PRE_PRINT_SETUP_GUIDE.md          (setup procedures)
3. PRINTING_PROCESS_GUIDE.md         (run experiments)
4. ../post-processing/README.md      (analyze data)
```

### Graduate Student / Lead Developer
```
1. PRE_PRINT_SETUP_GUIDE.md          (system overview)
2. PRINTING_PROCESS_GUIDE.md         (detailed operations)
3. DEPLOYMENT_GUIDE.md               (maintenance)
4. technical/                        (algorithms and specs)
5. ../support_modules/README.md      (code documentation)
```

### New Lab Member (Hardware Experience)
```
1. UNDERGRADUATE_TEAM_GUIDE.md       (quick intro)
2. PRE_PRINT_SETUP_GUIDE.md          (hands-on setup)
3. PRINTING_PROCESS_GUIDE.md         (start printing)
```

---

## Directory Structure

```
documentation/
├── README.md                               # This file - documentation index
├── PRE_PRINT_SETUP_GUIDE.md                # Complete setup procedures
├── PRINTING_PROCESS_GUIDE.md               # Print operations guide
├── DEPLOYMENT_GUIDE.md                     # System deployment
├── UNDERGRADUATE_TEAM_GUIDE.md             # Beginner's guide
│
├── technical/                              # Technical references
│   ├── WORK_OF_ADHESION_METRICS_DEFINITIONS.md
│   ├── ANALYSIS_RESULTS_COMPARISON.md
│   ├── UNIFIED_CALCULATOR_IMPLEMENTATION.md
│   ├── POST_PRINT_ANALYSIS_INTEGRATION.md
│   └── LAYER_BOUNDARY_DETECTION.md
│
├── project_status/                         # Project history
│   ├── PROJECT_UPDATE_HYBRID_SYSTEM.md
│   ├── HYBRID_SYSTEM_SUCCESS_REPORT.md
│   └── HYBRID_SYSTEM_BACKUP_MANIFEST.md
│
└── implementation/                         # Code examples
    └── (Example implementations and usage guides)
```

---

## Document Relationships

1. **Scientific methodology** in `WORK_OF_ADHESION_METRICS_DEFINITIONS.md` is implemented in the calculator as documented in `UNIFIED_CALCULATOR_IMPLEMENTATION.md`

2. **Layer boundary detection** algorithm in `LAYER_BOUNDARY_DETECTION.md` is used by the post-print analysis system described in `POST_PRINT_ANALYSIS_INTEGRATION.md`

3. **Project updates** in `PROJECT_UPDATE_HYBRID_SYSTEM.md` reference the implementation details from other technical documents

4. **Setup procedures** in `PRE_PRINT_SETUP_GUIDE.md` reference technical details from `technical/` directory

5. **Process guide** in `PRINTING_PROCESS_GUIDE.md` explains algorithms documented in `technical/`

---

## Quick Start Checklist

**Documentation for Common Tasks:**

✅ **Setting up system first time:**  
→ `PRE_PRINT_SETUP_GUIDE.md`

✅ **Running first print:**  
→ `PRINTING_PROCESS_GUIDE.md` § Quick Start

✅ **Analyzing print data:**  
→ `../post-processing/README.md` § Workflow

✅ **Troubleshooting print issues:**  
→ `PRINTING_PROCESS_GUIDE.md` § Troubleshooting

✅ **Updating system software:**  
→ `DEPLOYMENT_GUIDE.md`

✅ **Understanding adhesion metrics:**  
→ `UNDERGRADUATE_TEAM_GUIDE.md` § Force Measurement

✅ **Calibrating hardware:**  
→ `PRE_PRINT_SETUP_GUIDE.md` § Calibration Procedures

✅ **Designing experiments:**  
→ `UNDERGRADUATE_TEAM_GUIDE.md` § Running Experiments

---

## Cross-References

### Related Documentation

**Code Documentation:**
- `../README_COMPREHENSIVE.md` - Project overview
- `../support_modules/README.md` - Module details
- `../post-processing/README.md` - Analysis pipeline
- `../ui_components/README.md` - UI components

**External Resources:**
- Zaber Motion Library docs
- Phidgets API documentation
- OpenCV documentation
- Tkinter reference

### Quick Links

**Most Referenced Sections:**

- **Phase Labels** → `PRINTING_PROCESS_GUIDE.md` § Phase Detection
- **Motion Profiles** → `PRINTING_PROCESS_GUIDE.md` § 2-Stage Smooth Motion
- **Data Formats** → `../post-processing/README.md` § Output Files
- **Calibration** → `PRE_PRINT_SETUP_GUIDE.md` § Calibration Procedures
- **Troubleshooting** → Any guide § Troubleshooting section

---

## Document Standards

### Structure Guidelines

**All guides should include:**
```markdown
# Document Title

[Brief description of purpose and audience]

## Table of Contents
[Links to major sections]

## Section 1
[Content with subsections]

---

**Last Updated:** [Date]
**Guide Version:** [Version number]
**Software Version:** [Applicable software version]
```

### Writing Style

**User Guides:** Active voice, clear step-by-step instructions, friendly tone  
**Technical Docs:** Precise terminology, complete specs, professional tone  
**Process Docs:** Explanatory style, conceptual diagrams, educational tone

---

## Glossary of Common Terms

**Abbreviations:**
- **DLP** - Digital Light Processing
- **FEP** - Fluorinated Ethylene Propylene (resin tank film)
- **CSV** - Comma-Separated Values (data file format)
- **GUI** - Graphical User Interface

**Technical Terms:**
- **Adhesion** - Attractive force between cured layer and FEP film
- **Peeling** - Separation process during lifting
- **Baseline** - Force gauge reading with no adhesion forces
- **Decimation** - Reducing data rate by systematic sampling
- **Phase** - Operational state during printing (Exposure, Lift, etc.)
- **Work of Adhesion** - Energy required to separate surfaces

**See also:** `UNDERGRADUATE_TEAM_GUIDE.md` § Terminology

---

## Document Maintenance

### Updating Documentation

**When to update:**
- After system changes
- When users report confusion
- After troubleshooting new issues
- When adding new features

**How to update:**
1. Identify affected documents
2. Update all related sections
3. Add version/date stamps
4. Test procedures if changed
5. Notify users of changes

**Critical:** When updating code, update corresponding documentation simultaneously.

---

## Feedback and Contributions

### Improving Documentation

**Found an error?**
- Note the document name and section
- Describe the issue
- Suggest correction
- Email: evanjones2026@u.northwestern.edu

**Something unclear?**
- Document what confused you
- Describe what you expected to find
- Suggest improvements

---

## Contact

**Documentation Questions:** Evan Jones (evanjones2026@u.northwestern.edu)  
**Technical Questions:** Boyuan Sun (boyuansun2026@u.northwestern.edu)  
**General Inquiries:** Professor Cheng Sun

---

**Last Updated:** February 2, 2026  
**Document Count:** 8+ active guides  
**Coverage:** Setup, Operation, Analysis, Troubleshooting, Development
1. Start with `PROJECT_UPDATE_HYBRID_SYSTEM.md` for the latest system status
2. Refer to `WORK_OF_ADHESION_METRICS_DEFINITIONS.md` for scientific methodology
3. Check `UNIFIED_CALCULATOR_IMPLEMENTATION.md` for implementation details
4. Use `LAYER_BOUNDARY_DETECTION.md` for understanding data processing
5. Review `HYBRID_SYSTEM_SUCCESS_REPORT.md` for complete project context