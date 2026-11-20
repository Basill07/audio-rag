# Station 3 – Automated Screwdriving Cell (SDC-300)
## Operator and Maintenance Manual

> Sample document for the Audio RAG demo. The machine, the company and all values are fictional.

Manufacturer: Example Automation GmbH
Model: SDC-300
Line position: Station 3 of the battery module assembly line
Manual version: 2.1

---

## 1. Overview

The SDC-300 is an automated screwdriving cell. It fastens 12 M5 screws on each battery module housing. A six-axis robot carries the electric screwdriver. A vision camera checks the screw position before and after each fastening step. The cycle time is 38 seconds per module.

Main components:
- Six-axis robot with screwdriver spindle (EC-Spindle 50)
- Screw feeder with vibration bowl and feed hose
- Vision camera (VC-12) above the work area
- Part fixture with two clamping cylinders
- Safety light curtain at the loading opening
- Operator touch panel (HMI) on the right side of the cell

## 2. Technical data

| Parameter | Value |
|---|---|
| Screw size | M5 x 12 |
| Target torque | 4.5 Nm |
| Torque tolerance | ± 0.3 Nm |
| Final angle window | 180° to 360° |
| Cycle time | 38 s per module |
| Compressed air | 6 bar (minimum 5.5 bar) |
| Power supply | 400 V, 3-phase, 16 A |
| Feeder capacity | 2,000 screws |

## 3. Safety

- Never reach into the cell while the robot is in automatic mode.
- The light curtain stops the robot when it is interrupted. Do not bridge or disable it.
- Before any maintenance inside the cell, switch the main switch to OFF and lock it with your personal padlock (lockout/tagout).
- Wear safety glasses when you clean the screw feeder with compressed air.
- The emergency stop buttons are on the HMI and at the loading opening.

## 4. Operation

### 4.1 Starting the cell
1. Check that the compressed air shows at least 5.5 bar on the pressure gauge.
2. Turn the main switch to ON.
3. Wait until the HMI shows "Ready" (about 60 seconds).
4. Press "Reference" so the robot moves to its home position.
5. Load a module into the fixture and press the two-hand start buttons.

### 4.2 Shutting down
1. Finish the current cycle. Press "Cycle stop" and wait until the robot is in its home position.
2. Remove the last module from the fixture.
3. Turn the main switch to OFF.

### 4.3 Changing the screw type
Only trained setup personnel may change the screw type. Load the matching program on the HMI under Menu > Programs, change the feeder bowl insert and run one test module.

## 5. Error codes

When an error occurs, the cell stops and the HMI shows the error code in red. After fixing the cause, press "Acknowledge" on the HMI and then "Reference".

### E12 – Low compressed air
Cause: The air pressure is below 5.5 bar.
Solution: Check the main air valve and the hose connection at the back of the cell. Check the pressure gauge. If the pressure stays low, inform maintenance.

### E23 – Light curtain interrupted
Cause: Something interrupted the light curtain during automatic mode.
Solution: Remove the object from the loading opening. Press "Acknowledge". If the error comes back without a reason, clean the light curtain lenses with a dry cloth.

### E31 – Clamping cylinder not in position
Cause: The part fixture did not close fully, usually because the module is not seated correctly.
Solution: Open the fixture with the HMI button "Clamp open", place the module correctly against both stops and start again.

### E47 – Screw feeder jam
Cause: A screw is stuck in the feed hose or at the outlet of the vibration bowl. This is the most common error on Station 3. It often happens when screws of the wrong length are in the feeder.
Solution:
1. Press "Cycle stop" and wait for the robot to reach its home position.
2. Switch the main switch to OFF and lock it (lockout/tagout).
3. Open the feeder cover on the left side of the cell.
4. Remove the stuck screw at the bowl outlet. If no screw is visible there, disconnect the feed hose at the screwdriver end and push the screw out with the cleaning rod (in the tool holder on the cell door). Do not use compressed air to blow it out.
5. Check the feeder for screws of the wrong length and remove them.
6. Close the cover, switch on the cell, press "Acknowledge" and then "Reference".
If E47 appears more than three times in one shift, inform maintenance to check the feed hose for wear.

### E52 – Torque out of tolerance
Cause: The final torque was not between 4.2 and 4.8 Nm. Possible reasons are a damaged thread, a worn bit or a wrong screw.
Solution: The module is marked as "NOK" and must be moved to the rework box. Check the screwdriver bit for wear. If E52 appears on three modules in a row, replace the bit (see section 6.2).

### E60 – Vision check failed
Cause: The camera did not find the screw in the expected position.
Solution: Clean the camera lens with a lens cloth. Check that the work area light is on. If the error continues, recalibrate the camera under Menu > Vision > Calibrate.

## 6. Maintenance

### 6.1 Maintenance schedule

| Interval | Task |
|---|---|
| Every shift | Clean the work area and empty the rework box |
| Daily | Check the compressed air pressure and the light curtain function |
| Weekly | Clean the camera lens and the screw feeder bowl |
| Every 50,000 cycles | Replace the screwdriver bit |
| Every 6 months | Replace the feed hose and lubricate the robot axes |
| Every 12 months | Torque calibration of the spindle by the service team |

### 6.2 Replacing the screwdriver bit
1. Move the robot to the service position (Menu > Service > Bit change).
2. Switch the main switch to OFF and lock it.
3. Pull the quick-release sleeve on the spindle and remove the old bit.
4. Insert the new bit (part number BIT-T25-70) until it clicks.
5. Switch the cell on and reset the bit counter under Menu > Service > Counters.

## 7. Spare parts

| Part | Part number |
|---|---|
| Screwdriver bit T25, 70 mm | BIT-T25-70 |
| Feed hose, 3 m | HOSE-F5-3000 |
| Camera lens cover | VC12-LC |
| Light curtain cleaning kit | LC-CLEAN-01 |

## 8. Contacts

- Line maintenance: extension 4710
- Service hotline Example Automation GmbH: +49 000 0000000 (fictional)
