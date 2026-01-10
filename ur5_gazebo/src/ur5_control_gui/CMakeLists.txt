cmake_minimum_required(VERSION 3.0.2)
project(ur5_control_gui)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  sensor_msgs
  trajectory_msgs
  control_msgs
  actionlib
  controller_manager_msgs
  moveit_commander
  moveit_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/ur5_control_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
