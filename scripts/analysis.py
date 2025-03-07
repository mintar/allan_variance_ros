#!/usr/bin/env python3

# 
# @file   analysis.py
# @brief  Plotting and analysis tool to determine IMU parameters.
# @author Russell Buchanan
# 

import os
import csv
import argparse
import numpy as np
from scipy.spatial.transform import Rotation
from numpy.linalg import inv
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

def line_func(x, m, b):
  return m * x + b

def get_intercept(x, y, m, b):
	
	logx = np.log(x)
	logy = np.log(y)
	coeffs, _ = curve_fit(line_func, logx, logy, bounds=([m, -np.inf], [m + 0.001, np.inf]))
	poly = np.poly1d(coeffs)
	yfit = lambda x: np.exp(poly(np.log(x)))

	return yfit(b), yfit



if __name__ == "__main__":

	parser = argparse.ArgumentParser()

	parser.add_argument('--data', metavar='STR', type=str,
                    help='TUM data files to plot')

	parser.add_argument("--skip", type=int, default=1)

	args = parser.parse_args()

	line_count = 0

	rostopic = "/sensors/imu"
	update_rate = 400.0



	# Assumes tum format

	period = np.array([])
	acceleration = np.empty((0,3), float)
	rotation_rate = np.empty((0,3), float)

	with open(args.data) as input_file:
		csv_reader = csv.reader(input_file, delimiter=' ')

		first_row = True
		counter = 0

		for row in csv_reader:
			# if(first_row):
			# 	first_row = False
			# 	continue

			counter = counter + 1

			if (counter % args.skip != 0):
				continue

			t = float(row[0])
			period = np.append(period, [t], axis=0) 
			acceleration = np.append(acceleration, np.array([float(row[1]), float(row[2]), float(row[3])]).reshape(1,3), axis=0)
			rotation_rate = np.append(rotation_rate, np.array([float(row[4]), float(row[5]), float(row[6])]).reshape(1,3), axis=0)


white_noise_break_point = np.where(period == 10)[0][0]
random_rate_break_point = np.where(period == 10)[0][0]


accel_wn_intercept_x, xfit_wn = get_intercept(period[0:white_noise_break_point], acceleration[0:white_noise_break_point,0], -0.5, 1.0)
accel_wn_intercept_y, yfit_wn = get_intercept(period[0:white_noise_break_point], acceleration[0:white_noise_break_point,1], -0.5, 1.0)
accel_wn_intercept_z, zfit_wn = get_intercept(period[0:white_noise_break_point], acceleration[0:white_noise_break_point,2], -0.5, 1.0)

accel_rr_intercept_x, xfit_rr = get_intercept(period, acceleration[:,0], 0.5, 3.0)
accel_rr_intercept_y, yfit_rr = get_intercept(period, acceleration[:,1], 0.5, 3.0)
accel_rr_intercept_z, zfit_rr = get_intercept(period, acceleration[:,2], 0.5, 3.0)


accel_min_x = np.amin(acceleration[:,0])
accel_min_y = np.amin(acceleration[:,1])
accel_min_z = np.amin(acceleration[:,2])

accel_min_x_index = np.argmin(acceleration[:,0])
accel_min_y_index = np.argmin(acceleration[:,1])
accel_min_z_index = np.argmin(acceleration[:,2])

yaml_file = open("imu.yaml", "w")

print("ACCELEROMETER:")
print(f"X Velocity Random Walk: {accel_wn_intercept_x: .5f} m/s/sqrt(s) {accel_wn_intercept_x*60: .5f} m/s/sqrt(hr)")
print(f"Y Velocity Random Walk: {accel_wn_intercept_y: .5f} m/s/sqrt(s) {accel_wn_intercept_y*60: .5f} m/s/sqrt(hr)")
print(f"Z Velocity Random Walk: {accel_wn_intercept_z: .5f} m/s/sqrt(s) {accel_wn_intercept_z*60: .5f} m/s/sqrt(hr)")

print(f"X Bias Instability: {accel_min_x: .5f} m/s^2 {accel_min_x*60*60: .5f} m/hr^2")
print(f"Y Bias Instability: {accel_min_y: .5f} m/s^2 {accel_min_y*60*60: .5f} m/hr^2")
print(f"Z Bias Instability: {accel_min_z: .5f} m/s^2 {accel_min_z*60*60: .5f} m/hr^2")

