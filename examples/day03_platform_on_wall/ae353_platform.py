import numpy as np
import pybullet as p
import time
import os.path

class RobotSimulator:
    def __init__(self):
        # Choose the time step
        self.dt = 0.01

        # Connect to and configure pybullet
        p.connect(p.GUI)
        p.setGravity(0, 0, -9.81)
        p.setPhysicsEngineParameter(fixedTimeStep=self.dt, numSubSteps=1)

        # Define the camera view
        p.resetDebugVisualizerCamera(3.5, 50, -35, (0., 0., 0.))

        # Disable the GUI controller
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)

        # Load plane
        p.loadURDF('./urdf/plane.urdf', baseOrientation=p.getQuaternionFromEuler([0., 0.5 * np.pi, 0.]))

        # Load robot (with mass and inertia coming from the URDF rather than being recomputed by pybullet)
        self.robot_id = p.loadURDF('./urdf/platform.urdf',
                                   flags=(p.URDF_USE_IMPLICIT_CYLINDER | p.URDF_USE_INERTIA_FROM_FILE))

        # Specify maximum applied torque
        self.tau_max = 5.

        # Create a dictionary that maps joint names to joint indices
        self.joint_map = {}
        for joint_index in range(p.getNumJoints(self.robot_id)):
            joint_name = p.getJointInfo(self.robot_id, joint_index)[1].decode('UTF-8')
            self.joint_map[joint_name] = joint_index

        # Create a 1D numpy array with the index (according to bullet) of each joint we care about
        self.joint_names = [
            'base_to_platform',
            'connector_to_wheel',
        ]
        self.num_joints = len(self.joint_names)
        self.joint_ids = np.array([self.joint_map[joint_name] for joint_name in self.joint_names])

        # Disable velocity control on joints so we can use torque control
        p.setJointMotorControlArray(self.robot_id, self.joint_ids,
                                    p.VELOCITY_CONTROL, forces=np.zeros(self.num_joints))

    def get_sensor_measurements(self):
        """
        returns joint angle and joint velocity of platform and wheel
        """
        q, v = self.get_state()
        return q[0], v[0], q[1], v[1]

    def set_actuator_commands(self, tau_desired):
        """
        sets the applied torque to the number given by tau, clipped to bounds
        """
        tau = np.clip(tau_desired, -self.tau_max, self.tau_max)
        self.set_joint_torque(np.array([0., tau]))
        return tau

    def reset(self):
        """
        sets all joint angles and joint velocities to zero
        """
        self.set_state(np.zeros(2), np.zeros(2))

    def get_state(self):
        """
        returns two 1D numpy arrays: joint positions and joint velocities
        """
        joint_states = p.getJointStates(self.robot_id, self.joint_ids)
        q = np.zeros([self.num_joints])
        v = np.zeros_like(q)
        for i in range(self.num_joints):
            q[i] = joint_states[i][0]
            v[i] = joint_states[i][1]
        return q, v

    def set_state(self, q, v=None):
        """
        sets the state to the joint positions and joint velocities that are
        specified by 1D numpy arrays q and (optionally) v, respectively
        """
        if v is None:
            v = np.zeros_like(q)
        for i, joint_id in enumerate(self.joint_ids):
            p.resetJointState(self.robot_id, joint_id, q[i], v[i])

    def set_joint_torque(self, tau):
        """
        sets joint torques (or forces) to the values specified by the 1D numpy
        array tau
        """
        assert(tau.shape[0] == self.num_joints)
        zero_gains = tau.shape[0] * (0.,)
        p.setJointMotorControlArray(self.robot_id, self.joint_ids,
                                    p.TORQUE_CONTROL, forces=tau,
                                    positionGains=zero_gains, velocityGains=zero_gains)

    def step(self):
        """
        does one step in the simulation
        """
        time.sleep(self.dt)
        p.stepSimulation()
