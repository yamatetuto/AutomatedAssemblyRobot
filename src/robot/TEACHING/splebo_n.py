# *********************************************************************#
# File Name : splebo_n.py
# Explanation : splebo_n Library Parameter
# Project Name : SPLEBO N
# ----------------------------------------------------------------------
# History :
#           ver0.0.1 2024.10.22 New Create
# *********************************************************************#

# - Define import/from -------------------------------------------------
# import sys
import os
# import enum
# from enum import Enum
import RPi.GPIO as GPIO
import threading
from threading import Thread
import time
import copy
# import math
import file_ctrl as filectl
import motion_control as motion_ctl
# import io_expander as io_ex
import can
import mmap
import constant as const


# - Class --------------------------------------------------------------
class NOVA_Class:
    kWR0 = 0x00

    kRR0 = 0x00
    kRR0_XDRV = 0x01
    kRR0_YDRV = 0x02
    kRR0_ZDRV = 0x04
    kRR0_UDRV = 0x08
    kRR0_XERR = 0x10
    kRR0_YERR = 0x20
    kRR0_ZERR = 0x40
    kRR0_UERR = 0x80

    kRR1 = 0x01

    kRR2 = 0x02
    kRR2_ALM = 10
    kRR2_EMG = 20

    kRR3 = 0x03
    kRR3_STOP0 = 0x01
    kRR3_STOP1 = 0x02
    kRR3_STOP2 = 0x04
    kRR3_INPOS = 0x20

    kRR4 = 0x04
    kRR4_XPIO0 = 0x01
    kRR4_XPIO1 = 0x02
    kRR4_XPIO2 = 0x04
    kRR4_XPIO3 = 0x08
    kRR4_XPIO4 = 0x10
    kRR4_XPIO5 = 0x20
    kRR4_XPIO6 = 0x40
    kRR4_XPIO7 = 0x80
    kRR4_YPIO0 = 0x100
    kRR4_YPIO1 = 0x200
    kRR4_YPIO2 = 0x400
    kRR4_YPIO3 = 0x800
    kRR4_YPIO4 = 0x1000
    kRR4_YPIO5 = 0x2000
    kRR4_YPIO6 = 0x4000
    kRR4_YPIO7 = 0x8000

    kRR5 = 0x05
    kRR5_ZPIO0 = 0x01
    kRR5_ZPIO1 = 0x02
    kRR5_ZPIO2 = 0x04
    kRR5_ZPIO3 = 0x08
    kRR5_ZPIO4 = 0x10
    kRR5_ZPIO5 = 0x20
    kRR5_ZPIO6 = 0x40
    kRR5_ZPIO7 = 0x80
    kRR5_UPIO0 = 0x100
    kRR5_UPIO1 = 0x200
    kRR5_UPIO2 = 0x400
    kRR5_UPIO3 = 0x800
    kRR5_UPIO4 = 0x1000
    kRR5_UPIO5 = 0x2000
    kRR5_UPIO6 = 0x4000
    kRR5_UPIO7 = 0x8000


class gpio_class:
    kNova_reset_pin = 14
    kNova_Power_pin = 12  # 17
    kCan_CS_pin = 8
    kEmergencyBtn = 15


class axis_move_type_class:
    kRelative = 0
    kAbsolute = 1
    kJog = 2


class axis_io_no_class:
    kOUT0 = 0
    kOUT2 = 1
    kOUT4 = 2
    kOUT6 = 3
    kDCC_OUT = 4
    kOUT1 = 5
    kOUT3 = 6
    kOUT5 = 7
    kOUT7 = 8


class axis_setting_class:
    max_speed = 0
    max_accel = 0
    max_decel = 0
    start_speed = 0
    offset_speed = 0
    origin_speed = 0
    origin_offset = 0
    limit_plus = 0
    limit_minus = 0
    pulse_length = 0
    origin_order = 0
    origin_dir = 0
    origin_sensor = 0
    origin_sensor_name = ""
    in_position = 0
    motor_type = 0
    motor_type_name = ""


class axis_setting_type_class:
    kMax_speed = 0
    kMax_accel = 1
    kMax_decel = 2
    kStart_speed = 3
    kOffset_speed = 4
    kOrigin_speed = 5
    kOrigin_offset = 6
    kLimit_plus = 7
    kLimit_minus = 8
    kPulse_length = 9
    kOrigin_order = 10
    kOrigin_dir = 11
    kOrigin_sensor = 12
    kIn_position = 13
    kMotor_type = 14


class axis_maker_Class:
    kNone = 0
    kIAI = 2
    kStepping = 4
    kaSTEP = 5


class on_off_auto_class:
    kOFF = 0
    kON = 1
    kAUTO = 2


class motion_controller_cmd_class():
    kOpen = 1
    kSetMode = 2
    kSetDriveSpeed = 3
    kSetInitialVelocity = 4
    kSetAcceleration = 5
    kSetDeceleration = 6
    kSetRetOriginMode = 7
    kSetIOSignal = 8
    kSetInputSignalFilter = 9
    kAutoOrigin = 10
    kSetSoftLimit = 11
    kMoveRelative = 12
    kMoveAbsolute = 13
    kMoveJOG = 14
    kStop = 15
    kDecelerationStop = 16
    kLineInterpolation = 17
    kCircleInterpolation = 18
    kContinueInterpolation = 19
    kGetLogicalCoord = 20
    kGetRelativeCoord = 21
    kSetLogicalCoord = 22
    kSetRelativeCoord = 23
    kGetGeneralIO = 24
    kSetGeneralOutput = 25
    kSetGeneralOutputBit = 26
    kGetAxisStatus = 27
    kWriteRegister = 28
    kReadRegister = 29
    kWriteRegister6_7 = 30
    kReadRegister6_7 = 31
    kGetNowDriveSpeed = 32
    kGetNowAccDec = 33
    kGetMultiRegister = 34
    kGetTimer = 35
    kGetMaxPointInterpolation = 36
    kGetHelicalRotationNum = 37
    kGetHelicalCalcValue = 38
    kGetWR1_2_3 = 39
    kGetPI0Mode = 40
    kGetMultiRegisterMode = 41
    kGetAcceleration = 42
    kGetInitialVelocity = 43
    kGetDriveSpeed = 44
    kGetEndPoint = 45
    kGetSplitPulse1 = 46
    kGetGeneralInput = 47
    kGetEndCoordinate = 48
    kGetArcCenterCoordinate = 49
    kSetManualDec = 50
    kSetInterpolationMode = 51
    kGetApi = 52


class axis_type_class:
    axis_ALL = -1
    axis_X = 0
    axis_Y = 1
    axis_Z = 2
    axis_U = 3
    axis_S1 = 4
    axis_S2 = 5
    axis_A = 6
    axis_B = 7

    axis_count = 8


class homing_class:
    kHomeMoveStart = 0
    kHomeMoveCheck = 1
    kNovaHomeMoveStart = 2
    kNovaHomeMoveCheck = 3
    kOriginSensorCheck = 4
    kOffsetMoveStart = 5
    kOffsetMoveCheck = 6
    kParameterSet = 7
    kEnd = 8

    home_seq = []
    home_is_end_list = []
    home_turn_list = []
    home_turn = 0

    def init():
        homing_class.home_seq.clear()
        homing_class.home_is_end_list.clear()
        homing_class.home_turn_list.clear()
        homing_class.home_turn = 0

        for i in range(0, axis_type_class.axis_count):
            homing_class.home_seq.append(0)
            if axis_set_class[i].motor_type != \
               axis_maker_Class.kNone:
                homing_class.home_is_end_list.append(False)
                is_add = False
                for j in range(len(homing_class.home_turn_list)):
                    if homing_class.home_turn_list[j][0]\
                            == int(axis_set_class[i].origin_order):
                        homing_class.home_turn_list[j].append(i)
                        is_add = True
                        break
                if not is_add:
                    idx = int(axis_set_class[i].origin_order)
                    homing_class.home_turn_list.append([idx, i])
            else:
                homing_class.home_is_end_list.append(True)


