# Prince
Repository for The Printer Formerly Known as Prince

## Overview
This repository contains the control software for a lab-grade 3D-printer system. The printer integrates multiple hardware components controlled through Python to enable precise additive manufacturing.

## Hardware Components

### DLP9000 (Texas Instruments)
- **Manufacturer**: DLi (Digital Light Innovations)
- **Description**: Digital Light Processing projector system based on the Texas Instruments DLP9000 chipset
- **Purpose**: Provides high-resolution light projection for stereolithography-based 3D printing

### Zaber Linear Stage
- **Manufacturer**: Zaber Technologies
- **Description**: Precision linear motion stage
- **Purpose**: Controls the vertical (Z-axis) movement of the build platform during the printing process

### Phidgets Force Gauge
- **Manufacturer**: Phidgets Inc.
- **Description**: Force/load sensor for real-time force measurement
- **Purpose**: Monitors force applied during the printing process for quality control and feedback

## Software

### Python Control System
The printer is controlled using Python, which interfaces with all hardware components to orchestrate the printing process. The control system manages:
- Light projection patterns from the DLP9000
- Vertical stage positioning via the Zaber linear stage
- Force monitoring through the Phidgets force gauge
- Print job execution and coordination
