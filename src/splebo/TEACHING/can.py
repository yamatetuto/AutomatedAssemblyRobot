# *********************************************************************#
# File Name : can.py
# Explanation : Access IO Expander
# Project Name : Table Robot
# ----------------------------------------------------------------------
# History :
#           ver0.0.1 2024.6.3 New Create
# *********************************************************************#

# - Define import/from -------------------------------------------------
import spidev
import RPi.GPIO as GPIO
import time
import threading
# from threading import Thread
import splebo_n


# - Class --------------------------------------------------------------
class can_data_st:
    kMAXCHAR_ONEMESSAGE = 8         # 1 time send Max char length

    id = 0
    eid_en = False
    bnum = 0
    data = bytearray(kMAXCHAR_ONEMESSAGE)
    len = 0


class can_ctrl_class:
    kMAX_CAN_BOAD = 16              # Max Boad Number
    kWRITE_DATA_SIZE = 8            # Write CAN Data Size
    kREAD_DATA_SIZE = 4             # Read CAN Data Size

    kMCP2515_CMD_RESET = 0xC0       # MCP2515 Reset
    kMCP2515_CMD_READ = 0x03        # Read Register
    kMCP2515_CMD_WRITE = 0x02       # Write Register
    kMCP2515_CMD_BITMOD = 0x05      # Change Bit
    kMCP2515_CMD_RDRXBUF = 0x90     # Read RX Buffer
    kMCP2515_CMD_LDTXBUF = 0x40     # Write TX Buffer
    kMCP2515_CMD_RTS = 0x80         # Request Send Message
    kMCP2515_CMD_STATUS = 0xA0      # Read Status
    kMCP2515_CMD_RXSTATUS = 0xB0    # Read RX Status

    kREG_RXB0CTRL = 0x60            # Receive Buffer 0 Control
    kREG_RXB1CTRL = 0x70            # Receive Buffer 1 Control

    kMSK_EXIDE = 0b1000
    kREG_CAN_CTRL = 0x0F            # CAN Control Register
    kREG_CAN_CNF1 = 0x2A            # Configration Register 1
    kREG_CAN_CNF2 = 0x29            # Configration Register 2
    kREG_CAN_CNF3 = 0x28            # Configration Register 3
    kREG_CANSTAT = 0x0E             # CAN Status Register

    kCAN_MODE_NORMAL = 0            # Normal Mode
    kCAN_MODE_SLEEP = 1             # Sleep Mode
    kCAN_MODE_LOOPBACK = 2          # Loop Back Mode
    kCAN_MODE_LISTEN = 3            # Listen Mode
    kCAN_MODE_CONFIG = 4            # Config Mode

    kRX0_1_NO_MASK = 0x60           # Set None Mask : 0110-0000

    kMSK_MSGRX0 = 0x40              # Check Receive RXB0 Mask
    kMSK_MSGRX1 = 0x80              # Check Receive RXB1 Mask

    kWRITE_CAN_ID_TOP = 0xC0        # Write Can Top

    spi_device = None               # SPI Devide
    write_can_buffer_ary = []       # Write CAN Buffer Array
    read_can_buffer_ary = []        # Read CAN Buffer Array

    valid_can_board = [False, False, False, False, False, False, False,
                       False, False, False, False, False, False, False,
                       False, False]
    Flag_canio_thread = False

    def __init__(self):
        """CAN Contruct.

        Parameters
        ----------
        None

        Returns
        ----------
        None
        """

        # Reserves the specified number of CAN buffers for writing & reading
        for i in range(self.kMAX_CAN_BOAD):
            self.write_can_buffer_ary = [[0 for _ in range(
                self.kWRITE_DATA_SIZE)] for _ in range(self.kMAX_CAN_BOAD)]
            self.read_can_buffer_ary = [[0 for _ in range(
                self.kREAD_DATA_SIZE)] for _ in range(self.kMAX_CAN_BOAD)]
            self.valid_can_board[i] = True

        self.spi_device = spidev.SpiDev()   # Set SPI Data Source

    def initialize_can(self):
        """CAN Initialize.

        Parameters
        ----------
        self
            instance object

        Returns
        ----------
        None
        """
        self.spi_device.open(0, 0)               # Open SPI
        self.spi_device.mode = 3                # Set SPI Mode
        self.spi_device.max_speed_hz = 500000   # Set SPI Max speed

        self.reset_mcp2515()                    # Reset MCP2515
        time.sleep(0.03)

        # Set Config Mode
        self.can_spi_config(self.kREG_CAN_CTRL, 0xE0,
                            (self.kCAN_MODE_CONFIG << 5))

        # Check Set Config Mode
        while True:
            status = self.can_spi_read_reg(self.kREG_CANSTAT)
            if (status & (self.kCAN_MODE_CONFIG << 5)):
                break

        # Set MCP2515 BaudRate 16Mhz 500kbps
        self.can_spi_write_reg(self.kREG_CAN_CNF1, 0x00)
        self.can_spi_write_reg(self.kREG_CAN_CNF2, 0x80)
        self.can_spi_write_reg(self.kREG_CAN_CNF3, 0x01)

        # Receive Buffer 0 , None Mask, None Roll Over
        self.can_spi_write_reg(self.kREG_RXB0CTRL, self.kRX0_1_NO_MASK)

        # Receive Buffer 1 , None Mask, None Roll Over
        self.can_spi_write_reg(self.kREG_RXB1CTRL, self.kRX0_1_NO_MASK)

        # Set Normal Mode
        self.can_spi_config(self.kREG_CAN_CTRL, 0xE0,
                            (self.kCAN_MODE_NORMAL << 5))

        # Check Set Normal Mode
        while True:
            status = self.can_spi_read_reg(self.kREG_CANSTAT)
            if not (status & (self.kCAN_MODE_CONFIG << 5)):
                break

        return True

    def reset_mcp2515(self):
        """Reset MCP2515.

        Parameters
        ----------
        self
            instance object

        Returns
        ----------
        None
        """
        wd_buffer = self.kMCP2515_CMD_RESET

        ret = self.can_spi_RW(wd_buffer, 1)
        if ret == -1:
            print("Could not Reset SPI")
        #
        time.sleep(0.002)
        return ret

    def canio_thread_proc(self):
        while (self.Flag_canio_thread):
            #
            for canId in range(self.kMAX_CAN_BOAD):
                #
                if (self.valid_can_board[canId]):
                    stat = self.read_control_can(canId)
                    if stat is False:
                        self.valid_can_board[canId] = False
                    time.sleep(0.002)
                #
            # Go to Loop
        #
        # Quit CAN IO thread Loop
        print("Quit CAN_IO_Thread_Loop")

    def start_canio_thread(self):
        if (self.Flag_canio_thread is False):
            self.Flag_canio_thread = True
            #
            self.canio_thread = threading.Thread(target=self.canio_thread_proc)
            self.canio_thread.start()
        #
        # Quit CAN IO Thread

    def stop_canio_thread(self):
        self.Flag_canio_thread = False
        self.canio_thread.join()

    def input(self, boardId, portNo):
        canId = boardId & 0x0f
        idx = portNo / 8
        bitNo = portNo % 8
        data = self.read_can_buffer_ary[canId][idx]
        return (data & (1 << bitNo))

    def inputInt(self, boardId):
        canId = boardId & 0x0f
        data0 = self.read_can_buffer_ary[canId][0]
        data1 = self.read_can_buffer_ary[canId][1]
        data2 = self.read_can_buffer_ary[canId][2]
        data3 = self.read_can_buffer_ary[canId][3]
        data = (data3 << 24) | (data2 << 16) | (data1 << 8) | data0
        return (data)

    def output(self, boardId, portNo, onoff):
        canId = boardId & 0x0f
        idx = int(portNo / 8)
        bitNo = portNo % 8
        if (onoff):
            self.write_can_buffer_ary[canId][idx] = \
                self.write_can_buffer_ary[canId][idx] | (1 << bitNo)
        else:
            self.write_can_buffer_ary[canId][idx] = \
                self.write_can_buffer_ary[canId][idx] & ~(1 << bitNo)
        return

    def set_tx_buff(self, dat):
        """Send CAN Data.

        Parameters
        ----------
        self
            instance object
        dat
            write can data struct

        Returns
        ----------
        None
        """
        packet = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        cmd_bit = 1

        if dat.bnum > 3:
            dat.bnum = 2

        cmd_bit = 1 * dat.bnum

        if not dat.eid_en:
            packet[0] = ((dat.id & 0x7F8) >> 3) & 0xFF
            packet[1] = ((dat.id & 0x7) << 5) & 0xFF
            packet[2] = 0
            packet[3] = 0
        else:
            packet[0] = (dat.id & 0x1FE00000) >> 21
            packet[1] = self.kMSK_EXIDE
            packet[1] |= (dat.id & 0x1C0000) >> 13
            packet[1] |= (dat.id & 0x30000) >> 16
            packet[2] = (dat.id & 0xFF00) >> 8
            packet[3] = (dat.id & 0xFF)

        if dat.len >= 9:
            dat.len = 8

        packet[4] = dat.len

        for i in range(dat.len):
            packet[5 + i] = dat.data[i]

        self.can_spi_write_tx_buff(self.kMCP2515_CMD_LDTXBUF | cmd_bit,
                                   packet, 5 + dat.len)

    def send_can_data(self, boadId, sData, cnt):
        """Send CAN Data.

        Parameters
        ----------
        self
            instance object
        boadId
            write boad ID
        sData
            write data
        cnt
            write data length

        Returns
        ----------
        None
        """

        sendData = can_data_st()
        sendData.id = self.kWRITE_CAN_ID_TOP + boadId
        sendData.len = cnt
        for i in range(cnt):
            sendData.data[i] = sData[i]
        self.set_tx_buff(sendData)
        self.can_spi_write_rts(0)

    def can_spi_write_tx_buff(self, cmd, packet, pktCnt):
        write_buffer = list(range(1 + pktCnt))
        write_buffer[0] = cmd
        for i in range(pktCnt):
            write_buffer[1+i] = packet[i]
        #
        self.can_spi_RW(write_buffer, len(write_buffer))

    def can_spi_RW(self, data, cnt):
        if cnt == 1:
            sendData = [0]
            sendData[0] = data
        else:
            sendData = list(range(cnt))

            for i in range(cnt):
                sendData[i] = data[i]

        GPIO.output(splebo_n.gpio_class.kCan_CS_pin, False)

        ret = self.spi_device.xfer2(sendData)

        GPIO.output(splebo_n.gpio_class.kCan_CS_pin, True)
        time.sleep(0.001)
        #
        return ret

    def can_spi_write_1byte(self, data):
        sendData = [0]
        sendData[0] = data
        return self.spi_device.xfer2(sendData)

    def can_spi_write_reg(self, addr, data):
        wd_buffer = list(range(3))
        wd_buffer[0] = self.kMCP2515_CMD_WRITE
        wd_buffer[1] = addr
        wd_buffer[2] = data
        return self.can_spi_RW(wd_buffer, 3)

    def can_spi_write_rts(self, bNum):
        """Write CAN RTS.

        Parameters
        ----------
        self
            instance object
        bNum
            write Bit Number

        Returns
        ----------
        None
        """
        write_data = self.kMCP2515_CMD_RTS | (0x1 << bNum)
        self.can_spi_RW(write_data, 1)

    def can_spi_read_reg(self, addr):
        ret = 0
        rd_buffer = [0, 0, 0]

        rd_buffer[0] = self.kMCP2515_CMD_READ
        rd_buffer[1] = addr
        rd_buffer[2] = 0
        ret = self.can_spi_RW(rd_buffer, 3)
        return ret[2]

    def can_spi_read_buf(self, addr, readData, cnt):
        cnt = cnt + 1
        rd_buffer = list(range(cnt))
        for i in range(cnt):
            rd_buffer[i] = 0x00
        rd_buffer[0] = addr
        ret = self.can_spi_RW(rd_buffer, len(rd_buffer))
        return ret[1:]

    def can_spi_read_RX_Status(self):
        ret = 0
        rd_buffer = [0, 0]

        rd_buffer[0] = self.kMCP2515_CMD_RXSTATUS
        rd_buffer[1] = 0
        ret = self.can_spi_RW(rd_buffer, 2)
        return ret[1]

    def can_spi_config(self, addr, mask, data):
        ret = 0
        wd_buffer = list(range(4))
        wd_buffer[0] = self.kMCP2515_CMD_BITMOD
        wd_buffer[1] = addr
        wd_buffer[2] = mask
        wd_buffer[3] = data
        ret = self.can_spi_RW(wd_buffer, 4)
        return ret

    def can_spi_read_RX_buff(self):
        """Read CAN Buffer.

        Parameters
        ----------
        self
            instance object

        Returns
        ----------
        readData
            read Can data
        """
        # can_d_st = can_data_st()

        read_data = self.can_spi_read_RX_Status()   # Read RX buff

        if (read_data & self.kMSK_MSGRX0) == self.kMSK_MSGRX0:  # Receive RXB0?
            readData = [0, 0, 0, 0, 0]
            read_data = self.can_spi_read_buf(self.kMCP2515_CMD_RDRXBUF,
                                              readData, 5)

            readData = [0, 0, 0, 0, 0, 0, 0, 0]
            read_data = self.can_spi_read_buf(self.kMCP2515_CMD_RDRXBUF | 0x02,
                                              readData, 8)
        else:
            read_data = [0]

        return read_data

    def set_write_can(self, can_Id, write_bit, is_on):
        """Write and Read CAN.

        Parameters
        ----------
        self
            instance object
        can_Id
            write boad ID
        write_bit
            can write bit
        is_on
            can write bit on off

        Returns
        ----------
        None
        """
        bit_pos = 0
        if write_bit >= 0 and write_bit <= 7:
            bit_pos = 0
        elif write_bit >= 8 and write_bit <= 15:
            bit_pos = 1
            write_bit = write_bit - 8
        elif write_bit >= 16 and write_bit <= 23:
            bit_pos = 2
            write_bit = write_bit - 16
        else:
            bit_pos = 3
            write_bit = write_bit - 24
        #
        if is_on:
            self.write_can_buffer_ary[can_Id][bit_pos] = \
                self.write_can_buffer_ary[can_Id][bit_pos] | (1 << write_bit)
        else:
            self.write_can_buffer_ary[can_Id][bit_pos] = \
                self.write_can_buffer_ary[can_Id][bit_pos] & ~(1 << write_bit)

    def read_control_can(self, can_Id):
        """Write and Read CAN.

        Parameters
        ----------
        self
            instance object
        can_Id
            write or read boad ID

        Returns
        ----------
        Comm Success
        """
        readData = [0, 0, 0, 0]

        self.send_can_data(can_Id, self.write_can_buffer_ary[can_Id],
                           self.kWRITE_DATA_SIZE)
        readData = self.can_spi_read_RX_buff()
        if len(readData) >= 4:
            self.read_can_buffer_ary[can_Id][0] = readData[0]
            self.read_can_buffer_ary[can_Id][1] = readData[1]
            self.read_can_buffer_ary[can_Id][2] = readData[2]
            self.read_can_buffer_ary[can_Id][3] = readData[3]
            return True
        #
        return False

# - Variable -----------------------------------------------------------


# - Function -----------------------------------------------------------


# ---------END OF CODE--------- #
