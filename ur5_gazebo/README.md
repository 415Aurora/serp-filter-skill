# UR5 Gazebo ROS Noetic Simulation

This project provides a comprehensive simulation environment for the Universal Robots UR5 robotic arm using ROS Noetic and Gazebo. It includes robot descriptions, simulation launch files, MoveIt! configurations, and a custom control GUI for advanced control algorithms.

## Project Structure

The workspace is organized into several ROS packages under the `src` directory:

```text
ur5_gazebo/
├── src/
│   └── universal_robot-noetic-devel/
│       ├── ur_description/          # URDF models, meshes, and configuration files for UR robots.
│       ├── ur_gazebo/               # Gazebo simulation launch files and custom control scripts.
│       │   ├── launch/              # Simulation bringup files (e.g., ur5_bringup.launch).
│       │   └── pd.py                # Custom GUI for PID and Computed Torque Control.
│       ├── ur5_moveit_config/       # MoveIt! configuration for motion planning with UR5.
│       ├── ur_kinematics/           # Kinematics plugins and utilities.
│       └── universal_robots/        # Metapackage for the repository.
└── README.md                        # This file.
```

## Key Features

- **High-Fidelity Simulation**: Gazebo-based environment for testing control algorithms and motion planning.
- **Custom Control GUI (`pd.py`)**:
  - **Control Methods**: Supports both Joint Space PID Control and Computed Torque Control (CTC).
  - **Kinematics**: Real-time calculation and display of the Jacobian matrix and DH Parameters.
  - **Visualization**: Live plotting of joint angles and errors using Matplotlib.
  - **Interface**: Intuitive Tkinter-based dashboard for robot interaction.
- **Motion Planning**: Full integration with MoveIt! for collision-aware trajectory generation.
- **Dynamic Modeling**: Uses KDL (Kinematics and Dynamics Library) for accurate torque calculations and gravity compensation.

## Getting Started

### Prerequisites

Ensure you have ROS Noetic installed on Ubuntu 20.04. Additional dependencies include:

```bash
sudo apt-get install ros-noetic-moveit ros-noetic-ros-control ros-noetic-ros-controllers ros-noetic-gazebo-ros-control
pip install numpy matplotlib
```

### Installation

1. Create a catkin workspace (if you haven't already):
   ```bash
   mkdir -p ~/ur5_ws/src
   cd ~/ur5_ws/src
   ```
2. Clone this repository into the `src` folder.
3. Build the workspace:
   ```bash
   cd ~/ur5_ws
   catkin_make
   source devel/setup.bash
   ```

### Usage

#### 1. Launch Gazebo Simulation
Bring up the UR5 robot in an empty Gazebo world:
```bash
roslaunch ur_gazebo ur5_bringup.launch
```

#### 2. Launch MoveIt! (Optional)
For motion planning and RViz visualization:
```bash
roslaunch ur5_moveit_config moveit_planning_execution.launch sim:=true
roslaunch ur5_moveit_config moveit_rviz.launch config:=true
```

#### 3. Run Custom Control GUI
Execute the custom controller for advanced control experiments:
```bash
rosrun ur_gazebo pd.py
```

## License

This project incorporates components from the `universal_robot` repository, which is primarily licensed under the BSD-3-Clause and Apache-2.0 licenses. Please refer to the package-specific LICENSE files for details.
