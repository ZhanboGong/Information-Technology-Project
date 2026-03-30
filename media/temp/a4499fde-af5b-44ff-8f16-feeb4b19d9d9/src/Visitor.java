public class Visitor extends Person {
    private String ticketType;
    private String entryTime;

    // 默认构造函数
    public Visitor() {
        super();
        this.ticketType = "General";
        this.entryTime = "Unknown";
    }

    // 只需要名字和年龄的构造函数
    public Visitor(String name, int age) {
        super(name, age, "Unknown"); // 假设 contactNumber 默认为 "Unknown"
        this.ticketType = "General"; // 默认为 "General"
        this.entryTime = "Unknown"; // 默认值为 0
    }

    // 带参数的构造函数
    public Visitor(String name, int age, String contactNumber, String ticketType, String entryTime) {
        super(name, age, contactNumber);
        this.ticketType = ticketType;
        this.entryTime = entryTime;
    }

    // Getters 和 Setters
    public String getTicketType() {
        return ticketType;
    }

    public void setTicketType(String ticketType) {
        this.ticketType = ticketType;
    }

    public String getEntryTime() {
        return entryTime;
    }

    public void setEntryTime(String entryTime) {
        this.entryTime = entryTime;
    }
    @Override
    public String getName() {
        return super.getName();  // Call the getName() method from the Person class
    }
}
