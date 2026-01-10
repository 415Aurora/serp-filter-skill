import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import numpy as np
import threading
import time
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from .kinematics import JOINT_NAMES, JOINT_NAMES_TF, DH_PARAMETERS, DH_PARAMETERS_TF, update_dh_parameters, calculate_transformation_matrix, get_jacobian

class UR5GUI:
    def __init__(self, controller):
        self.ctrl = controller
        self.root = None
        self.running = True
        self.is_moving = False
        self.stop_requested = False
        self.plotting_active = False
        self.control_method = "PID"
        self.plot_data = {name: {'time': [], 'angle': []} for name in JOINT_NAMES}
        self.plot_start_time = time.time()
        
        # Home positions
        joint_angles_degrees = [0, -90, 0, -90, 0, 0]
        self.home_positions = [np.radians(a) for a in joint_angles_degrees]

    def start(self, ready_event):
        self.root = tk.Tk()
        self.root.title("UR5 Control Dashboard")
        self.root.geometry("900x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.setup_ui()
        
        threading.Thread(target=self.status_loop, daemon=True).start()
        ready_event.set()
        self.root.mainloop()

    def setup_ui(self):
        # Top buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10, fill=tk.X, padx=10)
        
        # Control methods
        method_frame = tk.LabelFrame(btn_frame, text="Control Method")
        method_frame.grid(row=0, column=0, columnspan=5, pady=5, sticky="ew")
        
        self.method_var = tk.StringVar(value="PID")
        tk.Radiobutton(method_frame, text="PID", variable=self.method_var, value="PID", command=self.update_method).grid(row=0, column=0, padx=10)
        tk.Radiobutton(method_frame, text="Computed Torque", variable=self.method_var, value="CT", command=self.update_method).grid(row=0, column=1, padx=10)
        
        # Action buttons
        tk.Button(btn_frame, text="Set Target", command=self.prompt_target, width=12).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="Go Home", command=self.go_home, width=12).grid(row=1, column=1, padx=5, pady=5)
        self.stop_btn = tk.Button(btn_frame, text="STOP", command=self.request_stop, width=12, bg="#ff9999")
        self.stop_btn.grid(row=1, column=2, padx=5, pady=5)
        tk.Button(btn_frame, text="Save Plot", command=self.save_plot, width=12).grid(row=1, column=3, padx=5, pady=5)
        tk.Button(btn_frame, text="Exit", command=self.on_close, width=12, bg="#ff6666").grid(row=1, column=4, padx=5, pady=5)
        
        # Matrix buttons
        tk.Button(btn_frame, text="EE Pose", command=self.show_ee_pose, bg="#ffcc99").grid(row=2, column=0, padx=5)
        tk.Button(btn_frame, text="Jacobian", command=self.show_jacobian, bg="#ffcc99").grid(row=2, column=1, padx=5)
        tk.Button(btn_frame, text="DH Table", command=self.show_dh, bg="#ffcc99").grid(row=2, column=2, padx=5)
        tk.Button(btn_frame, text="Joint-Joint T", command=self.prompt_joint_t, bg="#ffcc99").grid(row=2, column=3, padx=5)

        # Status
        status_frame = tk.LabelFrame(self.root, text="System Status")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        self.status_msg = tk.StringVar(value="Ready")
        tk.Label(status_frame, textvariable=self.status_msg, fg="blue").pack(anchor="w")
        self.pos_msg = tk.StringVar()
        tk.Label(status_frame, textvariable=self.pos_msg).pack(anchor="w")
        self.joint_msg = tk.StringVar()
        tk.Label(status_frame, textvariable=self.joint_msg).pack(anchor="w")

        # Plot
        self.fig = Figure(figsize=(8, 4))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Joint Angles (deg)")
        self.ax.grid(True)
        self.lines = {name: self.ax.plot([], [], label=name)[0] for name in JOINT_NAMES}
        self.ax.legend()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def on_close(self):
        self.running = False
        rospy.signal_shutdown("GUI Exit")
        self.root.destroy()

    def update_method(self):
        self.control_method = self.method_var.get()
        if self.control_method == "CT" and not self.ctrl.robot_model:
            messagebox.showwarning("Warning", "No dynamics model loaded. Falling back to PID.")
            self.method_var.set("PID")
            self.control_method = "PID"

    def status_loop(self):
        while self.running and not rospy.is_shutdown():
            pose = self.ctrl.get_end_effector_pose()
            if pose is not None:
                p = pose[:3, 3]
                self.pos_msg.set(f"EE Pose: x={p[0]:.3f}, y={p[1]:.3f}, z={p[2]:.3f}")
            
            joints, _ = self.ctrl.get_joint_states()
            if joints:
                js = ", ".join([f"{np.degrees(j):.1f}" for j in joints])
                self.joint_msg.set(f"Joints (deg): {js}")
                if self.plotting_active:
                    self.update_plot_data(joints)
            
            time.sleep(0.1)

    def update_plot_data(self, joints):
        t = time.time() - self.plot_start_time
        for i, name in enumerate(JOINT_NAMES):
            self.plot_data[name]['time'].append(t)
            self.plot_data[name]['angle'].append(np.degrees(joints[i]))
        self.root.after(0, self.refresh_plot)

    def refresh_plot(self):
        if not self.plotting_active: return
        for name in JOINT_NAMES:
            self.lines[name].set_data(self.plot_data[name]['time'], self.plot_data[name]['angle'])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def save_plot(self):
        path = filedialog.asksaveasfilename(defaultextension=".png")
        if path: self.fig.savefig(path)

    def request_stop(self):
        self.stop_requested = True
        self.is_moving = False
        self.status_msg.set("Stopping...")
        # Logic to send zero velocity or cancel goal would go here/in controller

    def go_home(self):
        if self.is_moving: return
        self.status_msg.set("Moving Home...")
        threading.Thread(target=self.execute_move, args=(self.home_positions, 10.0)).start()

    def prompt_target(self):
        # Minimal prompt logic for brevity in refactor
        target_str = simpledialog.askstring("Target", "Enter 6 angles (deg) separated by space:")
        if target_str:
            try:
                angles = [np.radians(float(a)) for a in target_str.split()]
                if len(angles) == 6:
                    self.execute_move(angles, 10.0)
            except:
                messagebox.showerror("Error", "Invalid input")

    def execute_move(self, target, duration):
        self.is_moving = True
        self.stop_requested = False
        self.plotting_active = True
        self.plot_start_time = time.time()
        for n in JOINT_NAMES: self.plot_data[n] = {'time': [], 'angle': []}
        
        if self.control_method == "PID":
            success = self.run_pid_control(target, duration)
        else:
            success = self.run_ctc_control(target, duration)
            
        self.is_moving = False
        self.status_msg.set("Move Complete" if success else "Move Stopped")

    def run_pid_control(self, target, duration):
        rate = rospy.Rate(self.ctrl.control_frequency)
        start = time.time()
        while time.time() - start < duration and not self.stop_requested:
            pos, vel = self.ctrl.get_joint_states()
            if not pos: continue
            
            err = [t - p for t, p in zip(target, pos)]
            if max(abs(e) for e in err) < 0.01: return True
            
            # Simple PID step
            dt = 1.0/self.ctrl.control_frequency
            self.ctrl.integral_errors = [i + e*dt for i, e in zip(self.ctrl.integral_errors, err)]
            out = [self.ctrl.Kp*e + self.ctrl.Ki*i for e, i in zip(err, self.ctrl.integral_errors)]
            
            # Send goal via action client
            goal = FollowJointTrajectoryGoal()
            goal.trajectory.joint_names = JOINT_NAMES
            p = JointTrajectoryPoint(positions=[p + o*dt for p, o in zip(pos, out)], time_from_start=rospy.Duration(0.1))
            goal.trajectory.points.append(p)
            self.ctrl.client.send_goal(goal)
            rate.sleep()
        return False

    def run_ctc_control(self, target, duration):
        if not self.ctrl.switch_to_controller([self.ctrl.effort_controller_name], self.ctrl.current_controllers):
            return False
            
        rate = rospy.Rate(self.ctrl.control_frequency)
        start = time.time()
        while time.time() - start < duration and not self.stop_requested:
            pos, vel = self.ctrl.get_joint_states()
            if not pos: continue
            
            err_p = [t - p for t, p in zip(target, pos)]
            if max(abs(e) for e in err_p) < 0.01: break
            
            err_v = [0 - v for v in vel]
            torques = self.ctrl.calculate_ctc_torques(pos, vel, target, [0]*6, err_p, err_v, max(abs(e) for e in err_p) < 0.1)
            
            if torques:
                msg = Float64MultiArray(data=torques)
                self.ctrl.effort_pub.publish(msg)
            rate.sleep()
            
        self.ctrl.switch_to_controller(['eff_joint_traj_controller'], [self.ctrl.effort_controller_name])
        return True

    def show_ee_pose(self):
        pose = self.ctrl.get_end_effector_pose()
        if pose is not None:
            s = "\n".join(["\t".join([f"{v:.4f}" for v in r]) for r in pose])
            messagebox.showinfo("EE Pose Matrix", s)

    def show_jacobian(self):
        pos, _ = self.ctrl.get_joint_states()
        if pos:
            jac = get_jacobian(self.ctrl.robot_model, pos)
            messagebox.showinfo("Jacobian", jac if jac else "Failed")

    def show_dh(self):
        pos, _ = self.ctrl.get_joint_states()
        if pos:
            params = update_dh_parameters(pos, DH_PARAMETERS)
            s = "Standard DH Table:\nJoint\tTheta\ta\tAlpha\td\n"
            for k, v in params.items():
                s += f"{k}\t{np.degrees(v['theta']):.1f}\t{v['a']}\t{np.degrees(v['alpha']):.1f}\t{v['d']}\n"
            messagebox.showinfo("DH Parameters", s)

    def prompt_joint_t(self):
        j1 = simpledialog.askstring("Joint 1", "Start Joint (e.g. base):")
        j2 = simpledialog.askstring("Joint 2", "End Joint (e.g. elbow_joint):")
        if j1 and j2:
            pos, _ = self.ctrl.get_joint_states()
            if pos:
                params = update_dh_parameters(pos, DH_PARAMETERS_TF)
                t = calculate_transformation_matrix(params, j1, j2)
                s = "\n".join(["\t".join([f"{v:.4f}" for v in r]) for r in t])
                messagebox.showinfo(f"T from {j1} to {j2}", s)

    def run_ctc_control(self, target, duration):
        # Already implemented above
        pass
