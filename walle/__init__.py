"""WALL-E & EVE's Signal: an autonomous Bayesian search agent in a simulated world."""
from .agents import BayesianAgent, GreedySignalAgent, RandomAgent, make_agent
from .config import build_config, generate_mission, load_config
from .environment import Environment
from .runner import run_mission

__all__ = ["BayesianAgent", "GreedySignalAgent", "RandomAgent", "make_agent", "build_config",
           "generate_mission", "load_config", "Environment", "run_mission"]
__version__ = "1.0.0"