# -------------------------------------------------------------------
backup_home_is_end_list = []
# -------------------------------------------------------------------


class axis_func_maker_class:
    func_home_move_start = None
    func_home_move_check = None
    func_nova_home_move_start = None
    func_nova_home_move_check = None
    func_origin_sensor_check = None

    func_offset_move_start = None
    func_offset_move_check = None
    func_parameter_start = None

    func_servo_on_off = None
    func_reset_actuator = None
    func_homing_on_off = None


class axis_const_class:
    kMinPoint = 0
    kMaxPoint = 5000
    kSpeedMaxRange = 100
    kSpeedMinRange = 1
    kMaxStrokeLimit = 999.9
    kMinStrokeLimit = 0
    kMaxCommentLen = 7

    kMaxSettingSpeed = 10000
    kMinSettingSpeed = 1
    kMaxSettingCoord = 10000
    kMinSettingCoord = -10000
    kMaxPulseLength = 100.0
    kMinPulseLength = 0.01


class axis_status_class:
    maker_type = axis_maker_Class.kIAI     # Maker Type

    is_io_ready = False
    is_io_alarm = False
    is_io_in0 = False
    is_io_in1 = False
    is_io_in2 = False
    is_io_in3 = False
    is_io_home = False
    is_io_busy = False
    is_io_emergency = False
    is_io_out0 = False
    is_io_out1 = False
    is_io_out2 = False
    is_io_out3 = False
    is_io_out4 = False
    is_io_out5 = False
    is_io_out6 = False
    is_io_out7 = False
    is_io_dcc_out = False
    is_io_origin_sensor = False
    is_homing_err = False

    abs_coord = 0.00                            # absolute Coordinate
    rel_coord = 0.00                            # relative coordinate


class order_motion_controller_class:
    axis = 0
    cmd = motion_controller_cmd_class.kOpen

    wr1 = 0                                     # write register 1
    wr2 = 0                                     # write register 2
    wr3 = 0                                     # write register 3
    dv = 0                                      # drive speed
    sv = 0                                      # initial velocity
    ac = 0                                      # acceleration
    dc = 0                                      # deceleration
    h1m = 0                                     # return origin mode 1
    h2m = 0                                     # return origin mode 2
    p1m = 0                                     # I/O signal set 1
    p2m = 0                                     # I/O signal set 2
    flm = 0                                     # input signal filter
    hv = 0                                      # origin detect speed
    slm = 0                                     # software limit minus
    slp = 0                                     # software limit plus
    tp = 0                                      # target coord
    isAbs = False                               # True(Absolute):(relative)
    isCcw = False                               # True(CCW):(CW)
    sts_no = 0                                   # status number
    reg_no = 0                                  # register number
    data = 0                                    # write data
    bit = 0                                     # bit
    on_off = False                              # ON/OFF
    mrNo = 0                                    # multipurpose register value
    wrNo = 0                                    # write register value
    pio = 0                                     # i/o status

    readData = ""
    isFuncSuccess = False

    isRead = False                              # Read Complete Flag
    isSet = False                               # Set Complete Flag


class order_move_motion_controller_class:
    is_move = False
    speed = 0
    target_coord = 0


# - Variable -----------------------------------------------------------
kMaxOrderMotionCtrlBuffSize = 255

axis_set_class = []
axis_sts_class = []
order_motion_ctrl_class = []
order_move_motion_ctrl_class = []
axis_func_class = []

set_order_motion_ctrl_class = order_motion_controller_class()

enable_type_list = ["OFF", "ON"]
origin_type_list = ["OFF", "", "AUTO"]
maker_type_list = ["None", "", "IAI", "", "Stepping", "aSTEP"]
equal_sign_type_list = ["-", "+"]

def_max_speed_ary = [800, 800, 225, 1200, 10, 10, 8000, 8000]
def_max_accel_ary = [2940, 2940, 1960, 40000, 100, 100, 50000, 50000]
def_max_decel_ary = [2940, 2940, 1960, 40000, 100, 100, 50000, 50000]
def_start_speed_ary = [200, 200, 50, 50, 10, 10, 500, 500]
def_offset_speed_ary = [10, 10, 10, 50, 10, 10, 10, 10]
def_origin_speed_ary = [10, 10, 10, 50, 10, 10, 10, 10]
def_origin_offset_ary = [0, 0, 0, 0, 0, 0, 0, 0]
def_limit_plus_ary = [300.5, 300.5, 100.5, 0, 0, 0, 0, 0]
def_limit_minus_ary = [-0.5, -0.5, -0.5, 0, 0, 0, 0, 0]
def_pulse_length_ary = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]
def_origin_order_ary = [2, 2, 1, 1, 1, 1, 1, 1]
def_origin_dir_ary = [0, 0, 0, 0, 0, 0, 0, 0]
def_origin_sensor_ary = [0, 0, 0, 0, 0, 0, 0, 0]
def_in_position_ary = [1, 1, 1, 1, 0, 0, 0, 0]
def_motor_type_ary = [1, 1, 1, 0, 0, 0, 0, 0]

program_end_flag = False

APP_LOGO = ''

G_DataToGUI = bytearray([0,0,0,0,0,0,0,0,0,0])


