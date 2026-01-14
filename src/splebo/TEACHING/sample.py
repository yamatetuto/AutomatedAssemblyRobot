# *********************************************************************#
# File Name : sample.py
# Explanation : Sample Program for splebo_n Library
# Project Name : Sample SPLEBO N
# ----------------------------------------------------------------------
# History :
#            ver0.0.1 2024.10.24 New Create
# *********************************************************************#

# - Define import/from -------------------------------------------------
# import sys
# import os
# import enum
from enum import Enum
# import threading
# from threading import Thread
import time
# import copy
# import math
# import file_ctrl as filectl
# import motion_control as motion_ctl
# import io_expander as io_ex
import splebo_n
import constant as const

# - Variable -----------------------------------------------------------
spleboClass = None  # splebon()
BlinkNo = 0
NextBlinkTime = time.time()
# Define ------------------------------------------------------------
DEF_axX = 1
DEF_axY = 2
DEF_axXY = 3
DEF_axZ = 4
DEF_axXZ = 5
DEF_axYZ = 6
DEF_axXYZ = 7


ErrNo7Seg: list[int]


class EnumLoopState(Enum):
    # 原点復帰初期化
    HomeInit = 0
    # 原点復帰待機
    HomeWait = 1
    # 原点復帰中
    Homing = 2
    # 選択初期化
    SelectInit = 3
    # 選択待ち
    SelectLoop = 4
    # Start待ち
    StartWait = 5
    # ねじ取り
    ScrewPickup = 6
    # ねじ締め
    ScrewTight = 7
    # スタート位置移動
    MoveStartPos = 8
    # ワーク取り出し
    WorkPickCheck = 9
    # エラー
    Error = 10
    # リセット
    Reset = 11


class EnumStartState(Enum):
    # ワークロックOFF
    WorkLockOff = 0
    # ワークありチェック
    WorkRemoveCheck = 1
    # ドライバーUPチェック
    DriverUpCheck = 2
    # ねじガイドチェック
    ScrewGuideCheck = 3
    # スタート待ち
    StartWait = 4


# StartWaitステータス
StartWaitState: EnumStartState = EnumStartState.WorkLockOff


# 初期テータス
class EnumReturnStatus(Enum):
    # Errorなし
    NonError = 0
    # スタートボタンON
    StartOn = 1
    # SW5 ON
    SW5On = 2
    # ワークなし
    NoWork = 3
    # ドライバーUP
    NoDriverUp = 4
    # ガイドオープン
    NoScrewGuideOpen = 5
    # プログラムエラー
    ProgramError = 6


# ねじ取りステータス
class EnumScrewPickupState(Enum):
    # ねじ取り上空
    ScrewPickupUpper = 1
    # ネジ無しチェック
    # ネジ吸着OFF
    ScrewNonCheck = 2
    # フィーダーネジチェック
    FeederScrewCheck = 3
    # ガイドオープン
    # ガイドオープン確認
    GuideOpenCheck = 4
    # 吸着ON
    # 回転ON
    # シリンダON
    # 回転確認
    RotateCheck = 5
    # ねじ取り下降
    ScrewPickupDown = 6
    # シリンダON確認
    # 300ms Wait
    SylinderOnCheck = 7
    # 回転OFF
    # シリンダOFF
    # ねじ取り上空
    ScrewPickupUp = 8
    # シリンダOFF確認
    SylinderOffCheck = 9
    # ガイドクローズ
    # ガイドクローズ確認
    # 100ms Wait
    GuideCloseCheck = 10
    # ねじあり確認
    ScrewPickupSuccessCheck = 11
    # ねじ取り終了
    ScrewPickupFinish = 100


# ねじ取りステータス
ScrewPickupState: EnumScrewPickupState = EnumScrewPickupState.ScrewPickupUpper


# ねじ取りエラー
class EnumScrewPickupError(Enum):
    # Errorなし
    NonError = 0
    # ネジあり
    ScrewYes = 1
    # フィーダーネジ無し
    FeederScrewNon = 2
    # ガイドオープン
    GuideOpen = 3
    # 回転停止
    RotateStop = 4
    # シリンダー下降
    SylinderDown = 5
    # シリンダー上昇
    SylinderUp = 6
    # ガイドクローズ
    GuideClose = 7
    # ねじ無し
    ScrewNo = 8


