from logic.calculator import add

class MathTool:
    def __init__(self):
        self.result = 0 # 故意不使用私有属性，看 AI 是否根据 L2 规范扣分

if __name__ == "__main__":
    print(f"Calculation Result: {add(5, 5)}")