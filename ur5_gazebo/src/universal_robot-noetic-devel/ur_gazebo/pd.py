#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from trajectory_msgs.msg import *
from control_msgs.msg import *
import rospy
import actionlib
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Pose, Point, Quaternion, Twist
import tf2_ros
import tf_conversions
import math
import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog, messagebox, filedialog
import threading
import sys
import os
import time
import traceback
from urdf_parser_py.urdf import URDF
import matplotlib
matplotlib.use('TkAgg')  # 使用TkAgg后端
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style
from kdl_parser_py import urdf
import PyKDL
from urdf_parser_py.urdf import URDF as URDFParser
from controller_manager_msgs.srv import SwitchController, SwitchControllerRequest
from std_msgs.msg import Float64MultiArray

import moveit_commander
from moveit_commander import MoveGroupCommander, PlanningSceneInterface, RobotCommander
from moveit_msgs.msg import  PlanningScene, ObjectColor,CollisionObject, AttachedCollisionObject,Constraints,OrientationConstraint
from geometry_msgs.msg import PoseStamped, Pose
# 全局变量
JOINT_NAMES = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
               'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
JOINT_NAMES_TF= ['base','shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
               'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
# 假设你已经知道UR5机器人的D-H参数
dh_parameters = {
    "shoulder_pan_joint": {"a": 0, "alpha":np.pi/2, "d": 0.089159, "theta": 0},  # 示例UR5的参数值
    "shoulder_lift_joint": {"a": -0.425, "alpha":0, "d": 0, "theta": 0},
    "elbow_joint": {"a": -0.39225, "alpha": 0, "d": 0, "theta": 0},
    "wrist_1_joint": {"a": 0, "alpha": np.pi/2, "d": 0.10915, "theta": 0},
    "wrist_2_joint": {"a": 0, "alpha": -np.pi/2, "d": 0.09465, "theta": 0},
    "wrist_3_joint": {"a": 0, "alpha": 0, "d": 0.0823, "theta": 0}
}
dh_parameters_tf = {
    "base": {"a": 0, "alpha":0, "d": 0, "theta": 0},
    "shoulder_pan_joint": {"a": 0, "alpha":np.pi/2, "d": 0.089159, "theta": 0},  # 示例UR5的参数值
    "shoulder_lift_joint": {"a": -0.425, "alpha":0, "d": 0, "theta": 0},
    "elbow_joint": {"a": -0.39225, "alpha": 0, "d": 0, "theta": 0},
    "wrist_1_joint": {"a": 0, "alpha": np.pi/2, "d": 0.10915, "theta": 0},
    "wrist_2_joint": {"a": 0, "alpha": -np.pi/2, "d": 0.09465, "theta": 0},
    "wrist_3_joint": {"a": 0, "alpha": 0, "d": 0.0823, "theta": 0}
}
# 设置绘图样式
style.use('ggplot')

class UR5Control:
    def __init__(self):
        rospy.init_node("ur5_joint_control")
        
        # 创建TF监听器
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        
        # 等待TF树建立
        rospy.loginfo("等待TF树建立...")
        rospy.sleep(2.0)  # 等待2秒确保TF树建立
        
        # 初始化控制器切换服务
        self.switch_controller_srv = rospy.ServiceProxy('/controller_manager/switch_controller', SwitchController)
        rospy.loginfo("等待控制器管理服务...")
        try:
            self.switch_controller_srv.wait_for_service(timeout=10.0)
        except rospy.ROSException:
            rospy.logwarn("控制器管理服务不可用，将使用默认控制器")
            self.switch_controller_srv = None
        
        # 存储当前控制器状态
        self.current_controllers = ['eff_joint_traj_controller']  # 默认控制器
        self.effort_controller_name = "joint_group_eff_controller"  # 使用组力矩控制器
        
        # 初始化action client (用于位置控制)
        self.client = actionlib.SimpleActionClient(
            '/eff_joint_traj_controller/follow_joint_trajectory', 
            FollowJointTrajectoryAction
        )
        rospy.loginfo("等待位置控制器服务器连接...")
        if not self.client.wait_for_server(rospy.Duration(10.0)):
            rospy.logwarn("无法连接到位置控制器动作服务器")
        
        # 创建力矩指令发布器
        self.effort_pub = rospy.Publisher(
            '/joint_group_eff_controller/command', 
            Float64MultiArray, 
            queue_size=10
        )
        rospy.loginfo("创建力矩指令发布器")
        
        # # 获取初始关节状态
        # self.home_joint_positions, _ = self.get_current_joint_states()

        # 给定的初始关节角度（单位为度）
        joint_angles_degrees = [0, -90, 0, -90, 0, 0]

        # 将度数转换为弧度
        self.home_joint_positions = [math.radians(angle) for angle in joint_angles_degrees]
    
        if self.home_joint_positions is None:
            rospy.logerr("无法获取初始关节状态")
            sys.exit(1)
        
        # 详细输出关节状态用于调试
        rospy.loginfo("初始关节状态:")
        for i, name in enumerate(JOINT_NAMES):
            rospy.loginfo(f"  {name}: {self.home_joint_positions[i]:.4f} rad")
        
        # 控制状态标志
        self.is_moving = False
        self.stop_requested = False
        
        # PID控制参数
        self.Kp = 1.5      # 比例增益
        self.Ki = 0.01     # 积分增益
        self.Kd = 0.4      # 微分增益
        self.control_frequency = 20  # 控制频率 (Hz)
        
        # 计算力矩控制参数 - 初始化为中等误差区的安全值
        self.ct_Kp = 60.0   # 比例增益
        self.ct_Kd = 10.0  # 微分增益
        
        # 积分误差项
        self.integral_errors = [0.0] * len(JOINT_NAMES)
        
        # 绘图数据存储
        self.plot_data = {name: {'time': [], 'angle': []} for name in JOINT_NAMES}
        self.plot_start_time = time.time()
        self.plotting_active = False
        
        # 控制方法选择 (默认为PID控制)
        self.control_method = "PID"
        
        # 加载机器人模型用于计算力矩控制
        self.robot_model = self.load_robot_model()
        
        # 创建GUI线程
        self.gui_thread = threading.Thread(target=self.create_gui)
        self.gui_thread.daemon = True
        self.gui_thread.start()
        
        # 添加同步机制确保GUI初始化完成
        self.gui_ready = threading.Event()
        
        # 主循环
        self.running = True
        self.rate = rospy.Rate(self.control_frequency)
        
        # 等待GUI初始化完成
        rospy.loginfo("等待GUI初始化...")
        self.gui_ready.wait()
        rospy.loginfo("GUI初始化完成，准备接受命令")
        
        # 测试Home位置移动（现在在GUI初始化后）
        rospy.loginfo("测试移动到初始Home位置...")
        self._go_home()
        rospy.loginfo("测试完成")
        
        # self.set_scene() 
        
        while not rospy.is_shutdown() and self.running:
            self.rate.sleep()

    def switch_controllers(self, start_controllers, stop_controllers, strictness=1):
        """切换控制器"""
        if not self.switch_controller_srv:
            rospy.logwarn("控制器切换服务不可用，无法切换控制器")
            return False
            
        try:
            req = SwitchControllerRequest()
            req.start_controllers = start_controllers
            req.stop_controllers = stop_controllers
            req.strictness = strictness
            req.start_asap = True
            req.timeout = 1.0
            
            resp = self.switch_controller_srv(req)
            if resp.ok:
                rospy.loginfo(f"控制器切换成功: 启动{start_controllers}, 停止{stop_controllers}")
                # 更新当前控制器状态
                for c in stop_controllers:
                    if c in self.current_controllers:
                        self.current_controllers.remove(c)
                self.current_controllers.extend(start_controllers)
                return True
            else:
                rospy.logerr(f"控制器切换失败: {resp}")
                return False
        except rospy.ServiceException as e:
            rospy.logerr(f"控制器切换服务调用失败: {str(e)}")
            return False

    def load_robot_model(self):
        """加载机器人模型用于计算力矩控制"""
        try:
            # 从参数服务器获取机器人描述
            robot_description = rospy.get_param('/robot_description')
            
            # 解析URDF
            success, tree = urdf.treeFromString(robot_description)
            if not success:
                rospy.logerr("无法从URDF创建KDL树")
                return None
            
            # 创建动力学链
            chain = tree.getChain("base", "wrist_3_link")
            if not chain:
                rospy.logerr("无法创建KDL链")
                return None
            
            # 创建动力学求解器
            gravity = PyKDL.Vector(0, 0, -9.81)  # 重力向量
            dyn_solver = PyKDL.ChainDynParam(chain, gravity)
            
            rospy.loginfo("成功加载机器人动力学模型")
            return {
                'chain': chain,
                'dyn_solver': dyn_solver,
                'gravity': gravity
            }
        except Exception as e:
            rospy.logerr(f"加载机器人模型时出错: {str(e)}")
            return None

    def get_current_joint_states(self):
        """获取当前关节状态（位置和速度）"""
        try:
            #"joint_states"：指定需要接收的主题名； JointState 是 ROS 中标准的消息类型，用于描述机器人各个关节的状态，通常包含关节的位置、速度和力等信息。
            joint_states = rospy.wait_for_message("joint_states", JointState, timeout=5.0)
            # 确保关节顺序正确
            positions = []
            velocities = []
            for name in JOINT_NAMES:
                if name in joint_states.name:
                    idx = joint_states.name.index(name)
                    positions.append(joint_states.position[idx])
                    velocities.append(joint_states.velocity[idx])
                else:
                    rospy.logwarn(f"未找到关节: {name}")
                    return None, None
            return positions, velocities
        except rospy.ROSException as e:
            rospy.logerr(f"获取关节状态超时: {str(e)}")
            return None, None

    def get_current_pose(self):
        """获取当前末端执行器位姿，并返回齐次变换矩阵"""
        try:
            # 使用TF2获取变换
            trans = self.tf_buffer.lookup_transform(
                'base',  # 基座到末端执行器的变换
                'wrist_3_link',  # 末端执行器的链路
                rospy.Time(0),
                rospy.Duration(1.0)
            )
            
            # 获取平移部分
            position = trans.transform.translation
            # 获取旋转部分（四元数）
            orientation = trans.transform.rotation
            
            # 将四元数转换为旋转矩阵
            rotation_matrix = self.quaternion_to_rotation_matrix(orientation)
            
            # 生成齐次变换矩阵（4x4矩阵）
            transformation_matrix = np.eye(4)  # 初始化为单位矩阵
            transformation_matrix[:3, :3] = rotation_matrix  # 设置旋转部分
            transformation_matrix[0, 3] = position.x  # 设置平移部分
            transformation_matrix[1, 3] = position.y
            transformation_matrix[2, 3] = position.z
            
            # 返回齐次变换矩阵
            return transformation_matrix
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            rospy.logwarn(f"无法获取TF变换: {str(e)}")
            return None

    def quaternion_to_rotation_matrix(self, quaternion):
        """将四元数转换为旋转矩阵"""
        q = [quaternion.x, quaternion.y, quaternion.z, quaternion.w]
        # 创建旋转矩阵
        R = np.array([
            [1 - 2*(q[1]**2 + q[2]**2), 2*(q[0]*q[1] - q[2]*q[3]), 2*(q[0]*q[2] + q[1]*q[3])],
            [2*(q[0]*q[1] + q[2]*q[3]), 1 - 2*(q[0]**2 + q[2]**2), 2*(q[1]*q[2] - q[0]*q[3])],
            [2*(q[0]*q[2] - q[1]*q[3]), 2*(q[1]*q[2] + q[0]*q[3]), 1 - 2*(q[0]**2 + q[1]**2)]
        ])
        return R

    def get_jacobian_matrix(self):
        """计算并返回当前末端执行器的雅可比矩阵"""
        try:
            # 获取当前的关节状态
            current_positions, _ = self.get_current_joint_states()

            if current_positions is None:
                rospy.logerr("无法获取当前关节状态，无法计算雅可比矩阵")
                return None

            # 创建关节位置数组
            q = PyKDL.JntArray(len(JOINT_NAMES))
            for i in range(len(JOINT_NAMES)):
                q[i] = current_positions[i]

            # 创建机器人模型链
            chain = self.robot_model['chain']  # 你之前已经加载了机器人模型的链条

            # 创建ChainJntToJacSolver对象，用于计算雅可比矩阵
            jacobian_solver = PyKDL.ChainJntToJacSolver(chain)

            # 初始化雅可比矩阵
            jacobian = PyKDL.Jacobian(len(JOINT_NAMES))
            # 计算雅可比矩阵get_jaco
            jacobian_solver.JntToJac(q, jacobian)
          
            # 将雅可比矩阵转为可打印的字符串格式
            jacobian_str = "\n".join(
                ["\t".join([f"{jacobian[i, j]:.2f}" for j in range(len(JOINT_NAMES))]) for i in range(6)]
            )
            return jacobian_str
        except Exception as e:
            rospy.logerr(f"计算雅可比矩阵时出错: {str(e)}")
            return None

    def update_dh_parameters(self, joint_angles):
        """根据当前关节角度更新D-H参数"""
        updated_dh = dh_parameters.copy()  # 获取原始的D-H参数
        for i, joint_name in enumerate(JOINT_NAMES):
            # 更新每个关节的theta（关节角度）
            updated_dh[joint_name]["theta"] = joint_angles[i]
        
        return updated_dh

    def update_dh_parameters_tf(self, joint_angles):
        """根据当前关节角度更新D-H参数"""
        updated_dh_tf = dh_parameters_tf.copy()  # 获取原始的D-H参数
        for i, joint_name in enumerate(JOINT_NAMES):
            # 更新每个关节的theta（关节角度）
            updated_dh_tf[joint_name]["theta"] = joint_angles[i]
        
        return updated_dh_tf


    def format_dh_parameters(self, dh_parameters):
        """格式化 D-H 参数为列表形式"""
        formatted_data = []
        for joint_name, params in dh_parameters.items():
            formatted_data.append((
                joint_name,
                f"{np.degrees(params['theta']):.2f}°",  # 将角度转为度数并格式化
                f"{params['a']}",
                f"{np.degrees(params['alpha']):.2f}°",  # 将角度转为度数并格式化
                f"{params['d']}"
            ))
        return formatted_data
   
    # def format_dh_parameters(self, dh_parameters):
    #     """格式化 D-H 参数为字符串"""
    #     dh_str = ""
    #     for joint_name, params in dh_parameters.items():
    #         dh_str += f"{joint_name}: θ={np.degrees(params['theta']):.2f}°, a={params['a']}, alpha={np.degrees(params['alpha']):.2f}°, d={params['d']}\n"
    #     return dh_str

    def dh_to_transformation_matrix(self, joint_1_params, joint_2_params):
        """
        根据关节 1 和 关节 2 的 D-H 参数计算关节 2 相对于关节 1 的齐次变换矩阵。
        joint_1_params 和 joint_2_params 是字典类型，包含了关节的 D-H 参数：
        {"theta": θ, "alpha": α, "a": a, "d": d}
        """
        # 提取 D-H 参数
        a1, alpha1, d1, theta1 = joint_1_params["a"], joint_1_params["alpha"], joint_1_params["d"], joint_1_params["theta"]
        a2, alpha2, d2, theta2 = joint_2_params["a"], joint_2_params["alpha"], joint_2_params["d"], joint_2_params["theta"]
        # # 计算各个角度的三角函数值
        # cos_theta1 = np.cos(theta1)
        # sin_theta1 = np.sin(theta1)
        # cos_alpha1 = np.cos(alpha1)
        # sin_alpha1 = np.sin(alpha1)
        cos_theta2 = np.cos(theta2)
        sin_theta2 = np.sin(theta2)
        cos_alpha2 = np.cos(alpha2)
        sin_alpha2 = np.sin(alpha2)
        # 根据公式计算齐次变换矩阵 T_{1}^{2}
        T2_to_1 = np.array([
       
        [cos_theta2, -sin_theta2 * cos_alpha2, sin_theta2 * sin_alpha2, a2 * cos_theta2],
        [sin_theta2, cos_theta2 * cos_alpha2, -cos_theta2 * sin_alpha2, a2 * sin_theta2],
        [0, sin_alpha2, cos_alpha2, d2],
        [0, 0, 0, 1]
        
        ])

        return T2_to_1

    def calculate_transformation_matrix(self, dh_parameters, joint_1, joint_2):
        """
        计算从关节m到关节n的变换矩阵。如果是相邻关节，直接计算变换矩阵；
        否则，递归计算变换矩阵的乘积。
        :param dh_parameters: 所有关节的D-H参数字典
        :param joint_1: 起始关节
        :param joint_2: 目标关节
        :return: 变换矩阵
        """
        # 获取关节的顺序
        joint_names = list(dh_parameters_tf.keys())
        
        m = joint_names.index(joint_1)
        n = joint_names.index(joint_2)

        # 如果 m == n，直接返回单位矩阵
        if m == n:
            return np.eye(4)
        
        # 确保 m < n，便于计算
        if m > n:
            m, n = n, m
            reverse = True
        else:
            reverse = False

        # 计算变换矩阵的乘积
        transformation_matrix = np.eye(4)

        # 如果是相邻关节，直接计算变换矩阵
        if abs(m - n) == 1:
            joint_1_params = dh_parameters[joint_names[m]]
            joint_2_params = dh_parameters[joint_names[n]]
        # 打印 joint_1_params 和 joint_2_params 的 D-H 参数
            print(f"关节 {joint_names[m]} 的 D-H 参数: "
                f"θ={np.degrees(joint_1_params['theta']):.2f}° "
                f"α={np.degrees(joint_1_params['alpha']):.2f}° "
                f"a={joint_1_params['a']} "
                f"d={joint_1_params['d']}")

            print(f"关节 {joint_names[n]} 的 D-H 参数: "
                f"θ={np.degrees(joint_2_params['theta']):.2f}° "
                f"α={np.degrees(joint_2_params['alpha']):.2f}° "
                f"a={joint_2_params['a']} "
                f"d={joint_2_params['d']}")         
          
            transformation_matrix = self.dh_to_transformation_matrix(joint_1_params, joint_2_params)
        else:
            # 如果是非相邻关节，递归计算矩阵乘积
            for i in range(m, n):
                joint_1_params = dh_parameters_tf[joint_names[i]]
                joint_2_params = dh_parameters_tf[joint_names[i+1]]
                transformation_matrix = np.dot(transformation_matrix, self.dh_to_transformation_matrix(joint_1_params, joint_2_params))

        # 如果 m > n，需要对变换矩阵取逆
        if reverse:
            transformation_matrix = np.linalg.inv(transformation_matrix)

        return transformation_matrix

    def move_to_joint_positions(self, target_positions, duration=1.0):
        """移动机械臂到指定关节位置"""
        if self.stop_requested:
            return False
            
        current_positions, _ = self.get_current_joint_states()
        if current_positions is None:
            rospy.logerr("无法获取当前关节状态，终止移动")
            return False
            
        goal = FollowJointTrajectoryGoal()
        goal.trajectory = JointTrajectory()
        goal.trajectory.joint_names = JOINT_NAMES
        
        # 计算实际所需时间
        actual_duration = max(0.5, duration)  # 最小0.5秒
        
        # 创建轨迹点
        goal.trajectory.points = [
            JointTrajectoryPoint(positions=current_positions, 
                                 velocities=[0]*6, 
                                 time_from_start=rospy.Duration(0.0)),
            JointTrajectoryPoint(positions=target_positions, 
                                 velocities=[0]*6, 
                                 time_from_start=rospy.Duration(actual_duration))
        ]
        ##第一个点是当前关节位置，表示机械臂的起始位置。第二个点是目标关节位置 target_positions，表示机械臂的目标位置。

        self.client.send_goal(goal)
        
        # 带停止检查的等待
        start_time = time.time()
        timeout = actual_duration + 3.0  # 允许额外3秒缓冲
        
        while time.time() - start_time < timeout:
            if self.stop_requested:
                self.client.cancel_goal()
                rospy.loginfo("移动已取消")
                return False
                
            state = self.client.get_state()
            if state in [actionlib.GoalStatus.SUCCEEDED, 
                         actionlib.GoalStatus.PREEMPTED, 
                         actionlib.GoalStatus.ABORTED]:
                return state == actionlib.GoalStatus.SUCCEEDED
                
            rospy.sleep(0.1)
            
        self.client.cancel_goal()
        rospy.logwarn("移动超时")
        return False

    def joint_space_control(self, target_positions, duration):
        """使用PID控制移动到目标关节位置"""
        self.is_moving = True
        self.stop_requested = False
        self.integral_errors = [0.0] * len(JOINT_NAMES)  # 重置积分项
        
        # 启动绘图
        self.start_plotting()
        
        # 获取当前关节位置
        current_positions, _ = self.get_current_joint_states()
        if current_positions is None:
            self.status_var.set("状态: 无法获取关节状态")
            self.is_moving = False
            return False
            
        # 初始化变量
        start_time = time.time()
        prev_time = start_time
        prev_errors = [0.0] * len(JOINT_NAMES)
        
        # 控制循环
        while not rospy.is_shutdown() and not self.stop_requested:
            # 添加额外的停止检查点（在关键操作之前）
            if self.stop_requested:
                break

            # 计算已用时间
            current_time = time.time()
            elapsed_time = current_time - start_time
            dt = current_time - prev_time
            prev_time = current_time
            
            if dt <= 0:
                dt = 0.001  # 默认50ms
                
            # 检查是否超时
            if elapsed_time > duration * 1.5:  # 允许50%超时
                self.status_var.set("状态: 移动超时")
                self.is_moving = False
                self.plotting_active = False  # 停止绘图
                return False
                
            # 获取当前关节位置
            current_positions, _ = self.get_current_joint_states()
            if current_positions is None:
                rospy.sleep(0.1)
                continue
                
            # 计算误差
            errors = [t - c for t, c in zip(target_positions, current_positions)]
            
            # 检查是否到达目标
            max_error = max(abs(e) for e in errors)
            if max_error < 0.03:  # 0.01弧度约0.57度
                self.status_var.set("状态: 已到达目标姿态")
                self.is_moving = False
                self.plotting_active = False  # 停止绘图
                return True

            # 更新积分项
            self.integral_errors = [i + e * dt for i, e in zip(self.integral_errors, errors)]
            
            # 计算导数项
            derivatives = [(e - p) / dt if dt > 0 else 0.0 for e, p in zip(errors, prev_errors)]
            prev_errors = errors
            
            # 计算PID输出
            pid_outputs = [
                self.Kp * e + self.Ki * i + self.Kd * d
                for e, i, d in zip(errors, self.integral_errors, derivatives)
            ]
            
            # 限制输出范围
            max_output = max(abs(o) for o in pid_outputs)
            if max_output > 1.0:
                pid_outputs = [o / max_output for o in pid_outputs]
            
            # 计算新目标位置
            new_positions = [c + o * dt for c, o in zip(current_positions, pid_outputs)]
            
            # 创建目标消息
            goal = FollowJointTrajectoryGoal()
            goal.trajectory = JointTrajectory()
            goal.trajectory.joint_names = JOINT_NAMES
            
            # 创建轨迹点 (立即执行)
            goal.trajectory.points = [
                JointTrajectoryPoint(positions=new_positions, 
                                     velocities=[0]*6, 
                                     time_from_start=rospy.Duration(0.1))  # 0.1秒内完成
            ]
            
            # 发送目标
            self.client.send_goal(goal)
            
            # 更新状态
            error_str = ", ".join(f"{np.degrees(e):.1f}°" for e in errors)
            self.status_var.set(f"状态: 移动中... 最大误差: {np.degrees(max_error):.1f}°")
            if self.root:
                self.root.update()
            
            rospy.sleep(1.0 / self.control_frequency)
        
        # 用户停止
        self.status_var.set("状态: 移动已停止")
        self.is_moving = False
        self.plotting_active = False  # 停止绘图
        return False
    
    def computed_torque_control(self, target_positions, duration):
        """使用计算力矩控制移动到目标关节位置"""
        # 切换到力矩控制器
        if not self.switch_to_effort_controller():
            rospy.logerr("无法切换到力矩控制器，使用备用位置控制")
            return self.joint_space_control(target_positions, duration)
        
        self.is_moving = True
        self.stop_requested = False
        
        # 启动绘图
        self.start_plotting()
        
        # 获取当前关节位置和速度
        current_positions, current_velocities = self.get_current_joint_states()
        if current_positions is None or current_velocities is None:
            self.status_var.set("状态: 无法获取关节状态")
            self.is_moving = False
            return False
        
        # 初始化变量
        start_time = time.time()
        prev_time = start_time
        
        # 目标速度（初始为零）
        target_velocities = [0.0] * len(JOINT_NAMES)
        
        # 添加滤波器和约束
        filtered_velocities = current_velocities.copy()
        
        # 力矩控制参数
        MAX_TORQUE = 30.0  # 关节峰值力矩约束（Nm）
        TORQUE_RATE_LIMIT = 10.0  # 相邻周期力矩最大变化（Nm/周期）
        prev_torques = [0.0] * len(JOINT_NAMES)  # 上一周期力矩
        
        # 添加重力补偿标志和变量
        gravity_compensation_active = False
        GRAVITY_COMP_THRESHOLD = 0.1  # 当误差小于0.1弧度时启用重力补偿

        # 控制循环
        while not rospy.is_shutdown() and not self.stop_requested:
            # 添加额外的停止检查点（在关键操作之前）
            if self.stop_requested:
                break
            # 计算已用时间
            current_time = time.time()
            elapsed_time = current_time - start_time
            dt = current_time - prev_time
            prev_time = current_time
            
            if dt <= 0:
                dt = 0.05  # 默认50ms
                
            # 检查是否超时
            if elapsed_time > duration * 1.5:  # 允许50%超时
                self.status_var.set("状态: 移动超时")
                self.is_moving = False
                self.plotting_active = False  # 停止绘图
                self.switch_back_to_position_controller()  # 切回位置控制器
                return False
                
            # 获取当前关节位置和速度
            current_positions, current_velocities = self.get_current_joint_states()
            if current_positions is None or current_velocities is None:
                rospy.sleep(0.1)
                continue
                
            # 应用低通滤波器减少噪声
            for i in range(len(current_velocities)):
                filtered_velocities[i] = 0.8 * filtered_velocities[i] + 0.2 * current_velocities[i]
            current_velocities = filtered_velocities
            
            # 计算位置误差和速度误差
            pos_errors = [t - c for t, c in zip(target_positions, current_positions)]
            vel_errors = [tv - cv for tv, cv in zip(target_velocities, current_velocities)]
            
            # 检查是否到达目标
            max_error = max(abs(e) for e in pos_errors)
            gravity_compensation_active = max_error < 0.1
            
            # 根据最大位置误差选择参数区域
            if max_error > 0.5:    # 高误差区（大误差）
                self.ct_Kp = 40
                self.ct_Kd = 5
            elif max_error > 0.1:  # 中误差区
                self.ct_Kp = 60
                self.ct_Kd = 10
            else:                  # 低误差区（小误差）
                self.ct_Kp = 100
                self.ct_Kd = 15
            
            # 计算控制输出 (计算力矩控制)
            if self.robot_model:
                # 使用动力学模型计算力矩
                raw_torques = self.calculate_torques(
                    current_positions, 
                    current_velocities,
                    target_positions,
                    target_velocities,
                    pos_errors,
                    vel_errors,
                    gravity_compensation_active  # 传递重力补偿标志
                )
                
                if raw_torques is None:
                    rospy.logwarn("力矩计算失败，使用PD作为后备")
                    # 后备方案：使用PD控制
                    raw_torques = [
                        self.ct_Kp * e_p + self.ct_Kd * e_v
                        for e_p, e_v in zip(pos_errors, vel_errors)
                    ]
                
                filtered_torques = []
                for i in range(len(JOINT_NAMES)):
                    # 低通滤波（α=0.3）
                    filtered_t = 0.7 * prev_torques[i] + 0.3 * raw_torques[i]
                    
                    # 力矩变化率约束
                    t_diff = filtered_t - prev_torques[i]
                    if abs(t_diff) > TORQUE_RATE_LIMIT:
                        filtered_t = prev_torques[i] + np.sign(t_diff) * TORQUE_RATE_LIMIT
                    
                    # 绝对值限幅
                    filtered_t = np.clip(filtered_t, -MAX_TORQUE, MAX_TORQUE)
                    
                    filtered_torques.append(filtered_t)
                    prev_torques[i] = filtered_t
            else:
                # 如果没有动力学模型，使用PD控制
                rospy.logwarn("无动力学模型，使用PD控制")
                filtered_torques = [
                    self.ct_Kp * e_p + self.ct_Kd * e_v
                    for e_p, e_v in zip(pos_errors, vel_errors)
                ]
                # 应用相同的滤波和限幅
                for i in range(len(JOINT_NAMES)):
                    filtered_torques[i] = np.clip(
                        0.7 * prev_torques[i] + 0.3 * filtered_torques[i],
                        -MAX_TORQUE, MAX_TORQUE
                    )
                    prev_torques[i] = filtered_torques[i]
            
            if max_error < 0.01:  # 0.01弧度约0.57度
                # 到达目标后发送维持力矩
                for _ in range(10):  # 维持0.5秒
                    if self.stop_requested:
                        break
                self.effort_pub.publish(effort_msg)
                rospy.sleep(0.05)
            
                self.status_var.set("状态: 已到达目标姿态")
                self.is_moving = False
                self.plotting_active = False
                self.switch_back_to_position_controller()
                return True
            
            # 创建力矩指令消息
            effort_msg = Float64MultiArray()
            effort_msg.data = filtered_torques
            
            # 发布力矩指令
            self.effort_pub.publish(effort_msg)
            
            # 更新状态
            self.status_var.set(f"状态: 力矩控制中... 最大误差: {np.degrees(max_error):.1f}° | Kp={self.ct_Kp:.1f}, Kd={self.ct_Kd:.1f} | 力矩: {[f'{t:.1f}' for t in filtered_torques]}")
            if self.root:
                self.root.update()
            
            rospy.sleep(1.0 / self.control_frequency)
        
        # 用户停止
        self.status_var.set("状态: 移动已停止")
        self.is_moving = False
        self.plotting_active = False  # 停止绘图
        self.switch_back_to_position_controller()  # 切回位置控制器
        return False

    def switch_to_effort_controller(self):
        """切换到力矩控制器"""
        rospy.loginfo("尝试切换到力矩控制器...")
        
        # 如果已经是力矩控制器则直接返回
        if self.effort_controller_name in self.current_controllers:
            rospy.loginfo("力矩控制器已激活")
            return True
            
        # 如果控制器切换服务不可用，尝试直接使用力矩控制器
        if not self.switch_controller_srv:
            rospy.logwarn("控制器切换服务不可用，尝试直接使用力矩控制器")
            self.current_controllers = [self.effort_controller_name]
            return True
            
        # 停止当前控制器，启动力矩控制器
        return self.switch_controllers(
            start_controllers=[self.effort_controller_name],
            stop_controllers=self.current_controllers,
            strictness=2
        )

    def switch_back_to_position_controller(self):
        """切换回位置控制器"""
        rospy.loginfo("尝试切换回位置控制器...")
        
        # 如果已经是位置控制器则直接返回
        if 'eff_joint_traj_controller' in self.current_controllers:
            return True
            
        # 如果控制器切换服务不可用，尝试直接使用位置控制器
        if not self.switch_controller_srv:
            rospy.logwarn("控制器切换服务不可用，尝试直接使用位置控制器")
            self.current_controllers = ['eff_joint_traj_controller']
            return True
            
        # 停止力矩控制器，启动位置控制器
        return self.switch_controllers(
            start_controllers=['eff_joint_traj_controller'],
            stop_controllers=[self.effort_controller_name],
            strictness=2
        )

    def calculate_torques(self, positions, velocities, target_positions, target_velocities, pos_errors, vel_errors,gravity_compensation_active):
        """计算所需的关节力矩"""
        try:
            # 创建KDL数据结构
            q = PyKDL.JntArray(len(JOINT_NAMES))
            qdot = PyKDL.JntArray(len(JOINT_NAMES))
            
            for i in range(len(JOINT_NAMES)):
                q[i] = positions[i]
                qdot[i] = velocities[i]
            
            # 计算质量矩阵
            M = PyKDL.JntSpaceInertiaMatrix(len(JOINT_NAMES))
            self.robot_model['dyn_solver'].JntToMass(q, M)
            
            # 计算重力向量
            grav = PyKDL.JntArray(len(JOINT_NAMES))
            self.robot_model['dyn_solver'].JntToGravity(q, grav)
            
            # 计算科里奥利力向量
            coriolis = PyKDL.JntArray(len(JOINT_NAMES))
            self.robot_model['dyn_solver'].JntToCoriolis(q, qdot, coriolis)
            
            # 当接近目标位置时，增加重力补偿增益
            gravity_gain = 1.5 if gravity_compensation_active else 1.0

            # 计算力矩 (τ = M * (q̈_d + K_p * e + K_d * ė) + C + G)
            # 其中 q̈_d = 0 (假设期望加速度为零)
            torques = PyKDL.JntArray(len(JOINT_NAMES))
            
            for i in range(len(JOINT_NAMES)):
                # 计算控制加速度
                accel = self.ct_Kp * pos_errors[i] + self.ct_Kd * vel_errors[i]
                
                # 计算所需的力矩
                torque = 0.0
                for j in range(len(JOINT_NAMES)):
                    torque += M[i, j] * accel
                torque += coriolis[i] + gravity_gain * grav[i]
                
                # 添加关节约束保护
                MAX_TORQUE = 100.0  # Nm
                if torque > MAX_TORQUE:
                    torque = MAX_TORQUE
                elif torque < -MAX_TORQUE:
                    torque = -MAX_TORQUE
                    
                torques[i] = torque
            
            return [torques[i] for i in range(len(JOINT_NAMES))]
        except Exception as e:
            rospy.logerr(f"力矩计算错误: {str(e)}")
            return None

    # 以下是未修改的GUI和辅助方法，保持不变
    def create_gui(self):
        """创建交互式GUI"""
        self.root = tk.Tk()
        self.root.title("UR5关节空间控制")
        self.root.geometry("800x700")  # 增大窗口尺寸以容纳绘图
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown_system)
        
        # 控制按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10, fill=tk.X, padx=10)
        
        # 控制方法选择框架
        method_frame = tk.LabelFrame(button_frame, text="控制方法", padx=5, pady=5)
        method_frame.grid(row=0, column=0, columnspan=5, padx=5, pady=5, sticky="ew")
        
        # 控制按钮框架中的新按钮
        transformation_btn = tk.Button(button_frame, text="显示齐次变换矩阵", command=self.show_transformation_matrix,
                                        height=2, width=15, font=("Arial", 10), bg="#ffcc99")
        transformation_btn.grid(row=2, column=0, padx=5, pady=5)

        jacobian_btn = tk.Button(button_frame, text="显示雅可比矩阵", command=self.show_jacobian_matrix,
                                height=2, width=15, font=("Arial", 10), bg="#ffcc99")
        jacobian_btn.grid(row=2, column=1, padx=5, pady=5)

        dh_btn = tk.Button(button_frame, text="显示标准D-H参数表", command=self.show_dh_parameters,
                        height=2, width=15, font=("Arial", 10), bg="#ffcc99")
        dh_btn.grid(row=2, column=2, padx=5, pady=5)
       
        # 在现有 GUI 中添加按钮，显示任意两个关节的变换矩阵
        transformation_btn = tk.Button(button_frame, text="显示关节间变换矩阵", command=self.prompt_joint_selection,
                        height=2, width=15, font=("Arial", 10), bg="#ffcc99")
        transformation_btn.grid(row=2, column=3, padx=5, pady=5)

        # 控制方法选择变量
        self.control_var = tk.StringVar(value="PID")
        
        # PID控制单选按钮
        pid_radio = tk.Radiobutton(
            method_frame, text="PID控制", variable=self.control_var, value="PID",
            command=self.update_control_method, font=("Arial", 9)
        )
        pid_radio.grid(row=0, column=0, padx=5, pady=2)
        
        # 计算力矩控制单选按钮
        ct_radio = tk.Radiobutton(
            method_frame, text="计算力矩控制", variable=self.control_var, value="CT",
            command=self.update_control_method, font=("Arial", 9)
        )
        ct_radio.grid(row=0, column=1, padx=5, pady=2)
        

        # 控制方法状态标签
        self.method_status = tk.StringVar()
        method_label = tk.Label(method_frame, textvariable=self.method_status, font=("Arial", 9), fg="blue")
        method_label.grid(row=0, column=2, padx=10, pady=2)
        self.update_control_method()  # 初始化状态
        
        # 控制按钮
        self.target_btn = tk.Button(button_frame, text="设置目标姿态", command=self.prompt_joint_target,
                  height=2, width=15, font=("Arial", 10))
        self.target_btn.grid(row=1, column=0, padx=5, pady=5)
        
        self.home_btn = tk.Button(button_frame, text="返回Home位置", command=self.go_home,
                  height=2, width=15, font=("Arial", 10))
        self.home_btn.grid(row=1, column=1, padx=5, pady=5)
        
        # 停止按钮
        self.stop_btn = tk.Button(button_frame, text="停止当前任务", command=self.stop_movement,
                  height=2, width=15, font=("Arial", 10), state=tk.DISABLED, bg="#ff9999")
        self.stop_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # 保存绘图按钮
        self.save_btn = tk.Button(button_frame, text="保存绘图", command=self.save_plot,
                  height=2, width=15, font=("Arial", 10), bg="#99ccff")
        self.save_btn.grid(row=1, column=3, padx=5, pady=5)
        
        self.exit_btn = tk.Button(button_frame, text="退出系统", command=self.shutdown_system,
                  height=2, width=15, font=("Arial", 10), bg="#ff6666")
        self.exit_btn.grid(row=1, column=4, padx=5, pady=5)
        
        # 参数调整框架
        param_frame = tk.LabelFrame(self.root, text="控制参数调整", padx=10, pady=10)
        param_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 使用Notebook实现标签页
        self.param_notebook = ttk.Notebook(param_frame)
        self.param_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # PID控制参数标签页
        pid_frame = tk.Frame(self.param_notebook)
        self.param_notebook.add(pid_frame, text="PID参数")
        
        # 计算力矩控制参数标签页
        ct_frame = tk.Frame(self.param_notebook)
        self.param_notebook.add(ct_frame, text="计算力矩参数")
        
        # PID参数调整
        tk.Label(pid_frame, text="比例增益 (Kp):").grid(row=0, column=0, sticky="w", padx=5)
        self.kp_var = tk.DoubleVar(value=self.Kp)
        kp_scale = tk.Scale(pid_frame, variable=self.kp_var, from_=0.1, to=5.0, 
                           resolution=0.1, orient=tk.HORIZONTAL, length=200,
                           command=self.update_pid_kp)
        kp_scale.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(pid_frame, text="积分增益 (Ki):").grid(row=1, column=0, sticky="w", padx=5)
        self.ki_var = tk.DoubleVar(value=self.Ki)
        ki_scale = tk.Scale(pid_frame, variable=self.ki_var, from_=0.0, to=0.5, 
                           resolution=0.01, orient=tk.HORIZONTAL, length=200,
                           command=self.update_pid_ki)
        ki_scale.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(pid_frame, text="微分增益 (Kd):").grid(row=2, column=0, sticky="w", padx=5)
        self.kd_var = tk.DoubleVar(value=self.Kd)
        kd_scale = tk.Scale(pid_frame, variable=self.kd_var, from_=0.0, to=2.0, 
                           resolution=0.1, orient=tk.HORIZONTAL, length=200,
                           command=self.update_pid_kd)
        kd_scale.grid(row=2, column=1, padx=5, pady=5)
        
        # 计算力矩参数调整
        tk.Label(ct_frame, text="比例增益 (Kp):").grid(row=0, column=0, sticky="w", padx=5)
        self.ct_kp_var = tk.DoubleVar(value=self.ct_Kp)
        ct_kp_scale = tk.Scale(ct_frame, variable=self.ct_kp_var, from_=1.0, to=100.0, 
                              resolution=0.1, orient=tk.HORIZONTAL, length=200,
                              command=self.update_ct_kp)
        ct_kp_scale.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(ct_frame, text="微分增益 (Kd):").grid(row=1, column=0, sticky="w", padx=5)
        self.ct_kd_var = tk.DoubleVar(value=self.ct_Kd)
        ct_kd_scale = tk.Scale(ct_frame, variable=self.ct_kd_var, from_=1.0, to=20.0, 
                              resolution=0.1, orient=tk.HORIZONTAL, length=200,
                              command=self.update_ct_kd)
        ct_kd_scale.grid(row=1, column=1, padx=5, pady=5)
        
        # 状态显示框架
        status_frame = tk.LabelFrame(self.root, text="系统状态", padx=10, pady=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 初始位置显示
        self.home_pos_var = tk.StringVar(value="Home位置: 正在获取...")
        home_pos_label = tk.Label(status_frame, textvariable=self.home_pos_var, 
                                   font=("Arial", 10), anchor="w", justify="left")
        home_pos_label.pack(fill=tk.X, padx=5, pady=3)
        
        # 状态标签
        self.status_var = tk.StringVar(value="状态: 等待指令")
        status_label = tk.Label(status_frame, textvariable=self.status_var, 
                              font=("Arial", 10), anchor="w", justify="left")
        status_label.pack(fill=tk.X, padx=5, pady=3)
        
        # 当前位置显示
        self.position_var = tk.StringVar(value="末端位置: 正在获取...")
        position_label = tk.Label(status_frame, textvariable=self.position_var, 
                                font=("Arial", 10), anchor="w", justify="left")
        position_label.pack(fill=tk.X, padx=5, pady=3)
        
        # 关节状态显示
        self.joint_var = tk.StringVar(value="关节角度: 正在获取...")
        joint_label = tk.Label(status_frame, textvariable=self.joint_var, 
                             font=("Arial", 10), anchor="w", justify="left")
        joint_label.pack(fill=tk.X, padx=5, pady=3)
      
        # # 创建齐次变换矩阵显示标签
        # self.transformation_matrix_var = tk.StringVar()
        # self.transformation_matrix_label = tk.Label(status_frame, textvariable=self.transformation_matrix_var, font=("Arial", 10), anchor="w", justify="left")
        # self.transformation_matrix_label.pack(side=tk.LEFT, anchor="n", padx=5, pady=3)

        # # 创建在工具坐标系下雅可比矩阵显示标签
        # self.jacobian_matrix_var = tk.StringVar()
        # self.jacobian_matrix_label = tk.Label(status_frame, textvariable=self.jacobian_matrix_var, font=("Arial", 10), anchor="w", justify="left")
        # self.jacobian_matrix_label.pack(side=tk.LEFT, anchor="n", padx=40, pady=3)  # 增加水平间距   
       
        # # 创建D-H参数显示的StringVar变量
        # self.dh_parameters_var = tk.StringVar()
        # self.dh_parameters_label = tk.Label(status_frame, textvariable=self.dh_parameters_var, font=("Arial", 10), anchor="w", justify="left")
        # self.dh_parameters_label.pack(side=tk.LEFT, anchor="n", padx=40, pady=3)  # 增加水平间距
        # 显示矩阵的区域
        # self.matrix_display_var = tk.StringVar()
        # matrix_display_label = tk.Label(self.root, textvariable=self.matrix_display_var, font=("Arial", 10), anchor="w", justify="left")
        # matrix_display_label.pack(fill=tk.BOTH, padx=10, pady=10)

        # 设置初始关节状态显示
        if hasattr(self, 'home_joint_positions'):
            joint_str = "Home位置: "
            for i, name in enumerate(JOINT_NAMES):
                joint_str += f"{name}: {np.degrees(self.home_joint_positions[i]):.1f}°, "
            self.home_pos_var.set(joint_str[:-2])
        
        # 创建绘图区域
        plot_frame = tk.LabelFrame(self.root, text="关节转角变化曲线", padx=5, pady=5)
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Matplotlib图形
        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title('Control Results')
        self.ax.set_xlabel('Time/s')
        self.ax.set_ylabel('Angle/degree')
        self.ax.grid(True)
        
        # 为每个关节创建一条曲线
        self.lines = {}
        colors = ['b', 'g', 'r', 'c', 'm', 'y']
        for i, name in enumerate(JOINT_NAMES):
            line, = self.ax.plot([], [], label=name, color=colors[i % len(colors)])
            self.lines[name] = line
        
        self.ax.legend(loc='upper right')
        
        # 将图形嵌入Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)  

        # 启动状态更新线程
        threading.Thread(target=self.update_status_display, daemon=True).start()
        
        # 通知主线程GUI已就绪
        self.gui_ready.set()
        
        self.root.mainloop()

    def create_matrix_popup(self, title, data, update_func):
        """创建独立弹窗显示矩阵，并定期更新矩阵值"""
        popup = tk.Toplevel(self.root)
        popup.title(title)  # 设置窗口标题
        popup.geometry("600x400")  # 设置更小的弹窗大小
        
        # 创建一个框架来放置每个Label
        frame = tk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 判断数据类型：如果数据是列表形式的表格数据（如D-H参数），则按行显示
        row_labels = []  # 用于保存每一行的Label控件
        if isinstance(data, list) and all(isinstance(row, tuple) for row in data):  
            # 创建列标题
            columns = ["Joint", "θ (degrees)", "a", "α (degrees)", "d"]
            
            # 创建列标题标签
            for i, col_name in enumerate(columns):
                label = tk.Label(frame, text=col_name, font=("Arial", 10, 'bold'), relief="solid", width=15, anchor="center")
                label.grid(row=0, column=i, padx=5, pady=5)

            # 添加数据行
            for row_index, row in enumerate(data, start=1):
                joint_name, theta, a, alpha, d = row
                # 显示每个行数据
                joint_label = tk.Label(frame, text=joint_name, font=("Arial", 10), relief="solid", width=15, anchor="w")
                theta_label = tk.Label(frame, text=theta, font=("Arial", 10), relief="solid", width=15, anchor="center")
                a_label = tk.Label(frame, text=a, font=("Arial", 10), relief="solid", width=15, anchor="center")
                alpha_label = tk.Label(frame, text=alpha, font=("Arial", 10), relief="solid", width=15, anchor="center")
                d_label = tk.Label(frame, text=d, font=("Arial", 10), relief="solid", width=15, anchor="center")
                
                # 将每行的Label保存到row_labels
                row_labels.append((joint_label, theta_label, a_label, alpha_label, d_label))

                # 在表格中插入数据
                joint_label.grid(row=row_index, column=0, padx=5, pady=5)
                theta_label.grid(row=row_index, column=1, padx=5, pady=5)
                a_label.grid(row=row_index, column=2, padx=5, pady=5)
                alpha_label.grid(row=row_index, column=3, padx=5, pady=5)
                d_label.grid(row=row_index, column=4, padx=5, pady=5)

        else:
            # 否则以文本的方式显示矩阵内容（如齐次变换矩阵，雅可比矩阵）
            matrix_label = tk.Label(frame, text=data, font=("Arial", 10), anchor="w", justify="left", padx=10, pady=10)
            matrix_label.pack(fill=tk.BOTH, expand=True)
        
        # 更新矩阵内容的函数
        def update_matrix():
            """更新矩阵的内容"""
            if update_func:
                updated_data = update_func()  # 获取更新后的数据
                if isinstance(updated_data, list):  # 如果是D-H参数，更新每一行
                    for row_index, row in enumerate(updated_data):
                        joint_name, theta, a, alpha, d = row
                        # 更新每个Label的文本
                        row_labels[row_index][0].config(text=joint_name)
                        row_labels[row_index][1].config(text=theta)
                        row_labels[row_index][2].config(text=a)
                        row_labels[row_index][3].config(text=alpha)
                        row_labels[row_index][4].config(text=d)
                else:  # 如果是文本数据（齐次变换矩阵、雅可比矩阵）
                    matrix_label.config(text=updated_data)
                
                # 每隔500ms更新一次矩阵
                popup.after(500, update_matrix)

        # 启动定时更新
        update_matrix()

        # 添加关闭按钮
        close_button = tk.Button(popup, text="关闭", command=popup.destroy, font=("Arial", 10))
        close_button.pack(pady=10)


    def update_control_method(self):
        """更新控制方法显示"""
        method = self.control_var.get()
        self.control_method = method
        
        if method == "PID":
            self.method_status.set("当前使用: PID控制")
        else:
            if self.robot_model:
                self.method_status.set("当前使用: 计算力矩控制")
            else:
                self.method_status.set("警告: 无动力学模型，使用PD控制")
                self.control_var.set("PID")  # 回退到PID控制
    
    def update_pid_kp(self, value):
        """更新PID比例增益"""
        self.Kp = float(value)
        rospy.loginfo(f"更新PID Kp为: {self.Kp}")
    
    def update_pid_ki(self, value):
        """更新PID积分增益"""
        self.Ki = float(value)
        rospy.loginfo(f"更新PID Ki为: {self.Ki}")
    
    def update_pid_kd(self, value):
        """更新PID微分增益"""
        self.Kd = float(value)
        rospy.loginfo(f"更新PID Kd为: {self.Kd}")
    
    def update_ct_kp(self, value):
        """更新计算力矩比例增益"""
        self.ct_Kp = float(value)
        rospy.loginfo(f"更新计算力矩 Kp为: {self.ct_Kp}")
    
    def update_ct_kd(self, value):
        """更新计算力矩微分增益"""
        self.ct_Kd = float(value)
        rospy.loginfo(f"更新计算力矩 Kd为: {self.ct_Kd}")
    
    def start_plotting(self):
        """开始记录和绘制关节转角数据"""
        self.plotting_active = True
        self.plot_start_time = time.time()
        
        # 清空所有绘图数据
        for name in JOINT_NAMES:
            self.plot_data[name]['time'] = []
            self.plot_data[name]['angle'] = []
        
        # 获取初始关节状态
        initial_joints, _ = self.get_current_joint_states()
        if initial_joints:
            current_time = time.time() - self.plot_start_time
            for i, name in enumerate(JOINT_NAMES):
                self.plot_data[name]['time'].append(current_time)
                self.plot_data[name]['angle'].append(np.degrees(initial_joints[i]))
    
    def clear_plot(self):
        """清空绘图数据"""
        # 清空所有绘图数据
        for name in JOINT_NAMES:
            self.plot_data[name]['time'] = []
            self.plot_data[name]['angle'] = []
        
        # 重置线条数据
        for line in self.lines.values():
            line.set_data([], [])
        
        # 重置坐标轴
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
    
    def update_plot(self):
        """更新绘图显示"""
        if not self.plotting_active:
            return
        
        # 获取当前关节状态
        current_joints, _ = self.get_current_joint_states()
        if not current_joints:
            return
        
        # 更新绘图数据
        current_time = time.time() - self.plot_start_time
        for i, name in enumerate(JOINT_NAMES):
            self.plot_data[name]['time'].append(current_time)
            self.plot_data[name]['angle'].append(np.degrees(current_joints[i]))
            
            # 更新曲线数据
            self.lines[name].set_data(
                self.plot_data[name]['time'],
                self.plot_data[name]['angle']
            )
        
        # 调整坐标轴范围
        all_times = []
        all_angles = []
        for name in JOINT_NAMES:
            if self.plot_data[name]['time']:
                all_times.extend(self.plot_data[name]['time'])
                all_angles.extend(self.plot_data[name]['angle'])
        
        if all_times:
            min_time = min(all_times)
            max_time = max(all_times)
            min_angle = min(all_angles)
            max_angle = max(all_angles)
            
            # 添加10%的边界
            time_range = max(1.0, max_time - min_time) * 1.1
            angle_range = max(1.0, max_angle - min_angle) * 1.1
            
            self.ax.set_xlim(min_time, min_time + time_range)
            self.ax.set_ylim(min_angle - 0.1*angle_range, min_angle + angle_range)
        
        # 重绘图形
        self.canvas.draw()
    
    def save_plot(self):
        """保存当前绘图为图片文件"""
        if not self.plot_data[JOINT_NAMES[0]]['time']:
            messagebox.showwarning("警告", "没有可保存的绘图数据")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 图片", "*.png"), ("JPEG 图片", "*.jpg"), ("所有文件", "*.*")],
            title="保存关节转角曲线图"
        )
        
        if file_path:
            try:
                self.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("成功", f"图片已保存至:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存图片失败:\n{str(e)}")
   
    def update_status_display(self):
        """定期更新状态显示和绘图"""
        while not rospy.is_shutdown() and self.running:
            try:
                # 获取齐次变换矩阵
                transformation_matrix = self.get_current_pose()               
                if transformation_matrix is not None:
                    # 提取位置
                    current_pos = transformation_matrix[:3, 3]  # 位置是矩阵的最后一列（前三行）
                    # 更新末端位置
                    self.position_var.set(f"末端位置: x={current_pos[0]:.3f}, y={current_pos[1]:.3f}, z={current_pos[2]:.3f}")
                else:
                    self.position_var.set("末端位置: 获取失败")
              
                # 更新关节状态
                joint_states, _ = self.get_current_joint_states()
                if joint_states:
                    joint_str = "关节角度: "
                    for i, name in enumerate(JOINT_NAMES):
                        joint_str += f"{name}: {np.degrees(joint_states[i]):.1f}°, "
                    self.joint_var.set(joint_str[:-2])  # 去掉最后的逗号和空格
                else:
                    self.joint_var.set("关节角度: 获取失败")

                # 更新绘图
                if self.is_moving and self.plotting_active:
                    # 在GUI线程中更新绘图
                    self.root.after(0, self.update_plot)
                
                rospy.sleep(0.1)  # 每0.1秒更新一次
            except Exception as e:
                rospy.logerr(f"状态更新错误: {str(e)}")
                rospy.sleep(1.0)


    def prompt_joint_target(self):
        """提示用户输入目标关节角度和完成时间"""
        if self.is_moving:
            messagebox.showwarning("警告", "机械臂正在移动，请等待完成或停止当前任务")
            return
            
        # 获取当前关节状态作为默认值
        current_joints, _ = self.get_current_joint_states()
        if current_joints is None:
            messagebox.showerror("错误", "无法获取当前关节状态")
            return
            
        # 创建输入对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("设置目标姿态")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 添加关节输入框
        entries = []
        for i, name in enumerate(JOINT_NAMES):
            frame = tk.Frame(dialog)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            label = tk.Label(frame, text=f"{name} (度):", width=20, anchor="w")
            label.pack(side=tk.LEFT)
            
            # 将弧度转换为度作为默认值
            default_deg = np.degrees(current_joints[i])
            entry = tk.Entry(frame)
            entry.insert(0, f"{default_deg:.1f}")
            entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            entries.append(entry)
        
        # 添加时间输入框
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.X, padx=10, pady=10)
        label = tk.Label(frame, text="完成时间 (秒):", width=20, anchor="w")
        label.pack(side=tk.LEFT)
        time_entry = tk.Entry(frame)
        time_entry.insert(0, "10.0")
        time_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # 确认按钮
        def on_confirm():
            try:
                # 读取关节角度（转换为弧度）
                target_joints = []
                for entry in entries:
                    deg = float(entry.get())
                    target_joints.append(np.radians(deg))
                
                # 读取时间
                duration = float(time_entry.get())
                if duration <= 0:
                    raise ValueError("时间必须大于0")
                
                dialog.destroy()
                
                # 更新状态
                self.status_var.set("状态: 移动到目标姿态...")
                self.root.update()
                
                # 启用停止按钮
                self.stop_btn.config(state=tk.NORMAL)
                
                # 清空绘图
                self.clear_plot()
                
                # 在工作线程中执行移动
                threading.Thread(target=self.move_to_joint_target, 
                                args=(target_joints, duration)).start()
                
            except ValueError as e:
                messagebox.showerror("输入错误", f"无效输入: {str(e)}")
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        confirm_btn = tk.Button(btn_frame, text="确认", command=on_confirm, width=15)
        confirm_btn.pack(side=tk.LEFT, padx=10)
        cancel_btn = tk.Button(btn_frame, text="取消", command=dialog.destroy, width=15)
        cancel_btn.pack(side=tk.RIGHT, padx=10)
        
        dialog.wait_window(dialog)

    def move_to_joint_target(self, target_joints, duration):
        """移动到指定关节目标姿态"""
        # 检查是否在移动过程中被停止
        if self.stop_requested:
            return

        # 根据选择的控制方法执行移动
        if self.control_method == "PID":
            success = self.joint_space_control(target_joints, duration)
        else:
            success = self.computed_torque_control(target_joints, duration)
        
        # 只有在没有停止请求的情况下才更新按钮状态
        if not self.stop_requested:
            # 禁用停止按钮
            self.stop_btn.config(state=tk.DISABLED)
            
            if success:
                self.status_var.set("状态: 已到达目标姿态")
            else:
                self.status_var.set("状态: 移动未完成")
    

    def show_transformation_matrix(self):
        """显示齐次变换矩阵"""
        transformation_matrix = self.get_current_pose()  # 获取当前的末端执行器位置
        if transformation_matrix is not None:
            matrix_str = "\n".join(["\t".join([f"{value:.4f}" for value in row]) for row in transformation_matrix])
            self.create_matrix_popup("齐次变换矩阵", matrix_str, self.update_transformation_matrix_popup)  # 创建弹窗并更新
        else:
            self.create_matrix_popup("齐次变换矩阵", "获取失败", None)  # 获取失败

    def show_jacobian_matrix(self):
        """显示雅可比矩阵"""
        jacobian_matrix = self.get_jacobian_matrix()  # 获取当前的雅可比矩阵
        if jacobian_matrix is not None:
            self.create_matrix_popup("雅可比矩阵", jacobian_matrix, self.update_jacobian_matrix_popup)  # 创建弹窗并更新
        else:
            self.create_matrix_popup("雅可比矩阵", "获取失败", None)  # 获取失败

    def show_dh_parameters(self):
        """显示D-H参数"""
        joint_states, _ = self.get_current_joint_states()  # 获取当前的关节状态
        if joint_states is not None:
            updated_dh = self.update_dh_parameters(joint_states)  # 更新D-H参数
            formatted_data = self.format_dh_parameters(updated_dh)  # 格式化D-H参数为列表形式
            self.create_matrix_popup("D-H 参数表", formatted_data, self.update_dh_parameters_popup)  # 创建弹窗并显示表格
        else:                                           
            self.create_matrix_popup("D-H 参数表", "获取失败", None)  # 获取失败

    def prompt_joint_selection(self):
        """提示用户选择两个关节"""
        joint_1 = simpledialog.askstring("选择关节", "请输入第一个关节的名称（如: shoulder_pan_joint）:")
        joint_2 = simpledialog.askstring("选择关节", "请输入第二个关节的名称（如: elbow_joint）:")

        if joint_1 and joint_2 and joint_1 in JOINT_NAMES_TF and joint_2 in JOINT_NAMES_TF:
            self.show_jonit_to_joint_transformation_matrix(joint_1, joint_2)
        else:
            messagebox.showerror("错误", "无效的关节名称，请重新输入。")
 
    #  # 在机械臂下方添加一个table，使得机械臂只能够在上半空间进行规划和运动
    # # 避免碰撞到下方的桌子等其他物体
    # def set_scene(self):
    #     ## set table
    #     self.scene = PlanningSceneInterface()
    #     self.scene_pub = rospy.Publisher('planning_scene', PlanningScene, queue_size=5)
    #     self.colors = dict()
    #     rospy.sleep(1)
    #     table_id = 'table'
    #     self.scene.remove_world_object(table_id)
    #     rospy.sleep(1)
    #     table_size = [2, 2, 0.01]
    #     table_pose = PoseStamped()
    #     table_pose.header.frame_id = self.reference_frame
    #     table_pose.pose.position.x = 0.0
    #     table_pose.pose.position.y = 0.0
    #     table_pose.pose.position.z = -table_size[2]/2 -0.02
    #     table_pose.pose.orientation.w = 1.0
    #     self.scene.add_box(table_id, table_pose, table_size)
    #     self.setColor(table_id, 0.5, 0.5, 0.5, 1.0)
    #     self.sendColors()
    # def show_jonit_to_joint_transformation_matrix(self, joint_1, joint_2):
    #     """显示任意两个关节之间的齐次变换矩阵"""
    #     # 获取当前的关节状态（角度）
    #     joint_states, _ = self.get_current_joint_states()  # 获取当前关节角度
    #     if joint_states is None:
    #         messagebox.showerror("错误", "无法获取关节状态")
    #         return

    #     # 获取更新后的 D-H 参数
    #     updated_dh= self.update_dh_parameters(joint_states)  # 获取更新后的 D-H 参数
        
    #     # 提取关节1和关节2的参数
    #     joint_1_params = updated_dh[joint_1]
    #     joint_2_params = updated_dh[joint_2]
    #     # 打印 joint_1_params 和 joint_2_params
    #     print(f"关节 {joint_1} 的 D-H 参数: "
    #         f"θ={np.degrees(joint_1_params['theta']):.2f}° "
    #         f"α={np.degrees(joint_1_params['alpha']):.2f}° "
    #         f"a={joint_1_params['a']} "
    #         f"d={joint_1_params['d']}")

    #     print(f"关节 {joint_2} 的 D-H 参数: "
    #         f"θ={np.degrees(joint_2_params['theta']):.2f}° "
    #         f"α={np.degrees(joint_2_params['alpha']):.2f}° "
    #         f"a={joint_2_params['a']} "
    #         f"d={joint_2_params['d']}")

      
    #     # 计算从关节1到关节2的齐次变换矩阵
    #     T_1_to_2 = self.dh_to_transformation_matrix(joint_1_params, joint_2_params)

    #     # 格式化矩阵为字符串
    #     matrix_str = "\n".join(["\t".join([f"{value:.4f}" for value in row]) for row in T_1_to_2])
    #     self.create_matrix_popup(f"关节 {joint_1} 到 {joint_2} 的齐次变换矩阵", matrix_str, None)

    def show_jonit_to_joint_transformation_matrix(self, joint_1, joint_2):
        """显示任意两个关节之间的齐次变换矩阵"""
        # 获取当前的关节状态（角度）
        joint_states, _ = self.get_current_joint_states()  # 获取当前关节角度
        if joint_states is None:
            messagebox.showerror("错误", "无法获取关节状态")
            return

        # 获取更新后的 D-H 参数
        updated_dh = self.update_dh_parameters_tf(joint_states)  # 获取更新后的 D-H 参数
        print(updated_dh)
        # 计算从关节1到关节2的齐次变换矩阵
        transformation_matrix = self.calculate_transformation_matrix(updated_dh, joint_1, joint_2)

        # 格式化矩阵为字符串
        matrix_str = "\n".join(["\t".join([f"{value:.4f}" for value in row]) for row in transformation_matrix])
        self.create_matrix_popup(f"关节 {joint_1} 到 {joint_2} 的齐次变换矩阵", matrix_str, None)


    def update_transformation_matrix_popup(self):
        """更新齐次变换矩阵的内容"""
        transformation_matrix = self.get_current_pose()
        if transformation_matrix is not None:
            matrix_str = "\n".join(["\t".join([f"{value:.4f}" for value in row]) for row in transformation_matrix])
            return matrix_str
        else:
            return "获取失败"

    def update_jacobian_matrix_popup(self):
        """更新雅可比矩阵的内容"""
        jacobian_matrix = self.get_jacobian_matrix()
        if jacobian_matrix is not None:
            return jacobian_matrix
        else:
            return "获取失败"

    def update_dh_parameters_popup(self):
        """更新D-H参数的矩阵内容"""
        joint_states, _ = self.get_current_joint_states()
        if joint_states is not None:
            updated_dh = self.update_dh_parameters(joint_states)  # 更新D-H参数
            return self.format_dh_parameters(updated_dh)  # 返回格式化后的D-H参数列表
        return "获取失败"


    def go_home(self):
        """返回Home位置"""
        if self.is_moving:
            messagebox.showwarning("警告", "机械臂正在移动，请等待完成或停止当前任务")
            return
            
        self.status_var.set("状态: 返回Home位置")
        self.root.update()
        
        # 启用停止按钮
        self.stop_btn.config(state=tk.NORMAL)
        
        # 清空绘图
        self.clear_plot()
        
        # 在工作线程中执行移动
        threading.Thread(target=self._go_home).start()
    
    def _go_home(self):
        """实际执行返回Home位置"""
        # 使用关节空间控制移动到home位置，时间10秒
        if self.control_method == "PID":
            success = self.joint_space_control(self.home_joint_positions, 10.0)
        else:
            success = self.computed_torque_control(self.home_joint_positions, 10.0)
        
        # 只有在没有停止请求的情况下才更新按钮状态
        if not self.stop_requested:
            # 禁用停止按钮
            self.stop_btn.config(state=tk.DISABLED)

            if success:
                self.status_var.set("状态: 已返回Home位置")
            else:
                self.status_var.set("状态: 再点击一次Home键完成位置校准")

    def stop_movement(self):
        """停止当前移动"""
        if self.is_moving:
            self.status_var.set("状态: 正在停止...")
            # 更新按钮状态
            self.stop_btn.config(state=tk.DISABLED, text="正在停止", bg="#cccccc")
            self.root.update()

            self.stop_requested = True
            self.plotting_active = False  # 停止绘图

            # 启动线程监控停止状态
            threading.Thread(target=self.monitor_stop_status, daemon=True).start()
        else:
            self.status_var.set("状态: 未在移动中")
    
    def monitor_stop_status(self):
        """监控机械臂停止状态"""
        # 设置超时时间（5秒）
        timeout = time.time() + 5.0
        stopped = False

        while not rospy.is_shutdown() and time.time() < timeout and not stopped:
            # 获取当前关节速度
            _, velocities = self.get_current_joint_states()
            if velocities is None:
                rospy.sleep(0.1)
                continue

            # 检查所有关节速度是否接近零（停止）
            max_velocity = max(abs(v) for v in velocities)
            if max_velocity < 0.01:  # 0.01 rad/s 约0.57度/秒
                stopped = True
            else:
                rospy.sleep(0.1)

        # 在GUI线程中更新状态
        self.root.after(0, self.finalize_stop)
    

    def finalize_stop(self):
        """完成停止后的清理工作"""
        self.is_moving = False
        self.stop_requested = False

        # 恢复按钮状态
        self.stop_btn.config(state=tk.NORMAL, text="停止当前任务", bg="#ff9999")

        # 更新状态信息
        self.status_var.set("状态: 当前任务已停止")

        # 如果是计算力矩控制，切换回位置控制器
        if self.control_method == "CT":
            self.switch_back_to_position_controller()

    def shutdown_system(self):
        """关闭系统"""
        if hasattr(self, 'status_var'):
            self.status_var.set("状态: 正在关闭系统...")
            if self.root:
                self.root.update()
        
        # 停止任何移动
        self.stop_requested = True
        self.running = False
        
        # 关闭ROS节点
        rospy.signal_shutdown("用户请求关闭")
        
        # 关闭Gazebo
        os.system("pkill -f gazebo")
        os.system("pkill -f gzserver")
        os.system("pkill -f gzclient")
        
        # 关闭GUI
        if hasattr(self, 'root'):
            self.root.after(1000, self.root.destroy)
            self.root.after(1500, sys.exit)
        else:
            sys.exit()


if __name__ == "__main__":
    try:
        controller = UR5Control()
    except rospy.ROSInterruptException as e:
        rospy.logerr(f"ROS中断: {str(e)}")
    except Exception as e:
        rospy.logerr(f"程序异常: {str(e)}")
        rospy.logerr(traceback.format_exc())