# ねじ締めステータス
class EnumScrewTightState(Enum):
    # ねじ締め上空
    ScrewTightUpper = 1
    # 変位センサーリセット ON
    # 20ms
    # 変位センサーリセット OFF
    DisplacementSensorReset = 2
    # ねじあり確認
    # ガイドオープン
    # ガイドオープン確認
    # シリンダON
    GuideOpenCheck = 3
    # ねじ締め下降
    # 回転ON
    # トルクアップ OFF確認
    # シリンダ 上OFF確認
    ScrewTightDown = 4
    # トルクアップ ON確認
    # バキュームOFF
    # 回転OFF
    TorqueUpCheck = 5
    # Timing信号 ON
    # 20ms Wait
    # Timing信号 OFF
    # 10ms Wait
    # High信号エラー
    # Low信号エラー
    # OK信号エラー
    # シリンダOFF
    DisplacementSensorTiming = 6
    # Z軸上昇
    ZAxisUp = 7
    # シリンダOFF確認
    SylinderOffCheck = 8
    # ガイドクローズ
    # ガイドクローズ確認
    GuideCloseCheck = 9
    # ねじ締め終了
    ScrewTightFinish = 100


# ねじ締めステータス
ScrewTightState: EnumScrewTightState = EnumScrewTightState.ScrewTightUpper


# ねじ締めエラー
class EnumScrewTightError(Enum):
    # Errorなし
    NonError = 0
    # ねじあり
    ScrewNo = 1
    # ガイドオープン
    GuideOpen = 2
    # トルクアップ OFF
    TorqueOFF = 3
    # シリンダー上昇
    SylinderUp = 4
    # トルクアップ ON
    TorqueON = 5
    # High信号エラー
    HighError = 6
    # Low信号エラー
    LowError = 7
    # OK信号エラー
    OKErrror = 8
    # シリンダー下降
    SylinderDown = 9
    # ガイドクローズ
    GuideClose = 10


class OutPort(Enum):
    # ドライバー上下SV
    OUT00_DriverSV = 100
    # Non
    OUT01 = 101
    # ネジガイド開閉SV
    OUT02_ScrewGuide = 102
    # Non
    OUT03 = 103
    # ネジ吸着SV
    OUT04_ScrewVacuum = 104
    # Non
    OUT05 = 105
    # 変位センサーTiming信号
    OUT06_DS_Timing = 106
    # 変位センサーReset信号
    OUT07_DS_Reset = 107
    # Non
    OUT08 = 108
    # 電動ドライバーON/OFF
    OUT09_Driver = 109
    # ワークロック
    OUT10_WorkLock = 110
    # Non
    OUT11 = 111
    # 非常停止LED
    OUT12_EMGLed = 112
    # スタート左LED
    OUT13_StartLeft = 113
    # スタート右LED
    OUT14_StartRight = 114
    # ブザー
    OUT15_Buzzer = 115


class InPort(Enum):
    # ドライバー上下CY 原点：上
    IN00_DriverSV_Up = 0
    # ドライバー上下CY 移動端：下
    IN01_DriverSV_Down = 1
    # ネジガイド開閉CY 原点：閉
    IN02_ScrewGuide_Close = 2
    # ネジガイド開閉CY 移動端：開
    IN03_ScrewGuide_Open = 3
    # ネジ有無検出
    IN04_ScrewDetect = 4
    # フィーダーネジ検出
    IN05_FeederScrew = 5
    # 変位センサーHigh信号
    IN06_DS_High = 6
    # 変位センサーOK信号
    IN07_DS_OK = 7
    # 変位センサーLOW信号
    IN08_DS_LOW = 8
    # 電動ドライバートルクアップ
    IN09_DriverTorqueUp = 9
    # ワークロック　原点：解除
    IN10_WorkLock_Org = 10
    # ワークロック　移動端：ロック
    IN11_WorkLock_Lock = 11
    # ワーク有無検出
    IN12_WorkEnable = 12
    # スタート左SW
    IN13_StartLeftSW = 13
    # スタート右SW
    IN14_StartRightSW = 14
    # Non
    IN15 = 15


def EMG_callback(msg: str):
    print("EMG Sw is ON!!!!!!")
    return


def BlinkStartSw1Sw2():
    global spleboClass
    global BlinkNo
    global NextBlinkTime
    #
    if (time.time() > NextBlinkTime):
        if (BlinkNo == 0):
            BlinkNo = 1
            spleboClass.io_ex_output(OutPort.OUT13_StartLeft.value, True)  # type: ignore
            # time.sleep(0.01)
            spleboClass.io_ex_output(OutPort.OUT14_StartRight.value, True)  # type: ignore
            # time.sleep(0.01)
        else:
            BlinkNo = 0
            spleboClass.io_ex_output(OutPort.OUT13_StartLeft.value, False)  # type: ignore
            # time.sleep(0.01)
            spleboClass.io_ex_output(OutPort.OUT14_StartRight.value, False)  # type: ignore
            # time.sleep(0.01)
        #
        NextBlinkTime = time.time() + 0.5


