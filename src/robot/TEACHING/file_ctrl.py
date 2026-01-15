# *********************************************************************
# File Name : file_ctrl.py
# Explanation : Control the file
# Project Name : Table Robot
# ----------------------------------------------------------------------
# History :
#           ver0.0.1 2024.5.16 New Create
# *********************************************************************#

# - Define import/from -------------------------------------------------
import os
import datetime
import re
import splebo_n


# - Class --------------------------------------------------------------
class PositionFileClass:
    kPositionFileName = "SPLEBO-N.pos"
    position_file_path = ""
    kData_type = "SPLEBO-N.POS"
    kVersion = "1.00"
    kPointLineTag = "[Point]"
    INIT_POSITION_DATA = ["Item1=1,0,0,0,0,,,,,,0,Home Position"]

    position_data_list = []

    def __init__(self):
        """
        constructor
        """
        self.position_file_path = get_current_working_directory() + "/" \
            + self.kPositionFileName

    def create_position_file(self):
        """
        Create Position File
        """
        if is_file_check(self.position_file_path):
            # If the file exists, delete it
            file_delete(self.position_file_path)

        with open(self.position_file_path, 'w', encoding="utf-8") as file:
            file.writelines("[Position]\n")
            file.writelines("DataType="+self.kData_type + "\n")
            file.writelines("Version="+self.kVersion + "\n")
            dt_now = datetime.datetime.now()
            file.writelines("TimeStamp=" +
                            dt_now.strftime('%Y/%m/%d %H:%M:%S'))
            file.writelines("\n")
            file.writelines("\n")
            file.writelines("[Point]\n")
            file.writelines("Count=" + str(len(PositionFileClass.
                                               position_data_list)))

            for i in range(0, len(PositionFileClass.position_data_list)):
                file.writelines("\n")
                file.writelines(PositionFileClass.position_data_list[i])

    def read_position_file(self):
        """
        Read Position File
        """
        PositionFileClass.position_data_list.clear()

        if not is_file_check(self.position_file_path):
            self.create_position_file()

        position_header = ""
        data_type = ""
        version = ""
        with open(self.position_file_path, 'r', encoding="utf_8") as file:
            position_header = file.readline()
            data_type = file.readline().rstrip('\n').split("=")
            version = file.readline().rstrip('\n').split("=")

        if data_type[1] != self.kData_type:
            return False, self.kPositionFileName + " is " + \
                "Wrong DataType.\n\nSupport DataType:" + self.kData_type + \
                "\n" + "Current DataType:" + data_type[1]

        if not version[1].startswith(self.kVersion):
            return False, self.kPositionFileName + " is " + \
                "Wrong Version.\n\nSupport Version:" + self.kVersion + \
                "\n" + "Current Version:" + version[1]

        with open(self.position_file_path, 'r', encoding="utf_8") as file:
            read_text = file.read().split("\n")

        modified_chars = []
        for i in range(0, len(read_text)):
            if read_text[i] == self.kPointLineTag:
                line_count = 0
                while True:
                    if len(read_text) <= i + line_count + 2:
                        break

                    data = read_text[i + line_count + 2]
                    is_find_equal = False
                    modified_chars.clear()
                    for char in data:
                        if char == '=':
                            if not is_find_equal:
                                modified_chars.append(char)
                                is_find_equal = True
                            else:
                                modified_chars.append('＝')
                        else:
                            modified_chars.append(char)

                    # リストを再度文字列に結合
                    data = ''.join(modified_chars)

                    PositionFileClass.position_data_list.append(data)
                    line_count = line_count + 1
        #
        return True, ""

    def update_pos(self, item, point, is_abs, x_coord, y_coord, z_coord,
                   u_coord, s1_coord, s2_coord, a_coord, b_coord, is_protect,
                   comment):
        is_abs_n = 0
        is_protect_n = 0
        if (is_abs is True):
            is_abs_n = 0
        #
        if (is_protect is True):
            is_protect_n = 1
        #
        text = "Item" + str(item + 1) + "=" + str(point) + "," + \
            str(is_abs_n) + "," + str(x_coord) + "," + str(y_coord) + \
            "," + str(z_coord) + "," + str(u_coord) + "," + \
            str(s1_coord) + "," + str(s2_coord) + "," + str(a_coord) + \
            "," + str(b_coord) + "," + str(is_protect_n) + "," + str(comment)
        PositionFileClass.position_data_list[item] = text

        self.create_position_file()

    def ret_position_data(self, point, param):
        return (PositionFileClass.position_data_list[point].split('=')[1]).\
            split(',')[param]

    def add_point(self, point, add_text):
        item_count = len(PositionFileClass.position_data_list) + 1

        point_text = add_text
        if add_text == "":
            point_text = "Item" + str(item_count) + "=" + str(point) + \
                ",0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0,"

        PositionFileClass.position_data_list.append(point_text)

        self.sort_list()

        self.create_position_file()

    def delete_point(self, point):
        del PositionFileClass.position_data_list[point]
        self.sort_list()
        self.create_position_file()

    def copy_point(self, from_val, to_val):
        for i in range(0, len(PositionFileClass.position_data_list)):
            if PositionFileClass.position_data_list[i].\
               split('=')[1].split(',')[0] == str(from_val):
                point_ary = PositionFileClass.position_data_list[i].\
                        split('=')[1].split(',')

                data = ""
                for j in range(1, len(point_ary)):
                    data = data + "," + point_ary[j]

                self.add_point(int(to_val), "Item" + str(i - 6) + "=" +
                               str(to_val) + data)

        self.create_position_file()

    def modify_point(self, from_val, to_val):
        for i in range(0, len(PositionFileClass.position_data_list)):
            if int(PositionFileClass.position_data_list[i].
                   split('=')[1].split(',')[0]) == int(from_val):
                point_ary = PositionFileClass.\
                            position_data_list[i].split('=')[1].split(',')

                data = ""
                for j in range(1, len(point_ary)):
                    data = data + "," + point_ary[j]
                #
                PositionFileClass.position_data_list[i] =\
                    ("Item" + str(i) + "=" + str(to_val) + data)
                self.sort_list()
                break
        #
        self.create_position_file()

    def sort_list(self):
        temp_posi_list = []
        repar_posi_list = []

        for i in range(0, len(PositionFileClass.position_data_list)):
            temp_posi_list.append(PositionFileClass.
                                  position_data_list[i].split('=')[1])
        #
        temp_posi_list = sorted(temp_posi_list, key=lambda s:int(re.search(r'\d+', s).group()))

        for i in range(0, len(temp_posi_list)):
            posi_text = "Item" + str(i + 1) + "=" + temp_posi_list[i]
            repar_posi_list.append(posi_text)
        #
        PositionFileClass.position_data_list = repar_posi_list[:]

    def GetPointData(self, pNo, axis):
        """
        Function: ポイント番号の位置情報を取得する

        Arguments:
        pno  – ポイント番号
        para - 位置情報の軸指定
        """
        # maxCnt = len(PositionFileClass.position_data_list) - 1
        maxCnt = len(PositionFileClass.position_data_list)
        for i in range(0, maxCnt):
            tblPno = self.ret_position_data(i, 0)
            iPno = int(tblPno)
            if (pNo == iPno):
                posData = self.ret_position_data(i, (2 + axis))
                # print ("posData=[", i, posData, "]")
                break
            #
        #
        return posData

