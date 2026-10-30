from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def log(self, message: str):
        # Messaggio interno dell'agente per tracciare il processo
        pass
