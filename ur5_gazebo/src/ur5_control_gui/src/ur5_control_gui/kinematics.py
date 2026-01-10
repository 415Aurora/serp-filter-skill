import numpy as np
import PyKDL
from urdf_parser_py.urdf import URDF as URDFParser
from kdl_parser_py import urdf
import rospy

# Joint names constant
JOINT_NAMES = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
               'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
JOINT_NAMES_TF = ['base', 'shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
                  'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']

# DH Parameters
DH_PARAMETERS = {
    "shoulder_pan_joint": {"a": 0, "alpha": np.pi/2, "d": 0.089159, "theta": 0},
    "shoulder_lift_joint": {"a": -0.425, "alpha": 0, "d": 0, "theta": 0},
    "elbow_joint": {"a": -0.39225, "alpha": 0, "d": 0, "theta": 0},
    "wrist_1_joint": {"a": 0, "alpha": np.pi/2, "d": 0.10915, "theta": 0},
    "wrist_2_joint": {"a": 0, "alpha": -np.pi/2, "d": 0.09465, "theta": 0},
    "wrist_3_joint": {"a": 0, "alpha": 0, "d": 0.0823, "theta": 0}
}

DH_PARAMETERS_TF = {
    "base": {"a": 0, "alpha": 0, "d": 0, "theta": 0},
    "shoulder_pan_joint": {"a": 0, "alpha": np.pi/2, "d": 0.089159, "theta": 0},
    "shoulder_lift_joint": {"a": -0.425, "alpha": 0, "d": 0, "theta": 0},
    "elbow_joint": {"a": -0.39225, "alpha": 0, "d": 0, "theta": 0},
    "wrist_1_joint": {"a": 0, "alpha": np.pi/2, "d": 0.10915, "theta": 0},
    "wrist_2_joint": {"a": 0, "alpha": -np.pi/2, "d": 0.09465, "theta": 0},
    "wrist_3_joint": {"a": 0, "alpha": 0, "d": 0.0823, "theta": 0}
}

def load_robot_model():
    """Load robot model for dynamics calculations."""
    try:
        robot_description = rospy.get_param('/robot_description')
        success, tree = urdf.treeFromString(robot_description)
        if not success:
            rospy.logerr("Could not create KDL tree from URDF")
            return None
        
        chain = tree.getChain("base", "wrist_3_link")
        if not chain:
            rospy.logerr("Could not create KDL chain")
            return None
        
        gravity = PyKDL.Vector(0, 0, -9.81)
        dyn_solver = PyKDL.ChainDynParam(chain, gravity)
        
        return {
            'chain': chain,
            'dyn_solver': dyn_solver,
            'gravity': gravity
        }
    except Exception as e:
        rospy.logerr(f"Error loading robot model: {str(e)}")
        return None

def update_dh_parameters(joint_angles, dh_params_dict):
    """Update DH parameters with current joint angles."""
    updated_dh = dh_params_dict.copy()
    for i, joint_name in enumerate(JOINT_NAMES):
        if joint_name in updated_dh:
            updated_dh[joint_name]["theta"] = joint_angles[i]
    return updated_dh

def dh_to_transformation_matrix(params):
    """Calculate transformation matrix from DH parameters."""
    a, alpha, d, theta = params["a"], params["alpha"], params["d"], params["theta"]
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    cos_a = np.cos(alpha)
    sin_a = np.sin(alpha)
    
    return np.array([
        [cos_t, -sin_t * cos_a, sin_t * sin_a, a * cos_t],
        [sin_t, cos_t * cos_a, -cos_t * sin_a, a * sin_t],
        [0, sin_a, cos_a, d],
        [0, 0, 0, 1]
    ])

def calculate_transformation_matrix(dh_params, joint_start, joint_end):
    """Calculate transformation matrix between two joints."""
    joint_names = list(DH_PARAMETERS_TF.keys())
    m = joint_names.index(joint_start)
    n = joint_names.index(joint_end)
    
    if m == n:
        return np.eye(4)
    
    reverse = False
    if m > n:
        m, n = n, m
        reverse = True
        
    transformation_matrix = np.eye(4)
    for i in range(m, n):
        # The original code used dh_to_transformation_matrix with next joint params
        # This assumes the standard DH convention where Ti maps frame i-1 to i
        joint_params = dh_params[joint_names[i+1]]
        transformation_matrix = np.dot(transformation_matrix, dh_to_transformation_matrix(joint_params))
        
    if reverse:
        transformation_matrix = np.linalg.inv(transformation_matrix)
        
    return transformation_matrix

def get_jacobian(robot_model, joint_positions):
    """Calculate Jacobian matrix."""
    if not robot_model:
        return None
        
    q = PyKDL.JntArray(len(JOINT_NAMES))
    for i in range(len(JOINT_NAMES)):
        q[i] = joint_positions[i]
        
    jacobian_solver = PyKDL.ChainJntToJacSolver(robot_model['chain'])
    jacobian = PyKDL.Jacobian(len(JOINT_NAMES))
    jacobian_solver.JntToJac(q, jacobian)
    
    # Convert to string format as requested by original GUI
    jacobian_str = "\n".join(
        ["\t".join([f"{jacobian[i, j]:.2f}" for j in range(len(JOINT_NAMES))]) for i in range(6)]
    )
    return jacobian_str
