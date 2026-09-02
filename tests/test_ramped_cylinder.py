# -*- coding: utf-8 -*-
"""
Unit Tests for Ramped Cylinder generation backend math and file creation.
"""

import unittest
import os
import shutil
import tempfile
import numpy as np
from support_modules.image_modification.ramped_cylinder import generate_ramped_cylinder_workflow


class TestRampedCylinder(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_speed_ramped_cylinder_generation(self):
        # Parameters
        diameter_um = 2000.0
        start_val = 10.0
        end_val = 50.0
        layer_height = 5.0
        points = 5
        replicates = 3
        led_current = 120.0
        step_speed = 800.0
        overstep = 400.0
        acceleration = 6.0
        pause = 0.5
        sandwich_speed = 600.0

        # Execute workflow
        folder_path, warnings = generate_ramped_cylinder_workflow(
            output_base_folder=self.test_dir,
            diameter_um=diameter_um,
            start_val=start_val,
            end_val=end_val,
            layer_height=layer_height,
            points=points,
            replicates=replicates,
            led_current=led_current,
            step_speed=step_speed,
            overstep=overstep,
            acceleration=acceleration,
            pause=pause,
            sandwich_speed=sandwich_speed,
            ramp_mode="speed"
        )

        # 1. Verify folder exists
        self.assertTrue(os.path.isdir(folder_path))
        folder_name = os.path.basename(folder_path)
        self.assertIn("RampedCylinder", folder_name)
        self.assertNotIn("Power", folder_name)

        # 2. Verify total images generated (1 base layer + points * replicates = 16)
        total_expected_layers = 1 + points * replicates
        for i in range(1, total_expected_layers + 1):
            img_path = os.path.join(folder_path, f"{i}.png")
            self.assertTrue(os.path.isfile(img_path))

        # 3. Verify instruction file exists
        txt_name = f"{folder_name}.txt"
        txt_path = os.path.join(folder_path, txt_name)
        self.assertTrue(os.path.isfile(txt_path))

        # 4. Verify instruction file content
        with open(txt_path, "r") as f:
            lines = f.readlines()
        
        # Verify header columns
        header = lines[0].strip().split("\t")
        expected_header = [
            "Layer", "File", "Thickness", "Time", "Intensity", 
            "Step Speed", "Overstep Distance", "Acceleration", "Pause", "Sandwich Speed"
        ]
        self.assertEqual(header, expected_header)

        # Verify row count
        self.assertEqual(len(lines) - 1, total_expected_layers)

        # Verify Base Layer (Layer 1)
        base_cols = lines[1].strip().split("\t")
        self.assertEqual(base_cols[0], "1")
        self.assertEqual(base_cols[1], "1.png")
        self.assertAlmostEqual(float(base_cols[3]), 2.0, places=5)  # Default exposure_time_val
        self.assertEqual(base_cols[4], "120")  # led_current

        # Verify values for ramped layers (Layers 2..16)
        expected_speeds = [10.0]*3 + [20.0]*3 + [30.0]*3 + [40.0]*3 + [50.0]*3
        
        for idx in range(2, total_expected_layers + 1):
            cols = lines[idx].strip().split("\t")
            self.assertEqual(cols[0], str(idx))
            self.assertEqual(cols[1], f"{idx}.png")
            self.assertEqual(cols[2], "5")  # thickness
            
            # check computed time: Thickness / Speed
            expected_speed = expected_speeds[idx - 2]
            expected_time = layer_height / expected_speed
            self.assertAlmostEqual(float(cols[3]), expected_time, places=5)
            
            self.assertEqual(cols[4], "120")  # led_current (intensity)
            self.assertEqual(cols[5], "800")
            self.assertEqual(cols[6], "400")
            self.assertEqual(cols[7], "6")
            self.assertEqual(cols[8], "0.5")
            self.assertEqual(cols[9], "600")

    def test_power_ramped_cylinder_generation(self):
        # Parameters
        diameter_um = 2000.0
        start_val = 100.0
        end_val = 50.0
        layer_height = 5.0
        points = 5
        replicates = 3
        led_current = 1.0 # Should be ignored in power ramp
        step_speed = 800.0
        overstep = 400.0
        acceleration = 6.0
        pause = 0.5
        sandwich_speed = 600.0
        ramp_mode = "power"
        exposure_time_val = 2.5

        # Execute workflow
        folder_path, warnings = generate_ramped_cylinder_workflow(
            output_base_folder=self.test_dir,
            diameter_um=diameter_um,
            start_val=start_val,
            end_val=end_val,
            layer_height=layer_height,
            points=points,
            replicates=replicates,
            led_current=led_current,
            step_speed=step_speed,
            overstep=overstep,
            acceleration=acceleration,
            pause=pause,
            sandwich_speed=sandwich_speed,
            ramp_mode=ramp_mode,
            exposure_time_val=exposure_time_val,
        )

        # 1. Verify folder exists
        self.assertTrue(os.path.isdir(folder_path))
        folder_name = os.path.basename(folder_path)
        self.assertIn("PowerRampedCylinder", folder_name)

        # 2. Verify total images generated (1 base layer + points * replicates = 16)
        total_expected_layers = 1 + points * replicates
        for i in range(1, total_expected_layers + 1):
            img_path = os.path.join(folder_path, f"{i}.png")
            self.assertTrue(os.path.isfile(img_path))

        # 3. Verify instruction file exists
        txt_name = f"{folder_name}.txt"
        txt_path = os.path.join(folder_path, txt_name)
        self.assertTrue(os.path.isfile(txt_path))

        # 4. Verify instruction file content
        with open(txt_path, "r") as f:
            lines = f.readlines()
        
        # Verify row count
        self.assertEqual(len(lines) - 1, total_expected_layers)

        # Verify Base Layer (Layer 1)
        base_cols = lines[1].strip().split("\t")
        self.assertEqual(base_cols[0], "1")
        self.assertEqual(base_cols[1], "1.png")
        self.assertAlmostEqual(float(base_cols[3]), exposure_time_val, places=5)
        self.assertEqual(base_cols[4], "100")  # start_val intensity for power mode base layer

        # Verify values for ramped layers (Layers 2..16)
        expected_powers = [100]*3 + [88]*3 + [75]*3 + [62]*3 + [50]*3
        
        for idx in range(2, total_expected_layers + 1):
            cols = lines[idx].strip().split("\t")
            self.assertEqual(cols[0], str(idx))
            self.assertEqual(cols[1], f"{idx}.png")
            self.assertEqual(cols[2], "5")  # thickness
            
            # Exposure time should be constant
            self.assertAlmostEqual(float(cols[3]), exposure_time_val, places=5)
            
            # Intensity should ramp
            expected_power = expected_powers[idx - 2]
            self.assertEqual(int(cols[4]), expected_power)
            self.assertEqual(cols[5], "800")
            self.assertEqual(cols[6], "400")
            self.assertEqual(cols[7], "6")
            self.assertEqual(cols[8], "0.5")
            self.assertEqual(cols[9], "600")

    def test_validation_invalid_diameter(self):
        # Validation error for negative/zero diameter or diameter too large
        with self.assertRaises(ValueError):
            generate_ramped_cylinder_workflow(
                output_base_folder=self.test_dir,
                diameter_um=-100.0,
                start_val=10.0,
                end_val=50.0,
                layer_height=5.0,
                points=5,
                replicates=3,
                led_current=120.0,
                step_speed=1000.0,
                overstep=500.0,
                acceleration=5.0,
                pause=0.0,
                sandwich_speed=500.0,
            )

    def test_validation_invalid_power_range(self):
        # Validation error for power out of range in power mode
        with self.assertRaises(ValueError):
            generate_ramped_cylinder_workflow(
                output_base_folder=self.test_dir,
                diameter_um=2000.0,
                start_val=256.0, # out of 1-255 range
                end_val=50.0,
                layer_height=5.0,
                points=5,
                replicates=3,
                led_current=1.0,
                step_speed=1000.0,
                overstep=500.0,
                acceleration=5.0,
                pause=0.0,
                sandwich_speed=500.0,
                ramp_mode="power",
                exposure_time_val=2.5,
            )

    def test_dosage_coupled_ramped_cylinder_generation(self):
        # Parameters
        diameter_um = 2000.0
        start_val = 10.0
        end_val = 50.0
        layer_height = 5.0
        points = 5
        replicates = 1
        control_speed = 20.0
        control_power = 100.0

        # Execute workflow
        folder_path, warnings = generate_ramped_cylinder_workflow(
            output_base_folder=self.test_dir,
            diameter_um=diameter_um,
            start_val=start_val,
            end_val=end_val,
            layer_height=layer_height,
            points=points,
            replicates=replicates,
            led_current=1.0,
            step_speed=800.0,
            overstep=400.0,
            acceleration=6.0,
            pause=0.5,
            sandwich_speed=600.0,
            ramp_mode="dosage_coupled",
            control_speed=control_speed,
            control_power=control_power,
        )

        self.assertTrue(os.path.isdir(folder_path))
        self.assertIn("DosageCoupledCylinder", os.path.basename(folder_path))

    def test_cone_ramped_generation(self):
        # Parameters
        diameter_um = 1000.0
        ending_diameter_um = 3000.0
        base_diameter_um = 1000.0
        start_val = 10.0
        end_val = 50.0
        layer_height = 5.0
        points = 5
        replicates = 1
        led_current = 100.0

        folder_path, warnings = generate_ramped_cylinder_workflow(
            output_base_folder=self.test_dir,
            diameter_um=diameter_um,
            ending_diameter_um=ending_diameter_um,
            base_diameter_um=base_diameter_um,
            start_val=start_val,
            end_val=end_val,
            layer_height=layer_height,
            points=points,
            replicates=replicates,
            led_current=led_current,
            step_speed=800.0,
            overstep=400.0,
            acceleration=6.0,
            pause=0.5,
            sandwich_speed=600.0,
            ramp_mode="speed",
        )

        self.assertTrue(os.path.isdir(folder_path))
        self.assertIn("RampedCone", os.path.basename(folder_path))

        # Check total images generated (1 base layer + 5 ramped layers = 6)
        for i in range(1, 7):
            self.assertTrue(os.path.isfile(os.path.join(folder_path, f"{i}.png")))

    def test_gui_validation_with_empty_grayed_out_boxes(self):
        """Verify that GUI generation succeeds when grayed-out inputs are left empty."""
        import tkinter as tk
        from unittest.mock import patch
        from support_modules.image_modification.ramped_cylinder import RampedCylinderWindow

        root = tk.Tk()
        root.withdraw()
        gui = RampedCylinderWindow(root)
        gui.var_output_base.set(self.test_dir)

        # 1. Test Cone Constant mode with empty ending speed & empty dosage anchor
        gui.var_workflow_mode.set("cone_constant")
        gui.var_diameter.set("1000.0")
        gui.var_ending_diameter.set("2000.0")
        gui.var_start_val.set("15.0")
        gui.var_end_val.set("")             # Grayed out: MUST NOT throw error
        gui.var_control_speed.set("")       # Grayed out: MUST NOT throw error
        gui.var_control_power.set("")       # Grayed out: MUST NOT throw error
        gui.var_points.set("5")
        gui.var_replicates.set("1")

        with patch("tkinter.messagebox.showinfo"):
            gui._on_generate()

        # 2. Test Parameter Ramp (Cylinder) mode with empty ending diameter
        gui.var_workflow_mode.set("cylinder_ramp")
        gui.var_ramp_mode.set("speed")
        gui.var_diameter.set("2000.0")
        gui.var_ending_diameter.set("")     # Grayed out: MUST NOT throw error
        gui.var_start_val.set("10.0")
        gui.var_end_val.set("50.0")
        gui.var_control_speed.set("")       # Grayed out: MUST NOT throw error
        gui.var_control_power.set("")       # Grayed out: MUST NOT throw error
        gui.var_points.set("5")
        gui.var_replicates.set("1")

        with patch("tkinter.messagebox.showinfo"):
            gui._on_generate()

        root.destroy()

    def test_logarithmic_param_spacing(self):
        """Verify that logarithmic parameter spacing generates geometrically spaced speeds."""
        from pathlib import Path
        diameter_um = 2000.0
        start_val = 10.0
        end_val = 1000.0
        layer_height = 5.0
        points = 5
        replicates = 1

        folder_path, warnings = generate_ramped_cylinder_workflow(
            output_base_folder=self.test_dir,
            diameter_um=diameter_um,
            start_val=start_val,
            end_val=end_val,
            layer_height=layer_height,
            points=points,
            replicates=replicates,
            led_current=100.0,
            step_speed=800.0,
            overstep=400.0,
            acceleration=6.0,
            pause=0.5,
            sandwich_speed=600.0,
            ramp_mode="speed",
            param_spacing="log",
        )

        self.assertTrue(os.path.isdir(folder_path))
        self.assertIn("LogRampedCylinder", os.path.basename(folder_path))

        # Check instruction file
        txt_files = list(Path(folder_path).glob("*.txt"))
        self.assertEqual(len(txt_files), 1)

        expected_speeds = np.geomspace(start_val, end_val, points)
        with open(txt_files[0], "r", encoding="utf-8") as f:
            lines = [line.strip().split("\t") for line in f.readlines()]

        # Line 0: Header
        # Line 1: Base layer (Layer 1)
        # Line 2..6: Ramped layers
        for idx, exp_spd in enumerate(expected_speeds, start=2):
            layer_num = int(lines[idx][0])
            self.assertEqual(layer_num, idx)
            time_val = float(lines[idx][3])
            expected_time = layer_height / exp_spd
            self.assertAlmostEqual(time_val, expected_time, places=4)

    def test_logarithmic_diameter_spacing(self):
        """Verify that logarithmic diameter spacing generates geometrically spaced cone slices."""
        diameter_um = 1000.0
        ending_diameter_um = 5000.0
        start_val = 20.0
        layer_height = 5.0
        points = 4
        replicates = 1

        folder_path, warnings = generate_ramped_cylinder_workflow(
            output_base_folder=self.test_dir,
            diameter_um=diameter_um,
            ending_diameter_um=ending_diameter_um,
            start_val=start_val,
            end_val=start_val,
            layer_height=layer_height,
            points=points,
            replicates=replicates,
            led_current=100.0,
            step_speed=800.0,
            overstep=400.0,
            acceleration=6.0,
            pause=0.5,
            sandwich_speed=600.0,
            ramp_mode="speed",
            diameter_spacing="log",
        )

        self.assertTrue(os.path.isdir(folder_path))
        self.assertIn("RampedLogCone", os.path.basename(folder_path))

        expected_diameters = np.geomspace(diameter_um, ending_diameter_um, points)
        # Verify generated PNGs
        for i in range(1, points + 2): # 1 base + 4 ramped = 5
            self.assertTrue(os.path.isfile(os.path.join(folder_path, f"{i}.png")))


if __name__ == "__main__":
    unittest.main()