class splebo_n_class:
    # - Variable ----------------------------------------------------------
    file_pos_class = None   # filectl.PositionFileClass()
    file_prj_class = None   # filectl.ProjectFileClass()
    motion_class = None     # motion_ctl.motion_control_class()
    stdio_class = None
    canio_class = can.can_ctrl_class()
    backup_home_is_end_list = []

    # - Function ----------------------------------------------------------
    def __init__(self):
        print("__init()__")
        self.init()
        return

    def init(self):
        """
        Function: 本ライブラリ初期化
        """
        print("splebo_n.init()")

        self.param_init()
        #
        self.init_gpio()
        #

        self.__init__gui()

        self.start_chk_EMG_thread()

        self.file_pos_class = filectl.PositionFileClass()
        self.file_prj_class = filectl.ProjectFileClass()
        self.motion_class = motion_ctl.motion_control_class()
        # self.stdio_class = self.motion_class

        is_success, is_errmsg = self.read_syspara_file()
        if not is_success:
            raise ValueError(is_errmsg)

        if not self.motion_init():
            raise ValueError("Failed to initialize the Motion Controller.")

        homing_class.init()

        # Read Position File
        is_success, is_errmsg = self.read_position_file()
        if not is_success:
            raise ValueError(is_errmsg)

        # if not self.motion_init():
        #    raise ValueError("Failed to initialize the Motion Controller.")
        #
        # motion_init includes io_ex_init()
        # if not self.io_ex_init():
        #    raise ValueError("Failed to initialize the IO.")

        self.canio_init()

    def close(self):
        """
        Function: 本ライブラリClose
        """
        #
        self.stop_chk_EMG_thread()
        #
        self.stop_canio_thread()
        #
        self.stop_motion_thread()
        #
        # stop_motion_thread() includes stop_io_expander_thread()
        # self.stop_io_expander_thread()
        #
        self.canio_class = None
        self.motion_class = None
        # self.stdio_class = None

    def param_init(self):
        """
        Function: 本ライブラリのパラメータ初期化
        """
        global axis_set_cls
        global axis_sts_class
        global order_motion_ctrl_class
        global kMaxOrderMotionCtrlBuffSize
        global order_move_motion_ctrl_class
        global axis_func_class
        for i in range(kMaxOrderMotionCtrlBuffSize):
            order_motion_ctrl_class.append(order_motion_controller_class())
        #
        for i in range(axis_type_class.axis_count):
            axis_set_class.append(axis_setting_class())
            axis_set_class[i].max_speed = def_max_speed_ary[i]
            axis_set_class[i].max_accel = def_max_accel_ary[i]
            axis_set_class[i].max_decel = def_max_decel_ary[i]
            axis_set_class[i].start_speed = def_start_speed_ary[i]
            axis_set_class[i].offset_speed = def_offset_speed_ary[i]
            axis_set_class[i].origin_speed = def_origin_speed_ary[i]
            axis_set_class[i].origin_offset = def_origin_offset_ary[i]
            axis_set_class[i].limit_plus = def_limit_plus_ary[i]
            axis_set_class[i].limit_minus = def_limit_minus_ary[i]
            axis_set_class[i].pulse_length = def_pulse_length_ary[i]
            axis_set_class[i].origin_order = def_origin_order_ary[i]
            axis_set_class[i].origin_dir = def_origin_dir_ary[i]
            axis_set_class[i].origin_sensor = def_origin_sensor_ary[i]
            axis_set_class[i].in_position = def_in_position_ary[i]
            axis_set_class[i].motor_type = def_motor_type_ary[i]
            #
            axis_sts_class.append(axis_status_class())
            order_motion_ctrl_class.append(order_motion_controller_class())
            order_move_motion_ctrl_class.\
                append(order_move_motion_controller_class())
            axis_func_class.append(axis_func_maker_class())

    def clear_all_order_move_motion_ctrl_class(self):
        """
        Function: order_move_motion_ctrl_classクリア
        """
        global order_move_motion_ctrl_class
        for i in range(axis_type_class.axis_count):
            order_move_motion_ctrl_class[i].is_move = False

            order_move_motion_ctrl_class[i].speed = 0
            order_move_motion_ctrl_class[i].target_coord = 0

    def motion_init(self):
        """
        Function: モーション制御の初期化
        """
        return self.motion_class.initialize_motion_contoller()

    def stop_motion_thread(self):
        """
        Function: モーション制御スレッドの停止
        """
        self.motion_class.stop_motion_thread()
        return

    def motion_movePoint(self, axisbit, pointNo, speedRate):
        """
        Function: ポイント番号の地点へ移動させる

        Arguments:
        axisbit  - 軸指定ビット（bit0=X, bit1=Y, bit2=Z, bit3=U...)
        targetPos - 目標ポイント
        speedRate - 速度レート(%)
        """
        self.motion_movePoint_start(axisbit, pointNo, speedRate)
        self.motion_wait_move_end_All()

    def motion_movePoint_start(self, axisbit, pointNo, speedRate):
        """
        Function: ポイント番号の地点へ移動させる

        Arguments:
       axisbit  - 軸指定ビット（bit0=X, bit1=Y, bit2=Z, bit3=U...)
        targetPos - 目標ポイント
        speedRate - 速度レート(%)
        """
        axis0 = 0
        axis1 = 0
        axis2 = 0
        pNo = int(pointNo)
        if (axisbit == 0):
            return
        elif (axisbit == 0x01):
            axis0 = 0
            targetPos0 = float(self.file_pos_class.GetPointData(pNo, axis0))
            self.motion_move_start(axis0, targetPos0, speedRate)
        elif (axisbit == 0x02):
            axis0 = 1
            targetPos0 = float(self.file_pos_class.GetPointData(pNo, axis0))
            self.motion_move_start(axis0, targetPos0, speedRate)
        elif (axisbit == 0x04):
            axis0 = 2
            targetPos0 = float(self.file_pos_class.GetPointData(pNo, axis0))
            self.motion_move_start(axis0, targetPos0, speedRate)
        elif (axisbit == 0x03):
            axis0 = 0
            targetPos0 = float(self.file_pos_class.GetPointData(pNo, axis0))
            axis1 = 1
            targetPos1 = float(self.file_pos_class.GetPointData(pNo, axis1))
            self.motion_2axis_move_start(axis0, targetPos0, speedRate,
                                         axis1, targetPos1, speedRate)
        elif (axisbit == 0x05):
            axis0 = 0
            targetPos0 = float(self.file_pos_class.GetPointData(pNo, axis0))
            axis1 = 2
            targetPos1 = float(self.file_pos_class.GetPointData(pNo, axis1))
            self.motion_2axis_move_start(axis0, targetPos0, speedRate,
                                         axis1, targetPos1, speedRate)
        elif (axisbit == 0x06):
            axis0 = 1
            targetPos0 = float(self.file_pos_class.GetPointData(pNo, axis0))
            axis1 = 2
            targetPos1 = float(self.file_pos_class.GetPointData(pNo, axis1))
            self.motion_2axis_move_start(axis0, targetPos0, speedRate,
                                         axis1, targetPos1, speedRate)
        elif (axisbit == 0x07):
            axis0 = 0
            targetPos0 = float(self.file_pos_class.GetPointData(pNo, axis0))
            axis1 = 1
            targetPos1 = float(self.file_pos_class.GetPointData(pNo, axis1))
            axis2 = 2
            targetPos2 = float(self.file_pos_class.GetPointData(pNo, axis2))
            self.motion_3axis_move_start(axis0, targetPos0, speedRate,
                                         axis1, targetPos1, speedRate,
                                         axis2, targetPos2, speedRate)
        #
        return

    def motion_wait_move_end_All(self):
        """
        Function: 移動完了待ち
        """
        self.motion_wait_move_end(0)
        self.motion_wait_move_end(1)
        self.motion_wait_move_end(2)
        # self.motion_wait_move_end(3)
        return

    def motion_move(self, axis, targetPos, speedRate):
        """
        Function: 指定軸を、指定位置へ、指定の速度率で移動

        Arguments:
        axis - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos - 目標位置（mm値）
        speedRate - システムパラメータにて設定された速度の速度率（％値：1～100）
        """
        self.motion_move_start(axis, targetPos, speedRate)
        self.motion_wait_move_end(axis)

    def motion_move_start(self, axis, targetPos, speedRate):
        """
        Function: 指定軸を、指定位置へ、指定の速度率で移動開始します
                  （移動完了を待ちません）

        Arguments:
        axis - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos - 目標位置（mm値）
        speedRate - システムパラメータにて設定された速度の速度率（％値：1～100）
        """
        axisNo = int(axis)
        if (axisNo < 0 or axis_type_class.axis_count <= axisNo):
            return
        #
        Plslen = self.motion_class.convert_axis_mm_to_pulse(axisNo, targetPos)
        Speed = self.motion_class.\
            convert_axis_speed_per_to_speed(axisNo, speedRate)
        # print ("pulseLength=", Plslen)
        # print ("Speed=", Speed)
        Result = self.motion_class.cmd_move_absolute(axisNo, Plslen, Speed)
        if (Result is False):
            pass
            # Error
        #
        return

    def motion_wait_move_end(self, axis):
        """
        Function: 指定軸の移動完了を待ちます

        Arguments:
        axis - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        """
        ret = False

        time.sleep(0.1)

        while True:
            if (self.emg_getstat() is True):
                return False
            ret_str = self.motion_class.read_register(axis, NOVA_Class.kRR3)
            if not ret_str == "":
                reg3_0 = 0x0000FFFF & int(ret_str)
                # reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16

                if (reg3_0 & NOVA_Class.kRR3_INPOS) == 0:
                    ret = True
                    break
                #
        return ret

    def motion_2axis_move(self, axis0, targetPos0, speedRate0,
                          axis1, targetPos1, speedRate1):
        """
        Function: 指定２軸を、各指定位置へ、各指定の速度率で移動します

        Arguments:
        axis0 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos0 - 目標位置（mm値）
        speedRate0 - システムパラメータにて設定された速度の速度率（％値：1～100）
        axis1 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos1 - 目標位置（mm値）
        speedRate1 - システムパラメータにて設定された速度の速度率（％値：1～100）
        """
        self.motion_2axis_move_start(axis0, targetPos0, speedRate0,
                                     axis1, targetPos1, speedRate1)
        self.motion_wait_2axis_move_end(axis0, axis1)

    def motion_2axis_move_start(self, axis0, targetPos0, speedRate0,
                                axis1, targetPos1, speedRate1):
        """
        Function: 指定２軸を、各指定位置へ、各指定の速度率で移動開始します
                  （移動完了を待ちません）
        Arguments:
        axis0 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos0 - 目標位置（mm値）
        speedRate0 - システムパラメータにて設定された速度の速度率（％値：1～100）
        axis1 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos1 - 目標位置（mm値）
        speedRate1 - システムパラメータにて設定された速度の速度率（％値：1～100）
        """
        axisNo0 = int(axis0)
        if (axisNo0 < 0 or axis_type_class.axis_count <= axisNo0):
            return
        #
        axisNo1 = int(axis1)
        if (axisNo1 < 0 or axis_type_class.axis_count <= axisNo1):
            return
        #
        if (axisNo0 == axisNo1):
            return
        #
        Plslen0 = self.motion_class.convert_axis_mm_to_pulse(
                axisNo0, targetPos0)
        Speed0 = self.motion_class.convert_axis_speed_per_to_speed(
                axisNo0, speedRate0)
        #
        Plslen1 = self.motion_class.convert_axis_mm_to_pulse(
                axisNo1, targetPos1)
        Speed1 = self.motion_class.convert_axis_speed_per_to_speed(
                axisNo1, speedRate1)
        #
        Result = self.motion_class.cmd_move_absolute(
            axisNo0, Plslen0, Speed0)
        if Result is False:
            # Error
            pass
        #
        Result = self.motion_class.cmd_move_absolute(
            axisNo1, Plslen1, Speed1)
        if Result is False:
            # Error
            pass
        #
        return

    def motion_wait_2axis_move_end(self, axis0, axis1):
        """
        Function: 指定２軸移動完了を待ちます

        Arguments:
        axis0 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        axis1 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        """
        ret = False

        time.sleep(0.1)

        while True:
            if (self.emg_getstat() is True):
                return False
            ret_str = self.motion_class.read_register(axis0, NOVA_Class.kRR3)
            if not ret_str == "":
                reg3_0 = 0x0000FFFF & int(ret_str)
                # reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16

                if (reg3_0 & NOVA_Class.kRR3_INPOS) == 0:
                    ret = True
                    break
                #
        while True:
            if (self.emg_getstat() is True):
                return False
            ret_str = self.motion_class.read_register(axis1, NOVA_Class.kRR3)
            if not ret_str == "":
                reg3_0 = 0x0000FFFF & int(ret_str)
                # reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16

                if (reg3_0 & NOVA_Class.kRR3_INPOS) == 0:
                    ret = True
                    break
                #
        return ret

    def motion_3axis_move(self, axis0, targetPos0, speedRate0,
                          axis1, targetPos1, speedRate1,
                          axis2, targetPos2, speedRate2):
        """
        Function: 指定３軸を、各指定位置へ、各指定の速度率で移動します
        Arguments:
        axis0 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos0 - 目標位置（mm値）
        speedRate0 - システムパラメータにて設定された速度の速度率（％値：1～100）
        axis1 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos1 - 目標位置（mm値）
        speedRate1 - システムパラメータにて設定された速度の速度率（％値：1～100）
        axis2 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos2 - 目標位置（mm値）
        speedRate2 - システムパラメータにて設定された速度の速度率（％値：1～100）
        """
        self.motion_3axis_move_start(axis0, targetPos0, speedRate0,
                                     axis1, targetPos1, speedRate1,
                                     axis2, targetPos2, speedRate2)
        self.motion_wait_3axis_move_end(axis0, axis1, axis2)

    def motion_3axis_move_start(self, axis0, targetPos0, speedRate0,
                                axis1, targetPos1, speedRate1,
                                axis2, targetPos2, speedRate2):
        """
        Function: 指定３軸を、各指定位置へ、各指定の速度率で移動開始します
                  （移動完了を待ちません）
        Arguments:
        axis0 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos0 - 目標位置（mm値）
        speedRate0 - システムパラメータにて設定された速度の速度率（％値：1～100）
        axis1 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos1 - 目標位置（mm値）
        speedRate1 - システムパラメータにて設定された速度の速度率（％値：1～100）
        axis2 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        targetPos2 - 目標位置（mm値）
        speedRate2 - システムパラメータにて設定された速度の速度率（％値：1～100）
        """
        axisNo0 = int(axis0)
        if (axisNo0 < 0 or axis_type_class.axis_count <= axisNo0):
            return
        #
        axisNo1 = int(axis1)
        if (axisNo1 < 0 or axis_type_class.axis_count <= axisNo1):
            return
        #
        axisNo2 = int(axis2)
        if (axisNo2 < 0 or axis_type_class.axis_count <= axisNo2):
            return
        #
        if (axisNo0 == axisNo1) or (axisNo0 == axisNo2) or \
                (axisNo1 == axisNo2):
            return
        #
        Plslen0 = self.motion_class.convert_axis_mm_to_pulse(
                axisNo0, targetPos0)
        Speed0 = self.motion_class.convert_axis_speed_per_to_speed(
                axisNo0, speedRate0)
        #
        Plslen1 = self.motion_class.convert_axis_mm_to_pulse(
                axisNo1, targetPos1)
        Speed1 = self.motion_class.convert_axis_speed_per_to_speed(
                axisNo1, speedRate1)
        #
        Plslen2 = self.motion_class.convert_axis_mm_to_pulse(
                axisNo2, targetPos2)
        Speed2 = self.motion_class.convert_axis_speed_per_to_speed(
                axisNo2, speedRate2)
        #
        Result = self.motion_class.cmd_move_absolute(axisNo0, Plslen0, Speed0)
        if Result is False:
            # Error
            pass
        #
        Result = self.motion_class.cmd_move_absolute(axisNo1, Plslen1, Speed1)
        if Result is False:
            # Error
            pass
        #
        Result = self.motion_class.cmd_move_absolute(axisNo2, Plslen2, Speed2)
        if Result is False:
            # Error
            pass
        #
        return

    def motion_wait_3axis_move_end(self, axis0, axis1, axis2):
        """
        Function: 指定３軸移動完了を待ちます

        Arguments:
        axis0 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        axis1 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        axis2 - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        """
        ret = False

        time.sleep(0.1)

        while True:
            if (self.emg_getstat() is True):
                return False
            ret_str = self.motion_class.read_register(axis0, NOVA_Class.kRR3)
            if not ret_str == "":
                reg3_0 = 0x0000FFFF & int(ret_str)
                # reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16

                if (reg3_0 & NOVA_Class.kRR3_INPOS) == 0:
                    ret = True
                    break
                #
        while True:
            if (self.emg_getstat() is True):
                return False
            ret_str = self.motion_class.read_register(axis1, NOVA_Class.kRR3)
            if not ret_str == "":
                reg3_0 = 0x0000FFFF & int(ret_str)
                # reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16

                if (reg3_0 & NOVA_Class.kRR3_INPOS) == 0:
                    ret = True
                    break
                #
        while True:
            if (self.emg_getstat() is True):
                return False
            ret_str = self.motion_class.read_register(axis2, NOVA_Class.kRR3)
            if not ret_str == "":
                reg3_0 = 0x0000FFFF & int(ret_str)
                # reg3_1 = (0xFFFF0000 & int(ret_str)) >> 16

                if (reg3_0 & NOVA_Class.kRR3_INPOS) == 0:
                    ret = True
                    break
                #
        return ret

    def motion_getposition(self, axis):
        """
        Function: 指定の現在の位置情報を取得します

        Arguments:
        axis - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        """
        self.motion_class.get_axis_coord(axis)
        return (axis_sts_class[axis].abs_coord)

    def backup_homing_class(self):
        """
        Function: 原点復帰の情報を（一時的に）バックアップします
        """
        self.backup_home_is_end_list = \
            copy.deepcopy(homing_class.home_is_end_list)
        return

    def restore_homing_class(self):
        """
        Function: バックアップしていた原点復帰の情報をリストアします
        """
        homing_class.home_is_end_list = \
            copy.deepcopy(self.backup_home_is_end_list)
        return

    def motion_home(self):
        """
        Function: システムパラメータファイルに従って原点復帰させます
        """
        self.motion_home_start()
        self.motion_wait_home_end()
        return

    def motion_home_start(self):
        """
        Function: システムパラメータファイルに従って原点復帰開始します
        """
        homing_class.init()
        time.sleep(0.01)
        for loop in range(10):
            self.motion_class.order_homing()
            # time.sleep(0.01)
        return

    def motion_wait_home_end(self):
        """
        Function: 原点復帰完了を待ちます
        """
        Flag_HomeEnd = False
        while (Flag_HomeEnd is False):
            Flag_HomeEnd = self.motion_class.order_homing()
            time.sleep(0.01)
        #
        return

    def read_syspara_file(self):
        """
        Function: システムパラメータファイルを読み込みます
        """
        is_success, is_errmsg = self.file_prj_class.read_project_file()
        return is_success, is_errmsg

    def read_position_file(self):
        """
        Function: ポジションデータファイルを読み込みます
        """
        is_success, is_errmsg = self.file_pos_class.read_position_file()
        return is_success, is_errmsg

    def io_ex_input(self, portNo: int) -> int:
        """
        Function: I2C_IO入力ポートの状態を取得します

        Arguments:
        portNo - ポート番号（0..31）
        """
        if (0 <= portNo) and (portNo < 32):
            # readData = (self.stdio_class.expand_read_data_list[1] << 16) | \
            #    self.stdio_class.expand_read_data_list[0]
            readData = (self.motion_class.expand_read_data_list[1] << 16) | \
                self.motion_class.expand_read_data_list[0]
            if (readData & (1 << portNo) != 0):
                return 1
            else:
                return 0
        return 0

    def io_ex_output(self, portNo: int, onoff: bool) -> None:
        """
        Function: I2C_IO出力ポートへOn/Offを出力します

        Arguments:
        portNo - ポート番号（0..31）
        onoff - (ON=1 または True指定 / OFF=0 または False指定)
        """
        if (100 <= portNo) and (portNo < 116):
            # self.stdio_class.write_bit(0, (portNo-100), onoff)
            self.motion_class.write_bit(0, (portNo-100), onoff)
        elif (116 <= portNo) and (portNo < 132):
            # self.stdio_class.write_bit(1, (portNo-116), onoff)
            self.motion_class.write_bit(1, (portNo-116), onoff)

    def WaitStartSW_On(self):
        """
        Function: I2C_IOのSTARTSWがONになるのを待ちます
        """
        while (True):
            swStat = self.io_ex_input(2)
            # print ("Wait ON PinBlk[2]=", hex(swStat))
            if (swStat & const.DEFSwStat.StartSw1Sw2ON) == \
                    const.DEFSwStat.StartSw1Sw2ON:
                # print ("Wait ON PinBlk[2]=", hex(swStat))
                return True
            else:
                return False

    def WaitStartSW_Off(self):
        """
        Function: I2C_IOのSTARTSW1、2がOFFになるのを待ちます
        """
        while (True):
            swStat = self.io_ex_input(2)
            # print ("Wait ON PinBlk[2]=", hex(swStat))
            if (swStat & const.DEFSwStat.StartSw1Sw2ON) == 0:
                # print ("Wait ON PinBlk[2]=", hex(swStat))
                return True
            else:
                return False

    def ResetAllAxis(self):
        global axis_set_class

        for i in range(0, axis_type_class.axis_count):
            if axis_set_class[i].motor_type != \
               axis_maker_Class.kNone:
                self.motion_class.read_axis_io(i)

        self.motion_class.reset_all_axis()

        return

    # ---------------------------------------------------------------
    #
    # CAN-IO Class
    #
    # ---------------------------------------------------------------
    def canio_init(self):
        """
        Function: CAN-IO制御を初期化
        """
        stat = self.canio_class.initialize_can()
        if (stat):
            self.canio_class.start_canio_thread()
        return stat

    def stop_canio_thread(self):
        """
        Function: CAN-IO制御のスレッドを停止させます
        """
        self.canio_class.stop_canio_thread()

    def canio_input(self, boardId, portNo):
        """
        Function: CAN-IOボードのポート状態を取得します

        Arguments:
        boardId - CAN-IOボードのID(0..15)：ボードのデジスイッチの値
        portNo – ボード内のポート番号(0..31)
        """
        return self.canio_class.input(boardId, portNo)

    def canio_inputInt(self, boardId):
        """
        Function: CAN-IOボードのポート状態を一括取得します

        Arguments:
        boardId - CAN-IOボードのID(0..15)：ボードのデジスイッチの値
        """
        return self.canio_class.inputInt(boardId)

    def canio_output(self, boardId, portNo, onoff):
        """
        Function: CAN-IOボードのポートへOn/Off出力します

        Arguments:
        boardId - CAN-IOボードのID(0..15)：ボードのデジスイッチの値
        portNo – ボード内のポート番号(0..31)
        onoff - (ON=1 または True指定 / OFF=0 または False指定)
        """
        return self.canio_class.output(boardId, portNo, onoff)

    # ---------------------------------------------------------------
    # EMGスイッチ 監視処理
    # ---------------------------------------------------------------]
    Flag_chk_emg_thread = False
    Stat_EMG_prev = 1
    Stat_EMG_now = 1
    EMG_callback = None  # Non_EMG_callback

    def Non_EMG_callback(self, info):
        """
        Function: EMGスイッチcallbackが設定されていない時のダミーのCallBack関数
        """
        # print("Non_EMG_callback__", info)
        return

    def handler(self, func, *args):
        return func(*args)

    def emg_setcallback(self, objname):
        """
        Function: EMGスイッチcallback関数にユーザー指定の関数をセット

        Arguments:
        objname - ユーザー指定の関数
        """
        self.EMG_callback = objname
        return

    def emg_clrcallback(self):
        """
        Function: EMGスイッチcallback関数の設定をクリア
        """
        self.EMG_callback = None
        return

    def emg_getstat(self):
        """
        Function: EMGスイッチの状態を返す
        """
        statNow = self.Stat_EMG_now
        if (statNow):
            return True
        else:
            return False

    def chk_emg_thread_proc(self):
        """
        Function: EMGスイッチの状態を監視するスレッド
                  EMGスイッチがOff->Onとなったら、callback関数をcallする
        """
        while (self.Flag_chk_emg_thread):
            #
            self.Stat_EMG_now = GPIO.input(gpio_class.kEmergencyBtn)
            if (self.Stat_EMG_prev == 0) and (self.Stat_EMG_now == 1):
                #
                try:
                    if (self.EMG_callback is not None):
                        self.handler(self.EMG_callback, "Call User Method")
                    else:
                        self.Non_EMG_callback("No set Callback")
                except ArithmeticError as e:
                    print(e)
                    print(type(e))
                    #
            #
            self.Stat_EMG_prev = self.Stat_EMG_now
            #
            time.sleep(0.005)
            #
            # Go to Loop
        #
        # Quit Chk EMG thread Loop
        # print("Quit ChK_EMG_Thread_Loop")

    def start_chk_EMG_thread(self):
        """
        Function: EMGスイッチ監視スレッド（chk_emg_thread_proc）を起動する
        """
        # global Non_EMG_callback
        # self.emg_setcallback(self.Non_EMG_callback)
        if (self.Flag_chk_emg_thread is False):
            self.Flag_chk_emg_thread = True
            #
            self.chk_emg_thread = threading.Thread(
                target=self.chk_emg_thread_proc)
            self.chk_emg_thread.start()
            # self.chk_emg_thread.join()
        #
        # Quit Chk EMG Thread

    def stop_chk_EMG_thread(self):
        """
        Function: EMGスイッチ監視スレッド（chk_emg_thread_proc）を停止する
        """
        self.Flag_chk_emg_thread = False
        self.chk_emg_thread.join()
        #
        # Wait quit Chk EMG Thread

    def get_system_parameter_value(self, axis, sys_type):
        """
        Function: システムパラメータを取得する

        Arguments:
        axis - 軸番号（0=Ｘ軸、1=Ｙ軸、2=Ｚ軸．．．
        obsys_typejname - システムパラメータ内の情報箇所
        """
        global axis_set_class

        if sys_type == axis_setting_type_class.kMax_speed:
            return axis_set_class[axis].max_speed
        elif sys_type == axis_setting_type_class.kMax_accel:
            return axis_set_class[axis].max_accel
        elif sys_type == axis_setting_type_class.kMax_decel:
            return axis_set_class[axis].max_decel
        elif sys_type == axis_setting_type_class.kStart_speed:
            return axis_set_class[axis].start_speed
        elif sys_type == axis_setting_type_class.kOffset_speed:
            return axis_set_class[axis].offset_speed
        elif sys_type == axis_setting_type_class.kOrigin_speed:
            return axis_set_class[axis].origin_speed
        elif sys_type == axis_setting_type_class.kOrigin_offset:
            return axis_set_class[axis].origin_offset
        elif sys_type == axis_setting_type_class.kLimit_plus:
            return axis_set_class[axis].limit_plus
        elif sys_type == axis_setting_type_class.kLimit_minus:
            return axis_set_class[axis].limit_minus
        elif sys_type == axis_setting_type_class.kPulse_length:
            return axis_set_class[axis].pulse_length
        elif sys_type == axis_setting_type_class.kOrigin_order:
            return axis_set_class[axis].origin_order
        elif sys_type == axis_setting_type_class.kOrigin_dir:
            return axis_set_class[axis].origin_dir
        elif sys_type == axis_setting_type_class.kOrigin_sensor:
            value_list = [item for item in origin_type_list if item.strip()]
            for i in range(0, len(value_list)):
                if axis_set_class[axis].origin_sensor_name == value_list[i]:
                    return i
        elif sys_type == axis_setting_type_class.kIn_position:
            return axis_set_class[axis].in_position
        elif sys_type == axis_setting_type_class.kMotor_type:
            value_list = [item for item in maker_type_list if item.strip()]
            for i in range(0, len(value_list)):
                if axis_set_class[axis].motor_type_name == value_list[i]:
                    return i
        return 0

    def init_gpio(self):
        """
        Function: GPIO初期化
        """
        # RPi.GPIO の警告を抑止（既に使用中のチャネルに対する警告）
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_class.kNova_reset_pin, GPIO.OUT)
        GPIO.setup(gpio_class.kNova_Power_pin, GPIO.OUT)
        GPIO.setup(gpio_class.kCan_CS_pin, GPIO.OUT)
        GPIO.setup(gpio_class.kEmergencyBtn, GPIO.IN)

    def gpio_on_off(self, pin_no, onoff):
        """
        Function: GPIOへOn/Off出力

        Arguments:
        pin_no - GPIOのピン番号
        onoff - (ON=1 または True指定 / OFF=0 または False指定)
        """
        if onoff:
            GPIO.output(pin_no, GPIO.HIGH)
        else:
            GPIO.output(pin_no, GPIO.LOW)

    def gpio_read(self, pin_no):
        """
        Function: GPIOの状態を取得

        Arguments:
        pin_no - GPIOのピン番号
        """
        input_state = GPIO.input(pin_no)
        if input_state == GPIO.HIGH:
            return True
        else:
            return False

    def program_close(self):
        """
        Function: GPIOをclose
        """
        GPIO.cleanup()

    # *********************************************************************
    # GUI interface Class : gui_ctrl
    # Explanation : GUI control
    # Project Name : Table Robot
    # ----------------------------------------------------------------------
    # History :
    #           ver0.0.1 2024.11.02 New Create
    # *********************************************************************#

    # - Define import/from -------------------------------------------------
    # import os
    # import time
    # # import math
    # import mmap
    # # import threading
    # from threading import Thread
    # import constant as const

    # - Variable -----------------------------------------------------------
    # G_DataToGUI = bytearray(bcytes(10))
    # G_DataToGUI = bytearray([0,0,0,0,0,0,0,0,0,0])

    # - Class --------------------------------------------------------------
    # class IOFileClass:
    # ----------------------------------------------------------------------
    #
    IO_FILE_FOLDER_PASS = "/home/splebopi/SPLEBO/MONITOR/temp/"
    OUT_FILE_NAME = "ToPyIO.dat"
    IN_FILE_NAME = "ToCIO.dat"
    OUT_FILE_SIZE = 10
    IN_FILE_SIZE = 8

    send_mmap = 0
    recv_mmap = 0

    def __init__gui(self):
        """
        Function: GUI_IFの初期化
        """
        global G_DataToGUI
        # python MMAP -> MONITOR
        # filePath = self.IO_FILE_FOLDER_PASS
        # path = os.path.join(os.getcwd(), "temp", self.OUT_FILE_NAME)
        path = os.path.join(self.IO_FILE_FOLDER_PASS, self.OUT_FILE_NAME)
        # os.remove(path)
        if os.path.exists(path) is False:
            self.createMMapFile(path, self.OUT_FILE_SIZE)

        with open(path, "r+b") as s:
            # 共有メモリ作成
            self.send_mmap = mmap.mmap(s.fileno(), self.OUT_FILE_SIZE,
                                       access=mmap.ACCESS_WRITE)

        # クリア
        # G_DataToGUI = b'\00\00\00\00\00\00\00\00\00\00'
        self.SendOutputFieldToC(G_DataToGUI)

        # G_DataToGUI[2] = G_DataToGUI[2] | const.Bit.BitOn3
        # print ("G_DataToGUI[2] | const.Bit.BitOn3 = ", hex(G_DataToGUI[2]))


        # MONITOR -> python
        # path = os.path.join(os.getcwd(),  "temp", self.IN_FILE_NAME)
        path = os.path.join(self.IO_FILE_FOLDER_PASS, self.IN_FILE_NAME)
        # os.remove(path)
        if os.path.exists(path) is False:
            self.createMMapFile(path, self.IN_FILE_SIZE)

        with open(path, "r+b") as s:
            # 共有メモリ作成
            self.recv_mmap = mmap.mmap(s.fileno(), self.IN_FILE_SIZE,
                                       access=mmap.ACCESS_WRITE)

    def createMMapFile(self, path, size):
        with open(path, mode="wb") as file:
            initStr = '00' * size
            initByte = bytes.fromhex(initStr)
            file.write(initByte)

        # print("_createMMapFile end.")

    def SendOutputFieldToC(self, data):
        """
        Function: GUI_IFの通信ファイルへの送信（書込み）

        Arguments:
        pin_no - 送信データ
        """
        # バイナリ変換
        write_data = data

        # データ書き込み
        self.send_mmap.seek(0)
        self.send_mmap.write(write_data)

    def ReceiveInputFieldFromC(self):
        """
        Function: GUI_IFの通信ファイルの読込み
        """
        self.recv_mmap.seek(0)
        read_data = self.recv_mmap.read(self.IN_FILE_SIZE)
        return read_data

    def CloseMMAPFile(self):
        """
        Function: GUI_IFのClose
        """
        self.send_mmap.close()
        self.recv_mmap.close()

    # ---------------------------------------------------------------
    def Chk_GUI_HomeSw(self):
        """
        Function: ＧＵＩ画面のHomeSw状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[1] & const.Bit.BitOn2)

    def Chk_GUI_StartSw(self):
        """
        Function: ＧＵＩ画面のSTARTSw状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[1] & const.Bit.BitOn1)

    def Chk_GUI_StopSw(self):
        """
        Function: ＧＵＩ画面のSTOPSw状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[0] & const.Bit.BitOn1)

    def Chk_GUI_ResetSw(self):
        """
        Function: ＧＵＩ画面のRESETSw状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[0] & const.Bit.BitOn2)

    def chk_GUI_ProgNo(self):
        """
        Function: ＧＵＩ画面のProgramNo値を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        itemp = int(G_ReqData[2])
        progNo = ((itemp >> 4) * 10) + (itemp & 0x0f)
        return (progNo)

    def Chk_GUI_SW1(self):
        """
        Function: ＧＵＩ画面のSW1状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[0] & const.Bit.BitOn0)

    def Chk_GUI_SW2(self):
        """
        Function: ＧＵＩ画面のSW2状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[0] & const.Bit.BitOn3)

    def Chk_GUI_SW3(self):
        """
        Function: ＧＵＩ画面のSW3状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[1] & const.Bit.BitOn0)

    def Chk_GUI_SW4(self):
        """
        Function: ＧＵＩ画面のSW4状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[1] & const.Bit.BitOn3)

    def Chk_GUI_SW5(self):
        """
        Function: ＧＵＩ画面のSW5状態を取得します
        """
        global G_ReqData
        G_ReqData = self.ReceiveInputFieldFromC()
        return (G_ReqData[1] & const.Bit.BitOn4)

    # ---------------------------------------------------------------

# class GUIRespFileClass:
    #
    # G_DataToGUI = bytearray(bytes(10))

    # def SendOutputFieldToC(sendData):
    #    return self.IoFileCls.SendOutputFieldToC(sendData)

    def setGUILampALLOff(self):
        """
        Function: ＧＵＩ画面のインジケータを全てOFFします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[0] = 0
        G_DataToGUI[1] = 0
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOffRDYALMHOME(self):
        """
        Function: ＧＵＩ画面のHOMEランプをOFFします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff012
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampRDY(self, OnOff):
        """
        Function: ＧＵＩ画面のRDYランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn0
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff0
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOnRDYonly(self):
        """
        Function: ＧＵＩ画面のRDYランプをONします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[0] = G_DataToGUI[0] & (const.Bit.BitOff012) |\
            const.Bit.BitOn0
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampALM(self, OnOff):
        """
        Function: ＧＵＩ画面のALMランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn1
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff1
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOnALMonly(self):
        """
        Function: ＧＵＩ画面のRDYランプをONします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[0] = (G_DataToGUI[0] & (const.Bit.BitOff012)) |\
            const.Bit.BitOn1
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampHOME(self, OnOff):
        """
        Function: ＧＵＩ画面のHOMEランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn2
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff2
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOnHOMEonly(self):
        """
        Function: ＧＵＩ画面のRDYランプをONします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[0] = (G_DataToGUI[0] & (const.Bit.BitOff012)) |\
            const.Bit.BitOn2
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOPT1(self, OnOff):
        """
        Function: ＧＵＩ画面のOPT1ランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn3
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff3
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOPT2(self, OnOff):
        """
        Function: ＧＵＩ画面のOPT2ランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn4
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff4
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOPT3(self, OnOff):
        """
        Function: ＧＵＩ画面のOPT3ランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn5
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff5
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOPT4(self, OnOff):
        """
        Function: ＧＵＩ画面のOPT4ランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn6
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff6
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOPT5(self, OnOff):
        """
        Function: ＧＵＩ画面のOPT5ランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[0] = G_DataToGUI[0] | const.Bit.BitOn7
        else:
            G_DataToGUI[0] = G_DataToGUI[0] & const.Bit.BitOff7
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOPT6(self, OnOff):
        """
        Function: ＧＵＩ画面のOPT6ランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn0
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff0
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOPT7(self, OnOff):
        """
        Function: ＧＵＩ画面のOPT7ランプをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn1
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff1
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampHOMESW(self, OnOff):
        """
        Function: ＧＵＩ画面のHOME SWをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn2
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff2
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOnHOMESWonly(self):
        """
        Function: ＧＵＩ画面のHOME SWをONします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[1] = (G_DataToGUI[1] & (const.Bit.BitOff2345)) |\
            const.Bit.BitOn2
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSTARTSW(self, OnOff):
        """
        Function: ＧＵＩ画面のSTART SWをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn3
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff3
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSTART_RESETSW(self, OnOff):
        """
        Function: ＧＵＩ画面のSTART,RESET SWをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] |\
                (const.Bit.BitOn5 | const.Bit.BitOn3)
        else:
            G_DataToGUI[1] = G_DataToGUI[1] &\
                (const.Bit.BitOff5 & const.Bit.BitOff3)
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOnSTARTSWonly(self):
        """
        Function: ＧＵＩ画面のSTART SWをONします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[1] = (G_DataToGUI[1] & (const.Bit.BitOff2345)) |\
            const.Bit.BitOn3
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSTOPSW(self, OnOff):
        """
        Function: ＧＵＩ画面のSTOP SWをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn4
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff4
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOnSTOPSWonly(self):
        """
        Function: ＧＵＩ画面のSTOP SWをON/OFFします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[1] = (G_DataToGUI[1] & (const.Bit.BitOff2345)) |\
            const.Bit.BitOn4
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampRESETSW(self, OnOff):
        """
        Function: ＧＵＩ画面のRESET SWをON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn5
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff5
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampOnRESETSWonly(self):
        """
        Function: ＧＵＩ画面のRESET SWをONします
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[1] = (G_DataToGUI[1] & (const.Bit.BitOff2345)) |\
            const.Bit.BitOn5
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSW1(self, OnOff):
        """
        Function: ＧＵＩ画面のSW1をON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn6
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff6
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSW2(self, OnOff):
        """
        Function: ＧＵＩ画面のSW2をON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[1] = G_DataToGUI[1] | const.Bit.BitOn7
        else:
            G_DataToGUI[1] = G_DataToGUI[1] & const.Bit.BitOff7
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSW3(self, OnOff):
        """
        Function: ＧＵＩ画面のSW3をON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[2] = G_DataToGUI[2] | const.Bit.BitOn0
        else:
            G_DataToGUI[2] = G_DataToGUI[2] & const.Bit.BitOff0
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSW4(self, OnOff):
        """
        Function: ＧＵＩ画面のSW4をON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[2] = G_DataToGUI[2] | const.Bit.BitOn1
        else:
            G_DataToGUI[2] = G_DataToGUI[2] & const.Bit.BitOff1
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSW5(self, OnOff):
        """
        Function: ＧＵＩ画面のSW5をON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[2] = G_DataToGUI[2] | const.Bit.BitOn2
        else:
            G_DataToGUI[2] = G_DataToGUI[2] & const.Bit.BitOff2
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUILampSW10(self, OnOff):
        """
        Function: ＧＵＩ画面のSW10をON/OFFします

        Arguments:
        OnOff - On=1またはTrue ／ Off=0またはFalse
        """
        global G_DataToGUI
        time.sleep(0.001)
        if (OnOff):
            G_DataToGUI[2] = G_DataToGUI[2] | const.Bit.BitOn3
        else:
            G_DataToGUI[2] = G_DataToGUI[2] & const.Bit.BitOff3
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    def setGUI7SegOff(self, no):
        """
        Function: ＧＵＩ画面の7セグをOFFします

        Arguments:
        no - 0=1行目1桁目、1=1行目2桁目、2=1行目3桁目、
             3=2行目1桁目、4=2行目2桁目、5=2行目3桁目
        """
        global G_DataToGUI
        time.sleep(0.001)
        G_DataToGUI[3 + no] = 0x80
        # バイナリファイルへの書き込み
        return self.SendOutputFieldToC(G_DataToGUI)

    blinkTime = 0
    blinkBitTbl = [0, 0, 0]
    blinkSatrtStop = 0
    blinkLastLamp = 0

    def StartBlinkLED(self, LedNo, interval):
        """
        Function: ＧＵＩ画面のインジケータを点滅開始します

        Arguments:
        LedNo - インジケータのデータ（3バイト）
        interval - 点滅のインターバル
        """
        #
        self.blinkBitTbl[0] = LedNo[0]
        self.blinkBitTbl[1] = LedNo[1]
        self.blinkBitTbl[2] = LedNo[2]
        self.blinkTime = int(interval / 0.005) + 1
        #
        self.blinkSatrtStop = 1
        led_blink_func_thred = Thread(target=self.ledBlinkLoop)
        led_blink_func_thred.start()

    def ledBlinkLoop(self):
        """
        Function: ＧＵＩ画面のインジケータを点滅させるスレッド
        """
        global G_DataToGUI
        while True:
            if (self.blinkSatrtStop == 0):
                break
            # ledを点滅する処理を入れる
            G_DataToGUI[0] = G_DataToGUI[0] ^ self.blinkBitTbl[0]
            G_DataToGUI[1] = G_DataToGUI[1] ^ self.blinkBitTbl[1]
            G_DataToGUI[2] = G_DataToGUI[2] ^ self.blinkBitTbl[2]
            self.SendOutputFieldToC(G_DataToGUI)
            #
            for i in range(self.blinkTime):
                time.sleep(0.0045)
                if (self.blinkSatrtStop == 0):
                    break
        #
        self.led_blink_func_thred = None
        #
        if (self.blinkLastLamp == 1):
            # 点灯状態で点滅終わり
            G_DataToGUI[0] = G_DataToGUI[0] | self.blinkBitTbl[0]
            G_DataToGUI[1] = G_DataToGUI[1] | self.blinkBitTbl[1]
            G_DataToGUI[2] = G_DataToGUI[2] | self.blinkBitTbl[2]
        else:
            # 消灯状態で点滅終わり
            G_DataToGUI[0] = G_DataToGUI[0] & ~(self.blinkBitTbl[0])
            G_DataToGUI[1] = G_DataToGUI[1] & ~(self.blinkBitTbl[1])
            G_DataToGUI[2] = G_DataToGUI[2] & ~(self.blinkBitTbl[2])
        #
        self.SendOutputFieldToC(G_DataToGUI)
        return

    def StopBlinkLED(self, lastlamp):
        """
        Function: ＧＵＩ画面のインジケータを点滅停止させます

        Arguments:
        lastlamp - 点滅停止後の状態（1=点灯／0=消灯）
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = lastlamp
        time.sleep(0.01)

    def BlinkStartLampHOMESW(self):
        """
        Function: ＧＵＩ画面のHOME SWを点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 4, 0], 0.5)

    def BlinkStartLampHOME(self):
        """
        Function: ＧＵＩ画面のHOMEランプを点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([4, 0, 0], 0.5)

    def BlinkStartLampSTARTSW(self):
        """
        Function: ＧＵＩ画面のSTART SWを点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 8, 0], 0.5)

    def BlinkStartLampSTOPSW(self):
        """
        Function: ＧＵＩ画面のSTOP SWを点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0x10, 0], 0.5)

    def BlinkStartLampRESETSW(self):
        """
        Function: ＧＵＩ画面のRESET SWを点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0x20, 0], 0.5)

    def BlinkStartLampSW1(self):
        """
        Function: ＧＵＩ画面のSW1を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0x40, 0], 0.5)

    def BlinkStartLampSW2(self):
        """
        Function: ＧＵＩ画面のSW2を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0x80, 0], 0.5)

    def BlinkStartLampSW3(self):
        """
        Function: ＧＵＩ画面のSW3を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0, 1], 0.5)

    def BlinkStartLampSW4(self):
        """
        Function: ＧＵＩ画面のSW4を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0, 2], 0.5)

    def BlinkStartLampSW5(self):
        """
        Function: ＧＵＩ画面のSW5を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0, 4], 0.5)

    def BlinkStartLampOPT1(self):
        """
        Function: ＧＵＩ画面のOPT1を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0x08, 0, 0], 0.5)

    def BlinkStartLampOPT2(self):
        """
        Function: ＧＵＩ画面のOPT2を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0x10, 0, 0], 0.5)

    def BlinkStartLampOPT3(self):
        """
        Function: ＧＵＩ画面のOPT3を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0x20, 0, 0], 0.5)

    def BlinkStartLampOPT4(self):
        """
        Function: ＧＵＩ画面のOPT4を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0x40, 0, 0], 0.5)

    def BlinkStartLampOPT5(self):
        """
        Function: ＧＵＩ画面のOPT5を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0x80, 0, 0], 0.5)

    def BlinkStartLampOPT6(self):
        """
        Function: ＧＵＩ画面のOPT6を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0x01, 0], 0.5)

    def BlinkStartLampOPT7(self):
        """
        Function: ＧＵＩ画面のOPT7を点滅開始します
        """
        self.blinkSatrtStop = 0
        self.blinkLastLamp = 0
        time.sleep(0.01)
        self.StartBlinkLED([0, 0x02, 0], 0.5)

    def Disp7SegLine1(self, msg3char: list[int]):
        """
        Function: ＧＵＩ画面の７セグ１行目に表示します

        Arguments:
        msg3char - ７セグの表示データ３バイト
        """
        global G_DataToGUI
        #
        G_DataToGUI[3] = msg3char[0]
        G_DataToGUI[4] = msg3char[1]
        G_DataToGUI[5] = msg3char[2]
        self.SendOutputFieldToC(G_DataToGUI)

    def Disp7SegLine2(self, msg3char: list[int]) -> None:
        """
        Function: ＧＵＩ画面の７セグ２行目に表示します

        Arguments:
        msg3char - ７セグの表示データ３バイト
        """
        global G_DataToGUI
        #
        G_DataToGUI[6] = msg3char[0]
        G_DataToGUI[7] = msg3char[1]
        G_DataToGUI[8] = msg3char[2]
        self.SendOutputFieldToC(G_DataToGUI)

# ---------END OF CODE--------- #


# -------------------------------------------------------------------
# Method outof splebo_n class
# -------------------------------------------------------------------
def bit_check(data, bit_pos):
    if data & bit_pos:
        return True
    else:
        return False

# ---------END OF CODE--------- #
