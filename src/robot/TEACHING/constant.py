# ***********************************************************************#
# File Name : constant.py
# Explanation : Define a constant
# Project Name : Table Robot
# -----------------------------------------------------------------------
# History :
#           ver0.0.1 2022.7.11 New Create
# ***********************************************************************#

class Bit:
    BitOn0 = 0x01
    BitOn1 = 0x02
    BitOn2 = 0x04
    BitOn3 = 0x08
    BitOn4 = 0x10
    BitOn5 = 0x20
    BitOn6 = 0x40
    BitOn7 = 0x80
    BitOff0 = 0xFE
    BitOff1 = 0xFD
    BitOff2 = 0xFB
    BitOff3 = 0xF7
    BitOff4 = 0xEF
    BitOff5 = 0xDF
    BitOff6 = 0xBF
    BitOff7 = 0x7F
    BitOff012 = 0xF8
    BitOff2345 = 0xC3


class DEFSwStat:
    LEFTSW = 21
    RIGHTSW = 22
    StartSw1ON = 0x20
    StartSw2ON = 0x40
    StartSw1Sw2ON = 0x60


class Led7SegClass:
    LED_0 = 0x3F
    LED_1 = 0x06
    LED_2 = 0x5B
    LED_3 = 0x4F
    LED_4 = 0x66
    LED_5 = 0x6D
    LED_6 = 0x7D
    LED_7 = 0x07
    LED_8 = 0x7F
    LED_9 = 0x6F
    LED_A = 0x77
    LED_B = 0x7C
    LED_C = 0x58
    LED_D = 0x5E
    LED_E = 0x79
    LED_F = 0x71
    LED_G = 0x3D
    LED_H = 0x76
    LED_I = 0x04
    LED_J = 0x1E
    LED_K = 0x3A
    LED_L = 0x38
    LED_M = 0x55
    LED_N = 0x54
    LED_O = 0x5C
    LED_P = 0x73
    LED_Q = 0x67
    LED_R = 0x50
    LED_S = 0x2D
    LED_T = 0x78
    LED_U = 0x3E
    LED_V = 0x1C
    LED_W = 0x1D
    LED_X = 0x236
    LED_Y = 0x6E
    LED_Z = 0x1B
    LED_Minus = 0x40
    LED_sharp = 0x00
    LED_Lkakko = 0x19
    LED_Rkakko = 0x0F
    LED_plus = 0x70
    LED_minus = 0x40
    LED_slash = 0x52
    LED_colon = 0x09
    LED_equals = 0x48
    LED_leftbracket = 0x21
    LED_yen = 0x49
    LED_rightbracket = 0x0C
    LED_exclusiv = 0x01
    LED_underline = 0x08
    LED_off = 0x00

    SEG_ORG = [LED_O, LED_R, LED_G]
    SEG_STB = [LED_S, LED_T, LED_B]
    SEG_RUN = [LED_R, LED_U, LED_N]
    SEG_3MINUS = [LED_minus, LED_minus, LED_minus]
    SEG_3EQUALS = [LED_equals, LED_equals, LED_equals]
    SEG_RDY = [LED_R, LED_D, LED_Y]
    SEG_END = [LED_E, LED_N, LED_D]
    SEG_ERR = [LED_E, LED_R, LED_R]
    SEG_EMG = [LED_E, LED_M, LED_G]
    SEG_PRG = [LED_P, LED_R, LED_G]
    SEG_OFF = [LED_off, LED_off, LED_off]
    #
    SEG_E17 = [LED_E, LED_1, LED_7]
    SEG_E18 = [LED_E, LED_1, LED_8]
    SEG_E19 = [LED_E, LED_1, LED_9]
    SEG_E27 = [LED_E, LED_2, LED_7]
    SEG_E28 = [LED_E, LED_2, LED_8]
    SEG_E29 = [LED_E, LED_2, LED_9]
    SEG_E41 = [LED_E, LED_4, LED_1]
    SEG_E42 = [LED_E, LED_4, LED_2]
    #
    SEG_ALM = [LED_A, LED_L, LED_M]
    SEG_R18 = [LED_R, LED_1, LED_8]
    SEG_R19 = [LED_R, LED_1, LED_9]

    @staticmethod
    def get_led_value(num: int):
        mapping = {
            0: Led7SegClass.LED_0,
            1: Led7SegClass.LED_1,
            2: Led7SegClass.LED_2,
            3: Led7SegClass.LED_3,
            4: Led7SegClass.LED_4,
            5: Led7SegClass.LED_5,
            6: Led7SegClass.LED_6,
            7: Led7SegClass.LED_7,
            8: Led7SegClass.LED_8,
            9: Led7SegClass.LED_9,
        }
        return mapping.get(num, 0x00)

    @staticmethod
    def get_led_list(num: int, prog: bool):
        tens = num // 10
        ones = num % 10
        if (prog):
            return [
                Led7SegClass.LED_P,                 # 先頭のLED
                Led7SegClass.get_led_value(tens),     # 10の位
                Led7SegClass.get_led_value(ones)      # 1の位
            ]
        else:
            return [
                Led7SegClass.LED_off,                 # 先頭のLED
                Led7SegClass.get_led_value(tens),     # 10の位
                Led7SegClass.get_led_value(ones)      # 1の位
            ]


# ---------END OF CODE--------- #
