#!/usr/bin/env python3
"""
直接ネイティブライブラリをテストするスクリプト
TEACHINGと同じ方法でホーミングを試みる
"""
import ctypes
from ctypes import c_int, c_bool, POINTER, cast
import time
import sys

def main():
    print("="*60)
    print(" 直接ネイティブライブラリテスト")
    print("="*60)
    
    # 1. pigpioを初期化
    print("\n1. pigpio初期化...")
    pigpio_lib = None
    for path in ["libpigpio.so", "libpigpio.so.1", "/usr/lib/libpigpio.so"]:
        try:
            pigpio_lib = ctypes.cdll.LoadLibrary(path)
            print(f"   pigpioライブラリ読み込み: {path}")
            break
        except:
            continue
    
    if pigpio_lib is None:
        print("   [FAIL] pigpioライブラリが見つかりません")
        return
    
    result = pigpio_lib.gpioInitialise()
    if result < 0:
        print(f"   [FAIL] gpioInitialise() 失敗: {result}")
        return
    print(f"   [OK] gpioInitialise() 成功 (version: {result})")
    
    # 2. ネイティブライブラリをロード
    print("\n2. ネイティブライブラリをロード...")
    lib_path = "/home/splebopi/SPLEBO/TEACHING/libcsms_splebo_n.so"
    try:
        lib = ctypes.cdll.LoadLibrary(lib_path)
        print(f"   [OK] ロード成功: {lib_path}")
    except Exception as e:
        print(f"   [FAIL] ロード失敗: {e}")
        pigpio_lib.gpioTerminate()
        return
    
    # 関数シグネチャ設定
    lib.cw_mc_open.restype = c_bool
    lib.cw_mc_set_drive.argtypes = (c_int, c_int, c_bool)
    lib.cw_mc_set_drive.restype = c_bool
    lib.cw_mc_set_org_mode.argtypes = (c_int, c_int, c_int, c_bool)
    lib.cw_mc_set_org_mode.restype = c_bool
    lib.cw_mc_org.argtypes = (c_int, c_int, c_int)
    lib.cw_mc_org.restype = c_bool
    lib.cw_mc_r_reg.argtypes = (c_int, c_int, POINTER(c_int))
    lib.cw_mc_r_reg.restype = c_bool
    
    # 3. ボードオープン
    print("\n3. ボードオープン...")
    if lib.cw_mc_open():
        print("   [OK] cw_mc_open() 成功")
    else:
        print("   [FAIL] cw_mc_open() 失敗")
        pigpio_lib.gpioTerminate()
        return
    
    # 4. レジスタ読み取りテスト
    print("\n4. レジスタ読み取りテスト...")
    axis = 0
    for reg_no in range(4):
        buffer = (c_int * 16)()
        ptr = cast(buffer, POINTER(c_int))
        if lib.cw_mc_r_reg(axis, reg_no, ptr):
            print(f"   軸{axis} RR{reg_no}: 0x{ptr.contents.value:08X}")
        else:
            print(f"   軸{axis} RR{reg_no}: 読み取り失敗")
    
    # 5. ホーミングテスト
    print("\n5. 軸0のホーミングテスト...")
    print("   注意: モーターが動作します！")
    
    try:
        input("   Enterキーを押すとホーミングを開始します...")
    except KeyboardInterrupt:
        print("\n   キャンセル")
        pigpio_lib.gpioTerminate()
        return
    
    # 5a. ドライブ速度設定
    print("\n   5a. ドライブ速度設定...")
    origin_speed = 5000  # pulse/sec
    if lib.cw_mc_set_drive(axis, origin_speed, False):
        print(f"       [OK] cw_mc_set_drive({axis}, {origin_speed}, False)")
    else:
        print(f"       [FAIL] cw_mc_set_drive() 失敗")
    
    # 5b. オリジンモード設定
    print("\n   5b. オリジンモード設定...")
    # TEACHING: h1m = 0x315 | orgn_dir, h2m = 0x686
    h1m = 0x315  # CCW方向の場合
    h2m = 0x686
    if lib.cw_mc_set_org_mode(axis, h1m, h2m, False):
        print(f"       [OK] cw_mc_set_org_mode({axis}, 0x{h1m:04X}, 0x{h2m:04X}, False)")
    else:
        print(f"       [FAIL] cw_mc_set_org_mode() 失敗")
    
    # 5c. オートオリジンコマンド
    print("\n   5c. オートオリジンコマンド発行...")
    hv = origin_speed - 1
    dv = origin_speed
    if lib.cw_mc_org(axis, hv, dv):
        print(f"       [OK] cw_mc_org({axis}, {hv}, {dv})")
    else:
        print(f"       [FAIL] cw_mc_org() 失敗")
    
    # 5d. 状態監視
    print("\n   5d. ホーミング状態監視...")
    start_time = time.time()
    timeout = 30.0
    
    while (time.time() - start_time) < timeout:
        # RR0を読み取ってBusyビットを確認
        buffer = (c_int * 16)()
        ptr = cast(buffer, POINTER(c_int))
        if lib.cw_mc_r_reg(axis, 0, ptr):  # RR0
            reg0 = ptr.contents.value
            is_busy = bool(reg0 & 0x01)  # XDRV bit
            elapsed = time.time() - start_time
            print(f"       [{elapsed:5.1f}s] RR0=0x{reg0:08X}, busy={is_busy}")
            
            if not is_busy and elapsed > 1.0:
                print("       -> ホーミング完了!")
                break
        else:
            print("       レジスタ読み取り失敗")
        
        time.sleep(0.5)
    else:
        print("       -> タイムアウト")
    
    # 6. クリーンアップ
    print("\n6. クリーンアップ...")
    pigpio_lib.gpioTerminate()
    print("   [OK] 完了")


if __name__ == "__main__":
    main()
