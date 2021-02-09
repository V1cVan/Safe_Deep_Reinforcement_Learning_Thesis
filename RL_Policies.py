from hwsim import CustomPolicy, ActionType
import tensorflow as tf
import numpy as np

class AcPolicyDiscrete(CustomPolicy):
    """
    Actor-critic on-policy RL controller for highway decision making.
    """
    LONG_ACTION = ActionType.REL_VEL
    LAT_ACTION = ActionType.LANE

    def __init__(self, trainer):
        super(AcPolicyDiscrete, self).__init__()
        self.trainer = trainer  # trainer = f(NN_model)


    def init_vehicle(self, veh):
        # Book-keeping of last states and actions
        # s0, a0, c0 = previous vehicle state and action-critic pair
        # s1, a1, c0 = current vehicle state action-critic pair

        veh.s0 = None
        veh.s0_mod = None
        veh.s1 = veh.s_raw
        veh.s1_mod = self.convert_state(veh)
        veh.a0 = None
        veh.a0_mod = None
        veh.a0_choice = None
        veh.c0 = None
        veh.a1_mod = None
        veh.a1_choice = None
        veh.a1 = None
        veh.c1 = None

    def custom_action(self, veh):
        # s0, a0 = previous vehicle state action pair
        # s1, a1 = current vehicle state action pair

        # Set current vehicle state and action pair
        veh.s1 = veh.s_raw
        veh.s1_mod = self.convert_state(veh)
        action_vel_probs, action_off_probs, veh.c1 = self.get_action_and_critic(veh.s1_mod)
        veh.a1_mod = [action_vel_probs, action_off_probs]
        action_choice_vel, action_choice_off = self.trainer.get_action_choice([action_vel_probs, action_off_probs])
        veh.a1_choice = [action_choice_vel, action_choice_off]
        veh.a1 = self.convert_action_discrete(veh, [action_choice_vel, action_choice_off])

        # Save experience
        if veh.a0_mod is not None:
            # Calculate reward at current state (if action was taken previously)
            veh.reward = self.get_reward(veh)
            if self.trainer is not None and self.trainer.training is True:
                # Save action taken previously on previous state value
                action = veh.a0_mod[0][0, veh.a0_choice[0]], veh.a0_mod[1][0, veh.a0_choice[1]]
                # Save to buffer from the Buffer class in HelperClasses.py module
                self.trainer.buffer.add_experience(self.trainer.timestep, np.squeeze(veh.s0_mod),
                                                   np.array(action[0]), np.array(action[1]),
                                                   veh.a0[0], veh.a0[1],
                                                   veh.a0_choice[0], veh.a0_choice[1],
                                                   veh.reward, np.squeeze(veh.c0))

        # Set past vehicle state and action pair
        veh.s0 = veh.s1
        veh.s0_mod = veh.s1_mod
        veh.a0 = veh.a1
        veh.a0_mod = veh.a1_mod
        veh.a0_choice = veh.a1_choice
        veh.c0 = veh.c1

        LONG_ACTION = veh.a1[0]
        LAT_ACTION = veh.a1[1]
        return np.array([LONG_ACTION, LAT_ACTION], dtype=np.float64)  # The hwsim library uses double precision floats

    def convert_state(self, veh):
        """
        Assembles state vector in TF form to pass to neural network.
        Normalises certain state variables and excludes constants.
        """

        # Normalise states and remove unnecessary states:
        lane_width = veh.s["laneC"]["width"]  # Excluded
        gap_to_road_edge = veh.s["gapB"]/(lane_width*3)  # Normalised
        max_vel = veh.s["maxVel"]  # Excluded
        curr_vel = veh.s["vel"][0]/max_vel  # Normalised and lateral component exluded


        # Current Lane:
        offset_current_lane_center = np.squeeze(veh.s["laneC"]["off"])/(lane_width)  # Normalised
        rel_offset_back_center_lane = np.hstack((np.squeeze(veh.s["laneC"]["relB"]["off"])[0]/150,
                                                 np.squeeze(veh.s["laneC"]["relB"]["off"])[1]/(lane_width)))  # Normalised to Dmax default
        rel_vel_back_center_lane = np.squeeze(veh.s["laneC"]["relB"]["vel"])/max_vel  # Normalised
        rel_offset_front_center_lane = np.hstack((np.squeeze(veh.s["laneC"]["relF"]["off"])[0]/150,
                                                  np.squeeze(veh.s["laneC"]["relF"]["off"])[1]/(lane_width)))  # Normalised to Dmax default
        rel_vel_front_center_lane = np.squeeze(veh.s["laneC"]["relF"]["vel"])/max_vel  # Normalised

        # Left Lane:
        offset_left_lane_center = np.squeeze(veh.s["laneL"]["off"])/(lane_width)  # Normalised
        rel_offset_back_left_lane = np.hstack((np.squeeze(veh.s["laneL"]["relB"]["off"])[0]/150,
                                               np.squeeze(veh.s["laneL"]["relB"]["off"])[1]/(lane_width)))  # Normalised to Dmax default
        rel_vel_back_left_lane = np.squeeze(veh.s["laneL"]["relB"]["vel"])/max_vel  # Normalised
        rel_offset_front_left_lane = np.hstack((np.squeeze(veh.s["laneL"]["relF"]["off"])[0]/150,
                                                np.squeeze(veh.s["laneL"]["relF"]["off"])[1]/(lane_width)))  # Normalised to Dmax default
        rel_vel_front_left_lane = np.squeeze(veh.s["laneL"]["relF"]["vel"])/max_vel  # Normalised

        # Right Lane:
        offset_right_lane_center = np.squeeze(veh.s["laneR"]["off"])/(lane_width)  # Normalised
        rel_offset_back_right_lane = np.hstack((np.squeeze(veh.s["laneR"]["relB"]["off"])[0]/150,
                                                np.squeeze(veh.s["laneR"]["relB"]["off"])[1]/(lane_width)))  # Normalised to Dmax default
        rel_vel_back_right_late = np.squeeze(veh.s["laneR"]["relB"]["vel"])/max_vel  # Normalised
        rel_offset_front_right_lane = np.hstack((np.squeeze(veh.s["laneR"]["relB"]["off"])[0]/150,
                                                 np.squeeze(veh.s["laneR"]["relB"]["off"])[1]/(lane_width)))  # Normalised to Dmax default
        rel_vel_front_right_late = np.squeeze(veh.s["laneR"]["relB"]["vel"])/max_vel  # Normalised

        # Assemble state vector
        state = np.hstack((gap_to_road_edge, curr_vel,
                          offset_current_lane_center, rel_offset_back_center_lane, rel_vel_back_center_lane, rel_offset_front_center_lane, rel_vel_front_center_lane,
                          offset_left_lane_center, rel_offset_back_left_lane, rel_vel_back_left_lane, rel_offset_front_left_lane, rel_vel_front_left_lane,
                          offset_right_lane_center, rel_offset_back_right_lane, rel_vel_back_right_late, rel_offset_front_right_lane, rel_vel_front_right_late))

        state = tf.convert_to_tensor(state, dtype=tf.float32, name="state_input")  # 30 entries
        state = tf.expand_dims(state, 0)
        return state  # Can be overridden by subclasses

    def get_action_and_critic(self, state):
        """ Get the modified action vector from the modified state vector. I.e. the mapping s_mod->a_mod """
        # Receive action and critic values from NN:
        action_vel_probs, action_off_probs, critic_prob = self.trainer.actor_critic_net(state)
        return action_vel_probs, action_off_probs, critic_prob

    def convert_action_discrete(self, veh, action_choices):
        """
        Get the action vector that will be passed to the vehicle from the given model action vector
        (used by the actor and critic models and available in veh). I.e. the mapping a_mod->a
        4 discrete actions: slow, maintain ,acc, left, centre, right
        """
        sim_action = np.array([0, 0], dtype=np.float32)
        vel_actions, off_actions = action_choices

        # Compute safe velocity action:
        vel_bounds = veh.a_bounds["long"]  # [min_rel_vel, max_rel_vel]
        if vel_actions == 0:  # Slow down
            vel_controller = np.maximum(vel_bounds[0], -3)
        elif vel_actions == 1:  # Constant speed
            vel_controller = 0
        elif vel_actions == 2:  # Speed up
            vel_controller = np.minimum(vel_bounds[1], +3)
        else:
            print("Error with setting vehicle velocity!")
        sim_action[0] = vel_controller

        # Compute safe offset action:
        off_bounds = veh.a_bounds["lat"]
        if off_actions == 0:  # Turn left
            off_controller = np.maximum(off_bounds[0], -1)
        elif off_actions == 1:  # Straight
            off_controller = 0
        elif off_actions == 2:  # Turn right
            off_controller = np.minimum(off_bounds[1], 1)
        else:
            print("Error with setting offset action!")
        sim_action[1] = off_controller

        return sim_action

    def get_reward(self, veh=None):
        """
        Calculate reward for actions.
        Reward = Speed + LaneCentre + FollowingDistance
        """
        # Reward function weightings:
        w_vel = self.trainer.reward_weights[0]  # Speed weight
        w_off = self.trainer.reward_weights[1]  # Lateral position
        w_dist = self.trainer.reward_weights[2]  # Lateral position

        # Reward function declaration:
        reward = np.array([0], dtype=np.float32)
        if veh is not None:
            # Velocity reward:
            v = np.squeeze(veh.s["vel"])[0]
            v_lim = 120 / 3.6
            r_vel = np.exp(-(v_lim - v) ** 2 / 140) - np.exp(-(v) ** 2 / 70)

            # Lane center reward:
            lane_offset = np.squeeze(veh.s["laneC"]["off"])
            r_off = np.exp(-(lane_offset) ** 2 / 3.6)

            # Following distance:
            d_gap = np.squeeze(veh.s["laneC"]["relF"]["gap"])[0]
            d_lim = 10
            r_follow = -np.exp(-(d_lim - d_gap) ** 2 / 20)

            reward = w_vel*r_vel + w_off*r_off + w_dist*r_follow
        else:
            reward = 0
        return reward
