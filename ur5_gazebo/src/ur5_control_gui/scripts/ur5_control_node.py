#!/usr/bin/env python3
import rospy
import threading
from ur5_control_gui.controller import UR5Controller
from ur5_control_gui.gui import UR5GUI

def main():
    rospy.init_node('ur5_control_gui_node')
    
    # Initialize controller
    controller = UR5Controller()
    controller.wait_for_services()
    
    # Initialize GUI
    gui = UR5GUI(controller)
    
    # Start GUI in main thread (Tkinter requirement)
    gui_ready = threading.Event()
    gui.start(gui_ready)

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