class ProjectFileClass:
    kProjectFileName = "SPLEBO-N.sys"
    kData_type = "SPLEBO-N.SYS"
    kVersion = "1.00"
    kSysParamLineTag = "[SysParam]"

    project_file_path = ""

    def __init__(self):
        """
        constructor
        """
        self.project_file_path = get_current_working_directory() + "/" \
            + self.kProjectFileName

    def create_project_file(self):
        """
        Create Project File
        """
        if is_file_check(self.project_file_path):
            return True

        with open(self.project_file_path, 'w', encoding="utf-8") as file:
            file.writelines("[Project]\n")
            file.writelines("DataType="+self.kData_type + "\n")
            file.writelines("Version="+self.kVersion + "\n")
            dt_now = datetime.datetime.now()
            file.writelines("TimeStamp=" + dt_now.strftime('%Y/%m/%d %H:%M:%S') + "\n")
            file.writelines("\n")
            file.writelines("[SysParam]\n")

            max_speed_text = ""
            max_accel_text = ""
            max_decel_text = ""
            start_speed_text = ""
            offset_speed_text = ""
            origin_speed_text = ""
            origin_offset_text = ""
            limit_plus_text = ""
            limit_minus_text = ""
            pulse_length_text = ""
            origin_order_text = ""
            origin_dir_text = ""
            origin_sensor_text = ""
            in_position_text = ""
            motor_type_text = ""

            for i in range(splebo_n.axis_type_class.axis_count):
                max_speed_text = max_speed_text + \
                    str(splebo_n.axis_set_class[i].max_speed) + ","
                max_accel_text = max_accel_text + \
                    str(splebo_n.axis_set_class[i].max_accel) + ","
                max_decel_text = max_decel_text + \
                    str(splebo_n.axis_set_class[i].max_decel) + ","
                start_speed_text = start_speed_text + \
                    str(splebo_n.axis_set_class[i].start_speed) + ","
                offset_speed_text = offset_speed_text + \
                    str(splebo_n.axis_set_class[i].offset_speed) + ","
                origin_speed_text = origin_speed_text + \
                    str(splebo_n.axis_set_class[i].origin_speed) + ","
                origin_offset_text = origin_offset_text + \
                    str(splebo_n.axis_set_class[i].origin_offset) + ","
                limit_plus_text = limit_plus_text + \
                    str(splebo_n.axis_set_class[i].limit_plus) + ","
                limit_minus_text = limit_minus_text \
                    + str(splebo_n.axis_set_class[i].limit_minus) + ","
                pulse_length_text = pulse_length_text + \
                    str(splebo_n.axis_set_class[i].pulse_length) + ","
                origin_order_text = origin_order_text + \
                    str(splebo_n.axis_set_class[i].origin_order) + ","
                origin_dir_text = origin_dir_text + \
                    str(splebo_n.axis_set_class[i].origin_dir) + ","
                origin_sensor_text = origin_sensor_text + \
                    str(splebo_n.axis_set_class[i].origin_sensor) + ","
                in_position_text = in_position_text + \
                    str(splebo_n.axis_set_class[i].in_position) + ","
                motor_type_text = motor_type_text + \
                    str(splebo_n.axis_set_class[i].motor_type) + ","

            file.writelines("MaxSpeed=" + max_speed_text[:-1] + "\n")
            file.writelines("MaxAccel=" + max_accel_text[:-1] + "\n")
            file.writelines("MaxDecel=" + max_decel_text[:-1] + "\n")
            file.writelines("StartSpeed=" + start_speed_text[:-1] + "\n")
            file.writelines("OffsetSpeed=" + offset_speed_text[:-1] + "\n")
            file.writelines("OriginSpeed=" + origin_speed_text[:-1] + "\n")
            file.writelines("OriginOffset=" + origin_offset_text[:-1] + "\n")
            file.writelines("LimitPlus=" + limit_plus_text[:-1] + "\n")
            file.writelines("LimitMinus=" + limit_minus_text[:-1] + "\n")
            file.writelines("PulseLength=" + pulse_length_text[:-1] + "\n")
            file.writelines("OriginOrder=" + origin_order_text[:-1] + "\n")
            file.writelines("OriginDir=" + origin_dir_text[:-1] + "\n")
            file.writelines("OriginSensor=" + origin_sensor_text[:-1] + "\n")
            file.writelines("InPosition=" + in_position_text[:-1] + "\n")
            file.writelines("MotorType=" + motor_type_text[:-1] + "\n")

    def read_project_file(self):
        """
        Read Position File
        """
        if not is_file_check(self.project_file_path):
            self.create_project_file()
        #
        position_header = ""
        data_type = ""
        version = ""
        with open(self.project_file_path, 'r', encoding="utf_8") as file:
            position_header = file.readline()
            data_type = file.readline().rstrip('\n').split("=")
            version = file.readline().rstrip('\n').split("=")
        #
        if data_type[1] != self.kData_type:
            retMsg = self.kProjectFileName + " is " + \
                "Wrong DataType.\n\nSupport DataType:" + self.kData_type + \
                "\n" + "Current DataType:" + data_type[1]
            return False, retMsg
        #
        if not version[1].startswith(self.kVersion):
            retMsg = self.kProjectFileName + " is " + \
                "Wrong Version.\n\nSupport Version:" + self.kVersion + \
                "\n" + "Current Version:" + version[1]
            return False, retMsg
        #
        with open(self.project_file_path, 'r', encoding="utf_8") as file:
            read_text = file.read().split("\n")

        for i in range(0, len(read_text)):
            if read_text[i] == self.kSysParamLineTag:
                line_count = 0
                while True:
                    for j in range(0, splebo_n.axis_type_class.axis_count):
                        data = self.get_syspara_data(read_text[
                            i + line_count + 1])
                        #
                        if splebo_n.axis_setting_type_class.kMax_speed \
                                == line_count:
                            splebo_n.axis_set_class[j].max_speed = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kMax_accel \
                                == line_count:
                            splebo_n.axis_set_class[j].max_accel = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kMax_decel \
                                == line_count:
                            splebo_n.axis_set_class[j].max_decel = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kStart_speed\
                                == line_count:
                            splebo_n.axis_set_class[j].start_speed = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kOffset_speed \
                                == line_count:
                            splebo_n.axis_set_class[j].offset_speed = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kOrigin_speed \
                                == line_count:
                            splebo_n.axis_set_class[j].origin_speed = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kOrigin_offset \
                                == line_count:
                            splebo_n.axis_set_class[j].origin_offset = \
                                float(data[j])
                        elif splebo_n.axis_setting_type_class.kLimit_plus \
                                == line_count:
                            splebo_n.axis_set_class[j].limit_plus = \
                                float(data[j])
                        elif splebo_n.axis_setting_type_class.kLimit_minus \
                                == line_count:
                            splebo_n.axis_set_class[j].limit_minus = \
                                float(data[j])
                        elif splebo_n.axis_setting_type_class.kPulse_length \
                                == line_count:
                            splebo_n.axis_set_class[j].pulse_length = \
                                float(data[j])
                        elif splebo_n.axis_setting_type_class.kOrigin_order \
                                == line_count:
                            splebo_n.axis_set_class[j].origin_order = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kOrigin_dir \
                                == line_count:
                            splebo_n.axis_set_class[j].origin_dir = \
                                int(data[j])
                        elif splebo_n.axis_setting_type_class.kOrigin_sensor\
                                == line_count:
                            idata = int(data[j])
                            if (idata == splebo_n.on_off_auto_class.kOFF) or\
                               (idata == splebo_n.on_off_auto_class.kAUTO):
                                splebo_n.axis_set_class[j].origin_sensor\
                                    = idata
                                splebo_n.axis_set_class[j].origin_sensor_name\
                                    = splebo_n.origin_type_list[idata]
                            else:
                                idx = splebo_n.on_off_auto_class.kOFF
                                splebo_n.axis_set_class[j].origin_sensor = idx
                                splebo_n.axis_set_class[j].origin_sensor_name\
                                    = splebo_n.origin_type_list[idx]
                        elif splebo_n.axis_setting_type_class.kIn_position\
                                == line_count:
                            splebo_n.axis_set_class[j].in_position\
                                = int(data[j])
                        elif splebo_n.axis_setting_type_class.kMotor_type\
                                == line_count:
                            idat = int(data[j])
                            if (idat == splebo_n.axis_maker_Class.kIAI)\
                                    or\
                               (idat == splebo_n.axis_maker_Class.kaSTEP)\
                                    or\
                               (idat == splebo_n.axis_maker_Class.kStepping):
                                splebo_n.axis_set_class[j].motor_type = idat
                                splebo_n.axis_set_class[j].motor_type_name\
                                    = splebo_n.maker_type_list[idat]
                            else:
                                idx = splebo_n.axis_maker_Class.kNone
                                splebo_n.axis_set_class[j].motor_type = idx
                                splebo_n.axis_set_class[j].motor_type_name\
                                    = splebo_n.maker_type_list[idx]
                        else:
                            pass
                    #
                    line_count = line_count + 1

                    if splebo_n.axis_setting_type_class.kMotor_type\
                            < line_count:
                        break
        return True, ""

    def get_syspara_data(self, tag_text):
        data = tag_text.split("=")
        return data[1].split(",")

    def update_project_file(self):
        file_delete(self.project_file_path)
        self.create_project_file()


# - Function -----------------------------------------------------------
def is_file_check(file_pass):
    """
    Check If The File Exists

    Parameters
    ----------
    file_pass : string
        File pass

    Returns
    ----------
    is_file : bool
        Presence or absence of file(True:Existing)
    """
    is_file = os.path.isfile(file_pass)
    return is_file


def file_delete(file_pass):
    """
    Delete File

    Parameters
    ----------
    file_pass (string): File pass
    """
    if is_file_check(file_pass):
        os.remove(file_pass)


def get_current_working_directory():
    """
    Get Working Directory Path

    Returns
    ----------
        string: working directory path
    """
    return os.getcwd()

# ---------END OF CODE--------- #