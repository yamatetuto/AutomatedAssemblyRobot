# *********************************************************************#
# File Name : motion_control.py
# Explanation : Motion controller
# Project Name : Table Robot
# ----------------------------------------------------------------------
# History :
#           ver0.0.1 2024.5.17 New Create
# *********************************************************************#

# - Define import/from -------------------------------------------------
# - Define import/from -------------------------------------------------
import time
import ctypes
from ctypes import *
import numpy as np
import threading
from threading import Thread
from enum import Enum
import ctypes as ctype
import re
import pdb
import RPi.GPIO as GPIO
import splebo_n

# - Define import/from io_expander  ------------------------------------
import smbus
# import threading
# import time


# - Variable -----------------------------------------------------------
eCsms_lib = ctype.cdll.LoadLibrary("./libcsms_splebo_n.so")

write_order_motion_ctrl_count = 0
read_order_motion_ctrl_count = 0
rdy_open_motion_contoller = False
is_init_success = False


# - Class --------------------------------------------------------------
class motion_control_class:
    motion_api_thread = None
    lock = threading.Lock()

    def __init__(self):
        global write_order_motion_ctrl_count
        global read_order_motion_ctrl_count
        global rdy_open_motion_contoller
        global is_init_success
        #
        # print ("motion_ctrl.__init__()")
        #
        write_order_motion_ctrl_count = 0
        read_order_motion_ctrl_count = 0
        rdy_open_motion_contoller = False
        is_init_success = False
        #
        self.__init__sub()

    def initialize_motion_contoller(self):
        global rdy_open_motion_contoller
        global is_init_success
        #
        # print ("motion_ctrl.initialize_motion_contoller()")
        #
        is_init_success = False

        # Include io_expander() ----------------------------------------
        # smbus.SMBus()
        # self.initialize_io_expander()
        # --------------------------------------------------------------

        # モーションボードの電源ON
        # self.write_bit(1, (128-116), True)
        #
        # RESET前に ＝＝＞ 供給電源を OFF/On を追加
        GPIO.output(splebo_n.gpio_class.kNova_Power_pin, True)
        time.sleep(0.1)
        # GPIO.output(splebo_n.gpio_class.kNova_Power_pin, False)
        # time.sleep(0.1)
        #
        # GPIO.output(splebo_n.gpio_class.kNova_reset_pin, True)
        # time.sleep(0.001)
        GPIO.output(splebo_n.gpio_class.kNova_reset_pin, False)
        time.sleep(0.1)
        # time.sleep(0.001)
        # GPIO.output(splebo_n.gpio_class.kNova_reset_pin, True)

        self.motion_api_thread = Thread(target=self.motion_control_loop)
        self.motion_api_thread.start()
        time.sleep(1)

        if (rdy_open_motion_contoller is False):
            # Api Module Open
            print("OPN")
            cmdData = splebo_n.motion_controller_cmd_class.kOpen
            order_id = self.set_write_command(cmdData)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OPEN MOTION CTRL")
                return False
            else:
                rdy_open_motion_contoller = True

        # Select Axis Set Function & Homing Singnal OFF
        for i in range(0, splebo_n.axis_type_class.axis_count):
            splebo_n.set_order_motion_ctrl_class.axis = i

            if splebo_n.axis_set_class[i].motor_type != \
                    splebo_n.axis_maker_Class.kNone:
                if splebo_n.axis_set_class[i].motor_type == \
                        splebo_n.axis_maker_Class.kIAI:
                    splebo_n.set_order_motion_ctrl_class.wr1 = 0
                    splebo_n.set_order_motion_ctrl_class.wr2 = 0xA384

                    if splebo_n.axis_set_class[i].in_position == 0:
                        splebo_n.set_order_motion_ctrl_class.wr2 = \
                            splebo_n.set_order_motion_ctrl_class.wr2 & 0xFF7F

                    splebo_n.set_order_motion_ctrl_class.wr3 = 0x0B40
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kSetMode)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        #
                        print("ERR SET MODE" + ":" + str(i))
                        return False
                    #
                    splebo_n.set_order_motion_ctrl_class.p1m = 0x4055
                    splebo_n.set_order_motion_ctrl_class.p2m = 0
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kSetIOSignal)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET IO SIGNAL" + ":" + str(i))
                        return False
                    #
                    splebo_n.set_order_motion_ctrl_class.flm = 0
                    order_id = self.set_write_command(
                            splebo_n.motion_controller_cmd_class.
                            kSetInputSignalFilter)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET INPUT SIGNAL FILTER" + ":" + str(i))
                        return False

                    splebo_n.axis_func_class[i].func_home_move_start = \
                        self.homing_move_start_IAI
                    splebo_n.axis_func_class[i].func_home_move_check = \
                        self.homing_move_check_IAI
                    splebo_n.axis_func_class[i].func_nova_home_move_start = \
                        self.nova_homing_move_start_IAI
                    splebo_n.axis_func_class[i].func_nova_home_move_check = \
                        self.nova_homing_move_check_IAI
                    splebo_n.axis_func_class[i].func_origin_sensor_check = \
                        self.origin_sensor_check_IAI
                    splebo_n.axis_func_class[i].func_offset_move_start = \
                        self.homing_offset_move_start
                    splebo_n.axis_func_class[i].func_offset_move_check = \
                        self.move_inpos_check
                    splebo_n.axis_func_class[i].func_parameter_start = \
                        self.homing_parameter_set
                    splebo_n.axis_func_class[i].func_servo_on_off = \
                        self.servo_on_off_IAI
                    splebo_n.axis_func_class[i].func_reset_actuator = \
                        self.clear_on_off_IAI
                    splebo_n.axis_func_class[i].func_homing_on_off = \
                        self.homing_on_off_IAI

                elif splebo_n.axis_set_class[i].motor_type == \
                        splebo_n.axis_maker_Class.kStepping:
                    splebo_n.set_order_motion_ctrl_class.wr1 = 0
                    splebo_n.set_order_motion_ctrl_class.wr2 = 0xA384

                    if splebo_n.axis_set_class[i].in_position == 0:
                        splebo_n.set_order_motion_ctrl_class.wr2 = \
                            splebo_n.set_order_motion_ctrl_class.wr2 & 0xFF7F

                    splebo_n.set_order_motion_ctrl_class.wr3 = 0x0F90
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kSetMode)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET MODE" + ":" + str(i))
                        return False
                    #
                    splebo_n.set_order_motion_ctrl_class.p1m = 0x4055
                    splebo_n.set_order_motion_ctrl_class.p2m = 0
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kSetIOSignal)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET IO SIGNAL" + ":" + str(i))
                        return False

                    splebo_n.set_order_motion_ctrl_class.flm = 0
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.
                        kSetInputSignalFilter)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET INPUT SIGNAL FILTER" + ":" + str(i))
                        return False

                    splebo_n.axis_func_class[i].func_home_move_start = \
                        self.homing_move_start_STEP
                    splebo_n.axis_func_class[i].func_home_move_check = \
                        self.homing_move_check_STEP
                    splebo_n.axis_func_class[i].func_nova_home_move_start = \
                        self.nova_homing_move_start_STEP
                    splebo_n.axis_func_class[i].func_nova_home_move_check = \
                        self.nova_homing_move_check_STEP
                    splebo_n.axis_func_class[i].func_origin_sensor_check = \
                        self.origin_sensor_check_STEP
                    splebo_n.axis_func_class[i].func_offset_move_start = \
                        self.homing_offset_move_start
                    splebo_n.axis_func_class[i].func_offset_move_check = \
                        self.move_inpos_check
                    splebo_n.axis_func_class[i].func_parameter_start = \
                        self.homing_parameter_set
                    splebo_n.axis_func_class[i].func_servo_on_off = \
                        self.servo_on_off_STEP
                    splebo_n.axis_func_class[i].func_reset_actuator = \
                        self.clear_on_off_STEP
                    splebo_n.axis_func_class[i].func_homing_on_off = \
                        self.homing_on_off_STEP
                #
                elif splebo_n.axis_set_class[i].motor_type == \
                        splebo_n.axis_maker_Class.kaSTEP:
                    splebo_n.set_order_motion_ctrl_class.wr1 = 0
                    splebo_n.set_order_motion_ctrl_class.wr2 = 0xA384
                    #
                    if splebo_n.axis_set_class[i].in_position == 0:
                        splebo_n.set_order_motion_ctrl_class.wr2 = \
                            splebo_n.set_order_motion_ctrl_class.wr2 & 0xFF7F

                    splebo_n.set_order_motion_ctrl_class.wr3 = 0x0F90
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kSetMode)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET MODE" + ":" + str(i))
                        return False
                    #
                    splebo_n.set_order_motion_ctrl_class.p1m = 0x4055
                    splebo_n.set_order_motion_ctrl_class.p2m = 0
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kSetIOSignal)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET IO SIGNAL" + ":" + str(i))
                        return False
                    #
                    splebo_n.set_order_motion_ctrl_class.flm = 0
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.
                        kSetInputSignalFilter)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR SET INPUT SIGNAL FILTER" + ":" + str(i))
                        return False

                    splebo_n.axis_func_class[i].func_home_move_start = \
                        self.homing_move_start_aSTEP
                    splebo_n.axis_func_class[i].func_home_move_check = \
                        self.homing_move_check_aSTEP
                    splebo_n.axis_func_class[i].func_nova_home_move_start = \
                        self.nova_homing_move_start_aSTEP
                    splebo_n.axis_func_class[i].func_nova_home_move_check = \
                        self.nova_homing_move_check_aSTEP
                    splebo_n.axis_func_class[i].func_origin_sensor_check = \
                        self.origin_sensor_check_aSTEP
                    splebo_n.axis_func_class[i].func_offset_move_start = \
                        self.homing_offset_move_start
                    splebo_n.axis_func_class[i].func_offset_move_check = \
                        self.move_inpos_check
                    splebo_n.axis_func_class[i].func_parameter_start = \
                        self.homing_parameter_set
                    splebo_n.axis_func_class[i].func_servo_on_off = \
                        self.servo_on_off_aSTEP
                    splebo_n.axis_func_class[i].func_reset_actuator = \
                        self.clear_on_off_aSTEP
                    splebo_n.axis_func_class[i].func_homing_on_off = \
                        self.homing_on_off_aSTEP

                splebo_n.axis_func_class[i].func_homing_on_off(i, False)
                splebo_n.axis_func_class[i].func_servo_on_off(i, False)

        # Select Axis Parameter Set
        for i in range(0, splebo_n.axis_type_class.axis_count):
            splebo_n.axis_sts_class[i].is_homing_err = False

            if splebo_n.axis_set_class[i].motor_type != \
                    splebo_n.axis_maker_Class.kNone:
                splebo_n.set_order_motion_ctrl_class.axis = i

                splebo_n.set_order_motion_ctrl_class.dv = \
                    splebo_n.axis_set_class[i].max_speed
                order_id = self.set_write_command(
                    splebo_n.motion_controller_cmd_class.kSetDriveSpeed)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR SET DRIVE" + ":" + str(i))
                    return False

                splebo_n.set_order_motion_ctrl_class.sv = int(
                    splebo_n.axis_set_class[i].start_speed /
                    float(splebo_n.axis_set_class[i].pulse_length))
                order_id = self.set_write_command(
                    splebo_n.motion_controller_cmd_class.kSetInitialVelocity)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR SET InitialVelocity" + ":" + str(i))
                    return False

                splebo_n.set_order_motion_ctrl_class.ac = \
                    splebo_n.axis_set_class[i].max_accel
                order_id = self.set_write_command(
                    splebo_n.motion_controller_cmd_class.kSetAcceleration)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR SET Acceleration" + ":" + str(i))
                    return False

                splebo_n.set_order_motion_ctrl_class.dc = \
                    splebo_n.axis_set_class[i].max_decel
                order_id = self.set_write_command(
                    splebo_n.motion_controller_cmd_class.kSetDeceleration)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR SET Deceleration" + ":" + str(i))
                    return False

                splebo_n.set_order_motion_ctrl_class.tp = 0
                order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kSetLogicalCoord)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR SET Logical Coord" + ":" + str(i))
                    return False

                splebo_n.set_order_motion_ctrl_class.tp = 0
                order_id = self.set_write_command(
                    splebo_n.motion_controller_cmd_class.kSetRelativeCoord)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR SET Relative Coord" + ":" + str(i))
                    return False
                #
                splebo_n.set_order_motion_ctrl_class.slm = \
                    self.convert_axis_mm_to_pulse(i,
                                                  splebo_n.axis_set_class[i].
                                                  limit_minus)
                splebo_n.set_order_motion_ctrl_class.slp = \
                    self.convert_axis_mm_to_pulse(i,
                                                  splebo_n.axis_set_class[i].
                                                  limit_plus)
                order_id = self.set_write_command(
                    splebo_n.motion_controller_cmd_class.kSetSoftLimit)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR SET Software Limit" + ":" + str(i))
                    return False

        # Select Axis ALARM Reset and Servo ON
        for i in range(0, splebo_n.axis_type_class.axis_count):
            if splebo_n.axis_set_class[i].motor_type != \
                    splebo_n.axis_maker_Class.kNone:
                splebo_n.set_order_motion_ctrl_class.axis = i

                # All Axis Io OFF
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT0, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT1, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT2, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT3, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT4, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT5, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT6, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kOUT7, False)
                self.write_axis_io(i, splebo_n.axis_io_no_class.kDCC_OUT,
                                   False)

                splebo_n.axis_func_class[i].func_reset_actuator(i, True)
                time.sleep(0.1)
                splebo_n.axis_func_class[i].func_reset_actuator(i, False)
                time.sleep(0.1)
                splebo_n.axis_func_class[i].func_servo_on_off(i, True)
                time.sleep(1)

        is_init_success = True

        # Include io_expander() ----------------------------------------
        self.initialize_io_expander()
        # --------------------------------------------------------------
        #
        return True

    def stop_motion_thread(self):
        splebo_n.program_end_flag = True
        self.motion_api_thread.join()

    def get_init_success_state(self):
        global is_init_success
        return is_init_success

    def motion_control_loop(self):
        global read_order_motion_ctrl_count

        while True:
            if splebo_n.program_end_flag:
                break

            # ------------------------------------------------------------
            # try:
            #     self.io_thread_1action()
            # except OSError:
            #     pass  # パネル通信エラーが出ても無視して次へ進む
            # ------------------------------------------------------------

            if splebo_n.order_motion_ctrl_class[
                    read_order_motion_ctrl_count].isSet is True:
                splebo_n.order_motion_ctrl_class[
                    read_order_motion_ctrl_count].isSet = False

                ret = False

                if splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kOpen:
                    ret = self.cmd_board_open()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetMode:
                    ret = self.cmd_set_mode(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.wr1,
                        splebo_n.set_order_motion_ctrl_class.wr2,
                        splebo_n.set_order_motion_ctrl_class.wr3, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetDriveSpeed:
                    ret = self.cmd_set_drive_speed(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.dv, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kSetInitialVelocity:
                    ret = self.cmd_set_initial_velocity(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.sv, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetAcceleration:
                    ret = self.cmd_set_acceleration(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.ac, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetDeceleration:
                    ret = self.cmd_set_deceleration(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.dc, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetRetOriginMode:
                    ret = self.cmd_set_ret_origin_mode(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.h1m,
                        splebo_n.set_order_motion_ctrl_class.h2m, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetIOSignal:
                    ret = self.cmd_set_io_signal(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.p1m,
                        splebo_n.set_order_motion_ctrl_class.p2m, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kSetInputSignalFilter:
                    ret = self.cmd_set_input_signal_filter(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.flm, False)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kAutoOrigin:
                    ret = self.cmd_auto_origin(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.hv,
                        splebo_n.set_order_motion_ctrl_class.dv)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetSoftLimit:
                    ret = self.cmd_set_soft_limit(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.slm,
                        splebo_n.set_order_motion_ctrl_class.slp)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kMoveRelative:
                    ret = self.cmd_move_relative(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.tp,
                        splebo_n.set_order_motion_ctrl_class.dv,
                        splebo_n.set_order_motion_ctrl_class.isAbs)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kMoveAbsolute:
                    ret = self.cmd_move_absolute()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kMoveJOG:
                    ret = self.cmd_move_jog(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.isCcw,
                        splebo_n.set_order_motion_ctrl_class.dv)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kStop:
                    ret = self.cmd_stop(
                        splebo_n.set_order_motion_ctrl_class.axis)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kDecelerationStop:
                    ret = self.cmd_deceleration_stop(
                        splebo_n.set_order_motion_ctrl_class.axis)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kLineInterpolation:
                    ret = self.cmd_line_interpolation()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kCircleInterpolation:
                    ret = self.cmd_circle_interpolation()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kContinueInterpolation:
                    ret = self.cmd_continue_interpolation()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetLogicalCoord:
                    ret = self.cmd_get_logicalCoord(
                        splebo_n.set_order_motion_ctrl_class.axis)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetRelativeCoord:
                    ret = self.cmd_get_relativeCoord(
                        splebo_n.set_order_motion_ctrl_class.axis)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kSetLogicalCoord:
                    ret = self.cmd_set_logicalCoord(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.tp)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kSetRelativeCoord:
                    ret = self.cmd_set_relativeCoord(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.tp)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetGeneralIO:
                    ret = self.cmd_get_generalIO(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.pio)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kSetGeneralOutput:
                    ret = self.cmd_set_general_output()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kSetGeneralOutputBit:
                    ret = self.cmd_set_general_output_bit(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.bit,
                        splebo_n.set_order_motion_ctrl_class.on_off)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetAxisStatus:
                    ret = self.cmd_get_axis_status(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.sts_no)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kWriteRegister:
                    ret = self.cmd_write_register(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.reg_no,
                        splebo_n.set_order_motion_ctrl_class.data)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kReadRegister:
                    ret = self.cmd_read_register(
                        splebo_n.set_order_motion_ctrl_class.axis,
                        splebo_n.set_order_motion_ctrl_class.reg_no)
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kWriteRegister6_7:
                    ret = self.cmd_write_register6_7()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kReadRegister6_7:
                    ret = self.cmd_read_register6_7()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetNowDriveSpeed:
                    ret = self.cmd_get_now_drive_speed()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetNowAccDec:
                    ret = self.cmd_get_now_acc_dec()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetMultiRegister:
                    ret = self.cmd_get_multi_register()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetTimer:
                    ret = self.cmd_get_timer()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetMaxPointInterpolation:
                    ret = self.cmd_get_max_point_interpolation()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetHelicalRotationNum:
                    ret = self.cmd_get_helical_rotation_num()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetHelicalCalcValue:
                    ret = self.cmd_get_helical_calc_value()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetWR1_2_3:
                    ret = self.cmd_get_wr1_2_3()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetPI0Mode:
                    ret = self.cmd_get_PI0_mode()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetMultiRegisterMode:
                    ret = self.cmd_get_multi_register_mode()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetAcceleration:
                    ret = self.cmd_get_acceleration()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetInitialVelocity:
                    ret = self.cmd_get_initial_velocity()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetDriveSpeed:
                    ret = self.cmd_get_drive_speed()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetEndPoint:
                    ret = self.cmd_get_end_point()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetSplitPulse1:
                    ret = self.cmd_get_split_pulse1()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetGeneralInput:
                    ret = self.cmd_get_general_input()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetEndCoordinate:
                    ret = self.cmd_get_end_coordinate()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kGetArcCenterCoordinate:
                    ret = self.cmd_get_arc_center_coordinate()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kSetManualDec:
                    ret = self.cmd_set_manual_dec()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.\
                        kSetInterpolationMode:
                    ret = self.cmd_set_interpolation_mode()
                elif splebo_n.order_motion_ctrl_class[
                        read_order_motion_ctrl_count].cmd == \
                        splebo_n.motion_controller_cmd_class.kGetApi:
                    ret = self.cmd_get_api()

                splebo_n.order_motion_ctrl_class[
                    read_order_motion_ctrl_count].isFuncSuccess = ret
                splebo_n.order_motion_ctrl_class[
                    read_order_motion_ctrl_count].isRead = True
                read_order_motion_ctrl_count = read_order_motion_ctrl_count + 1

                if read_order_motion_ctrl_count >= \
                        splebo_n.kMaxOrderMotionCtrlBuffSize:
                    read_order_motion_ctrl_count = 0

            time.sleep(0.01)

    def set_write_command(self, cmd):
        global write_order_motion_ctrl_count

        with self.lock:
            if write_order_motion_ctrl_count >= \
                    splebo_n.kMaxOrderMotionCtrlBuffSize:
                write_order_motion_ctrl_count = 0

            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                cmd = cmd
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                axis = splebo_n.set_order_motion_ctrl_class.axis
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                wr1 = splebo_n.set_order_motion_ctrl_class.wr1
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                wr2 = splebo_n.set_order_motion_ctrl_class.wr2
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                wr3 = splebo_n.set_order_motion_ctrl_class.wr3
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                dv = splebo_n.set_order_motion_ctrl_class.dv
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                sv = splebo_n.set_order_motion_ctrl_class.sv
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                ac = splebo_n.set_order_motion_ctrl_class.ac
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                dc = splebo_n.set_order_motion_ctrl_class.dc
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                h1m = splebo_n.set_order_motion_ctrl_class.h1m
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                h2m = splebo_n.set_order_motion_ctrl_class.h2m
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                p1m = splebo_n.set_order_motion_ctrl_class.p1m
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                p2m = splebo_n.set_order_motion_ctrl_class.p2m
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                flm = splebo_n.set_order_motion_ctrl_class.flm
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                hv = splebo_n.set_order_motion_ctrl_class.hv
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                slm = splebo_n.set_order_motion_ctrl_class.slm
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                slp = splebo_n.set_order_motion_ctrl_class.slp
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                tp = splebo_n.set_order_motion_ctrl_class.tp
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                isAbs = splebo_n.set_order_motion_ctrl_class.isAbs
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                isCcw = splebo_n.set_order_motion_ctrl_class.isCcw
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                sts_no = splebo_n.set_order_motion_ctrl_class.sts_no
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                reg_no = splebo_n.set_order_motion_ctrl_class.reg_no
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                data = splebo_n.set_order_motion_ctrl_class.data
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                bit = splebo_n.set_order_motion_ctrl_class.bit
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                on_off = splebo_n.set_order_motion_ctrl_class.on_off
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                mrNo = splebo_n.set_order_motion_ctrl_class.mrNo
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                wrNo = splebo_n.set_order_motion_ctrl_class.wrNo
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                isSet = True
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                isRead = False
            splebo_n.order_motion_ctrl_class[write_order_motion_ctrl_count].\
                isFuncSuccess = False

            write_order_motion_ctrl_count = write_order_motion_ctrl_count + 1

        return write_order_motion_ctrl_count - 1

    def read_order_motion_ctrl(self, order_id):
        return splebo_n.order_motion_ctrl_class[order_id].isRead, \
                splebo_n.order_motion_ctrl_class[order_id].readData

    def wait_write_order_motion_ctrl(self, order_id):
        global read_order_motion_ctrl_count

        while (True):
            if splebo_n.order_motion_ctrl_class[order_id].isRead:
                break

    def get_axis_coord(self, axis):
        if not self.get_init_success_state():
            return

        if splebo_n.axis_set_class[axis].motor_type != \
                splebo_n.axis_maker_Class.kNone:
            splebo_n.set_order_motion_ctrl_class.axis = axis
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kGetLogicalCoord)

            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR GET Logical Coord")
            else:
                try:
                    abs_coord = int(splebo_n.
                                    order_motion_ctrl_class[order_id].readData)
                    abs_coord = round(abs_coord * splebo_n.axis_set_class[
                            axis].pulse_length, 2)
                    splebo_n.axis_sts_class[axis].abs_coord = abs_coord
                except Exception:
                    return

    def convert_axis_speed_mm_to_pulse(self, axis, speed, speed_gear):
        speed = int(speed * (speed_gear / 100))
        return int(speed / float(splebo_n.axis_set_class[axis].pulse_length))

    def convert_axis_mm_to_pulse(self, axis, target_coord):
        coord = target_coord * 100
        speed_gear = float(splebo_n.axis_set_class[axis].pulse_length) * 100
        coord = int(coord / speed_gear)
        return coord

    def convert_axis_speed_per_to_speed(self, axis, speed_per):
        if (float(speed_per) <= 1.0):
            speed_per = 1.0
        elif (100.0 <= float(speed_per)):
            speed_per = 100.0
        speed = int(splebo_n.axis_set_class[axis].max_speed *
                    (float(speed_per) / 100.0))
        return int(speed / float(splebo_n.axis_set_class[axis].pulse_length))

    def order_move_axis(self, move_type, is_ccw):
        if move_type == splebo_n.axis_move_type_class.kRelative:
            for i in range(0, splebo_n.axis_type_class.axis_count):
                if splebo_n.order_move_motion_ctrl_class[i].is_move:
                    splebo_n.set_order_motion_ctrl_class.axis = i
                    splebo_n.set_order_motion_ctrl_class.tp = \
                        splebo_n.order_move_motion_ctrl_class[i].target_coord
                    splebo_n.set_order_motion_ctrl_class.dv = \
                        splebo_n.order_move_motion_ctrl_class[i].speed
                    splebo_n.set_order_motion_ctrl_class.is_abs = False
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kMoveRelative)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR RELATIVE MOVE")

        elif move_type == splebo_n.axis_move_type_class.kAbsolute:
            print("A")

        elif move_type == splebo_n.axis_move_type_class.kJog:
            for i in range(0, splebo_n.axis_type_class.axis_count):
                if splebo_n.order_move_motion_ctrl_class[i].is_move:
                    splebo_n.set_order_motion_ctrl_class.axis = i
                    splebo_n.set_order_motion_ctrl_class.dv = \
                        splebo_n.order_move_motion_ctrl_class[i].speed
                    splebo_n.set_order_motion_ctrl_class.isCcw = is_ccw
                    order_id = self.set_write_command(
                        splebo_n.motion_controller_cmd_class.kMoveJOG)
                    self.wait_write_order_motion_ctrl(order_id)
                    if not splebo_n.order_motion_ctrl_class[order_id].\
                            isFuncSuccess:
                        print("ERR JOG MOVE")
        else:
            print("ERR ORDER MOVE TYPE")

    def order_homing(self):
        is_init_target = False
        is_end_homing = True
        for i in range(0, len(splebo_n.homing_class.home_turn_list)):
            for k in range(1, len(splebo_n.homing_class.home_turn_list[i])):
                if not len(splebo_n.homing_class.home_turn_list[i]) == 1:
                    if splebo_n.homing_class.home_turn == \
                            splebo_n.homing_class.home_turn_list[i][0]:
                        if not splebo_n.homing_class.home_is_end_list[
                                splebo_n.homing_class.home_turn_list[i][k]]:
                            self.order_homing_sequence(
                                splebo_n.homing_class.home_turn_list[i][k])
                            is_end_homing = False
                        is_init_target = True

        if (not is_init_target) or (is_end_homing):
            splebo_n.homing_class.home_turn = \
                splebo_n.homing_class.home_turn + 1

        is_all_axis_homing_end = True
        for i in range(0, splebo_n.axis_type_class.axis_count):
            if not splebo_n.homing_class.home_is_end_list[i]:
                is_all_axis_homing_end = False
                break

        if is_all_axis_homing_end:
            print("HOMING_ALL_END")

        return is_all_axis_homing_end

    def order_homing_sequence(self, axis):
        self.read_axis_io(axis)

        if splebo_n.axis_sts_class[axis].is_io_alarm or \
                splebo_n.axis_sts_class[axis].is_io_emergency:
            # Axis Error
            splebo_n.homing_class.home_is_end_list[axis] = True
            return

        # print("ORGN:" + str(axis))
        if splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kHomeMoveStart:
            splebo_n.axis_func_class[axis].func_home_move_start(axis)
            splebo_n.homing_class.home_seq[axis] = \
                splebo_n.homing_class.home_seq[axis] + 1
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kHomeMoveCheck:
            if splebo_n.axis_func_class[axis].func_home_move_check(axis):
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.home_seq[axis] + 1
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kNovaHomeMoveStart:
            if splebo_n.axis_set_class[axis].origin_sensor == \
                    splebo_n.on_off_auto_class.kAUTO:
                if splebo_n.axis_func_class[axis].\
                        func_nova_home_move_start(axis):
                    splebo_n.homing_class.home_seq[axis] = \
                        splebo_n.homing_class.home_seq[axis] + 1
            else:
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.kOriginSensorCheck
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kNovaHomeMoveCheck:
            if splebo_n.axis_func_class[axis].func_nova_home_move_check(axis):
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.home_seq[axis] + 1
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kOriginSensorCheck:
            if splebo_n.axis_set_class[axis].origin_sensor == \
                    splebo_n.on_off_auto_class.kON:
                if splebo_n.axis_func_class[axis].\
                        func_origin_sensor_check(axis):
                    splebo_n.homing_class.home_seq[axis] = \
                        splebo_n.homing_class.home_seq[axis] + 1
            else:
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.home_seq[axis] + 1
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kOffsetMoveStart:
            if not float(splebo_n.axis_set_class[axis].origin_offset) == 0:
                splebo_n.axis_func_class[axis].func_offset_move_start(axis)
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.home_seq[axis] + 1
            else:
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.kParameterSet
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kOffsetMoveCheck:
            if splebo_n.axis_func_class[axis].func_offset_move_check(axis):
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.home_seq[axis] + 1
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kParameterSet:
            if splebo_n.axis_func_class[axis].func_parameter_start(axis):
                splebo_n.homing_class.home_seq[axis] = \
                    splebo_n.homing_class.home_seq[axis] + 1
        elif splebo_n.homing_class.home_seq[axis] == \
                splebo_n.homing_class.kEnd:
            splebo_n.homing_class.home_is_end_list[axis] = True
            splebo_n.axis_sts_class[axis].is_io_home = True
        else:
            splebo_n.homing_class.home_is_end_list[axis] = True

    def write_axis_io(self, axis, io_no, on_off):
        if io_no == splebo_n.axis_io_no_class.kOUT0:
            splebo_n.axis_sts_class[axis].is_io_out0 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 0
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT0")
        elif io_no == splebo_n.axis_io_no_class.kOUT1:
            splebo_n.axis_sts_class[axis].is_io_out1 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 1
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT1")
        elif io_no == splebo_n.axis_io_no_class.kOUT2:
            splebo_n.axis_sts_class[axis].is_io_out2 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 2
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT2")
        elif io_no == splebo_n.axis_io_no_class.kOUT3:
            splebo_n.axis_sts_class[axis].is_io_out3 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 3
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT3")
        elif io_no == splebo_n.axis_io_no_class.kOUT4:
            splebo_n.axis_sts_class[axis].is_io_out4 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 4
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT4")
        elif io_no == splebo_n.axis_io_no_class.kOUT5:
            splebo_n.axis_sts_class[axis].is_io_out5 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 5
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT5")
        elif io_no == splebo_n.axis_io_no_class.kOUT6:
            splebo_n.axis_sts_class[axis].is_io_out6 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 6
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT6")
        elif io_no == splebo_n.axis_io_no_class.kOUT7:
            splebo_n.axis_sts_class[axis].is_io_out7 = on_off

            splebo_n.set_order_motion_ctrl_class.axis = axis
            splebo_n.set_order_motion_ctrl_class.bit = 7
            splebo_n.set_order_motion_ctrl_class.on_off = on_off
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kSetGeneralOutputBit)
            self.wait_write_order_motion_ctrl(order_id)
            if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
                print("ERR OUT7")
        elif io_no == splebo_n.axis_io_no_class.kDCC_OUT:
            splebo_n.axis_sts_class[axis].is_io_dcc_out = on_off

    def read_axis_io(self, axis):
        drive_bit = False
        err_bit = False
        alarm_bit = False
        emg_bit = False
        emg_btn_push = False

        # Read Emergency Button --------------------
        emg_btn_push = GPIO.input(splebo_n.gpio_class.kEmergencyBtn)

        # Read Register RR0 --------------------
        read_reg0_data = self.read_register(axis, splebo_n.NOVA_Class.kRR0)
        if not read_reg0_data == "":
            read_reg0_data = int(read_reg0_data)
            if (axis == splebo_n.axis_type_class.axis_X) or \
                    (axis == splebo_n.axis_type_class.axis_S1):
                drive_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_XDRV)
                err_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_XERR)
            elif (axis == splebo_n.axis_type_class.axis_Y) or \
                    (axis == splebo_n.axis_type_class.axis_S2):
                drive_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_YDRV)
                err_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_YERR)
            elif (axis == splebo_n.axis_type_class.axis_Z) or \
                    (axis == splebo_n.axis_type_class.axis_A):
                drive_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_ZDRV)
                err_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_ZERR)
            else:
                drive_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_UDRV)
                err_bit = splebo_n.bit_check(
                    read_reg0_data, splebo_n.NOVA_Class.kRR0_UERR)

        # Read Register RR1 --------------------
        read_reg1_data = self.read_register(axis, splebo_n.NOVA_Class.kRR1)
        if not read_reg1_data == "":
            read_reg1_data = int(read_reg1_data)

        # Read Register RR2 --------------------
        read_reg2_data = self.read_register(axis, splebo_n.NOVA_Class.kRR2)
        if not read_reg2_data == "":
            read_reg2_data = int(read_reg2_data)
            alarm_bit = splebo_n.bit_check(
                read_reg2_data, splebo_n.NOVA_Class.kRR2_ALM)
            emg_bit = splebo_n.bit_check(
                read_reg2_data, splebo_n.NOVA_Class.kRR2_EMG)

        # Read Register RR3 --------------------
        read_reg3_data = self.read_register(axis, splebo_n.NOVA_Class.kRR3)
        if not read_reg3_data == "":
            reg3_0 = 0x0000FFFF & int(read_reg3_data)
            # reg3_1 = (0xFFFF0000 & int(read_reg3_data)) >> 16

            splebo_n.axis_sts_class[axis].is_io_origin_sensor = \
                splebo_n.bit_check(reg3_0, splebo_n.NOVA_Class.kRR3_STOP1)

        if (axis == splebo_n.axis_type_class.axis_X) or \
           (axis == splebo_n.axis_type_class.axis_Y) or \
           (axis == splebo_n.axis_type_class.axis_S1) or \
           (axis == splebo_n.axis_type_class.axis_S2):
            # Read Register RR4 --------------------
            read_reg4_data = self.read_register(axis, splebo_n.NOVA_Class.kRR4)
            if not read_reg4_data == "":
                read_reg4_data = int(read_reg4_data)

                if (axis == splebo_n.axis_type_class.axis_X) or \
                   (axis == splebo_n.axis_type_class.axis_S1):
                    splebo_n.axis_sts_class[axis].is_io_in0 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_XPIO0)
                    splebo_n.axis_sts_class[axis].is_io_in1 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_XPIO1)
                    splebo_n.axis_sts_class[axis].is_io_in2 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_XPIO2)
                    splebo_n.axis_sts_class[axis].is_io_in3 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_XPIO3)
                else:
                    splebo_n.axis_sts_class[axis].is_io_in0 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_YPIO0)
                    splebo_n.axis_sts_class[axis].is_io_in1 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_YPIO1)
                    splebo_n.axis_sts_class[axis].is_io_in2 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_YPIO2)
                    splebo_n.axis_sts_class[axis].is_io_in3 = \
                        splebo_n.bit_check(
                            read_reg4_data, splebo_n.NOVA_Class.kRR4_YPIO3)
        else:
            # Read Register RR5--------------------
            read_reg5_data = self.read_register(axis, splebo_n.NOVA_Class.kRR5)
            if not read_reg5_data == "":
                read_reg5_data = int(read_reg5_data)
                print(format(read_reg5_data, 'x'))
                if (axis == splebo_n.axis_type_class.axis_Z) or \
                   (axis == splebo_n.axis_type_class.axis_A):
                    splebo_n.axis_sts_class[axis].is_io_in0 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_ZPIO0)
                    splebo_n.axis_sts_class[axis].is_io_in1 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_ZPIO1)
                    splebo_n.axis_sts_class[axis].is_io_in2 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_ZPIO2)
                    splebo_n.axis_sts_class[axis].is_io_in3 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_ZPIO3)
                else:
                    splebo_n.axis_sts_class[axis].is_io_in0 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_UPIO0)
                    splebo_n.axis_sts_class[axis].is_io_in1 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_UPIO1)
                    splebo_n.axis_sts_class[axis].is_io_in2 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_UPIO2)
                    splebo_n.axis_sts_class[axis].is_io_in3 = \
                        splebo_n.bit_check(
                            read_reg5_data, splebo_n.NOVA_Class.kRR5_UPIO3)

        splebo_n.axis_sts_class[axis].is_io_busy = drive_bit
        splebo_n.axis_sts_class[axis].is_io_alarm = alarm_bit or err_bit
        splebo_n.axis_sts_class[axis].is_io_emergency = emg_bit or emg_btn_push
        splebo_n.axis_sts_class[axis].is_io_ready = \
            (not splebo_n.axis_sts_class[axis].is_io_busy) and \
            (not splebo_n.axis_sts_class[axis].is_io_alarm) and \
            (not splebo_n.axis_sts_class[axis].is_io_emergency)
        #
        # If there is an error or the emergency stop button is pressed,
        #  lower the home flag.
        if splebo_n.axis_sts_class[axis].is_io_alarm or \
                splebo_n.axis_sts_class[axis].is_io_emergency:
            splebo_n.axis_sts_class[axis].is_io_home = False

    def use_axis_error_check(self):
        for i in range(0, splebo_n.axis_type_class.axis_count):
            if splebo_n.axis_set_class[i].motor_type != \
                    splebo_n.axis_maker_Class.kNone:
                if splebo_n.axis_sts_class[i].is_io_emergency or \
                        splebo_n.axis_sts_class[i].is_io_alarm:
                    return True
        #
        return False

    def reset_all_axis(self):
        for i in range(0, splebo_n.axis_type_class.axis_count):
            splebo_n.axis_sts_class[i].is_homing_err = False

            if splebo_n.axis_set_class[i].motor_type != \
                    splebo_n.axis_maker_Class.kNone:
                splebo_n.axis_func_class[i].func_reset_actuator(i, True)
                time.sleep(1)
                splebo_n.axis_func_class[i].func_reset_actuator(i, False)

                clear_cmd = 0x79
                clear_cmd = clear_cmd | 1 << (i + 8)

                print(clear_cmd)

                splebo_n.set_order_motion_ctrl_class.axis = i
                splebo_n.set_order_motion_ctrl_class.reg_no = \
                    splebo_n.NOVA_Class.kWR0
                splebo_n.set_order_motion_ctrl_class.data = clear_cmd
                order_id = self.set_write_command(
                    splebo_n.motion_controller_cmd_class.kWriteRegister)
                self.wait_write_order_motion_ctrl(order_id)
                if not splebo_n.order_motion_ctrl_class[order_id].\
                        isFuncSuccess:
                    print("ERR CLEAR AXIS")

                self.read_axis_io(i)

    def read_register(self, axis, reg_no):
        ret_str = ""

        splebo_n.set_order_motion_ctrl_class.axis = axis

        if (reg_no == splebo_n.NOVA_Class.kRR2) or \
           (reg_no == splebo_n.NOVA_Class.kRR3):
            splebo_n.set_order_motion_ctrl_class.sts_no = reg_no
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kGetAxisStatus)
        else:
            splebo_n.set_order_motion_ctrl_class.reg_no = reg_no
            order_id = self.set_write_command(
                splebo_n.motion_controller_cmd_class.kReadRegister)
        #
        self.wait_write_order_motion_ctrl(order_id)
        if splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            ret_str = splebo_n.order_motion_ctrl_class[order_id].readData
        return ret_str

    # ----------------------------------------#
    # ---------Homing Common Function---------#
    # ----------------------------------------#
    def homing_offset_move_start(self, axis):
        splebo_n.clear_all_order_move_motion_ctrl_class()

        splebo_n.order_move_motion_ctrl_class[axis].is_move = True
        splebo_n.order_move_motion_ctrl_class[axis].speed = \
            int(splebo_n.axis_set_class[axis].offset_speed /
                float(splebo_n.axis_set_class[axis].pulse_length))
        coord = float(splebo_n.axis_set_class[axis].origin_offset) * 100
        speed_gear = float(splebo_n.axis_set_class[axis].pulse_length) * 100
        coord = int(coord / speed_gear)
        splebo_n.order_move_motion_ctrl_class[axis].target_coord = coord

        self.order_move_axis(splebo_n.axis_move_type_class.kRelative, False)

    def homing_parameter_set(self, axis):
        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.dv = \
            splebo_n.axis_set_class[axis].max_speed
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetDriveSpeed)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET DRIVE")

        splebo_n.set_order_motion_ctrl_class.tp = 0
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetLogicalCoord)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET Logical Coord")

        splebo_n.set_order_motion_ctrl_class.tp = 0
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetRelativeCoord)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET Relative Coord")

        splebo_n.set_order_motion_ctrl_class.slm = \
            self.convert_axis_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].limit_minus)
        splebo_n.set_order_motion_ctrl_class.slp = \
            self.convert_axis_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].limit_plus)
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetSoftLimit)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET Software Limit")

        return True

    def all_axis_stop_check(self):
        for i in range(0, splebo_n.axis_type_class.axis_count):
            if splebo_n.axis_set_class[i].motor_type != \
                    splebo_n.axis_maker_Class.kNone:
                if not self.move_inpos_check(i):
                    return False

        return True

    def move_inpos_check(self, axis):
        ret = False

        ret_str = self.read_register(axis, splebo_n.NOVA_Class.kRR0)
        if not ret_str == "":
            if (axis == splebo_n.axis_type_class.axis_X) or \
                    (axis == splebo_n.axis_type_class.axis_S1):
                if (int(ret_str) & splebo_n.NOVA_Class.kRR0_XDRV) == 0:
                    ret = True
            elif (axis == splebo_n.axis_type_class.axis_Y) or \
                    (axis == splebo_n.axis_type_class.axis_S2):
                if (int(ret_str) & splebo_n.NOVA_Class.kRR0_YDRV) == 0:
                    ret = True
            elif (axis == splebo_n.axis_type_class.axis_Z) or \
                    (axis == splebo_n.axis_type_class.axis_A):
                if (int(ret_str) & splebo_n.NOVA_Class.kRR0_ZDRV) == 0:
                    ret = True
            else:
                if (int(ret_str) & splebo_n.NOVA_Class.kRR0_UDRV) == 0:
                    ret = True

        # ret_str = self.read_register(axis, splebo_n.NOVA_Class.kRR3)
        # if not ret_str == "":
        #    reg3_0 = 0x0000FFFF & int(ret_str)
        #    reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16

        #    if (reg3_0 & splebo_n.NOVA_Class.kRR3_INPOS) == 0:
        #        ret = True
        return ret

    # ----------------------------------------#
    # ------------ IAI Function---------------#
    # ----------------------------------------#
    def homing_move_start_IAI(self, axis):
        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.slm = 0
        splebo_n.set_order_motion_ctrl_class.slp = 0
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetSoftLimit)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET Software Limit")

        self.homing_on_off_IAI(axis, True)
        time.sleep(0.1)
        self.homing_on_off_IAI(axis, False)

    def homing_move_check_IAI(self, axis):
        ret = False

        ret_str = self.read_register(axis, splebo_n.NOVA_Class.kRR3)
        if not ret_str == "":
            reg3_0 = 0x0000FFFF & int(ret_str)
            # reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16
            if (reg3_0 & splebo_n.NOVA_Class.kRR3_STOP2) == 0:
                ret = True
        return ret

    def nova_homing_move_start_IAI(self, axis):
        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.dv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100)
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetDriveSpeed)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET DRIVE")

        splebo_n.set_order_motion_ctrl_class.slm = 0
        splebo_n.set_order_motion_ctrl_class.slp = 0
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetSoftLimit)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET Software Limit")

        orgn_dir = 0x00
        if splebo_n.axis_set_class[axis].origin_dir == 0:
            orgn_dir = 0x02

        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.h1m = 0x315 | orgn_dir
        splebo_n.set_order_motion_ctrl_class.h2m = 0x686
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetRetOriginMode)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET AUTO HOMING MODE")

        splebo_n.set_order_motion_ctrl_class.hv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100) - 1
        splebo_n.set_order_motion_ctrl_class.dv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100)
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kAutoOrigin)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR START AUTO HOMING")

    def nova_homing_move_check_IAI(self, axis):
        print("")

    def origin_sensor_check_IAI(self, axis):
        if not splebo_n.axis_sts_class[axis].is_io_origin_sensor:
            splebo_n.axis_sts_class[axis].is_homing_err = True
        return True

    def servo_on_off_IAI(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT0, on_off)

    def clear_on_off_IAI(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT1, on_off)

    def homing_on_off_IAI(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT2, on_off)

    # ----------------------------------------#
    # --------- STEPPING Function-------------#
    # ----------------------------------------#
    def homing_move_start_STEP(self, axis):
        self.homing_parameter_set(axis)
        return True

    def homing_move_check_STEP(self, axis):
        return True

    def nova_homing_move_start_STEP(self, axis):
        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.dv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100)
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetDriveSpeed)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET DRIVE")

        splebo_n.set_order_motion_ctrl_class.slm = 0
        splebo_n.set_order_motion_ctrl_class.slp = 0
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetSoftLimit)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET Software Limit")

        orgn_dir = 0x00
        if splebo_n.axis_set_class[axis].origin_dir == 0:
            orgn_dir = 0x02

        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.h1m = 0x315 | orgn_dir
        splebo_n.set_order_motion_ctrl_class.h2m = 0x686
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetRetOriginMode)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET AUTO HOMING MODE")

        splebo_n.set_order_motion_ctrl_class.hv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100) - 1
        splebo_n.set_order_motion_ctrl_class.dv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100)
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kAutoOrigin)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR START AUTO HOMING")

        while (True):
            if not self.nova_homing_move_check_STEP(axis):
                break

        return True

    def nova_homing_move_check_STEP(self, axis):
        self.read_axis_io(axis)
        return not splebo_n.axis_sts_class[axis].is_io_busy

    def origin_sensor_check_STEP(self, axis):
        if not splebo_n.axis_sts_class[axis].is_io_origin_sensor:
            splebo_n.axis_sts_class[axis].is_homing_err = True
        return True

    def servo_on_off_STEP(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT0, on_off)

    def clear_on_off_STEP(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT1, on_off)

    def homing_on_off_STEP(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT2, on_off)

    # ----------------------------------------#
    # ------------ aSTEP Function-------------#
    # ----------------------------------------#
    def homing_move_start_aSTEP(self, axis):
        self.homing_parameter_set(axis)
        return True

    def homing_move_check_aSTEP(self, axis):
        return True

    def nova_homing_move_start_aSTEP(self, axis):
        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.dv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100)
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetDriveSpeed)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET DRIVE")

        orgn_dir = 0x00
        if splebo_n.axis_set_class[axis].origin_dir == 0:
            orgn_dir = 0x02

        splebo_n.set_order_motion_ctrl_class.axis = axis
        splebo_n.set_order_motion_ctrl_class.h1m = 0x315 | orgn_dir
        splebo_n.set_order_motion_ctrl_class.h2m = 0x686
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kSetRetOriginMode)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR SET AUTO HOMING MODE")

        splebo_n.set_order_motion_ctrl_class.hv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100) - 1
        splebo_n.set_order_motion_ctrl_class.dv = \
            self.convert_axis_speed_mm_to_pulse(
                axis, splebo_n.axis_set_class[axis].origin_speed, 100)
        order_id = self.set_write_command(
            splebo_n.motion_controller_cmd_class.kAutoOrigin)
        self.wait_write_order_motion_ctrl(order_id)
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("ERR START AUTO HOMING")
        #
        while (True):
            if not self.nova_homing_move_check_aSTEP(axis):
                break
        return True

    def nova_homing_move_check_aSTEP(self, axis):
        self.read_axis_io(axis)
        return not splebo_n.axis_sts_class[axis].is_io_busy

    def origin_sensor_check_aSTEP(self, axis):
        if not splebo_n.axis_sts_class[axis].is_io_origin_sensor:
            splebo_n.axis_sts_class[axis].is_homing_err = True
        return True

    def servo_on_off_aSTEP(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT0, on_off)

    def clear_on_off_aSTEP(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT1, on_off)

    def homing_on_off_aSTEP(self, axis, on_off):
        self.write_axis_io(axis, splebo_n.axis_io_no_class.kOUT2, on_off)

    # ----------------------------------------#
    # -Motion Controller Api Command Function-#
    # ----------------------------------------#
    def cmd_board_open(self):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        if (False):
            eCsms_lib._thn_pg_open.restype = ctype.c_bool
            if eCsms_lib._thn_pg_open():
                ret = True
        else:
            eCsms_lib.cw_mc_open.restype = ctype.c_bool
            if eCsms_lib.cw_mc_open():
                ret = True

        return ret

    def cmd_set_mode(self, axis, wr1, wr2, wr3, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_mode.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_mode.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_mode(axis, wr1, wr2, wr3, lock):
            print("SUCCESS_MODE" + str(wr1) + "," + str(wr2) + "," + str(wr3))
            ret = True

        return ret

    def cmd_set_drive_speed(self, axis, dv, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_drive.argtypes = \
            (ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_drive.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_drive(axis, dv, lock):
            ret = True

        return ret

    def cmd_set_initial_velocity(self, axis, sv, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_iv.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_iv.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_iv(axis, sv, lock):
            ret = True

        return ret

    def cmd_set_acceleration(self, axis, ac, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_acc.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_acc.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_acc(axis, ac, lock):
            ret = True

        return ret

    def cmd_set_deceleration(self, axis, dc, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_dec.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_dec.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_dec(axis, dc, lock):
            ret = True

        return ret

    def cmd_set_ret_origin_mode(self, axis, h1m, h2m, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_org_mode.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_org_mode.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_org_mode(axis, h1m, h2m, lock):
            ret = True
        return ret

    def cmd_set_io_signal(self, axis, p1m, p2m, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_signal_io.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_signal_io.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_signal_io(axis, p1m, p2m, lock):
            ret = True

        return ret

    def cmd_set_input_signal_filter(self, axis, flm, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_input_filter.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_input_filter.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_input_filter(axis, flm, lock):
            ret = True

        return ret

    def cmd_auto_origin(self, axis, hv, dv):
        global eCsms_lib
        global read_order_motion_ctrl_count

        eCsms_lib.cw_mc_org.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_org.restype = ctype.c_bool
        if eCsms_lib.cw_mc_org(axis, hv, dv):
            ret = True

        return ret

    def cmd_set_soft_limit(self, axis, slm, slp):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_slimit.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_set_slimit.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_slimit(axis, slm, slp):
            ret = True

        return ret

    def cmd_move_relative(self, axis, tp, dv, is_abs):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_ptp.argtypes = (
            ctype.c_int, ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_ptp.restype = ctype.c_bool
        if eCsms_lib.cw_mc_ptp(axis, tp, dv, is_abs):
            ret = True

        return ret

    def cmd_move_absolute(self, axis, tp, dv):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_abs.argtypes = (ctype.c_int, ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_abs.restype = ctype.c_bool
        if eCsms_lib.cw_mc_abs(axis, tp, dv):
            ret = True

        return ret

    def cmd_move_jog(self, axis, ccw, dv):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_jog.argtypes = (ctype.c_int, ctype.c_bool, ctype.c_int)
        eCsms_lib.cw_mc_jog.restype = ctype.c_bool
        if eCsms_lib.cw_mc_jog(axis, ccw, dv):
            ret = True

        return ret

    def cmd_stop(self, axis):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_stop.argtypes = (ctype.c_int,)
        eCsms_lib.cw_mc_stop.restype = ctype.c_bool
        if eCsms_lib.cw_mc_stop(axis):
            ret = True

        return ret

    def cmd_deceleration_stop(self, axis):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_dcc_stop.argtypes = ctype.c_int
        eCsms_lib.cw_mc_dcc_stop.restype = ctype.c_bool
        if eCsms_lib.cw_mc_dcc_stop(axis):
            ret = True

        return ret

    def cmd_line_interpolation(self, axis, vect, decen, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        print("NO_LINE_VECT")

        return ret

    def cmd_circle_interpolation(self, axis, vect, ccw, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        print("NO_CIRCLE_VECT")

        return ret

    def cmd_continue_interpolation(self, axis, vect):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        print("NO_CONTINUE_VECT")

        return ret

    def cmd_get_logicalCoord(self, axis):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_logic_cie.argtypes = (
            ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_logic_cie.restype = ctype.c_bool

        buffer = (ctype.c_int * 16)()
        lp = cast(buffer, POINTER(ctype.c_int))

        if eCsms_lib.cw_mc_get_logic_cie(axis, lp):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(lp.contents.value)
            ret = True

        return ret

    def cmd_get_relativeCoord(self, axis):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_real_cie.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        buffer = (ctype.c_int * 16)()
        rp = cast(buffer, POINTER(ctype.c_int))

        if eCsms_lib.cw_mc_get_real_cie(axis, rp):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(rp.contents.value)
            ret = True

        return ret

    def cmd_set_logicalCoord(self, axis, lp):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_logic_cie.argtypes = (ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_set_logic_cie.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_logic_cie(axis, lp):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(lp)
            ret = True

        return ret

    def cmd_set_relativeCoord(self, axis, rp):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_real_cie.argtypes = (ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_set_real_cie.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_real_cie(axis, rp):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(rp)
            ret = True

        return ret

    def cmd_get_generalIO(self, axis, pio):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_gen_io.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        if eCsms_lib.cw_mc_get_gen_io(axis, pio):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(pio.value)
            ret = True

        return ret

    def cmd_set_general_output(self, axis, out):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_gen_out.argtypes = (ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_set_gen_out.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_gen_out(axis, out):
            ret = True

        return ret

    def cmd_set_general_output_bit(self, axis, bit, onoff):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_gen_bout.argtypes = \
            (ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_gen_bout.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_gen_bout(axis, bit, onoff):
            ret = True

        return ret

    def cmd_get_axis_status(self, axis, sts_no):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False
        sts = 0x00

        eCsms_lib.cw_mc_get_sts.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int), ctype.c_int)
        eCsms_lib.cw_mc_get_sts.restype = ctype.c_bool

        buffer = (ctype.c_int * 16)()
        sts = cast(buffer, POINTER(ctype.c_int))

        if eCsms_lib.cw_mc_get_sts(axis, sts, sts_no):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(sts[0])
            ret = True

        return ret

    def cmd_write_register(self, axis, reg_no, data):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_w_reg.argtypes = \
            (ctype.c_int, ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_w_reg.restype = ctype.c_bool
        if eCsms_lib.cw_mc_w_reg(axis, reg_no, data):
            ret = True

        return ret

    def cmd_read_register(self, axis, reg_no):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_r_reg.argtypes =\
            (ctype.c_int, ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_r_reg.restype = ctype.c_bool

        buffer = (ctype.c_int * 16)()
        data = cast(buffer, POINTER(ctype.c_int))

        if eCsms_lib.cw_mc_r_reg(axis, reg_no, data):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData =\
                    str(data.contents.value)
            ret = True

        return ret

    def cmd_write_register6_7(self, axis, data):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_w_reg67.argtypes = (ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_w_reg67.restype = ctype.c_bool
        if eCsms_lib.cw_mc_w_reg67(axis, data):
            ret = True

        return ret

    def cmd_read_register6_7(self, axis, data):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_r_reg67.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_r_reg67.restype = ctype.c_bool
        if eCsms_lib.cw_mc_r_reg67(axis, data):
            ret = True

        return ret

    def cmd_get_now_drive_speed(self, axis, cv):
        global eCsms_lib
        ret = False

        eCsms_lib.cw_mc_get_move_drive.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        if eCsms_lib.cw_mc_get_move_drive(axis, cv):
            ret = True

        return ret

    def cmd_get_now_acc_dec(self, axis, ca):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_acc_dec.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_acc_dec.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_acc_dec(axis, ca):
            ret = True

        return ret

    def cmd_get_multi_register(self, axis, mr_no, mr):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_mult_reg.argtypes = \
            (ctype.c_int, ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_mult_reg.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_mult_reg(axis, mr_no, mr):
            ret = True

        return ret

    def cmd_get_timer(self, axis, ct):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_timer.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_timer.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_timer(axis, ct):
            ret = True

        return ret

    def cmd_get_max_point_interpolation(self, axis, tx):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_max_intrpt.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        if eCsms_lib.cw_mc_get_max_intrpt(axis, tx):
            ret = True

        return ret

    def cmd_get_helical_rotation_num(self, axis, chln):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_helical_num.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_helical_num.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_helical_num(axis, chln):
            ret = True

        return ret

    def cmd_get_helical_calc_value(self, axis, hlv):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_calc_helical.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_calc_helical.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_calc_helical(axis, hlv):
            ret = True

        return ret

    def cmd_get_wr1_2_3(self, axis, wr_no, wr):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_wr123.argtypes = \
            (ctype.c_int, ctype.c_int, POINTER(ctype.c_int))
        if eCsms_lib.cw_mc_get_wr123(axis, wr_no, wr):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(wr.value)
            ret = True

        return ret

    def cmd_get_PI0_mode(self, axis, pm):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_pio_mode.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_pio_mode.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_pio_mode(axis, pm):
            ret = True

        return ret

    def cmd_get_multi_register_mode(self, axis, mrm):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_mult_reg_mode.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_mult_reg_mode.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_mult_reg_mode(axis, mrm):
            ret = True

        return ret

    def cmd_get_acceleration(self, axis, ac):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_acc.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_acc.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_acc(axis, ac):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(ac.value)
            ret = True

        return ret

    def cmd_get_initial_velocity(self, axis, sv):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_iv.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_iv.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_iv(axis, sv):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(sv.value)
            ret = True

        return ret

    def cmd_get_drive_speed(self, axis, dv):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_drive.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_drive.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_drive(axis, dv):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(dv.value)
            ret = True

        return ret

    def cmd_get_end_point(self, axis, tp):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_end_point.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_end_point.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_end_point(axis, tp):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(tp.value)
            ret = True

        return ret

    def cmd_get_split_pulse1(self, axis, sp1):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_split1.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_split1.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_split1(axis, sp1):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(sp1.value)
            ret = True

        return ret

    def cmd_get_general_input(self, axis, ui):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_gen_in.argtypes = \
            (ctype.c_int, POINTER(ctype.c_int))
        eCsms_lib.cw_mc_get_gen_in.restype = ctype.c_bool
        if eCsms_lib.cw_mc_get_gen_in(axis, ui):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(ui.value)
            ret = True

        return ret

    def cmd_get_end_coordinate(self, axis, tp):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_end_cie.argtypes = \
            (ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_set_end_cie.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_end_cie(axis, tp):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(tp)
            ret = True

        return ret

    def cmd_get_arc_center_coordinate(self, axis, cp):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_circ_center.argtypes = \
            (ctype.c_int, ctype.c_int)
        eCsms_lib.cw_mc_set_circ_center.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_circ_center(axis, cp):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(cp)
            ret = True

        return ret

    def cmd_set_manual_dec(self, axis, dp, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_manual_dec.argtypes = \
            (ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_manual_dec.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_manual_dec(axis, dp, lock):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(dp)
            ret = True

        return ret

    def cmd_set_interpolation_mode(self, axis, ipm, lock):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_set_intrpt_mode.argtypes = \
            (ctype.c_int, ctype.c_int, ctype.c_bool)
        eCsms_lib.cw_mc_set_intrpt_mode.restype = ctype.c_bool
        if eCsms_lib.cw_mc_set_intrpt_mode(axis, ipm, lock):
            splebo_n.order_motion_ctrl_class[
                read_order_motion_ctrl_count].readData = str(ipm)
            ret = True

        return ret

    def cmd_get_api(self):
        global eCsms_lib
        global read_order_motion_ctrl_count
        ret = False

        eCsms_lib.cw_mc_get_ver.restype = ctype.c_char_p
        splebo_n.order_motion_ctrl_class[
            read_order_motion_ctrl_count].readData = eCsms_lib._thn_Api_ePI09()
        ret = True

        return ret


# - Class --------------------------------------------------------------
# class io_expander_class:
    kBoard_count = 2
    kBoard_bit = 8

    kI2c_bus = 3	# 5
    kExpand_module_address_0 = 0x21
    kExpand_module_address_1 = 0x24
    kExpand_module_address_2 = 0x23
    kExpand_module_address_3 = 0x26

    kExpand_HD1_PA0 = 0x01
    kExpand_HD1_PA1 = 0x02
    kExpand_HD1_PA2 = 0x04
    kExpand_HD1_PA3 = 0x08
    kExpand_HD1_PA4 = 0x10
    kExpand_HD1_PA5 = 0x20
    kExpand_HD1_PA6 = 0x40
    kExpand_HD1_PA7 = 0x80

    kExpand_HD2_PB0 = 0x01
    kExpand_HD2_PB1 = 0x02
    kExpand_HD2_PB2 = 0x04
    kExpand_HD2_PB3 = 0x08
    kExpand_HD2_PB4 = 0x10
    kExpand_HD2_PB5 = 0x20
    kExpand_HD2_PB6 = 0x40
    kExpand_HD2_PB7 = 0x80

    kExpand_IODIRA_BANK0 = 0x00
    kExpand_IODIRB_BANK0 = 0x01
    kExpand_IPOLA_BANK0 = 0x02
    kExpand_IPOLB_BANK0 = 0x03
    kExpand_GPINTENA_BANK0 = 0x04
    kExpand_GPINTENB_BANK0 = 0x05
    kExpand_DEFVALA_BANK0 = 0x06
    kExpand_DEFVALB_BANK0 = 0x07
    kExpand_INTCONA_BANK0 = 0x08
    kExpand_INTCONB_BANK0 = 0x09
    kExpand_IOCON_BANK0 = 0x0A
    kExpand_GPPUA_BANK0 = 0x0C
    kExpand_GPPUB_BANK0 = 0x0D
    kExpand_INTFA_BANK0 = 0x0E
    kExpand_INTFB_BANK0 = 0x0F
    kExpand_INTCAPA_BANK0 = 0x10
    kExpand_INTCAPB_BANK0 = 0x11
    kExpand_GPIOA_BANK0 = 0x12
    kExpand_GPIOB_BANK0 = 0x13
    kExpand_OLATA_BANK0 = 0x14
    kExpand_OLATB_BANK0 = 0x15

    i2c_smbus = None
    expand_data_list = None
    expand_read_data_list = None
    expand_write_data_list = None

    Flag_io_expander_thread = False
    io_thread = None

    def __init__sub(self):
        # global i2c_smbus
        # global expand_data_list
        # global expand_read_data_list
        # global expand_write_data_list
        #
        # print ("io_ex_ctrl.__init__()")
        #
        self.i2c_smbus = smbus.SMBus(self.kI2c_bus)
        self.expand_data_list = [[0 for j in range(self.kBoard_bit)]
                                 for i in range(self.kBoard_count)]
        self.expand_read_data_list = [0 for i in range(self.kBoard_count)]
        self.expand_write_data_list = [0 for i in range(self.kBoard_count)]

    def initialize_io_expander(self):
        # global i2c_smbus
        #
        # print ("io_ex_ctrl.initialize_io_expander()")
        #
        try:
            # Input ----------------------------------------------------------
            # Expander Board No.1 Set I/O Direction
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_0, self.kExpand_IODIRA_BANK0, 0xFF)
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_0, self.kExpand_IODIRB_BANK0, 0xFF)

            # Expander Board No.1 Set I/O Logic
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_0, self.kExpand_IPOLA_BANK0, 0xFF)
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_0, self.kExpand_IPOLB_BANK0, 0xFF)

            # Expander Board No.2 Set I/O Direction
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_2, self.kExpand_IODIRA_BANK0, 0xFF)
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_2, self.kExpand_IODIRB_BANK0, 0xFF)

            # Expander Board No.2 Set I/O Logic
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_2, self.kExpand_IPOLA_BANK0, 0xFF)
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_2, self.kExpand_IPOLB_BANK0, 0xFF)

            # Output ---------------------------------------------------------
            # Expander Board No.1 Set I/O Direction
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_1, self.kExpand_IODIRA_BANK0, 0x00)
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_1, self.kExpand_IODIRB_BANK0, 0x00)

            # Expander Board No.1 Set I/O Logic
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_1, self.kExpand_IPOLA_BANK0, 0x00)
            self.i2c_smbus.write_byte_data(
                self.kExpand_module_address_1, self.kExpand_IPOLB_BANK0, 0x00)

            # Expander Board No.2 Set I/O Direction
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_3, self.kExpand_IODIRA_BANK0, 0x00)
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_3, self.kExpand_IODIRB_BANK0, 0x00)

            # Expander Board No.2 Set I/O Logic
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_3, self.kExpand_IPOLA_BANK0, 0x00)
            # self.i2c_smbus.write_byte_data(
            #     self.kExpand_module_address_3, self.kExpand_IPOLB_BANK0, 0x00)

        except OSError as e:
            print(f"Error:initialize_io_expanderにてエラーが発生しました: {e}")
            return False
        return True

    def write_bit(self, board_no: int, bit_no: int, on_off: bool) -> None:
        #
        if board_no < 0 or 15 < board_no:
            return None

        if on_off:
            self.expand_write_data_list[board_no] = \
                (self.expand_write_data_list[board_no] & 0xFFFF) |\
                (0x0001 << bit_no)
        else:
            self.expand_write_data_list[board_no] = \
                (self.expand_write_data_list[board_no] & 0xFFFF) &\
                (~(0x0001 << bit_no))

    def read_board(self, board_no):
        #
        expand_address = 0x00

        if board_no == 0:
            expand_address = self.kExpand_module_address_0
        elif board_no == 1:
            expand_address = self.kExpand_module_address_2
        else:
            return None

        read_data = 0x0000

        side_a_data = self.i2c_smbus.read_byte_data(
            expand_address, self.kExpand_GPIOA_BANK0)
        side_b_data = self.i2c_smbus.read_byte_data(
            expand_address, self.kExpand_GPIOB_BANK0)

        read_data = side_a_data | (side_b_data << 8)

        self.expand_read_data_list[board_no] = read_data

        return read_data

    def write_board(self, board_no):
        global i2c_smbus
        #
        if board_no == 0:
            expand_address = self.kExpand_module_address_1
        elif board_no == 1:
            expand_address = self.kExpand_module_address_3
        #
        write_data = self.expand_write_data_list[board_no]
        side_a_data = write_data & 0x00FF
        side_b_data = (write_data >> 8) & 0x00FF
        self.i2c_smbus.write_byte_data(
            expand_address, self.kExpand_OLATA_BANK0, side_a_data)
        self.i2c_smbus.write_byte_data(
            expand_address, self.kExpand_OLATB_BANK0, side_b_data)

    def io_thread_1action(self):
        if (True):      # (self.Flag_io_expander_thread):
            #
            self.write_board(0)
            time.sleep(0.001)
            #
            # self.write_board(1)
            # time.sleep(0.001)
            #
            self.read_board(0)
            time.sleep(0.001)
            #
            # self.read_board(1)
            # time.sleep(0.001)
            #
        # End thread Loop

# - Function -----------------------------------------------------------

# ---------END OF CODE--------- #
