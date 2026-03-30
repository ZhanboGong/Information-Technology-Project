public class Employee extends Person {
    private String position;
    private double salary;

    // Default constructor
    public Employee() {
        super();
        this.position = "Unknown";
        this.salary = 0.0;
    }

    // Constructor with parameters
    public Employee(String name, int age, String contactNumber, String position, double salary) {
        super(name, age, contactNumber);
        this.position = position;
        this.salary = salary;
    }

    // Getters and setters
    public String getPosition() {
        return position;
    }

    public void setPosition(String position) {
        this.position = position;
    }

    public double getSalary() {
        return salary;
    }

    public void setSalary(double salary) {
        this.salary = salary;
    }
}
