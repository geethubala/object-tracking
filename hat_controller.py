#!/usr/bin/env python2

import argparse
import logging
from logging import info
from threading import Thread

import calibrate_servo
import pantilthat as pth
from common_constants import LOGGING_ARGS
from hat_servo import HatServo
from location_client import LocationClient

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--grpc", required=True, help="gRPC location server hostname")
    parser.add_argument("-a", "--alternate", default=False, action="store_true", help="Alternate servo actions [false]")
    parser.add_argument("-c", "--calib", default=False, action="store_true", help="Calibration mode [false]")
    parser.add_argument("-v", "--verbose", default=logging.INFO, help="Include debugging info",
                        action="store_const", dest="loglevel", const=logging.DEBUG)
    args = vars(parser.parse_args())
    alternate = args["alternate"]
    calib = args["calib"]

    logging.basicConfig(**LOGGING_ARGS)

    locations = LocationClient(args["grpc"]).start()

    # Create servos
    servo_x = HatServo("Pan", alternate, pth.pan, 1.0, 8)
    servo_y = HatServo("Tilt", alternate, pth.tilt, 1.0, 8)

    calib_t = None
    if calib:
        calib_t = Thread(target=calibrate_servo.calibrate, args=(locations, servo_x, servo_y))
        calib_t.start()
    else:
        if alternate:
            # Set servo X to go first if alternating
            servo_x.ready_event.set()

    servo_x.start(False, lambda: locations.get_x(), servo_y.ready_event if not calib else None)
    servo_y.start(False, lambda: locations.get_y(), servo_x.ready_event if not calib else None)

    try:
        if calib_t is not None:
            calib_t.join()
        else:
            servo_x.join()
            servo_y.join()
    except KeyboardInterrupt:
        pass
    finally:
        servo_x.stop()
        servo_y.stop()
        locations.stop()

    info("Exiting...")
