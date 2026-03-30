public interface RideInterface {
    void addVisitorToQueue(Visitor v);
    void removeVisitorFromQueue(Visitor v);
    void printQueue();
    void runOneCycle();
    void addVisitorToHistory(Visitor v);
    boolean checkVisitorFromHistory(Visitor v);
    int numberOfVisitors();  // 返回已乘坐游乐设施的访客数量
    void PrintRideHistory(); // 打印所有已乘坐过游乐设施的访客信息
}

