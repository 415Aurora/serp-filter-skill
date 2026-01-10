import rospy
import actionlib
import numpy as np
import time
import math
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.msg import FollowJointTrajectoryAction, FollowJointTrajectoryGoal
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from controller_manager_msgs.srv import SwitchController, SwitchControllerRequest
import tf2_ros
import PyKDL
from .kinematics import JOINT_NAMES, load_robot_model

class UR5Controller:
    def __init__(self):
        # TF Buffer
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        
        # Controller Manager Service
        self.switch_controller_srv = rospy.ServiceProxy('/controller_manager/switch_controller', SwitchController)
        
        # Position Action Client
        self.client = actionlib.SimpleActionClient(
            '/eff_joint_traj_controller/follow_joint_trajectory', 
            FollowJointTrajectoryAction
        )
        
        # Effort Publisher
        self.effort_pub = rospy.Publisher(
            '/joint_group_eff_controller/command', 
            Float64MultiArray, 
            queue_size=10
        )
        
        self.current_controllers = ['eff_joint_traj_controller']
        self.effort_controller_name = "joint_group_eff_controller"
        self.robot_model = load_robot_model()
        
        # Control Params
        self.Kp = 1.5
        self.Ki = 0.01
        self.Kd = 0.4
        self.ct_Kp = 60.0
        self.ct_Kd = 10.0
        
        self.control_frequency = 20
        self.integral_errors = [0.0] * 6
        self.prev_errors = [0.0] * 6
        self.prev_torques = [0.0] * 6
        
    def wait_for_services(self):
        rospy.loginfo("Waiting for services and servers...")
        try:
            self.switch_controller_srv.wait_for_service(timeout=10.0)
        except:
            rospy.logwarn("Controller manager service not available")
            
        if not self.client.wait_for_server(rospy.Duration(10.0)):
            rospy.logwarn("Position controller action server not available")

    def get_joint_states(self):
        try:
            msg = rospy.wait_for_message("joint_states", JointState, timeout=5.0)
            pos, vel = [], []
            for name in JOINT_NAMES:
                idx = msg.name.index(name)
                pos.append(msg.position[idx])
                vel.append(msg.velocity[idx])
            return pos, vel
        except:
            return None, None

    def get_end_effector_pose(self):
        try:
            trans = self.tf_buffer.lookup_transform('base', 'wrist_3_link', rospy.Time(0), rospy.Duration(1.0))
            pos = trans.transform.translation
            rot = trans.transform.rotation
            q = [rot.x, rot.y, rot.z, rot.w]
            
            # Rotation matrix from quaternion
            R = np.array([
                [1 - 2*(q[1]**2 + q[2]**2), 2*(q[0]*q[1] - q[2]*q[3]), 2*(q[0]*q[2] + q[1]*q[3])],
                [2*(q[0]*q[1] + q[2]*q[3]), 1 - 2*(q[0]**2 + q[2]**2), 2*(q[1]*q[2] - q[0]*q[3])],
                [2*(q[0]*q[2] - q[1]*q[3]), 2*(q[1]*q[2] + q[0]*q[3]), 1 - 2*(q[0]**2 + q[1]**2)]
            ])
            T = np.eye(4)
            T[:3, :3] = R
            T[0, 3], T[1, 3], T[2, 3] = pos.x, pos.y, pos.z
            return T
        except:
            return None

    def switch_to_controller(self, start, stop):
        req = SwitchControllerRequest()
        req.start_controllers = start
        req.stop_controllers = stop
        req.strictness = 2
        req.start_asap = True
        req.timeout = 1.0
        try:
            resp = self.switch_controller_srv(req)
            if resp.ok:
                for c in stop:
                    if c in self.current_controllers: self.current_controllers.remove(c)
                self.current_controllers.extend(start)
                return True
        except:
            pass
        return False

    def calculate_ctc_torques(self, pos, vel, target_pos, target_vel, pos_err, vel_err, gravity_comp):
        if not self.robot_model: return None
        try:
            q = PyKDL.JntArray(6)
            qdot = PyKDL.JntArray(6)
            for i in range(6):
                q[i], qdot[i] = pos[i], vel[i]
                
            M = PyKDL.JntSpaceInertiaMatrix(6)
            self.robot_model['dyn_solver'].JntToMass(q, M)
            grav = PyKDL.JntArray(6)
            self.robot_model['dyn_solver'].JntToGravity(q, grav)
            coriolis = PyKDL.JntArray(6)
            self.robot_model['dyn_solver'].JntToCoriolis(q, qdot, coriolis)
            
            gain = 1.5 if gravity_comp else 1.0
            torques = []
            for i in range(6):
                accel = self.ct_Kp * pos_err[i] + self.ct_Kd * vel_err[i]
                t = sum(M[i, j] * accel for j in range(6))
                t += coriolis[i] + gain * grav[i]
                torques.append(np.clip(t, -100.0, 100.0))
            return torques
        except:
            return None
