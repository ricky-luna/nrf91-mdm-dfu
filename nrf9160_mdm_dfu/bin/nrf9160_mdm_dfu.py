from nrf9160_mdm_dfu.api import nrf_dfu_API
import os
import time
import argparse

def main():

    start = time.time()
    global event_received

    parser = argparse.ArgumentParser(description='Update the firmware of nrf9160 devices.')
    group =  parser.add_mutually_exclusive_group(required = True)
    group.add_argument('--update', help='update firmware', action='store_true')
    group.add_argument('--read', dest='read', type=str, nargs=3, metavar=('Addr', 'Len', 'file'), help='Reading from the modem, Addr and Len must be hex values, file is a file path')
    group.add_argument('--UUID', help='read UUID', dest='UUID', action='store_true')
    group.add_argument('--digest', help='read digest from modem', dest='digest', action='store_true')
    parser.add_argument('-s', '--snr', dest='snr', type=int, help='Serialnumber for the nrf9160 device.')
    parser.add_argument('-q', '--quiet', dest='quiet', help='Enables quiet mode.', action='store_true')
    parser.add_argument('--fwpath', dest='fwpath', help='firmware update image path', type=str, nargs=1, metavar='path', default=["firmware.update.image.hex"])
    parser.add_argument('--ipcpath', dest='ipcpath', help='IPC hex file path', type=str, nargs=1, metavar='path')
    parser.add_argument('--fwdigestpath', dest='fwdigestpath', help='firmware update image digest path', type=str, nargs=1, metavar='path', default=["firmware.update.image.digest.txt"])

    args = parser.parse_args()
    nrf_dfu = nrf_dfu_API.nrf_dfu_API(quiet=args.quiet)
    if args.read is None and args.update is None:
        print ("No arguments found")
        return -1

    if args.read is not None:
        if not "0x" in args.read[0]:
            print("ERROR: Addr must be a hexadecimal number.")
            return -1
        elif not "0x" in args.read[1]:
            print("ERROR: Len must be a hexadecimal number.")
            return -1
        if ((int(args.read[1], 16) % 4) != 0):
            print("ERROR: number of bytes must be a multiple of 4")
            return -1

    if args.update is not None:
        if not os.path.isfile(args.fwpath[0]):
            print ("ERROR: Missing file: firmware.update.image.hex")
            return -1
        if not os.path.isfile(args.fwdigestpath[0]):
            print ("ERROR: Missing file: firmware.update.image.digest.txt")
            return -1

    if ((args.ipcpath is not None) and (not os.path.isfile(args.ipcpath[0]))):
        print("ERROR: Missing file: ipc_dfu.*.ihex")
    if nrf_dfu.init(args.snr, args.ipcpath) < 0:
        nrf_dfu.close()
        return -1

    if (args.read is not None):
        if nrf_dfu.read(args.read[0], args.read[1], args.read[2]) < 0:
            nrf_dfu.close()
            return -1

    elif (args.update):
        if nrf_dfu.update_firmware(args.fwpath[0]) < 0:
            nrf_dfu.close()
            return -1

        if nrf_dfu.verify_update(args.fwpath[0], args.fwdigestpath[0]) < 0:
            nrf_dfu.close()
            return -1

    elif (args.UUID):
        return_value, uuid_value = nrf_dfu.read_uuid()
        if return_value != 0:
            nrf_dfu.close()
            print("ERROR: Reading uuid failed")
            return -1

    elif args.digest:
        return_value, digest = nrf_dfu.read_digest()
        if return_value != 0:
            nrf_dfu.close()
            print("ERROR: Reading digest failed")
            return -1

    end = time.time()
    time_used = end - start
    if (not args.quiet):
        print("Total time used: %f" % time_used)
    nrf_dfu.close()

    return 0

if __name__ == "__main__":
    main()

