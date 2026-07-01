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
        folder_path = generate_ramped_cylinder_workflow(
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

        # 2. Verify total images generated (points * replicates = 15)
        total_expected_layers = points * replicates
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

        # Verify values for layers
        # speeds should go from 10 to 50 linearly with 5 points: [10, 20, 30, 40, 50]
        # Repeated 3 times: [10, 10, 10, 20, 20, 20, 30, 30, 30, 40, 40, 40, 50, 50, 50]
        expected_speeds = [10.0]*3 + [20.0]*3 + [30.0]*3 + [40.0]*3 + [50.0]*3
        
        for idx in range(1, total_expected_layers + 1):
            cols = lines[idx].strip().split("\t")
            self.assertEqual(cols[0], str(idx))
            self.assertEqual(cols[1], f"{idx}.png")
            self.assertEqual(cols[2], "5")  # thickness
            
            # check computed time: Thickness / Speed (which represents continuous print speed)
            expected_speed = expected_speeds[idx - 1]
            expected_time = layer_height / expected_speed
            self.assertAlmostEqual(float(cols[3]), expected_time, places=5)
            
            self.assertEqual(cols[4], "120")  # led_current (intensity)
            
            # Step Speed is left constant as the default value (800) instead of ramping
            self.assertEqual(cols[5], "800")
            
            self.assertEqual(cols[6], "400")  # overstep
            self.assertEqual(cols[7], "6")  # acceleration
            self.assertEqual(cols[8], "0.5")  # pause
            self.assertEqual(cols[9], "600")  # sandwich_speed

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
        folder_path = generate_ramped_cylinder_workflow(
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

        # 2. Verify total images generated (points * replicates = 15)
        total_expected_layers = points * replicates
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

        # Verify values for layers
        # powers should go from 100 to 50 linearly with 5 points: [100, 87.5, 75, 62.5, 50]
        # Rounded to integers (with banker's round-to-even for 62.5 -> 62 and 87.5 -> 88): [100, 88, 75, 62, 50]
        # Repeated 3 times
        expected_powers = [100]*3 + [88]*3 + [75]*3 + [62]*3 + [50]*3
        
        for idx in range(1, total_expected_layers + 1):
            cols = lines[idx].strip().split("\t")
            self.assertEqual(cols[0], str(idx))
            self.assertEqual(cols[1], f"{idx}.png")
            self.assertEqual(cols[2], "5")  # thickness
            
            # Exposure time should be constant
            self.assertAlmostEqual(float(cols[3]), exposure_time_val, places=5)
            
            # Intensity should ramp
            expected_power = expected_powers[idx - 1]
            self.assertEqual(int(cols[4]), expected_power)
            
            # Step Speed is left constant as the default value (800) instead of ramping
            self.assertEqual(cols[5], "800")
            
            self.assertEqual(cols[6], "400")  # overstep
            self.assertEqual(cols[7], "6")  # acceleration
            self.assertEqual(cols[8], "0.5")  # pause
            self.assertEqual(cols[9], "600")  # sandwich_speed

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


if __name__ == "__main__":
    unittest.main()
