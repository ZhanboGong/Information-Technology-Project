class Account:
    def __init__(self, bal):
        self.balance = bal  # 错误：未私有化

    def deposit(self, a):   # 错误：变量名无意义
        self.balance += a   # 错误：未检查 a <= 0