print(f"X Accel Random Walk: {accel_rr_intercept_x: .5f} m/s^2")
print(f"Y Accel Random Walk: {accel_rr_intercept_y: .5f} m/s^2")
print(f"Z Accel Random Walk: {accel_rr_intercept_z: .5f} m/s^2")

average_vrw = (accel_wn_intercept_x + accel_wn_intercept_y + accel_wn_intercept_z) / 3
average_abi = (accel_rr_intercept_x + accel_rr_intercept_y + accel_rr_intercept_z) / 3

yaml_file.write("#Accelerometer\n")
yaml_file.write("accelerometer_noise_density: " + repr(average_vrw) + " \n")
yaml_file.write("accelerometer_random_walk: " + repr(average_abi) + " \n")
yaml_file.write("\n")


dpi = 90
figsize = (16, 9)
fig1 = plt.figure(num="Acceleration", dpi=dpi, figsize=figsize)

plt.loglog(period, acceleration[:,0], "r--" , label='X')
plt.loglog(period, acceleration[:,1], "g--" , label='Y')
plt.loglog(period, acceleration[:,2], "b--" , label='Z')

plt.loglog(period, xfit_wn(period), "m-")
plt.loglog(period, yfit_wn(period), "m-")
plt.loglog(period, zfit_wn(period), "m-", label="White noise fit line")

plt.loglog(period, xfit_rr(period), "y-",)
plt.loglog(period, yfit_rr(period), "y-",)
plt.loglog(period, zfit_rr(period), "y-", label="Random Rate fit line")

plt.loglog(1.0, accel_wn_intercept_x, "ro", markersize=20)
plt.loglog(1.0, accel_wn_intercept_y, "go", markersize=20)
plt.loglog(1.0, accel_wn_intercept_z, "bo", markersize=20)

plt.loglog(3.0, accel_rr_intercept_x, "r*", markersize=20)
plt.loglog(3.0, accel_rr_intercept_y, "g*", markersize=20)
plt.loglog(3.0, accel_rr_intercept_z, "b*", markersize=20)

plt.loglog(period[accel_min_x_index], accel_min_x, "r^", markersize=20)
plt.loglog(period[accel_min_y_index], accel_min_y, "g^", markersize=20)
plt.loglog(period[accel_min_z_index], accel_min_z, "b^", markersize=20)

plt.title("Accelerometer", fontsize=30)
plt.ylabel("Allan Deviation m/s^2", fontsize=30)
plt.legend(fontsize=25)
plt.grid(True)
plt.xlabel("Period (s)", fontsize=30)
plt.tight_layout()

plt.draw()
plt.pause(1)
w = plt.waitforbuttonpress(timeout=5)
plt.close()

fig1.savefig('acceleration.png', dpi=600, bbox_inches = "tight") 

gyro_wn_intercept_x, xfit_wn = get_intercept(period[0:white_noise_break_point], rotation_rate[0:white_noise_break_point,0], -0.5, 1.0)
gyro_wn_intercept_y, yfit_wn = get_intercept(period[0:white_noise_break_point], rotation_rate[0:white_noise_break_point,1], -0.5, 1.0)
gyro_wn_intercept_z, zfit_wn = get_intercept(period[0:white_noise_break_point], rotation_rate[0:white_noise_break_point,2], -0.5, 1.0)

gyro_rr_intercept_x, xfit_rr = get_intercept(period, rotation_rate[:,0], 0.5, 3.0)
gyro_rr_intercept_y, yfit_rr = get_intercept(period, rotation_rate[:,1], 0.5, 3.0)
gyro_rr_intercept_z, zfit_rr = get_intercept(period, rotation_rate[:,2], 0.5, 3.0)

gyro_min_x = np.amin(rotation_rate[:,0])
gyro_min_y = np.amin(rotation_rate[:,1])
gyro_min_z = np.amin(rotation_rate[:,2])

gyro_min_x_index = np.argmin(rotation_rate[:,0])
gyro_min_y_index = np.argmin(rotation_rate[:,1])
gyro_min_z_index = np.argmin(rotation_rate[:,2])