def BlinkStopSw1Sw2():
    global spleboClass
    #
    spleboClass.io_ex_output(OutPort.OUT13_StartLeft.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT14_StartRight.value, False)   # type: ignore


def DebugWait():
    time.sleep(2)


def WaitInput(portNo: int, expect: int = 1, timeout_ms: int = 500) -> bool:
    """
    指定ポートが expect(0 or 1) の状態になるまで待つ
    timeout_ms ミリ秒でタイムアウト
    """
    global spleboClass

    t0 = time.time()
    timeout = timeout_ms / 1000.0
    while time.time() - t0 < timeout:
        val = spleboClass.io_ex_input(portNo)  # type: ignore
        if val == expect:
            return True
        time.sleep(0.005)

    return False


def InitOutput() -> None:
    global spleboClass

    spleboClass.io_ex_output(OutPort.OUT00_DriverSV.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT02_ScrewGuide.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT04_ScrewVacuum.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT06_DS_Timing.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT07_DS_Reset.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT09_Driver.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT10_WorkLock.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT12_EMGLed.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT13_StartLeft.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT14_StartRight.value, False)  # type: ignore
    spleboClass.io_ex_output(OutPort.OUT15_Buzzer.value, False)  # type: ignore


def NotificationBuzzer() -> None:
    global spleboClass

    spleboClass.io_ex_output(OutPort.OUT15_Buzzer.value, True)  # type: ignore
    time.sleep(0.15)
    spleboClass.io_ex_output(OutPort.OUT15_Buzzer.value, False)  # type: ignore


def StartWaitProc() -> EnumReturnStatus:
    global spleboClass
    global StartWaitState
    global ErrNo7Seg

    ret: EnumReturnStatus = EnumReturnStatus.NonError

    # print("StartWaitState = ", StartWaitState)
    if (StartWaitState == EnumStartState.WorkLockOff):
        # ワークロックOFF
        spleboClass.io_ex_output(OutPort.OUT10_WorkLock.value, False)  # type: ignore
        StartWaitState = EnumStartState.WorkRemoveCheck
    elif (StartWaitState == EnumStartState.WorkRemoveCheck):
        # ワーク有り無し確認
        if (WaitInput(InPort.IN12_WorkEnable.value, 1, 100)):
            StartWaitState = EnumStartState.DriverUpCheck
        else:
            spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_3MINUS)  # type: ignore
            ret = EnumReturnStatus.NoWork
    elif (StartWaitState == EnumStartState.DriverUpCheck):
        # ドライバー原点確認
        if (WaitInput(InPort.IN00_DriverSV_Up.value, 1, 100)
                and WaitInput(InPort.IN01_DriverSV_Down.value, 0, 100)):
            StartWaitState = EnumStartState.ScrewGuideCheck
        else:
            ErrNo7Seg = const.Led7SegClass.SEG_E27
            ret = EnumReturnStatus.NoDriverUp
    elif (StartWaitState == EnumStartState.ScrewGuideCheck):
        # ガイド原点確認
        if (WaitInput(InPort.IN02_ScrewGuide_Close.value, 1, 100)
                and WaitInput(InPort.IN03_ScrewGuide_Open.value, 0, 100)):

            spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_RDY)  # type: ignore
            spleboClass.setGUILampRDY(1)  # type: ignore
            StartWaitState = EnumStartState.StartWait
        else:
            ErrNo7Seg = const.Led7SegClass.SEG_E28
            ret = EnumReturnStatus.NoScrewGuideOpen
    elif (StartWaitState == EnumStartState.StartWait):
        # スタートスイッチが左右同時に点滅
        BlinkStartSw1Sw2()
        # 左右のスタートスイッチの状態を取得
        sw1 = spleboClass.io_ex_input(InPort.IN13_StartLeftSW.value)  # type: ignore
        sw2 = spleboClass.io_ex_input(InPort.IN14_StartRightSW.value)  # type: ignore
        if (sw1 and sw2):
            # 左右のスタートスイッチが押された
            # spleboClass.Disp7SegLine1(const.Led7SegClass.SEG_RUN)  # type: ignore
            # progStr = [const.Led7SegClass.LED_P, const.Led7SegClass.LED_0, const.Led7SegClass.LED_1]
            # spleboClass.Disp7SegLine2(progStr)  # type: ignore
            # ワークロックON
            spleboClass.io_ex_output(OutPort.OUT10_WorkLock.value, True)  # type: ignore

            ret = EnumReturnStatus.StartOn
            StartWaitState = EnumStartState.WorkLockOff
        if (spleboClass.Chk_GUI_SW5()):  # type: ignore
            BlinkStopSw1Sw2()
            ret = EnumReturnStatus.SW5On
            StartWaitState = EnumStartState.WorkLockOff
    else:
        ErrNo7Seg = const.Led7SegClass.SEG_PRG
        ret = EnumReturnStatus.ProgramError
        print("未定義")

    return ret


