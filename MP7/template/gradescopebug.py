import math

import gym
import numpy as np
import torch

import utils
from policies import QPolicy


class TabQPolicy(QPolicy):
    def __init__(self, env, buckets, actionsize, lr, gamma, model=None):
        """
        Inititalize the tabular q policy

        @param env: the gym environment
        @param buckets: specifies the discretization of the continuous state space for each dimension
        @param actionsize: dimension of the descrete action space.
        @param lr: learning rate for the model update 
        @param gamma: discount factor
        @param model (optional): Stores the Q-value for each state-action
            model = np.zeros(self.buckets + (actionsize,))
            
        """
        super().__init__(len(buckets), actionsize, lr, gamma)
        self.env = env
        self.buckets=buckets
        if model==None:
            self.model=np.zeros(self.buckets + (actionsize,))
        else:
            self.model=model
        self.C=1E3
        self.model2=np.zeros(self.buckets+ (actionsize,))#table holding the time Q(S,A) is updated
    def discretize(self, obs):
        """
        Discretizes the continuous input observation

        @param obs: continuous observation
        @return: discretized observation  
        """
        upper_bounds = [self.env.observation_space.high[0], self.env.observation_space.high[1]]
        lower_bounds = [self.env.observation_space.low[0], self.env.observation_space.low[1]]
        ratios = [(obs[i] + abs(lower_bounds[i])) / (upper_bounds[i] - lower_bounds[i]) for i in range(len(obs))]
        new_obs = [int(round((self.buckets[i] - 1) * ratios[i])) for i in range(len(obs))]
        new_obs = [min(self.buckets[i] - 1, max(0, new_obs[i])) for i in range(len(obs))]
        #print('tuple(new_obs)',tuple(new_obs))
        return tuple(new_obs)

    def qvals(self, states):
        """
        Returns the q values for the states.

        @param state: the state
        
        @return qvals: the q values for the state for each action. 
        """
        dstates = [self.discretize(state) for state in states]
        return np.array([self.model[state] for state in dstates])
    def td_step(self, state, action, reward, next_state, done):
        """
        One step TD update to the model

        @param state: the current state
        @param action: the action
        @param reward: the reward of taking the action at the current state
        @param next_state: the next state after taking the action at the
            current state
        @param done: true if episode has terminated, false otherwise
        @return loss: total loss the at this time step
        """
        if done == True and next_state[0] >= 0.5:  # following homework documentation
            reward = 1
        if next_state[0] < 0.5 or done == False:  # if the state is not terminal
            Target = np.max(self.qvals(next_state[np.newaxis])[0]) * self.gamma + reward
            Q = self.qvals(state[np.newaxis])[0][action]
        else:
            Target = reward
            Q = self.qvals(state[np.newaxis])[0][action]
        loss = np.square(Target - Q)
        index_tuple = self.discretize(state)
        product=self.C/(self.model2[index_tuple][action]+self.C)
        learningrate=min(self.lr,product)
        Qnew = Q + learningrate * (Target - Q)*product
        self.model[index_tuple][action] = Qnew  # get the index such that I can update the Q table
        self.model2[index_tuple][action]+=1
        return loss
   
    def save(self, outpath):
        """
        saves the model at the specified outpath
        """
        torch.save(self.model, outpath)


if __name__ == '__main__':
    args = utils.hyperparameters()

    env = gym.make('MountainCar-v0')

    statesize = env.observation_space.shape[0]
    actionsize = env.action_space.n
    policy = TabQPolicy(env, buckets=(18, 14), actionsize=actionsize, lr=args.lr, gamma=args.gamma)

    utils.qlearn(env, policy, args)
    #print('at the end Q is',policy.model)
    torch.save(policy.model, 'models/tabular.npy')
