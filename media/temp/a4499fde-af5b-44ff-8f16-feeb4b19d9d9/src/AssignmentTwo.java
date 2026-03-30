public class AssignmentTwo {
    public static void main(String[] args) {
        AssignmentTwo assignment = new AssignmentTwo();

        assignment.partThree();
        assignment.partFourA();
        assignment.partFourB();
        assignment.partFive();
        assignment.partSix();
        assignment.partSeven();
    }
    public void partThree(){
        System.out.println("Part 3");
        // 创建一个新的 Ride 对象
        Ride ride = new Ride("Ferris Wheel", 10, null);

        // 创建至少 5 个 Visitor 对象并添加到队列
        Visitor visitor1 = new Visitor("Alice", 25, "1234567890", "VIP", "10:01");
        Visitor visitor2 = new Visitor("Bob", 30, "0987654321", "General", "10:01");
        Visitor visitor3 = new Visitor("Charlie", 28, "1122334455", "VIP", "10:01");
        Visitor visitor4 = new Visitor("David", 35, "5566778899", "General", "10:01");
        Visitor visitor5 = new Visitor("Eva", 22, "6677889900", "Student", "10:01");

        // 将访客添加到队列
        ride.addVisitorToQueue(visitor1);
        ride.addVisitorToQueue(visitor2);
        ride.addVisitorToQueue(visitor3);
        ride.addVisitorToQueue(visitor4);
        ride.addVisitorToQueue(visitor5);

        // 从队列中移除一个访客
        ride.removeVisitorFromQueue(visitor3);

        // 打印队列中的所有访客
        ride.printQueue();
        System.out.println("——————————————————————————————————————————————————————————————————————————————————");
    }
    public void partFourA(){
        System.out.println("Part 4A");
        // 创建一个新的 Ride 对象
        Ride ride = new Ride("Ferris wheel", 10, null);

        // 创建至少 5 个 Visitor 对象并添加到队列
        Visitor visitor1 = new Visitor("Alice", 25, "1234567890", "VIP", "10:01");
        Visitor visitor2 = new Visitor("Bob", 30, "0987654321", "普通", "10:01");
        Visitor visitor3 = new Visitor("Charlie", 28, "1122334455", "VIP", "10:01");
        Visitor visitor4 = new Visitor("David", 35, "5566778899", "普通", "10:01");
        Visitor visitor5 = new Visitor("Eva", 22, "6677889900", "学生", "10:01");

        // 将访客添加到队列
        ride.addVisitorToQueue(visitor1);
        ride.addVisitorToQueue(visitor2);
        ride.addVisitorToQueue(visitor3);
        ride.addVisitorToQueue(visitor4);
        ride.addVisitorToQueue(visitor5);

        // 运行一个循环，让访客体验游乐设施
        ride.runOneCycle();
        ride.runOneCycle();
        ride.runOneCycle();

        // 检查一个特定访客是否已体验过游乐设施
        ride.checkVisitorFromHistory(visitor3);

        // 打印游乐设施历史记录中的访客数量
        System.out.println("Number of visitors who have already taken the amusement facilities:" + ride.numberOfVisitors());

        // 打印所有已经乘坐过游乐设施的访客
        ride.PrintRideHistory();
        System.out.println("——————————————————————————————————————————————————————————————————————————————————");
    }
    public void partFourB(){
        System.out.println("Part 4B");
        // 创建一个新的 Ride 对象
        Ride ride = new Ride("Ferris Wheel", 10, null);

        // 创建至少 5 个 Visitor 对象并添加到历史记录
        Visitor visitor1 = new Visitor("Alice", 25, "1234567890", "VIP", "10:01");
        Visitor visitor2 = new Visitor("Bob", 30, "0987654321", "General", "10:01");
        Visitor visitor3 = new Visitor("Charlie", 28, "1122334455", "VIP", "10:01");
        Visitor visitor4 = new Visitor("David", 35, "5566778899", "General", "10:01");
        Visitor visitor5 = new Visitor("Eva", 22, "6677889900", "Student", "10:01");

        // 添加访客到历史记录
        ride.addVisitorToHistory(visitor1);
        ride.addVisitorToHistory(visitor2);
        ride.addVisitorToHistory(visitor3);
        ride.addVisitorToHistory(visitor4);
        ride.addVisitorToHistory(visitor5);

        // 打印原始的历史记录
        System.out.println("Original historical records of amusement facilities:");
        ride.PrintRideHistory();

        // 使用 VisitorComparator 排序
        VisitorComparator comparator = new VisitorComparator();
        ride.sortRideHistory(comparator);

        // 打印排序后的历史记录
        System.out.println("\nSorted amusement facility history:");
        ride.PrintRideHistory();
        System.out.println("——————————————————————————————————————————————————————————————————————————————————");
    }
    public void partFive(){
        System.out.println("Part 5");
        // 创建一个新的 Ride 对象
        Employee rideOperator = new Employee("John", 40, "123-456-7890", "Operator", 5000);
        Ride ride = new Ride("Ferris Wheel", 10, rideOperator);

        // 创建至少 10 个 Visitor 对象并添加到队列
        Visitor visitor1 = new Visitor("Alice", 25, "1234567890", "VIP", "10:01");
        Visitor visitor2 = new Visitor("Bob", 30, "0987654321", "General", "10:01");
        Visitor visitor3 = new Visitor("Charlie", 28, "1122334455", "VIP", "10:01");
        Visitor visitor4 = new Visitor("David", 35, "5566778899", "General", "10:01");
        Visitor visitor5 = new Visitor("Eva", 22, "6677889900", "Student", "10:01");
        Visitor visitor6 = new Visitor("Frank", 27, "7788990011", "VIP", "10:01");
        Visitor visitor7 = new Visitor("Grace", 23, "8899001122", "General", "10:01");
        Visitor visitor8 = new Visitor("Hannah", 32, "9900112233", "Student", "10:01");
        Visitor visitor9 = new Visitor("Ivy", 21, "1112233445", "VIP", "10:01");
        Visitor visitor10 = new Visitor("Jack", 29, "2233445566", "General", "10:01");

        // 将游客添加到队列
        ride.addVisitorToQueue(visitor1);
        ride.addVisitorToQueue(visitor2);
        ride.addVisitorToQueue(visitor3);
        ride.addVisitorToQueue(visitor4);
        ride.addVisitorToQueue(visitor5);
        ride.addVisitorToQueue(visitor6);
        ride.addVisitorToQueue(visitor7);
        ride.addVisitorToQueue(visitor8);
        ride.addVisitorToQueue(visitor9);
        ride.addVisitorToQueue(visitor10);

        // 打印当前队列中的所有访客
        ride.printQueue();

        // 运行一个循环
        ride.runOneCycle();

        // 打印队列中的访客和历史记录
        System.out.println("\nAfter one cycle:");
        ride.printQueue();
        ride.PrintRideHistory();
        System.out.println("——————————————————————————————————————————————————————————————————————————————————");
    }
    public void partSix(){
        System.out.println("Part 6");
        // 创建一个新的 Ride 实例
        Ride ride = new Ride("Ferris Wheel", 10, new Employee("John", 40, "123-456-7890", "Operator", 5000));

        // Add 5 visitors to the ride history
        ride.addVisitorToHistory(new Visitor("Alice", 25, "1234567890", "VIP", "10:01"));
        ride.addVisitorToHistory(new Visitor("Grace", 23, "8899001122", "General", "10:01"));
        ride.addVisitorToHistory(new Visitor("Ivy", 21, "1112233445", "VIP", "10:01"));
        ride.addVisitorToHistory(new Visitor("Jack", 29, "2233445566", "General", "10:01"));
        ride.addVisitorToHistory(new Visitor("Eva", 22, "6677889900", "Student", "10:01"));

        // 将历史记录导出到文件
        ride.exportRideHistory("ride_history.csv");
        System.out.println("——————————————————————————————————————————————————————————————————————————————————");

    }
    public void partSeven(){
        System.out.println("Part 7");

        // 创建一个新的 Ride 实例
        Ride ride = new Ride("Ferris Wheel", 10, new Employee("John", 40, "123-456-7890", "Operator", 5000));

        // 从文件导入历史记录
        ride.importRideHistory("ride_history.csv");

        // 打印导入的访客数量
        System.out.println("Number of visitors in the history: " + ride.numberOfVisitors());

        // 打印所有导入的访客信息
        ride.PrintRideHistory();
        System.out.println("——————————————————————————————————————————————————————————————————————————————————"); }
}   