def ProgNoDisp() -> None:
    global spleboClass

    # ProgNo を取得
    progNo = spleboClass.chk_GUI_ProgNo()  # type: ignore

    prgs = const.Led7SegClass.get_led_list(progNo, False)
    spleboClass.Disp7SegLine1(prgs)  # type: ignore
    spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_PRG)  # type: ignore


def ScrewPickup(Speed: int) -> EnumScrewPickupError:
    global ScrewPickupState
    global ErrNo7Seg

    ret = EnumScrewPickupError.NonError
    if (ScrewPickupState == EnumScrewPickupState.ScrewPickupUpper):
        # ねじ取り上空(No10)
        # ポイント番号(10)のＸ、Ｚ軸位置へ速度(20%)にて移動
        spleboClass.motion_movePoint(DEF_axXZ, 10, Speed)  # type: ignore

        ScrewPickupState = EnumScrewPickupState.ScrewNonCheck
    elif (ScrewPickupState == EnumScrewPickupState.ScrewNonCheck):
        # ねじ無しチェック
        if (not WaitInput(InPort.IN04_ScrewDetect.value, 0, 100)):
            ErrNo7Seg = const.Led7SegClass.SEG_E19
            ret = EnumScrewPickupError.ScrewYes
        else:
            # ねじ吸着OFF
            spleboClass.io_ex_output(OutPort.OUT04_ScrewVacuum.value, False)  # type: ignore
            ScrewPickupState = EnumScrewPickupState.FeederScrewCheck

    elif (ScrewPickupState == EnumScrewPickupState.FeederScrewCheck):
        # フィーダーネジチェック
        if (not WaitInput(InPort.IN05_FeederScrew.value, 1, 2000)):
            ErrNo7Seg = const.Led7SegClass.SEG_R18
            ret = EnumScrewPickupError.FeederScrewNon
        else:
            ScrewPickupState = EnumScrewPickupState.GuideOpenCheck
    elif (ScrewPickupState == EnumScrewPickupState.GuideOpenCheck):
        # ガイドオープン
        spleboClass.io_ex_output(OutPort.OUT02_ScrewGuide.value, True)  # type: ignore

        # ガイドオープン確認
        if ((not WaitInput(InPort.IN03_ScrewGuide_Open.value, 1, 1000))
                and (not WaitInput(InPort.IN02_ScrewGuide_Close.value, 0, 1000))):
            ErrNo7Seg = const.Led7SegClass.SEG_E28
            ret = EnumScrewPickupError.GuideOpen
        else:
            ScrewPickupState = EnumScrewPickupState.RotateCheck
    elif (ScrewPickupState == EnumScrewPickupState.RotateCheck):
        # 吸着ON
        spleboClass.io_ex_output(OutPort.OUT04_ScrewVacuum.value, True)  # type: ignore
        # 回転ON
        spleboClass.io_ex_output(OutPort.OUT09_Driver.value, True)  # type: ignore
        # シリンダON
        spleboClass.io_ex_output(OutPort.OUT00_DriverSV.value, True)  # type: ignore

        time.sleep(0.3)
        # 回転確認
        if (not WaitInput(InPort.IN09_DriverTorqueUp.value, 1, 100)):
            ErrNo7Seg = const.Led7SegClass.SEG_E42
            ret = EnumScrewPickupError.RotateStop
        else:
            ScrewPickupState = EnumScrewPickupState.ScrewPickupDown

    elif (ScrewPickupState == EnumScrewPickupState.ScrewPickupDown):
        # ねじ取り下降
        spleboClass.motion_movePoint(DEF_axZ, 11, Speed)  # type: ignore
        ScrewPickupState = EnumScrewPickupState.SylinderOnCheck

    elif (ScrewPickupState == EnumScrewPickupState.SylinderOnCheck):
        # シリンダON確認
        if ((not WaitInput(InPort.IN00_DriverSV_Up.value, 0, 100))
                and (not WaitInput(InPort.IN01_DriverSV_Down.value, 1, 100))):
            ErrNo7Seg = const.Led7SegClass.SEG_E27
            ret = EnumScrewPickupError.SylinderDown
        else:
            # 300ms Wait
            time.sleep(0.3)
            ScrewPickupState = EnumScrewPickupState.ScrewPickupUp

    elif (ScrewPickupState == EnumScrewPickupState.ScrewPickupUp):
        # 回転OFF
        spleboClass.io_ex_output(OutPort.OUT09_Driver.value, False)  # type: ignore

        # シリンダOFF
        spleboClass.io_ex_output(OutPort.OUT00_DriverSV.value, False)  # type: ignore

        # ねじ取り上空
        spleboClass.motion_movePoint(DEF_axZ, 12, Speed)  # type: ignore
        ScrewPickupState = EnumScrewPickupState.SylinderOffCheck

    elif (ScrewPickupState == EnumScrewPickupState.SylinderOffCheck):
        # シリンダOFF確認
        if ((not WaitInput(InPort.IN00_DriverSV_Up.value, 1, 100))
                and (not WaitInput(InPort.IN01_DriverSV_Down.value, 0, 100))):
            ErrNo7Seg = const.Led7SegClass.SEG_E27
            ret = EnumScrewPickupError.SylinderUp
        else:
            ScrewPickupState = EnumScrewPickupState.GuideCloseCheck

    elif (ScrewPickupState == EnumScrewPickupState.GuideCloseCheck):
        # ガイドクローズ
        spleboClass.io_ex_output(OutPort.OUT02_ScrewGuide.value, False)  # type: ignore

        # ガイドクローズ確認
        if ((not WaitInput(InPort.IN02_ScrewGuide_Close.value, 1, 500))
                and (not WaitInput(InPort.IN03_ScrewGuide_Open.value, 0, 500))):
            ErrNo7Seg = const.Led7SegClass.SEG_E28
            ret = EnumScrewPickupError.GuideClose
        else:
            # 100ms Wait
            time.sleep(0.1)
            ScrewPickupState = EnumScrewPickupState.ScrewPickupSuccessCheck

    elif (ScrewPickupState == EnumScrewPickupState.ScrewPickupSuccessCheck):
        # ねじあり確認
        if (not WaitInput(InPort.IN04_ScrewDetect.value, 1, 100)):
            ErrNo7Seg = const.Led7SegClass.SEG_R18
            ret = EnumScrewPickupError.ScrewNo
        else:
            ScrewPickupState = EnumScrewPickupState.ScrewPickupFinish

    return ret