print("GYROSCOPE:")
print(f"X Angle Random Walk: {gyro_wn_intercept_x: .5f} deg/sqrt(s) {gyro_wn_intercept_x * 60: .5f} deg/sqrt(hr)")
print(f"Y Angle Random Walk: {gyro_wn_intercept_y: .5f} deg/sqrt(s) {gyro_wn_intercept_y * 60: .5f} deg/sqrt(hr)")
print(f"Z Angle Random Walk: {gyro_wn_intercept_z: .5f} deg/sqrt(s) {gyro_wn_intercept_z * 60: .5f} deg/sqrt(hr)")

print(f"X Bias Instability: {gyro_min_x: .5f} deg/s {gyro_min_x*60*60: .5f} deg/hr")
print(f"Y Bias Instability: {gyro_min_y: .5f} deg/s	{gyro_min_y*60*60: .5f} deg/hr")
print(f"Z Bias Instability: {gyro_min_z: .5f} deg/s	{gyro_min_z*60*60: .5f} deg/hr")

print(f"X Rate Random Walk: {gyro_rr_intercept_x: .5f} deg/s")
print(f"Y Rate Random Walk: {gyro_rr_intercept_y: .5f} deg/s")
print(f"Z Rate Random Walk: {gyro_rr_intercept_z: .5f} deg/s")

average_arw = (gyro_wn_intercept_x + gyro_wn_intercept_y + gyro_wn_intercept_z) / 3
average_abi = (gyro_rr_intercept_x + gyro_rr_intercept_y + gyro_rr_intercept_z) / 3

yaml_file.write("#Gyroscope\n")
yaml_file.write("gyroscope_noise_density: " + repr(average_arw * np.pi / 180) + " \n")
yaml_file.write("gyroscope_random_walk: " + repr(average_abi * np.pi / 180) + " \n")
yaml_file.write("\n")

yaml_file.write("rostopic: " + repr(rostopic) + " #Make sure this is correct\n")
yaml_file.write("update_rate: " + repr(update_rate) + " #Make sure this is correct\n")
yaml_file.write("\n")
yaml_file.close()


fig2 = plt.figure(num="Gyro", dpi=dpi, figsize=figsize)

plt.loglog(period, rotation_rate[:,0], "r-" , label='X')
plt.loglog(period, rotation_rate[:,1], "g-" , label='Y')
plt.loglog(period, rotation_rate[:,2], "b-" , label='Z')

plt.loglog(period, xfit_wn(period), "m-")
plt.loglog(period, yfit_wn(period), "m-")
plt.loglog(period, zfit_wn(period), "m-", label="White noise fit line")

plt.loglog(period, xfit_rr(period), "y-")
plt.loglog(period, yfit_rr(period), "y-")
plt.loglog(period, zfit_rr(period), "y-", label="Random rate fit line")

plt.loglog(1.0, gyro_wn_intercept_x, "ro", markersize=20)
plt.loglog(1.0, gyro_wn_intercept_y, "go", markersize=20)
plt.loglog(1.0, gyro_wn_intercept_z, "bo", markersize=20)

plt.loglog(3.0, gyro_rr_intercept_x, "r*", markersize=20)
plt.loglog(3.0, gyro_rr_intercept_y, "g*", markersize=20)
plt.loglog(3.0, gyro_rr_intercept_z, "b*", markersize=20)

plt.loglog(period[gyro_min_x_index], gyro_min_x, "r^", markersize=20)
plt.loglog(period[gyro_min_y_index], gyro_min_y, "g^", markersize=20)
plt.loglog(period[gyro_min_z_index], gyro_min_z, "b^", markersize=20)
plt.title("Gyroscope", fontsize=30)

plt.ylabel("Allan Deviation deg/s", fontsize=30)
plt.legend(fontsize=25)
plt.grid(True)
plt.xlabel("Period (s)", fontsize=30)
plt.tight_layout()

plt.draw()
plt.pause(1)
w = plt.waitforbuttonpress(timeout=5)
plt.close()

fig2.savefig('gyro.png', dpi=600, bbox_inches = "tight") 

print("Writing Kalibr imu.yaml file.")
print("Make sure to update rostopic and rate.")
