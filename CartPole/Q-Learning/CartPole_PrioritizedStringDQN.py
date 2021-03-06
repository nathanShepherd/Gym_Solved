# Categorize Continuous State Space using Binning
# Aggregate reward in Q-Matrix using dictionary
# \\ \\ \\ \\ \\ \\ \\ \\
# Developed by Nathan Shepherd


import gym
import pickle
import random
import numpy as np
import matplotlib.pyplot as plt

def max_dict(d):
    max_val = float('-inf')
    max_key = ""
    for key, val in d.items():
        if val > max_val:
            max_val = val
            max_key = key
    return max_key, max_val

class DQN:
    def __init__(self, obs_space, num_bins, num_actions, observation):

        self.obs_space = obs_space
        self.num_actions = num_actions
        
        self.bins = self.get_bins(num_bins)
        self.init_Q_matrix(observation)
        self.transition_cache = []
        self.prior_heap = {}
        
        self.memory = {}#story transitions in BST
        
        self.sample_frequency = SAMPLE_FREQUENCY
        self.batch_size = BATCH_SIZE
        self.transition_depth = TRANSITION_DEPTH
        self.train_iters= 0

    def init_Q_matrix(self, obs):
        assert(len(obs)==self.obs_space)
        self.Q = {}
        self.find(''.join(str(int(elem)) for elem in self.digitize(obs)))

    def find(self, state_string):
        try:
            self.Q[state_string]
        except KeyError as e:
            self.Q[state_string] = {}
            for action in range(self.num_actions):
                self.Q[state_string][action] = 0

    def get_action(self, state):        
        string_state = ''.join(str(int(elem)) for elem in self.digitize(state))
        self.find(string_state)
        return max_dict( self.Q[string_state] )[0]

    def evaluate_utility(self, state):
        string_state = ''.join(str(int(elem)) for elem in self.digitize(state))
        self.find(string_state)
        return max_dict( self.Q[string_state] )[1]

    def update_policy(self, state, state_next, action, reward):
        state_value = self.evaluate_utility(state)
        
        action = self.get_action(state)
        reward_next = self.evaluate_utility(state_next)
        state_value += ALPHA*(reward + GAMMA * reward_next - state_value)

        state = ''.join(str(int(elem)) for elem in self.digitize(state))
        expected_state_value = self.Q[state][action]
        self.Q[state][action] = state_value

        #store transition trans_depth*(s, r, E(r), a, s_n) in memory
        t = [state, state_value, expected_state_value, action, state_next]
        self.transition_cache.append(t)
        if len(self.transition_cache) == self.transition_depth:
            priority = 1# assume highest initial priority of new states
            key = id(self.transition_cache)# avoiding repeats of exact sequence
            if key not in self.memory:
                self.memory[key] = self.transition_cache
                self.prior_heap[key] = priority
            
            self.transition_cache = []

        self.prioritized_replay()

    def prioritized_replay(self):
        # Partial Implimentation of RainbowDQN
        # @ https://arxiv.org/pdf/1710.02298.pdf
        #We construct the target distribution by
        #contracting the value distribution in St+n according to the
        #cumulative discount, and shifting it by the truncated n-step
        #discounted return
        self.train_iters += 1
        done = False
        
        if self.train_iters % self.sample_frequency == 0 and not done:
            # sample from memory self.batch_size
            # TODO: ACCORDING TO PRIORITY (self.prior_heap[key])
            keys = random.sample(list(self.memory), self.batch_size)
            #print(self.memory[keys[0]], self.transition_depth)
            assert(len(self.memory[keys[0]]) == self.transition_depth)

            #update values in Q function
            transitions = []
            for key in keys:
                transitions.append([self.memory[key], self.prior_heap[key]])
            transitions = sorted(transitions, key=lambda t:t[1])
            transitions = [trans[:-2] for trans in transitions]
            #[print(trans[1]) for trans in transitions]
            for i, trans in enumerate(transitions):
                #print(len(trans))
                for ep in trans:
                    if type(ep[1]) == list:
                        print("Recusive list ERROR")
                        break
                    while i > 0:
                        i -= 0.5
                        #[print(p) for p in ep]
                        self.update_policy(ep[0], ep[4], ep[3], ep[1])
                    
            #update priorites
            # proportionally to high diff in expected reward
            # abs(ExpectedValue(state) - Actual_Val(state))
            dead_keys = []
            for key in keys:
                total = 0
                #print(len(self.memory[key]))
                #print(self.memory[key])
                for trans in self.memory[key]:
                    #trans = state, state_value, expected_state_value, action, state_next
                    #print(trans[2]);
                    #print(trans[1], end="\n\n")
                    diff = abs(trans[2] - trans[1])
                    total += diff

                priority = np.sin( np.tanh( (np.pi*total) / 2 ) )
                self.prior_heap[key] = priority
                
            done = True
            
            
            
    
        

    def get_bins(self, num_bins):
        # Make 10 x state_depth matrix,  each column elem is range/10
        # Digitize using bins ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # obs[0]--> max: 0.265506 | min: -0.149958 | std: 0.151244
        # obs[1]--> max: 0.045574 | min: -0.036371 | std: 0.032354
        # obs[2]--> max: 0.241036 | min: -0.336625 | std: 0.205835
        # obs[3]--> max: 0.046279 | min: -0.051943 | std: 0.039247        
        
        bins = []
        ranges = [4.8, 5, 0.418, 5]
        for i in range(self.obs_space):
            # use minimum value to anchor buckets
            start, stop = -ranges[i], ranges[i]
            buckets = np.linspace(start, stop, num_bins)
            bins.append(buckets)
        return bins         
            
    def digitize(self, arr):
        # distrubute each elem in state to the index of the closest bin
        state = np.zeros(len(self.bins))
        for i in range(len(self.bins)):
            state[i] = np.digitize(arr[i], self.bins[i])
        return state

    def get_state_stats(self):
        for i in range(len(self.Q)):
            print("\nElem:",i,end=" ")
            keys = [key for key in self.Q[i].keys()]
            print("Range: [%s, %s]" % (min(keys), max(keys)),
                  "STDDEV:", round(np.std(keys), 3), "Count:" , len(keys))