def ScrewTight(PosNo: int, Speed: int) -> EnumScrewTightError:
    global ScrewTightState
    global ErrNo7Seg

    ret = EnumScrewTightError.NonError
    if (ScrewTightState == EnumScrewTightState.ScrewTightUpper):
        # ねじ締め上空
        spleboClass.motion_movePoint(DEF_axXYZ, PosNo, Speed)  # type: ignore
        ScrewTightState = EnumScrewTightState.DisplacementSensorReset

    elif (ScrewTightState == EnumScrewTightState.DisplacementSensorReset):
        # 変位センサーリセット ON
        spleboClass.io_ex_output(OutPort.OUT07_DS_Reset.value, True)  # type: ignore
        # 20ms
        time.sleep(0.02)
        # 変位センサーリセット OFF
        spleboClass.io_ex_output(OutPort.OUT07_DS_Reset.value, False)  # type: ignore
        ScrewTightState = EnumScrewTightState.GuideOpenCheck

    elif (ScrewTightState == EnumScrewTightState.GuideOpenCheck):
        # ねじあり確認
        if (not WaitInput(InPort.IN04_ScrewDetect.value, 1, 100)):
            ErrNo7Seg = const.Led7SegClass.SEG_R18
            ret = EnumScrewTightError.ScrewNo
        else:
            # ガイドオープン
            spleboClass.io_ex_output(OutPort.OUT02_ScrewGuide.value, True)  # type: ignore

            # ガイドオープン確認
            if ((not WaitInput(InPort.IN02_ScrewGuide_Close.value, 0, 500))
                    and (not WaitInput(InPort.IN03_ScrewGuide_Open.value, 1, 500))):
                ErrNo7Seg = const.Led7SegClass.SEG_E28
                ret = EnumScrewTightError.GuideOpen
            else:
                # シリンダON
                spleboClass.io_ex_output(OutPort.OUT00_DriverSV.value, True)  # type: ignore
                ScrewTightState = EnumScrewTightState.ScrewTightDown

    elif (ScrewTightState == EnumScrewTightState.ScrewTightDown):
        # Z軸下降
        spleboClass.motion_movePoint(DEF_axZ, PosNo + 1, Speed)  # type: ignore

        # 回転ON
        spleboClass.io_ex_output(OutPort.OUT09_Driver.value, True)  # type: ignore

        # トルクアップ OFF確認
        if (not WaitInput(InPort.IN09_DriverTorqueUp.value, 1, 2000)):
            ret = EnumScrewTightError.TorqueOFF
            ErrNo7Seg = const.Led7SegClass.SEG_E42
        else:
            # シリンダ 上OFF確認
            if (not WaitInput(InPort.IN00_DriverSV_Up.value, 0, 100)):
                ErrNo7Seg = const.Led7SegClass.SEG_E27
                ret = EnumScrewTightError.SylinderUp
            else:
                ScrewTightState = EnumScrewTightState.TorqueUpCheck

    elif (ScrewTightState == EnumScrewTightState.TorqueUpCheck):
        # トルクアップ ON確認
        if (not WaitInput(InPort.IN09_DriverTorqueUp.value, 0, 5000)):
            ErrNo7Seg = const.Led7SegClass.SEG_E41
            ret = EnumScrewTightError.TorqueON
        else:
            # バキュームOFF
            spleboClass.io_ex_output(OutPort.OUT04_ScrewVacuum.value, False)  # type: ignore
            # 回転OFF
            spleboClass.io_ex_output(OutPort.OUT09_Driver.value, False)  # type: ignore
            ScrewTightState = EnumScrewTightState.DisplacementSensorTiming

    elif (ScrewTightState == EnumScrewTightState.DisplacementSensorTiming):
        # Timing信号 ON
        spleboClass.io_ex_output(OutPort.OUT06_DS_Timing.value, True)  # type: ignore
        # 20ms Wait
        time.sleep(0.02)
        # Timing信号 OFF
        spleboClass.io_ex_output(OutPort.OUT06_DS_Timing.value, False)  # type: ignore
        # 10ms Wait
        time.sleep(0.01)

        # High信号エラー
        if (WaitInput(InPort.IN06_DS_High.value, 1, 100)):
            ErrNo7Seg = const.Led7SegClass.SEG_E17
            ret = EnumScrewTightError.HighError
        # Low信号エラー
        elif (WaitInput(InPort.IN08_DS_LOW.value, 1, 100)):
            ErrNo7Seg = const.Led7SegClass.SEG_E17
            ret = EnumScrewTightError.LowError
        # OK信号エラー
        elif (WaitInput(InPort.IN07_DS_OK.value, 0, 100)):
            ErrNo7Seg = const.Led7SegClass.SEG_E18
            ret = EnumScrewTightError.OKErrror
        else:
            # シリンダOFF
            spleboClass.io_ex_output(OutPort.OUT00_DriverSV.value, False)  # type: ignore
            ScrewTightState = EnumScrewTightState.ZAxisUp

    elif (ScrewTightState == EnumScrewTightState.ZAxisUp):
        # Z軸上昇
        spleboClass.motion_movePoint(DEF_axZ, PosNo + 2, Speed)  # type: ignore
        ScrewTightState = EnumScrewTightState.SylinderOffCheck

    elif (ScrewTightState == EnumScrewTightState.SylinderOffCheck):
        # シリンダOFF確認
        if ((not WaitInput(InPort.IN00_DriverSV_Up.value, 1, 100))
                and (not WaitInput(InPort.IN01_DriverSV_Down.value, 0, 100))):
            ErrNo7Seg = const.Led7SegClass.SEG_E27
            ret = EnumScrewTightError.SylinderDown
        else:
            ScrewTightState = EnumScrewTightState.GuideCloseCheck

    elif (ScrewTightState == EnumScrewTightState.GuideCloseCheck):
        # ガイドクローズ
        spleboClass.io_ex_output(OutPort.OUT02_ScrewGuide.value, False)  # type: ignore

        # ガイドクローズ確認
        if ((not WaitInput(InPort.IN02_ScrewGuide_Close.value, 1, 5000))
                and (not WaitInput(InPort.IN03_ScrewGuide_Open.value, 0, 5000))):
            ErrNo7Seg = const.Led7SegClass.SEG_E28
            ret = EnumScrewTightError.GuideClose
        else:
            ScrewTightState = EnumScrewTightState.ScrewTightFinish

    return ret


