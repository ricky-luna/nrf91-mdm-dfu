from pynrfjprog import API
import time
import sys
import argparse
import time
import codecs
import mmap
import enum
from intelhex import IntelHex
from pynrfjprog import Hex

PACKAGE_VERSION = '0.10.0'


@enum.unique
class NrfDfuErr(enum.IntEnum):
    """

    """

    SUCCESS                 =  0
    TIME_OUT                = -1
    WRONG_FAMILY_FOR_TOOL   = -2
    MISSING_IPC_FILE        = -3
    DFU_ERROR               = -4
    INVALID_PARAMETER       = -5


    NRFJPROG_ERRROR         = -100


class nrf_dfu_API(object):

    def __init__(self, quiet=False, verbose=False):
        self._quiet = quiet
        self._verbose = verbose
        self.api = API.API("NRF91")

    def init(self, snr=None, ipc_path=None):
        self.api.open()
        if (snr is not None):
            self.api.connect_to_emu_with_snr(snr)
        else:
            self.api.connect_to_emu_without_snr()
            self.api.sys_reset()

        if (self.api.read_device_family == API.DeviceFamily.NRF91):
            print("ERROR: Wrong device for tool, this tool is only available for NRF91 family")
            return NrfDfuErr.WRONG_FAMILY_FOR_TOOL

        if (not self._quiet):
            print("Configure APP IPC as non-secure")
        self.api.write_u32(0x500038A8, 0x00000002, True)

        if (not self._quiet):
            print("Configure IPC HW for DFU")
        self.api.write_u32(0x4002A514, 0x00000002, True)
        self.api.write_u32(0x4002A51C, 0x00000008, True)
        self.api.write_u32(0x4002A610, 0x21000000, True)
        self.api.write_u32(0x4002A614, 0x00000000, True)
        self.api.write_u32(0x4002A590, 0x00000001, True)
        self.api.write_u32(0x4002A598, 0x00000004, True)
        self.api.write_u32(0x4002A5A0, 0x00000010, True)
        self.acknowlage_events()

        if (not self._quiet):
            print ("Configure APP RAM as non-secure")
        self.api.power_ram_all()
        regidx = 32 * 4
        ramregion_base = 0x50003700

        while (regidx != 0):
            regidx = regidx - 4
            permreg = ramregion_base + regidx
            self.api.write_u32(permreg, 0x00000007, True)

        if (not self._quiet):
            print("Store DFU indication into shared memory")
        self.api.write_u32(0x20000000, 0x80010000, True)
        self.api.write_u32(0x20000004, 0x2100000C, True)
        self.api.write_u32(0x20000008, 0x0003FC00, True)

        if (not self._quiet):
            print("Power up / reset modem")
        self.api.write_u32(0x50005610, 0x00000000, True)
        self.api.write_u32(0x50005614, 0x00000001, True)
        self.api.write_u32(0x50005610, 0x00000001, True)
        self.api.write_u32(0x50005614, 0x00000000, True)
        self.api.write_u32(0x50005610, 0x00000000, True)

        if (not self._quiet):
            print("Start polling IPC.MODEM_CTRL_EVENT to receive root key digest")
        start_time = time.time()
        event_received = False
        while (event_received == False):
            if ((time.time() - start_time) > 10):
                print ("ERROR: Time out, no event received after 10 sec.")
                return NrfDfuErr.TIME_OUT
            return_value, event_received = self.get_event_status()
            if return_value < 0:
                return return_value

        self.acknowlage_events()

        return_value, modem_response = self.read_be(0x2000000C)

        if (not self._quiet):
            print ("Modem responded with %s" % modem_response)

        digest = ""
        for i in range(0x20000010, 0x20000030, 4):
            return_value, lelevel = self.hex_read(i)
            digest = digest + lelevel


        if (not self._quiet):
            print ("Modem root key digest received: %s" % digest)

        return_value = self.program(digest, ipc_path)
        if (return_value < 0):
            return return_value
        if (not self._quiet):
            print ("Store IPC DFU executable into shared memory")
            print ("Send IPC.APP_CTRL_TASK")
        self.api.write_u32(0x4002A004, 0x00000001, False)

        if (not self._quiet):
            print ("Start polling IPC.MODEM_CTRL_EVENT To receive 'Started' indication from DFU executable")

        start_time = time.time()
        event_received = False
        while (event_received == False):
            if ((time.time() - start_time) > 10):
                print ("ERROR: Time out, no event received after 10 sec.")
                return NrfDfuErr.TIME_OUT
            return_value, event_received = self.get_event_status()
            if return_value < 0:
                return return_value

        self.acknowlage_events()

        if (not self._quiet):
            print("IPC DFU 'Started' indication from DFU received")

        self.read_be(0x2000000C)

        return NrfDfuErr.SUCCESS


    def get_event_status(self):

        fault_event_detected = self.api.read(0x4002A100,4)
        command_event_detected = self.api.read(0x4002A108,4)
        data_event_detected = self.api.read(0x4002A110,4)

        if (fault_event_detected[0] != 0):
            print("Fault detected. Error Code: {}".format(fault_event_detected[0]))
            event_received = True
            return (NrfDfuErr.DFU_ERROR, event_received)
        elif (command_event_detected[0] != 0):
            event_received = True
            return (NrfDfuErr.SUCCESS, event_received)
        elif (data_event_detected[0] != 0):
            event_received = True
            return (NrfDfuErr.SUCCESS, event_received)
        else:
            event_received = False

        return (NrfDfuErr.SUCCESS, event_received)


    def read_be(self, addr):
        belevel = ""
        belevel_temp = "%08x"%(self.api.read_u32(addr))
        for i in range(0,7,2):
           belevel = belevel + belevel_temp[i] + belevel_temp[i+1]

        return (NrfDfuErr.SUCCESS, belevel)


    def hex_read(self, addr):
        lelevel_temp = "%08x"%(self.api.read_u32(addr))
        lelevel= lelevel_temp[6] + lelevel_temp[7] + lelevel_temp[4] + lelevel_temp[5] + lelevel_temp[2] + lelevel_temp[3] + lelevel_temp[0] + lelevel_temp[1]

        return (NrfDfuErr.SUCCESS, lelevel)

    def acknowlage_events(self):

        self.api.write_u32(0x4002A100, 0, False)
        self.api.write_u32(0x4002A108, 0, False)
        self.api.write_u32(0x4002A110, 0, False)

        return NrfDfuErr.SUCCESS


    def program(self, modem_digest, path=None):

        # Parse the hex file with the help of the HEX module
        if path is not None:
            test_program = Hex.Hex(path[0])
        else:
            try:
                test_program = Hex.Hex(modem_digest[0:7].upper()+".ipc_dfu.signed.ihex")
            except:
                print("ERROR: cant find: "+modem_digest[0:7]+".ipc_dfu.signed.ihex")
                print("ERROR: Missing correct ipc_dfu for current verison.")
                return NrfDfuErr.MISSING_IPC_FILE

        # Program the parsed hex into the device's memory.
        for segment in test_program:
            self.api.write(segment.address, segment.data, False)

        return NrfDfuErr.SUCCESS

    def update_firmware(self, hex_file_path):
        firmware_start = time.time()
        if (not self._quiet):
            print("Updating modem firmware")

        buffer_size=0x3FC00 - 0x18
        test_program = Hex.Hex(hex_file_path)
        program_start = time.time()

        for segment in test_program:
            data = []
            address = segment.address
            length = len(segment.data)
            max_length = len(segment.data)
            start = 0
            if (not self._quiet):
                print("Programming pages from address %s" % hex(address))
            if (length > buffer_size - 1):
                end = buffer_size
                length = end - start
            else:
                end = length

            while True:
                if (address % 8192 != 0):
                    if (not self._quiet):
                        print("address missalignement")
                    length += (address % 8192)
                    address = address - (address % 8192)
                    if (not self._quiet):
                        print ("Address aligned to {}".format(address))
                    data = [0xFF]*(address % 8192)

                data += segment.data[start:end]

                if (length % 8192 != 0):
                    length += (length % 8192)
                    data += [0xFF] * (length % 8192)

                self.api.write(0x20000018, data, False)
                self.api.write_u32(0x20000010, address, False)
                self.api.write_u32(0x20000014, length, False)
                self.api.write_u32(0x4002A100, 1, False)

                #initiate write
                self.api.write_u32(0x2000000C, 0x00000003, True)
                self.api.write_u32(0x4002A004, 0x00000001, False)

                start_time = time.time()
                event_received = False
                while (event_received == False):
                    if ((time.time() - start_time) > 10):
                        print ("ERROR: Time out, no event received after 10 sec.")
                        return NrfDfuErr.TIME_OUT
                    return_value, event_received = self.get_event_status()
                    if return_value < 0:
                        return return_value

                self.acknowlage_events()

                return_value, modem_response = self.read_be(0x2000000C)

                if (modem_response == "5a000001"):
                    print("\n\n ERROR: UNKNOWN COMMAND")
                    return NrfDfuErr.DFU_ERROR
                elif (modem_response == "5a000002"):
                    print("\n\n ERROR: COMMAND ERROR")
                    error_result = self.api.read_u32(0x20000010)
                    print("Program failed at {}".format(hex(error_result)))
                    return NrfDfuErr.DFU_ERROR

                if (length < buffer_size - 1):
                    break
                else:
                    start = start + length
                    address =  address +length
                    if end + length >= max_length:
                        end = max_length
                    else:
                        end = end + length

        program_end = time.time()
        if (not self._quiet):
            print ("Programing firmware time: %f" % (program_end - program_start))
        fimrware_end = time.time()
        if (not self._quiet):
            print ("Firmware update time including overhead: %f" % (fimrware_end - firmware_start))
            print ("Firmware updated.")
        return NrfDfuErr.SUCCESS

    def partial_erase(self, address, length):
        if (not self._quiet):
            print("Erasing pages from address %s" % hex(address))
        if (address % 8192 != 0):
            print ("ERROR: Address is not page aligned")
            return NrfDfuErr.INVALID_PARAMETER

        if (length % 8192 != 0):
            print ("ERROR: Length is not page aligned")
            return NrfDfuErr.INVALID_PARAMETER
        if (length == 0):
            print ("ERROR: Length can not be 0")
            return NrfDfuErr.INVALID_PARAMETER

        self.api.write_u32(0x20000010, address, False)
        self.api.write_u32(0x20000014, length, False)

        self.api.write_u32(0x2000000C, 0x00000002, False)
        self.api.write_u32(0x4002A004, 0x00000001, False)

        start_time = time.time()
        event_received = False
        while (event_received == False):
            if ((time.time() - start_time) > 10):
                print ("ERROR: Time out, no event received after 10 sec.")
                return NrfDfuErr.TIME_OUT
            return_value, event_received = self.get_event_status()
            if return_value < 0:
                return return_value

        self.acknowlage_events()

        return_value, modem_response = self.read_be(0x2000000C)

        if (modem_response == "5a000001"):
            print("\n\n ERROR: UNKNOWN COMMAND")
            return NrfDfuErr.DFU_ERROR
        elif (modem_response == "5a000002"):
            print("\n\n ERROR: COMMAND ERROR")
            error_result = self.api.read_u32(0x20000010)
            print("ERROR: Program failed at %s" % hex(error_result))
            return NrfDfuErr.DFU_ERROR

        if (not self._quiet):
            print("Erasing pages complete.")

        return NrfDfuErr.SUCCESS

    def verify_update(self, hex_file_path, fw_digest_path):
        if (not self._quiet):
            print ("Starting verification")
        address = []
        length = []

        test_program = Hex.Hex(hex_file_path)

        for segment in test_program:
            if segment.address < 0x1000000:
                address.append(segment.address)
                length.append(len(segment.data))

        self.api.write_u32(0x2000000C, 0x00000007, True)
        self.api.write_u32(0x20000010, len(address), False)

        for n in range(0, len(address)):
            self.api.write_u32(0x20000014+(n*8), address[n], False)
            self.api.write_u32(0x20000018+(n*8), length[n], False)

        self.api.write_u32(0x4002A004, 0x00000001, False)

        start_time = time.time()
        event_received = False
        while (event_received == False):
            if ((time.time() - start_time) > 10):
                print ("ERROR: Time out, no event received after 10 sec.")
                return NrfDfuErr.TIME_OUT
            return_value, event_received = self.get_event_status()
            if return_value < 0:
                return return_value

        self.acknowlage_events()

        return_value, modem_response = self.read_be(0x2000000C)

        #print ("Modem responded with %s" % modem_response)

        if (modem_response == "5a000001"):
            print("\n\n ERROR: UNKNOWN COMMAND")
            return NrfDfuErr.DFU_ERROR
        elif (modem_response == "5a000002"):
            print("\n\n ERROR: COMMAND ERROR")
            error_result = self.api.read_u32(0x20000010)
            print("ERROR: Program failed at %s" % hex(error_result))
            return NrfDfuErr.DFU_ERROR

        return_value, digest = self.read_digest()
        datafile = open(fw_digest_path)
        for line in datafile:
            if ("%s"%digest).upper() in line:
                if (not self._quiet):
                    print ("Verification success")
                verified = True
                break
            else:
                verified = False

        if not verified:
            if (not self._quiet):
                print("Verification failed")
            return NrfDfuErr.DFU_ERROR
        else:
            return NrfDfuErr.SUCCESS


    def read(self, address, length, hex_file_path):

        if ((int(length, 16) % 4) != 0):
            print("ERROR: number of bytes must be a multiple of 4")
            return NrfDfuErr.INVALID_PARAMETER

        if (not self._quiet):
            print("Reading %s bytes from address %s" % (length, address))

        open(hex_file_path, 'w+')
        ih = IntelHex(hex_file_path)
        ih.__init__()

        self.api.write_u32(0x2000000C, 0x00000004, True)
        self.api.write_u32(0x20000010, int(address, 16), False)
        self.api.write_u32(0x20000014, int(length, 16), False)

        self.api.write_u32(0x4002A004, 0x00000001, False)

        start_time = time.time()
        event_received = False
        while (event_received == False):
            if ((time.time() - start_time) > 10):
                print ("ERROR: Time out, no event received after 10 sec.")
                return NrfDfuErr.TIME_OUT
            return_value, event_received = self.get_event_status()
            if return_value < 0:
                return return_value

        self.acknowlage_events()

        return_value, modem_response = self.read_be(0x2000000C)

        if (modem_response == "5a000001"):
            print("\n\n ERROR: UNKNOWN COMMAND")
            return NrfDfuErr.DFU_ERROR
        elif (modem_response == "5a000002"):
            print("\n\n ERROR: COMMAND ERROR")
            error_result = self.api.read_u32(0x20000010)
            print("ERROR: Read failed at {}".format(hex(error_result)))
            return NrfDfuErr.DFU_ERROR

        word_count = int(length, 16)//4

        for i in range(0, word_count):
            return_value, lelevel = self.hex_read(0x20000010+(i*4))
            ih.puts(int(address,16)+(i*4), codecs.decode(lelevel, "hex"))

        ih.write_hex_file(hex_file_path)
        if (not self._quiet):
            print ("Reading completed")

        return NrfDfuErr.SUCCESS

    def read_uuid(self):
        """
        Reads and returns the UUID

        :return tuple of NrfDfuErr type and string with UUID:
        """
        if (not self._quiet):
            print("UUID reading started")
        self.api.write_u32(0x2000000C, 0x00000008, True)

        self.api.write_u32(0x4002A004, 0x00000001, False)
        start_time = time.time()
        event_received = False
        while (event_received == False):
            if ((time.time() - start_time) > 10):
                print ("ERROR: Time out, no event received after 10 sec.")
                return NrfDfuErr.TIME_OUT, ""
            return_value, event_received = self.get_event_status()
            if return_value < 0:
                return return_value, ""

        self.acknowlage_events()

        return_value, modem_response = self.read_be(0x2000000C)

        if (modem_response == "5a000001"):
            print("\n\n ERROR: UNKNOWN COMMAND")
            return NrfDfuErr.DFU_ERROR, ""
        elif (modem_response == "5a000002"):
            print("\n\n ERROR: COMMAND ERROR")
            error_result = self.api.read_u32(0x20000010)
            print("ERROR: Read failed at %s" % hex(error_result))
            return NrfDfuErr.DFU_ERROR, ""

        a = []
        for i in range(0, 9):
            for n in (0, 8, 16, 24):
                a.append(chr(int(hex(int(self.api.read_u32(0x20000010 + (i * 4))) >> n & 0xff), 16)))
        print (''.join(a))

        return NrfDfuErr.SUCCESS, a

    def read_digest(self):
        """
        Reads and returns the digest from the modem

        :return tuple of NrfDfuErr type and string with digest:
        """
        if not self._quiet:
            print("Digest reading started")

        digest = ""
        for i in range(0x20000010, 0x20000030, 4):
            return_value, belevel = self.read_be(i)
            digest = digest + belevel

        if not self._quiet:
            print("Firmware digest received from modem: %s" % digest)

        # Return hardcoded NrfDfuErr.SUCCESS due to self.read_be always returns NrfDfuErr.SUCCESS
        return NrfDfuErr.SUCCESS, digest

    def close(self):
        """
        Closes connection to the device

        :return:
        """
        self.api.sys_reset()
        self.api.go()
        self.api.close()

        return NrfDfuErr.SUCCESS
