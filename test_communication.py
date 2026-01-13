#!/usr/bin/env python3
# *********************************************************************#
# File Name : test_communication.py
# Explanation : CAN/I/O/モーター通信の確認テスト（実機を動かさない）
# Project : AutomatedAssemblyRobot - SPLEBO-N
# ----------------------------------------------------------------------
# 参照元: TEACHING/motion_control.py
# *********************************************************************#
"""
実機を動かさずにハードウェア通信を確認するテストスクリプト

確認項目:
1. libcsms_splebo_n.so ネイティブライブラリの読み込み
2. GPIO ピンのアクセス
3. I2C I/Oエキスパンダの通信
4. モーションコントローラボードのオープン

使用方法:
    python test_communication.py
"""

import sys
import os
import time
from pathlib import Path

# テスト結果の色付け
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(title: str):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE} {title}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")

def print_success(msg: str):
    print(f"  {Colors.GREEN}✓ {msg}{Colors.END}")

def print_fail(msg: str):
    print(f"  {Colors.RED}✗ {msg}{Colors.END}")

def print_warn(msg: str):
    print(f"  {Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_info(msg: str):
    print(f"  {Colors.BLUE}ℹ {msg}{Colors.END}")


# =============================================================================
# 1. ネイティブライブラリのテスト
# =============================================================================
def test_native_library():
    print_header("1. ネイティブライブラリ (libcsms_splebo_n.so) のテスト")
    
    import ctypes
    from ctypes import c_int, c_bool, POINTER, cast
    
    # ライブラリパスの候補
    lib_paths = [
        "./libcsms_splebo_n.so",
        "/home/splebopi/SPLEBO/TEACHING/libcsms_splebo_n.so",
        "/home/splebopi/SPLEBO/AutomatedAssemblyRobot/libcsms_splebo_n.so",
        "/usr/local/lib/libcsms_splebo_n.so",
        "/usr/lib/libcsms_splebo_n.so",
    ]
    
    lib = None
    found_path = None
    
    for path in lib_paths:
        if os.path.exists(path):
            print_info(f"ファイル存在確認: {path}")
            try:
                lib = ctypes.cdll.LoadLibrary(path)
                found_path = path
                print_success(f"ライブラリ読み込み成功: {path}")
                break
            except OSError as e:
                print_fail(f"ライブラリ読み込み失敗: {e}")
        else:
            print_warn(f"ファイルが見つかりません: {path}")
    
    if lib is None:
        print_fail("ネイティブライブラリが見つかりませんでした")
        print_info("解決策: libcsms_splebo_n.so をカレントディレクトリにコピーしてください")
        return False, None
    
    # API関数の存在確認
    print("\n  利用可能なAPI関数の確認:")
    api_functions = [
        'cw_mc_open',           # ボードオープン
        'cw_mc_set_mode',       # モード設定
        'cw_mc_set_drive',      # 速度設定
        'cw_mc_set_acc',        # 加速度設定
        'cw_mc_set_dec',        # 減速度設定
        'cw_mc_abs',            # 絶対位置移動
        'cw_mc_ptp',            # 相対位置移動
        'cw_mc_jog',            # JOG移動
        'cw_mc_stop',           # 停止
        'cw_mc_get_logic_cie',  # 論理座標取得
        'cw_mc_get_sts',        # ステータス取得
        'cw_mc_r_reg',          # レジスタ読み込み
        'cw_mc_w_reg',          # レジスタ書き込み
        'cw_mc_set_gen_bout',   # 汎用出力ビット設定
    ]
    
    available_funcs = []
    for func_name in api_functions:
        try:
            func = getattr(lib, func_name)
            available_funcs.append(func_name)
            print_success(f"  {func_name}")
        except AttributeError:
            print_fail(f"  {func_name} (未実装)")
    
    print(f"\n  {len(available_funcs)}/{len(api_functions)} 関数が利用可能")
    
    return True, lib


# =============================================================================
# 2. ボードオープンのテスト（実際にボードに接続）
# =============================================================================
def test_board_open(lib):
    print_header("2. モーションコントローラボードのオープンテスト")
    
    if lib is None:
        print_fail("ライブラリがロードされていません")
        return False
    
    import ctypes
    
    try:
        lib.cw_mc_open.restype = ctypes.c_bool
        result = lib.cw_mc_open()
        
        if result:
            print_success("モーションコントローラボードのオープン成功!")
            print_info("ボードとの通信が確立されました")
            return True
        else:
            print_fail("モーションコントローラボードのオープン失敗")
            print_info("ボードが接続されているか、電源が入っているか確認してください")
            return False
            
    except Exception as e:
        print_fail(f"ボードオープン中にエラー: {e}")
        return False


# =============================================================================
# 3. GPIOのテスト（pigpio経由）
# =============================================================================
def test_gpio(pigpio_lib):
    """GPIOテスト（pigpio経由）
    
    注意: RPi.GPIOではなくpigpioを使用する。
    RPi.GPIOを使用すると、libcsms_splebo_n.soのpigpio設定と競合し、
    I2C通信が失敗する。詳細: docs/GPIO_CONFLICT_ISSUE.md
    """
    print_header("3. GPIOのテスト（pigpio経由）")
    
    if pigpio_lib is None:
        print_fail("pigpioが初期化されていません")
        return False
    
    # GPIOピン定義 (splebo_n.py参照)
    GPIO_PINS = {
        'kNova_reset_pin': 14,
        'kNova_Power_pin': 12,
        'kCan_CS_pin': 8,
        'kEmergencyBtn': 15,
    }
    
    try:
        print_success("pigpio経由でGPIO読み取り")
        
        # ピンの読み取り（モードは変更しない）
        for name, pin in GPIO_PINS.items():
            try:
                value = pigpio_lib.gpioRead(pin)
                if value >= 0:
                    print_success(f"{name} (GPIO{pin}): 読み取り可能 (現在値: {value})")
                else:
                    print_warn(f"{name} (GPIO{pin}): 読み取りエラー (戻り値: {value})")
            except Exception as e:
                print_fail(f"{name} (GPIO{pin}): {e}")
        
        # 緊急停止ボタンの状態確認
        emg_pin = GPIO_PINS['kEmergencyBtn']
        emg_state = pigpio_lib.gpioRead(emg_pin)
        if emg_state != 0:
            print_warn(f"緊急停止ボタンが押されています! (GPIO{emg_pin} = {emg_state})")
        else:
            print_success(f"緊急停止ボタンは解除されています (GPIO{emg_pin} = {emg_state})")
        
        return True
        
    except Exception as e:
        print_fail(f"GPIOテスト中にエラー: {e}")
        return False


# =============================================================================
# 4. I2C I/Oエキスパンダのテスト
# =============================================================================
def test_i2c_expander():
    print_header("4. I2C I/Oエキスパンダのテスト")
    
    try:
        import smbus
        print_success("smbus モジュールのインポート成功")
    except ImportError:
        print_fail("smbus モジュールがインストールされていません")
        print_info("インストール: sudo apt-get install python3-smbus")
        return False
    
    # I2C設定 
    # オリジナルのio_expander.py: kI2c_bus = 5
    # 利用可能なバス: /dev/i2c-1, /dev/i2c-3, /dev/i2c-20, /dev/i2c-21
    I2C_BUS = 3  # または環境に合わせて変更
    I2C_ADDRESSES = {
        'Input Board 0': 0x21,
        'Output Board 0': 0x24,
        'Input Board 1': 0x23,
        'Output Board 1': 0x26,
    }
    
    # MCP23017レジスタ
    IODIRA = 0x00
    IODIRB = 0x01
    GPIOA = 0x12
    GPIOB = 0x13
    
    try:
        bus = smbus.SMBus(I2C_BUS)
        print_success(f"I2Cバス {I2C_BUS} のオープン成功")
        
        for name, addr in I2C_ADDRESSES.items():
            try:
                # デバイスからの読み取りテスト
                data_a = bus.read_byte_data(addr, GPIOA)
                data_b = bus.read_byte_data(addr, GPIOB)
                print_success(f"{name} (0x{addr:02X}): 通信OK")
                print_info(f"    GPIOA: 0x{data_a:02X}, GPIOB: 0x{data_b:02X}")
            except OSError as e:
                if e.errno == 121:
                    print_warn(f"{name} (0x{addr:02X}): デバイスが応答しません")
                else:
                    print_fail(f"{name} (0x{addr:02X}): {e}")
        
        bus.close()
        return True
        
    except FileNotFoundError:
        print_fail(f"I2Cバス {I2C_BUS} が見つかりません")
        print_info("I2Cインターフェースが有効になっているか確認してください:")
        print_info("  sudo raspi-config -> Interface Options -> I2C")
        return False
    except Exception as e:
        print_fail(f"I2Cテスト中にエラー: {e}")
        return False


# =============================================================================
# 5. CAN通信のテスト
# =============================================================================
def test_can():
    print_header("5. CAN通信のテスト")
    
    # CAN関連のファイル確認
    can_file = "/home/splebopi/SPLEBO/TEACHING/can.py"
    
    if os.path.exists(can_file):
        print_success(f"CANモジュール存在: {can_file}")
    else:
        print_warn(f"CANモジュールが見つかりません: {can_file}")
    
    # MCP2515 SPIデバイスの確認
    spi_devices = ["/dev/spidev0.0", "/dev/spidev0.1"]
    for dev in spi_devices:
        if os.path.exists(dev):
            print_success(f"SPIデバイス存在: {dev}")
        else:
            print_warn(f"SPIデバイスなし: {dev}")
    
    # CANインターフェースの確認
    try:
        import subprocess
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
        if 'can0' in result.stdout:
            print_success("CAN0インターフェースが検出されました")
        else:
            print_warn("CAN0インターフェースが見つかりません")
            print_info("SocketCANを使用する場合: sudo ip link set can0 up type can bitrate 500000")
    except Exception as e:
        print_warn(f"CANインターフェース確認失敗: {e}")
    
    return True


# =============================================================================
# 6. レジスタ読み取りテスト（ボードがオープンされている場合）
# =============================================================================
def test_register_read(lib):
    print_header("6. モーションコントローラ レジスタ読み取りテスト")
    
    if lib is None:
        print_fail("ライブラリがロードされていません")
        return False
    
    import ctypes
    from ctypes import c_int, POINTER, cast
    
    # NOVA レジスタ定義 (splebo_n.py参照)
    REGISTERS = {
        'RR0': 0x00,  # 駆動状態/エラー
        'RR1': 0x01,
        'RR2': 0x02,  # アラーム/非常停止
        'RR3': 0x03,  # 原点センサ/INPOS
    }
    
    try:
        lib.cw_mc_r_reg.argtypes = (c_int, c_int, POINTER(c_int))
        lib.cw_mc_r_reg.restype = ctypes.c_bool
        
        for axis in range(3):  # X, Y, Z軸のみテスト
            print(f"\n  軸 {axis} のレジスタ:")
            for reg_name, reg_no in REGISTERS.items():
                buffer = (c_int * 16)()
                data = cast(buffer, POINTER(c_int))
                
                result = lib.cw_mc_r_reg(axis, reg_no, data)
                if result:
                    value = data.contents.value
                    print_success(f"    {reg_name}: 0x{value:08X}")
                    
                    # RR0の解析
                    if reg_no == 0x00:
                        if value & 0x01:
                            print_info("      X軸駆動中")
                        if value & 0x10:
                            print_warn("      X軸エラー")
                else:
                    print_fail(f"    {reg_name}: 読み取り失敗")
        
        return True
        
    except Exception as e:
        print_fail(f"レジスタ読み取り中にエラー: {e}")
        return False


# =============================================================================
# メイン
# =============================================================================
def main():
    print("\n" + "="*60)
    print(" SPLEBO-N 通信確認テスト")
    print(" (実機を動かさずにハードウェア接続を確認します)")
    print("="*60)
    
    results = {}
    
    # pigpioの初期化（libcsms_splebo_n.soが内部で使用）
    # CレベルのgpioInitialise()を呼び出す必要がある
    pigpio_initialized = False
    pigpio_lib = None
    
    import ctypes
    pigpio_lib_paths = [
        "libpigpio.so",
        "libpigpio.so.1",
        "/usr/lib/libpigpio.so",
        "/usr/lib/arm-linux-gnueabihf/libpigpio.so",
        "/usr/local/lib/libpigpio.so",
    ]
    
    for path in pigpio_lib_paths:
        try:
            pigpio_lib = ctypes.cdll.LoadLibrary(path)
            print_info(f"pigpioライブラリ読み込み成功: {path}")
            break
        except OSError:
            continue
    
    if pigpio_lib:
        try:
            result = pigpio_lib.gpioInitialise()
            if result >= 0:
                pigpio_initialized = True
                print_success(f"gpioInitialise() 成功 (version: {result})")
            else:
                print_warn(f"gpioInitialise() 失敗 (エラーコード: {result})")
                print_info("root権限で実行してください: sudo python test_communication.py")
        except Exception as e:
            print_warn(f"gpioInitialise() エラー: {e}")
    else:
        print_warn("libpigpio.soが見つかりません")
        # フォールバック: Pythonのpigpioモジュール経由でデーモン接続
        try:
            import pigpio
            pigpio_pi = pigpio.pi()
            if pigpio_pi.connected:
                print_success("pigpioデーモンに接続しました（デーモンモード）")
                pigpio_initialized = True
            else:
                print_warn("pigpioデーモンに接続できません")
                print_info("解決策: sudo pigpiod を実行してください")
        except ImportError:
            print_warn("pigpioモジュールがインストールされていません")
            print_info("インストール: sudo apt-get install python3-pigpio")
        except Exception as e:
            print_warn(f"pigpio初期化エラー: {e}")
    
    # 1. ネイティブライブラリのテスト
    results['native_lib'], lib = test_native_library()
    
    # 2. ボードオープンのテスト
    if lib:
        results['board_open'] = test_board_open(lib)
    else:
        results['board_open'] = False
    
    # 3. GPIOのテスト（pigpio経由）
    results['gpio'] = test_gpio(pigpio_lib)
    
    # 4. I2C I/Oエキスパンダのテスト
    results['i2c'] = test_i2c_expander()
    
    # 5. CAN通信のテスト
    results['can'] = test_can()
    
    # 6. レジスタ読み取りテスト
    if results.get('board_open'):
        results['register'] = test_register_read(lib)
    else:
        print_header("6. モーションコントローラ レジスタ読み取りテスト")
        print_warn("ボードがオープンされていないため、スキップします")
        results['register'] = None
    
    # pigpioクリーンアップ
    if pigpio_initialized and pigpio_lib:
        try:
            pigpio_lib.gpioTerminate()
            print_info("pigpio終了処理完了")
        except:
            pass
    
    # サマリー
    print_header("テスト結果サマリー")
    
    all_passed = True
    for test_name, passed in results.items():
        if passed is True:
            print_success(f"{test_name}: PASS")
        elif passed is False:
            print_fail(f"{test_name}: FAIL")
            all_passed = False
        else:
            print_warn(f"{test_name}: SKIPPED")
    
    print()
    if all_passed:
        print(f"{Colors.GREEN}すべてのテストが成功しました！{Colors.END}")
    else:
        print(f"{Colors.YELLOW}一部のテストが失敗しました。上記の結果を確認してください。{Colors.END}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