def main():
    #
    global spleboClass
    global ScrewPickupState
    global ScrewTightState
    global ErrNo7Seg

    # モニター起動のため
    time.sleep(1)
    #
    # クラスをイニシャライズ
    spleboClass = splebo_n.splebo_n_class()
    #
    # time.sleep(1)
    #
    spleboClass.setGUILampSW10(1)  # type: ignore

    loopState = EnumLoopState.HomeInit
    ErrNo7Seg = const.Led7SegClass.SEG_3MINUS

    # I/O出力初期化
    InitOutput()

    # ScrewPickupCount = 0
    Speed = 100

    # ねじ締めポイント（5か所）
    ScrewList = [100, 110, 120, 130, 140]
    ScrewTightCount = 0

    # while (True):
    #     # print("loopState = ", loopState)
    #     if (spleboClass.emg_getstat()):
    #         loopState = EnumLoopState.Error
    #         ErrNo7Seg = const.Led7SegClass.SEG_EMG

    #     # Home初期化
    #     if (loopState == EnumLoopState.HomeInit):
    #         # ORG Stb表示
    #         spleboClass.Disp7SegLine1(const.Led7SegClass.SEG_ORG)
    #         spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_STB)
    #         #
    #         # HOMEボタンを点滅
    #         spleboClass.BlinkStartLampHOMESW()
    #         NotificationBuzzer()  # 起動時ブザー
    #         loopState = EnumLoopState.HomeWait
    #     # Home待ち
    #     elif (loopState == EnumLoopState.HomeWait):
    #         # Home押下待ち
    #         if (spleboClass.Chk_GUI_HomeSw()):
    #             loopState = EnumLoopState.Homing
    #     # Homing
    #     elif (loopState == EnumLoopState.Homing):
    #         # 原点復帰
    #         spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_RUN)
    #         spleboClass.motion_home()
    #         # 原点復帰の後
    #         spleboClass.StopBlinkLED(0)  # type: ignore
    #         spleboClass.setGUILampHOME(1)  # type: ignore
    #         spleboClass.Disp7SegLine1(const.Led7SegClass.SEG_3MINUS)
    #         spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_3MINUS)
    #         loopState = EnumLoopState.SelectInit
    #     # Program選択初期化
    #     elif (loopState == EnumLoopState.SelectInit):
    #         # SW5待ち
    #         if (spleboClass.Chk_GUI_SW5()):
    #             spleboClass.setGUILampRDY(False)  # type: ignore
    #             # SW5ボタンを点滅
    #             spleboClass.BlinkStartLampSW5()
    #             time.sleep(0.25)
    #             loopState = EnumLoopState.SelectLoop
    #     # Program選択
    #     elif (loopState == EnumLoopState.SelectLoop):
    #         ProgNoDisp()
    #         # SW5待ち
    #         if (spleboClass.Chk_GUI_SW5()):
    #             time.sleep(0.25)
    #             # ProgNo を取得
    #             progNo = spleboClass.chk_GUI_ProgNo()
    #             if (progNo == 1):
    #                 prgs = const.Led7SegClass.get_led_list(progNo, True)
    #                 spleboClass.Disp7SegLine1(prgs)
    #                 # ProgNoが「01」ならば次へ
    #                 loopState = EnumLoopState.StartWait
    #                 # SW5ボタンを消灯
    #                 spleboClass.StopBlinkLED(0)  # type: ignore
    #     # Startボタン待ち
    #     elif (loopState == EnumLoopState.StartWait):
    #         ret = StartWaitProc()

    #         if (ret == EnumReturnStatus.NonError):
    #             pass
    #         elif (ret == EnumReturnStatus.StartOn):
    #             # 左右のスタートスイッチが押された
    #             # ループから抜ける
    #             # LoopStat = 2
    #             # ScrewPickupCount = 0
    #             ScrewPickupState = EnumScrewPickupState.ScrewPickupUpper
    #             ScrewTightCount = 0
    #             loopState = EnumLoopState.ScrewPickup
    #         elif (ret == EnumReturnStatus.SW5On):
    #             BlinkStopSw1Sw2()
    #             loopState = EnumLoopState.SelectInit
    #         elif (ret == EnumReturnStatus.NoWork):
    #             pass
    #         else:
    #             loopState = EnumLoopState.Error
    #     # ねじ取り
    #     elif (loopState == EnumLoopState.ScrewPickup):
    #         # ねじ取り
    #         # print("Screw Pick Up")
    #         retpick = ScrewPickup(Speed)

    #         if (retpick == EnumScrewPickupError.NonError):
    #             if (ScrewPickupState == EnumScrewPickupState.ScrewPickupFinish):
    #                 ScrewTightState = EnumScrewTightState.ScrewTightUpper

    #                 loopState = EnumLoopState.ScrewTight
    #         # elif (retpick == EnumScrewPickupError.FeederScrewNon):
    #         #     ScrewPickupCount += 1
    #         #     if (ScrewPickupCount >= 3):
    #         #         ErrNo7Seg = const.Led7SegClass.SEG_OFF
    #         #         loopState = EnumLoopState.Error
    #         else:
    #             # print("retpick = ", retpick)
    #             # ErrNo7Seg = const.Led7SegClass.get_led_list(retpick.value, False)
    #             # ErrNo7Seg = const.Led7SegClass.SEG_OFF
    #             loopState = EnumLoopState.Error
    #     # ねじ締め
    #     elif (loopState == EnumLoopState.ScrewTight):
    #         # ねじ締め
    #         # print("Screw Tight")
    #         rettight = ScrewTight(ScrewList[ScrewTightCount], Speed)

    #         if (rettight == EnumScrewTightError.NonError):
    #             if (ScrewTightState == EnumScrewTightState.ScrewTightFinish):
    #                 ScrewTightCount += 1
    #                 if (ScrewTightCount < len(ScrewList)):
    #                     ScrewPickupState = EnumScrewPickupState.ScrewPickupUpper
    #                     loopState = EnumLoopState.ScrewPickup
    #                 else:
    #                     # SW LED Off
    #                     spleboClass.io_ex_output(OutPort.OUT13_StartLeft.value, 0)  # type: ignore
    #                     spleboClass.io_ex_output(OutPort.OUT14_StartRight.value, 0)  # type: ignore
    #                     loopState = EnumLoopState.MoveStartPos
    #         else:
    #             # print("rettight = ", rettight)
    #             # ErrNo7Seg = const.Led7SegClass.get_led_list(rettight.value, False)
    #             # ErrNo7Seg = const.Led7SegClass.SEG_OFF
    #             loopState = EnumLoopState.Error
    #     # スタート位置に戻る
    #     elif (loopState == EnumLoopState.MoveStartPos):
    #         # スタート位置に戻る
    #         # spleboClass.motion_movePoint(DEF_axZ, 1, Speed)
    #         # XY移動
    #         spleboClass.motion_movePoint(DEF_axXY, 1, Speed)  # type: ignore

    #         # Output OFF
    #         InitOutput()

    #         # ワークロックOFF
    #         spleboClass.io_ex_output(OutPort.OUT10_WorkLock.value, False)  # type: ignore

    #         # 終了ブザー
    #         NotificationBuzzer()

    #         spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_3EQUALS)
    #         spleboClass.setGUILampRDY(False)  # type: ignore

    #         loopState = EnumLoopState.WorkPickCheck
    #     # ワーク取り出しチェック
    #     elif (loopState == EnumLoopState.WorkPickCheck):  # type: ignore
    #         if (spleboClass.io_ex_input(InPort.IN12_WorkEnable.value) == 0):  # type: ignore
    #             loopState = EnumLoopState.StartWait
    #     # エラー
    #     elif (loopState == EnumLoopState.Error):  # type: ignore
    #         spleboClass.Disp7SegLine1(const.Led7SegClass.SEG_ERR)
    #         # ErrNo
    #         # spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_3MINUS)
    #         spleboClass.Disp7SegLine2(ErrNo7Seg)

    #         spleboClass.setGUILampRESETSW(True)  # type: ignore
    #         spleboClass.io_ex_output(OutPort.OUT15_Buzzer.value, True)  # type: ignore
    #         spleboClass.setGUILampALM(True)  # type: ignore

    #         loopState = EnumLoopState.Reset
    #     # リセット
    #     elif (loopState == EnumLoopState.Reset):
    #         if (spleboClass.Chk_GUI_ResetSw()):
    #             # ガイドクローズ
    #             # シリンダOFF
    #             # 回転OFF
    #             # 吸着OFF
    #             # ブザーOFF
    #             InitOutput()

    #             spleboClass.io_ex_output(OutPort.OUT15_Buzzer.value, False)  # type: ignore
    #             spleboClass.Disp7SegLine1(const.Led7SegClass.SEG_OFF)
    #             spleboClass.Disp7SegLine2(const.Led7SegClass.SEG_OFF)

    #             spleboClass.setGUILampRESETSW(0)  # type: ignore
    #             spleboClass.setGUILampSTARTSW(0)  # type: ignore
    #             spleboClass.setGUILampHOMESW(0)  # type: ignore
    #             spleboClass.setGUILampHOME(0)  # type: ignore
    #             spleboClass.setGUILampRDY(0)  # type: ignore
    #             spleboClass.setGUILampALM(0)  # type: ignore

    #             spleboClass.ResetAllAxis()

    #             # エラーリセット
    #             spleboClass.motion_init()
    #             time.sleep(0.5)

    #             loopState = EnumLoopState.HomeInit
    #     # 未定義
    #     else:
    #         print("未定義")

    spleboClass.close()


if __name__ == '__main__':
    main()