def play_episode(agent, act_space, epsilon=.2, viz=False):
    state = env.reset()
    total_reward = 0
    terminal = False
    num_frames = 0

    max_rwd = -200
    while not terminal:
        if viz: env.render()
        #if num_frames > 300: epsilon = 0.1

        if random.random() < epsilon:
            action = env.action_space.sample()
        else:
            action = agent.get_action(state)
        
        state_next, reward, terminal, info = env.step(action)

        total_reward += reward
        
        if terminal:
            #if num_frames > 150:
            #    reward += np.log(num_frames)
        
            if  num_frames < 200:
                reward = -300

        action_next = agent.get_action(state_next)
        
        agent.update_policy(state, state_next, action, reward)
              
        state = state_next
        num_frames += 1
        

    return total_reward, num_frames

def train(obs_space, act_space=None,epochs=2000, obs=False, agent=False):
    if not agent: agent = DQN(obs_space, NUM_BINS, act_space, env.reset())

    stacked_frames = []
    #TODO: Plot reward averages
    rewards = [0]
    for ep in range(epochs):
        epsilon = max(EPSILON_MIN, np.tanh(-ep/(epochs/2))+ 1)

        ep_reward, num_frames = play_episode(agent, act_space, epsilon, viz=obs)
        if ep % 100 == 0:
            print("Ep: {} | {}".format(ep, epochs),
                  "%:", round(ep*100/epochs, 2),
                  "Epsilon:", round(epsilon, 4),
                  "Avg rwd:", round(np.mean(rewards),3),
                  "Ep rwd:", round(ep_reward, 3))

        stacked_frames.append(num_frames)
        rewards.append(ep_reward)

    return rewards, stacked_frames, agent

def observe(agent, N=15):
    [play_episode(agent, -1, viz=True) for ep in range(N)]

def plot_running_avg(reward_arr):
    N = len(reward_arr)
    #init unitialized array
    # (faster than np.zeros)
    running_avg = np.empty(N)

    for t in range(100, N):
        running_avg[t] = np.mean(reward_arr[t-100: t+1])

    plt.plot(running_avg, color="purple", label="Q-Learning Running Average")

def play_random(viz=False):
    observation = env.reset()
    total_reward = 0
    terminal = False

    while not terminal:
        if viz: env.render()
        action = env.action_space.sample()
        observation, reward, terminal, info = env.step(action)
        total_reward += reward

        #if terminal and num_frames < 200:
         #   reward = -300
        
    return total_reward

gym.envs.register(
    id='CartPoleExtraLong-v0',
    entry_point='gym.envs.classic_control:CartPoleEnv',
    max_episode_steps=250,
    reward_threshold=-110.0,
)
env = gym.make('CartPoleExtraLong-v0')
#env = gym.make('CartPole-v0')
observe_training = False
EPSILON_MIN = 0.1
NUM_BINS = 10
ALPHA = 0.01
GAMMA = 0.9

#Sample from DQN Memory
#Using Prior. Exp. Replay
SAMPLE_FREQUENCY = 500#500
TRANSITION_DEPTH = 5
BATCH_SIZE = 100
'''
          Concatinating bin indecies as string to correlate states
'''

EPOCHS = 10000

obs_space = 4
action_space = env.action_space.n

if __name__ == "__main__":
    episode_rewards, _, Agent = train(obs_space, act_space=action_space,
                                      epochs = EPOCHS, obs = observe_training)
    
    random_rwds = [play_random() for ep in range(EPOCHS)]

    plt.title("Average Reward with Q-Learning By Episode (CartPole)")
    plot_running_avg(episode_rewards)
    plt.plot(random_rwds, color="gray", label="Random Moves Running Average")

    plt.xlabel('Training Time (episodes)', fontsize=18)
    plt.ylabel('Average Reward per Episode', fontsize=16)
    plt.legend()
    plt.show()






















